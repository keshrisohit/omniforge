"""Tests for MCP configuration loading."""

import json
import os
import tempfile

import pytest

from omniforge.mcp.config import MCPConfig, MCPServerConfig, load_mcp_config


class TestMCPServerConfig:
    def test_valid_stdio(self) -> None:
        cfg = MCPServerConfig(transport="stdio", command="npx", args=["-y", "some-server"])
        assert cfg.command == "npx"
        assert cfg.args == ["-y", "some-server"]

    def test_valid_http(self) -> None:
        cfg = MCPServerConfig(transport="http", url="http://localhost:8080/mcp")
        assert cfg.url == "http://localhost:8080/mcp"

    def test_stdio_missing_command_raises(self) -> None:
        with pytest.raises(ValueError, match="command.*required"):
            MCPServerConfig(transport="stdio")

    def test_http_missing_url_raises(self) -> None:
        with pytest.raises(ValueError, match="url.*required"):
            MCPServerConfig(transport="http")

    def test_unsupported_transport_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsupported transport"):
            MCPServerConfig(transport="websocket", url="ws://localhost")

    def test_stdio_with_env(self) -> None:
        cfg = MCPServerConfig(transport="stdio", command="cmd", env={"KEY": "val"})
        assert cfg.env == {"KEY": "val"}

    def test_http_with_headers(self) -> None:
        cfg = MCPServerConfig(
            transport="http", url="http://x.com", headers={"Authorization": "Bearer tok"}
        )
        assert cfg.headers["Authorization"] == "Bearer tok"


class TestLoadMcpConfig:
    def test_empty_returns_empty_config(self) -> None:
        cfg = load_mcp_config()
        assert isinstance(cfg, MCPConfig)
        assert cfg.servers == {}

    def test_from_dict_claude_desktop_format(self) -> None:
        raw = {
            "mcpServers": {
                "filesystem": {
                    "transport": "stdio",
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
                }
            }
        }
        cfg = load_mcp_config(config=raw)
        assert "filesystem" in cfg.servers
        assert cfg.servers["filesystem"].command == "npx"

    def test_from_dict_servers_format(self) -> None:
        raw = {"servers": {"api": {"transport": "http", "url": "http://localhost:8080/mcp"}}}
        cfg = load_mcp_config(config=raw)
        assert "api" in cfg.servers
        assert cfg.servers["api"].url == "http://localhost:8080/mcp"

    def test_from_json_string(self) -> None:
        raw = json.dumps(
            {"mcpServers": {"test": {"transport": "stdio", "command": "echo", "args": ["hello"]}}}
        )
        cfg = load_mcp_config(config=raw)
        assert "test" in cfg.servers

    def test_from_file(self) -> None:
        raw = {
            "mcpServers": {
                "fs": {"transport": "stdio", "command": "npx", "args": ["-y", "server-fs"]}
            }
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(raw, f)
            path = f.name

        try:
            cfg = load_mcp_config(config=path)
            assert "fs" in cfg.servers
        finally:
            os.unlink(path)

    def test_from_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        raw = json.dumps(
            {
                "mcpServers": {
                    "env_server": {
                        "transport": "http",
                        "url": "http://env.example.com/mcp",
                    }
                }
            }
        )
        monkeypatch.setenv("OMNIFORGE_MCP_CONFIG", raw)
        cfg = load_mcp_config()
        assert "env_server" in cfg.servers

    def test_env_var_not_used_when_config_provided(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(
            "OMNIFORGE_MCP_CONFIG",
            json.dumps({"mcpServers": {"env_s": {"transport": "stdio", "command": "cmd"}}}),
        )
        direct = {"mcpServers": {"direct_s": {"transport": "stdio", "command": "cmd2"}}}
        cfg = load_mcp_config(config=direct)
        assert "direct_s" in cfg.servers
        assert "env_s" not in cfg.servers

    def test_invalid_json_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid MCP config JSON"):
            load_mcp_config(config="{not valid json}")

    def test_multiple_servers(self) -> None:
        raw = {
            "mcpServers": {
                "a": {"transport": "stdio", "command": "cmd_a"},
                "b": {"transport": "http", "url": "http://b.example.com"},
            }
        }
        cfg = load_mcp_config(config=raw)
        assert len(cfg.servers) == 2
        assert "a" in cfg.servers
        assert "b" in cfg.servers
