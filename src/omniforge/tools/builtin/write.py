"""Write tool for writing file contents.

This module provides WriteTool for writing text to files through the
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


class WriteTool(BaseTool):
    """Tool for writing file contents.

    Provides file writing through the unified tool interface with:
    - Text encoding support
    - File size limits
    - Automatic directory creation
    - UTF-8 encoding with error handling

    Example:
        >>> tool = WriteTool(max_file_size_mb=10)
        >>> context = ToolCallContext(
        ...     correlation_id="corr-1",
        ...     task_id="task-1",
        ...     agent_id="agent-1"
        ... )
        >>> result = await tool.execute(
        ...     arguments={
        ...         "file_path": "/path/to/file.txt",
        ...         "content": "Hello, World!"
        ...     },
        ...     context=context
        ... )
        >>> result.success
        True
    """

    def __init__(self, max_file_size_mb: int = 10) -> None:
        """Initialize WriteTool.

        Args:
            max_file_size_mb: Maximum file size in MB (default: 10MB)
        """
        self._max_file_size_bytes = max_file_size_mb * 1024 * 1024

    @property
    def definition(self) -> ToolDefinition:
        """Get tool definition."""
        return ToolDefinition(
            name="write",
            type=ToolType.FILE_WRITE,
            description=(
                "Write content to a text file. Creates the file if it doesn't exist, "
                "overwrites if it does. Automatically creates parent directories. "
                "Use for saving results, generating output files, or creating "
                "configuration files during skill execution."
            ),
            parameters=[
                ToolParameter(
                    name="file_path",
                    type=ParameterType.STRING,
                    description="Absolute path to the file to write",
                    required=True,
                ),
                ToolParameter(
                    name="content",
                    type=ParameterType.STRING,
                    description="Content to write to the file",
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
        """Write file contents.

        Args:
            context: Execution context
            arguments: Tool arguments containing file_path, content, and encoding

        Returns:
            ToolResult with write confirmation or error
        """
        start_time = time.time()

        # Extract arguments
        file_path_str = arguments.get("file_path", "").strip()
        content = arguments.get("content")
        encoding = arguments.get("encoding", "utf-8")

        # Validate file_path
        if not file_path_str:
            return ToolResult(
                success=False,
                error="file_path cannot be empty",
                duration_ms=int((time.time() - start_time) * 1000),
            )

        # Validate content
        if content is None:
            return ToolResult(
                success=False,
                error="content is required",
                duration_ms=int((time.time() - start_time) * 1000),
            )

        try:
            file_path = Path(file_path_str).resolve()

            # Check content size
            content_size = len(content.encode(encoding))
            if content_size > self._max_file_size_bytes:
                return ToolResult(
                    success=False,
                    error=(
                        f"Content size ({content_size} bytes) exceeds maximum "
                        f"({self._max_file_size_bytes} bytes)"
                    ),
                    duration_ms=int((time.time() - start_time) * 1000),
                )

            # Create parent directory if needed
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write file
            file_path.write_text(content, encoding=encoding)

            duration_ms = int((time.time() - start_time) * 1000)

            return ToolResult(
                success=True,
                result={
                    "message": "File written successfully",
                    "file_path": str(file_path),
                    "size_bytes": content_size,
                    "encoding": encoding,
                },
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return ToolResult(
                success=False,
                error=f"Failed to write file: {str(e)}",
                duration_ms=duration_ms,
            )
