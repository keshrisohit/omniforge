"""Tests for MCPServerManager."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from omniforge.mcp.config import MCPConfig, MCPServerConfig
from omniforge.mcp.connection import MCPConnection
from omniforge.mcp.errors import MCPConnectionError
from omniforge.mcp.manager import MCPServerManager, create_mcp_manager
from omniforge.tools.registry import ToolRegistry

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(
    *servers: tuple[str, str, str],
) -> MCPConfig:
    """Build MCPConfig from (name, transport, command_or_url) tuples."""
    server_cfgs: dict[str, MCPServerConfig] = {}
    for name, transport, target in servers:
        if transport == "stdio":
            server_cfgs[name] = MCPServerConfig(transport="stdio", command=target)
        else:
            server_cfgs[name] = MCPServerConfig(transport="http", url=target)
    return MCPConfig(servers=server_cfgs)


def _make_connection(
    tools: list[dict[str, Any]] = None,
    fail_connect: bool = False,
    fail_list: bool = False,
) -> MagicMock:
    conn = MagicMock(spec=MCPConnection)
    conn.is_connected = True

    if fail_connect:
        conn.connect = AsyncMock(side_effect=MCPConnectionError("srv", "refused"))
    else:
        conn.connect = AsyncMock()

    if fail_list:
        conn.list_tools = AsyncMock(side_effect=MCPConnectionError("srv", "list failed"))
    else:
        conn.list_tools = AsyncMock(
            return_value=tools
            or [
                {
                    "name": "search_repos",
                    "description": "Search repos",
                    "input_schema": {"type": "object"},
                }
            ]
        )

    conn.disconnect = AsyncMock()
    return conn


# ---------------------------------------------------------------------------
# connect_all
# ---------------------------------------------------------------------------


class TestMCPServerManagerConnectAll:
    @pytest.mark.asyncio
    async def test_connects_and_registers_tools(self) -> None:
        config = _make_config(("github", "stdio", "gh-server"))
        registry = ToolRegistry()

        conn = _make_connection(
            tools=[
                {"name": "searchRepos", "description": "Search", "input_schema": {"type": "object"}}
            ]
        )

        with patch("omniforge.mcp.manager.create_connection", return_value=conn):
            manager = MCPServerManager(config, registry)
            await manager.connect_all()

        assert "github" in manager.connected_servers
        tool_names = registry.list_tools()
        assert "mcp__github__search_repos" in tool_names

    @pytest.mark.asyncio
    async def test_failed_connect_is_skipped(self) -> None:
        config = _make_config(("broken", "stdio", "bad-cmd"))
        registry = ToolRegistry()

        conn = _make_connection(fail_connect=True)

        with patch("omniforge.mcp.manager.create_connection", return_value=conn):
            manager = MCPServerManager(config, registry)
            await manager.connect_all()  # should not raise

        assert "broken" not in manager.connected_servers
        assert registry.list_tools() == []

    @pytest.mark.asyncio
    async def test_failed_list_tools_skips_registration(self) -> None:
        config = _make_config(("srv", "stdio", "cmd"))
        registry = ToolRegistry()

        conn = _make_connection(fail_list=True)

        with patch("omniforge.mcp.manager.create_connection", return_value=conn):
            manager = MCPServerManager(config, registry)
            await manager.connect_all()

        # Server is connected but no tools registered
        assert "srv" in manager.connected_servers
        assert registry.list_tools() == []

    @pytest.mark.asyncio
    async def test_multiple_servers_all_connected(self) -> None:
        config = _make_config(
            ("a", "stdio", "cmd-a"),
            ("b", "http", "http://localhost:8080"),
        )
        registry = ToolRegistry()

        conn_a = _make_connection(tools=[{"name": "tool_a", "description": "", "input_schema": {}}])
        conn_b = _make_connection(tools=[{"name": "tool_b", "description": "", "input_schema": {}}])

        call_count = {"n": 0}

        def fake_create(server_name: str, cfg: MCPServerConfig) -> MagicMock:
            call_count["n"] += 1
            return conn_a if server_name == "a" else conn_b

        with patch("omniforge.mcp.manager.create_connection", side_effect=fake_create):
            manager = MCPServerManager(config, registry)
            await manager.connect_all()

        assert "a" in manager.connected_servers
        assert "b" in manager.connected_servers
        tool_names = registry.list_tools()
        assert "mcp__a__tool_a" in tool_names
        assert "mcp__b__tool_b" in tool_names

    @pytest.mark.asyncio
    async def test_one_server_fails_other_still_registers(self) -> None:
        config = _make_config(
            ("ok", "stdio", "cmd-ok"),
            ("bad", "stdio", "cmd-bad"),
        )
        registry = ToolRegistry()

        conn_ok = _make_connection(
            tools=[{"name": "ok_tool", "description": "", "input_schema": {}}]
        )
        conn_bad = _make_connection(fail_connect=True)

        def fake_create(server_name: str, cfg: MCPServerConfig) -> MagicMock:
            return conn_ok if server_name == "ok" else conn_bad

        with patch("omniforge.mcp.manager.create_connection", side_effect=fake_create):
            manager = MCPServerManager(config, registry)
            await manager.connect_all()

        assert "ok" in manager.connected_servers
        assert "bad" not in manager.connected_servers
        tool_names = registry.list_tools()
        assert "mcp__ok__ok_tool" in tool_names


# ---------------------------------------------------------------------------
# disconnect_all
# ---------------------------------------------------------------------------


class TestMCPServerManagerDisconnectAll:
    @pytest.mark.asyncio
    async def test_disconnects_all_servers(self) -> None:
        config = _make_config(("srv", "stdio", "cmd"))
        registry = ToolRegistry()
        conn = _make_connection()

        with patch("omniforge.mcp.manager.create_connection", return_value=conn):
            manager = MCPServerManager(config, registry)
            await manager.connect_all()

        await manager.disconnect_all()

        conn.disconnect.assert_awaited_once()
        assert manager.connected_servers == []

    @pytest.mark.asyncio
    async def test_disconnect_error_does_not_raise(self) -> None:
        config = _make_config(("srv", "stdio", "cmd"))
        registry = ToolRegistry()
        conn = _make_connection()
        conn.disconnect = AsyncMock(side_effect=RuntimeError("bang"))

        with patch("omniforge.mcp.manager.create_connection", return_value=conn):
            manager = MCPServerManager(config, registry)
            await manager.connect_all()

        await manager.disconnect_all()  # should not raise


# ---------------------------------------------------------------------------
# create_mcp_manager
# ---------------------------------------------------------------------------


class TestCreateMcpManager:
    @pytest.mark.asyncio
    async def test_returns_none_when_no_servers(self) -> None:
        registry = ToolRegistry()
        empty_config = MCPConfig(servers={})
        result = await create_mcp_manager(registry, config=empty_config)
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_manager_when_servers_present(self) -> None:
        registry = ToolRegistry()
        config = _make_config(("fs", "stdio", "npx"))
        conn = _make_connection(tools=[])

        with patch("omniforge.mcp.manager.create_connection", return_value=conn):
            result = await create_mcp_manager(registry, config=config)

        assert result is not None
        assert isinstance(result, MCPServerManager)

    @pytest.mark.asyncio
    async def test_loads_config_from_env_when_not_provided(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import json

        monkeypatch.setenv(
            "OMNIFORGE_MCP_CONFIG",
            json.dumps({"mcpServers": {"env_srv": {"transport": "stdio", "command": "echo"}}}),
        )
        registry = ToolRegistry()
        conn = _make_connection(tools=[])

        with patch("omniforge.mcp.manager.create_connection", return_value=conn):
            result = await create_mcp_manager(registry)

        assert result is not None
        assert "env_srv" in result.connected_servers
