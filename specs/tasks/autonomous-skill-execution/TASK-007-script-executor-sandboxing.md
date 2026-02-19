# TASK-007: Create ScriptExecutor with Docker sandboxing

**Priority:** P0 (Must Have) - Critical Security
**Estimated Effort:** Medium (1-3 days)
**Dependencies:** None

---

## Description

Create `ScriptExecutor` class for executing bundled scripts (Python, JS, shell) with configurable sandboxing. This addresses critical security concerns from the technical plan review - scripts must be sandboxed to prevent arbitrary code execution in multi-tenant environments.

Implements two-tier sandboxing:
- **Subprocess mode**: Basic resource limits (for SDK/development)
- **Docker mode**: Full container isolation (for production platform)

## Files to Create

- `src/omniforge/skills/script_executor.py` - ScriptExecutor implementation

## Implementation Requirements

### SandboxMode Enum
```python
class SandboxMode(str, Enum):
    NONE = "none"           # No sandboxing (dev only, not recommended)
    SUBPROCESS = "subprocess"  # Basic subprocess isolation
    DOCKER = "docker"       # Full Docker isolation (production)
```

### ScriptExecutionConfig
```python
@dataclass
class ScriptExecutionConfig:
    sandbox_mode: SandboxMode = SandboxMode.SUBPROCESS
    timeout_seconds: int = 30
    max_memory_mb: int = 512
    max_cpu_percent: int = 50
    allow_network: bool = False
    allow_file_write: bool = True  # In temp workspace only
```

### ScriptResult
```python
@dataclass
class ScriptResult:
    success: bool
    output: str
    exit_code: int
    duration_ms: int
```

### ScriptExecutor Class

**Methods:**
- `async execute_script(script_path, skill_dir, workspace) -> ScriptResult`
- `_execute_in_docker(...)` - Docker container execution
- `_execute_in_subprocess(...)` - Subprocess with resource limits
- `_is_safe_path(script_path, skill_dir) -> bool` - Path validation

### Security Requirements (Critical)

1. **Path Validation**: Script MUST be in `${SKILL_DIR}/scripts/` directory
2. **Resource Limits**: CPU, memory, timeout enforced
3. **Network Isolation**: No network access by default
4. **File System**: Read-only skill directory, temp workspace for writes
5. **No Environment Leakage**: Sanitize environment variables

### Docker Execution

```python
container = docker_client.containers.run(
    image=image,
    command=cmd,
    volumes={
        skill_dir: {'bind': '/skill', 'mode': 'ro'},  # Read-only
        temp_workspace: {'bind': '/workspace', 'mode': 'rw'},
    },
    mem_limit=f"{config.max_memory_mb}m",
    cpu_period=100000,
    cpu_quota=config.max_cpu_percent * 1000,
    network_mode='none' if not config.allow_network else 'bridge',
    detach=True,
    remove=True,
)
```

### Subprocess Execution

```python
import resource

def set_limits():
    resource.setrlimit(resource.RLIMIT_AS, (max_memory_mb * 1024 * 1024, -1))
    resource.setrlimit(resource.RLIMIT_CPU, (timeout_seconds, -1))

process = await asyncio.create_subprocess_exec(
    *cmd,
    cwd=workspace,
    preexec_fn=set_limits,
)
```

## Acceptance Criteria

- [ ] Path validation prevents execution outside skill directory
- [ ] Docker mode provides full container isolation
- [ ] Subprocess mode enforces resource limits
- [ ] Timeout kills runaway scripts
- [ ] Memory limits enforced
- [ ] Network disabled by default
- [ ] Script output captured and returned
- [ ] Error handling for Docker failures
- [ ] Audit logging for all script executions
- [ ] Unit tests with mocked Docker
- [ ] Integration tests with real subprocess

## Testing

```python
def test_path_validation_blocks_traversal():
    """Reject scripts outside skill directory."""
    executor = ScriptExecutor(config)
    with pytest.raises(SecurityError):
        await executor.execute_script(
            "/etc/passwd",  # Path traversal attempt
            skill_dir="/skills/test",
            workspace="/tmp/work"
        )

def test_path_validation_blocks_relative_traversal():
    """Reject relative path traversal."""
    with pytest.raises(SecurityError):
        await executor.execute_script(
            "/skills/test/scripts/../../../etc/passwd",
            skill_dir="/skills/test",
            workspace="/tmp/work"
        )

async def test_subprocess_timeout():
    """Script exceeding timeout is killed."""
    # Create script that sleeps for 60s
    config = ScriptExecutionConfig(timeout_seconds=2)
    result = await executor.execute_script(slow_script)
    assert not result.success
    assert "timeout" in result.output.lower()

async def test_subprocess_memory_limit():
    """Script exceeding memory is killed."""
    # Create script that allocates 1GB
    config = ScriptExecutionConfig(max_memory_mb=100)
    result = await executor.execute_script(memory_hog_script)
    assert not result.success
```

## Technical Notes

- Use `docker` Python library: `pip install docker`
- Default Docker images: python:3.11-slim, node:18-slim, ubuntu:22.04
- Cleanup temp workspace after execution
- Log all executions at INFO level, failures at WARNING
- Consider using seccomp profiles for additional hardening
- Resource module only works on Unix (handle Windows gracefully)
