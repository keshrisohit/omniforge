"""Secure template renderer using Jinja2 sandboxed environment.

This module provides a secure Jinja2-based template renderer with custom filters
for prompt-specific operations. All rendering happens in a sandboxed environment
to prevent code execution attacks.
"""

from typing import Any, Callable, Dict, Optional, Tuple, Union

from jinja2 import BaseLoader, Environment
from jinja2.sandbox import SandboxedEnvironment

from omniforge.prompts.errors import PromptRenderError


class PromptTemplateLoader(BaseLoader):
    """Minimal Jinja2 loader that returns templates from strings.

    This loader does not access the filesystem and only works with
    string-based templates for security.
    """

    def get_source(
        self, environment: Environment, template: str
    ) -> Tuple[str, Optional[str], Optional[Callable[[], bool]]]:
        """Get template source from string.

        Args:
            environment: Jinja2 environment instance
            template: Template content as string

        Returns:
            Tuple of (source, filename, uptodate_func):
                - source: Template content
                - filename: None (no file)
                - uptodate_func: None (always current)

        Raises:
            TemplateNotFound: Never raised, exists for interface compliance
        """
        return template, None, None


class TemplateRenderer:
    """Secure Jinja2 template renderer with custom filters.

    This renderer uses Jinja2's SandboxedEnvironment to prevent code execution
    and provides custom filters for common prompt operations.

    Custom Filters:
        - default: Return default value if variable is empty/undefined
        - truncate: Truncate string to specified length with suffix
        - capitalize_first: Capitalize only the first character
        - bullet_list: Format list items as bullet points

    Example:
        >>> renderer = TemplateRenderer()
        >>> template = "Hello {{ name | default('World') }}!"
        >>> result = await renderer.render(template, {"name": "Alice"})
        >>> print(result)
        'Hello Alice!'
    """

    def __init__(self) -> None:
        """Initialize template renderer with sandboxed environment."""
        from jinja2 import StrictUndefined

        self._env = SandboxedEnvironment(
            loader=PromptTemplateLoader(),
            autoescape=False,  # Prompts don't need HTML escaping
            trim_blocks=True,  # Remove first newline after block
            lstrip_blocks=True,  # Strip leading spaces before blocks
            undefined=StrictUndefined,  # Raise errors for undefined variables
        )

        # Register custom filters
        self._env.filters["default"] = self._filter_default
        self._env.filters["truncate"] = self._filter_truncate
        self._env.filters["capitalize_first"] = self._filter_capitalize_first
        self._env.filters["bullet_list"] = self._filter_bullet_list

    def _filter_default(
        self, value: Any, default_value: Any = "", empty_strings: bool = True
    ) -> Any:
        """Return default value if variable is empty or undefined.

        Args:
            value: Variable value to check
            default_value: Value to return if empty (default: "")
            empty_strings: Treat empty strings as empty (default: True)

        Returns:
            Original value or default if empty
        """
        if value is None:
            return default_value
        if empty_strings and isinstance(value, str) and not value.strip():
            return default_value
        return value

    def _filter_truncate(self, value: str, length: int = 100, suffix: str = "...") -> str:
        """Truncate string to specified length with suffix.

        Args:
            value: String to truncate
            length: Maximum length (default: 100)
            suffix: Suffix to append if truncated (default: "...")

        Returns:
            Truncated string with suffix if longer than length
        """
        if not isinstance(value, str):
            value = str(value)

        if len(value) <= length:
            return value

        # Account for suffix length
        max_content_length = max(0, length - len(suffix))
        return value[:max_content_length] + suffix

    def _filter_capitalize_first(self, value: str) -> str:
        """Capitalize only the first character of the string.

        Args:
            value: String to capitalize

        Returns:
            String with first character capitalized
        """
        if not isinstance(value, str) or not value:
            return str(value)

        return value[0].upper() + value[1:]

    def _filter_bullet_list(
        self, items: Union[list, tuple], bullet: str = "•", indent: str = "  "
    ) -> str:
        """Format list items as bullet points.

        Args:
            items: List or tuple of items to format
            bullet: Bullet character (default: "•")
            indent: Indentation before bullet (default: "  ")

        Returns:
            Formatted string with bullet points
        """
        if not isinstance(items, (list, tuple)):
            return str(items)

        if not items:
            return ""

        lines = [f"{indent}{bullet} {item}" for item in items]
        return "\n".join(lines)

    async def render(self, template: str, variables: Optional[Dict[str, Any]] = None) -> str:
        """Render template with provided variables.

        Args:
            template: Jinja2 template string
            variables: Dictionary of variables for substitution (default: {})

        Returns:
            Rendered template string

        Raises:
            PromptRenderError: If template rendering fails
        """
        if variables is None:
            variables = {}

        try:
            # Parse and compile template
            compiled_template = self._env.from_string(template)

            # Render with variables
            result = compiled_template.render(**variables)

            return result

        except Exception as e:
            # Convert Jinja2 exceptions to PromptRenderError
            error_message = str(e)
            variable_name = None

            # Try to extract variable name from error message
            if "is undefined" in error_message:
                # Extract variable name from "UndefinedError: 'var_name' is undefined"
                parts = error_message.split("'")
                if len(parts) >= 2:
                    variable_name = parts[1]

            raise PromptRenderError(
                message=error_message,
                variable=variable_name,
                details={"template": template, "variables": list(variables.keys())},
            ) from e

    def validate_syntax(self, template: str) -> list[str]:
        """Validate template syntax without rendering.

        Args:
            template: Jinja2 template string to validate

        Returns:
            List of syntax error messages (empty if valid)
        """
        errors = []

        try:
            # Try to parse template
            self._env.from_string(template)
        except Exception as e:
            # Capture syntax errors
            error_message = str(e)
            errors.append(error_message)

        return errors
