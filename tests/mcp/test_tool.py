"""Tests for MCPTool."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from omniforge.mcp.connection import MCPConnection
from omniforge.mcp.errors import MCPConnectionError, MCPToolCallError
from omniforge.mcp.tool import MCPTool, _content_to_dict
from omniforge.tools.base import ToolCallContext
from omniforge.tools.types import ToolType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_context() -> ToolCallContext:
    return ToolCallContext(
        correlation_id="corr-1",
        task_id="task-1",
        agent_id="agent-1",
    )


def _make_connection(
    content: Any = None,
    raise_exc: Exception = None,
) -> MagicMock:
    conn = MagicMock(spec=MCPConnection)
    if raise_exc:
        conn.call_tool = AsyncMock(side_effect=raise_exc)
    else:
        conn.call_tool = AsyncMock(return_value=content or [{"type": "text", "text": "ok"}])
    return conn


def _make_tool(
    connection: MagicMock = None,
    schema: dict = None,
) -> MCPTool:
    return MCPTool(
        omniforge_name="mcp__github__search_repos",
        server_name="github",
        mcp_tool_name="searchRepos",
        description="Search GitHub repositories",
        input_schema=schema or {"type": "object", "properties": {"query": {"type": "string"}}},
        connection=connection or _make_connection(),
    )


# ---------------------------------------------------------------------------
# ToolDefinition
# ---------------------------------------------------------------------------


class TestMCPToolDefinition:
    def test_name(self) -> None:
        tool = _make_tool()
        assert tool.definition.name == "mcp__github__search_repos"

    def test_type_is_mcp(self) -> None:
        tool = _make_tool()
        assert tool.definition.type == ToolType.MCP

    def test_parameters_empty(self) -> None:
        tool = _make_tool()
        assert tool.definition.parameters == []

    def test_description_contains_schema(self) -> None:
        tool = _make_tool(schema={"type": "object", "properties": {"q": {"type": "string"}}})
        desc = tool.definition.description
        assert "JSON Schema" in desc
        assert '"q"' in desc

    def test_description_contains_server_name(self) -> None:
        tool = _make_tool()
        assert "github" in tool.definition.description

    def test_description_contains_tool_description(self) -> None:
        tool = _make_tool()
        assert "Search GitHub repositories" in tool.definition.description


# ---------------------------------------------------------------------------
# validate_arguments
# ---------------------------------------------------------------------------


class TestMCPToolValidate:
    def test_validate_is_noop_for_unknown_params(self) -> None:
        tool = _make_tool()
        # Should NOT raise even with "unknown" params
        tool.validate_arguments({"anything": "goes", "extra": 123})

    def test_validate_is_noop_for_empty_args(self) -> None:
        tool = _make_tool()
        tool.validate_arguments({})


# ---------------------------------------------------------------------------
# execute — success paths
# ---------------------------------------------------------------------------


class TestMCPToolExecute:
    @pytest.mark.asyncio
    async def test_successful_call_returns_true(self) -> None:
        conn = _make_connection(content=[{"type": "text", "text": "hello"}])
        tool = _make_tool(connection=conn)

        result = await tool.execute(_make_context(), {"query": "omniforge"})

        assert result.success is True
        conn.call_tool.assert_awaited_once_with("searchRepos", {"query": "omniforge"})

    @pytest.mark.asyncio
    async def test_result_dict_wraps_content(self) -> None:
        content = [{"type": "text", "text": "result text"}]
        conn = _make_connection(content=content)
        tool = _make_tool(connection=conn)

        result = await tool.execute(_make_context(), {})

        assert result.result is not None
        assert "content" in result.result

    @pytest.mark.asyncio
    async def test_duration_ms_is_positive(self) -> None:
        tool = _make_tool()
        result = await tool.execute(_make_context(), {})
        assert result.duration_ms >= 0

    # -- error paths --

    @pytest.mark.asyncio
    async def test_mcp_connection_error_returns_failure(self) -> None:
        exc = MCPConnectionError("github", "not connected")
        conn = _make_connection(raise_exc=exc)
        tool = _make_tool(connection=conn)

        result = await tool.execute(_make_context(), {})

        assert result.success is False
        assert "github" in result.error

    @pytest.mark.asyncio
    async def test_mcp_tool_call_error_returns_failure(self) -> None:
        exc = MCPToolCallError("github", "searchRepos", "server error")
        conn = _make_connection(raise_exc=exc)
        tool = _make_tool(connection=conn)

        result = await tool.execute(_make_context(), {})

        assert result.success is False
        assert "server error" in result.error

    @pytest.mark.asyncio
    async def test_unexpected_exception_returns_failure(self) -> None:
        conn = _make_connection(raise_exc=RuntimeError("boom"))
        tool = _make_tool(connection=conn)

        result = await tool.execute(_make_context(), {})

        assert result.success is False
        assert "boom" in result.error


# ---------------------------------------------------------------------------
# _content_to_dict helper
# ---------------------------------------------------------------------------


class TestContentToDict:
    def test_list_of_dicts(self) -> None:
        result = _content_to_dict([{"type": "text", "text": "hi"}])
        assert result == {"content": [{"type": "text", "text": "hi"}]}

    def test_plain_dict_passthrough(self) -> None:
        result = _content_to_dict({"key": "val"})
        assert result == {"key": "val"}

    def test_string_becomes_content(self) -> None:
        result = _content_to_dict("hello")
        assert result == {"content": "hello"}

    def test_object_with_dunder_dict(self) -> None:
        class Obj:
            def __init__(self) -> None:
                self.type = "text"
                self.text = "msg"
                self._private = "ignored"

        result = _content_to_dict([Obj()])
        assert result["content"][0]["type"] == "text"
        assert result["content"][0]["text"] == "msg"
        assert "_private" not in result["content"][0]

    def test_empty_list(self) -> None:
        result = _content_to_dict([])
        assert result == {"content": []}
