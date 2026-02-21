"""MCP server configuration loading.

Supports Claude Desktop JSON format via the OMNIFORGE_MCP_CONFIG environment variable
or a direct config dict/file path.
"""

import json
import os
from typing import Any, Optional

from pydantic import BaseModel, Field, model_validator


class MCPServerConfig(BaseModel):
    """Configuration for a single MCP server."""

    transport: str = Field(description="Transport type: 'stdio' or 'http'")

    # stdio transport fields
    command: Optional[str] = Field(default=None, description="Command to run (stdio only)")
    args: list[str] = Field(default_factory=list, description="Command arguments (stdio only)")
    env: Optional[dict[str, str]] = Field(
        default=None, description="Environment variables (stdio only)"
    )

    # http transport fields
    url: Optional[str] = Field(default=None, description="Server URL (http only)")
    headers: dict[str, str] = Field(default_factory=dict, description="HTTP headers (http only)")

    @model_validator(mode="after")
    def validate_transport_fields(self) -> "MCPServerConfig":
        """Validate required fields are present for the chosen transport."""
        transport = self.transport.lower()
        if transport == "stdio":
            if not self.command:
                raise ValueError("'command' is required for stdio transport")
        elif transport in ("http", "streamable_http", "streamable-http", "sse"):
            if not self.url:
                raise ValueError(f"'url' is required for {transport} transport")
        else:
            raise ValueError(
                f"Unsupported transport '{self.transport}'. Use 'stdio', 'http', or 'sse'."
            )
        return self


class MCPConfig(BaseModel):
    """Top-level MCP configuration (Claude Desktop JSON format)."""

    servers: dict[str, MCPServerConfig] = Field(
        default_factory=dict,
        description="Map of server name to server configuration",
    )


def load_mcp_config(
    config: Optional[Any] = None,
    env_var: str = "OMNIFORGE_MCP_CONFIG",
) -> MCPConfig:
    """Load MCP configuration from various sources.

    Priority (highest to lowest):
    1. ``config`` argument (dict or file path string)
    2. ``OMNIFORGE_MCP_CONFIG`` environment variable (JSON string or file path)

    The JSON format follows the Claude Desktop convention::

        {
          "mcpServers": {
            "filesystem": {
              "transport": "stdio",
              "command": "npx",
              "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
            }
          }
        }

    Args:
        config: Optional dict with raw config, file path string, or None.
        env_var: Name of the environment variable to check (default: OMNIFORGE_MCP_CONFIG).

    Returns:
        MCPConfig parsed from the resolved source, or empty MCPConfig if no source.
    """
    raw: Optional[dict[str, Any]] = None

    if config is not None:
        if isinstance(config, dict):
            raw = config
        elif isinstance(config, str):
            raw = _load_from_file_or_json(config)
    else:
        env_value = os.environ.get(env_var)
        if env_value:
            raw = _load_from_file_or_json(env_value)

    if raw is None:
        return MCPConfig()

    return _parse_raw_config(raw)


def _load_from_file_or_json(value: str) -> dict[str, Any]:
    """Load a JSON dict from a file path or raw JSON string."""
    # Try as file path first
    if os.path.exists(value):
        with open(value) as f:
            return json.load(f)  # type: ignore[no-any-return]

    # Otherwise treat as a JSON string
    try:
        result = json.loads(value)
        if not isinstance(result, dict):
            raise ValueError(f"Expected a JSON object, got {type(result).__name__}")
        return result  # type: ignore[no-any-return]
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid MCP config JSON: {exc}") from exc


def _parse_raw_config(raw: dict[str, Any]) -> MCPConfig:
    """Parse a raw config dict into MCPConfig.

    Accepts both ``mcpServers`` (Claude Desktop) and ``servers`` keys.
    """
    # Support Claude Desktop format: {"mcpServers": {...}}
    if "mcpServers" in raw:
        servers_raw = raw["mcpServers"]
    elif "servers" in raw:
        servers_raw = raw["servers"]
    else:
        # Treat the entire dict as server map
        servers_raw = raw

    servers = {name: MCPServerConfig(**server_data) for name, server_data in servers_raw.items()}
    return MCPConfig(servers=servers)
