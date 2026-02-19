"""MCP client integration for OmniForge.

Provides MCP server connection management and tool registration so that
OmniForge agents can transparently consume tools from any MCP server.

Typical usage::

    from omniforge.tools.registry import ToolRegistry
    from omniforge.tools.setup import setup_default_tools, setup_mcp_tools

    registry = ToolRegistry()
    setup_default_tools(registry)
    mcp_manager = await setup_mcp_tools(registry)

    # ... run agent ...

    if mcp_manager:
        await mcp_manager.disconnect_all()
"""

from omniforge.mcp.config import MCPConfig, MCPServerConfig, load_mcp_config
from omniforge.mcp.connection import MCPConnection, MCPConnectionHTTP, MCPConnectionStdio
from omniforge.mcp.errors import MCPConnectionError, MCPToolCallError
from omniforge.mcp.manager import MCPServerManager, create_mcp_manager
from omniforge.mcp.naming import make_omniforge_tool_name, to_snake_case
from omniforge.mcp.tool import MCPTool

__all__ = [
    # Config
    "MCPConfig",
    "MCPServerConfig",
    "load_mcp_config",
    # Connection
    "MCPConnection",
    "MCPConnectionStdio",
    "MCPConnectionHTTP",
    # Errors
    "MCPConnectionError",
    "MCPToolCallError",
    # Manager
    "MCPServerManager",
    "create_mcp_manager",
    # Naming
    "to_snake_case",
    "make_omniforge_tool_name",
    # Tool
    "MCPTool",
]
