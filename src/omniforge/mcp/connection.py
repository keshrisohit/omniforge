"""MCP server connection abstractions.

Provides connect/disconnect lifecycle and list_tools/call_tool operations
for stdio and Streamable HTTP transports.

Adapted from src/omniforge/skills/mcp-builder/scripts/connections.py.
"""

from abc import ABC, abstractmethod
from contextlib import AsyncExitStack
from typing import Any, Optional

from omniforge.mcp.config import MCPServerConfig
from omniforge.mcp.errors import MCPConnectionError, MCPToolCallError


class MCPConnection(ABC):
    """Base class for MCP server connections.

    Maintains a persistent session for the lifetime of the connection.
    Call ``connect()`` before any tool operations, and ``disconnect()``
    when done.
    """

    def __init__(self, server_name: str) -> None:
        self.server_name = server_name
        self._session: Any = None
        self._stack: Optional[AsyncExitStack] = None

    @property
    def is_connected(self) -> bool:
        """Whether the connection is currently active."""
        return self._session is not None

    @abstractmethod
    def _create_context(self) -> Any:
        """Create the transport-specific async context manager."""

    async def connect(self) -> None:
        """Establish connection to the MCP server and initialise the session."""
        from mcp import ClientSession

        self._stack = AsyncExitStack()
        await self._stack.__aenter__()

        try:
            ctx = self._create_context()
            result = await self._stack.enter_async_context(ctx)

            # Transports return (read, write) or (read, write, _)
            if len(result) == 2:
                read, write = result
            elif len(result) >= 3:
                read, write = result[0], result[1]
            else:
                raise MCPConnectionError(
                    self.server_name,
                    f"Unexpected transport result length: {len(result)}",
                )

            session_ctx = ClientSession(read, write)
            self._session = await self._stack.enter_async_context(session_ctx)
            await self._session.initialize()
        except MCPConnectionError:
            await self._stack.__aexit__(None, None, None)
            self._stack = None
            raise
        except Exception as exc:
            await self._stack.__aexit__(None, None, None)
            self._stack = None
            raise MCPConnectionError(self.server_name, str(exc)) from exc

    async def disconnect(self) -> None:
        """Close the connection and clean up resources."""
        if self._stack is not None:
            await self._stack.__aexit__(None, None, None)
        self._session = None
        self._stack = None

    async def list_tools(self) -> list[dict[str, Any]]:
        """Retrieve available tools from the MCP server.

        Returns:
            List of dicts with keys: name, description, input_schema

        Raises:
            MCPConnectionError: If not connected.
        """
        if not self.is_connected:
            raise MCPConnectionError(self.server_name, "Not connected; call connect() first")

        try:
            response = await self._session.list_tools()
            return [
                {
                    "name": tool.name,
                    "description": tool.description or "",
                    "input_schema": tool.inputSchema,
                }
                for tool in response.tools
            ]
        except Exception as exc:
            raise MCPConnectionError(self.server_name, f"list_tools failed: {exc}") from exc

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Call a tool on the MCP server.

        Args:
            tool_name: The original MCP tool name (not the OmniForge namespaced name).
            arguments: Tool arguments dict.

        Returns:
            The content returned by the MCP server.

        Raises:
            MCPConnectionError: If not connected.
            MCPToolCallError: If the call fails.
        """
        if not self.is_connected:
            raise MCPConnectionError(self.server_name, "Not connected; call connect() first")

        try:
            result = await self._session.call_tool(tool_name, arguments=arguments)
            return result.content
        except (MCPConnectionError, MCPToolCallError):
            raise
        except Exception as exc:
            raise MCPToolCallError(self.server_name, tool_name, str(exc)) from exc


class MCPConnectionStdio(MCPConnection):
    """MCP connection via stdio transport."""

    def __init__(
        self,
        server_name: str,
        command: str,
        args: Optional[list[str]] = None,
        env: Optional[dict[str, str]] = None,
    ) -> None:
        super().__init__(server_name)
        self.command = command
        self.args = args or []
        self.env = env

    def _create_context(self) -> Any:
        from mcp import StdioServerParameters
        from mcp.client.stdio import stdio_client

        return stdio_client(
            StdioServerParameters(command=self.command, args=self.args, env=self.env)
        )


class MCPConnectionHTTP(MCPConnection):
    """MCP connection via Streamable HTTP transport."""

    def __init__(
        self,
        server_name: str,
        url: str,
        headers: Optional[dict[str, str]] = None,
    ) -> None:
        super().__init__(server_name)
        self.url = url
        self.headers = headers or {}

    def _create_context(self) -> Any:
        from mcp.client.streamable_http import streamablehttp_client

        return streamablehttp_client(url=self.url, headers=self.headers)


def create_connection(server_name: str, config: MCPServerConfig) -> MCPConnection:
    """Factory: create the correct MCPConnection for a server config.

    Args:
        server_name: Logical name for the server (used in error messages).
        config: Parsed MCPServerConfig.

    Returns:
        Appropriate MCPConnection subclass (not yet connected).
    """
    transport = config.transport.lower()

    if transport == "stdio":
        assert config.command is not None
        return MCPConnectionStdio(
            server_name=server_name,
            command=config.command,
            args=config.args,
            env=config.env,
        )
    elif transport in ("http", "streamable_http", "streamable-http"):
        assert config.url is not None
        return MCPConnectionHTTP(
            server_name=server_name,
            url=config.url,
            headers=config.headers,
        )
    else:
        raise ValueError(f"Unsupported transport: {config.transport}")
