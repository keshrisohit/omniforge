"""Default tool registry setup.

This module provides convenience functions for initializing the tool system
with built-in tools like the LLM tool.
"""

import threading
from typing import TYPE_CHECKING, Optional

from omniforge.llm.config import LLMConfig, load_config_from_env
from omniforge.tools.registry import ToolRegistry

if TYPE_CHECKING:
    from omniforge.mcp.config import MCPConfig
    from omniforge.mcp.manager import MCPServerManager

# Thread-safe singleton for default registry
_default_registry: Optional[ToolRegistry] = None
_registry_lock = threading.Lock()


def setup_default_tools(registry: ToolRegistry, config: Optional[LLMConfig] = None) -> ToolRegistry:
    """Set up default built-in tools in a registry.

    Registers all essential built-in tools including:
    - LLM tool for AI completions
    - Bash tool for command execution
    - Read tool for reading files
    - Write tool for writing files
    - Grep tool for searching file contents
    - Glob tool for finding files by pattern

    Args:
        registry: ToolRegistry to register tools in
        config: Optional LLM configuration. If not provided, loads from environment.

    Returns:
        The configured registry (for chaining)

    Example:
        >>> registry = ToolRegistry()
        >>> setup_default_tools(registry)
        >>> "llm" in registry.list_tools()
        True
        >>> "bash" in registry.list_tools()
        True
    """
    # Lazy imports to avoid circular dependencies
    from omniforge.tools.builtin.bash import BashTool
    from omniforge.tools.builtin.glob import GlobTool
    from omniforge.tools.builtin.grep import GrepTool
    from omniforge.tools.builtin.llm import LLMTool
    from omniforge.tools.builtin.read import ReadTool
    from omniforge.tools.builtin.write import WriteTool

    # Use provided config or load from environment
    llm_config = config or load_config_from_env()

    # Register LLM tool
    llm_tool = LLMTool(config=llm_config)
    registry.register(llm_tool)

    # Register file operation tools
    bash_tool = BashTool()
    registry.register(bash_tool)

    read_tool = ReadTool()
    registry.register(read_tool)

    write_tool = WriteTool()
    registry.register(write_tool)

    # Register search tools
    grep_tool = GrepTool()
    registry.register(grep_tool)

    glob_tool = GlobTool()
    registry.register(glob_tool)

    return registry


async def setup_mcp_tools(
    registry: ToolRegistry,
    config: "Optional[MCPConfig]" = None,
) -> "Optional[MCPServerManager]":
    """Connect to configured MCP servers and register their tools in the registry.

    Loads configuration from the ``OMNIFORGE_MCP_CONFIG`` environment variable
    unless a config object is provided directly.

    Args:
        registry: ToolRegistry to register MCP tools into.
        config: Optional pre-loaded MCPConfig. If None, loads from environment.

    Returns:
        Connected MCPServerManager (call ``disconnect_all()`` at shutdown),
        or None if no servers are configured.

    Example::

        registry = ToolRegistry()
        setup_default_tools(registry)
        mcp_manager = await setup_mcp_tools(registry)
        # ... run agent ...
        if mcp_manager:
            await mcp_manager.disconnect_all()
    """
    from omniforge.mcp.manager import create_mcp_manager

    return await create_mcp_manager(registry, config=config)


def get_default_tool_registry() -> ToolRegistry:
    """Get the default tool registry with built-in tools registered.

    This returns a singleton registry instance. On first call, it creates
    the registry and registers default tools. Subsequent calls return the
    same instance.

    Thread-safe with lazy initialization.

    Returns:
        Singleton ToolRegistry with default tools

    Example:
        >>> registry = get_default_tool_registry()
        >>> tools = registry.list_tools()
        >>> any(tool.name == "llm" for tool in tools)
        True
    """
    global _default_registry

    # Check if already initialized (fast path without lock)
    if _default_registry is not None:
        return _default_registry

    # Initialize with lock (slow path)
    with _registry_lock:
        # Double-check after acquiring lock
        if _default_registry is None:
            _default_registry = ToolRegistry()
            setup_default_tools(_default_registry)

        return _default_registry
