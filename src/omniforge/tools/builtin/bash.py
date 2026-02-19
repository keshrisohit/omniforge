"""Bash command execution tool for running shell commands and scripts.

This module provides BashTool for executing bash commands, including
Python scripts and other executables, through the unified tool interface.
"""


import asyncio
import subprocess
import time
from pathlib import Path
from typing import Any, Optional

from omniforge.tools.base import (
    BaseTool,
    ParameterType,
    ToolCallContext,
    ToolDefinition,
    ToolParameter,
    ToolResult,
)
from omniforge.tools.types import ToolType


class BashTool(BaseTool):
    """Tool for executing bash commands and scripts.

    Provides command execution through the unified tool interface with:
    - Working directory specification
    - Environment variable support
    - Timeout control
    - stdout/stderr capture
    - Exit code checking

    Example:
        >>> tool = BashTool(timeout_ms=30000)
        >>> context = ToolCallContext(
        ...     correlation_id="corr-1",
        ...     task_id="task-1",
        ...     agent_id="agent-1"
        ... )
        >>> result = await tool.execute(
        ...     arguments={"command": "python script.py", "cwd": "/path/to/skill"},
        ...     context=context
        ... )
        >>> result.success
        True
    """

    def __init__(
        self,
        timeout_ms: int = 30000,
        max_output_size: int = 1_000_000,
    ) -> None:
        """Initialize BashTool.

        Args:
            timeout_ms: Command execution timeout in milliseconds (default: 30s)
            max_output_size: Maximum size of stdout/stderr in bytes (default: 1MB)
        """
        self._timeout_ms = timeout_ms
        self._max_output_size = max_output_size

    @property
    def definition(self) -> ToolDefinition:
        """Get tool definition."""
        return ToolDefinition(
            name="bash",
            type=ToolType.BASH,
            description=(
                "Execute bash commands and scripts. Use for running Python scripts and code, "
                "shell commands, and other executables. Supports working directory "
                "and environment variables."
            ),
            parameters=[
                ToolParameter(
                    name="command",
                    type=ParameterType.STRING,
                    description="Bash command to execute",
                    required=True,
                ),
                ToolParameter(
                    name="cwd",
                    type=ParameterType.STRING,
                    description="Working directory for command execution",
                    required=False,
                ),
                ToolParameter(
                    name="env",
                    type=ParameterType.OBJECT,
                    description="Environment variables (dict of str to str)",
                    required=False,
                ),
            ],
            timeout_ms=self._timeout_ms,
        )

    async def execute(
        self, context: ToolCallContext, arguments: dict[str, Any]
    ) -> ToolResult:
        """Execute bash command.

        Args:
            context: Execution context
            arguments: Tool arguments containing command, cwd, and env

        Returns:
            ToolResult with command output (stdout, stderr, exit_code) or error
        """
        start_time = time.time()

        # Extract arguments
        if isinstance(arguments, str):
            command = arguments
            cwd = None
            env = None
        else:
            # Handle both {"command": "..."} and {"value": "..."} formats
            # The ReActParser wraps string action_input in {"value": ...}
            # Support "Command" (capital C) as suggested in some prompts
            command = (
                arguments.get("command")
                or arguments.get("Command")
                or arguments.get("value", "")
            )
            cwd = arguments.get("cwd")
            env = arguments.get("env")

        if isinstance(command, str):
            command = command.strip()
        else:
            command = str(command).strip() if command else ""

        # Validate command
        if not command:
            return ToolResult(
                success=False,
                error="Command cannot be empty",
                duration_ms=int((time.time() - start_time) * 1000),
            )

        # Validate cwd
        if cwd:
            cwd_path = Path(cwd)
            if not cwd_path.exists():
                return ToolResult(
                    success=False,
                    error=f"Working directory does not exist: {cwd}",
                    duration_ms=int((time.time() - start_time) * 1000),
                )
            if not cwd_path.is_dir():
                return ToolResult(
                    success=False,
                    error=f"Working directory is not a directory: {cwd}",
                    duration_ms=int((time.time() - start_time) * 1000),
                )

        # Validate env
        if env is not None and not isinstance(env, dict):
            return ToolResult(
                success=False,
                error="Environment variables must be a dictionary",
                duration_ms=int((time.time() - start_time) * 1000),
            )

        try:
            # Execute command
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=env,
            )

            # Wait for completion with timeout
            timeout_seconds = self._timeout_ms / 1000
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout_seconds,
                )
            except asyncio.TimeoutError:
                # Kill process if timeout
                process.kill()
                await process.wait()
                return ToolResult(
                    success=False,
                    error=f"Command timed out after {timeout_seconds} seconds",
                    duration_ms=int((time.time() - start_time) * 1000),
                )


            # Decode output
            stdout = stdout_bytes.decode("utf-8", errors="replace")
            stderr = stderr_bytes.decode("utf-8", errors="replace")

            # Truncate if too large
            if len(stdout) > self._max_output_size:
                stdout = (
                    stdout[: self._max_output_size]
                    + f"\n\n[Output truncated at {self._max_output_size} bytes]"
                )
            if len(stderr) > self._max_output_size:
                stderr = (
                    stderr[: self._max_output_size]
                    + f"\n\n[Output truncated at {self._max_output_size} bytes]"
                )

            exit_code = process.returncode
            duration_ms = int((time.time() - start_time) * 1000)

            # Success if exit code is 0
            success = exit_code == 0

            return ToolResult(
                success=success,
                result={
                    "stdout": stdout,
                    "stderr": stderr,
                    "exit_code": exit_code,
                    "command": command,
                    "cwd": cwd,
                },
                error=None if success else f"Command failed with exit code {exit_code}",
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return ToolResult(
                success=False,
                error=f"Command execution failed: {str(e)}",
                duration_ms=duration_ms,
            )


if __name__ == "__main__":
    # Create a test context with required fields
    context = ToolCallContext(
        correlation_id="test-corr-1",
        task_id="test-task-1",
        agent_id="test-agent-1"
    )

    # Fixed command: hanoi call must be outside the function definition
    result = asyncio.run(BashTool().execute(context, {
        "command": 'python -c \'def hanoi(n, source, target, auxiliary):\n    if n > 0:\n        hanoi(n-1, source, auxiliary, target)\n        print(f"Move disk {n} from {source} to {target}")\n        hanoi(n-1, auxiliary, target, source)\nhanoi(3, "A", "C", "B")\''
    }))

    print(f"Success: {result.success}")
    if result.success:
        print(f"Output:\n{result.result['stdout']}")
    else:
        print(f"Error: {result.error}")
