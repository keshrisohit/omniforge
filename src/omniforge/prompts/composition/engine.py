"""Composition engine for orchestrating prompt composition across layers.

This module provides the CompositionEngine class that orchestrates the complete
prompt composition flow: loading prompts from layers, merging, rendering, and caching.
"""

import logging
import time
from typing import Any, Dict, Optional, Union

from omniforge.prompts.cache.keys import generate_cache_key
from omniforge.prompts.cache.manager import CacheManager
from omniforge.prompts.composition.merge import MergeProcessor
from omniforge.prompts.composition.renderer import TemplateRenderer
from omniforge.prompts.enums import PromptLayer
from omniforge.prompts.errors import PromptCompositionError, PromptNotFoundError
from omniforge.prompts.models import ComposedPrompt, Prompt
from omniforge.prompts.storage.repository import PromptRepository
from omniforge.prompts.validation.safety import SafetyValidator

logger = logging.getLogger(__name__)


class CompositionEngine:
    """Main composition engine for orchestrating prompt assembly across layers.

    The CompositionEngine coordinates the entire prompt composition workflow:
    1. Check cache for existing composed prompt
    2. Load prompts from all applicable layers (SYSTEM, TENANT, FEATURE, AGENT)
    3. Apply merge point processing to combine layers
    4. Build complete variable context with namespacing
    5. Render final template with variables
    6. Store result in cache
    7. Return ComposedPrompt with metadata

    Attributes:
        _repository: Prompt storage repository
        _cache: Optional cache manager for composed prompts
        _renderer: Template renderer for variable substitution
        _merge_processor: Merge point processor for layer combination
        _safety_validator: Safety validator for user input sanitization
    """

    def __init__(
        self,
        repository: PromptRepository,
        cache: Optional[CacheManager] = None,
    ) -> None:
        """Initialize the composition engine.

        Args:
            repository: Prompt repository for loading prompts
            cache: Optional cache manager for caching composed prompts
        """
        self._repository = repository
        self._cache = cache
        self._renderer = TemplateRenderer()
        self._merge_processor = MergeProcessor()
        self._safety_validator = SafetyValidator()

        logger.info(f"CompositionEngine initialized with cache_enabled={cache is not None}")

    async def compose(
        self,
        agent_id: str,
        tenant_id: Optional[str] = None,
        feature_ids: Optional[Union[str, list[str]]] = None,
        user_input: Optional[str] = None,
        variables: Optional[Dict[str, Any]] = None,
        skip_cache: bool = False,
    ) -> ComposedPrompt:
        """Compose a prompt by loading, merging, and rendering all layers.

        This is the main entry point for prompt composition. It orchestrates
        the complete workflow from cache check to final rendering.

        Args:
            agent_id: ID of the agent requesting the prompt
            tenant_id: Optional tenant ID for multi-tenancy
            feature_ids: Optional feature ID(s) to include (string or list)
            user_input: Optional user input to sanitize and inject
            variables: Optional variables for template rendering
            skip_cache: If True, bypass cache and force recomposition

        Returns:
            ComposedPrompt with final content and metadata

        Raises:
            PromptNotFoundError: If required prompts are not found
            PromptCompositionError: If composition fails

        Example:
            >>> engine = CompositionEngine(repository)
            >>> result = await engine.compose(
            ...     agent_id="agent-123",
            ...     tenant_id="tenant-456",
            ...     user_input="What is AI?",
            ...     variables={"context": "general"}
            ... )
            >>> print(result.content)
            'System: ... Agent: ... User: What is AI?'
        """
        start_time = time.time()

        # Sanitize user input for safety
        sanitized_user_input = (
            self._safety_validator.sanitize_user_input(user_input) if user_input else None
        )

        # Normalize feature_ids to list
        feature_id_list: list[str] = []
        if feature_ids:
            if isinstance(feature_ids, str):
                feature_id_list = [feature_ids]
            else:
                feature_id_list = list(feature_ids)

        # Try cache first (if not skipping)
        cache_key = None
        if not skip_cache and self._cache:
            # Load prompts to get version info for cache key
            layer_prompts = await self._load_layer_prompts(agent_id, tenant_id, feature_id_list)
            version_ids = self._extract_version_ids(layer_prompts)
            cache_key = generate_cache_key(version_ids, variables)

            cached_prompt = await self._cache.get(cache_key)
            if cached_prompt:
                logger.debug(f"Cache hit for key: {cache_key[:16]}...")
                return cached_prompt

        # Cache miss - perform full composition
        logger.debug(
            f"Composing prompt for agent={agent_id}, tenant={tenant_id}, "
            f"features={feature_id_list}"
        )

        # Load prompts from all layers
        layer_prompts = await self._load_layer_prompts(agent_id, tenant_id, feature_id_list)

        # Merge prompts across layers
        merged_template = await self._merge_processor.merge(
            layer_prompts, user_input=sanitized_user_input
        )

        # Build complete variable context
        variable_context = self._build_variable_context(tenant_id, agent_id, variables or {})

        # Render final template with variables
        rendered_content = await self._renderer.render(merged_template, variable_context)

        # Calculate composition time
        composition_time_ms = (time.time() - start_time) * 1000

        # Extract version metadata
        layer_versions = self._extract_layer_versions(layer_prompts)

        # Create composed prompt result
        composed_prompt = ComposedPrompt(
            content=rendered_content,
            layer_versions=layer_versions,
            cache_key=cache_key,
            composition_time_ms=composition_time_ms,
        )

        # Store in cache
        if self._cache and cache_key:
            await self._cache.set(cache_key, composed_prompt)
            logger.debug(f"Cached composed prompt with key: {cache_key[:16]}...")

        logger.info(
            f"Composition completed in {composition_time_ms:.2f}ms " f"for agent={agent_id}"
        )

        return composed_prompt

    async def _load_layer_prompts(
        self,
        agent_id: str,
        tenant_id: Optional[str],
        feature_ids: list[str],
    ) -> Dict[PromptLayer, Optional[Prompt]]:
        """Load prompts from all applicable layers.

        Loads prompts from SYSTEM, TENANT, FEATURE, and AGENT layers.
        Missing layers are gracefully skipped (set to None).

        Args:
            agent_id: Agent ID for agent layer
            tenant_id: Optional tenant ID for tenant layer
            feature_ids: List of feature IDs for feature layer

        Returns:
            Dictionary mapping layers to their prompts (None if not found)

        Raises:
            PromptNotFoundError: If SYSTEM or AGENT layer prompts are not found
        """
        layer_prompts: Dict[PromptLayer, Optional[Prompt]] = {}

        # Load SYSTEM layer (required)
        system_prompt = await self._repository.get_by_layer(PromptLayer.SYSTEM, scope_id="default")
        if not system_prompt:
            raise PromptNotFoundError("system:default")
        layer_prompts[PromptLayer.SYSTEM] = system_prompt

        # Load TENANT layer (optional)
        if tenant_id:
            tenant_prompt = await self._repository.get_by_layer(
                PromptLayer.TENANT, scope_id=tenant_id, tenant_id=tenant_id
            )
            layer_prompts[PromptLayer.TENANT] = tenant_prompt
        else:
            layer_prompts[PromptLayer.TENANT] = None

        # Load FEATURE layer (optional, may have multiple)
        if feature_ids:
            feature_prompts = []
            for feature_id in feature_ids:
                feature_prompt = await self._repository.get_by_layer(
                    PromptLayer.FEATURE, scope_id=feature_id, tenant_id=tenant_id
                )
                if feature_prompt:
                    feature_prompts.append(feature_prompt)

            # Merge multiple feature prompts if needed
            if feature_prompts:
                merged_feature = await self._merge_feature_prompts(feature_prompts)
                layer_prompts[PromptLayer.FEATURE] = merged_feature
            else:
                layer_prompts[PromptLayer.FEATURE] = None
        else:
            layer_prompts[PromptLayer.FEATURE] = None

        # Load AGENT layer (required)
        agent_prompt = await self._repository.get_by_layer(
            PromptLayer.AGENT, scope_id=agent_id, tenant_id=tenant_id
        )
        if not agent_prompt:
            raise PromptNotFoundError(f"agent:{agent_id}")
        layer_prompts[PromptLayer.AGENT] = agent_prompt

        return layer_prompts

    async def _merge_feature_prompts(self, prompts: list[Prompt]) -> Prompt:
        """Merge multiple feature prompts into a single prompt.

        When multiple features are specified, their prompts are combined
        by concatenating their content sections.

        Args:
            prompts: List of feature prompts to merge

        Returns:
            Single merged feature prompt

        Raises:
            PromptCompositionError: If merging fails
        """
        if not prompts:
            raise PromptCompositionError("No feature prompts to merge")

        if len(prompts) == 1:
            return prompts[0]

        # Use the first prompt as base and merge content from others
        base_prompt = prompts[0]
        merged_content_parts = [base_prompt.content]

        for prompt in prompts[1:]:
            merged_content_parts.append(prompt.content)

        # Create a new merged prompt
        merged_prompt = Prompt(
            id=f"feature:merged:{'-'.join(p.id for p in prompts)}",
            layer=PromptLayer.FEATURE,
            scope_id=f"merged:{'-'.join(p.scope_id for p in prompts)}",
            name=f"Merged: {', '.join(p.name for p in prompts)}",
            content="\n\n".join(merged_content_parts),
            merge_points=base_prompt.merge_points,
            variables_schema=base_prompt.variables_schema,
            tenant_id=base_prompt.tenant_id,
            version=1,
        )

        return merged_prompt

    def _build_variable_context(
        self,
        tenant_id: Optional[str],
        agent_id: str,
        user_variables: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build complete variable context with namespacing.

        Creates a namespaced variable context that includes:
        - system: Platform-level variables
        - tenant: Tenant-specific variables
        - agent: Agent-specific variables
        - user-provided variables (top-level)

        Args:
            tenant_id: Optional tenant ID
            agent_id: Agent ID
            user_variables: User-provided variables

        Returns:
            Complete variable context dictionary

        Example:
            >>> engine._build_variable_context("tenant-1", "agent-1", {"query": "test"})
            {
                "system": {"platform_name": "OmniForge", "platform_version": "1.0.0"},
                "tenant": {"id": "tenant-1"},
                "agent": {"id": "agent-1"},
                "query": "test"
            }
        """
        context: Dict[str, Any] = {
            # System-level variables
            "system": {
                "platform_name": "OmniForge",
                "platform_version": "1.0.0",
            },
            # Tenant-level variables
            "tenant": {
                "id": tenant_id or "default",
            },
            # Agent-level variables
            "agent": {
                "id": agent_id,
            },
        }

        # Add user-provided variables at top level
        context.update(user_variables)

        return context

    def _extract_version_ids(
        self, layer_prompts: Dict[PromptLayer, Optional[Prompt]]
    ) -> dict[str, str]:
        """Extract version IDs from layer prompts for cache key generation.

        Args:
            layer_prompts: Dictionary of layer prompts

        Returns:
            Dictionary mapping layer names to version IDs
        """
        version_ids: dict[str, str] = {}

        for layer, prompt in layer_prompts.items():
            if prompt:
                version_ids[layer.value] = f"{prompt.id}:v{prompt.version}"

        return version_ids

    def _extract_layer_versions(
        self, layer_prompts: Dict[PromptLayer, Optional[Prompt]]
    ) -> dict[str, int]:
        """Extract layer version numbers for metadata.

        Args:
            layer_prompts: Dictionary of layer prompts

        Returns:
            Dictionary mapping layer names to version numbers
        """
        layer_versions: dict[str, int] = {}

        for layer, prompt in layer_prompts.items():
            if prompt:
                layer_versions[layer.value] = prompt.version

        return layer_versions
