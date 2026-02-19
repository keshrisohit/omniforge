"""File system operations tool with security controls.

This module provides the FileSystemTool for file read/write operations
through the unified tool interface with path validation and safety controls.
"""

import os
import time
from pathlib import Path
from typing import Any, List, Optional

from omniforge.tools.base import (
    BaseTool,
    ParameterType,
    ToolCallContext,
    ToolDefinition,
    ToolParameter,
    ToolResult,
)
from omniforge.tools.types import ToolType


class FileSystemTool(BaseTool):
    """Tool for file system operations with security controls.

    Provides file system access through the unified tool interface with:
    - Path validation and traversal attack prevention
    - allowed_paths restriction for security
    - Read-only mode support
    - File size limits
    - Support for read, write, list, and exists operations

    Example:
        >>> tool = FileSystemTool(
        ...     allowed_paths=["/tmp/agent_workspace"],
        ...     read_only=False,
        ...     max_file_size_mb=10
        ... )
        >>> context = ToolCallContext(
        ...     correlation_id="corr-1",
        ...     task_id="task-1",
        ...     agent_id="agent-1"
        ... )
        >>> result = await tool.execute(
        ...     arguments={"operation": "read", "path": "/tmp/agent_workspace/data.txt"},
        ...     context=context
        ... )
        >>> result.success
        True
    """

    def __init__(
        self,
        allowed_paths: List[str],
        read_only: bool = False,
        max_file_size_mb: int = 10,
    ) -> None:
        """Initialize FileSystemTool.

        Args:
            allowed_paths: List of directory paths that can be accessed
            read_only: If True, only read and list operations are allowed
            max_file_size_mb: Maximum file size in MB for read/write operations
        """
        self._allowed_paths = [Path(p).resolve() for p in allowed_paths]
        self._read_only = read_only
        self._max_file_size_bytes = max_file_size_mb * 1024 * 1024

    @property
    def definition(self) -> ToolDefinition:
        """Get tool definition."""
        return ToolDefinition(
            name="file_system",
            type=ToolType.FILE_SYSTEM,
            description="Perform file system operations (read, write, list, exists) with security controls",
            parameters=[
                ToolParameter(
                    name="operation",
                    type=ParameterType.STRING,
                    description="Operation to perform: read, write, list, or exists",
                    required=True,
                ),
                ToolParameter(
                    name="path",
                    type=ParameterType.STRING,
                    description="File or directory path",
                    required=True,
                ),
                ToolParameter(
                    name="content",
                    type=ParameterType.STRING,
                    description="Content to write (required for write operation)",
                    required=False,
                ),
                ToolParameter(
                    name="encoding",
                    type=ParameterType.STRING,
                    description="Text encoding (default: utf-8)",
                    required=False,
                ),
            ],
            timeout_ms=30000,  # 30 seconds default
        )

    async def execute(self, context: ToolCallContext, arguments: dict[str, Any]) -> ToolResult:
        """Execute file system operation with security controls.

        Args:
            context: Execution context
            arguments: Tool arguments containing operation, path, content, and encoding

        Returns:
            ToolResult with operation results or error
        """
        start_time = time.time()

        # Extract arguments
        operation = arguments.get("operation", "").lower()
        path_str = arguments.get("path", "")
        content = arguments.get("content")
        encoding = arguments.get("encoding", "utf-8")

        # Validate operation
        valid_operations = ["read", "write", "list", "exists"]
        if operation not in valid_operations:
            return ToolResult(
                success=False,
                error=f"Invalid operation '{operation}'. Must be one of: {', '.join(valid_operations)}",
                duration_ms=int((time.time() - start_time) * 1000),
            )

        # Validate path
        if not path_str:
            return ToolResult(
                success=False,
                error="Path cannot be empty",
                duration_ms=int((time.time() - start_time) * 1000),
            )

        try:
            # Resolve and validate path
            target_path = Path(path_str).resolve()

            # Check if path is within allowed paths
            if not self._is_path_allowed(target_path):
                return ToolResult(
                    success=False,
                    error=f"Access denied: Path '{path_str}' is not within allowed directories",
                    duration_ms=int((time.time() - start_time) * 1000),
                )

            # Check read-only mode for write operations
            if self._read_only and operation == "write":
                return ToolResult(
                    success=False,
                    error="Write operations are not allowed in read-only mode",
                    duration_ms=int((time.time() - start_time) * 1000),
                )

            # Execute operation
            if operation == "read":
                result = await self._read_file(target_path, encoding)
            elif operation == "write":
                result = await self._write_file(target_path, content, encoding)
            elif operation == "list":
                result = await self._list_directory(target_path)
            elif operation == "exists":
                result = await self._check_exists(target_path)
            else:
                return ToolResult(
                    success=False,
                    error=f"Unknown operation: {operation}",
                    duration_ms=int((time.time() - start_time) * 1000),
                )

            duration_ms = int((time.time() - start_time) * 1000)

            return ToolResult(
                success=True,
                result=result,
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return ToolResult(
                success=False,
                error=f"File system operation failed: {str(e)}",
                duration_ms=duration_ms,
            )

    def _is_path_allowed(self, path: Path) -> bool:
        """Check if path is within allowed directories.

        Args:
            path: Path to validate

        Returns:
            True if path is allowed, False otherwise
        """
        # Check if path is under any allowed path
        for allowed_path in self._allowed_paths:
            try:
                # Check if target is under allowed path
                path.relative_to(allowed_path)
                return True
            except ValueError:
                # Not a subpath, continue checking
                continue

        return False

    async def _read_file(self, path: Path, encoding: str) -> dict[str, Any]:
        """Read file content.

        Args:
            path: Path to file
            encoding: Text encoding

        Returns:
            Dictionary with file content and metadata

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file is too large
        """
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        if not path.is_file():
            raise ValueError(f"Path is not a file: {path}")

        # Check file size
        file_size = path.stat().st_size
        if file_size > self._max_file_size_bytes:
            raise ValueError(
                f"File size ({file_size} bytes) exceeds maximum "
                f"({self._max_file_size_bytes} bytes)"
            )

        # Read file
        content = path.read_text(encoding=encoding)

        return {
            "content": content,
            "size_bytes": file_size,
            "path": str(path),
            "encoding": encoding,
        }

    async def _write_file(
        self, path: Path, content: Optional[str], encoding: str
    ) -> dict[str, Any]:
        """Write content to file.

        Args:
            path: Path to file
            content: Content to write
            encoding: Text encoding

        Returns:
            Dictionary with write operation metadata

        Raises:
            ValueError: If content is None or too large
        """
        if content is None:
            raise ValueError("Content is required for write operation")

        # Check content size
        content_size = len(content.encode(encoding))
        if content_size > self._max_file_size_bytes:
            raise ValueError(
                f"Content size ({content_size} bytes) exceeds maximum "
                f"({self._max_file_size_bytes} bytes)"
            )

        # Create parent directory if it doesn't exist
        path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        path.write_text(content, encoding=encoding)

        return {
            "message": "File written successfully",
            "path": str(path),
            "size_bytes": content_size,
            "encoding": encoding,
        }

    async def _list_directory(self, path: Path) -> dict[str, Any]:
        """List directory contents.

        Args:
            path: Path to directory

        Returns:
            Dictionary with directory contents

        Raises:
            FileNotFoundError: If directory doesn't exist
            ValueError: If path is not a directory
        """
        if not path.exists():
            raise FileNotFoundError(f"Directory not found: {path}")

        if not path.is_dir():
            raise ValueError(f"Path is not a directory: {path}")

        # List contents
        entries = []
        for entry in path.iterdir():
            entries.append({
                "name": entry.name,
                "path": str(entry),
                "is_file": entry.is_file(),
                "is_dir": entry.is_dir(),
                "size_bytes": entry.stat().st_size if entry.is_file() else None,
            })

        # Sort by name
        entries.sort(key=lambda x: x["name"])

        return {
            "path": str(path),
            "entries": entries,
            "count": len(entries),
        }

    async def _check_exists(self, path: Path) -> dict[str, Any]:
        """Check if path exists.

        Args:
            path: Path to check

        Returns:
            Dictionary with existence information
        """
        exists = path.exists()

        result = {
            "path": str(path),
            "exists": exists,
        }

        if exists:
            result["is_file"] = path.is_file()
            result["is_dir"] = path.is_dir()
            if path.is_file():
                result["size_bytes"] = path.stat().st_size

        return result
