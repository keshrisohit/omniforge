"""MCP-specific error types.

These extend the base ToolError hierarchy so MCP failures integrate
naturally with OmniForge's existing error handling.
"""

from typing import Any

from omniforge.tools.errors import ToolError


class MCPConnectionError(ToolError):
    """Raised when an MCP server connection cannot be established or is lost."""

    error_code = "MCP_CONNECTION_ERROR"

    def __init__(self, server_name: str, reason: str, **context: Any) -> None:
        message = f"MCP connection failed for server '{server_name}': {reason}"
        super().__init__(message, server_name=server_name, reason=reason, **context)


class MCPToolCallError(ToolError):
    """Raised when an MCP tool call fails at the protocol or execution level."""

    error_code = "MCP_TOOL_CALL_ERROR"

    def __init__(self, server_name: str, tool_name: str, reason: str, **context: Any) -> None:
        message = f"MCP tool call failed: server='{server_name}' tool='{tool_name}': {reason}"
        super().__init__(
            message, server_name=server_name, tool_name=tool_name, reason=reason, **context
        )
