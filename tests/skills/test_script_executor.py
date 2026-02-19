"""Tests for ScriptExecutor with sandboxing."""

import os
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pytest

from omniforge.skills.script_executor import (
    SandboxMode,
    ScriptExecutionConfig,
    ScriptExecutor,
    ScriptResult,
    SecurityError,
)


class TestSandboxMode:
    """Tests for SandboxMode enum."""

    def test_sandbox_mode_values(self) -> None:
        """Test SandboxMode enum has correct values."""
        assert SandboxMode.NONE.value == "none"
        assert SandboxMode.SUBPROCESS.value == "subprocess"
        assert SandboxMode.DOCKER.value == "docker"


class TestScriptExecutionConfig:
    """Tests for ScriptExecutionConfig dataclass."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = ScriptExecutionConfig()

        assert config.sandbox_mode == SandboxMode.SUBPROCESS
        assert config.timeout_seconds == 30
        assert config.max_memory_mb == 512
        assert config.max_cpu_percent == 50
        assert config.allow_network is False
        assert config.allow_file_write is True

    def test_custom_config(self) -> None:
        """Test custom configuration values."""
        config = ScriptExecutionConfig(
            sandbox_mode=SandboxMode.DOCKER,
            timeout_seconds=60,
            max_memory_mb=1024,
            max_cpu_percent=100,
            allow_network=True,
            allow_file_write=False,
        )

        assert config.sandbox_mode == SandboxMode.DOCKER
        assert config.timeout_seconds == 60
        assert config.max_memory_mb == 1024
        assert config.max_cpu_percent == 100
        assert config.allow_network is True
        assert config.allow_file_write is False


class TestScriptResult:
    """Tests for ScriptResult dataclass."""

    def test_successful_result(self) -> None:
        """Test successful script result."""
        result = ScriptResult(
            success=True,
            output="Script completed successfully",
            exit_code=0,
            duration_ms=1500,
        )

        assert result.success is True
        assert result.output == "Script completed successfully"
        assert result.exit_code == 0
        assert result.duration_ms == 1500

    def test_failed_result(self) -> None:
        """Test failed script result."""
        result = ScriptResult(
            success=False,
            output="Error: script failed",
            exit_code=1,
            duration_ms=500,
        )

        assert result.success is False
        assert result.output == "Error: script failed"
        assert result.exit_code == 1
        assert result.duration_ms == 500


class TestSecurityError:
    """Tests for SecurityError exception."""

    def test_security_error_creation(self) -> None:
        """Test SecurityError exception creation."""
        error = SecurityError(
            message="Path traversal detected",
            violation_type="path_traversal",
            context={"path": "/etc/passwd"},
        )

        assert error.message == "Path traversal detected"
        assert error.violation_type == "path_traversal"
        assert error.error_code == "security_violation"
        assert error.context["violation_type"] == "path_traversal"
        assert error.context["path"] == "/etc/passwd"


class TestScriptExecutorInitialization:
    """Tests for ScriptExecutor initialization."""

    def test_executor_with_subprocess_mode(self) -> None:
        """Test executor initialization with subprocess mode."""
        config = ScriptExecutionConfig(sandbox_mode=SandboxMode.SUBPROCESS)
        executor = ScriptExecutor(config)

        assert executor.config.sandbox_mode == SandboxMode.SUBPROCESS
        assert executor._docker_client is None

    def test_executor_with_none_mode(self) -> None:
        """Test executor initialization with no sandboxing."""
        config = ScriptExecutionConfig(sandbox_mode=SandboxMode.NONE)
        executor = ScriptExecutor(config)

        assert executor.config.sandbox_mode == SandboxMode.NONE

    @patch("docker.from_env")
    def test_executor_with_docker_mode_success(self, mock_from_env: Mock) -> None:
        """Test executor initialization with Docker mode when Docker is available."""
        # Mock Docker client
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_from_env.return_value = mock_client

        config = ScriptExecutionConfig(sandbox_mode=SandboxMode.DOCKER)
        executor = ScriptExecutor(config)

        assert executor.config.sandbox_mode == SandboxMode.DOCKER
        assert executor._docker_client is not None
        mock_from_env.assert_called_once()

    @patch("docker.from_env")
    def test_executor_with_docker_mode_not_available(self, mock_from_env: Mock) -> None:
        """Test executor initialization fails when Docker is not available."""
        mock_from_env.side_effect = Exception("Docker not running")

        config = ScriptExecutionConfig(sandbox_mode=SandboxMode.DOCKER)

        with pytest.raises(RuntimeError, match="Docker is not available"):
            ScriptExecutor(config)

    def test_executor_with_docker_mode_import_error(self) -> None:
        """Test executor initialization fails when docker package not installed."""
        config = ScriptExecutionConfig(sandbox_mode=SandboxMode.DOCKER)

        # Simulate ImportError by mocking the docker import
        with patch.dict("sys.modules", {"docker": None}):
            with pytest.raises(RuntimeError, match="requires 'docker' package"):
                ScriptExecutor(config)


class TestPathValidation:
    """Tests for script path validation."""

    def test_safe_path_in_scripts_directory(self, tmp_path: Path) -> None:
        """Test that script in scripts directory is validated as safe."""
        skill_dir = tmp_path / "my-skill"
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir(parents=True)

        script_path = scripts_dir / "process.py"
        script_path.write_text("print('hello')")

        config = ScriptExecutionConfig(sandbox_mode=SandboxMode.NONE)
        executor = ScriptExecutor(config)

        assert executor._is_safe_path(script_path, skill_dir) is True

    def test_path_traversal_blocked_absolute(self, tmp_path: Path) -> None:
        """Test that absolute path traversal is blocked."""
        skill_dir = tmp_path / "my-skill"
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir(parents=True)

        # Attempt to access file outside skill directory
        script_path = Path("/etc/passwd")

        config = ScriptExecutionConfig(sandbox_mode=SandboxMode.NONE)
        executor = ScriptExecutor(config)

        assert executor._is_safe_path(script_path, skill_dir) is False

    def test_path_traversal_blocked_relative(self, tmp_path: Path) -> None:
        """Test that relative path traversal is blocked."""
        skill_dir = tmp_path / "my-skill"
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir(parents=True)

        # Attempt to use .. to escape scripts directory
        script_path = scripts_dir / ".." / ".." / "etc" / "passwd"

        config = ScriptExecutionConfig(sandbox_mode=SandboxMode.NONE)
        executor = ScriptExecutor(config)

        assert executor._is_safe_path(script_path, skill_dir) is False

    def test_path_traversal_blocked_with_parent_references(self, tmp_path: Path) -> None:
        """Test that paths with .. references are blocked."""
        skill_dir = tmp_path / "my-skill"
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir(parents=True)

        # Path contains .. even if it resolves to scripts dir
        script_path = Path(f"{scripts_dir}/../scripts/process.py")

        config = ScriptExecutionConfig(sandbox_mode=SandboxMode.NONE)
        executor = ScriptExecutor(config)

        # Blocked because path string contains ".."
        assert executor._is_safe_path(script_path, skill_dir) is False

    def test_path_outside_scripts_directory_blocked(self, tmp_path: Path) -> None:
        """Test that script outside scripts directory is blocked."""
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir(parents=True)

        # Script in skill root, not in scripts subdirectory
        script_path = skill_dir / "evil_script.py"
        script_path.write_text("print('evil')")

        config = ScriptExecutionConfig(sandbox_mode=SandboxMode.NONE)
        executor = ScriptExecutor(config)

        assert executor._is_safe_path(script_path, skill_dir) is False


class TestExecuteScript:
    """Tests for execute_script method."""

    @pytest.mark.asyncio
    async def test_execute_script_security_validation_failure(self, tmp_path: Path) -> None:
        """Test that execute_script raises SecurityError for invalid paths."""
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir(parents=True)
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # Try to execute script outside scripts directory
        script_path = "/etc/passwd"

        config = ScriptExecutionConfig(sandbox_mode=SandboxMode.NONE)
        executor = ScriptExecutor(config)

        with pytest.raises(SecurityError, match="must be in .*/scripts/ directory"):
            await executor.execute_script(
                script_path=script_path,
                skill_dir=str(skill_dir),
                workspace=str(workspace),
            )

    @pytest.mark.asyncio
    async def test_execute_script_file_not_found(self, tmp_path: Path) -> None:
        """Test that execute_script raises FileNotFoundError for missing script."""
        skill_dir = tmp_path / "my-skill"
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir(parents=True)
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # Script doesn't exist
        script_path = scripts_dir / "missing.py"

        config = ScriptExecutionConfig(sandbox_mode=SandboxMode.NONE)
        executor = ScriptExecutor(config)

        with pytest.raises(FileNotFoundError, match="Script not found"):
            await executor.execute_script(
                script_path=str(script_path),
                skill_dir=str(skill_dir),
                workspace=str(workspace),
            )

    @pytest.mark.asyncio
    async def test_execute_script_creates_workspace(self, tmp_path: Path) -> None:
        """Test that execute_script creates workspace directory if missing."""
        skill_dir = tmp_path / "my-skill"
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir(parents=True)

        # Create simple Python script
        script_path = scripts_dir / "hello.py"
        script_path.write_text("print('hello world')")

        # Workspace doesn't exist yet
        workspace = tmp_path / "workspace"
        assert not workspace.exists()

        config = ScriptExecutionConfig(sandbox_mode=SandboxMode.SUBPROCESS)
        executor = ScriptExecutor(config)

        result = await executor.execute_script(
            script_path=str(script_path),
            skill_dir=str(skill_dir),
            workspace=str(workspace),
        )

        # Workspace should be created
        assert workspace.exists()
        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_python_script_subprocess(self, tmp_path: Path) -> None:
        """Test executing Python script in subprocess mode."""
        skill_dir = tmp_path / "my-skill"
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir(parents=True)
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # Create Python script
        script_path = scripts_dir / "test.py"
        script_path.write_text("print('Hello from Python')")

        config = ScriptExecutionConfig(
            sandbox_mode=SandboxMode.SUBPROCESS,
            timeout_seconds=5,
        )
        executor = ScriptExecutor(config)

        result = await executor.execute_script(
            script_path=str(script_path),
            skill_dir=str(skill_dir),
            workspace=str(workspace),
        )

        assert result.success is True
        assert "Hello from Python" in result.output
        assert result.exit_code == 0
        assert result.duration_ms > 0

    @pytest.mark.asyncio
    async def test_execute_shell_script_subprocess(self, tmp_path: Path) -> None:
        """Test executing shell script in subprocess mode."""
        skill_dir = tmp_path / "my-skill"
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir(parents=True)
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # Create shell script
        script_path = scripts_dir / "test.sh"
        script_path.write_text("#!/bin/bash\necho 'Hello from Bash'")
        script_path.chmod(0o755)

        config = ScriptExecutionConfig(
            sandbox_mode=SandboxMode.SUBPROCESS,
            timeout_seconds=5,
        )
        executor = ScriptExecutor(config)

        result = await executor.execute_script(
            script_path=str(script_path),
            skill_dir=str(skill_dir),
            workspace=str(workspace),
        )

        assert result.success is True
        assert "Hello from Bash" in result.output
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_execute_script_with_error(self, tmp_path: Path) -> None:
        """Test executing script that exits with error."""
        skill_dir = tmp_path / "my-skill"
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir(parents=True)
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # Create script that fails
        script_path = scripts_dir / "fail.py"
        script_path.write_text("import sys\nprint('Error occurred')\nsys.exit(1)")

        config = ScriptExecutionConfig(sandbox_mode=SandboxMode.SUBPROCESS)
        executor = ScriptExecutor(config)

        result = await executor.execute_script(
            script_path=str(script_path),
            skill_dir=str(skill_dir),
            workspace=str(workspace),
        )

        assert result.success is False
        assert "Error occurred" in result.output
        assert result.exit_code == 1

    @pytest.mark.asyncio
    async def test_execute_script_timeout(self, tmp_path: Path) -> None:
        """Test that long-running script is killed on timeout."""
        skill_dir = tmp_path / "my-skill"
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir(parents=True)
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # Create script that sleeps for 10 seconds
        script_path = scripts_dir / "slow.py"
        script_path.write_text("import time\ntime.sleep(10)\nprint('done')")

        config = ScriptExecutionConfig(
            sandbox_mode=SandboxMode.SUBPROCESS,
            timeout_seconds=1,  # Very short timeout
        )
        executor = ScriptExecutor(config)

        result = await executor.execute_script(
            script_path=str(script_path),
            skill_dir=str(skill_dir),
            workspace=str(workspace),
        )

        assert result.success is False
        assert "timed out" in result.output.lower()
        assert result.exit_code == -1

    @pytest.mark.asyncio
    async def test_execute_script_with_env_vars(self, tmp_path: Path) -> None:
        """Test executing script with custom environment variables."""
        skill_dir = tmp_path / "my-skill"
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir(parents=True)
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # Create script that reads environment variable
        script_path = scripts_dir / "env_test.py"
        script_path.write_text("import os\nprint(f'TEST_VAR={os.environ.get(\"TEST_VAR\")}')")

        config = ScriptExecutionConfig(sandbox_mode=SandboxMode.SUBPROCESS)
        executor = ScriptExecutor(config)

        result = await executor.execute_script(
            script_path=str(script_path),
            skill_dir=str(skill_dir),
            workspace=str(workspace),
            env_vars={"TEST_VAR": "test_value"},
        )

        assert result.success is True
        assert "TEST_VAR=test_value" in result.output


class TestDockerExecution:
    """Tests for Docker execution mode."""

    @pytest.mark.asyncio
    @patch(
        "docker.errors.ImageNotFound", new_callable=lambda: type("ImageNotFound", (Exception,), {})
    )
    @patch("docker.from_env")
    async def test_execute_python_script_docker(
        self, mock_from_env: Mock, mock_image_not_found: Mock, tmp_path: Path
    ) -> None:
        """Test executing Python script in Docker mode."""
        skill_dir = tmp_path / "my-skill"
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir(parents=True)
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # Create Python script
        script_path = scripts_dir / "test.py"
        script_path.write_text("print('Hello from Docker')")

        # Mock Docker client and container
        mock_client = Mock()
        mock_container = Mock()
        mock_container.wait.return_value = {"StatusCode": 0}
        mock_container.logs.return_value = b"Hello from Docker\n"
        mock_client.containers.run.return_value = mock_container
        mock_client.ping.return_value = True
        mock_from_env.return_value = mock_client

        config = ScriptExecutionConfig(
            sandbox_mode=SandboxMode.DOCKER,
            timeout_seconds=30,
            max_memory_mb=256,
            max_cpu_percent=50,
            allow_network=False,
        )
        executor = ScriptExecutor(config)

        result = await executor.execute_script(
            script_path=str(script_path),
            skill_dir=str(skill_dir),
            workspace=str(workspace),
        )

        assert result.success is True
        assert "Hello from Docker" in result.output
        assert result.exit_code == 0

        # Verify Docker was called with correct parameters
        call_args = mock_client.containers.run.call_args
        assert call_args[1]["image"] == "python:3.11-slim"
        assert call_args[1]["mem_limit"] == "256m"
        assert call_args[1]["network_mode"] == "none"
        assert call_args[1]["detach"] is True

    @pytest.mark.asyncio
    @patch(
        "docker.errors.ImageNotFound", new_callable=lambda: type("ImageNotFound", (Exception,), {})
    )
    @patch("docker.from_env")
    async def test_execute_javascript_script_docker(
        self, mock_from_env: Mock, mock_image_not_found: Mock, tmp_path: Path
    ) -> None:
        """Test executing JavaScript script in Docker mode."""
        skill_dir = tmp_path / "my-skill"
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir(parents=True)
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # Create JavaScript script
        script_path = scripts_dir / "test.js"
        script_path.write_text("console.log('Hello from Node');")

        # Mock Docker
        mock_client = Mock()
        mock_container = Mock()
        mock_container.wait.return_value = {"StatusCode": 0}
        mock_container.logs.return_value = b"Hello from Node\n"
        mock_client.containers.run.return_value = mock_container
        mock_client.ping.return_value = True
        mock_from_env.return_value = mock_client

        config = ScriptExecutionConfig(sandbox_mode=SandboxMode.DOCKER)
        executor = ScriptExecutor(config)

        result = await executor.execute_script(
            script_path=str(script_path),
            skill_dir=str(skill_dir),
            workspace=str(workspace),
        )

        assert result.success is True
        assert "Hello from Node" in result.output

        # Verify Node image was used
        call_args = mock_client.containers.run.call_args
        assert call_args[1]["image"] == "node:18-slim"

    @pytest.mark.asyncio
    @patch(
        "docker.errors.ImageNotFound", new_callable=lambda: type("ImageNotFound", (Exception,), {})
    )
    @patch("docker.from_env")
    async def test_execute_shell_script_docker(
        self, mock_from_env: Mock, mock_image_not_found: Mock, tmp_path: Path
    ) -> None:
        """Test executing shell script in Docker mode."""
        skill_dir = tmp_path / "my-skill"
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir(parents=True)
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # Create shell script
        script_path = scripts_dir / "test.sh"
        script_path.write_text("#!/bin/bash\necho 'Hello from Bash'")

        # Mock Docker
        mock_client = Mock()
        mock_container = Mock()
        mock_container.wait.return_value = {"StatusCode": 0}
        mock_container.logs.return_value = b"Hello from Bash\n"
        mock_client.containers.run.return_value = mock_container
        mock_client.ping.return_value = True
        mock_from_env.return_value = mock_client

        config = ScriptExecutionConfig(sandbox_mode=SandboxMode.DOCKER)
        executor = ScriptExecutor(config)

        result = await executor.execute_script(
            script_path=str(script_path),
            skill_dir=str(skill_dir),
            workspace=str(workspace),
        )

        assert result.success is True

        # Verify Ubuntu image was used
        call_args = mock_client.containers.run.call_args
        assert call_args[1]["image"] == "ubuntu:22.04"

    @pytest.mark.asyncio
    @patch(
        "docker.errors.ImageNotFound", new_callable=lambda: type("ImageNotFound", (Exception,), {})
    )
    @patch("docker.from_env")
    async def test_docker_network_enabled(
        self, mock_from_env: Mock, mock_image_not_found: Mock, tmp_path: Path
    ) -> None:
        """Test Docker execution with network enabled."""
        skill_dir = tmp_path / "my-skill"
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir(parents=True)
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        script_path = scripts_dir / "test.py"
        script_path.write_text("print('test')")

        # Mock Docker
        mock_client = Mock()
        mock_container = Mock()
        mock_container.wait.return_value = {"StatusCode": 0}
        mock_container.logs.return_value = b"test\n"
        mock_client.containers.run.return_value = mock_container
        mock_client.ping.return_value = True
        mock_from_env.return_value = mock_client

        config = ScriptExecutionConfig(
            sandbox_mode=SandboxMode.DOCKER,
            allow_network=True,
        )
        executor = ScriptExecutor(config)

        await executor.execute_script(
            script_path=str(script_path),
            skill_dir=str(skill_dir),
            workspace=str(workspace),
        )

        # Verify network mode is bridge when enabled
        call_args = mock_client.containers.run.call_args
        assert call_args[1]["network_mode"] == "bridge"

    @pytest.mark.asyncio
    @patch(
        "docker.errors.ImageNotFound", new_callable=lambda: type("ImageNotFound", (Exception,), {})
    )
    @patch("docker.from_env")
    async def test_docker_image_auto_pull(
        self, mock_from_env: Mock, mock_image_not_found: Mock, tmp_path: Path
    ) -> None:
        """Test that Docker image is automatically pulled if not found."""
        skill_dir = tmp_path / "my-skill"
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir(parents=True)
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        script_path = scripts_dir / "test.py"
        script_path.write_text("print('test')")

        # Mock Docker - first call raises ImageNotFound, second succeeds
        mock_client = Mock()
        mock_container = Mock()
        mock_container.wait.return_value = {"StatusCode": 0}
        mock_container.logs.return_value = b"test\n"

        # First call raises ImageNotFound, use the mocked exception class
        call_count = 0

        def run_side_effect(*args: Any, **kwargs: Any) -> Mock:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise mock_image_not_found("Image not found")
            return mock_container

        mock_client.containers.run.side_effect = run_side_effect
        mock_client.ping.return_value = True
        mock_from_env.return_value = mock_client

        config = ScriptExecutionConfig(sandbox_mode=SandboxMode.DOCKER)
        executor = ScriptExecutor(config)

        result = await executor.execute_script(
            script_path=str(script_path),
            skill_dir=str(skill_dir),
            workspace=str(workspace),
        )

        # Should succeed after pulling image
        assert result.success is True
        # Verify image was pulled
        mock_client.images.pull.assert_called_once_with("python:3.11-slim")


class TestEnvironmentSanitization:
    """Tests for environment variable sanitization."""

    def test_sanitize_with_no_vars(self) -> None:
        """Test sanitization with no environment variables."""
        config = ScriptExecutionConfig()
        executor = ScriptExecutor(config)

        sanitized = executor._sanitize_env_vars(None, include_system=False)

        assert sanitized == {}

    def test_sanitize_with_user_vars_only(self) -> None:
        """Test sanitization with user-provided variables."""
        config = ScriptExecutionConfig()
        executor = ScriptExecutor(config)

        user_vars = {"MY_VAR": "value1", "ANOTHER_VAR": "value2"}
        sanitized = executor._sanitize_env_vars(user_vars, include_system=False)

        assert sanitized == user_vars

    def test_sanitize_with_system_vars(self) -> None:
        """Test sanitization includes safe system variables when requested."""
        config = ScriptExecutionConfig()
        executor = ScriptExecutor(config)

        user_vars = {"MY_VAR": "value1"}
        sanitized = executor._sanitize_env_vars(user_vars, include_system=True)

        assert "MY_VAR" in sanitized
        assert sanitized["MY_VAR"] == "value1"

        # Should include PATH if it exists in system
        if "PATH" in os.environ:
            assert "PATH" in sanitized


class TestUnsupportedScriptTypes:
    """Tests for handling unsupported script types."""

    @pytest.mark.asyncio
    async def test_unsupported_script_type_subprocess(self, tmp_path: Path) -> None:
        """Test that unsupported script type raises error in subprocess mode."""
        skill_dir = tmp_path / "my-skill"
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir(parents=True)
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # Create unsupported script type
        script_path = scripts_dir / "test.rb"
        script_path.write_text("puts 'Hello from Ruby'")

        config = ScriptExecutionConfig(sandbox_mode=SandboxMode.SUBPROCESS)
        executor = ScriptExecutor(config)

        result = await executor.execute_script(
            script_path=str(script_path),
            skill_dir=str(skill_dir),
            workspace=str(workspace),
        )

        assert result.success is False
        assert "Unsupported script type" in result.output

    @pytest.mark.asyncio
    @patch(
        "docker.errors.ImageNotFound", new_callable=lambda: type("ImageNotFound", (Exception,), {})
    )
    @patch("docker.from_env")
    async def test_unsupported_script_type_docker(
        self, mock_from_env: Mock, mock_image_not_found: Mock, tmp_path: Path
    ) -> None:
        """Test that unsupported script type raises error in Docker mode."""
        skill_dir = tmp_path / "my-skill"
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir(parents=True)
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        script_path = scripts_dir / "test.rb"
        script_path.write_text("puts 'Hello'")

        # Mock Docker
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_from_env.return_value = mock_client

        config = ScriptExecutionConfig(sandbox_mode=SandboxMode.DOCKER)
        executor = ScriptExecutor(config)

        result = await executor.execute_script(
            script_path=str(script_path),
            skill_dir=str(skill_dir),
            workspace=str(workspace),
        )

        assert result.success is False
        assert "Unsupported script type" in result.output
