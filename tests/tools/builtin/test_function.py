"""Tests for internal function invocation tool."""

import asyncio

import pytest

from omniforge.tools.base import ParameterType, ToolCallContext, ToolParameter
from omniforge.tools.builtin.function import FunctionRegistry, FunctionTool, function


# Test functions
def add_numbers(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


def format_text(text: str, style: str = "lower") -> str:
    """Format text in different styles."""
    if style == "upper":
        return text.upper()
    elif style == "lower":
        return text.lower()
    elif style == "title":
        return text.title()
    return text


async def async_multiply(x: int, y: int) -> int:
    """Async multiply function."""
    await asyncio.sleep(0.01)  # Simulate async work
    return x * y


async def slow_task() -> str:
    """Slow async task for timeout testing."""
    await asyncio.sleep(10)
    return "done"


def failing_function():
    """Function that raises an exception."""
    raise ValueError("This function always fails")


@pytest.fixture
def function_registry():
    """Create function registry."""
    return FunctionRegistry()


@pytest.fixture
def tool_context() -> ToolCallContext:
    """Create test tool call context."""
    return ToolCallContext(
        correlation_id="corr-123",
        task_id="task-123",
        agent_id="agent-456",
    )


def test_function_registry_initialization():
    """Test FunctionRegistry initializes correctly."""
    registry = FunctionRegistry()
    assert len(registry.list_functions()) == 0


def test_function_registry_register(function_registry):
    """Test registering a function."""
    function_registry.register(
        name="add",
        func=add_numbers,
        description="Add two numbers",
        parameters=[
            ToolParameter(
                name="a",
                type=ParameterType.INTEGER,
                description="First number",
                required=True,
            ),
            ToolParameter(
                name="b",
                type=ParameterType.INTEGER,
                description="Second number",
                required=True,
            ),
        ],
    )

    function_def = function_registry.get("add")
    assert function_def.name == "add"
    assert function_def.func is add_numbers
    assert function_def.description == "Add two numbers"
    assert len(function_def.parameters) == 2
    assert function_def.is_async is False


def test_function_registry_register_async(function_registry):
    """Test registering an async function."""
    function_registry.register(
        name="multiply",
        func=async_multiply,
        description="Multiply two numbers asynchronously",
    )

    function_def = function_registry.get("multiply")
    assert function_def.name == "multiply"
    assert function_def.is_async is True


def test_function_registry_register_duplicate_error(function_registry):
    """Test registering duplicate function raises error."""
    function_registry.register(
        name="add",
        func=add_numbers,
        description="Add two numbers",
    )

    with pytest.raises(ValueError, match="already registered"):
        function_registry.register(
            name="add",
            func=add_numbers,
            description="Another add",
        )


def test_function_registry_get_not_found(function_registry):
    """Test getting non-existent function raises error."""
    with pytest.raises(KeyError, match="not found"):
        function_registry.get("nonexistent")


def test_function_registry_list_functions(function_registry):
    """Test listing functions."""
    function_registry.register("add", add_numbers, "Add numbers")
    function_registry.register("format", format_text, "Format text")

    functions = function_registry.list_functions()
    assert len(functions) == 2
    function_names = [f.name for f in functions]
    assert "add" in function_names
    assert "format" in function_names


def test_function_registry_auto_extract_parameters(function_registry):
    """Test automatic parameter extraction from function signature."""
    function_registry.register(
        name="add",
        func=add_numbers,
        description="Add two numbers",
        # Don't provide parameters, let it extract
    )

    function_def = function_registry.get("add")
    assert len(function_def.parameters) == 2

    # Check parameter names
    param_names = [p.name for p in function_def.parameters]
    assert "a" in param_names
    assert "b" in param_names

    # Check types were inferred
    a_param = next(p for p in function_def.parameters if p.name == "a")
    assert a_param.type == ParameterType.INTEGER


def test_function_registry_extract_optional_parameters(function_registry):
    """Test extraction recognizes optional parameters."""
    function_registry.register(
        name="format",
        func=format_text,
        description="Format text",
    )

    function_def = function_registry.get("format")
    text_param = next(p for p in function_def.parameters if p.name == "text")
    style_param = next(p for p in function_def.parameters if p.name == "style")

    assert text_param.required is True  # No default
    assert style_param.required is False  # Has default value


def test_function_decorator_basic(function_registry):
    """Test @function decorator for registration."""

    @function("greet", "Greet a person", registry=function_registry)
    def greet_person(name: str) -> str:
        return f"Hello, {name}!"

    function_def = function_registry.get("greet")
    assert function_def.name == "greet"
    assert function_def.description == "Greet a person"
    assert function_def.func("Alice") == "Hello, Alice!"


def test_function_decorator_adds_metadata():
    """Test @function decorator adds metadata to function."""

    @function("test", "Test function")
    def test_func():
        pass

    assert test_func._function_name == "test"
    assert test_func._function_description == "Test function"


def test_function_tool_initialization(function_registry):
    """Test FunctionTool initializes correctly."""
    tool = FunctionTool(function_registry, timeout_ms=5000)

    assert tool._function_registry is function_registry
    assert tool._timeout_ms == 5000


def test_function_tool_definition(function_registry):
    """Test FunctionTool definition."""
    tool = FunctionTool(function_registry)
    definition = tool.definition

    assert definition.name == "function"
    assert definition.type.value == "function"

    param_names = [p.name for p in definition.parameters]
    assert "function_name" in param_names
    assert "arguments" in param_names

    assert definition.timeout_ms == 30000


@pytest.mark.asyncio
async def test_function_tool_execute_sync_function(function_registry, tool_context):
    """Test executing a synchronous function."""
    function_registry.register("add", add_numbers, "Add two numbers")

    tool = FunctionTool(function_registry)

    result = await tool.execute(
        arguments={
            "function_name": "add",
            "arguments": {"a": 5, "b": 3},
        },
        context=tool_context,
    )

    assert result.success is True
    assert result.result["output"] == 8
    assert result.duration_ms >= 0


@pytest.mark.asyncio
async def test_function_tool_execute_async_function(function_registry, tool_context):
    """Test executing an asynchronous function."""
    function_registry.register("multiply", async_multiply, "Multiply two numbers")

    tool = FunctionTool(function_registry)

    result = await tool.execute(
        arguments={
            "function_name": "multiply",
            "arguments": {"x": 4, "y": 7},
        },
        context=tool_context,
    )

    assert result.success is True
    assert result.result["output"] == 28
    assert result.duration_ms >= 0


@pytest.mark.asyncio
async def test_function_tool_missing_function_name(function_registry, tool_context):
    """Test error when function_name is missing."""
    tool = FunctionTool(function_registry)

    result = await tool.execute(
        arguments={"arguments": {"a": 1, "b": 2}},
        context=tool_context,
    )

    assert result.success is False
    assert "required" in result.error.lower()


@pytest.mark.asyncio
async def test_function_tool_function_not_found(function_registry, tool_context):
    """Test error when function not found."""
    tool = FunctionTool(function_registry)

    result = await tool.execute(
        arguments={
            "function_name": "nonexistent",
            "arguments": {},
        },
        context=tool_context,
    )

    assert result.success is False
    assert "not found" in result.error.lower()


@pytest.mark.asyncio
async def test_function_tool_invalid_arguments_type(function_registry, tool_context):
    """Test error when arguments is not a dict."""
    function_registry.register("add", add_numbers, "Add numbers")

    tool = FunctionTool(function_registry)

    result = await tool.execute(
        arguments={
            "function_name": "add",
            "arguments": "not a dict",  # Invalid type
        },
        context=tool_context,
    )

    assert result.success is False
    assert "dictionary" in result.error.lower()


@pytest.mark.asyncio
async def test_function_tool_missing_required_arguments(function_registry, tool_context):
    """Test error when required arguments are missing."""
    function_registry.register("add", add_numbers, "Add numbers")

    tool = FunctionTool(function_registry)

    result = await tool.execute(
        arguments={
            "function_name": "add",
            "arguments": {"a": 5},  # Missing 'b'
        },
        context=tool_context,
    )

    assert result.success is False
    assert "invalid arguments" in result.error.lower()


@pytest.mark.asyncio
async def test_function_tool_timeout(function_registry, tool_context):
    """Test timeout for long-running functions."""
    function_registry.register("slow", slow_task, "Slow task")

    tool = FunctionTool(function_registry, timeout_ms=100)  # 100ms timeout

    result = await tool.execute(
        arguments={
            "function_name": "slow",
            "arguments": {},
        },
        context=tool_context,
    )

    assert result.success is False
    assert "timed out" in result.error.lower()


@pytest.mark.asyncio
async def test_function_tool_function_exception(function_registry, tool_context):
    """Test handling of function exceptions."""
    function_registry.register("fail", failing_function, "Failing function")

    tool = FunctionTool(function_registry)

    result = await tool.execute(
        arguments={
            "function_name": "fail",
            "arguments": {},
        },
        context=tool_context,
    )

    assert result.success is False
    assert "failed" in result.error.lower()


@pytest.mark.asyncio
async def test_function_tool_optional_arguments(function_registry, tool_context):
    """Test function with optional arguments."""
    function_registry.register("format", format_text, "Format text")

    tool = FunctionTool(function_registry)

    # Without optional argument
    result = await tool.execute(
        arguments={
            "function_name": "format",
            "arguments": {"text": "HELLO"},
        },
        context=tool_context,
    )

    assert result.success is True
    assert result.result["output"] == "hello"  # Default style is 'lower'

    # With optional argument
    result = await tool.execute(
        arguments={
            "function_name": "format",
            "arguments": {"text": "hello", "style": "upper"},
        },
        context=tool_context,
    )

    assert result.success is True
    assert result.result["output"] == "HELLO"


@pytest.mark.asyncio
async def test_function_tool_no_arguments(function_registry, tool_context):
    """Test function that requires no arguments."""

    def get_constant() -> int:
        return 42

    function_registry.register("constant", get_constant, "Get constant")

    tool = FunctionTool(function_registry)

    result = await tool.execute(
        arguments={"function_name": "constant"},
        context=tool_context,
    )

    assert result.success is True
    assert result.result["output"] == 42


@pytest.mark.asyncio
async def test_function_tool_complex_return_type(function_registry, tool_context):
    """Test function that returns complex types."""

    def get_data() -> dict:
        return {"name": "Alice", "age": 30, "scores": [95, 87, 92]}

    function_registry.register("data", get_data, "Get data")

    tool = FunctionTool(function_registry)

    result = await tool.execute(
        arguments={"function_name": "data"},
        context=tool_context,
    )

    assert result.success is True
    assert result.result["name"] == "Alice"
    assert result.result["age"] == 30
    assert len(result.result["scores"]) == 3
