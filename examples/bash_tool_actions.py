"""Action-based interface for BashTool.

This module provides a high-level, action-based wrapper around the BashTool
that simplifies common bash operations by providing predefined actions like
'echo', 'create_file', 'run_python', etc.
"""

import asyncio
from typing import Any, Optional

from omniforge.tools.base import ToolCallContext
from omniforge.tools.builtin.bash import BashTool


class BashActionExecutor:
    """Action-based executor for bash commands.

    Provides a simplified interface for common bash operations through
    predefined actions instead of raw bash commands.
    """

    def __init__(self, timeout_ms: int = 30000) -> None:
        """Initialize BashActionExecutor.

        Args:
            timeout_ms: Command execution timeout in milliseconds
        """
        self.bash_tool = BashTool(timeout_ms=timeout_ms)

    async def execute_action(
        self,
        action: str,
        input_data: dict[str, Any],
        context: ToolCallContext,
    ) -> dict[str, Any]:
        """Execute a predefined action.

        Args:
            action: The action to execute (e.g., 'echo', 'create_file')
            input_data: Action-specific input parameters
            context: Tool execution context

        Returns:
            Dictionary with execution results

        Raises:
            ValueError: If action is not supported or required parameters are missing
        """
        action_handlers = {
            "echo": self._echo_action,
            "list_files": self._list_files_action,
            "create_file": self._create_file_action,
            "read_file": self._read_file_action,
            "delete_file": self._delete_file_action,
            "run_python": self._run_python_action,
        }

        if action not in action_handlers:
            raise ValueError(f"Unsupported action: {action}")

        handler = action_handlers[action]
        command, cwd, env = handler(input_data)

        arguments = {"command": command}
        if cwd:
            arguments["cwd"] = cwd
        if env:
            arguments["env"] = env

        tool_result = await self.bash_tool.execute(arguments=arguments, context=context)

        result = {
            "action": action,
            "input": input_data,
            "success": tool_result.success,
            "output": "",
            "error_output": "",
            "exit_code": 0,
            "error": tool_result.error,
            "duration_ms": tool_result.duration_ms,
        }

        if tool_result.result:
            result["output"] = tool_result.result.get("stdout", "")
            result["error_output"] = tool_result.result.get("stderr", "")
            result["exit_code"] = tool_result.result.get("exit_code", 0)

        return result

    def _echo_action(self, input_data: dict) -> tuple[str, Optional[str], Optional[dict]]:
        """Generate command for echo action."""
        message = input_data.get("message", "")
        command = f"printf '%s\\n' {self._shell_quote(message)}"
        cwd = input_data.get("cwd")
        env = input_data.get("env")
        return command, cwd, env

    def _list_files_action(self, input_data: dict) -> tuple[str, Optional[str], Optional[dict]]:
        """Generate command for list_files action."""
        directory = input_data.get("directory", ".")
        pattern = input_data.get("pattern", "*")
        command = f"ls -1 {self._shell_quote(directory)}/{pattern}"
        cwd = input_data.get("cwd")
        env = input_data.get("env")
        return command, cwd, env

    def _create_file_action(
        self, input_data: dict
    ) -> tuple[str, Optional[str], Optional[dict]]:
        """Generate command for create_file action."""
        filepath = input_data.get("filepath")
        if not filepath:
            raise ValueError("filepath is required for create_file action")

        content = input_data.get("content", "")
        command = f"cat > {self._shell_quote(filepath)} << 'OMNIFORGE_EOF'\n{content}\nOMNIFORGE_EOF"
        cwd = input_data.get("cwd")
        env = input_data.get("env")
        return command, cwd, env

    def _read_file_action(self, input_data: dict) -> tuple[str, Optional[str], Optional[dict]]:
        """Generate command for read_file action."""
        filepath = input_data.get("filepath")
        if not filepath:
            raise ValueError("filepath is required for read_file action")

        command = f"cat {self._shell_quote(filepath)}"
        cwd = input_data.get("cwd")
        env = input_data.get("env")
        return command, cwd, env

    def _delete_file_action(self, input_data: dict) -> tuple[str, Optional[str], Optional[dict]]:
        """Generate command for delete_file action."""
        filepath = input_data.get("filepath")
        if not filepath:
            raise ValueError("filepath is required for delete_file action")

        command = f"rm {self._shell_quote(filepath)}"
        cwd = input_data.get("cwd")
        env = input_data.get("env")
        return command, cwd, env

    def _run_python_action(self, input_data: dict) -> tuple[str, Optional[str], Optional[dict]]:
        """Generate command for run_python action."""
        code = input_data.get("code")
        if not code:
            raise ValueError("code is required for run_python action")

        command = f"python3 -c {self._shell_quote(code)}"
        cwd = input_data.get("cwd")
        env = input_data.get("env")
        return command, cwd, env

    @staticmethod
    def _shell_quote(text: str) -> str:
        """Quote text for safe shell usage."""
        escaped = text.replace("'", "'\\''")
        return f"'{escaped}'"


async def main() -> None:
    """Demo of BashActionExecutor."""
    print("Bash Tool Actions Demo")
    executor = BashActionExecutor(timeout_ms=30000)
    context = ToolCallContext(
        correlation_id="demo-1", task_id="task-1", agent_id="agent-1"
    )

    result = await executor.execute_action(
        action="echo",
        input_data={"message": "Hello from BashActionExecutor!"},
        context=context,
    )
    print(f"Success: {result['success']}")
    print(f"Output: {result['output']}")


if __name__ == "__main__":
    asyncio.run(main())
