"""Prompt template registry for centralized template management.

This module provides a thread-safe registry for storing and retrieving prompt templates.
It serves as a lightweight layer for template management, with optional integration
with the full PromptManager for versioning and A/B testing.
"""

import threading
from typing import Any, Optional

from omniforge.prompts.errors import PromptNotFoundError, PromptRenderError


class PromptTemplateRegistry:
    """Thread-safe registry for prompt templates.

    This registry provides a centralized store for named prompt templates with
    basic CRUD operations and rendering capabilities. Templates can be registered
    with variable schemas for validation.

    Example:
        >>> registry = PromptTemplateRegistry()
        >>> registry.register(
        ...     name="greeting",
        ...     content="Hello, {name}!",
        ...     variables_schema={"name": str}
        ... )
        >>> rendered = registry.render("greeting", name="Alice")
        >>> print(rendered)
        Hello, Alice!
    """

    def __init__(self) -> None:
        """Initialize empty prompt template registry."""
        self._templates: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()

    def register(
        self,
        name: str,
        content: str,
        variables_schema: Optional[dict[str, type]] = None,
    ) -> None:
        """Register a new prompt template.

        Args:
            name: Unique template name
            content: Template content with optional {variable} placeholders
            variables_schema: Optional schema defining expected variables and types

        Raises:
            ValueError: If template name is empty

        Example:
            >>> registry.register(
            ...     name="skill_wrapper",
            ...     content="Skill: {skill_name}\\n{instructions}",
            ...     variables_schema={"skill_name": str, "instructions": str}
            ... )
        """
        if not name or not name.strip():
            raise ValueError("Template name cannot be empty")

        with self._lock:
            self._templates[name] = {
                "content": content,
                "variables_schema": variables_schema or {},
            }

    def get(self, name: str) -> str:
        """Get template content by name.

        Args:
            name: Template name

        Returns:
            Template content string

        Raises:
            PromptNotFoundError: If template not found

        Example:
            >>> content = registry.get("greeting")
            >>> print(content)
            Hello, {name}!
        """
        with self._lock:
            if name not in self._templates:
                raise PromptNotFoundError(f"Template '{name}' not found")
            return self._templates[name]["content"]

    def render(self, template_name: str, **variables: Any) -> str:
        """Render template with variables.

        Args:
            template_name: Template name
            **variables: Variables to substitute in template

        Returns:
            Rendered template string

        Raises:
            PromptNotFoundError: If template not found
            PromptRenderError: If rendering fails (missing variables, invalid format)

        Example:
            >>> rendered = registry.render("greeting", name="Bob")
            >>> print(rendered)
            Hello, Bob!
        """
        content = self.get(template_name)

        try:
            return content.format(**variables)
        except KeyError as e:
            raise PromptRenderError(
                f"Missing required variable for template '{template_name}': {e}"
            ) from e
        except Exception as e:
            raise PromptRenderError(
                f"Failed to render template '{template_name}': {e}"
            ) from e

    def list_templates(self) -> list[str]:
        """List all registered template names.

        Returns:
            Sorted list of template names

        Example:
            >>> templates = registry.list_templates()
            >>> print(templates)
            ['greeting', 'skill_wrapper', 'react_base']
        """
        with self._lock:
            return sorted(self._templates.keys())

    def exists(self, name: str) -> bool:
        """Check if template exists.

        Args:
            name: Template name

        Returns:
            True if template exists, False otherwise

        Example:
            >>> if registry.exists("greeting"):
            ...     print("Template found!")
        """
        with self._lock:
            return name in self._templates

    def remove(self, name: str) -> None:
        """Remove template from registry.

        Args:
            name: Template name

        Raises:
            PromptNotFoundError: If template not found

        Example:
            >>> registry.remove("greeting")
        """
        with self._lock:
            if name not in self._templates:
                raise PromptNotFoundError(f"Template '{name}' not found")
            del self._templates[name]

    def clear(self) -> None:
        """Remove all templates from registry.

        Example:
            >>> registry.clear()
            >>> len(registry.list_templates())
            0
        """
        with self._lock:
            self._templates.clear()
