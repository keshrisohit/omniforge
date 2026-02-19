"""MCPServerManager — lifecycle management and tool registration for MCP servers.

Connects to all configured MCP servers, discovers their tools, wraps each tool
as an MCPTool, and registers them in an OmniForge ToolRegistry.
"""

import logging
from typing import Optional

from omniforge.mcp.config import MCPConfig, MCPServerConfig, load_mcp_config
from omniforge.mcp.connection import MCPConnection, create_connection
from omniforge.mcp.errors import MCPConnectionError
from omniforge.mcp.naming import make_omniforge_tool_name
from omniforge.mcp.tool import MCPTool
from omniforge.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class MCPServerManager:
    """Manages the lifecycle of MCP server connections and tool registration.

    Usage::

        manager = MCPServerManager(config, registry)
        await manager.connect_all()   # at startup
        # ... agent runs ...
        await manager.disconnect_all()  # at shutdown
    """

    def __init__(self, config: MCPConfig, registry: ToolRegistry) -> None:
        self._config = config
        self._registry = registry
        self._connections: dict[str, MCPConnection] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def connect_all(self) -> None:
        """Connect to all configured MCP servers and register their tools.

        Failed servers are logged and skipped — they do not abort startup.
        """
        for server_name, server_cfg in self._config.servers.items():
            await self._connect_server(server_name, server_cfg)

    async def disconnect_all(self) -> None:
        """Disconnect from all connected MCP servers."""
        for server_name, connection in list(self._connections.items()):
            try:
                await connection.disconnect()
                logger.info("MCP server '%s' disconnected", server_name)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Error disconnecting from MCP server '%s': %s", server_name, exc)
        self._connections.clear()

    @property
    def connected_servers(self) -> list[str]:
        """Names of currently connected MCP servers."""
        return list(self._connections.keys())

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _connect_server(self, server_name: str, config: MCPServerConfig) -> None:
        """Connect to a single server and register its tools; log on failure."""
        try:
            connection = create_connection(server_name, config)
            await connection.connect()
            self._connections[server_name] = connection
            logger.info("Connected to MCP server '%s'", server_name)

            await self._register_tools(server_name, connection)
        except MCPConnectionError as exc:
            logger.error("Failed to connect to MCP server '%s': %s (skipping)", server_name, exc)
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Unexpected error connecting to MCP server '%s': %s (skipping)", server_name, exc
            )

    async def _register_tools(self, server_name: str, connection: MCPConnection) -> None:
        """Discover tools from a connected server and register them."""
        try:
            tools = await connection.list_tools()
        except MCPConnectionError as exc:
            logger.error("Failed to list tools from MCP server '%s': %s", server_name, exc)
            return

        registered = 0
        for tool_info in tools:
            mcp_tool_name = tool_info["name"]
            omniforge_name = make_omniforge_tool_name(server_name, mcp_tool_name)

            mcp_tool = MCPTool(
                omniforge_name=omniforge_name,
                server_name=server_name,
                mcp_tool_name=mcp_tool_name,
                description=tool_info.get("description", ""),
                input_schema=tool_info.get("input_schema", {}),
                connection=connection,
            )

            try:
                self._registry.register(mcp_tool)
                registered += 1
                logger.debug(
                    "Registered MCP tool '%s' from server '%s'", omniforge_name, server_name
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Failed to register MCP tool '%s' from server '%s': %s",
                    omniforge_name,
                    server_name,
                    exc,
                )

        logger.info("Registered %d tool(s) from MCP server '%s'", registered, server_name)


async def create_mcp_manager(
    registry: ToolRegistry,
    config: Optional[MCPConfig] = None,
) -> Optional[MCPServerManager]:
    """Convenience factory: load config, create manager, connect all servers.

    Args:
        registry: ToolRegistry to register MCP tools into.
        config: Optional pre-loaded MCPConfig.  If None, loads from
                OMNIFORGE_MCP_CONFIG environment variable.

    Returns:
        Connected MCPServerManager, or None if no servers are configured.
    """
    resolved_config = config or load_mcp_config()

    if not resolved_config.servers:
        logger.debug("No MCP servers configured; skipping MCP setup")
        return None

    manager = MCPServerManager(resolved_config, registry)
    await manager.connect_all()
    return manager
