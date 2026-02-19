"""DEPRECATED: Internal skill invocation tool (use function.py instead).

This module provides backward compatibility for the old SkillTool API.
All functionality has been moved to function.py with renamed classes.

DEPRECATED:
- SkillDefinition → Use FunctionDefinition instead
- SkillRegistry → Use FunctionRegistry instead
- SkillTool → Use FunctionTool instead
- @skill decorator → Use @function decorator instead
"""

import warnings
from typing import Any, Callable, Optional

from omniforge.tools.base import (
    ParameterType,
    ToolCallContext,
    ToolDefinition,
    ToolParameter,
    ToolResult,
)
from omniforge.tools.builtin.function import (
    FunctionDefinition,
    FunctionRegistry,
    FunctionTool,
    function,
)
from omniforge.tools.types import ToolType

# Issue deprecation warning at module import time
warnings.warn(
    "The 'skill' module is deprecated. Use 'function' module instead:\n"
    "  - SkillDefinition → FunctionDefinition\n"
    "  - SkillRegistry → FunctionRegistry\n"
    "  - SkillTool → FunctionTool\n"
    "  - @skill → @function",
    DeprecationWarning,
    stacklevel=2,
)


class SkillDefinition(FunctionDefinition):
    """DEPRECATED: Use FunctionDefinition instead.

    This is a backward compatibility wrapper around FunctionDefinition.
    """

    def __init__(
        self,
        name: str,
        func: Callable,
        description: str,
        parameters: Optional[list[ToolParameter]] = None,
    ):
        """Initialize skill definition.

        Args:
            name: Unique skill name
            func: The skill function
            description: Skill description
            parameters: Optional list of parameter definitions
        """
        warnings.warn(
            "SkillDefinition is deprecated, use FunctionDefinition instead",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(name, func, description, parameters)


class SkillRegistry(FunctionRegistry):
    """DEPRECATED: Use FunctionRegistry instead.

    This is a backward compatibility wrapper around FunctionRegistry.
    """

    def __init__(self) -> None:
        """Initialize skill registry."""
        warnings.warn(
            "SkillRegistry is deprecated, use FunctionRegistry instead",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__()

    def list_skills(self) -> list:
        """DEPRECATED: List all registered skills (backward compatibility).

        Returns:
            List of all skill definitions
        """
        return self.list_functions()


class SkillTool(FunctionTool):
    """DEPRECATED: Use FunctionTool instead.

    This is a backward compatibility wrapper around FunctionTool.
    Note: This tool still uses the name "skill" in its definition for
    backward compatibility with existing agent configurations.
    """

    def __init__(self, skill_registry: FunctionRegistry, timeout_ms: int = 30000):
        """Initialize SkillTool.

        Args:
            skill_registry: Registry containing registered skills
            timeout_ms: Timeout for skill execution in milliseconds
        """
        warnings.warn(
            "SkillTool is deprecated, use FunctionTool instead",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(skill_registry, timeout_ms)
        # Store reference with old name for backward compatibility
        self._skill_registry = skill_registry

    @property
    def definition(self) -> ToolDefinition:
        """Get tool definition (overridden to use 'skill' name)."""
        return ToolDefinition(
            name="skill",  # Keep old name for backward compatibility
            type=ToolType.SKILL,
            description="Invoke an internal skill by name",
            parameters=[
                ToolParameter(
                    name="skill_name",
                    type=ParameterType.STRING,
                    description="Name of the skill to invoke",
                    required=True,
                ),
                ToolParameter(
                    name="arguments",
                    type=ParameterType.OBJECT,
                    description="Arguments to pass to the skill as key-value pairs",
                    required=False,
                ),
            ],
            timeout_ms=self._timeout_ms,
        )

    async def execute(self, context: ToolCallContext, arguments: dict[str, Any]) -> ToolResult:
        """Execute skill invocation.

        Args:
            context: Execution context
            arguments: Tool arguments (supports both skill_name and function_name)

        Returns:
            ToolResult with skill execution result or error
        """
        # Support both old (skill_name) and new (function_name) parameter names
        if "skill_name" in arguments and "function_name" not in arguments:
            arguments["function_name"] = arguments.pop("skill_name")

        return await super().execute(context, arguments)


def skill(
    name: str,
    description: str,
    registry: Optional[FunctionRegistry] = None,
    parameters: Optional[list[ToolParameter]] = None,
) -> Callable:
    """DEPRECATED: Use @function decorator instead.

    This is a backward compatibility wrapper around the function decorator.

    Args:
        name: Skill name
        description: Skill description
        registry: Optional registry to register to
        parameters: Optional list of parameter definitions

    Returns:
        Decorated function
    """
    warnings.warn(
        "@skill decorator is deprecated, use @function instead",
        DeprecationWarning,
        stacklevel=2,
    )

    def decorator(func: Callable) -> Callable:
        # Use the function decorator
        decorated_func = function(name, description, registry, parameters)(func)

        # Add legacy metadata for backward compatibility
        decorated_func._skill_name = name  # type: ignore
        decorated_func._skill_description = description  # type: ignore

        return decorated_func

    return decorator
