"""Tests for bash_tool_actions example."""

import tempfile
from pathlib import Path

import pytest

from examples.bash_tool_actions import BashActionExecutor
from omniforge.tools.base import ToolCallContext


@pytest.fixture
def executor() -> BashActionExecutor:
    """Create BashActionExecutor for tests."""
    return BashActionExecutor(timeout_ms=10000)


@pytest.fixture
def context() -> ToolCallContext:
    """Create test context."""
    return ToolCallContext(
        correlation_id="test-corr-123", task_id="test-task-123", agent_id="test-agent-456"
    )


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.mark.asyncio
async def test_echo_action(executor: BashActionExecutor, context: ToolCallContext) -> None:
    """Test echo action."""
    result = await executor.execute_action(
        action="echo", input_data={"message": "Hello World"}, context=context
    )

    assert result["success"] is True
    assert result["action"] == "echo"
    assert "Hello World" in result["output"]
    assert result["exit_code"] == 0
    assert result["error"] is None


@pytest.mark.asyncio
async def test_echo_action_with_special_chars(
    executor: BashActionExecutor, context: ToolCallContext
) -> None:
    """Test echo action with special characters."""
    result = await executor.execute_action(
        action="echo", input_data={"message": "Special chars: @#$%"}, context=context
    )

    assert result["success"] is True
    assert "Special chars: @#$%" in result["output"]


@pytest.mark.asyncio
async def test_list_files_action(
    executor: BashActionExecutor, context: ToolCallContext, temp_dir: Path
) -> None:
    """Test list_files action."""
    # Create some test files
    (temp_dir / "file1.txt").write_text("content1")
    (temp_dir / "file2.txt").write_text("content2")
    (temp_dir / "file3.py").write_text("print('hello')")

    result = await executor.execute_action(
        action="list_files",
        input_data={"directory": str(temp_dir), "pattern": "*.txt"},
        context=context,
    )

    assert result["success"] is True
    assert "file1.txt" in result["output"]
    assert "file2.txt" in result["output"]
    assert "file3.py" not in result["output"]  # Should not match *.txt pattern


@pytest.mark.asyncio
async def test_create_file_action(
    executor: BashActionExecutor, context: ToolCallContext, temp_dir: Path
) -> None:
    """Test create_file action."""
    test_file = temp_dir / "created.txt"

    result = await executor.execute_action(
        action="create_file",
        input_data={"filepath": str(test_file), "content": "Test content"},
        context=context,
    )

    assert result["success"] is True
    assert test_file.exists()
    assert test_file.read_text().strip() == "Test content"


@pytest.mark.asyncio
async def test_create_file_with_multiline_content(
    executor: BashActionExecutor, context: ToolCallContext, temp_dir: Path
) -> None:
    """Test create_file action with multiline content."""
    test_file = temp_dir / "multiline.txt"
    content = "Line 1\nLine 2\nLine 3"

    result = await executor.execute_action(
        action="create_file", input_data={"filepath": str(test_file), "content": content}, context=context
    )

    assert result["success"] is True
    assert test_file.exists()


@pytest.mark.asyncio
async def test_read_file_action(
    executor: BashActionExecutor, context: ToolCallContext, temp_dir: Path
) -> None:
    """Test read_file action."""
    test_file = temp_dir / "read_test.txt"
    test_file.write_text("Content to read")

    result = await executor.execute_action(
        action="read_file", input_data={"filepath": str(test_file)}, context=context
    )

    assert result["success"] is True
    assert "Content to read" in result["output"]


@pytest.mark.asyncio
async def test_read_nonexistent_file(
    executor: BashActionExecutor, context: ToolCallContext, temp_dir: Path
) -> None:
    """Test read_file action with nonexistent file."""
    result = await executor.execute_action(
        action="read_file", input_data={"filepath": str(temp_dir / "nonexistent.txt")}, context=context
    )

    assert result["success"] is False
    assert result["exit_code"] != 0


@pytest.mark.asyncio
async def test_delete_file_action(
    executor: BashActionExecutor, context: ToolCallContext, temp_dir: Path
) -> None:
    """Test delete_file action."""
    test_file = temp_dir / "to_delete.txt"
    test_file.write_text("Will be deleted")

    assert test_file.exists()

    result = await executor.execute_action(
        action="delete_file", input_data={"filepath": str(test_file)}, context=context
    )

    assert result["success"] is True
    assert not test_file.exists()


@pytest.mark.asyncio
async def test_run_python_action(executor: BashActionExecutor, context: ToolCallContext) -> None:
    """Test run_python action."""
    result = await executor.execute_action(
        action="run_python", input_data={"code": "print('Python output: 2+2 =', 2+2)"}, context=context
    )

    assert result["success"] is True
    assert "Python output: 2+2 = 4" in result["output"]


@pytest.mark.asyncio
async def test_run_python_with_imports(
    executor: BashActionExecutor, context: ToolCallContext
) -> None:
    """Test run_python action with imports."""
    code = "import sys; print(f'Python version: {sys.version_info.major}.{sys.version_info.minor}')"

    result = await executor.execute_action(
        action="run_python", input_data={"code": code}, context=context
    )

    assert result["success"] is True
    assert "Python version:" in result["output"]


@pytest.mark.asyncio
async def test_run_python_with_error(
    executor: BashActionExecutor, context: ToolCallContext
) -> None:
    """Test run_python action with code that raises error."""
    result = await executor.execute_action(
        action="run_python", input_data={"code": "raise ValueError('Test error')"}, context=context
    )

    assert result["success"] is False
    assert result["exit_code"] != 0
    assert "ValueError" in result["error_output"]


@pytest.mark.asyncio
async def test_unsupported_action(executor: BashActionExecutor, context: ToolCallContext) -> None:
    """Test error with unsupported action."""
    with pytest.raises(ValueError, match="Unsupported action"):
        await executor.execute_action(
            action="invalid_action", input_data={}, context=context
        )


@pytest.mark.asyncio
async def test_create_file_missing_filepath(
    executor: BashActionExecutor, context: ToolCallContext
) -> None:
    """Test create_file action without filepath."""
    with pytest.raises(ValueError, match="filepath is required"):
        await executor.execute_action(
            action="create_file", input_data={"content": "test"}, context=context
        )


@pytest.mark.asyncio
async def test_read_file_missing_filepath(
    executor: BashActionExecutor, context: ToolCallContext
) -> None:
    """Test read_file action without filepath."""
    with pytest.raises(ValueError, match="filepath is required"):
        await executor.execute_action(action="read_file", input_data={}, context=context)


@pytest.mark.asyncio
async def test_delete_file_missing_filepath(
    executor: BashActionExecutor, context: ToolCallContext
) -> None:
    """Test delete_file action without filepath."""
    with pytest.raises(ValueError, match="filepath is required"):
        await executor.execute_action(action="delete_file", input_data={}, context=context)


@pytest.mark.asyncio
async def test_run_python_missing_code(
    executor: BashActionExecutor, context: ToolCallContext
) -> None:
    """Test run_python action without code."""
    with pytest.raises(ValueError, match="code is required"):
        await executor.execute_action(action="run_python", input_data={}, context=context)


@pytest.mark.asyncio
async def test_action_with_cwd(
    executor: BashActionExecutor, context: ToolCallContext, temp_dir: Path
) -> None:
    """Test action with custom working directory."""
    # Create file in temp directory
    test_file = temp_dir / "cwd_test.txt"

    result = await executor.execute_action(
        action="create_file",
        input_data={"filepath": "cwd_test.txt", "content": "CWD test", "cwd": str(temp_dir)},
        context=context,
    )

    assert result["success"] is True
    assert test_file.exists()


@pytest.mark.asyncio
async def test_run_python_with_env_vars(
    executor: BashActionExecutor, context: ToolCallContext
) -> None:
    """Test run_python action with environment variables."""
    code = "import os; print(f\"VAR={os.environ.get('TEST_VAR', 'not found')}\")"

    result = await executor.execute_action(
        action="run_python",
        input_data={"code": code, "env": {"TEST_VAR": "test_value"}},
        context=context,
    )

    assert result["success"] is True
    assert "VAR=test_value" in result["output"]


@pytest.mark.asyncio
async def test_result_structure(executor: BashActionExecutor, context: ToolCallContext) -> None:
    """Test that result has correct structure."""
    result = await executor.execute_action(
        action="echo", input_data={"message": "test"}, context=context
    )

    # Check all expected keys
    assert "action" in result
    assert "input" in result
    assert "success" in result
    assert "output" in result
    assert "error_output" in result
    assert "exit_code" in result
    assert "error" in result
    assert "duration_ms" in result

    # Check types
    assert isinstance(result["action"], str)
    assert isinstance(result["input"], dict)
    assert isinstance(result["success"], bool)
    assert isinstance(result["duration_ms"], int)
