"""Tests for read file tool."""

import tempfile
from pathlib import Path

import pytest

from omniforge.tools.base import ToolCallContext
from omniforge.tools.builtin.read import ReadTool


@pytest.fixture
def tool_context() -> ToolCallContext:
    """Create test tool call context."""
    return ToolCallContext(
        correlation_id="corr-123",
        task_id="task-123",
        agent_id="agent-456",
    )


@pytest.fixture
def temp_workspace():
    """Create temporary workspace for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)

        # Create test files
        (workspace / "simple.txt").write_text("Hello, World!")
        (workspace / "multiline.txt").write_text("Line 1\nLine 2\nLine 3")
        (workspace / "empty.txt").write_text("")
        (workspace / "unicode.txt").write_text("Café ☕ 你好 🌍", encoding="utf-8")

        # Create subdirectory with file
        (workspace / "subdir").mkdir()
        (workspace / "subdir" / "nested.txt").write_text("Nested content")

        yield workspace


def test_read_tool_initialization() -> None:
    """Test ReadTool initializes correctly."""
    tool = ReadTool(max_file_size_mb=5)

    assert tool._max_file_size_bytes == 5 * 1024 * 1024


def test_read_tool_default_initialization() -> None:
    """Test ReadTool initializes with defaults."""
    tool = ReadTool()

    assert tool._max_file_size_bytes == 10 * 1024 * 1024


def test_read_tool_definition() -> None:
    """Test ReadTool definition."""
    tool = ReadTool()
    definition = tool.definition

    assert definition.name == "read"
    assert definition.type.value == "file_read"
    assert definition.timeout_ms == 10000

    # Check parameters
    param_names = [p.name for p in definition.parameters]
    assert "file_path" in param_names
    assert "encoding" in param_names

    # Check required parameters
    file_path_param = next(p for p in definition.parameters if p.name == "file_path")
    assert file_path_param.required is True

    encoding_param = next(p for p in definition.parameters if p.name == "encoding")
    assert encoding_param.required is False


@pytest.mark.asyncio
async def test_read_tool_simple_file(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test reading a simple text file."""
    tool = ReadTool()

    result = await tool.execute(
        arguments={"file_path": str(temp_workspace / "simple.txt")},
        context=tool_context,
    )

    assert result.success is True
    assert result.result["content"] == "Hello, World!"
    assert result.result["size_bytes"] == 13
    assert result.result["encoding"] == "utf-8"
    assert result.duration_ms >= 0


@pytest.mark.asyncio
async def test_read_tool_multiline_file(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test reading a multiline text file."""
    tool = ReadTool()

    result = await tool.execute(
        arguments={"file_path": str(temp_workspace / "multiline.txt")},
        context=tool_context,
    )

    assert result.success is True
    assert result.result["content"] == "Line 1\nLine 2\nLine 3"
    assert "Line 1" in result.result["content"]
    assert "Line 2" in result.result["content"]
    assert "Line 3" in result.result["content"]


@pytest.mark.asyncio
async def test_read_tool_empty_file(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test reading an empty file."""
    tool = ReadTool()

    result = await tool.execute(
        arguments={"file_path": str(temp_workspace / "empty.txt")},
        context=tool_context,
    )

    assert result.success is True
    assert result.result["content"] == ""
    assert result.result["size_bytes"] == 0


@pytest.mark.asyncio
async def test_read_tool_unicode_file(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test reading a file with unicode characters."""
    tool = ReadTool()

    result = await tool.execute(
        arguments={"file_path": str(temp_workspace / "unicode.txt")},
        context=tool_context,
    )

    assert result.success is True
    assert "Café" in result.result["content"]
    assert "☕" in result.result["content"]
    assert "你好" in result.result["content"]
    assert "🌍" in result.result["content"]


@pytest.mark.asyncio
async def test_read_tool_nested_file(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test reading a file in a subdirectory."""
    tool = ReadTool()

    result = await tool.execute(
        arguments={"file_path": str(temp_workspace / "subdir" / "nested.txt")},
        context=tool_context,
    )

    assert result.success is True
    assert result.result["content"] == "Nested content"


@pytest.mark.asyncio
async def test_read_tool_nonexistent_file(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test reading a nonexistent file returns error."""
    tool = ReadTool()

    result = await tool.execute(
        arguments={"file_path": str(temp_workspace / "nonexistent.txt")},
        context=tool_context,
    )

    assert result.success is False
    assert "not found" in result.error.lower()


@pytest.mark.asyncio
async def test_read_tool_directory_as_file(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test error when trying to read a directory."""
    tool = ReadTool()

    result = await tool.execute(
        arguments={"file_path": str(temp_workspace / "subdir")},
        context=tool_context,
    )

    assert result.success is False
    assert "not a file" in result.error.lower()


@pytest.mark.asyncio
async def test_read_tool_empty_path(tool_context: ToolCallContext) -> None:
    """Test error when file_path is empty."""
    tool = ReadTool()

    result = await tool.execute(
        arguments={"file_path": ""},
        context=tool_context,
    )

    assert result.success is False
    assert "cannot be empty" in result.error


@pytest.mark.asyncio
async def test_read_tool_whitespace_path(tool_context: ToolCallContext) -> None:
    """Test error when file_path is only whitespace."""
    tool = ReadTool()

    result = await tool.execute(
        arguments={"file_path": "   "},
        context=tool_context,
    )

    assert result.success is False
    assert "cannot be empty" in result.error


@pytest.mark.asyncio
async def test_read_tool_file_size_limit(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test file size limit is enforced."""
    tool = ReadTool(max_file_size_mb=1)  # 1 MB limit

    # Create a file larger than 1 MB
    large_file = temp_workspace / "large.txt"
    large_content = "x" * (2 * 1024 * 1024)  # 2 MB
    large_file.write_text(large_content)

    result = await tool.execute(
        arguments={"file_path": str(large_file)},
        context=tool_context,
    )

    assert result.success is False
    assert "exceeds maximum" in result.error


@pytest.mark.asyncio
async def test_read_tool_custom_encoding(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test reading file with custom encoding."""
    tool = ReadTool()

    # Create file with latin-1 encoding
    latin_file = temp_workspace / "latin.txt"
    latin_file.write_text("Café", encoding="latin-1")

    result = await tool.execute(
        arguments={"file_path": str(latin_file), "encoding": "latin-1"},
        context=tool_context,
    )

    assert result.success is True
    assert result.result["content"] == "Café"
    assert result.result["encoding"] == "latin-1"


@pytest.mark.asyncio
async def test_read_tool_invalid_encoding(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test error with invalid encoding."""
    tool = ReadTool()

    result = await tool.execute(
        arguments={
            "file_path": str(temp_workspace / "simple.txt"),
            "encoding": "invalid-encoding-xyz",
        },
        context=tool_context,
    )

    assert result.success is False
    assert "Failed to read file" in result.error


@pytest.mark.asyncio
async def test_read_tool_resolves_path(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test that file path is resolved to absolute path."""
    tool = ReadTool()

    result = await tool.execute(
        arguments={"file_path": str(temp_workspace / "simple.txt")},
        context=tool_context,
    )

    assert result.success is True
    # Result should contain resolved absolute path
    assert Path(result.result["file_path"]).is_absolute()


@pytest.mark.asyncio
async def test_read_tool_special_characters_in_content(
    temp_workspace, tool_context: ToolCallContext
) -> None:
    """Test reading file with special characters in content."""
    tool = ReadTool()

    # Create file with special characters
    special_file = temp_workspace / "special.txt"
    special_content = "Line with\ttabs\nLine with\r\nCRLF\nLine with 'quotes' and \"double quotes\""
    special_file.write_text(special_content)

    result = await tool.execute(
        arguments={"file_path": str(special_file)},
        context=tool_context,
    )

    assert result.success is True
    assert "\t" in result.result["content"]
    assert "'quotes'" in result.result["content"]
    assert '"double quotes"' in result.result["content"]


@pytest.mark.asyncio
async def test_read_tool_exact_size_limit(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test file at exact size limit is readable."""
    tool = ReadTool(max_file_size_mb=1)

    # Create file exactly 1 MB
    exact_file = temp_workspace / "exact.txt"
    exact_content = "x" * (1024 * 1024)
    exact_file.write_text(exact_content)

    result = await tool.execute(
        arguments={"file_path": str(exact_file)},
        context=tool_context,
    )

    assert result.success is True
    assert len(result.result["content"]) == 1024 * 1024


@pytest.mark.asyncio
async def test_read_tool_one_byte_over_limit(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test file one byte over limit is rejected."""
    tool = ReadTool(max_file_size_mb=1)

    # Create file 1 byte over 1 MB
    over_file = temp_workspace / "over.txt"
    over_content = "x" * (1024 * 1024 + 1)
    over_file.write_text(over_content)

    result = await tool.execute(
        arguments={"file_path": str(over_file)},
        context=tool_context,
    )

    assert result.success is False
    assert "exceeds maximum" in result.error


@pytest.mark.asyncio
async def test_read_tool_preserves_line_endings(
    temp_workspace, tool_context: ToolCallContext
) -> None:
    """Test that different line endings are preserved."""
    tool = ReadTool()

    # Create file with mixed line endings
    mixed_file = temp_workspace / "mixed.txt"
    mixed_file.write_bytes(b"Line 1\nLine 2\r\nLine 3\rLine 4")

    result = await tool.execute(
        arguments={"file_path": str(mixed_file)},
        context=tool_context,
    )

    assert result.success is True
    # Content should be preserved as-is
    assert "Line 1" in result.result["content"]
    assert "Line 2" in result.result["content"]
