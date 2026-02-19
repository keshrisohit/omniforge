"""Internal function invocation tool for agent capabilities.

This module provides the FunctionRegistry for managing internal functions (Python functions)
and the FunctionTool for invoking them through the unified tool interface.
"""

import asyncio
import inspect
import time
from typing import Any, Callable, Optional

from omniforge.tools.base import (
    BaseTool,
    ParameterType,
    ToolCallContext,
    ToolDefinition,
    ToolParameter,
    ToolResult,
)
from omniforge.tools.types import ToolType


class FunctionDefinition:
    """Definition of a registered function.

    Attributes:
        name: Unique function name
        func: The function (sync or async)
        description: Function description
        parameters: List of parameter definitions
        is_async: Whether the function is async
    """

    def __init__(
        self,
        name: str,
        func: Callable,
        description: str,
        parameters: Optional[list[ToolParameter]] = None,
    ):
        """Initialize function definition.

        Args:
            name: Unique function name
            func: The function
            description: Function description
            parameters: Optional list of parameter definitions
        """
        self.name = name
        self.func = func
        self.description = description
        self.parameters = parameters or []
        self.is_async = asyncio.iscoroutinefunction(func)


class FunctionRegistry:
    """Registry for managing internal functions.

    Provides registration, lookup, and listing of internal functions
    that can be invoked by agents.

    Example:
        >>> registry = FunctionRegistry()
        >>> registry.register(
        ...     name="format_text",
        ...     func=lambda text, style: text.upper() if style == "upper" else text,
        ...     description="Format text in different styles",
        ...     parameters=[
        ...         ToolParameter(name="text", type=ParameterType.STRING, required=True),
        ...         ToolParameter(name="style", type=ParameterType.STRING, required=True),
        ...     ]
        ... )
        >>> function = registry.get("format_text")
        >>> result = function.func("hello", "upper")
        'HELLO'
    """

    def __init__(self) -> None:
        """Initialize function registry."""
        self._functions: dict[str, FunctionDefinition] = {}

    def register(
        self,
        name: str,
        func: Callable,
        description: str,
        parameters: Optional[list[ToolParameter]] = None,
    ) -> None:
        """Register a function.

        Args:
            name: Unique function name
            func: The function (can be sync or async)
            description: Function description
            parameters: Optional list of parameter definitions

        Raises:
            ValueError: If function name already exists
        """
        if name in self._functions:
            raise ValueError(f"Function '{name}' is already registered")

        # Auto-extract parameters from function signature if not provided
        if parameters is None:
            parameters = self._extract_parameters(func)

        function_def = FunctionDefinition(
            name=name,
            func=func,
            description=description,
            parameters=parameters,
        )

        self._functions[name] = function_def

    def get(self, name: str) -> FunctionDefinition:
        """Get a function by name.

        Args:
            name: Function name

        Returns:
            FunctionDefinition for the requested function

        Raises:
            KeyError: If function not found
        """
        if name not in self._functions:
            raise KeyError(f"Function '{name}' not found")
        return self._functions[name]

    def list_functions(self) -> list[FunctionDefinition]:
        """List all registered functions.

        Returns:
            List of all function definitions
        """
        return list(self._functions.values())

    def _extract_parameters(self, func: Callable) -> list[ToolParameter]:
        """Extract parameters from function signature.

        Args:
            func: Function to inspect

        Returns:
            List of ToolParameter extracted from signature
        """
        parameters = []
        sig = inspect.signature(func)

        for param_name, param in sig.parameters.items():
            # Skip self and cls parameters
            if param_name in ("self", "cls"):
                continue

            # Determine if required (no default value)
            required = param.default == inspect.Parameter.empty

            # Try to infer type from annotation
            param_type = ParameterType.STRING  # Default
            if param.annotation != inspect.Parameter.empty:
                if param.annotation in (int, "int"):
                    param_type = ParameterType.INTEGER
                elif param.annotation in (float, "float"):
                    param_type = ParameterType.FLOAT
                elif param.annotation in (bool, "bool"):
                    param_type = ParameterType.BOOLEAN
                elif param.annotation in (dict, "dict"):
                    param_type = ParameterType.OBJECT
                elif param.annotation in (list, "list"):
                    param_type = ParameterType.ARRAY

            parameters.append(
                ToolParameter(
                    name=param_name,
                    type=param_type,
                    description=f"Parameter: {param_name}",
                    required=required,
                )
            )

        return parameters


def function(
    name: str,
    description: str,
    registry: Optional[FunctionRegistry] = None,
    parameters: Optional[list[ToolParameter]] = None,
) -> Callable:
    """Decorator for easy function registration.

    Args:
        name: Function name
        description: Function description
        registry: Optional registry to register to (if None, returns decorated function)
        parameters: Optional list of parameter definitions

    Returns:
        Decorated function

    Example:
        >>> registry = FunctionRegistry()
        >>> @function("greet", "Greet a person", registry=registry)
        ... def greet_person(name: str) -> str:
        ...     return f"Hello, {name}!"
        >>> registry.get("greet").func("Alice")
        'Hello, Alice!'
    """

    def decorator(func: Callable) -> Callable:
        if registry is not None:
            registry.register(
                name=name,
                func=func,
                description=description,
                parameters=parameters,
            )

        # Add metadata to function
        func._function_name = name  # type: ignore
        func._function_description = description  # type: ignore

        return func

    return decorator


class FunctionTool(BaseTool):
    """Tool for invoking registered internal functions.

    Provides function execution through the unified tool interface with:
    - Function lookup by name
    - Argument validation
    - Sync and async execution support
    - Error handling

    Example:
        >>> registry = FunctionRegistry()
        >>> registry.register(
        ...     name="add",
        ...     func=lambda a, b: a + b,
        ...     description="Add two numbers",
        ... )
        >>> tool = FunctionTool(registry)
        >>> context = ToolCallContext(
        ...     correlation_id="corr-1",
        ...     task_id="task-1",
        ...     agent_id="agent-1"
        ... )
        >>> result = await tool.execute(
        ...     arguments={"function_name": "add", "arguments": {"a": 5, "b": 3}},
        ...     context=context
        ... )
        >>> result.success
        True
        >>> result.result
        8
    """

    def __init__(self, function_registry: FunctionRegistry, timeout_ms: int = 30000):
        """Initialize FunctionTool.

        Args:
            function_registry: Registry containing registered functions
            timeout_ms: Timeout for function execution in milliseconds
        """
        self._function_registry = function_registry
        self._timeout_ms = timeout_ms

    @property
    def definition(self) -> ToolDefinition:
        """Get tool definition."""
        return ToolDefinition(
            name="function",
            type=ToolType.FUNCTION,
            description="Invoke an internal Python function by name",
            parameters=[
                ToolParameter(
                    name="function_name",
                    type=ParameterType.STRING,
                    description="Name of the function to invoke",
                    required=True,
                ),
                ToolParameter(
                    name="arguments",
                    type=ParameterType.OBJECT,
                    description="Arguments to pass to the function as key-value pairs",
                    required=False,
                ),
            ],
            timeout_ms=self._timeout_ms,
        )

    async def execute(self, context: ToolCallContext, arguments: dict[str, Any]) -> ToolResult:
        """Execute function invocation.

        Args:
            context: Execution context
            arguments: Tool arguments containing function_name and arguments

        Returns:
            ToolResult with function execution result or error
        """
        start_time = time.time()

        # Extract arguments
        function_name = arguments.get("function_name", "").strip()
        function_args = arguments.get("arguments", {})

        # Validate function name
        if not function_name:
            return ToolResult(
                success=False,
                error="function_name is required",
                duration_ms=int((time.time() - start_time) * 1000),
            )

        try:
            # Look up function
            function_def = self._function_registry.get(function_name)

            # Validate arguments (basic check)
            if not isinstance(function_args, dict):
                return ToolResult(
                    success=False,
                    error="arguments must be a dictionary",
                    duration_ms=int((time.time() - start_time) * 1000),
                )

            # Execute function
            if function_def.is_async:
                # Execute async function with timeout
                timeout_seconds = self._timeout_ms / 1000
                result = await asyncio.wait_for(
                    function_def.func(**function_args),
                    timeout=timeout_seconds,
                )
            else:
                # Execute sync function in executor to avoid blocking
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None, lambda: function_def.func(**function_args)
                )

            duration_ms = int((time.time() - start_time) * 1000)

            # Wrap result in dictionary for ToolResult
            result_dict = {"output": result} if not isinstance(result, dict) else result

            return ToolResult(
                success=True,
                result=result_dict,
                duration_ms=duration_ms,
            )

        except KeyError as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return ToolResult(
                success=False,
                error=f"Function not found: {str(e)}",
                duration_ms=duration_ms,
            )

        except asyncio.TimeoutError:
            duration_ms = int((time.time() - start_time) * 1000)
            return ToolResult(
                success=False,
                error=f"Function execution timed out after {self._timeout_ms}ms",
                duration_ms=duration_ms,
            )

        except TypeError as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return ToolResult(
                success=False,
                error=f"Invalid arguments for function: {str(e)}",
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return ToolResult(
                success=False,
                error=f"Function execution failed: {str(e)}",
                duration_ms=duration_ms,
            )
