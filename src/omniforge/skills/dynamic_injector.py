"""Dynamic context injection for skills with security hardening.

This module provides the DynamicInjector class for parsing and executing
!`command` syntax in skill content before execution starts. Commands are
validated against allowed-tools whitelist with multi-layered security
protections to prevent shell injection attacks.

Example:
    ```python
    injector = DynamicInjector(
        allowed_tools=["Bash(gh:*)"],
        timeout_seconds=5,
        max_output_chars=10_000
    )
    result = await injector.process(
        content="PR diff: !`gh pr diff`",
        task_id="task-123",
        working_dir="/path/to/repo"
    )
    ```

Security Features:
    - Multi-layered command validation
    - Shell operator blocking (;, &&, ||, |, >, <, $(), `)
    - Path traversal prevention (.., absolute paths)
    - Shlex parsing for quote handling
    - Timeout enforcement
    - Output size limits
    - Comprehensive audit logging
"""

import asyncio
import logging
import re
import shlex
import time
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class InjectionResult:
    """Result of a single command injection.

    Attributes:
        command: The command that was executed
        output: Command output or error message
        success: Whether the command executed successfully
        duration_ms: Execution duration in milliseconds
    """

    command: str
    output: str
    success: bool
    duration_ms: int


@dataclass
class InjectedContent:
    """Result of processing content with dynamic injections.

    Attributes:
        content: Content with !`command` replaced by output
        injections: List of injection results
        total_duration_ms: Total processing time in milliseconds
    """

    content: str
    injections: list[InjectionResult]
    total_duration_ms: int


class DynamicInjector:
    """Parse and execute !`command` syntax with security hardening.

    This class enables skills to inject live context (PR diffs, git status,
    system info) by executing commands before skill execution starts.

    SECURITY: Multi-layered validation prevents shell injection attacks:
        1. Block shell operators (;, &&, ||, |, >, <, $(), `)
        2. Parse with shlex to handle quotes safely
        3. Block path traversal (.., absolute paths)
        4. Validate against allowed_tools whitelist
        5. Enforce timeout and output limits

    All command execution attempts are logged for security auditing.
    """

    # Regex pattern to match !`command` syntax
    COMMAND_PATTERN = re.compile(r"!\`([^\`]+)\`")

    # Shell operators that must be blocked
    SHELL_OPERATORS = [";", "&&", "||", "|", ">", "<", "$(", "`", "\n", "\r"]

    def __init__(
        self,
        tool_executor: Optional[object] = None,
        allowed_tools: Optional[list[str]] = None,
        timeout_seconds: int = 5,
        max_output_chars: int = 10_000,
    ) -> None:
        """Initialize DynamicInjector.

        Args:
            tool_executor: Optional ToolExecutor for future integration
            allowed_tools: List of allowed tool patterns (e.g., ["Bash(gh:*)"])
            timeout_seconds: Command execution timeout in seconds (default: 5)
            max_output_chars: Max output characters (default: 10,000)
        """
        self._tool_executor = tool_executor
        self._allowed_tools = allowed_tools
        self._timeout_seconds = timeout_seconds
        self._max_output_chars = max_output_chars

    async def process(
        self,
        content: str,
        task_id: str = "default",
        working_dir: Optional[str] = None,
    ) -> InjectedContent:
        """Process content and replace !`command` with execution results.

        Finds all !`command` patterns in content, validates them, executes
        them, and replaces the patterns with their output.

        Args:
            content: Content with !`command` patterns
            task_id: Task identifier for logging
            working_dir: Working directory for command execution

        Returns:
            InjectedContent with replacements and execution metadata
        """
        start_time = time.time()
        injections: list[InjectionResult] = []

        # Find all command patterns
        matches = list(self.COMMAND_PATTERN.finditer(content))

        if not matches:
            # No commands to inject
            return InjectedContent(
                content=content,
                injections=[],
                total_duration_ms=0,
            )

        logger.info(f"[{task_id}] Found {len(matches)} command injection(s) to process")

        # Execute each command and collect results
        for match in matches:
            command = match.group(1).strip()

            # Validate and execute command
            result = await self._execute_command(command, working_dir)
            injections.append(result)

        # Replace all commands with their outputs
        processed_content = content
        for match, injection in zip(matches, injections):
            processed_content = processed_content.replace(
                match.group(0),  # Full !`command` pattern
                injection.output,
                1,  # Replace only first occurrence
            )

        total_duration_ms = int((time.time() - start_time) * 1000)

        logger.info(
            f"[{task_id}] Command injection completed in {total_duration_ms}ms "
            f"({len([i for i in injections if i.success])} successful, "
            f"{len([i for i in injections if not i.success])} failed)"
        )

        return InjectedContent(
            content=processed_content,
            injections=injections,
            total_duration_ms=total_duration_ms,
        )

    async def _execute_command(
        self,
        command: str,
        working_dir: Optional[str] = None,
    ) -> InjectionResult:
        """Execute command with timeout and security validation.

        SECURITY: Commands are validated before execution to prevent
        shell injection attacks. All execution attempts are logged.

        Args:
            command: Command to execute
            working_dir: Working directory for execution

        Returns:
            InjectionResult with command output or error
        """
        start_time = time.time()

        # SECURITY: Validate command before execution
        if not self._is_command_allowed(command):
            logger.warning(f"SECURITY: Blocked unauthorized command injection attempt: {command}")
            return InjectionResult(
                command=command,
                output="[Command blocked by security policy]",
                success=False,
                duration_ms=0,
            )

        # Log authorized execution attempt
        logger.info(f"Executing command injection: {command}")

        try:
            # Execute command with subprocess
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_dir,
            )

            # Wait for completion with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self._timeout_seconds,
                )
            except asyncio.TimeoutError:
                # Kill the process on timeout
                process.kill()
                await process.wait()

                duration_ms = int((time.time() - start_time) * 1000)
                logger.warning(
                    f"Command injection timed out after {self._timeout_seconds}s: {command}"
                )

                return InjectionResult(
                    command=command,
                    output=f"[Command timed out after {self._timeout_seconds}s]",
                    success=False,
                    duration_ms=duration_ms,
                )

            duration_ms = int((time.time() - start_time) * 1000)

            # Check return code
            if process.returncode != 0:
                # Command failed - include stderr
                error_output = stderr.decode("utf-8", errors="replace").strip()
                if len(error_output) > self._max_output_chars:
                    error_output = (
                        error_output[: self._max_output_chars]
                        + f"... [truncated, exceeded {self._max_output_chars} chars]"
                    )

                logger.warning(f"Command injection failed (exit {process.returncode}): {command}")

                return InjectionResult(
                    command=command,
                    output=f"[Command failed: {error_output}]",
                    success=False,
                    duration_ms=duration_ms,
                )

            # Command succeeded - return stdout
            output = stdout.decode("utf-8", errors="replace").strip()

            # Apply output size limit
            if len(output) > self._max_output_chars:
                logger.warning(
                    f"Command output truncated (exceeded {self._max_output_chars} chars)"
                )
                output = (
                    output[: self._max_output_chars]
                    + f"... [truncated, exceeded {self._max_output_chars} chars]"
                )

            logger.info(f"Command injection succeeded in {duration_ms}ms: {command}")

            return InjectionResult(
                command=command,
                output=output,
                success=True,
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.exception(f"Error executing command injection: {command}")

            return InjectionResult(
                command=command,
                output=f"[Execution error: {str(e)}]",
                success=False,
                duration_ms=duration_ms,
            )

    def _is_command_allowed(self, command: str) -> bool:
        """Check if command is allowed based on allowed_tools.

        SECURITY: Multi-layered validation to prevent injection attacks.

        Layer 1: Block shell operators (;, &&, ||, |, >, <, $(), `)
        Layer 2: Parse with shlex to handle quotes safely
        Layer 3: Block path traversal (.., absolute paths)
        Layer 4: Validate against allowed_tools whitelist

        Args:
            command: Command to validate

        Returns:
            True if command is allowed, False otherwise
        """
        # Layer 1: Block shell operators
        for operator in self.SHELL_OPERATORS:
            if operator in command:
                logger.warning(
                    f"SECURITY: Blocked command with shell operator '{operator}': {command}"
                )
                return False

        # Layer 2: Parse with shlex to handle quotes
        try:
            command_parts = shlex.split(command)
        except ValueError as e:
            logger.warning(
                f"SECURITY: Blocked command with invalid shell syntax: {command} " f"(error: {e})"
            )
            return False

        if not command_parts:
            return False

        base_command = command_parts[0]

        # Layer 3: Block path traversal (check all parts, not just base command)
        if ".." in command or base_command.startswith("/"):
            logger.warning(
                f"SECURITY: Blocked path traversal attempt: {command} "
                f"(base_command: {base_command})"
            )
            return False

        # Layer 4: Validate against allowed_tools whitelist
        if not self._allowed_tools:
            logger.warning(
                "SECURITY: Command injection with no allowed_tools restrictions. "
                "This is a security risk in multi-tenant environments."
            )
            # Allow in development, but warn
            return True

        # Check if command matches any allowed pattern
        for allowed in self._allowed_tools:
            if self._matches_allowed_pattern(base_command, allowed):
                return True

        logger.warning(
            f"SECURITY: Blocked command not in allowed_tools: {command} "
            f"(allowed_tools: {self._allowed_tools})"
        )
        return False

    def _matches_allowed_pattern(self, command: str, pattern: str) -> bool:
        """Check if command matches an allowed_tools pattern.

        Supported patterns:
            - "Bash" - Allow all bash commands
            - "Bash(gh:*)" - Allow commands starting with "gh"
            - "Bash(python:*)" - Allow commands starting with "python"

        Args:
            command: Base command to check (e.g., "gh", "python")
            pattern: Allowed pattern (e.g., "Bash(gh:*)")

        Returns:
            True if command matches pattern, False otherwise
        """
        # Pattern: Bash - allow all
        if pattern == "Bash":
            return True

        # Pattern: Bash(prefix:*) - allow commands starting with prefix
        match = re.match(r"Bash\(([^:]+):\*\)", pattern)
        if match:
            prefix = match.group(1)
            return command == prefix or command.startswith(prefix + " ")

        # Pattern: Exact match
        return command == pattern
