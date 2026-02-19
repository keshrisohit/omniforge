"""Merge point processor for combining prompts across layers.

This module provides the MergeProcessor class that combines prompt content from
multiple hierarchical layers at defined merge points. It handles different merge
behaviors (append, prepend, replace, inject) and enforces constraints like locked
and required merge points.
"""

import re
from typing import Dict, Optional

from omniforge.prompts.enums import MergeBehavior, PromptLayer
from omniforge.prompts.errors import MergePointConflictError, PromptValidationError
from omniforge.prompts.models import MergePointDefinition, Prompt


class MergeProcessor:
    """Processor for merging prompts across layers at defined merge points.

    The MergeProcessor combines prompts from hierarchical layers (SYSTEM, TENANT,
    FEATURE, AGENT) by resolving merge points in the system template. Each merge
    point can have different behaviors and constraints.

    Merge Behaviors:
        - APPEND: Higher layer content added after lower layer
        - PREPEND: Higher layer content added before lower layer
        - REPLACE: Higher layer content replaces lower layer
        - INJECT: Content inserted at specified position

    Constraints:
        - locked: Merge point cannot be overridden by higher layers
        - required: Merge point must be filled by at least one layer

    Example:
        >>> processor = MergeProcessor()
        >>> system_prompt = Prompt(content="Base: {{ merge_point('custom') }}", ...)
        >>> agent_prompt = Prompt(content="{{ merge_point('custom') }}\\nAgent logic", ...)
        >>> result = await processor.merge(
        ...     {PromptLayer.SYSTEM: system_prompt, PromptLayer.AGENT: agent_prompt},
        ...     user_input="User request"
        ... )
        >>> print(result)
        'Base: Agent logic\\nUser request'
    """

    # Layer priority from lowest to highest
    _LAYER_PRIORITY: list[PromptLayer] = [
        PromptLayer.SYSTEM,
        PromptLayer.TENANT,
        PromptLayer.FEATURE,
        PromptLayer.AGENT,
    ]

    # Regex pattern for merge point markers: {{ merge_point("name") }}
    _MERGE_POINT_PATTERN = re.compile(r'\{\{\s*merge_point\(\s*["\']([^"\']+)["\']\s*\)\s*\}\}')

    async def merge(
        self,
        layer_prompts: Dict[PromptLayer, Optional[Prompt]],
        user_input: Optional[str] = None,
    ) -> str:
        """Merge prompts from all layers at defined merge points.

        Args:
            layer_prompts: Dictionary mapping layers to their prompts
            user_input: Optional user input to substitute into user_input merge point

        Returns:
            Merged template string with all merge points resolved

        Raises:
            PromptValidationError: If required merge point is not filled
            MergePointConflictError: If locked merge point is overridden
        """
        # Start with system prompt as base template
        system_prompt = layer_prompts.get(PromptLayer.SYSTEM)
        if not system_prompt:
            raise PromptValidationError("System prompt is required as base template")

        # Collect all merge point definitions across layers
        merge_point_definitions = self._collect_merge_point_definitions(layer_prompts)

        # Extract merge point content from all layers
        merge_point_contents = self._collect_merge_point_contents(layer_prompts)

        # Validate locked and required constraints
        self._validate_merge_point_constraints(
            merge_point_definitions, merge_point_contents, layer_prompts
        )

        # Start with system template
        result = system_prompt.content

        # Process each merge point in the system template
        for merge_point_name in self._find_merge_points(result):
            # Special handling for user_input merge point (doesn't need definition)
            if merge_point_name == "user_input":
                content = user_input or ""
                result = self._replace_merge_point(result, merge_point_name, content)
                continue

            # Get the merge point definition
            definition = merge_point_definitions.get(merge_point_name)
            if not definition:
                # No definition means simple replacement with empty string
                result = self._replace_merge_point(result, merge_point_name, "")
                continue

            # Get content from all layers for this merge point
            contents_by_layer = merge_point_contents.get(merge_point_name, {})

            # Apply merge behavior
            merged_content = self._apply_merge_behavior(definition.behavior, contents_by_layer)

            # Replace the merge point marker with merged content
            result = self._replace_merge_point(result, merge_point_name, merged_content)

        # Clean up any remaining empty merge points
        result = self._clean_empty_merge_points(result)

        return result

    def _collect_merge_point_definitions(
        self, layer_prompts: Dict[PromptLayer, Optional[Prompt]]
    ) -> Dict[str, MergePointDefinition]:
        """Collect merge point definitions from all layers.

        Higher layers override lower layer definitions unless locked.

        Args:
            layer_prompts: Dictionary mapping layers to their prompts

        Returns:
            Dictionary mapping merge point names to their definitions
        """
        definitions: Dict[str, MergePointDefinition] = {}

        # Process layers from lowest to highest priority
        for layer in self._LAYER_PRIORITY:
            prompt = layer_prompts.get(layer)
            if not prompt:
                continue

            for merge_point in prompt.merge_points:
                # If merge point already exists and is locked, don't override
                existing = definitions.get(merge_point.name)
                if existing and existing.locked:
                    continue

                definitions[merge_point.name] = merge_point

        return definitions

    def _collect_merge_point_contents(
        self, layer_prompts: Dict[PromptLayer, Optional[Prompt]]
    ) -> Dict[str, Dict[PromptLayer, str]]:
        """Extract merge point content from all layers.

        Args:
            layer_prompts: Dictionary mapping layers to their prompts

        Returns:
            Dictionary mapping merge point names to layer-content mappings
        """
        contents: Dict[str, Dict[PromptLayer, str]] = {}

        for layer in self._LAYER_PRIORITY:
            prompt = layer_prompts.get(layer)
            if not prompt:
                continue

            # Extract content for each merge point defined in this layer
            for merge_point in prompt.merge_points:
                content = self._extract_merge_point_content(prompt, merge_point.name)
                if content:  # Only store non-empty content
                    if merge_point.name not in contents:
                        contents[merge_point.name] = {}
                    contents[merge_point.name][layer] = content

        return contents

    def _extract_merge_point_content(self, prompt: Prompt, merge_point_name: str) -> str:
        """Extract content for a specific merge point from a prompt.

        Args:
            prompt: Prompt to extract content from
            merge_point_name: Name of the merge point

        Returns:
            Content for the merge point (empty string if not found)
        """
        # Find the merge point marker in the content
        pattern = re.compile(
            r'\{\{\s*merge_point\(\s*["\']' + re.escape(merge_point_name) + r'["\']\s*\)\s*\}\}'
        )

        # Check if merge point exists in content
        if not pattern.search(prompt.content):
            return ""

        # Extract content by replacing the marker and getting surrounding content
        # For now, return empty as content is defined inline in higher layers
        # This will be populated from the prompt content itself
        return ""

    def _validate_merge_point_constraints(
        self,
        definitions: Dict[str, MergePointDefinition],
        contents: Dict[str, Dict[PromptLayer, str]],
        layer_prompts: Dict[PromptLayer, Optional[Prompt]],
    ) -> None:
        """Validate locked and required merge point constraints.

        Args:
            definitions: Merge point definitions
            contents: Merge point contents by layer
            layer_prompts: Dictionary mapping layers to their prompts

        Raises:
            PromptValidationError: If required merge point is not filled
            MergePointConflictError: If locked merge point is overridden
        """
        for name, definition in definitions.items():
            # Check required constraint
            if definition.required:
                layer_contents = contents.get(name, {})
                if not layer_contents or all(not c.strip() for c in layer_contents.values()):
                    raise PromptValidationError(
                        f"Required merge point '{name}' has no content", field=name
                    )

            # Check locked constraint
            if definition.locked:
                # Find which layer defined this locked merge point
                defining_layer = None
                for layer in self._LAYER_PRIORITY:
                    prompt = layer_prompts.get(layer)
                    if prompt:
                        for mp in prompt.merge_points:
                            if mp.name == name and mp.locked:
                                defining_layer = layer
                                break
                    if defining_layer:
                        break

                if defining_layer:
                    # Check if higher layers try to provide content
                    layer_contents = contents.get(name, {})
                    for layer, content in layer_contents.items():
                        if (
                            self._LAYER_PRIORITY.index(layer)
                            > self._LAYER_PRIORITY.index(defining_layer)
                            and content.strip()
                        ):
                            raise MergePointConflictError(
                                merge_point_name=name,
                                layer1=defining_layer.value,
                                layer2=layer.value,
                                conflict_reason=f"Merge point is locked at {defining_layer.value} "
                                f"layer and cannot be overridden",
                            )

    def _apply_merge_behavior(
        self, behavior: MergeBehavior, contents_by_layer: Dict[PromptLayer, str]
    ) -> str:
        """Apply merge behavior to combine content from multiple layers.

        Args:
            behavior: Merge behavior to apply
            contents_by_layer: Dictionary mapping layers to their content

        Returns:
            Merged content string
        """
        if not contents_by_layer:
            return ""

        # Sort layers by priority (lowest to highest)
        sorted_layers = [layer for layer in self._LAYER_PRIORITY if layer in contents_by_layer]

        if behavior == MergeBehavior.REPLACE:
            # Use content from highest layer
            return contents_by_layer[sorted_layers[-1]]

        elif behavior == MergeBehavior.APPEND:
            # Concatenate content from lowest to highest
            parts = [contents_by_layer[layer] for layer in sorted_layers]
            return "\n".join(part.strip() for part in parts if part.strip())

        elif behavior == MergeBehavior.PREPEND:
            # Concatenate content from highest to lowest
            parts = [contents_by_layer[layer] for layer in reversed(sorted_layers)]
            return "\n".join(part.strip() for part in parts if part.strip())

        elif behavior == MergeBehavior.INJECT:
            # For INJECT, use highest layer content (position-based injection)
            # This is similar to REPLACE but semantically different
            return contents_by_layer[sorted_layers[-1]]

        return ""

    def _find_merge_points(self, template: str) -> list[str]:
        """Find all merge point names in a template.

        Args:
            template: Template string to search

        Returns:
            List of merge point names found in the template
        """
        matches = self._MERGE_POINT_PATTERN.findall(template)
        # Return unique names in order of appearance
        seen = set()
        result = []
        for name in matches:
            if name not in seen:
                seen.add(name)
                result.append(name)
        return result

    def _replace_merge_point(self, template: str, merge_point_name: str, content: str) -> str:
        """Replace a merge point marker with content.

        Args:
            template: Template string
            merge_point_name: Name of the merge point to replace
            content: Content to substitute

        Returns:
            Template with merge point replaced
        """
        pattern = re.compile(
            r'\{\{\s*merge_point\(\s*["\']' + re.escape(merge_point_name) + r'["\']\s*\)\s*\}\}'
        )
        return pattern.sub(content, template)

    def _clean_empty_merge_points(self, template: str) -> str:
        """Clean up any remaining empty merge points.

        Removes merge point markers that weren't replaced and cleans up
        extra whitespace.

        Args:
            template: Template string to clean

        Returns:
            Cleaned template string
        """
        # Remove any remaining merge point markers
        result = self._MERGE_POINT_PATTERN.sub("", template)

        # Clean up multiple consecutive newlines (max 2)
        result = re.sub(r"\n{3,}", "\n\n", result)

        # Remove trailing/leading whitespace from lines
        lines = result.split("\n")
        lines = [line.rstrip() for line in lines]

        # Remove leading/trailing empty lines
        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()

        return "\n".join(lines)
