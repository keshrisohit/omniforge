"""Tests for bash command execution tool."""

import sys
import tempfile
from pathlib import Path

import pytest

from omniforge.tools.base import ToolCallContext
from omniforge.tools.builtin.bash import BashTool


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


def test_bash_tool_initialization() -> None:
    """Test BashTool initializes correctly."""
    tool = BashTool(timeout_ms=5000, max_output_size=500000)

    assert tool._timeout_ms == 5000
    assert tool._max_output_size == 500000


def test_bash_tool_default_initialization() -> None:
    """Test BashTool initializes with defaults."""
    tool = BashTool()

    assert tool._timeout_ms == 30000
    assert tool._max_output_size == 1_000_000


def test_bash_tool_definition() -> None:
    """Test BashTool definition."""
    tool = BashTool()
    definition = tool.definition

    assert definition.name == "bash"
    assert definition.type.value == "bash"
    assert definition.timeout_ms == 30000

    # Check parameters
    param_names = [p.name for p in definition.parameters]
    assert "command" in param_names
    assert "cwd" in param_names
    assert "env" in param_names

    # Check required parameters
    command_param = next(p for p in definition.parameters if p.name == "command")
    assert command_param.required is True


@pytest.mark.asyncio
async def test_bash_tool_simple_command(tool_context: ToolCallContext) -> None:
    """Test executing a simple bash command."""
    tool = BashTool()

    result = await tool.execute(
        arguments={"command": "echo 'Hello, World!'"},
        context=tool_context,
    )

    assert result.success is True
    assert "Hello, World!" in result.result["stdout"]
    assert result.result["exit_code"] == 0
    assert result.result["command"] == "echo 'Hello, World!'"
    assert result.duration_ms >= 0


@pytest.mark.asyncio
async def test_bash_tool_command_with_exit_code(tool_context: ToolCallContext) -> None:
    """Test command that returns non-zero exit code."""
    tool = BashTool()

    result = await tool.execute(
        arguments={"command": "exit 1"},
        context=tool_context,
    )

    assert result.success is False
    assert result.result["exit_code"] == 1
    assert "failed with exit code 1" in result.error


@pytest.mark.asyncio
async def test_bash_tool_command_with_stderr(tool_context: ToolCallContext) -> None:
    """Test command that outputs to stderr."""
    tool = BashTool()

    result = await tool.execute(
        arguments={"command": "echo 'error message' >&2"},
        context=tool_context,
    )

    assert result.success is True
    assert "error message" in result.result["stderr"]
    assert result.result["exit_code"] == 0


@pytest.mark.asyncio
async def test_bash_tool_python_command(tool_context: ToolCallContext) -> None:
    """Test executing a Python command."""
    tool = BashTool()

    result = await tool.execute(
        arguments={"command": f"{sys.executable} -c \"print('Python output')\""},
        context=tool_context,
    )

    assert result.success is True
    assert "Python output" in result.result["stdout"]
    assert result.result["exit_code"] == 0


@pytest.mark.asyncio
async def test_bash_tool_with_cwd(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test executing command with working directory."""
    tool = BashTool()

    result = await tool.execute(
        arguments={"command": "pwd", "cwd": str(temp_workspace)},
        context=tool_context,
    )

    assert result.success is True
    assert str(temp_workspace) in result.result["stdout"]
    assert result.result["cwd"] == str(temp_workspace)


@pytest.mark.asyncio
async def test_bash_tool_nonexistent_cwd(tool_context: ToolCallContext) -> None:
    """Test error when working directory does not exist."""
    tool = BashTool()

    result = await tool.execute(
        arguments={"command": "echo test", "cwd": "/nonexistent/directory"},
        context=tool_context,
    )

    assert result.success is False
    assert "does not exist" in result.error


@pytest.mark.asyncio
async def test_bash_tool_cwd_is_file(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test error when cwd is a file instead of directory."""
    tool = BashTool()

    # Create a file
    test_file = temp_workspace / "test.txt"
    test_file.write_text("content")

    result = await tool.execute(
        arguments={"command": "echo test", "cwd": str(test_file)},
        context=tool_context,
    )

    assert result.success is False
    assert "not a directory" in result.error


@pytest.mark.asyncio
async def test_bash_tool_with_env_vars(tool_context: ToolCallContext) -> None:
    """Test executing command with environment variables."""
    tool = BashTool()

    result = await tool.execute(
        arguments={
            "command": "echo $TEST_VAR",
            "env": {"TEST_VAR": "test_value"},
        },
        context=tool_context,
    )

    assert result.success is True
    assert "test_value" in result.result["stdout"]


@pytest.mark.asyncio
async def test_bash_tool_empty_command(tool_context: ToolCallContext) -> None:
    """Test error when command is empty."""
    tool = BashTool()

    result = await tool.execute(
        arguments={"command": ""},
        context=tool_context,
    )

    assert result.success is False
    assert "cannot be empty" in result.error


@pytest.mark.asyncio
async def test_bash_tool_whitespace_command(tool_context: ToolCallContext) -> None:
    """Test error when command is only whitespace."""
    tool = BashTool()

    result = await tool.execute(
        arguments={"command": "   "},
        context=tool_context,
    )

    assert result.success is False
    assert "cannot be empty" in result.error


@pytest.mark.asyncio
async def test_bash_tool_invalid_env_type(tool_context: ToolCallContext) -> None:
    """Test error when env is not a dictionary."""
    tool = BashTool()

    result = await tool.execute(
        arguments={"command": "echo test", "env": "not_a_dict"},
        context=tool_context,
    )

    assert result.success is False
    assert "must be a dictionary" in result.error


@pytest.mark.asyncio
async def test_bash_tool_timeout(tool_context: ToolCallContext) -> None:
    """Test command timeout handling."""
    tool = BashTool(timeout_ms=1000)  # 1 second timeout

    result = await tool.execute(
        arguments={"command": "sleep 5"},
        context=tool_context,
    )

    assert result.success is False
    assert "timed out" in result.error


@pytest.mark.asyncio
async def test_bash_tool_large_output_truncation(tool_context: ToolCallContext) -> None:
    """Test that large output is truncated."""
    tool = BashTool(max_output_size=100)  # 100 bytes

    # Generate output larger than 100 bytes
    result = await tool.execute(
        arguments={"command": f"{sys.executable} -c \"print('x' * 200)\""},
        context=tool_context,
    )

    assert result.success is True
    assert "[Output truncated" in result.result["stdout"]
    assert len(result.result["stdout"]) > 100  # Includes truncation message


@pytest.mark.asyncio
async def test_bash_tool_large_stderr_truncation(tool_context: ToolCallContext) -> None:
    """Test that large stderr is truncated."""
    tool = BashTool(max_output_size=100)

    result = await tool.execute(
        arguments={"command": f"{sys.executable} -c \"import sys; sys.stderr.write('x' * 200)\""},
        context=tool_context,
    )

    assert result.success is True
    assert "[Output truncated" in result.result["stderr"]


@pytest.mark.asyncio
async def test_bash_tool_multiline_output(tool_context: ToolCallContext) -> None:
    """Test command with multiline output."""
    tool = BashTool()

    result = await tool.execute(
        arguments={"command": "echo 'line1'; echo 'line2'; echo 'line3'"},
        context=tool_context,
    )

    assert result.success is True
    assert "line1" in result.result["stdout"]
    assert "line2" in result.result["stdout"]
    assert "line3" in result.result["stdout"]


@pytest.mark.asyncio
async def test_bash_tool_piped_commands(tool_context: ToolCallContext) -> None:
    """Test piped commands."""
    tool = BashTool()

    result = await tool.execute(
        arguments={"command": "echo 'hello world' | grep world"},
        context=tool_context,
    )

    assert result.success is True
    assert "hello world" in result.result["stdout"]


@pytest.mark.asyncio
async def test_bash_tool_command_with_quotes(tool_context: ToolCallContext) -> None:
    """Test command with quoted strings."""
    tool = BashTool()

    result = await tool.execute(
        arguments={"command": "echo \"Hello 'World'\""},
        context=tool_context,
    )

    assert result.success is True
    assert "Hello 'World'" in result.result["stdout"]


@pytest.mark.asyncio
async def test_bash_tool_invalid_command(tool_context: ToolCallContext) -> None:
    """Test executing an invalid command."""
    tool = BashTool()

    result = await tool.execute(
        arguments={"command": "nonexistent_command_xyz123"},
        context=tool_context,
    )

    assert result.success is False
    assert result.result["exit_code"] != 0


@pytest.mark.asyncio
async def test_bash_tool_command_with_special_chars(tool_context: ToolCallContext) -> None:
    """Test command with special characters."""
    tool = BashTool()

    result = await tool.execute(
        arguments={"command": "echo 'Special: @#$%^&*()'"},
        context=tool_context,
    )

    assert result.success is True
    assert "Special: @#$%^&*()" in result.result["stdout"]


@pytest.mark.asyncio
async def test_bash_tool_file_creation(temp_workspace, tool_context: ToolCallContext) -> None:
    """Test creating a file through bash command."""
    tool = BashTool()

    test_file = temp_workspace / "created.txt"

    result = await tool.execute(
        arguments={
            "command": f"echo 'test content' > {test_file}",
            "cwd": str(temp_workspace),
        },
        context=tool_context,
    )

    assert result.success is True
    assert test_file.exists()
    assert test_file.read_text().strip() == "test content"


@pytest.mark.asyncio
async def test_bash_tool_tower_of_hanoi(tool_context: ToolCallContext) -> None:
    """Test Tower of Hanoi program execution and output verification using python -c."""
    tool = BashTool()

    # Execute Tower of Hanoi with 3 disks using python -c
    python_code = """def hanoi(n, source, target, auxiliary):
    if n > 0:
        hanoi(n-1, source, auxiliary, target)
        print(f'Move disk {n} from {source} to {target}')
        hanoi(n-1, auxiliary, target, source)

hanoi(3, 'A', 'C', 'B')"""
    hanoi_command = f'{sys.executable} -c "{python_code}"'

    result = await tool.execute(
        arguments={"command": hanoi_command},
        context=tool_context,
    )

    # Verify execution success
    assert result.success is True
    assert result.result["exit_code"] == 0

    # Verify output is not empty
    stdout = result.result["stdout"]
    assert stdout is not None
    assert len(stdout.strip()) > 0

    # Verify output contains expected moves
    assert "Move disk" in stdout
    assert "from A to" in stdout or "from B to" in stdout

    # Count number of moves (should be 7 for 3 disks: 2^3 - 1 = 7)
    move_lines = [line for line in stdout.strip().split("\n") if "Move disk" in line]
    assert len(move_lines) == 7

    # Verify specific moves in the sequence
    assert "Move disk 1 from A to C" in move_lines[0]  # First move
    assert "Move disk 3 from A to C" in move_lines[3]  # Middle move (largest disk)
    assert "Move disk 1 from A to C" in move_lines[-1]  # Last move


@pytest.mark.asyncio
async def test_bash_tool_tower_of_hanoi_2_disks(tool_context: ToolCallContext) -> None:
    """Test Tower of Hanoi with 2 disks using python -c."""
    tool = BashTool()

    # Execute Tower of Hanoi with 2 disks
    python_code = """def hanoi(n, source, target, auxiliary):
    if n > 0:
        hanoi(n-1, source, auxiliary, target)
        print(f'Move disk {n} from {source} to {target}')
        hanoi(n-1, auxiliary, target, source)

hanoi(2, 'A', 'C', 'B')"""
    hanoi_command = f'{sys.executable} -c "{python_code}"'

    result = await tool.execute(
        arguments={"command": hanoi_command},
        context=tool_context,
    )

    assert result.success is True
    assert result.result["exit_code"] == 0

    stdout = result.result["stdout"]
    move_lines = [line for line in stdout.strip().split("\n") if "Move disk" in line]

    # 2 disks should require 3 moves (2^2 - 1 = 3)
    assert len(move_lines) == 3


@pytest.mark.asyncio
async def test_bash_tool_tower_of_hanoi_4_disks(tool_context: ToolCallContext) -> None:
    """Test Tower of Hanoi with 4 disks using python -c."""
    tool = BashTool()

    # Execute Tower of Hanoi with 4 disks
    python_code = """def hanoi(n, source, target, auxiliary):
    if n > 0:
        hanoi(n-1, source, auxiliary, target)
        print(f'Move disk {n} from {source} to {target}')
        hanoi(n-1, auxiliary, target, source)

hanoi(4, 'A', 'C', 'B')"""
    hanoi_command = f'{sys.executable} -c "{python_code}"'

    result = await tool.execute(
        arguments={"command": hanoi_command},
        context=tool_context,
    )

    assert result.success is True
    assert result.result["exit_code"] == 0

    stdout = result.result["stdout"]
    move_lines = [line for line in stdout.strip().split("\n") if "Move disk" in line]

    # 4 disks should require 15 moves (2^4 - 1 = 15)
    assert len(move_lines) == 15


@pytest.mark.asyncio
async def test_bash_tool_tower_of_hanoi_no_output_on_zero_disks(
    tool_context: ToolCallContext,
) -> None:
    """Test Tower of Hanoi with 0 disks produces no output."""
    tool = BashTool()

    # Execute Tower of Hanoi with 0 disks
    python_code = """def hanoi(n, source, target, auxiliary):
    if n > 0:
        hanoi(n-1, source, auxiliary, target)
        print(f'Move disk {n} from {source} to {target}')
        hanoi(n-1, auxiliary, target, source)

hanoi(0, 'A', 'C', 'B')"""
    hanoi_command = f'{sys.executable} -c "{python_code}"'

    result = await tool.execute(
        arguments={"command": hanoi_command},
        context=tool_context,
    )

    assert result.success is True
    assert result.result["exit_code"] == 0

    stdout = result.result["stdout"]
    # Should produce no output for 0 disks
    assert stdout.strip() == ""

