"""Glob tool for finding files by pattern.

This module provides GlobTool for finding files using glob patterns
through the unified tool interface.
"""

import time
from pathlib import Path
from typing import Any

from omniforge.tools.base import (
    BaseTool,
    ParameterType,
    ToolCallContext,
    ToolDefinition,
    ToolParameter,
    ToolResult,
)
from omniforge.tools.types import ToolType


class GlobTool(BaseTool):
    """Tool for finding files by pattern.

    Provides glob pattern matching through the unified tool interface with:
    - Recursive search support (**/)
    - Pattern matching (*, ?, [abc])
    - File metadata (size, modification time)
    - Result count limiting

    Example:
        >>> tool = GlobTool()
        >>> context = ToolCallContext(
        ...     correlation_id="corr-1",
        ...     task_id="task-1",
        ...     agent_id="agent-1"
        ... )
        >>> result = await tool.execute(
        ...     arguments={
        ...         "pattern": "**/*.py",
        ...         "base_path": "/path/to/search"
        ...     },
        ...     context=context
        ... )
        >>> result.success
        True
    """

    def __init__(self, max_results: int = 1000) -> None:
        """Initialize GlobTool.

        Args:
            max_results: Maximum number of results to return (default: 1000)
        """
        self._max_results = max_results

    @property
    def definition(self) -> ToolDefinition:
        """Get tool definition."""
        return ToolDefinition(
            name="glob",
            type=ToolType.GLOB,
            description=(
                "Find files matching a glob pattern. Supports wildcards: * (any chars), "
                "** (recursive directories), ? (single char), [abc] (char set). "
                "Returns list of matching file paths with metadata. Use for discovering "
                "files, finding scripts, or listing directory contents."
            ),
            parameters=[
                ToolParameter(
                    name="pattern",
                    type=ParameterType.STRING,
                    description=(
                        "Glob pattern (e.g., '*.py', '**/*.txt', 'src/**/*.js')"
                    ),
                    required=True,
                ),
                ToolParameter(
                    name="base_path",
                    type=ParameterType.STRING,
                    description="Base directory to search from (default: current directory)",
                    required=False,
                ),
                ToolParameter(
                    name="files_only",
                    type=ParameterType.BOOLEAN,
                    description="Return only files, exclude directories (default: True)",
                    required=False,
                ),
            ],
            timeout_ms=30000,  # 30 seconds
        )

    async def execute(
        self, context: ToolCallContext, arguments: dict[str, Any]
    ) -> ToolResult:
        """Find files matching pattern.

        Args:
            context: Execution context
            arguments: Tool arguments containing pattern and base_path

        Returns:
            ToolResult with matching file paths or error
        """
        start_time = time.time()

        # Extract arguments
        pattern = arguments.get("pattern", "").strip()
        base_path_str = arguments.get("base_path", ".")
        files_only = arguments.get("files_only", True)

        # Validate pattern
        if not pattern:
            return ToolResult(
                success=False,
                error="pattern cannot be empty",
                duration_ms=int((time.time() - start_time) * 1000),
            )

        try:
            base_path = Path(base_path_str).resolve()

            # Check base_path exists
            if not base_path.exists():
                return ToolResult(
                    success=False,
                    error=f"Base path does not exist: {base_path_str}",
                    duration_ms=int((time.time() - start_time) * 1000),
                )

            # Check it's a directory
            if not base_path.is_dir():
                return ToolResult(
                    success=False,
                    error=f"Base path is not a directory: {base_path_str}",
                    duration_ms=int((time.time() - start_time) * 1000),
                )

            # Find matches
            matches = []
            for match_path in base_path.glob(pattern):
                # Filter by type
                if files_only and not match_path.is_file():
                    continue

                # Get metadata
                try:
                    stat = match_path.stat()
                    match_entry = {
                        "path": str(match_path),
                        "name": match_path.name,
                        "is_file": match_path.is_file(),
                        "is_dir": match_path.is_dir(),
                        "size_bytes": stat.st_size if match_path.is_file() else None,
                        "modified_time": stat.st_mtime,
                    }
                    matches.append(match_entry)

                    # Stop if we've hit max results
                    if len(matches) >= self._max_results:
                        break
                except (OSError, PermissionError):
                    # Skip files we can't access
                    continue

            # Sort by path
            matches.sort(key=lambda x: x["path"])

            duration_ms = int((time.time() - start_time) * 1000)

            return ToolResult(
                success=True,
                result={
                    "matches": matches,
                    "match_count": len(matches),
                    "truncated": len(matches) >= self._max_results,
                    "pattern": pattern,
                    "base_path": str(base_path),
                },
                duration_ms=duration_ms,
                truncatable_fields=["matches"],  # Only truncate matches, preserve metadata
            )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return ToolResult(
                success=False,
                error=f"Glob operation failed: {str(e)}",
                duration_ms=duration_ms,
            )
