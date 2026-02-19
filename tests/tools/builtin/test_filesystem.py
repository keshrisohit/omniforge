"""Tests for file system operations tool."""

import tempfile
from pathlib import Path

import pytest

from omniforge.tools.base import ToolCallContext
from omniforge.tools.builtin.filesystem import FileSystemTool


@pytest.fixture
def temp_workspace():
    """Create temporary workspace for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)

        # Create test structure
        (workspace / "testdir").mkdir()
        (workspace / "testfile.txt").write_text("Hello, World!")
        (workspace / "testdir" / "nested.txt").write_text("Nested content")

        yield workspace


@pytest.fixture
def tool_context() -> ToolCallContext:
    """Create test tool call context."""
    return ToolCallContext(
        correlation_id="corr-123",
        task_id="task-123",
        agent_id="agent-456",
    )


def test_filesystem_tool_initialization(temp_workspace) -> None:
    """Test FileSystemTool initializes correctly."""
    tool = FileSystemTool(allowed_paths=[str(temp_workspace)], read_only=False, max_file_size_mb=5)

    assert len(tool._allowed_paths) == 1
    assert tool._read_only is False
    assert tool._max_file_size_bytes == 5 * 1024 * 1024


def test_filesystem_tool_definition(temp_workspace) -> None:
    """Test FileSystemTool definition."""
    tool = FileSystemTool(allowed_paths=[str(temp_workspace)])
    definition = tool.definition

    assert definition.name == "file_system"
    assert definition.type.value == "file_system"

    # Check parameters
    param_names = [p.name for p in definition.parameters]
    assert "operation" in param_names
    assert "path" in param_names
    assert "content" in param_names
    assert "encoding" in param_names

    assert definition.timeout_ms == 30000


@pytest.mark.asyncio
async def test_filesystem_tool_read_file(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test reading a file."""
    tool = FileSystemTool(allowed_paths=[str(temp_workspace)])

    result = await tool.execute(
        arguments={"operation": "read", "path": str(temp_workspace / "testfile.txt")},
        context=tool_context,
    )

    assert result.success is True
    assert result.result["content"] == "Hello, World!"
    assert result.result["size_bytes"] == 13
    assert result.result["encoding"] == "utf-8"
    assert result.duration_ms >= 0


@pytest.mark.asyncio
async def test_filesystem_tool_read_nested_file(
    temp_workspace, tool_context: ToolCallContext
) -> None:
    """Test reading a nested file."""
    tool = FileSystemTool(allowed_paths=[str(temp_workspace)])

    result = await tool.execute(
        arguments={"operation": "read", "path": str(temp_workspace / "testdir" / "nested.txt")},
        context=tool_context,
    )

    assert result.success is True
    assert result.result["content"] == "Nested content"


@pytest.mark.asyncio
async def test_filesystem_tool_read_nonexistent_file(
    temp_workspace, tool_context: ToolCallContext
) -> None:
    """Test reading a nonexistent file returns error."""
    tool = FileSystemTool(allowed_paths=[str(temp_workspace)])

    result = await tool.execute(
        arguments={"operation": "read", "path": str(temp_workspace / "nonexistent.txt")},
        context=tool_context,
    )

    assert result.success is False
    assert "not found" in result.error.lower()


@pytest.mark.asyncio
async def test_filesystem_tool_write_file(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test writing a file."""
    tool = FileSystemTool(allowed_paths=[str(temp_workspace)], read_only=False)

    result = await tool.execute(
        arguments={
            "operation": "write",
            "path": str(temp_workspace / "newfile.txt"),
            "content": "New content",
        },
        context=tool_context,
    )

    assert result.success is True
    assert "written successfully" in result.result["message"]
    assert result.result["size_bytes"] == 11

    # Verify file was created
    assert (temp_workspace / "newfile.txt").exists()
    assert (temp_workspace / "newfile.txt").read_text() == "New content"


@pytest.mark.asyncio
async def test_filesystem_tool_write_nested_file(
    temp_workspace, tool_context: ToolCallContext
) -> None:
    """Test writing a file in a new directory."""
    tool = FileSystemTool(allowed_paths=[str(temp_workspace)], read_only=False)

    result = await tool.execute(
        arguments={
            "operation": "write",
            "path": str(temp_workspace / "newdir" / "newfile.txt"),
            "content": "Nested new content",
        },
        context=tool_context,
    )

    assert result.success is True

    # Verify directory and file were created
    assert (temp_workspace / "newdir").exists()
    assert (temp_workspace / "newdir" / "newfile.txt").exists()


@pytest.mark.asyncio
async def test_filesystem_tool_write_without_content(
    temp_workspace, tool_context: ToolCallContext
) -> None:
    """Test writing without content returns error."""
    tool = FileSystemTool(allowed_paths=[str(temp_workspace)], read_only=False)

    result = await tool.execute(
        arguments={"operation": "write", "path": str(temp_workspace / "newfile.txt")},
        context=tool_context,
    )

    assert result.success is False
    assert "required" in result.error.lower()


@pytest.mark.asyncio
async def test_filesystem_tool_list_directory(
    temp_workspace, tool_context: ToolCallContext
) -> None:
    """Test listing directory contents."""
    tool = FileSystemTool(allowed_paths=[str(temp_workspace)])

    result = await tool.execute(
        arguments={"operation": "list", "path": str(temp_workspace)},
        context=tool_context,
    )

    assert result.success is True
    assert result.result["count"] == 2  # testdir and testfile.txt
    assert len(result.result["entries"]) == 2

    # Check entries
    names = [e["name"] for e in result.result["entries"]]
    assert "testdir" in names
    assert "testfile.txt" in names


@pytest.mark.asyncio
async def test_filesystem_tool_list_nested_directory(
    temp_workspace, tool_context: ToolCallContext
) -> None:
    """Test listing nested directory contents."""
    tool = FileSystemTool(allowed_paths=[str(temp_workspace)])

    result = await tool.execute(
        arguments={"operation": "list", "path": str(temp_workspace / "testdir")},
        context=tool_context,
    )

    assert result.success is True
    assert result.result["count"] == 1
    assert result.result["entries"][0]["name"] == "nested.txt"


@pytest.mark.asyncio
async def test_filesystem_tool_list_nonexistent_directory(
    temp_workspace, tool_context: ToolCallContext
) -> None:
    """Test listing nonexistent directory returns error."""
    tool = FileSystemTool(allowed_paths=[str(temp_workspace)])

    result = await tool.execute(
        arguments={"operation": "list", "path": str(temp_workspace / "nonexistent")},
        context=tool_context,
    )

    assert result.success is False
    assert "not found" in result.error.lower()


@pytest.mark.asyncio
async def test_filesystem_tool_exists_file(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test checking if file exists."""
    tool = FileSystemTool(allowed_paths=[str(temp_workspace)])

    result = await tool.execute(
        arguments={"operation": "exists", "path": str(temp_workspace / "testfile.txt")},
        context=tool_context,
    )

    assert result.success is True
    assert result.result["exists"] is True
    assert result.result["is_file"] is True
    assert result.result["is_dir"] is False
    assert "size_bytes" in result.result


@pytest.mark.asyncio
async def test_filesystem_tool_exists_directory(
    temp_workspace, tool_context: ToolCallContext
) -> None:
    """Test checking if directory exists."""
    tool = FileSystemTool(allowed_paths=[str(temp_workspace)])

    result = await tool.execute(
        arguments={"operation": "exists", "path": str(temp_workspace / "testdir")},
        context=tool_context,
    )

    assert result.success is True
    assert result.result["exists"] is True
    assert result.result["is_file"] is False
    assert result.result["is_dir"] is True


@pytest.mark.asyncio
async def test_filesystem_tool_exists_nonexistent(
    temp_workspace, tool_context: ToolCallContext
) -> None:
    """Test checking nonexistent path."""
    tool = FileSystemTool(allowed_paths=[str(temp_workspace)])

    result = await tool.execute(
        arguments={"operation": "exists", "path": str(temp_workspace / "nonexistent.txt")},
        context=tool_context,
    )

    assert result.success is True
    assert result.result["exists"] is False


@pytest.mark.asyncio
async def test_filesystem_tool_invalid_operation(
    temp_workspace, tool_context: ToolCallContext
) -> None:
    """Test invalid operation returns error."""
    tool = FileSystemTool(allowed_paths=[str(temp_workspace)])

    result = await tool.execute(
        arguments={"operation": "invalid", "path": str(temp_workspace / "testfile.txt")},
        context=tool_context,
    )

    assert result.success is False
    assert "invalid operation" in result.error.lower()


@pytest.mark.asyncio
async def test_filesystem_tool_empty_path(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test empty path returns error."""
    tool = FileSystemTool(allowed_paths=[str(temp_workspace)])

    result = await tool.execute(
        arguments={"operation": "read", "path": ""},
        context=tool_context,
    )

    assert result.success is False
    assert "cannot be empty" in result.error.lower()


@pytest.mark.asyncio
async def test_filesystem_tool_path_traversal_prevention(
    temp_workspace, tool_context: ToolCallContext
) -> None:
    """Test path traversal attacks are prevented."""
    tool = FileSystemTool(allowed_paths=[str(temp_workspace)])

    # Try to access parent directory
    result = await tool.execute(
        arguments={"operation": "read", "path": str(temp_workspace / ".." / "sensitive.txt")},
        context=tool_context,
    )

    assert result.success is False
    assert "access denied" in result.error.lower()


@pytest.mark.asyncio
async def test_filesystem_tool_absolute_path_outside_allowed(
    temp_workspace, tool_context: ToolCallContext
) -> None:
    """Test accessing absolute path outside allowed directories."""
    tool = FileSystemTool(allowed_paths=[str(temp_workspace)])

    result = await tool.execute(
        arguments={"operation": "read", "path": "/etc/passwd"},
        context=tool_context,
    )

    assert result.success is False
    assert "access denied" in result.error.lower()


@pytest.mark.asyncio
async def test_filesystem_tool_read_only_mode_allows_read(
    temp_workspace, tool_context: ToolCallContext
) -> None:
    """Test read-only mode allows read operations."""
    tool = FileSystemTool(allowed_paths=[str(temp_workspace)], read_only=True)

    result = await tool.execute(
        arguments={"operation": "read", "path": str(temp_workspace / "testfile.txt")},
        context=tool_context,
    )

    assert result.success is True
    assert result.result["content"] == "Hello, World!"


@pytest.mark.asyncio
async def test_filesystem_tool_read_only_mode_allows_list(
    temp_workspace, tool_context: ToolCallContext
) -> None:
    """Test read-only mode allows list operations."""
    tool = FileSystemTool(allowed_paths=[str(temp_workspace)], read_only=True)

    result = await tool.execute(
        arguments={"operation": "list", "path": str(temp_workspace)},
        context=tool_context,
    )

    assert result.success is True
    assert result.result["count"] > 0


@pytest.mark.asyncio
async def test_filesystem_tool_read_only_mode_prevents_write(
    temp_workspace, tool_context: ToolCallContext
) -> None:
    """Test read-only mode prevents write operations."""
    tool = FileSystemTool(allowed_paths=[str(temp_workspace)], read_only=True)

    result = await tool.execute(
        arguments={
            "operation": "write",
            "path": str(temp_workspace / "newfile.txt"),
            "content": "New content",
        },
        context=tool_context,
    )

    assert result.success is False
    assert "not allowed in read-only mode" in result.error


@pytest.mark.asyncio
async def test_filesystem_tool_file_size_limit(
    temp_workspace, tool_context: ToolCallContext
) -> None:
    """Test file size limit is enforced."""
    # Create a file larger than the limit
    large_content = "x" * (2 * 1024 * 1024)  # 2 MB
    (temp_workspace / "large.txt").write_text(large_content)

    tool = FileSystemTool(allowed_paths=[str(temp_workspace)], max_file_size_mb=1)  # 1 MB limit

    result = await tool.execute(
        arguments={"operation": "read", "path": str(temp_workspace / "large.txt")},
        context=tool_context,
    )

    assert result.success is False
    assert "exceeds maximum" in result.error.lower()


@pytest.mark.asyncio
async def test_filesystem_tool_write_size_limit(
    temp_workspace, tool_context: ToolCallContext
) -> None:
    """Test write size limit is enforced."""
    tool = FileSystemTool(
        allowed_paths=[str(temp_workspace)], read_only=False, max_file_size_mb=1
    )

    large_content = "x" * (2 * 1024 * 1024)  # 2 MB

    result = await tool.execute(
        arguments={
            "operation": "write",
            "path": str(temp_workspace / "large.txt"),
            "content": large_content,
        },
        context=tool_context,
    )

    assert result.success is False
    assert "exceeds maximum" in result.error.lower()


@pytest.mark.asyncio
async def test_filesystem_tool_custom_encoding(
    temp_workspace, tool_context: ToolCallContext
) -> None:
    """Test custom encoding for read/write."""
    tool = FileSystemTool(allowed_paths=[str(temp_workspace)], read_only=False)

    # Write with latin-1 encoding
    result = await tool.execute(
        arguments={
            "operation": "write",
            "path": str(temp_workspace / "encoded.txt"),
            "content": "Café",
            "encoding": "latin-1",
        },
        context=tool_context,
    )

    assert result.success is True

    # Read with latin-1 encoding
    result = await tool.execute(
        arguments={
            "operation": "read",
            "path": str(temp_workspace / "encoded.txt"),
            "encoding": "latin-1",
        },
        context=tool_context,
    )

    assert result.success is True
    assert result.result["content"] == "Café"
    assert result.result["encoding"] == "latin-1"
