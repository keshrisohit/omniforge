"""MCPTool — wraps a single MCP server tool as an OmniForge BaseTool.

Key design choices:
- ToolDefinition.parameters is empty; the raw JSON Schema is embedded in the
  description so the LLM can read it.
- validate_arguments() is a no-op: the MCP server validates its own inputs.
- The original MCP tool name is preserved on the instance for the call to the
  server; the OmniForge name uses the mcp__{server}__{tool} convention.
"""

import json
import time
from typing import Any

from omniforge.mcp.connection import MCPConnection
from omniforge.mcp.errors import MCPConnectionError, MCPToolCallError
from omniforge.tools.base import BaseTool, ToolCallContext, ToolDefinition, ToolResult
from omniforge.tools.types import ToolType


class MCPTool(BaseTool):
    """OmniForge tool wrapper for a single MCP server tool.

    Instances are created by MCPServerManager after listing tools from a
    connected server; they should not be instantiated directly.
    """

    def __init__(
        self,
        omniforge_name: str,
        server_name: str,
        mcp_tool_name: str,
        description: str,
        input_schema: dict[str, Any],
        connection: MCPConnection,
        timeout_ms: int = 60000,
    ) -> None:
        """
        Args:
            omniforge_name: Namespaced tool name (e.g. mcp__github__search_repos).
            server_name: Logical server identifier (e.g. "github").
            mcp_tool_name: Original MCP tool name used when calling the server.
            description: Human-readable description from the MCP server.
            input_schema: Raw JSON Schema dict for the tool's parameters.
            connection: Active MCPConnection to use for calls.
            timeout_ms: Execution timeout in milliseconds.
        """
        self._omniforge_name = omniforge_name
        self._server_name = server_name
        self._mcp_tool_name = mcp_tool_name
        self._description = description
        self._input_schema = input_schema
        self._connection = connection
        self._timeout_ms = timeout_ms

    @property
    def definition(self) -> ToolDefinition:
        schema_json = json.dumps(self._input_schema, indent=2)
        full_description = (
            f"{self._description}\n\n"
            f"MCP server: {self._server_name}\n"
            f"Parameters (JSON Schema):\n{schema_json}"
        )
        return ToolDefinition(
            name=self._omniforge_name,
            type=ToolType.MCP,
            description=full_description,
            parameters=[],  # Schema is in description; MCP server validates inputs
            timeout_ms=self._timeout_ms,
        )

    def validate_arguments(self, arguments: dict[str, Any]) -> None:
        """No-op: MCP server performs its own argument validation."""
        pass

    async def execute(self, context: ToolCallContext, arguments: dict[str, Any]) -> ToolResult:
        """Call the MCP tool and return a ToolResult.

        Args:
            context: OmniForge execution context (not forwarded to MCP server).
            arguments: Tool arguments forwarded verbatim to the MCP server.

        Returns:
            ToolResult wrapping the MCP server response.
        """
        start = time.time()

        try:
            content = await self._connection.call_tool(self._mcp_tool_name, arguments)
            duration_ms = int((time.time() - start) * 1000)

            # Normalise MCP content list into a serialisable dict
            result_data = _content_to_dict(content)

            return ToolResult(
                success=True,
                result=result_data,
                duration_ms=duration_ms,
            )

        except (MCPConnectionError, MCPToolCallError) as exc:
            duration_ms = int((time.time() - start) * 1000)
            return ToolResult(
                success=False,
                error=str(exc),
                duration_ms=duration_ms,
            )
        except Exception as exc:
            duration_ms = int((time.time() - start) * 1000)
            return ToolResult(
                success=False,
                error=f"Unexpected error calling MCP tool '{self._mcp_tool_name}': {exc}",
                duration_ms=duration_ms,
            )


def _content_to_dict(content: Any) -> dict[str, Any]:
    """Convert MCP content (list of content items or raw value) to a plain dict."""
    if isinstance(content, list):
        items = []
        for item in content:
            if hasattr(item, "__dict__"):
                items.append({k: v for k, v in item.__dict__.items() if not k.startswith("_")})
            elif isinstance(item, dict):
                items.append(item)
            else:
                items.append({"value": str(item)})
        return {"content": items}

    if isinstance(content, dict):
        return content

    return {"content": str(content)}
