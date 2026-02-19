"""Tests for MCP connection classes (mocked MCP session)."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from omniforge.mcp.config import MCPServerConfig
from omniforge.mcp.connection import (
    MCPConnectionHTTP,
    MCPConnectionStdio,
    create_connection,
)
from omniforge.mcp.errors import MCPConnectionError, MCPToolCallError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_tool(name: str, description: str = "desc", schema: dict = None) -> MagicMock:
    tool = MagicMock()
    tool.name = name
    tool.description = description
    tool.inputSchema = schema or {"type": "object", "properties": {}}
    return tool


def _make_session(tools: list[MagicMock] = None, call_result_content: Any = None) -> AsyncMock:
    """Build a mock ClientSession."""
    session = AsyncMock()

    list_response = MagicMock()
    list_response.tools = tools or []
    session.list_tools = AsyncMock(return_value=list_response)

    call_response = MagicMock()
    call_response.content = call_result_content or [{"type": "text", "text": "ok"}]
    session.call_tool = AsyncMock(return_value=call_response)

    session.initialize = AsyncMock()
    return session


# ---------------------------------------------------------------------------
# Patching helper — replaces ClientSession + transport context
# ---------------------------------------------------------------------------


def _patch_connection(session: AsyncMock, transport_result: tuple = None):
    """Context manager that patches the MCP client machinery."""
    if transport_result is None:
        transport_result = (AsyncMock(), AsyncMock())  # (read, write)

    # The AsyncExitStack.enter_async_context calls need to return the right things:
    # first call → transport result (read, write)
    # second call → session
    async def fake_enter_async_context(ctx: Any) -> Any:
        # Detect if we're entering the ClientSession or the transport
        if isinstance(ctx, AsyncMock) and hasattr(ctx, "initialize"):
            # It's the session
            return session
        # It's the transport context
        return transport_result

    return patch(
        "omniforge.mcp.connection.AsyncExitStack",
        side_effect=lambda: _make_exit_stack(fake_enter_async_context, session),
    )


def _make_exit_stack(enter_fn: Any, session: AsyncMock) -> MagicMock:
    stack = AsyncMock()
    # Track calls so first call = transport, second call = session
    call_count = {"n": 0}

    async def enter_async_context(ctx: Any) -> Any:
        call_count["n"] += 1
        if call_count["n"] == 1:
            # Transport
            return (AsyncMock(), AsyncMock())
        else:
            # Session — the ctx IS the ClientSession
            return session

    stack.enter_async_context = enter_async_context
    stack.__aenter__ = AsyncMock(return_value=stack)
    stack.__aexit__ = AsyncMock(return_value=None)
    return stack


# ---------------------------------------------------------------------------
# Tests for MCPConnectionStdio
# ---------------------------------------------------------------------------


class TestMCPConnectionStdio:
    def test_initial_state_not_connected(self) -> None:
        conn = MCPConnectionStdio("test", command="echo")
        assert not conn.is_connected

    @pytest.mark.asyncio
    async def test_connect_initialises_session(self) -> None:
        session = _make_session()

        with patch("omniforge.mcp.connection.AsyncExitStack") as mock_stack_cls:
            stack = _make_exit_stack(None, session)
            mock_stack_cls.return_value = stack

            with patch("omniforge.mcp.connection.MCPConnectionStdio._create_context") as mock_ctx:
                mock_ctx.return_value = AsyncMock(__aenter__=AsyncMock(), __aexit__=AsyncMock())

                conn = MCPConnectionStdio("srv", command="echo")
                await conn.connect()

        assert conn.is_connected

    @pytest.mark.asyncio
    async def test_list_tools_returns_tool_dicts(self) -> None:
        tools = [_make_tool("do_thing", "does thing")]
        session = _make_session(tools=tools)

        conn = MCPConnectionStdio("srv", command="echo")
        conn._session = session  # inject session directly

        result = await conn.list_tools()

        assert len(result) == 1
        assert result[0]["name"] == "do_thing"
        assert result[0]["description"] == "does thing"
        assert "input_schema" in result[0]

    @pytest.mark.asyncio
    async def test_call_tool_returns_content(self) -> None:
        content = [{"type": "text", "text": "hello"}]
        session = _make_session(call_result_content=content)

        conn = MCPConnectionStdio("srv", command="echo")
        conn._session = session

        result = await conn.call_tool("do_thing", {"arg": "val"})

        session.call_tool.assert_awaited_once_with("do_thing", arguments={"arg": "val"})
        assert result == content

    @pytest.mark.asyncio
    async def test_list_tools_raises_when_not_connected(self) -> None:
        conn = MCPConnectionStdio("srv", command="echo")
        with pytest.raises(MCPConnectionError, match="Not connected"):
            await conn.list_tools()

    @pytest.mark.asyncio
    async def test_call_tool_raises_when_not_connected(self) -> None:
        conn = MCPConnectionStdio("srv", command="echo")
        with pytest.raises(MCPConnectionError, match="Not connected"):
            await conn.call_tool("do_thing", {})

    @pytest.mark.asyncio
    async def test_disconnect_clears_session(self) -> None:
        conn = MCPConnectionStdio("srv", command="echo")
        conn._session = MagicMock()
        stack = AsyncMock()
        stack.__aexit__ = AsyncMock(return_value=None)
        conn._stack = stack

        await conn.disconnect()

        assert conn._session is None
        assert conn._stack is None

    @pytest.mark.asyncio
    async def test_call_tool_wraps_exceptions(self) -> None:
        session = _make_session()
        session.call_tool = AsyncMock(side_effect=RuntimeError("boom"))

        conn = MCPConnectionStdio("srv", command="echo")
        conn._session = session

        with pytest.raises(MCPToolCallError, match="boom"):
            await conn.call_tool("fail_tool", {})


# ---------------------------------------------------------------------------
# Tests for MCPConnectionHTTP
# ---------------------------------------------------------------------------


class TestMCPConnectionHTTP:
    def test_initial_state_not_connected(self) -> None:
        conn = MCPConnectionHTTP("srv", url="http://localhost:8080/mcp")
        assert not conn.is_connected

    @pytest.mark.asyncio
    async def test_list_tools_empty_server(self) -> None:
        session = _make_session(tools=[])

        conn = MCPConnectionHTTP("srv", url="http://localhost")
        conn._session = session

        result = await conn.list_tools()
        assert result == []


# ---------------------------------------------------------------------------
# Tests for create_connection factory
# ---------------------------------------------------------------------------


class TestCreateConnection:
    def test_stdio_config_returns_stdio_conn(self) -> None:
        cfg = MCPServerConfig(transport="stdio", command="npx", args=["-y", "server"])
        conn = create_connection("my_server", cfg)
        assert isinstance(conn, MCPConnectionStdio)
        assert conn.server_name == "my_server"
        assert conn.command == "npx"

    def test_http_config_returns_http_conn(self) -> None:
        cfg = MCPServerConfig(transport="http", url="http://localhost:8080/mcp")
        conn = create_connection("api", cfg)
        assert isinstance(conn, MCPConnectionHTTP)
        assert conn.url == "http://localhost:8080/mcp"

    def test_unsupported_transport_raises(self) -> None:
        cfg = MCPServerConfig.__new__(MCPServerConfig)
        cfg.__dict__["transport"] = "grpc"
        cfg.__dict__["command"] = None
        cfg.__dict__["url"] = None
        cfg.__dict__["args"] = []
        cfg.__dict__["env"] = None
        cfg.__dict__["headers"] = {}
        with pytest.raises(ValueError, match="Unsupported transport"):
            create_connection("x", cfg)
