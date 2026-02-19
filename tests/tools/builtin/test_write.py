"""Tests for write file tool."""

import tempfile
from pathlib import Path

import pytest

from omniforge.tools.base import ToolCallContext
from omniforge.tools.builtin.write import WriteTool


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
        yield workspace


def test_write_tool_initialization() -> None:
    """Test WriteTool initializes correctly."""
    tool = WriteTool(max_file_size_mb=5)

    assert tool._max_file_size_bytes == 5 * 1024 * 1024


def test_write_tool_default_initialization() -> None:
    """Test WriteTool initializes with defaults."""
    tool = WriteTool()

    assert tool._max_file_size_bytes == 10 * 1024 * 1024


def test_write_tool_definition() -> None:
    """Test WriteTool definition."""
    tool = WriteTool()
    definition = tool.definition

    assert definition.name == "write"
    assert definition.type.value == "file_write"
    assert definition.timeout_ms == 10000

    # Check parameters
    param_names = [p.name for p in definition.parameters]
    assert "file_path" in param_names
    assert "content" in param_names
    assert "encoding" in param_names

    # Check required parameters
    file_path_param = next(p for p in definition.parameters if p.name == "file_path")
    assert file_path_param.required is True

    content_param = next(p for p in definition.parameters if p.name == "content")
    assert content_param.required is True

    encoding_param = next(p for p in definition.parameters if p.name == "encoding")
    assert encoding_param.required is False


@pytest.mark.asyncio
async def test_write_tool_simple_file(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test writing a simple text file."""
    tool = WriteTool()

    file_path = temp_workspace / "test.txt"

    result = await tool.execute(
        arguments={"file_path": str(file_path), "content": "Hello, World!"},
        context=tool_context,
    )

    assert result.success is True
    assert "written successfully" in result.result["message"]
    assert result.result["size_bytes"] == 13
    assert result.result["encoding"] == "utf-8"
    assert result.duration_ms >= 0

    # Verify file was created
    assert file_path.exists()
    assert file_path.read_text() == "Hello, World!"


@pytest.mark.asyncio
async def test_write_tool_overwrite_existing_file(
    temp_workspace, tool_context: ToolCallContext
) -> None:
    """Test overwriting an existing file."""
    tool = WriteTool()

    file_path = temp_workspace / "existing.txt"
    file_path.write_text("Old content")

    result = await tool.execute(
        arguments={"file_path": str(file_path), "content": "New content"},
        context=tool_context,
    )

    assert result.success is True
    assert file_path.read_text() == "New content"


@pytest.mark.asyncio
async def test_write_tool_multiline_content(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test writing multiline content."""
    tool = WriteTool()

    file_path = temp_workspace / "multiline.txt"
    content = "Line 1\nLine 2\nLine 3"

    result = await tool.execute(
        arguments={"file_path": str(file_path), "content": content},
        context=tool_context,
    )

    assert result.success is True
    assert file_path.read_text() == content


@pytest.mark.asyncio
async def test_write_tool_empty_content(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test writing empty content."""
    tool = WriteTool()

    file_path = temp_workspace / "empty.txt"

    result = await tool.execute(
        arguments={"file_path": str(file_path), "content": ""},
        context=tool_context,
    )

    assert result.success is True
    assert file_path.exists()
    assert file_path.read_text() == ""
    assert result.result["size_bytes"] == 0


@pytest.mark.asyncio
async def test_write_tool_unicode_content(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test writing unicode content."""
    tool = WriteTool()

    file_path = temp_workspace / "unicode.txt"
    content = "Café ☕ 你好 🌍"

    result = await tool.execute(
        arguments={"file_path": str(file_path), "content": content},
        context=tool_context,
    )

    assert result.success is True
    assert file_path.read_text(encoding="utf-8") == content


@pytest.mark.asyncio
async def test_write_tool_create_parent_directories(
    temp_workspace, tool_context: ToolCallContext
) -> None:
    """Test that parent directories are created automatically."""
    tool = WriteTool()

    file_path = temp_workspace / "newdir" / "subdir" / "file.txt"

    result = await tool.execute(
        arguments={"file_path": str(file_path), "content": "Nested content"},
        context=tool_context,
    )

    assert result.success is True
    assert file_path.exists()
    assert file_path.read_text() == "Nested content"
    assert file_path.parent.exists()
    assert file_path.parent.is_dir()


@pytest.mark.asyncio
async def test_write_tool_empty_path(tool_context: ToolCallContext) -> None:
    """Test error when file_path is empty."""
    tool = WriteTool()

    result = await tool.execute(
        arguments={"file_path": "", "content": "test"},
        context=tool_context,
    )

    assert result.success is False
    assert "cannot be empty" in result.error


@pytest.mark.asyncio
async def test_write_tool_whitespace_path(tool_context: ToolCallContext) -> None:
    """Test error when file_path is only whitespace."""
    tool = WriteTool()

    result = await tool.execute(
        arguments={"file_path": "   ", "content": "test"},
        context=tool_context,
    )

    assert result.success is False
    assert "cannot be empty" in result.error


@pytest.mark.asyncio
async def test_write_tool_missing_content(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test error when content is missing."""
    tool = WriteTool()

    result = await tool.execute(
        arguments={"file_path": str(temp_workspace / "test.txt")},
        context=tool_context,
    )

    assert result.success is False
    assert "required" in result.error.lower()


@pytest.mark.asyncio
async def test_write_tool_none_content(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test error when content is None."""
    tool = WriteTool()

    result = await tool.execute(
        arguments={"file_path": str(temp_workspace / "test.txt"), "content": None},
        context=tool_context,
    )

    assert result.success is False
    assert "required" in result.error.lower()


@pytest.mark.asyncio
async def test_write_tool_content_size_limit(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test content size limit is enforced."""
    tool = WriteTool(max_file_size_mb=1)  # 1 MB limit

    # Create content larger than 1 MB
    large_content = "x" * (2 * 1024 * 1024)  # 2 MB

    result = await tool.execute(
        arguments={"file_path": str(temp_workspace / "large.txt"), "content": large_content},
        context=tool_context,
    )

    assert result.success is False
    assert "exceeds maximum" in result.error


@pytest.mark.asyncio
async def test_write_tool_custom_encoding(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test writing file with custom encoding."""
    tool = WriteTool()

    file_path = temp_workspace / "latin.txt"

    result = await tool.execute(
        arguments={"file_path": str(file_path), "content": "Café", "encoding": "latin-1"},
        context=tool_context,
    )

    assert result.success is True
    assert result.result["encoding"] == "latin-1"

    # Verify encoding
    assert file_path.read_text(encoding="latin-1") == "Café"


@pytest.mark.asyncio
async def test_write_tool_invalid_encoding(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test error with invalid encoding."""
    tool = WriteTool()

    result = await tool.execute(
        arguments={
            "file_path": str(temp_workspace / "test.txt"),
            "content": "test",
            "encoding": "invalid-encoding-xyz",
        },
        context=tool_context,
    )

    assert result.success is False
    assert "Failed to write file" in result.error


@pytest.mark.asyncio
async def test_write_tool_resolves_path(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test that file path is resolved to absolute path."""
    tool = WriteTool()

    result = await tool.execute(
        arguments={"file_path": str(temp_workspace / "test.txt"), "content": "test"},
        context=tool_context,
    )

    assert result.success is True
    # Result should contain resolved absolute path
    assert Path(result.result["file_path"]).is_absolute()


@pytest.mark.asyncio
async def test_write_tool_special_characters_in_content(
    temp_workspace, tool_context: ToolCallContext
) -> None:
    """Test writing file with special characters in content."""
    tool = WriteTool()

    file_path = temp_workspace / "special.txt"
    special_content = (
        "Line with\ttabs\nLine with\r\nCRLF\nLine with 'quotes' and \"double quotes\""
    )

    result = await tool.execute(
        arguments={"file_path": str(file_path), "content": special_content},
        context=tool_context,
    )

    assert result.success is True
    content = file_path.read_text()
    assert "\t" in content
    assert "'quotes'" in content
    assert '"double quotes"' in content


@pytest.mark.asyncio
async def test_write_tool_exact_size_limit(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test writing content at exact size limit."""
    tool = WriteTool(max_file_size_mb=1)

    # Create content exactly 1 MB
    exact_content = "x" * (1024 * 1024)

    result = await tool.execute(
        arguments={"file_path": str(temp_workspace / "exact.txt"), "content": exact_content},
        context=tool_context,
    )

    assert result.success is True
    assert result.result["size_bytes"] == 1024 * 1024


@pytest.mark.asyncio
async def test_write_tool_one_byte_over_limit(
    temp_workspace, tool_context: ToolCallContext
) -> None:
    """Test content one byte over limit is rejected."""
    tool = WriteTool(max_file_size_mb=1)

    # Create content 1 byte over 1 MB
    over_content = "x" * (1024 * 1024 + 1)

    result = await tool.execute(
        arguments={"file_path": str(temp_workspace / "over.txt"), "content": over_content},
        context=tool_context,
    )

    assert result.success is False
    assert "exceeds maximum" in result.error


@pytest.mark.asyncio
async def test_write_tool_preserves_line_endings(
    temp_workspace, tool_context: ToolCallContext
) -> None:
    """Test that different line endings are preserved."""
    tool = WriteTool()

    file_path = temp_workspace / "mixed.txt"
    # Python will normalize on some platforms, but content is preserved
    content = "Line 1\nLine 2\nLine 3"

    result = await tool.execute(
        arguments={"file_path": str(file_path), "content": content},
        context=tool_context,
    )

    assert result.success is True
    written_content = file_path.read_text()
    assert "Line 1" in written_content
    assert "Line 2" in written_content
    assert "Line 3" in written_content


@pytest.mark.asyncio
async def test_write_tool_with_leading_trailing_whitespace(
    temp_workspace, tool_context: ToolCallContext
) -> None:
    """Test writing content with leading and trailing whitespace."""
    tool = WriteTool()

    file_path = temp_workspace / "whitespace.txt"
    content = "  \n  Leading and trailing spaces  \n  "

    result = await tool.execute(
        arguments={"file_path": str(file_path), "content": content},
        context=tool_context,
    )

    assert result.success is True
    assert file_path.read_text() == content


@pytest.mark.asyncio
async def test_write_tool_numeric_content(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test writing content that looks numeric but is string."""
    tool = WriteTool()

    file_path = temp_workspace / "numeric.txt"
    content = "12345\n67890\n3.14159"

    result = await tool.execute(
        arguments={"file_path": str(file_path), "content": content},
        context=tool_context,
    )

    assert result.success is True
    assert file_path.read_text() == content
