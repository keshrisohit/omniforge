"""Tool name conversion utilities for MCP integration.

Converts MCP server/tool names to OmniForge's snake_case naming convention,
producing tool names in the format: mcp__{server}__{tool}
"""

import re


def to_snake_case(name: str) -> str:
    """Convert a name to snake_case.

    Handles camelCase, PascalCase, kebab-case, and space-separated names.

    Args:
        name: Name to convert

    Returns:
        snake_case version of the name

    Examples:
        >>> to_snake_case("searchRepos")
        'search_repos'
        >>> to_snake_case("ListDirectory")
        'list_directory'
        >>> to_snake_case("list-directory")
        'list_directory'
        >>> to_snake_case("read_file")
        'read_file'
    """
    # Replace hyphens and spaces with underscores
    name = re.sub(r"[-\s]+", "_", name)

    # Insert underscore before uppercase letters that follow lowercase letters or digits
    # e.g., "searchRepos" -> "search_Repos", "ListDirectory" -> "List_Directory"
    name = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)

    # Insert underscore before uppercase letters that are followed by lowercase letters
    # and preceded by uppercase letters — handles sequences like "APIClient" -> "API_Client"
    name = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)

    # Lowercase everything
    name = name.lower()

    # Collapse multiple underscores
    name = re.sub(r"_+", "_", name)

    # Strip leading/trailing underscores
    name = name.strip("_")

    return name


def make_omniforge_tool_name(server_name: str, tool_name: str) -> str:
    """Create an OmniForge tool name from an MCP server and tool name.

    The format is: mcp__{server_snake}__{tool_snake}

    Both server_name and tool_name are converted to snake_case before combining.

    Args:
        server_name: MCP server identifier (e.g., "github", "my-server")
        tool_name: MCP tool name (e.g., "searchRepos", "list_directory")

    Returns:
        OmniForge tool name (e.g., "mcp__github__search_repos")

    Examples:
        >>> make_omniforge_tool_name("github", "searchRepos")
        'mcp__github__search_repos'
        >>> make_omniforge_tool_name("my-server", "ListDirectory")
        'mcp__my_server__list_directory'
        >>> make_omniforge_tool_name("filesystem", "read_file")
        'mcp__filesystem__read_file'
    """
    server_snake = to_snake_case(server_name)
    tool_snake = to_snake_case(tool_name)
    return f"mcp__{server_snake}__{tool_snake}"
