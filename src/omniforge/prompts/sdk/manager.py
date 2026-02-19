"""SDK PromptManager - Main entry point for programmatic prompt management.

This module provides the PromptManager class, which is the primary interface
for developers to interact with the prompt management system.
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Optional, Union

from omniforge.prompts.cache.manager import CacheManager
from omniforge.prompts.composition.engine import CompositionEngine
from omniforge.prompts.enums import PromptLayer
from omniforge.prompts.errors import PromptNotFoundError
from omniforge.prompts.experiments.manager import ExperimentManager
from omniforge.prompts.models import (
    ComposedPrompt,
    ExperimentVariant,
    MergePointDefinition,
    Prompt,
    PromptExperiment,
    PromptVersion,
    VariableSchema,
)
from omniforge.prompts.storage.memory import InMemoryPromptRepository
from omniforge.prompts.storage.repository import PromptRepository
from omniforge.prompts.validation.schema import SchemaValidator
from omniforge.prompts.validation.syntax import SyntaxValidator
from omniforge.prompts.versioning.manager import VersionManager

logger = logging.getLogger(__name__)


class PromptManager:
    """Main SDK interface for prompt management operations.

    PromptManager provides a clean, developer-friendly API for all prompt
    management operations including CRUD, versioning, composition, validation,
    and experiments. It orchestrates all underlying components and provides
    sensible defaults for easy setup.

    Attributes:
        tenant_id: Default tenant ID for operations (optional)
        _repository: Storage backend for prompts
        _cache_manager: Cache manager for composed prompts
        _composition_engine: Engine for prompt composition
        _version_manager: Manager for version operations
        _experiment_manager: Manager for A/B test experiments
        _syntax_validator: Validator for template syntax
        _schema_validator: Validator for variable schemas

    Example:
        >>> # Simple usage with defaults
        >>> manager = PromptManager()
        >>>
        >>> # Create a prompt
        >>> prompt = await manager.create_prompt(
        ...     layer=PromptLayer.AGENT,
        ...     name="my-agent",
        ...     content="You are a helpful assistant.",
        ...     scope_id="agent-123",
        ...     created_by="user-1"
        ... )
        >>>
        >>> # Compose a prompt
        >>> result = await manager.compose_prompt(
        ...     agent_id="agent-123",
        ...     user_input="Hello!"
        ... )
    """

    def __init__(
        self,
        tenant_id: Optional[str] = None,
        repository: Optional[PromptRepository] = None,
        cache_manager: Optional[CacheManager] = None,
        enable_cache: bool = True,
    ) -> None:
        """Initialize the PromptManager with sensible defaults.

        Args:
            tenant_id: Optional default tenant ID for operations
            repository: Optional custom repository (defaults to InMemoryPromptRepository)
            cache_manager: Optional custom cache manager
            enable_cache: Whether to enable caching (default: True)

        Example:
            >>> # Use with defaults
            >>> manager = PromptManager()
            >>>
            >>> # Use with tenant
            >>> manager = PromptManager(tenant_id="tenant-123")
            >>>
            >>> # Use with custom repository
            >>> custom_repo = MyCustomRepository()
            >>> manager = PromptManager(repository=custom_repo)
        """
        self.tenant_id = tenant_id

        # Initialize repository with default if not provided
        self._repository = repository if repository else InMemoryPromptRepository()

        # Initialize cache manager if caching is enabled
        if enable_cache and cache_manager is None:
            self._cache_manager: Optional[CacheManager] = CacheManager(
                max_memory_items=1000,
                default_ttl=3600,
            )
        else:
            self._cache_manager = cache_manager

        # Initialize composition engine
        self._composition_engine = CompositionEngine(
            repository=self._repository,
            cache=self._cache_manager,
        )

        # Initialize version manager
        self._version_manager = VersionManager(repository=self._repository)

        # Initialize experiment manager
        self._experiment_manager = ExperimentManager(repository=self._repository)

        # Initialize validators
        self._syntax_validator = SyntaxValidator()
        self._schema_validator = SchemaValidator()

        logger.info(
            f"PromptManager initialized with tenant_id={tenant_id}, "
            f"cache_enabled={self._cache_manager is not None}"
        )

    # Prompt CRUD Operations

    async def create_prompt(
        self,
        layer: PromptLayer,
        name: str,
        content: str,
        scope_id: str,
        created_by: str,
        description: Optional[str] = None,
        merge_points: Optional[list[dict[str, Any]]] = None,
        variables_schema: Optional[dict[str, Any]] = None,
    ) -> Prompt:
        """Create a new prompt with validation and initial version.

        Args:
            layer: Hierarchical layer for the prompt
            name: Human-readable prompt name
            content: Prompt template content
            scope_id: Scope identifier (e.g., agent_id, tenant_id)
            created_by: ID of user creating the prompt
            description: Optional human-readable description
            merge_points: Optional list of merge point definitions as dicts
            variables_schema: Optional variable schema as dict

        Returns:
            Created Prompt with version 1

        Raises:
            PromptValidationError: If syntax validation fails
            PromptValidationError: If schema validation fails

        Example:
            >>> prompt = await manager.create_prompt(
            ...     layer=PromptLayer.AGENT,
            ...     name="support-agent",
            ...     content="You are a support agent. {{ context }}",
            ...     scope_id="agent-456",
            ...     created_by="user-1",
            ...     merge_points=[
            ...         {"name": "context", "behavior": "append", "required": False}
            ...     ],
            ...     variables_schema={
            ...         "properties": {"context": {"type": "string"}},
            ...         "required": ["context"]
            ...     }
            ... )
        """
        # Validate template syntax
        syntax_errors = self._syntax_validator.validate(content)
        if syntax_errors:
            from omniforge.prompts.errors import PromptValidationError

            raise PromptValidationError(
                message=f"Template syntax errors: {', '.join(syntax_errors)}",
                field="content",
                details={"errors": syntax_errors},
            )

        # Build merge points from dicts
        merge_point_defs: list[MergePointDefinition] = []
        if merge_points:
            for mp_dict in merge_points:
                merge_point_defs.append(MergePointDefinition(**mp_dict))

        # Build variable schema from dict
        var_schema: Optional[VariableSchema] = None
        if variables_schema:
            var_schema = VariableSchema(**variables_schema)
            # Validate schema
            schema_errors = self._schema_validator.validate_schema(var_schema)
            if schema_errors:
                from omniforge.prompts.errors import PromptValidationError

                raise PromptValidationError(
                    message=f"Schema validation errors: {', '.join(schema_errors)}",
                    field="variables_schema",
                    details={"errors": schema_errors},
                )

        # Generate prompt ID
        prompt_id = f"prompt_{uuid.uuid4().hex}"

        # Create prompt
        prompt = Prompt(
            id=prompt_id,
            layer=layer,
            scope_id=scope_id,
            name=name,
            content=content,
            merge_points=merge_point_defs,
            variables_schema=var_schema,
            tenant_id=self.tenant_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            version=1,
        )

        # Save to repository
        created_prompt = await self._repository.create(prompt)

        # Create initial version
        await self._version_manager.create_initial_version(created_prompt, created_by)

        logger.info(f"Created prompt {created_prompt.id} in layer {layer.value}")
        return created_prompt

    async def get_prompt(self, prompt_id: str) -> Prompt:
        """Retrieve a prompt by ID.

        Args:
            prompt_id: The prompt ID to retrieve

        Returns:
            The prompt

        Raises:
            PromptNotFoundError: If prompt does not exist

        Example:
            >>> prompt = await manager.get_prompt("prompt_abc123")
            >>> print(prompt.name)
        """
        prompt = await self._repository.get(prompt_id)
        if not prompt:
            raise PromptNotFoundError(prompt_id)

        return prompt

    async def update_prompt(
        self,
        prompt_id: str,
        content: str,
        change_message: str,
        changed_by: str,
        merge_points: Optional[list[dict[str, Any]]] = None,
        variables_schema: Optional[dict[str, Any]] = None,
    ) -> Prompt:
        """Update a prompt's content and create a new version.

        Args:
            prompt_id: ID of the prompt to update
            content: New prompt content
            change_message: Description of what changed
            changed_by: ID of user making the change
            merge_points: Optional updated merge points as dicts
            variables_schema: Optional updated variable schema as dict

        Returns:
            Updated Prompt

        Raises:
            PromptNotFoundError: If prompt does not exist
            PromptValidationError: If validation fails
            PromptLockViolationError: If prompt is locked

        Example:
            >>> updated = await manager.update_prompt(
            ...     prompt_id="prompt_abc123",
            ...     content="Updated content",
            ...     change_message="Added new instructions",
            ...     changed_by="user-1"
            ... )
        """
        # Get existing prompt
        prompt = await self.get_prompt(prompt_id)

        # Validate template syntax
        syntax_errors = self._syntax_validator.validate(content)
        if syntax_errors:
            from omniforge.prompts.errors import PromptValidationError

            raise PromptValidationError(
                message=f"Template syntax errors: {', '.join(syntax_errors)}",
                field="content",
                details={"errors": syntax_errors},
            )

        # Build merge points if provided
        merge_point_defs: Optional[list[MergePointDefinition]] = None
        if merge_points is not None:
            merge_point_defs = []
            for mp_dict in merge_points:
                merge_point_defs.append(MergePointDefinition(**mp_dict))

        # Build variable schema if provided
        var_schema: Optional[VariableSchema] = None
        if variables_schema is not None:
            var_schema = VariableSchema(**variables_schema)
            # Validate schema
            schema_errors = self._schema_validator.validate_schema(var_schema)
            if schema_errors:
                from omniforge.prompts.errors import PromptValidationError

                raise PromptValidationError(
                    message=f"Schema validation errors: {', '.join(schema_errors)}",
                    field="variables_schema",
                    details={"errors": schema_errors},
                )

        # Update prompt content
        prompt.content = content
        prompt.updated_at = datetime.utcnow()
        if merge_point_defs is not None:
            prompt.merge_points = merge_point_defs
        if var_schema is not None:
            prompt.variables_schema = var_schema

        # Save updated prompt
        updated_prompt = await self._repository.update(prompt)

        # Create new version
        await self._version_manager.create_version(
            prompt=updated_prompt,
            change_message=change_message,
            changed_by=changed_by,
        )

        # Invalidate cache for this prompt
        if self._cache_manager:
            await self._invalidate_prompt_cache(prompt_id)

        logger.info(f"Updated prompt {prompt_id}: {change_message}")
        return updated_prompt

    async def delete_prompt(self, prompt_id: str) -> None:
        """Soft delete a prompt.

        Args:
            prompt_id: ID of the prompt to delete

        Raises:
            PromptNotFoundError: If prompt does not exist

        Example:
            >>> await manager.delete_prompt("prompt_abc123")
        """
        # Verify prompt exists
        await self.get_prompt(prompt_id)

        # Soft delete
        deleted = await self._repository.delete(prompt_id)
        if not deleted:
            raise PromptNotFoundError(prompt_id)

        # Invalidate cache
        if self._cache_manager:
            await self._invalidate_prompt_cache(prompt_id)

        logger.info(f"Deleted prompt {prompt_id}")

    async def list_prompts(
        self, tenant_id: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> list[Prompt]:
        """List all prompts for a tenant.

        Args:
            tenant_id: Optional tenant ID (uses instance tenant_id if not provided)
            limit: Maximum number of results (default: 100)
            offset: Number of results to skip (default: 0)

        Returns:
            List of prompts sorted by created_at descending

        Example:
            >>> prompts = await manager.list_prompts(limit=10)
            >>> for prompt in prompts:
            ...     print(prompt.name)
        """
        tid = tenant_id if tenant_id else self.tenant_id
        if not tid:
            return []

        prompts = await self._repository.list_by_tenant(tenant_id=tid, limit=limit, offset=offset)
        return prompts

    # Versioning Operations

    async def get_prompt_history(
        self, prompt_id: str, limit: int = 50, offset: int = 0
    ) -> list[PromptVersion]:
        """Get version history for a prompt.

        Args:
            prompt_id: ID of the prompt
            limit: Maximum number of versions to return (default: 50)
            offset: Number of versions to skip (default: 0)

        Returns:
            List of versions sorted by version_number descending

        Example:
            >>> history = await manager.get_prompt_history("prompt_abc123", limit=10)
            >>> for version in history:
            ...     print(f"v{version.version_number}: {version.change_message}")
        """
        versions = await self._version_manager.list_versions(
            prompt_id=prompt_id, limit=limit, offset=offset
        )
        return versions

    async def rollback_prompt(self, prompt_id: str, to_version: int, rolled_back_by: str) -> Prompt:
        """Rollback a prompt to a previous version.

        Args:
            prompt_id: ID of the prompt to rollback
            to_version: Version number to rollback to
            rolled_back_by: ID of user performing the rollback

        Returns:
            Updated prompt with content from target version

        Raises:
            PromptNotFoundError: If prompt does not exist
            PromptVersionNotFoundError: If target version does not exist

        Example:
            >>> prompt = await manager.rollback_prompt(
            ...     prompt_id="prompt_abc123",
            ...     to_version=3,
            ...     rolled_back_by="user-1"
            ... )
        """
        updated_prompt = await self._version_manager.rollback(
            prompt_id=prompt_id,
            to_version=to_version,
            rolled_back_by=rolled_back_by,
        )

        # Invalidate cache
        if self._cache_manager:
            await self._invalidate_prompt_cache(prompt_id)

        logger.info(f"Rolled back prompt {prompt_id} to version {to_version}")
        return updated_prompt

    # Composition Operations

    async def compose_prompt(
        self,
        agent_id: str,
        tenant_id: Optional[str] = None,
        feature_ids: Optional[Union[str, list[str]]] = None,
        user_input: Optional[str] = None,
        variables: Optional[dict[str, Any]] = None,
        skip_cache: bool = False,
    ) -> ComposedPrompt:
        """Compose a prompt by merging all layers and rendering variables.

        This is the main entry point for prompt composition. It orchestrates
        loading prompts from all layers, merging them, and rendering the
        final template with variables.

        Args:
            agent_id: ID of the agent requesting the prompt
            tenant_id: Optional tenant ID (uses instance tenant_id if not provided)
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
            >>> result = await manager.compose_prompt(
            ...     agent_id="agent-123",
            ...     tenant_id="tenant-456",
            ...     user_input="What is AI?",
            ...     variables={"context": "general knowledge"},
            ...     feature_ids=["feature-search", "feature-analytics"]
            ... )
            >>> print(result.content)
            >>> print(f"Composition took {result.composition_time_ms}ms")
        """
        tid = tenant_id if tenant_id else self.tenant_id

        composed = await self._composition_engine.compose(
            agent_id=agent_id,
            tenant_id=tid,
            feature_ids=feature_ids,
            user_input=user_input,
            variables=variables,
            skip_cache=skip_cache,
        )

        return composed

    # Validation Operations

    def validate_template(self, content: str) -> list[str]:
        """Validate template syntax without creating a prompt.

        Args:
            content: Template content to validate

        Returns:
            List of error messages (empty if valid)

        Example:
            >>> errors = manager.validate_template("Hello {{ name }")
            >>> if errors:
            ...     print(f"Validation errors: {errors}")
        """
        return self._syntax_validator.validate(content)

    def validate_schema(self, schema: dict[str, Any]) -> list[str]:
        """Validate a variable schema.

        Args:
            schema: Variable schema dictionary to validate

        Returns:
            List of error messages (empty if valid)

        Example:
            >>> schema = {
            ...     "properties": {"name": {"type": "string"}},
            ...     "required": ["name"]
            ... }
            >>> errors = manager.validate_schema(schema)
            >>> if not errors:
            ...     print("Schema is valid")
        """
        try:
            var_schema = VariableSchema(**schema)
            return self._schema_validator.validate_schema(var_schema)
        except Exception as e:
            return [f"Invalid schema format: {str(e)}"]

    # Experiment Operations

    async def create_experiment(
        self,
        prompt_id: str,
        name: str,
        description: str,
        success_metric: str,
        variants: list[dict[str, Any]],
        created_by: Optional[str] = None,
    ) -> PromptExperiment:
        """Create a new A/B test experiment.

        Args:
            prompt_id: ID of the prompt to experiment on
            name: Human-readable experiment name
            description: Detailed description of the experiment
            success_metric: Name of the metric to optimize
            variants: List of experiment variants as dicts
            created_by: Optional ID of user creating the experiment

        Returns:
            Created experiment in DRAFT status

        Raises:
            PromptNotFoundError: If prompt does not exist
            PromptValidationError: If variants validation fails

        Example:
            >>> experiment = await manager.create_experiment(
            ...     prompt_id="prompt_abc123",
            ...     name="Test conciseness",
            ...     description="Compare concise vs detailed responses",
            ...     success_metric="user_satisfaction",
            ...     variants=[
            ...         {
            ...             "id": "var-1",
            ...             "name": "Concise",
            ...             "prompt_version_id": "prompt_abc123-v2",
            ...             "traffic_percentage": 50.0
            ...         },
            ...         {
            ...             "id": "var-2",
            ...             "name": "Detailed",
            ...             "prompt_version_id": "prompt_abc123-v3",
            ...             "traffic_percentage": 50.0
            ...         }
            ...     ],
            ...     created_by="user-1"
            ... )
        """
        # Build variant objects from dicts
        variant_objs = [ExperimentVariant(**v) for v in variants]

        experiment = await self._experiment_manager.create_experiment(
            prompt_id=prompt_id,
            name=name,
            description=description,
            success_metric=success_metric,
            variants=variant_objs,
            created_by=created_by,
        )

        logger.info(f"Created experiment {experiment.id} for prompt {prompt_id}")
        return experiment

    async def start_experiment(self, experiment_id: str) -> PromptExperiment:
        """Start a DRAFT or PAUSED experiment.

        Args:
            experiment_id: ID of the experiment to start

        Returns:
            Updated experiment with RUNNING status

        Raises:
            ExperimentNotFoundError: If experiment does not exist
            ExperimentStateError: If experiment cannot be started

        Example:
            >>> experiment = await manager.start_experiment("exp-123")
            >>> print(experiment.status)  # RUNNING
        """
        return await self._experiment_manager.start_experiment(experiment_id)

    async def pause_experiment(self, experiment_id: str) -> PromptExperiment:
        """Pause a RUNNING experiment.

        Args:
            experiment_id: ID of the experiment to pause

        Returns:
            Updated experiment with PAUSED status

        Raises:
            ExperimentNotFoundError: If experiment does not exist
            ExperimentStateError: If experiment is not RUNNING

        Example:
            >>> experiment = await manager.pause_experiment("exp-123")
            >>> print(experiment.status)  # PAUSED
        """
        return await self._experiment_manager.pause_experiment(experiment_id)

    async def complete_experiment(
        self, experiment_id: str, results: dict[str, Any]
    ) -> PromptExperiment:
        """Complete an experiment and store results.

        Args:
            experiment_id: ID of the experiment to complete
            results: Statistical results to store

        Returns:
            Updated experiment with COMPLETED status

        Raises:
            ExperimentNotFoundError: If experiment does not exist

        Example:
            >>> results = {"var-1": {"success_rate": 0.85}, "var-2": {"success_rate": 0.78}}
            >>> experiment = await manager.complete_experiment("exp-123", results)
        """
        return await self._experiment_manager.complete_experiment(experiment_id, results)

    async def cancel_experiment(self, experiment_id: str) -> PromptExperiment:
        """Cancel an experiment.

        Args:
            experiment_id: ID of the experiment to cancel

        Returns:
            Updated experiment with CANCELLED status

        Raises:
            ExperimentNotFoundError: If experiment does not exist

        Example:
            >>> experiment = await manager.cancel_experiment("exp-123")
            >>> print(experiment.status)  # CANCELLED
        """
        return await self._experiment_manager.cancel_experiment(experiment_id)

    # Cache Management (Internal)

    async def _invalidate_prompt_cache(self, prompt_id: str) -> None:
        """Invalidate all cached compositions for a prompt.

        Args:
            prompt_id: ID of the prompt whose cache should be invalidated
        """
        if not self._cache_manager:
            return

        # Invalidate all entries that might contain this prompt
        # Use a pattern that matches any cache key containing this prompt
        pattern = f"*{prompt_id}*"
        invalidated = await self._cache_manager.invalidate_pattern(pattern)
        logger.debug(f"Invalidated {invalidated} cache entries for prompt {prompt_id}")

    def get_cache_stats(self) -> dict[str, Any]:
        """Get current cache statistics.

        Returns:
            Dictionary containing cache statistics

        Example:
            >>> stats = manager.get_cache_stats()
            >>> print(f"Cache size: {stats['size']}/{stats['max_size']}")
            >>> # Calculate hit rate
            >>> hit_rate = stats['hit_count'] / (stats['hit_count'] + stats['miss_count'])
        """
        if self._cache_manager:
            return self._cache_manager.stats()
        return {"enabled": False}

    async def clear_cache(self) -> None:
        """Clear all cache entries.

        Example:
            >>> await manager.clear_cache()
        """
        if self._cache_manager:
            await self._cache_manager.clear()
            logger.info("Cache cleared")
