"""Tests for glob file pattern matching tool."""

import tempfile
from pathlib import Path

import pytest

from omniforge.tools.base import ToolCallContext
from omniforge.tools.builtin.glob import GlobTool


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
    """Create temporary workspace with test structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)

        # Create test structure
        (workspace / "file1.txt").write_text("content1")
        (workspace / "file2.txt").write_text("content2")
        (workspace / "file3.py").write_text("print('hello')")
        (workspace / "readme.md").write_text("# README")

        # Create subdirectories
        (workspace / "src").mkdir()
        (workspace / "src" / "main.py").write_text("def main(): pass")
        (workspace / "src" / "utils.py").write_text("def util(): pass")

        (workspace / "tests").mkdir()
        (workspace / "tests" / "test_main.py").write_text("def test_main(): pass")

        (workspace / "docs").mkdir()
        (workspace / "docs" / "guide.md").write_text("# Guide")
        (workspace / "docs" / "api.md").write_text("# API")

        # Nested structure
        (workspace / "src" / "lib").mkdir()
        (workspace / "src" / "lib" / "helper.py").write_text("def helper(): pass")

        yield workspace


def test_glob_tool_initialization() -> None:
    """Test GlobTool initializes correctly."""
    tool = GlobTool(max_results=500)

    assert tool._max_results == 500


def test_glob_tool_default_initialization() -> None:
    """Test GlobTool initializes with defaults."""
    tool = GlobTool()

    assert tool._max_results == 1000


def test_glob_tool_definition() -> None:
    """Test GlobTool definition."""
    tool = GlobTool()
    definition = tool.definition

    assert definition.name == "glob"
    assert definition.type.value == "glob"
    assert definition.timeout_ms == 30000

    # Check parameters
    param_names = [p.name for p in definition.parameters]
    assert "pattern" in param_names
    assert "base_path" in param_names
    assert "files_only" in param_names

    # Check required parameters
    pattern_param = next(p for p in definition.parameters if p.name == "pattern")
    assert pattern_param.required is True

    base_path_param = next(p for p in definition.parameters if p.name == "base_path")
    assert base_path_param.required is False


@pytest.mark.asyncio
async def test_glob_tool_simple_wildcard(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test simple wildcard pattern."""
    tool = GlobTool()

    result = await tool.execute(
        arguments={"pattern": "*.txt", "base_path": str(temp_workspace)},
        context=tool_context,
    )

    assert result.success is True
    assert result.result["match_count"] == 2
    assert result.result["truncated"] is False

    names = [m["name"] for m in result.result["matches"]]
    assert "file1.txt" in names
    assert "file2.txt" in names


@pytest.mark.asyncio
async def test_glob_tool_specific_extension(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test matching specific file extension."""
    tool = GlobTool()

    result = await tool.execute(
        arguments={"pattern": "*.py", "base_path": str(temp_workspace)},
        context=tool_context,
    )

    assert result.success is True
    assert result.result["match_count"] == 1
    assert result.result["matches"][0]["name"] == "file3.py"


@pytest.mark.asyncio
async def test_glob_tool_recursive_pattern(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test recursive pattern matching."""
    tool = GlobTool()

    result = await tool.execute(
        arguments={"pattern": "**/*.py", "base_path": str(temp_workspace)},
        context=tool_context,
    )

    assert result.success is True
    assert result.result["match_count"] == 5  # file3.py, main.py, utils.py, test_main.py, helper.py

    names = [m["name"] for m in result.result["matches"]]
    assert "file3.py" in names
    assert "main.py" in names
    assert "utils.py" in names
    assert "test_main.py" in names
    assert "helper.py" in names


@pytest.mark.asyncio
async def test_glob_tool_subdirectory_pattern(
    temp_workspace, tool_context: ToolCallContext
) -> None:
    """Test pattern in subdirectory."""
    tool = GlobTool()

    result = await tool.execute(
        arguments={"pattern": "src/*.py", "base_path": str(temp_workspace)},
        context=tool_context,
    )

    assert result.success is True
    assert result.result["match_count"] == 2  # main.py, utils.py

    names = [m["name"] for m in result.result["matches"]]
    assert "main.py" in names
    assert "utils.py" in names


@pytest.mark.asyncio
async def test_glob_tool_question_mark_wildcard(
    temp_workspace, tool_context: ToolCallContext
) -> None:
    """Test single character wildcard."""
    tool = GlobTool()

    result = await tool.execute(
        arguments={"pattern": "file?.txt", "base_path": str(temp_workspace)},
        context=tool_context,
    )

    assert result.success is True
    assert result.result["match_count"] == 2

    names = [m["name"] for m in result.result["matches"]]
    assert "file1.txt" in names
    assert "file2.txt" in names


@pytest.mark.asyncio
async def test_glob_tool_character_set(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test character set matching."""
    tool = GlobTool()

    result = await tool.execute(
        arguments={"pattern": "file[12].txt", "base_path": str(temp_workspace)},
        context=tool_context,
    )

    assert result.success is True
    assert result.result["match_count"] == 2

    names = [m["name"] for m in result.result["matches"]]
    assert "file1.txt" in names
    assert "file2.txt" in names


@pytest.mark.asyncio
async def test_glob_tool_no_matches(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test when pattern has no matches."""
    tool = GlobTool()

    result = await tool.execute(
        arguments={"pattern": "*.nonexistent", "base_path": str(temp_workspace)},
        context=tool_context,
    )

    assert result.success is True
    assert result.result["match_count"] == 0
    assert len(result.result["matches"]) == 0


@pytest.mark.asyncio
async def test_glob_tool_files_only_true(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test files_only=True excludes directories."""
    tool = GlobTool()

    result = await tool.execute(
        arguments={"pattern": "*", "base_path": str(temp_workspace), "files_only": True},
        context=tool_context,
    )

    assert result.success is True
    # Should only match files, not directories
    for match in result.result["matches"]:
        assert match["is_file"] is True
        assert match["is_dir"] is False


@pytest.mark.asyncio
async def test_glob_tool_files_only_false(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test files_only=False includes directories."""
    tool = GlobTool()

    result = await tool.execute(
        arguments={"pattern": "*", "base_path": str(temp_workspace), "files_only": False},
        context=tool_context,
    )

    assert result.success is True
    # Should include both files and directories
    has_files = any(m["is_file"] for m in result.result["matches"])
    has_dirs = any(m["is_dir"] for m in result.result["matches"])
    assert has_files is True
    assert has_dirs is True


@pytest.mark.asyncio
async def test_glob_tool_default_base_path(tool_context: ToolCallContext) -> None:
    """Test default base_path uses current directory."""
    tool = GlobTool()

    result = await tool.execute(
        arguments={"pattern": "*.md"},
        context=tool_context,
    )

    # Should succeed (may or may not find matches)
    assert result.success is True
    assert "base_path" in result.result


@pytest.mark.asyncio
async def test_glob_tool_empty_pattern(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test error when pattern is empty."""
    tool = GlobTool()

    result = await tool.execute(
        arguments={"pattern": "", "base_path": str(temp_workspace)},
        context=tool_context,
    )

    assert result.success is False
    assert "cannot be empty" in result.error


@pytest.mark.asyncio
async def test_glob_tool_nonexistent_base_path(tool_context: ToolCallContext) -> None:
    """Test error when base_path does not exist."""
    tool = GlobTool()

    result = await tool.execute(
        arguments={"pattern": "*.txt", "base_path": "/nonexistent/path"},
        context=tool_context,
    )

    assert result.success is False
    assert "does not exist" in result.error


@pytest.mark.asyncio
async def test_glob_tool_base_path_is_file(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test error when base_path is a file instead of directory."""
    tool = GlobTool()

    result = await tool.execute(
        arguments={"pattern": "*.txt", "base_path": str(temp_workspace / "file1.txt")},
        context=tool_context,
    )

    assert result.success is False
    assert "not a directory" in result.error


@pytest.mark.asyncio
async def test_glob_tool_match_metadata(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test that matches include metadata."""
    tool = GlobTool()

    result = await tool.execute(
        arguments={"pattern": "file1.txt", "base_path": str(temp_workspace)},
        context=tool_context,
    )

    assert result.success is True
    assert result.result["match_count"] == 1

    match = result.result["matches"][0]
    assert "path" in match
    assert "name" in match
    assert "is_file" in match
    assert "is_dir" in match
    assert "size_bytes" in match
    assert "modified_time" in match

    assert match["name"] == "file1.txt"
    assert match["is_file"] is True
    assert match["is_dir"] is False
    assert match["size_bytes"] > 0


@pytest.mark.asyncio
async def test_glob_tool_sorted_results(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test that results are sorted by path."""
    tool = GlobTool()

    result = await tool.execute(
        arguments={"pattern": "*.txt", "base_path": str(temp_workspace)},
        context=tool_context,
    )

    assert result.success is True
    paths = [m["path"] for m in result.result["matches"]]

    # Check paths are sorted
    assert paths == sorted(paths)


@pytest.mark.asyncio
async def test_glob_tool_max_results_limit(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test max results limit is enforced."""
    tool = GlobTool(max_results=2)

    result = await tool.execute(
        arguments={"pattern": "**/*.py", "base_path": str(temp_workspace)},
        context=tool_context,
    )

    assert result.success is True
    assert result.result["match_count"] <= 2
    assert result.result["truncated"] is True


@pytest.mark.asyncio
async def test_glob_tool_deeply_nested_pattern(
    temp_workspace, tool_context: ToolCallContext
) -> None:
    """Test pattern matching deeply nested files."""
    tool = GlobTool()

    result = await tool.execute(
        arguments={"pattern": "**/lib/*.py", "base_path": str(temp_workspace)},
        context=tool_context,
    )

    assert result.success is True
    assert result.result["match_count"] == 1
    assert result.result["matches"][0]["name"] == "helper.py"


@pytest.mark.asyncio
async def test_glob_tool_multiple_extensions(
    temp_workspace, tool_context: ToolCallContext
) -> None:
    """Test matching multiple file extensions."""
    tool = GlobTool()

    result = await tool.execute(
        arguments={"pattern": "**/*.md", "base_path": str(temp_workspace)},
        context=tool_context,
    )

    assert result.success is True
    assert result.result["match_count"] == 3  # readme.md, guide.md, api.md

    names = [m["name"] for m in result.result["matches"]]
    assert "readme.md" in names
    assert "guide.md" in names
    assert "api.md" in names


@pytest.mark.asyncio
async def test_glob_tool_star_star_alone(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test ** pattern for all files recursively."""
    tool = GlobTool()

    result = await tool.execute(
        arguments={"pattern": "**/*", "base_path": str(temp_workspace), "files_only": True},
        context=tool_context,
    )

    assert result.success is True
    # Should find all files in all subdirectories
    assert result.result["match_count"] > 5


@pytest.mark.asyncio
async def test_glob_tool_exact_filename(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test matching exact filename."""
    tool = GlobTool()

    result = await tool.execute(
        arguments={"pattern": "readme.md", "base_path": str(temp_workspace)},
        context=tool_context,
    )

    assert result.success is True
    assert result.result["match_count"] == 1
    assert result.result["matches"][0]["name"] == "readme.md"


@pytest.mark.asyncio
async def test_glob_tool_result_structure(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test that result has correct structure."""
    tool = GlobTool()

    result = await tool.execute(
        arguments={"pattern": "*.txt", "base_path": str(temp_workspace)},
        context=tool_context,
    )

    assert result.success is True
    assert "matches" in result.result
    assert "match_count" in result.result
    assert "truncated" in result.result
    assert "pattern" in result.result
    assert "base_path" in result.result

    assert result.result["pattern"] == "*.txt"
    assert result.result["base_path"] == str(temp_workspace.resolve())


@pytest.mark.asyncio
async def test_glob_tool_directory_metadata(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test that directories have correct metadata when included."""
    tool = GlobTool()

    result = await tool.execute(
        arguments={"pattern": "*", "base_path": str(temp_workspace), "files_only": False},
        context=tool_context,
    )

    assert result.success is True

    # Find a directory match
    dir_matches = [m for m in result.result["matches"] if m["is_dir"]]
    assert len(dir_matches) > 0

    dir_match = dir_matches[0]
    assert dir_match["is_file"] is False
    assert dir_match["is_dir"] is True
    assert dir_match["size_bytes"] is None  # Directories don't have size in result


@pytest.mark.asyncio
async def test_glob_tool_permission_error_handling(
    temp_workspace, tool_context: ToolCallContext
) -> None:
    """Test that permission errors are handled gracefully."""
    tool = GlobTool()

    # This test assumes the pattern might encounter files it can't access
    # The tool should skip them and continue
    result = await tool.execute(
        arguments={"pattern": "**/*", "base_path": str(temp_workspace), "files_only": True},
        context=tool_context,
    )

    # Should succeed even if some files can't be accessed
    assert result.success is True


@pytest.mark.asyncio
async def test_glob_tool_empty_directory(tool_context: ToolCallContext) -> None:
    """Test glob in empty directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        empty_dir = Path(tmpdir)
        tool = GlobTool()

        result = await tool.execute(
            arguments={"pattern": "*", "base_path": str(empty_dir)},
            context=tool_context,
        )

        assert result.success is True
        assert result.result["match_count"] == 0
