"""Tests for tool registry."""

import concurrent.futures
import threading
from typing import Any

import pytest

from omniforge.tools.base import BaseTool, ToolCallContext, ToolDefinition, ToolResult, ToolType
from omniforge.tools.errors import ToolAlreadyRegisteredError, ToolNotFoundError
from omniforge.tools.registry import ToolRegistry, get_default_registry, register_tool


class MockTool(BaseTool):
    """Mock tool for testing."""

    def __init__(self, name: str, tool_type: ToolType = ToolType.API) -> None:
        """Initialize mock tool with name and type."""
        self._definition = ToolDefinition(
            name=name,
            type=tool_type,
            description=f"Mock tool {name}",
        )

    @property
    def definition(self) -> ToolDefinition:
        """Get the tool definition."""
        return self._definition

    async def execute(self, context: ToolCallContext, arguments: dict[str, Any]) -> ToolResult:
        """Mock execute method."""
        return ToolResult(success=True, duration_ms=100)


class TestToolRegistry:
    """Tests for ToolRegistry class."""

    def test_register_tool_success(self) -> None:
        """Tool should be registered successfully."""
        registry = ToolRegistry()
        tool = MockTool("test_tool")

        registry.register(tool)

        assert registry.has_tool("test_tool")
        assert registry.get("test_tool") is tool
        assert registry.get_definition("test_tool") == tool.definition

    def test_register_duplicate_tool_raises_error(self) -> None:
        """Registering duplicate tool should raise ToolAlreadyRegisteredError."""
        registry = ToolRegistry()
        tool1 = MockTool("test_tool")
        tool2 = MockTool("test_tool")

        registry.register(tool1)

        with pytest.raises(ToolAlreadyRegisteredError, match="test_tool"):
            registry.register(tool2)

    def test_register_duplicate_tool_with_replace(self) -> None:
        """Registering duplicate tool with replace=True should succeed."""
        registry = ToolRegistry()
        tool1 = MockTool("test_tool")
        tool2 = MockTool("test_tool")

        registry.register(tool1)
        registry.register(tool2, replace=True)

        # Should return the second tool
        assert registry.get("test_tool") is tool2

    def test_unregister_tool_success(self) -> None:
        """Tool should be unregistered successfully."""
        registry = ToolRegistry()
        tool = MockTool("test_tool")

        registry.register(tool)
        assert registry.has_tool("test_tool")

        registry.unregister("test_tool")
        assert not registry.has_tool("test_tool")

    def test_unregister_nonexistent_tool_raises_error(self) -> None:
        """Unregistering nonexistent tool should raise ToolNotFoundError."""
        registry = ToolRegistry()

        with pytest.raises(ToolNotFoundError, match="nonexistent"):
            registry.unregister("nonexistent")

    def test_get_nonexistent_tool_raises_error(self) -> None:
        """Getting nonexistent tool should raise ToolNotFoundError."""
        registry = ToolRegistry()

        with pytest.raises(ToolNotFoundError, match="nonexistent"):
            registry.get("nonexistent")

    def test_get_definition_nonexistent_tool_raises_error(self) -> None:
        """Getting definition of nonexistent tool should raise ToolNotFoundError."""
        registry = ToolRegistry()

        with pytest.raises(ToolNotFoundError, match="nonexistent"):
            registry.get_definition("nonexistent")

    def test_has_tool_returns_true_for_registered_tool(self) -> None:
        """has_tool should return True for registered tool."""
        registry = ToolRegistry()
        tool = MockTool("test_tool")

        registry.register(tool)

        assert registry.has_tool("test_tool") is True

    def test_has_tool_returns_false_for_nonexistent_tool(self) -> None:
        """has_tool should return False for nonexistent tool."""
        registry = ToolRegistry()

        assert registry.has_tool("nonexistent") is False

    def test_list_tools_returns_all_tools(self) -> None:
        """list_tools should return all registered tool names."""
        registry = ToolRegistry()
        tool1 = MockTool("tool_a")
        tool2 = MockTool("tool_b")
        tool3 = MockTool("tool_c")

        registry.register(tool1)
        registry.register(tool2)
        registry.register(tool3)

        tools = registry.list_tools()

        assert tools == ["tool_a", "tool_b", "tool_c"]

    def test_list_tools_returns_empty_for_empty_registry(self) -> None:
        """list_tools should return empty list for empty registry."""
        registry = ToolRegistry()

        tools = registry.list_tools()

        assert tools == []

    def test_list_tools_filters_by_type(self) -> None:
        """list_tools should filter by tool type."""
        registry = ToolRegistry()
        api_tool = MockTool("api_tool", ToolType.API)
        search_tool = MockTool("search_tool", ToolType.SEARCH)
        database_tool = MockTool("db_tool", ToolType.DATABASE)

        registry.register(api_tool)
        registry.register(search_tool)
        registry.register(database_tool)

        api_tools = registry.list_tools(tool_type="api")
        search_tools = registry.list_tools(tool_type="search")

        assert api_tools == ["api_tool"]
        assert search_tools == ["search_tool"]

    def test_list_tools_returns_sorted_results(self) -> None:
        """list_tools should return sorted tool names."""
        registry = ToolRegistry()
        registry.register(MockTool("zebra"))
        registry.register(MockTool("alpha"))
        registry.register(MockTool("beta"))

        tools = registry.list_tools()

        assert tools == ["alpha", "beta", "zebra"]

    def test_clear_removes_all_tools(self) -> None:
        """clear should remove all tools from registry."""
        registry = ToolRegistry()
        registry.register(MockTool("tool_a"))
        registry.register(MockTool("tool_b"))

        assert len(registry.list_tools()) == 2

        registry.clear()

        assert len(registry.list_tools()) == 0
        assert not registry.has_tool("tool_a")
        assert not registry.has_tool("tool_b")

    def test_thread_safety_concurrent_registration(self) -> None:
        """Registry should handle concurrent registration safely."""
        registry = ToolRegistry()
        num_threads = 10
        num_tools_per_thread = 10

        def register_tools(thread_id: int) -> None:
            for i in range(num_tools_per_thread):
                tool = MockTool(f"tool_{thread_id}_{i}")
                registry.register(tool)

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(register_tools, i) for i in range(num_threads)]
            concurrent.futures.wait(futures)

        # All tools should be registered
        assert len(registry.list_tools()) == num_threads * num_tools_per_thread

    def test_thread_safety_concurrent_reads(self) -> None:
        """Registry should handle concurrent reads safely."""
        registry = ToolRegistry()
        tool = MockTool("test_tool")
        registry.register(tool)

        results = []

        def read_tool() -> None:
            try:
                retrieved_tool = registry.get("test_tool")
                results.append(retrieved_tool is tool)
            except Exception:
                results.append(False)

        threads = [threading.Thread(target=read_tool) for _ in range(100)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All reads should succeed
        assert all(results)
        assert len(results) == 100

    def test_thread_safety_concurrent_modification(self) -> None:
        """Registry should handle concurrent modifications safely."""
        registry = ToolRegistry()
        errors = []

        def register_and_unregister(tool_id: int) -> None:
            try:
                tool = MockTool(f"tool_{tool_id}")
                registry.register(tool)
                if registry.has_tool(f"tool_{tool_id}"):
                    registry.unregister(f"tool_{tool_id}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=register_and_unregister, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # No errors should occur (some unregister may fail if tool was already removed)
        # but we shouldn't have any race conditions or corruption
        assert len(errors) == 0 or all(isinstance(e, ToolNotFoundError) for e in errors)


class TestGlobalRegistry:
    """Tests for global registry functions."""

    def test_get_default_registry_returns_singleton(self) -> None:
        """get_default_registry should return the same instance."""
        registry1 = get_default_registry()
        registry2 = get_default_registry()

        assert registry1 is registry2

    def test_get_default_registry_thread_safe(self) -> None:
        """get_default_registry should be thread-safe."""
        registries = []

        def get_registry() -> None:
            registries.append(get_default_registry())

        threads = [threading.Thread(target=get_registry) for _ in range(100)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All threads should get the same registry instance
        assert all(r is registries[0] for r in registries)

    def test_register_tool_uses_default_registry(self) -> None:
        """register_tool should use the default registry."""
        # Clear any previous state
        registry = get_default_registry()
        registry.clear()

        tool = MockTool("global_tool")
        register_tool(tool)

        # Tool should be in the default registry
        assert registry.has_tool("global_tool")
        assert registry.get("global_tool") is tool

    def test_register_tool_with_replace(self) -> None:
        """register_tool should support replace parameter."""
        registry = get_default_registry()
        registry.clear()

        tool1 = MockTool("replaceable_tool")
        tool2 = MockTool("replaceable_tool")

        register_tool(tool1)
        register_tool(tool2, replace=True)

        # Should have the second tool
        assert registry.get("replaceable_tool") is tool2

    def test_register_tool_duplicate_raises_error(self) -> None:
        """register_tool should raise error for duplicates without replace."""
        registry = get_default_registry()
        registry.clear()

        tool1 = MockTool("duplicate_tool")
        tool2 = MockTool("duplicate_tool")

        register_tool(tool1)

        with pytest.raises(ToolAlreadyRegisteredError, match="duplicate_tool"):
            register_tool(tool2)


class TestRegistryEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_registry_handles_many_tools(self) -> None:
        """Registry should handle large number of tools."""
        registry = ToolRegistry()
        num_tools = 1000

        # Register many tools
        for i in range(num_tools):
            tool = MockTool(f"tool_{i:04d}")
            registry.register(tool)

        # All should be present
        assert len(registry.list_tools()) == num_tools

        # Should be able to retrieve any tool
        for i in range(0, num_tools, 100):
            assert registry.has_tool(f"tool_{i:04d}")

    def test_registry_clear_idempotent(self) -> None:
        """Calling clear multiple times should be safe."""
        registry = ToolRegistry()
        registry.register(MockTool("test_tool"))

        registry.clear()
        registry.clear()

        assert len(registry.list_tools()) == 0

    def test_list_tools_with_nonexistent_type(self) -> None:
        """list_tools with nonexistent type should return empty list."""
        registry = ToolRegistry()
        registry.register(MockTool("api_tool", ToolType.API))

        tools = registry.list_tools(tool_type="nonexistent_type")

        assert tools == []

    def test_register_after_clear(self) -> None:
        """Registry should work normally after being cleared."""
        registry = ToolRegistry()
        registry.register(MockTool("tool1"))
        registry.clear()

        # Should be able to register new tools
        tool = MockTool("tool2")
        registry.register(tool)

        assert registry.has_tool("tool2")
        assert not registry.has_tool("tool1")
