"""Grep tool for searching patterns in files.

This module provides GrepTool for searching text patterns using
regular expressions through the unified tool interface.
"""

import re
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


class GrepTool(BaseTool):
    """Tool for searching patterns in files.

    Provides grep-like pattern search through the unified tool interface with:
    - Regular expression support
    - Case-insensitive search option
    - Line number tracking
    - Match count limiting
    - Context lines (before/after)

    Example:
        >>> tool = GrepTool()
        >>> context = ToolCallContext(
        ...     correlation_id="corr-1",
        ...     task_id="task-1",
        ...     agent_id="agent-1"
        ... )
        >>> result = await tool.execute(
        ...     arguments={
        ...         "pattern": "error",
        ...         "file_path": "/path/to/log.txt"
        ...     },
        ...     context=context
        ... )
        >>> result.success
        True
    """

    def __init__(self, max_file_size_mb: int = 10, max_matches: int = 1000) -> None:
        """Initialize GrepTool.

        Args:
            max_file_size_mb: Maximum file size in MB (default: 10MB)
            max_matches: Maximum number of matches to return (default: 1000)
        """
        self._max_file_size_bytes = max_file_size_mb * 1024 * 1024
        self._max_matches = max_matches

    @property
    def definition(self) -> ToolDefinition:
        """Get tool definition."""
        return ToolDefinition(
            name="grep",
            type=ToolType.GREP,
            description=(
                "Search for patterns in text files using regular expressions. "
                "Returns matching lines with line numbers. Supports case-insensitive "
                "search and context lines. Use for finding specific content, "
                "debugging, or analyzing log files."
            ),
            parameters=[
                ToolParameter(
                    name="pattern",
                    type=ParameterType.STRING,
                    description="Regular expression pattern to search for",
                    required=True,
                ),
                ToolParameter(
                    name="file_path",
                    type=ParameterType.STRING,
                    description="Absolute path to the file to search",
                    required=True,
                ),
                ToolParameter(
                    name="case_insensitive",
                    type=ParameterType.BOOLEAN,
                    description="Perform case-insensitive search (default: False)",
                    required=False,
                ),
                ToolParameter(
                    name="context_lines",
                    type=ParameterType.INTEGER,
                    description="Number of context lines before and after match (default: 0)",
                    required=False,
                ),
            ],
            timeout_ms=30000,  # 30 seconds
        )

    async def execute(
        self, context: ToolCallContext, arguments: dict[str, Any]
    ) -> ToolResult:
        """Search for pattern in file.

        Args:
            context: Execution context
            arguments: Tool arguments containing pattern, file_path, etc.

        Returns:
            ToolResult with matching lines or error
        """
        start_time = time.time()

        # Extract arguments
        pattern_str = arguments.get("pattern", "").strip()
        file_path_str = arguments.get("file_path", "").strip()
        case_insensitive = arguments.get("case_insensitive", False)
        context_lines = arguments.get("context_lines", 0)

        # Validate pattern
        if not pattern_str:
            return ToolResult(
                success=False,
                error="pattern cannot be empty",
                duration_ms=int((time.time() - start_time) * 1000),
            )

        # Validate file_path
        if not file_path_str:
            return ToolResult(
                success=False,
                error="file_path cannot be empty",
                duration_ms=int((time.time() - start_time) * 1000),
            )

        try:
            # Compile regex pattern
            flags = re.IGNORECASE if case_insensitive else 0
            try:
                pattern = re.compile(pattern_str, flags)
            except re.error as e:
                return ToolResult(
                    success=False,
                    error=f"Invalid regular expression: {str(e)}",
                    duration_ms=int((time.time() - start_time) * 1000),
                )

            file_path = Path(file_path_str).resolve()

            # Check existence
            if not file_path.exists():
                return ToolResult(
                    success=False,
                    error=f"File not found: {file_path_str}",
                    duration_ms=int((time.time() - start_time) * 1000),
                )

            # Check it's a file
            if not file_path.is_file():
                return ToolResult(
                    success=False,
                    error=f"Path is not a file: {file_path_str}",
                    duration_ms=int((time.time() - start_time) * 1000),
                )

            # Check file size
            file_size = file_path.stat().st_size
            if file_size > self._max_file_size_bytes:
                return ToolResult(
                    success=False,
                    error=(
                        f"File size ({file_size} bytes) exceeds maximum "
                        f"({self._max_file_size_bytes} bytes)"
                    ),
                    duration_ms=int((time.time() - start_time) * 1000),
                )

            # Read and search file
            lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()

            matches = []
            matched_line_numbers = set()

            # Find all matching lines
            for line_num, line in enumerate(lines, start=1):
                if pattern.search(line):
                    matched_line_numbers.add(line_num)

                    # Stop if we've hit max matches
                    if len(matches) >= self._max_matches:
                        break

            # Build result with context
            for line_num in sorted(matched_line_numbers):
                # Get context lines
                start_line = max(1, line_num - context_lines)
                end_line = min(len(lines), line_num + context_lines)

                match_entry = {
                    "line_number": line_num,
                    "line": lines[line_num - 1],
                    "context_before": [],
                    "context_after": [],
                }

                # Add context before
                for i in range(start_line, line_num):
                    match_entry["context_before"].append({
                        "line_number": i,
                        "line": lines[i - 1],
                    })

                # Add context after
                for i in range(line_num + 1, end_line + 1):
                    match_entry["context_after"].append({
                        "line_number": i,
                        "line": lines[i - 1],
                    })

                matches.append(match_entry)

                if len(matches) >= self._max_matches:
                    break

            duration_ms = int((time.time() - start_time) * 1000)

            return ToolResult(
                success=True,
                result={
                    "matches": matches,
                    "match_count": len(matches),
                    "truncated": len(matched_line_numbers) > self._max_matches,
                    "file_path": str(file_path),
                    "pattern": pattern_str,
                },
                duration_ms=duration_ms,
                truncatable_fields=["matches"],  # Only truncate matches, preserve metadata
            )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return ToolResult(
                success=False,
                error=f"Grep operation failed: {str(e)}",
                duration_ms=duration_ms,
            )
