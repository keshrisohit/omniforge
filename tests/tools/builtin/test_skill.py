"""Tests for internal skill invocation tool (DEPRECATED - tests backward compatibility).

These tests ensure that the deprecated SkillTool API continues to work with
proper deprecation warnings. For new functionality, see test_function.py.
"""

import asyncio
import warnings

import pytest

from omniforge.tools.base import ParameterType, ToolCallContext, ToolParameter
from omniforge.tools.builtin.skill import (
    SkillDefinition,
    SkillRegistry,
    SkillTool,
    skill,
)


# Test skills
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


def failing_skill():
    """Skill that raises an exception."""
    raise ValueError("This skill always fails")


@pytest.fixture
def skill_registry():
    """Create skill registry."""
    return SkillRegistry()


@pytest.fixture
def tool_context() -> ToolCallContext:
    """Create test tool call context."""
    return ToolCallContext(
        correlation_id="corr-123",
        task_id="task-123",
        agent_id="agent-456",
    )


def test_skill_registry_initialization():
    """Test SkillRegistry initializes correctly."""
    registry = SkillRegistry()
    assert len(registry.list_skills()) == 0


def test_skill_registry_register(skill_registry):
    """Test registering a skill."""
    skill_registry.register(
        name="add",
        func=add_numbers,
        description="Add two numbers",
        parameters=[
            ToolParameter(name="a", type=ParameterType.INTEGER, description="First number", required=True),
            ToolParameter(name="b", type=ParameterType.INTEGER, description="Second number", required=True),
        ],
    )

    skill_def = skill_registry.get("add")
    assert skill_def.name == "add"
    assert skill_def.func is add_numbers
    assert skill_def.description == "Add two numbers"
    assert len(skill_def.parameters) == 2
    assert skill_def.is_async is False


def test_skill_registry_register_async(skill_registry):
    """Test registering an async skill."""
    skill_registry.register(
        name="multiply",
        func=async_multiply,
        description="Multiply two numbers asynchronously",
    )

    skill_def = skill_registry.get("multiply")
    assert skill_def.name == "multiply"
    assert skill_def.is_async is True


def test_skill_registry_register_duplicate_error(skill_registry):
    """Test registering duplicate skill raises error."""
    skill_registry.register(
        name="add",
        func=add_numbers,
        description="Add two numbers",
    )

    with pytest.raises(ValueError, match="already registered"):
        skill_registry.register(
            name="add",
            func=add_numbers,
            description="Another add",
        )


def test_skill_registry_get_not_found(skill_registry):
    """Test getting non-existent skill raises error."""
    with pytest.raises(KeyError, match="not found"):
        skill_registry.get("nonexistent")


def test_skill_registry_list_skills(skill_registry):
    """Test listing skills."""
    skill_registry.register("add", add_numbers, "Add numbers")
    skill_registry.register("format", format_text, "Format text")

    skills = skill_registry.list_skills()
    assert len(skills) == 2
    skill_names = [s.name for s in skills]
    assert "add" in skill_names
    assert "format" in skill_names


def test_skill_registry_auto_extract_parameters(skill_registry):
    """Test automatic parameter extraction from function signature."""
    skill_registry.register(
        name="add",
        func=add_numbers,
        description="Add two numbers",
        # Don't provide parameters, let it extract
    )

    skill_def = skill_registry.get("add")
    assert len(skill_def.parameters) == 2

    # Check parameter names
    param_names = [p.name for p in skill_def.parameters]
    assert "a" in param_names
    assert "b" in param_names

    # Check types were inferred
    a_param = next(p for p in skill_def.parameters if p.name == "a")
    assert a_param.type == ParameterType.INTEGER


def test_skill_registry_extract_optional_parameters(skill_registry):
    """Test extraction recognizes optional parameters."""
    skill_registry.register(
        name="format",
        func=format_text,
        description="Format text",
    )

    skill_def = skill_registry.get("format")
    text_param = next(p for p in skill_def.parameters if p.name == "text")
    style_param = next(p for p in skill_def.parameters if p.name == "style")

    assert text_param.required is True  # No default
    assert style_param.required is False  # Has default value


def test_skill_decorator_basic(skill_registry):
    """Test @skill decorator for registration."""

    @skill("greet", "Greet a person", registry=skill_registry)
    def greet_person(name: str) -> str:
        return f"Hello, {name}!"

    skill_def = skill_registry.get("greet")
    assert skill_def.name == "greet"
    assert skill_def.description == "Greet a person"
    assert skill_def.func("Alice") == "Hello, Alice!"


def test_skill_decorator_adds_metadata():
    """Test @skill decorator adds metadata to function."""

    @skill("test", "Test skill")
    def test_func():
        pass

    assert test_func._skill_name == "test"
    assert test_func._skill_description == "Test skill"


def test_skill_tool_initialization(skill_registry):
    """Test SkillTool initializes correctly."""
    tool = SkillTool(skill_registry, timeout_ms=5000)

    assert tool._skill_registry is skill_registry
    assert tool._timeout_ms == 5000


def test_skill_tool_definition(skill_registry):
    """Test SkillTool definition."""
    tool = SkillTool(skill_registry)
    definition = tool.definition

    assert definition.name == "skill"
    assert definition.type.value == "skill"

    param_names = [p.name for p in definition.parameters]
    assert "skill_name" in param_names
    assert "arguments" in param_names

    assert definition.timeout_ms == 30000


@pytest.mark.asyncio
async def test_skill_tool_execute_sync_skill(skill_registry, tool_context):
    """Test executing a synchronous skill."""
    skill_registry.register("add", add_numbers, "Add two numbers")

    tool = SkillTool(skill_registry)

    result = await tool.execute(
        context=tool_context,
        arguments={
            "skill_name": "add",
            "arguments": {"a": 5, "b": 3},
        },
        
    )

    assert result.success is True
    assert result.result["output"] == 8
    assert result.duration_ms >= 0


@pytest.mark.asyncio
async def test_skill_tool_execute_async_skill(skill_registry, tool_context):
    """Test executing an asynchronous skill."""
    skill_registry.register("multiply", async_multiply, "Multiply two numbers")

    tool = SkillTool(skill_registry)

    result = await tool.execute(
        context=tool_context,
        arguments={
            "skill_name": "multiply",
            "arguments": {"x": 4, "y": 7},
        },
        
    )

    assert result.success is True
    assert result.result["output"] == 28
    assert result.duration_ms >= 0


@pytest.mark.asyncio
async def test_skill_tool_missing_skill_name(skill_registry, tool_context):
    """Test error when skill_name is missing."""
    tool = SkillTool(skill_registry)

    result = await tool.execute(
        context=tool_context,
        arguments={"arguments": {"a": 1, "b": 2}},
        
    )

    assert result.success is False
    assert "required" in result.error.lower()


@pytest.mark.asyncio
async def test_skill_tool_skill_not_found(skill_registry, tool_context):
    """Test error when skill not found."""
    tool = SkillTool(skill_registry)

    result = await tool.execute(
        context=tool_context,
        arguments={
            "skill_name": "nonexistent",
            "arguments": {},
        },
        
    )

    assert result.success is False
    assert "not found" in result.error.lower()


@pytest.mark.asyncio
async def test_skill_tool_invalid_arguments_type(skill_registry, tool_context):
    """Test error when arguments is not a dict."""
    skill_registry.register("add", add_numbers, "Add numbers")

    tool = SkillTool(skill_registry)

    result = await tool.execute(
        context=tool_context,
        arguments={
            "skill_name": "add",
            "arguments": "not a dict",  # Invalid type
        },
        
    )

    assert result.success is False
    assert "dictionary" in result.error.lower()


@pytest.mark.asyncio
async def test_skill_tool_missing_required_arguments(skill_registry, tool_context):
    """Test error when required arguments are missing."""
    skill_registry.register("add", add_numbers, "Add numbers")

    tool = SkillTool(skill_registry)

    result = await tool.execute(
        context=tool_context,
        arguments={
            "skill_name": "add",
            "arguments": {"a": 5},  # Missing 'b'
        },
        
    )

    assert result.success is False
    assert "invalid arguments" in result.error.lower()


@pytest.mark.asyncio
async def test_skill_tool_timeout(skill_registry, tool_context):
    """Test timeout for long-running skills."""
    skill_registry.register("slow", slow_task, "Slow task")

    tool = SkillTool(skill_registry, timeout_ms=100)  # 100ms timeout

    result = await tool.execute(
        context=tool_context,
        arguments={
            "skill_name": "slow",
            "arguments": {},
        },
        
    )

    assert result.success is False
    assert "timed out" in result.error.lower()


@pytest.mark.asyncio
async def test_skill_tool_skill_exception(skill_registry, tool_context):
    """Test handling of skill exceptions."""
    skill_registry.register("fail", failing_skill, "Failing skill")

    tool = SkillTool(skill_registry)

    result = await tool.execute(
        context=tool_context,
        arguments={
            "skill_name": "fail",
            "arguments": {},
        },
        
    )

    assert result.success is False
    assert "failed" in result.error.lower()


@pytest.mark.asyncio
async def test_skill_tool_optional_arguments(skill_registry, tool_context):
    """Test skill with optional arguments."""
    skill_registry.register("format", format_text, "Format text")

    tool = SkillTool(skill_registry)

    # Without optional argument
    result = await tool.execute(
        context=tool_context,
        arguments={
            "skill_name": "format",
            "arguments": {"text": "HELLO"},
        },
        
    )

    assert result.success is True
    assert result.result["output"] == "hello"  # Default style is 'lower'

    # With optional argument
    result = await tool.execute(
        context=tool_context,
        arguments={
            "skill_name": "format",
            "arguments": {"text": "hello", "style": "upper"},
        },
        
    )

    assert result.success is True
    assert result.result["output"] == "HELLO"


@pytest.mark.asyncio
async def test_skill_tool_no_arguments(skill_registry, tool_context):
    """Test skill that requires no arguments."""

    def get_constant() -> int:
        return 42

    skill_registry.register("constant", get_constant, "Get constant")

    tool = SkillTool(skill_registry)

    result = await tool.execute(
        context=tool_context,
        arguments={"skill_name": "constant"},
        
    )

    assert result.success is True
    assert result.result["output"] == 42


@pytest.mark.asyncio
async def test_skill_tool_complex_return_type(skill_registry, tool_context):
    """Test skill that returns complex types."""

    def get_data() -> dict:
        return {"name": "Alice", "age": 30, "scores": [95, 87, 92]}

    skill_registry.register("data", get_data, "Get data")

    tool = SkillTool(skill_registry)

    result = await tool.execute(
        context=tool_context,
        arguments={"skill_name": "data"},
        
    )

    assert result.success is True
    assert result.result["name"] == "Alice"
    assert result.result["age"] == 30
    assert len(result.result["scores"]) == 3


# Deprecation warning tests
def test_skill_definition_deprecation_warning():
    """Test that SkillDefinition raises deprecation warning."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        skill_def = SkillDefinition("test", lambda: None, "Test")
        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)
        assert "SkillDefinition is deprecated" in str(w[0].message)


def test_skill_registry_deprecation_warning():
    """Test that SkillRegistry raises deprecation warning."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        registry = SkillRegistry()
        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)
        assert "SkillRegistry is deprecated" in str(w[0].message)


def test_skill_tool_deprecation_warning(skill_registry):
    """Test that SkillTool raises deprecation warning."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        tool = SkillTool(skill_registry)
        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)
        assert "SkillTool is deprecated" in str(w[0].message)


def test_skill_decorator_deprecation_warning(skill_registry):
    """Test that @skill decorator raises deprecation warning."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        @skill("test", "Test skill", registry=skill_registry)
        def test_func():
            return "result"

        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)
        assert "@skill decorator is deprecated" in str(w[0].message)

        # Verify backward compatibility - both old and new metadata exist
        assert hasattr(test_func, "_skill_name")
        assert test_func._skill_name == "test"
        assert hasattr(test_func, "_function_name")
        assert test_func._function_name == "test"


@pytest.mark.asyncio
async def test_skill_tool_backward_compatibility_skill_name_parameter(
    skill_registry, tool_context
):
    """Test that SkillTool supports old 'skill_name' parameter."""
    skill_registry.register("add", add_numbers, "Add two numbers")

    tool = SkillTool(skill_registry)

    # Use old parameter name 'skill_name' instead of 'function_name'
    result = await tool.execute(
        context=tool_context,
        arguments={
            "skill_name": "add",  # Old parameter name
            "arguments": {"a": 5, "b": 3},
        },
        
    )

    assert result.success is True
    assert result.result["output"] == 8


def test_skill_tool_inherits_from_function_tool(skill_registry):
    """Test that SkillTool properly inherits from FunctionTool."""
    from omniforge.tools.builtin.function import FunctionTool

    tool = SkillTool(skill_registry)
    assert isinstance(tool, FunctionTool)


def test_skill_registry_inherits_from_function_registry():
    """Test that SkillRegistry properly inherits from FunctionRegistry."""
    from omniforge.tools.builtin.function import FunctionRegistry

    registry = SkillRegistry()
    assert isinstance(registry, FunctionRegistry)
