"""Script executor with configurable sandboxing for safe script execution.

This module provides secure script execution with two-tier sandboxing:
- Subprocess mode: Basic resource limits for development and SDK usage
- Docker mode: Full container isolation for production multi-tenant environments

All script execution includes security validations, resource limits, and audit logging.
"""

import asyncio
import logging
import platform
import shutil
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

from omniforge.skills.errors import SkillError

logger = logging.getLogger(__name__)


class SecurityError(SkillError):
    """Raised when a security violation is detected during script execution.

    This error indicates attempts to bypass security restrictions such as
    path traversal, unauthorized file access, or resource limit violations.
    """

    def __init__(self, message: str, violation_type: str, context: Optional[dict] = None) -> None:
        """Initialize security error.

        Args:
            message: Human-readable error description
            violation_type: Type of security violation (e.g., "path_traversal")
            context: Optional additional context information
        """
        super().__init__(
            message=message,
            error_code="security_violation",
            context={"violation_type": violation_type, **(context or {})},
        )
        self.violation_type = violation_type


class SandboxMode(str, Enum):
    """Sandboxing mode for script execution.

    Defines the level of isolation applied to script execution:
    - NONE: No sandboxing (development only, not recommended for production)
    - SUBPROCESS: Basic subprocess isolation with resource limits
    - DOCKER: Full Docker container isolation (recommended for production)
    """

    NONE = "none"
    SUBPROCESS = "subprocess"
    DOCKER = "docker"


@dataclass
class ScriptExecutionConfig:
    """Configuration for script execution with sandboxing and resource limits.

    Attributes:
        sandbox_mode: Level of sandboxing to apply
        timeout_seconds: Maximum execution time in seconds
        max_memory_mb: Maximum memory allocation in megabytes
        max_cpu_percent: Maximum CPU usage percentage (100 = 1 core)
        allow_network: Whether to allow network access
        allow_file_write: Whether to allow file writes in workspace
    """

    sandbox_mode: SandboxMode = SandboxMode.SUBPROCESS
    timeout_seconds: int = 30
    max_memory_mb: int = 512
    max_cpu_percent: int = 50
    allow_network: bool = False
    allow_file_write: bool = True


@dataclass
class ScriptResult:
    """Result of script execution.

    Attributes:
        success: Whether script executed successfully
        output: Combined stdout and stderr output
        exit_code: Process exit code (0 = success)
        duration_ms: Execution duration in milliseconds
    """

    success: bool
    output: str
    exit_code: int
    duration_ms: int


class ScriptExecutor:
    """Executes scripts with configurable sandboxing for security.

    This executor provides secure script execution with path validation,
    resource limits, and optional Docker isolation for multi-tenant environments.

    Security features:
    - Path traversal prevention
    - Resource limits (CPU, memory, timeout)
    - Network isolation
    - Read-only skill directory
    - Isolated workspace for file writes
    - Environment variable sanitization
    - Audit logging

    Example:
        ```python
        config = ScriptExecutionConfig(
            sandbox_mode=SandboxMode.DOCKER,
            timeout_seconds=30,
            max_memory_mb=256,
        )
        executor = ScriptExecutor(config)

        result = await executor.execute_script(
            script_path="/skills/my-skill/scripts/process.py",
            skill_dir="/skills/my-skill",
            workspace="/tmp/workspace",
        )

        if result.success:
            print(f"Output: {result.output}")
        ```
    """

    def __init__(self, config: ScriptExecutionConfig) -> None:
        """Initialize script executor with configuration.

        Args:
            config: Execution configuration including sandbox mode and limits
        """
        self.config = config
        self._docker_client: Optional[object] = None

        # Validate Docker availability if Docker mode is selected
        if config.sandbox_mode == SandboxMode.DOCKER:
            self._ensure_docker_available()

    def _ensure_docker_available(self) -> None:
        """Ensure Docker is available and accessible.

        Raises:
            RuntimeError: If Docker is not available or not accessible
        """
        try:
            import docker  # type: ignore

            self._docker_client = docker.from_env()
            # Test Docker connectivity
            self._docker_client.ping()  # type: ignore
            logger.info("Docker client initialized successfully")
        except ImportError:
            raise RuntimeError(
                "Docker mode requires 'docker' package. Install with: pip install docker"
            )
        except Exception as e:
            raise RuntimeError(f"Docker is not available or not running: {e}")

    def _is_safe_path(self, script_path: Path, skill_dir: Path) -> bool:
        """Validate that script path is within skill directory scripts folder.

        This prevents path traversal attacks by ensuring scripts can only
        be executed from ${SKILL_DIR}/scripts/ directory.

        Args:
            script_path: Absolute path to script file
            skill_dir: Absolute path to skill directory

        Returns:
            True if path is safe, False otherwise
        """
        try:
            # Resolve to absolute paths to handle symlinks and relative paths
            resolved_script = script_path.resolve()
            resolved_skill_dir = skill_dir.resolve()

            # Expected scripts directory
            scripts_dir = resolved_skill_dir / "scripts"

            # Check if script is within scripts directory
            # relative_to() will raise ValueError if not a subpath
            resolved_script.relative_to(scripts_dir)

            # Additional check: ensure no parent directory references
            if ".." in str(script_path):
                return False

            return True

        except (ValueError, RuntimeError):
            # ValueError: not a subpath
            # RuntimeError: infinite loop in path resolution
            return False

    async def execute_script(
        self,
        script_path: str,
        skill_dir: str,
        workspace: str,
        env_vars: Optional[dict[str, str]] = None,
    ) -> ScriptResult:
        """Execute a script with configured sandboxing.

        Args:
            script_path: Absolute path to script file
            skill_dir: Absolute path to skill directory
            workspace: Absolute path to temporary workspace
            env_vars: Optional environment variables to pass to script

        Returns:
            ScriptResult with execution output and status

        Raises:
            SecurityError: If script path validation fails
            RuntimeError: If execution fails unexpectedly
        """
        # Convert to Path objects
        script_path_obj = Path(script_path)
        skill_dir_obj = Path(skill_dir)
        workspace_obj = Path(workspace)

        # Security validation: check path safety
        if not self._is_safe_path(script_path_obj, skill_dir_obj):
            logger.warning(
                "Security violation: attempted to execute script outside skill directory",
                extra={
                    "script_path": str(script_path),
                    "skill_dir": str(skill_dir),
                    "violation_type": "path_traversal",
                },
            )
            raise SecurityError(
                message=f"Script must be in {skill_dir}/scripts/ directory",
                violation_type="path_traversal",
                context={"script_path": str(script_path), "skill_dir": str(skill_dir)},
            )

        # Verify script exists
        if not script_path_obj.exists():
            raise FileNotFoundError(f"Script not found: {script_path}")

        # Ensure workspace exists
        workspace_obj.mkdir(parents=True, exist_ok=True)

        # Log execution start
        logger.info(
            "Starting script execution",
            extra={
                "script_path": str(script_path),
                "sandbox_mode": self.config.sandbox_mode.value,
                "timeout": self.config.timeout_seconds,
            },
        )

        # Execute based on sandbox mode
        start_time = time.time()

        try:
            if self.config.sandbox_mode == SandboxMode.DOCKER:
                result = await self._execute_in_docker(
                    script_path_obj, skill_dir_obj, workspace_obj, env_vars
                )
            elif self.config.sandbox_mode == SandboxMode.SUBPROCESS:
                result = await self._execute_in_subprocess(
                    script_path_obj, skill_dir_obj, workspace_obj, env_vars
                )
            else:  # NONE mode
                result = await self._execute_unsandboxed(
                    script_path_obj, skill_dir_obj, workspace_obj, env_vars
                )

            duration_ms = int((time.time() - start_time) * 1000)

            # Log execution result
            log_level = logging.INFO if result.success else logging.WARNING
            logger.log(
                log_level,
                "Script execution completed",
                extra={
                    "script_path": str(script_path),
                    "success": result.success,
                    "exit_code": result.exit_code,
                    "duration_ms": duration_ms,
                },
            )

            return ScriptResult(
                success=result.success,
                output=result.output,
                exit_code=result.exit_code,
                duration_ms=duration_ms,
            )

        except asyncio.TimeoutError:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.warning(
                "Script execution timeout",
                extra={
                    "script_path": str(script_path),
                    "timeout": self.config.timeout_seconds,
                    "duration_ms": duration_ms,
                },
            )
            return ScriptResult(
                success=False,
                output=f"Script execution timed out after {self.config.timeout_seconds}s",
                exit_code=-1,
                duration_ms=duration_ms,
            )
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(
                "Script execution failed",
                extra={
                    "script_path": str(script_path),
                    "error": str(e),
                    "duration_ms": duration_ms,
                },
                exc_info=True,
            )
            return ScriptResult(
                success=False,
                output=f"Script execution failed: {e}",
                exit_code=-1,
                duration_ms=duration_ms,
            )

    async def _execute_in_docker(
        self,
        script_path: Path,
        skill_dir: Path,
        workspace: Path,
        env_vars: Optional[dict[str, str]],
    ) -> ScriptResult:
        """Execute script in Docker container with full isolation.

        Args:
            script_path: Path to script file
            skill_dir: Skill directory path
            workspace: Workspace directory path
            env_vars: Optional environment variables

        Returns:
            ScriptResult with execution output
        """
        import docker  # type: ignore

        # Determine script interpreter and Docker image
        script_ext = script_path.suffix.lower()
        if script_ext == ".py":
            image = "python:3.11-slim"
            cmd = ["python", "/skill/scripts/" + script_path.name]
        elif script_ext == ".js":
            image = "node:18-slim"
            cmd = ["node", "/skill/scripts/" + script_path.name]
        elif script_ext in [".sh", ".bash"]:
            image = "ubuntu:22.04"
            cmd = ["bash", "/skill/scripts/" + script_path.name]
        else:
            raise ValueError(f"Unsupported script type: {script_ext}")

        # Prepare environment variables (sanitized)
        environment = self._sanitize_env_vars(env_vars)

        # Configure volumes
        volumes = {
            str(skill_dir): {"bind": "/skill", "mode": "ro"},  # Read-only
        }

        if self.config.allow_file_write:
            volumes[str(workspace)] = {"bind": "/workspace", "mode": "rw"}

        # Configure network mode
        network_mode = "bridge" if self.config.allow_network else "none"

        try:
            # Run container
            container = self._docker_client.containers.run(  # type: ignore
                image=image,
                command=cmd,
                volumes=volumes,
                mem_limit=f"{self.config.max_memory_mb}m",
                cpu_period=100000,
                cpu_quota=self.config.max_cpu_percent * 1000,
                network_mode=network_mode,
                environment=environment,
                working_dir="/workspace" if self.config.allow_file_write else "/skill",
                detach=True,
                remove=False,  # Don't auto-remove so we can get logs
            )

            # Wait for completion with timeout
            try:
                result = container.wait(timeout=self.config.timeout_seconds)
                exit_code = result["StatusCode"]

                # Get logs
                output = container.logs(stdout=True, stderr=True).decode("utf-8")

                # Clean up container
                container.remove()

                return ScriptResult(
                    success=(exit_code == 0),
                    output=output,
                    exit_code=exit_code,
                    duration_ms=0,  # Will be calculated by caller
                )

            except Exception as e:
                # Ensure container cleanup on error
                try:
                    container.kill()
                    container.remove()
                except Exception:
                    pass
                raise e

        except docker.errors.ImageNotFound:  # type: ignore
            logger.info(f"Pulling Docker image: {image}")
            self._docker_client.images.pull(image)  # type: ignore
            # Retry execution after pulling image
            return await self._execute_in_docker(script_path, skill_dir, workspace, env_vars)

    async def _execute_in_subprocess(
        self,
        script_path: Path,
        skill_dir: Path,
        workspace: Path,
        env_vars: Optional[dict[str, str]],
    ) -> ScriptResult:
        """Execute script in subprocess with resource limits.

        Note: Resource limits (memory, CPU) are only supported on Unix systems.
        On Windows, only timeout is enforced.

        Args:
            script_path: Path to script file
            skill_dir: Skill directory path
            workspace: Workspace directory path
            env_vars: Optional environment variables

        Returns:
            ScriptResult with execution output
        """
        # Determine script command
        script_ext = script_path.suffix.lower()
        if script_ext == ".py":
            interpreter = "python3" if shutil.which("python3") else "python"
            cmd = [interpreter, str(script_path)]
        elif script_ext == ".js":
            cmd = ["node", str(script_path)]
        elif script_ext in [".sh", ".bash"]:
            cmd = ["bash", str(script_path)]
        else:
            raise ValueError(f"Unsupported script type: {script_ext}")

        # Prepare environment
        env = self._sanitize_env_vars(env_vars, include_system=True)

        # Set resource limits (Unix only)
        preexec_fn = None
        if platform.system() != "Windows":
            preexec_fn = self._create_resource_limiter()

        # Execute subprocess
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(workspace),
                env=env,
                preexec_fn=preexec_fn,
            )

            # Wait with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.config.timeout_seconds,
                )

                output = stdout.decode("utf-8") + stderr.decode("utf-8")
                exit_code = process.returncode or 0

                return ScriptResult(
                    success=(exit_code == 0),
                    output=output,
                    exit_code=exit_code,
                    duration_ms=0,  # Will be calculated by caller
                )

            except asyncio.TimeoutError:
                # Kill process on timeout
                try:
                    process.kill()
                    await process.wait()
                except Exception:
                    pass
                raise

        except Exception as e:
            logger.error(f"Subprocess execution failed: {e}")
            raise

    async def _execute_unsandboxed(
        self,
        script_path: Path,
        skill_dir: Path,
        workspace: Path,
        env_vars: Optional[dict[str, str]],
    ) -> ScriptResult:
        """Execute script without sandboxing (development only).

        Warning: This mode provides no isolation and should only be used
        in development environments. Not recommended for production.

        Args:
            script_path: Path to script file
            skill_dir: Skill directory path
            workspace: Workspace directory path
            env_vars: Optional environment variables

        Returns:
            ScriptResult with execution output
        """
        logger.warning(
            "Executing script without sandboxing - use only in development",
            extra={"script_path": str(script_path)},
        )

        # Use subprocess execution but with minimal restrictions
        return await self._execute_in_subprocess(script_path, skill_dir, workspace, env_vars)

    def _create_resource_limiter(self) -> Callable[[], None]:
        """Create a preexec function for subprocess resource limits.

        Returns:
            Function to be used as preexec_fn in subprocess
        """
        import resource

        def set_limits() -> None:
            """Set resource limits for subprocess."""
            # Memory limit (in bytes)
            max_memory_bytes = self.config.max_memory_mb * 1024 * 1024
            try:
                resource.setrlimit(resource.RLIMIT_AS, (max_memory_bytes, max_memory_bytes))
            except ValueError:
                # Some systems don't support RLIMIT_AS
                logger.debug("RLIMIT_AS not supported on this system")

            # CPU time limit (in seconds)
            try:
                resource.setrlimit(
                    resource.RLIMIT_CPU,
                    (self.config.timeout_seconds, self.config.timeout_seconds),
                )
            except ValueError:
                logger.debug("RLIMIT_CPU not supported on this system")

        return set_limits

    def _sanitize_env_vars(
        self, env_vars: Optional[dict[str, str]], include_system: bool = False
    ) -> dict[str, str]:
        """Sanitize environment variables for security.

        Filters out sensitive environment variables and only includes
        explicitly passed variables plus safe system variables if requested.

        Args:
            env_vars: User-provided environment variables
            include_system: Whether to include safe system variables

        Returns:
            Sanitized environment variable dictionary
        """
        # Start with user-provided vars
        sanitized = env_vars.copy() if env_vars else {}

        if include_system:
            # Include only safe system variables
            import os

            safe_vars = ["PATH", "HOME", "USER", "LANG", "LC_ALL"]
            for var in safe_vars:
                if var in os.environ:
                    sanitized[var] = os.environ[var]

        return sanitized
