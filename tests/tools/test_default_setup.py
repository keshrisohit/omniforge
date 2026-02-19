"""Tests for default tool registry setup."""

import pytest

from omniforge.llm.config import LLMConfig, ProviderConfig
from omniforge.tools.base import ToolCallContext, ToolDefinition, ToolResult
from omniforge.tools.builtin.llm import LLMTool
from omniforge.tools.registry import ToolRegistry
from omniforge.tools.setup import get_default_tool_registry, setup_default_tools


def test_setup_default_tools_registers_llm_tool() -> None:
    """Test setup_default_tools registers LLM tool."""
    registry = ToolRegistry()
    config = LLMConfig(default_model="gpt-4")

    setup_default_tools(registry, config)

    tool_names = registry.list_tools()

    assert "llm" in tool_names


def test_setup_default_tools_with_custom_config() -> None:
    """Test setup_default_tools uses provided config."""
    registry = ToolRegistry()
    config = LLMConfig(
        default_model="claude-sonnet-4",
        approved_models=["claude-sonnet-4", "gpt-4"],
        providers={"anthropic": ProviderConfig(api_key="sk-test-key")},
    )

    setup_default_tools(registry, config)

    # Get the LLM tool
    tool_names = registry.list_tools()

    assert "llm" in tool_names


def test_setup_default_tools_returns_registry() -> None:
    """Test setup_default_tools returns the registry for chaining."""
    registry = ToolRegistry()
    config = LLMConfig(default_model="gpt-4")

    result = setup_default_tools(registry, config)

    assert result is registry


def test_setup_default_tools_without_config() -> None:
    """Test setup_default_tools loads config from environment if not provided."""
    registry = ToolRegistry()

    # Should use environment config or defaults
    setup_default_tools(registry)

    tool_names = registry.list_tools()

    assert "llm" in tool_names


def test_get_default_tool_registry_returns_registry() -> None:
    """Test get_default_tool_registry returns a ToolRegistry."""
    registry = get_default_tool_registry()

    assert isinstance(registry, ToolRegistry)


def test_get_default_tool_registry_has_llm_tool() -> None:
    """Test default registry includes LLM tool."""
    registry = get_default_tool_registry()

    tool_names = registry.list_tools()

    assert "llm" in tool_names


def test_get_default_tool_registry_returns_singleton() -> None:
    """Test get_default_tool_registry returns the same instance."""
    registry1 = get_default_tool_registry()
    registry2 = get_default_tool_registry()

    assert registry1 is registry2


def test_get_default_tool_registry_thread_safe() -> None:
    """Test get_default_tool_registry is thread-safe."""
    import threading

    registries = []

    def get_registry():
        reg = get_default_tool_registry()
        registries.append(reg)

    # Create multiple threads that get the registry simultaneously
    threads = [threading.Thread(target=get_registry) for _ in range(10)]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    # All should be the same instance
    assert all(reg is registries[0] for reg in registries)
    assert len(set(id(reg) for reg in registries)) == 1


def test_llm_tool_discoverable_via_list_tools() -> None:
    """Test LLM tool is discoverable via registry.list_tools()."""
    registry = get_default_tool_registry()

    tool_names = registry.list_tools()

    assert "llm" in tool_names

    # Verify we can get the tool definition
    llm_tool = registry.get("llm")
    assert llm_tool is not None
    assert llm_tool.definition.type.value == "llm"


def test_llm_tool_discoverable_via_get() -> None:
    """Test LLM tool is discoverable via registry.get()."""
    registry = get_default_tool_registry()

    llm_tool = registry.get("llm")

    assert llm_tool is not None
    assert isinstance(llm_tool, LLMTool)
    assert llm_tool.definition.name == "llm"


@pytest.mark.asyncio
async def test_llm_tool_executable_through_registry() -> None:
    """Test LLM tool can be executed through registry."""
    from unittest.mock import AsyncMock, MagicMock, patch

    registry = get_default_tool_registry()
    llm_tool = registry.get("llm")

    # Create mock response
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message = MagicMock()
    mock_response.choices[0].message.content = "Test response"
    mock_response.usage = MagicMock()
    mock_response.usage.prompt_tokens = 10
    mock_response.usage.completion_tokens = 5
    mock_response.model = "gpt-4"
    mock_response.__contains__ = MagicMock(side_effect=lambda x: x in ["usage", "model"])
    mock_response.get = MagicMock(
        side_effect=lambda k, default=None: {
            "usage": mock_response.usage,
            "model": mock_response.model,
        }.get(k, default)
    )

    context = ToolCallContext(correlation_id="corr-1", task_id="task-1", agent_id="agent-1")

    with patch("litellm.acompletion", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = mock_response

        result = await llm_tool.execute(arguments={"prompt": "Hello"}, context=context)

        assert result.success is True
        assert result.result["content"] == "Test response"


def test_setup_default_tools_idempotent() -> None:
    """Test setup_default_tools can be called multiple times safely."""
    registry = ToolRegistry()
    config = LLMConfig(default_model="gpt-4")

    # First call
    setup_default_tools(registry, config)

    # Second call should raise error (tool already registered)
    with pytest.raises(Exception):  # ToolAlreadyRegisteredError
        setup_default_tools(registry, config)


def test_custom_registry_with_additional_tools() -> None:
    """Test custom registry can have additional tools beyond defaults."""
    from omniforge.tools.base import BaseTool
    from omniforge.tools.types import ToolType

    class CustomTool(BaseTool):
        @property
        def definition(self) -> ToolDefinition:
            return ToolDefinition(name="custom", type=ToolType.FUNCTION, description="Custom tool")

        async def execute(self, context: ToolCallContext, arguments: dict) -> ToolResult:
            return ToolResult(success=True, duration_ms=0)

    registry = ToolRegistry()
    setup_default_tools(registry)

    # Add custom tool
    registry.register(CustomTool())

    tool_names = registry.list_tools()

    assert "llm" in tool_names
    assert "custom" in tool_names
    # Default tools: llm, bash, read, write, grep, glob (6) + custom (1) = 7
    assert len(tool_names) == 7
    assert "bash" in tool_names
    assert "read" in tool_names
    assert "write" in tool_names
    assert "grep" in tool_names
    assert "glob" in tool_names
