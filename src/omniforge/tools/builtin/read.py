"""Read tool for reading file contents.

This module provides ReadTool for reading text files through the
unified tool interface.
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


class ReadTool(BaseTool):
    """Tool for reading file contents.

    Provides file reading through the unified tool interface with:
    - Text encoding support
    - File size limits
    - UTF-8 decoding with error handling

    Example:
        >>> tool = ReadTool(max_file_size_mb=10)
        >>> context = ToolCallContext(
        ...     correlation_id="corr-1",
        ...     task_id="task-1",
        ...     agent_id="agent-1"
        ... )
        >>> result = await tool.execute(
        ...     arguments={"file_path": "/path/to/file.txt"},
        ...     context=context
        ... )
        >>> result.success
        True
    """

    def __init__(self, max_file_size_mb: int = 10) -> None:
        """Initialize ReadTool.

        Args:
            max_file_size_mb: Maximum file size in MB (default: 10MB)
        """
        self._max_file_size_bytes = max_file_size_mb * 1024 * 1024

    @property
    def definition(self) -> ToolDefinition:
        """Get tool definition."""
        return ToolDefinition(
            name="read",
            type=ToolType.FILE_READ,
            description=(
                "Read contents of a text file. Returns file content as a string. "
                "Use for loading reference documents, configuration files, or any "
                "text data needed during skill execution."
            ),
            parameters=[
                ToolParameter(
                    name="file_path",
                    type=ParameterType.STRING,
                    description="Absolute path to the file to read",
                    required=True,
                ),
                ToolParameter(
                    name="encoding",
                    type=ParameterType.STRING,
                    description="Text encoding (default: utf-8)",
                    required=False,
                ),
            ],
            timeout_ms=10000,  # 10 seconds
        )

    async def execute(
        self, context: ToolCallContext, arguments: dict[str, Any]
    ) -> ToolResult:
        """Read file contents.

        Args:
            context: Execution context
            arguments: Tool arguments containing file_path and encoding

        Returns:
            ToolResult with file content or error
        """
        start_time = time.time()

        # Extract arguments
        file_path_str = arguments.get("file_path", "").strip()
        encoding = arguments.get("encoding", "utf-8")

        # Validate file_path
        if not file_path_str:
            return ToolResult(
                success=False,
                error="file_path cannot be empty",
                duration_ms=int((time.time() - start_time) * 1000),
            )

        try:
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

            # Read file
            content = file_path.read_text(encoding=encoding)

            duration_ms = int((time.time() - start_time) * 1000)

            return ToolResult(
                success=True,
                result={
                    "content": content,
                    "file_path": str(file_path),
                    "size_bytes": file_size,
                    "encoding": encoding,
                },
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return ToolResult(
                success=False,
                error=f"Failed to read file: {str(e)}",
                duration_ms=duration_ms,
            )
