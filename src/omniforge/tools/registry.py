"""Tool registry for centralized tool management.

This module provides the ToolRegistry class for registering, retrieving, and
managing tools. It includes a global singleton registry for convenience.
"""

import threading
from typing import Optional

from omniforge.tools.base import BaseTool, ToolDefinition
from omniforge.tools.errors import ToolAlreadyRegisteredError, ToolNotFoundError


class ToolRegistry:
    """Centralized registry for tool registration and discovery.

    The registry maintains a thread-safe collection of tools and their definitions,
    supporting registration, retrieval, and filtering operations.

    Thread safety is ensured through a lock for all mutable operations.
    """

    def __init__(self) -> None:
        """Initialize an empty tool registry."""
        self._tools: dict[str, BaseTool] = {}
        self._definitions: dict[str, ToolDefinition] = {}
        self._lock = threading.Lock()

    def register(self, tool: BaseTool, replace: bool = False) -> None:
        """Register a tool in the registry.

        Args:
            tool: The tool instance to register
            replace: If True, replace existing tool with the same name.
                    If False, raise ToolAlreadyRegisteredError on duplicate.

        Raises:
            ToolAlreadyRegisteredError: If tool is already registered and replace=False
        """
        tool_name = tool.definition.name

        with self._lock:
            if tool_name in self._tools and not replace:
                raise ToolAlreadyRegisteredError(tool_name)

            self._tools[tool_name] = tool
            self._definitions[tool_name] = tool.definition

    def unregister(self, name: str) -> None:
        """Remove a tool from the registry.

        Args:
            name: Name of the tool to remove

        Raises:
            ToolNotFoundError: If tool is not found in registry
        """
        with self._lock:
            if name not in self._tools:
                raise ToolNotFoundError(name)

            del self._tools[name]
            del self._definitions[name]

    def get(self, name: str) -> BaseTool:
        """Get a tool instance by name.

        Args:
            name: Name of the tool to retrieve

        Returns:
            The BaseTool instance

        Raises:
            ToolNotFoundError: If tool is not found in registry
        """
        with self._lock:
            if name not in self._tools:
                raise ToolNotFoundError(name)
            return self._tools[name]

    def get_definition(self, name: str) -> ToolDefinition:
        """Get a tool definition by name.

        Args:
            name: Name of the tool whose definition to retrieve

        Returns:
            The ToolDefinition instance

        Raises:
            ToolNotFoundError: If tool is not found in registry
        """
        with self._lock:
            if name not in self._definitions:
                raise ToolNotFoundError(name)
            return self._definitions[name]

    def list_tools(self, tool_type: Optional[str] = None) -> list[str]:
        """List all registered tool names, optionally filtered by type.

        Args:
            tool_type: Optional tool type to filter by (e.g., "llm", "api")

        Returns:
            List of tool names matching the filter criteria
        """
        with self._lock:
            if tool_type is None:
                return sorted(self._tools.keys())

            # Filter by tool type
            filtered_tools = [
                name
                for name, definition in self._definitions.items()
                if definition.type.value == tool_type
            ]
            return sorted(filtered_tools)

    def has_tool(self, name: str) -> bool:
        """Check if a tool exists in the registry.

        Args:
            name: Name of the tool to check

        Returns:
            True if the tool exists, False otherwise
        """
        with self._lock:
            return name in self._tools

    def clear(self) -> None:
        """Remove all tools from the registry.

        This is primarily useful for testing and cleanup operations.
        """
        with self._lock:
            self._tools.clear()
            self._definitions.clear()


# Global singleton registry
_default_registry: Optional[ToolRegistry] = None
_registry_lock = threading.Lock()


def get_default_registry() -> ToolRegistry:
    """Get the global singleton tool registry.

    Returns:
        The global ToolRegistry instance (creates if needed)
    """
    global _default_registry

    if _default_registry is None:
        with _registry_lock:
            # Double-check locking pattern
            if _default_registry is None:
                _default_registry = ToolRegistry()

    return _default_registry


def register_tool(tool: BaseTool, replace: bool = False) -> None:
    """Register a tool in the global registry.

    Convenience function that delegates to the default registry.

    Args:
        tool: The tool instance to register
        replace: If True, replace existing tool with the same name

    Raises:
        ToolAlreadyRegisteredError: If tool is already registered and replace=False
    """
    registry = get_default_registry()
    registry.register(tool, replace=replace)
