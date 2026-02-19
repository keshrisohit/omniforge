"""Shared type definitions for tools and agents.

This module contains enums and types that are shared between the tools
and agents modules to avoid circular import dependencies.
"""

from enum import Enum


class ToolType(str, Enum):
    """Type of tool being called."""

    FUNCTION = "function"
    LLM = "llm"
    API = "api"
    DATABASE = "database"
    FILE_SYSTEM = "file_system"
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    BASH = "bash"
    GREP = "grep"
    GLOB = "glob"
    SEARCH = "search"
    SUB_AGENT = "sub_agent"
    SKILL = "skill"
    MCP = "mcp"
    OTHER = "other"


class VisibilityLevel(str, Enum):
    """Visibility level for reasoning steps."""

    FULL = "full"
    SUMMARY = "summary"
    HIDDEN = "hidden"
