"""Tests for grep pattern search tool."""

import tempfile
from pathlib import Path

import pytest

from omniforge.tools.base import ToolCallContext
from omniforge.tools.builtin.grep import GrepTool


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
        (workspace / "simple.txt").write_text("Hello, World!\nThis is a test.\nGoodbye, World!")

        (workspace / "log.txt").write_text(
            "INFO: Application started\n"
            "ERROR: Connection failed\n"
            "WARNING: Low memory\n"
            "INFO: Processing data\n"
            "ERROR: Timeout occurred\n"
        )

        (workspace / "code.py").write_text(
            "def hello():\n"
            "    print('Hello')\n"
            "\n"
            "def goodbye():\n"
            "    print('Goodbye')\n"
            "\n"
            "class TestClass:\n"
            "    pass\n"
        )

        (workspace / "empty.txt").write_text("")

        (workspace / "multicase.txt").write_text(
            "Apple\napple\nAPPLE\nOrange\norange\nORANGE\n"
        )

        yield workspace


def test_grep_tool_initialization() -> None:
    """Test GrepTool initializes correctly."""
    tool = GrepTool(max_file_size_mb=5, max_matches=500)

    assert tool._max_file_size_bytes == 5 * 1024 * 1024
    assert tool._max_matches == 500


def test_grep_tool_default_initialization() -> None:
    """Test GrepTool initializes with defaults."""
    tool = GrepTool()

    assert tool._max_file_size_bytes == 10 * 1024 * 1024
    assert tool._max_matches == 1000


def test_grep_tool_definition() -> None:
    """Test GrepTool definition."""
    tool = GrepTool()
    definition = tool.definition

    assert definition.name == "grep"
    assert definition.type.value == "grep"
    assert definition.timeout_ms == 30000

    # Check parameters
    param_names = [p.name for p in definition.parameters]
    assert "pattern" in param_names
    assert "file_path" in param_names
    assert "case_insensitive" in param_names
    assert "context_lines" in param_names

    # Check required parameters
    pattern_param = next(p for p in definition.parameters if p.name == "pattern")
    assert pattern_param.required is True

    file_path_param = next(p for p in definition.parameters if p.name == "file_path")
    assert file_path_param.required is True


@pytest.mark.asyncio
async def test_grep_tool_simple_match(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test simple pattern matching."""
    tool = GrepTool()

    result = await tool.execute(
        arguments={"pattern": "World", "file_path": str(temp_workspace / "simple.txt")},
        context=tool_context,
    )

    assert result.success is True
    assert result.result["match_count"] == 2
    assert len(result.result["matches"]) == 2
    assert result.result["truncated"] is False

    # Check matches
    lines = [m["line"] for m in result.result["matches"]]
    assert "Hello, World!" in lines
    assert "Goodbye, World!" in lines


@pytest.mark.asyncio
async def test_grep_tool_regex_pattern(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test regular expression pattern."""
    tool = GrepTool()

    result = await tool.execute(
        arguments={"pattern": "ERROR:.*", "file_path": str(temp_workspace / "log.txt")},
        context=tool_context,
    )

    assert result.success is True
    assert result.result["match_count"] == 2
    lines = [m["line"] for m in result.result["matches"]]
    assert "ERROR: Connection failed" in lines
    assert "ERROR: Timeout occurred" in lines


@pytest.mark.asyncio
async def test_grep_tool_case_sensitive(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test case-sensitive matching (default)."""
    tool = GrepTool()

    result = await tool.execute(
        arguments={
            "pattern": "apple",
            "file_path": str(temp_workspace / "multicase.txt"),
            "case_insensitive": False,
        },
        context=tool_context,
    )

    assert result.success is True
    assert result.result["match_count"] == 1
    assert result.result["matches"][0]["line"] == "apple"


@pytest.mark.asyncio
async def test_grep_tool_case_insensitive(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test case-insensitive matching."""
    tool = GrepTool()

    result = await tool.execute(
        arguments={
            "pattern": "apple",
            "file_path": str(temp_workspace / "multicase.txt"),
            "case_insensitive": True,
        },
        context=tool_context,
    )

    assert result.success is True
    assert result.result["match_count"] == 3
    lines = [m["line"] for m in result.result["matches"]]
    assert "Apple" in lines
    assert "apple" in lines
    assert "APPLE" in lines


@pytest.mark.asyncio
async def test_grep_tool_no_matches(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test when pattern has no matches."""
    tool = GrepTool()

    result = await tool.execute(
        arguments={"pattern": "NONEXISTENT", "file_path": str(temp_workspace / "simple.txt")},
        context=tool_context,
    )

    assert result.success is True
    assert result.result["match_count"] == 0
    assert len(result.result["matches"]) == 0


@pytest.mark.asyncio
async def test_grep_tool_empty_file(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test searching in empty file."""
    tool = GrepTool()

    result = await tool.execute(
        arguments={"pattern": "test", "file_path": str(temp_workspace / "empty.txt")},
        context=tool_context,
    )

    assert result.success is True
    assert result.result["match_count"] == 0


@pytest.mark.asyncio
async def test_grep_tool_line_numbers(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test that line numbers are correctly tracked."""
    tool = GrepTool()

    result = await tool.execute(
        arguments={"pattern": "def", "file_path": str(temp_workspace / "code.py")},
        context=tool_context,
    )

    assert result.success is True
    assert result.result["match_count"] == 2

    # Check line numbers
    line_numbers = [m["line_number"] for m in result.result["matches"]]
    assert 1 in line_numbers  # def hello()
    assert 4 in line_numbers  # def goodbye()


@pytest.mark.asyncio
async def test_grep_tool_context_lines(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test context lines before and after match."""
    tool = GrepTool()

    result = await tool.execute(
        arguments={
            "pattern": "ERROR",
            "file_path": str(temp_workspace / "log.txt"),
            "context_lines": 1,
        },
        context=tool_context,
    )

    assert result.success is True
    assert result.result["match_count"] == 2

    # Check first match has context
    first_match = result.result["matches"][0]
    assert len(first_match["context_before"]) == 1
    assert len(first_match["context_after"]) == 1
    assert first_match["context_before"][0]["line"] == "INFO: Application started"
    assert first_match["context_after"][0]["line"] == "WARNING: Low memory"


@pytest.mark.asyncio
async def test_grep_tool_context_at_file_boundaries(
    temp_workspace, tool_context: ToolCallContext
) -> None:
    """Test context lines at start and end of file."""
    tool = GrepTool()

    result = await tool.execute(
        arguments={
            "pattern": "Application started",
            "file_path": str(temp_workspace / "log.txt"),
            "context_lines": 1,
        },
        context=tool_context,
    )

    assert result.success is True
    first_match = result.result["matches"][0]
    # First line should have no context before
    assert len(first_match["context_before"]) == 0
    # Should have context after
    assert len(first_match["context_after"]) == 1


@pytest.mark.asyncio
async def test_grep_tool_empty_pattern(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test error when pattern is empty."""
    tool = GrepTool()

    result = await tool.execute(
        arguments={"pattern": "", "file_path": str(temp_workspace / "simple.txt")},
        context=tool_context,
    )

    assert result.success is False
    assert "cannot be empty" in result.error


@pytest.mark.asyncio
async def test_grep_tool_empty_file_path(tool_context: ToolCallContext) -> None:
    """Test error when file_path is empty."""
    tool = GrepTool()

    result = await tool.execute(
        arguments={"pattern": "test", "file_path": ""},
        context=tool_context,
    )

    assert result.success is False
    assert "cannot be empty" in result.error


@pytest.mark.asyncio
async def test_grep_tool_invalid_regex(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test error with invalid regular expression."""
    tool = GrepTool()

    result = await tool.execute(
        arguments={"pattern": "[invalid(regex", "file_path": str(temp_workspace / "simple.txt")},
        context=tool_context,
    )

    assert result.success is False
    assert "Invalid regular expression" in result.error


@pytest.mark.asyncio
async def test_grep_tool_nonexistent_file(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test error when file does not exist."""
    tool = GrepTool()

    result = await tool.execute(
        arguments={"pattern": "test", "file_path": str(temp_workspace / "nonexistent.txt")},
        context=tool_context,
    )

    assert result.success is False
    assert "not found" in result.error.lower()


@pytest.mark.asyncio
async def test_grep_tool_directory_as_file(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test error when trying to search a directory."""
    tool = GrepTool()

    subdir = temp_workspace / "subdir"
    subdir.mkdir()

    result = await tool.execute(
        arguments={"pattern": "test", "file_path": str(subdir)},
        context=tool_context,
    )

    assert result.success is False
    assert "not a file" in result.error.lower()


@pytest.mark.asyncio
async def test_grep_tool_file_size_limit(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test file size limit is enforced."""
    tool = GrepTool(max_file_size_mb=1)

    # Create file larger than 1 MB
    large_file = temp_workspace / "large.txt"
    large_file.write_text("x" * (2 * 1024 * 1024))

    result = await tool.execute(
        arguments={"pattern": "x", "file_path": str(large_file)},
        context=tool_context,
    )

    assert result.success is False
    assert "exceeds maximum" in result.error


@pytest.mark.asyncio
async def test_grep_tool_max_matches_limit(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test max matches limit is enforced."""
    tool = GrepTool(max_matches=5)

    # Create file with many matches
    many_matches_file = temp_workspace / "many.txt"
    many_matches_file.write_text("\n".join([f"match line {i}" for i in range(100)]))

    result = await tool.execute(
        arguments={"pattern": "match", "file_path": str(many_matches_file)},
        context=tool_context,
    )

    assert result.success is True
    assert result.result["match_count"] <= 5
    assert result.result["truncated"] is True


@pytest.mark.asyncio
async def test_grep_tool_special_regex_chars(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test pattern with special regex characters."""
    tool = GrepTool()

    special_file = temp_workspace / "special.txt"
    special_file.write_text("Price: $100\nEmail: test@example.com\nPath: /usr/bin")

    result = await tool.execute(
        arguments={"pattern": r"\$\d+", "file_path": str(special_file)},
        context=tool_context,
    )

    assert result.success is True
    assert result.result["match_count"] == 1
    assert "$100" in result.result["matches"][0]["line"]


@pytest.mark.asyncio
async def test_grep_tool_word_boundary(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test word boundary matching."""
    tool = GrepTool()

    word_file = temp_workspace / "words.txt"
    word_file.write_text("test\ntesting\ncontest\nunittest")

    # Match only "test" as a whole word
    result = await tool.execute(
        arguments={"pattern": r"\btest\b", "file_path": str(word_file)},
        context=tool_context,
    )

    assert result.success is True
    assert result.result["match_count"] == 1
    assert result.result["matches"][0]["line"] == "test"


@pytest.mark.asyncio
async def test_grep_tool_multiline_pattern_per_line(
    temp_workspace, tool_context: ToolCallContext
) -> None:
    """Test that patterns match within lines."""
    tool = GrepTool()

    result = await tool.execute(
        arguments={"pattern": ".*World.*", "file_path": str(temp_workspace / "simple.txt")},
        context=tool_context,
    )

    assert result.success is True
    assert result.result["match_count"] == 2


@pytest.mark.asyncio
async def test_grep_tool_unicode_pattern(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test pattern with unicode characters."""
    tool = GrepTool()

    unicode_file = temp_workspace / "unicode.txt"
    unicode_file.write_text("Café ☕\nTea 🍵\nCoffee ☕")

    result = await tool.execute(
        arguments={"pattern": "☕", "file_path": str(unicode_file)},
        context=tool_context,
    )

    assert result.success is True
    assert result.result["match_count"] == 2


@pytest.mark.asyncio
async def test_grep_tool_result_structure(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test that result has correct structure."""
    tool = GrepTool()

    result = await tool.execute(
        arguments={"pattern": "World", "file_path": str(temp_workspace / "simple.txt")},
        context=tool_context,
    )

    assert result.success is True
    assert "matches" in result.result
    assert "match_count" in result.result
    assert "truncated" in result.result
    assert "file_path" in result.result
    assert "pattern" in result.result

    # Check match structure
    match = result.result["matches"][0]
    assert "line_number" in match
    assert "line" in match
    assert "context_before" in match
    assert "context_after" in match
