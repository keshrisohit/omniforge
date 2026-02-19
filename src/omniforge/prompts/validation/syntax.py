"""Jinja2 template syntax validation.

This module provides utilities for validating Jinja2 template syntax
without rendering the templates.
"""

from jinja2 import TemplateSyntaxError
from jinja2.sandbox import SandboxedEnvironment

from omniforge.prompts.composition.renderer import PromptTemplateLoader


class SyntaxValidator:
    """Validator for Jinja2 template syntax.

    This validator parses templates without rendering them to detect
    syntax errors and provides descriptive error messages with line numbers.

    Example:
        >>> validator = SyntaxValidator()
        >>> errors = validator.validate("Hello {{ name }")
        >>> print(errors)
        ['unexpected end of template, expected }']
    """

    def __init__(self) -> None:
        """Initialize syntax validator with sandboxed environment."""
        self._env = SandboxedEnvironment(
            loader=PromptTemplateLoader(),
            autoescape=False,
        )

    def validate(self, content: str) -> list[str]:
        """Validate Jinja2 template syntax.

        Args:
            content: Template content to validate

        Returns:
            List of error messages with line numbers (empty if valid)

        Example:
            >>> validator = SyntaxValidator()
            >>> errors = validator.validate("{% if test %}no endif")
            >>> len(errors) > 0
            True
        """
        errors = []

        try:
            # Try to parse the template
            self._env.from_string(content)
        except TemplateSyntaxError as e:
            # Format error with line number if available
            if e.lineno is not None:
                error_msg = f"Line {e.lineno}: {e.message}"
            else:
                error_msg = e.message
            errors.append(error_msg)
        except Exception as e:
            # Catch any other parsing errors
            errors.append(f"Syntax error: {str(e)}")

        return errors
