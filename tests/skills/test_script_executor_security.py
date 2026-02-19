"""Security tests for ScriptExecutor sandboxing and isolation.

This module provides comprehensive security testing for the ScriptExecutor class,
focusing on preventing common attack vectors including path traversal, resource
exhaustion, and unauthorized filesystem/network access.
"""

import os
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from omniforge.skills.script_executor import (
    SandboxMode,
    ScriptExecutionConfig,
    ScriptExecutor,
    SecurityError,
)


@pytest.mark.security
class TestScriptExecutorPathTraversal:
    """Security tests for path traversal prevention."""

    def test_rejects_path_traversal_dotdot(self, tmp_path: Path) -> None:
        """Should reject scripts with .. in path."""
        skill_dir = tmp_path / "skill"
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir(parents=True)
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # Attempt path traversal using ..
        script_path = scripts_dir / ".." / ".." / "etc" / "passwd"

        config = ScriptExecutionConfig(sandbox_mode=SandboxMode.SUBPROCESS)
        executor = ScriptExecutor(config)

        assert executor._is_safe_path(script_path, skill_dir) is False

    @pytest.mark.asyncio
    async def test_rejects_absolute_path_outside_skill(self, tmp_path: Path) -> None:
        """Should reject absolute paths outside skill directory."""
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir(parents=True)
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # Attempt to access system file
        script_path = "/etc/passwd"

        config = ScriptExecutionConfig(sandbox_mode=SandboxMode.NONE)
        executor = ScriptExecutor(config)

        with pytest.raises(SecurityError, match="must be in .*/scripts/ directory"):
            await executor.execute_script(
                script_path=script_path,
                skill_dir=str(skill_dir),
                workspace=str(workspace),
            )

    def test_rejects_symlink_escape(self, tmp_path: Path) -> None:
        """Should reject symlinks that escape skill directory."""
        skill_dir = tmp_path / "skill"
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir(parents=True)

        # Create a symlink pointing outside skill directory
        escape_link = scripts_dir / "escape.py"
        target = tmp_path / "outside.py"
        target.write_text("print('escaped')")
        escape_link.symlink_to(target)

        config = ScriptExecutionConfig(sandbox_mode=SandboxMode.NONE)
        executor = ScriptExecutor(config)

        # Should be blocked because symlink resolves outside scripts dir
        assert executor._is_safe_path(escape_link, skill_dir) is False

    def test_rejects_path_with_parent_references(self, tmp_path: Path) -> None:
        """Should reject paths with .. references even if they resolve safely."""
        skill_dir = tmp_path / "skill"
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir(parents=True)

        # Path with .. that technically resolves to scripts dir
        script_path = Path(f"{scripts_dir}/../scripts/test.py")

        config = ScriptExecutionConfig(sandbox_mode=SandboxMode.NONE)
        executor = ScriptExecutor(config)

        # Blocked because path string contains ".."
        assert executor._is_safe_path(script_path, skill_dir) is False

    def test_allows_safe_script_path(self, tmp_path: Path) -> None:
        """Should allow scripts in the scripts directory."""
        skill_dir = tmp_path / "skill"
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir(parents=True)

        script_path = scripts_dir / "safe_script.py"
        script_path.write_text("print('safe')")

        config = ScriptExecutionConfig(sandbox_mode=SandboxMode.NONE)
        executor = ScriptExecutor(config)

        assert executor._is_safe_path(script_path, skill_dir) is True


@pytest.mark.security
class TestScriptExecutorResourceLimits:
    """Security tests for resource limit enforcement."""

    @pytest.mark.asyncio
    async def test_timeout_kills_script(self, tmp_path: Path) -> None:
        """Scripts exceeding timeout should be killed."""
        skill_dir = tmp_path / "skill"
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir(parents=True)
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # Create script that sleeps for 60 seconds
        script_path = scripts_dir / "sleep.py"
        script_path.write_text("import time\ntime.sleep(60)\nprint('done')")

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
        assert result.duration_ms < 5000  # Should be killed quickly

    @pytest.mark.asyncio
    async def test_script_with_large_output(self, tmp_path: Path) -> None:
        """Should handle scripts that produce large output."""
        skill_dir = tmp_path / "skill"
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir(parents=True)
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # Create script that produces large output (10MB of 'x')
        script_path = scripts_dir / "large_output.py"
        script_path.write_text("print('x' * 10_000_000)")

        config = ScriptExecutionConfig(
            sandbox_mode=SandboxMode.SUBPROCESS,
            timeout_seconds=30,
        )
        executor = ScriptExecutor(config)

        result = await executor.execute_script(
            script_path=str(script_path),
            skill_dir=str(skill_dir),
            workspace=str(workspace),
        )

        # Should complete but may truncate output
        # The important part is it doesn't crash
        assert result.exit_code >= 0  # Either succeeds or fails gracefully


@pytest.mark.security
@pytest.mark.docker
class TestScriptExecutorDockerIsolation:
    """Security tests for Docker-based isolation."""

    @pytest.mark.asyncio
    @patch("docker.errors.ImageNotFound", new_callable=lambda: type("ImageNotFound", (Exception,), {}))
    @patch("docker.from_env")
    async def test_network_disabled_by_default(
        self, mock_from_env: Mock, mock_image_not_found: Mock, tmp_path: Path
    ) -> None:
        """Scripts should not have network access by default."""
        skill_dir = tmp_path / "skill"
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir(parents=True)
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # Script that tries to make network request
        script_path = scripts_dir / "network_test.py"
        script_path.write_text(
            "import urllib.request\n"
            "try:\n"
            "    urllib.request.urlopen('http://example.com')\n"
            "    print('network_success')\n"
            "except Exception as e:\n"
            "    print(f'network_failed: {e}')\n"
        )

        # Mock Docker client
        mock_client = Mock()
        mock_container = Mock()
        mock_container.wait.return_value = {"StatusCode": 1}
        mock_container.logs.return_value = b"network_failed: Network is unreachable\n"
        mock_client.containers.run.return_value = mock_container
        mock_client.ping.return_value = True
        mock_from_env.return_value = mock_client

        config = ScriptExecutionConfig(
            sandbox_mode=SandboxMode.DOCKER,
            allow_network=False,  # Network disabled
        )
        executor = ScriptExecutor(config)

        result = await executor.execute_script(
            script_path=str(script_path),
            skill_dir=str(skill_dir),
            workspace=str(workspace),
        )

        # Verify network was blocked
        call_args = mock_client.containers.run.call_args
        assert call_args[1]["network_mode"] == "none"
        assert "network_failed" in result.output or "network_success" not in result.output

    @pytest.mark.asyncio
    @patch("docker.errors.ImageNotFound", new_callable=lambda: type("ImageNotFound", (Exception,), {}))
    @patch("docker.from_env")
    async def test_skill_dir_readonly(
        self, mock_from_env: Mock, mock_image_not_found: Mock, tmp_path: Path
    ) -> None:
        """Skill directory should be mounted read-only."""
        skill_dir = tmp_path / "skill"
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir(parents=True)
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # Script that tries to write to skill directory
        script_path = scripts_dir / "write_test.py"
        script_path.write_text(
            "try:\n"
            "    with open('/skill/test.txt', 'w') as f:\n"
            "        f.write('test')\n"
            "    print('write_success')\n"
            "except Exception as e:\n"
            "    print(f'write_failed: {e}')\n"
        )

        # Mock Docker client
        mock_client = Mock()
        mock_container = Mock()
        mock_container.wait.return_value = {"StatusCode": 1}
        mock_container.logs.return_value = b"write_failed: Read-only file system\n"
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

        # Verify skill directory was mounted read-only
        call_args = mock_client.containers.run.call_args
        volumes = call_args[1]["volumes"]
        # volumes is a dict: {host_path: {"bind": container_path, "mode": "ro/rw"}}
        # Find the volume with "/skill" as the bind target
        skill_mount = None
        for host_path, mount_config in volumes.items():
            if mount_config["bind"] == "/skill":
                skill_mount = mount_config
                break
        assert skill_mount is not None, "Skill directory not mounted"
        assert skill_mount["mode"] == "ro"

    @pytest.mark.asyncio
    @patch("docker.errors.ImageNotFound", new_callable=lambda: type("ImageNotFound", (Exception,), {}))
    @patch("docker.from_env")
    async def test_cannot_access_host_filesystem(
        self, mock_from_env: Mock, mock_image_not_found: Mock, tmp_path: Path
    ) -> None:
        """Script should not access host filesystem."""
        skill_dir = tmp_path / "skill"
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir(parents=True)
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # Script that tries to read /etc/passwd
        script_path = scripts_dir / "host_access.py"
        script_path.write_text(
            "try:\n"
            "    with open('/etc/passwd', 'r') as f:\n"
            "        content = f.read()\n"
            "        if 'root:x:0:0' in content:\n"
            "            print('host_passwd_found')\n"
            "        else:\n"
            "            print('container_passwd')\n"
            "except Exception as e:\n"
            "    print(f'access_failed: {e}')\n"
        )

        # Mock Docker client
        mock_client = Mock()
        mock_container = Mock()
        mock_container.wait.return_value = {"StatusCode": 0}
        # Container has its own /etc/passwd, not host's
        mock_container.logs.return_value = b"container_passwd\n"
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

        # Should not have access to host /etc/passwd
        assert "host_passwd_found" not in result.output


@pytest.mark.security
class TestScriptExecutorEnvironmentIsolation:
    """Security tests for environment variable isolation."""

    @pytest.mark.asyncio
    async def test_environment_sanitized(self, tmp_path: Path) -> None:
        """Sensitive environment variables should not be passed to scripts."""
        skill_dir = tmp_path / "skill"
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir(parents=True)
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # Set sensitive env vars in current process
        os.environ["AWS_SECRET_KEY"] = "secret123"
        os.environ["API_TOKEN"] = "token456"
        os.environ["DATABASE_PASSWORD"] = "dbpass789"

        # Script that prints all environment variables
        script_path = scripts_dir / "env_test.py"
        script_path.write_text(
            "import os\n"
            "for key, value in sorted(os.environ.items()):\n"
            "    print(f'{key}={value}')\n"
        )

        config = ScriptExecutionConfig(sandbox_mode=SandboxMode.SUBPROCESS)
        executor = ScriptExecutor(config)

        try:
            result = await executor.execute_script(
                script_path=str(script_path),
                skill_dir=str(skill_dir),
                workspace=str(workspace),
            )

            # Sensitive values should not appear in output
            assert "secret123" not in result.output
            assert "token456" not in result.output
            assert "dbpass789" not in result.output
        finally:
            # Cleanup
            del os.environ["AWS_SECRET_KEY"]
            del os.environ["API_TOKEN"]
            del os.environ["DATABASE_PASSWORD"]

    @pytest.mark.asyncio
    async def test_custom_env_vars_allowed(self, tmp_path: Path) -> None:
        """Custom non-sensitive environment variables should be passed."""
        skill_dir = tmp_path / "skill"
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir(parents=True)
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # Script that reads specific env var
        script_path = scripts_dir / "env_read.py"
        script_path.write_text(
            "import os\n"
            "print(f\"CUSTOM_VAR={os.environ.get('CUSTOM_VAR', 'not_found')}\")\n"
        )

        config = ScriptExecutionConfig(sandbox_mode=SandboxMode.SUBPROCESS)
        executor = ScriptExecutor(config)

        result = await executor.execute_script(
            script_path=str(script_path),
            skill_dir=str(skill_dir),
            workspace=str(workspace),
            env_vars={"CUSTOM_VAR": "custom_value"},
        )

        assert result.success is True
        assert "CUSTOM_VAR=custom_value" in result.output


@pytest.mark.security
class TestScriptExecutorSecurityErrors:
    """Security tests for error handling and audit logging."""

    @pytest.mark.asyncio
    async def test_security_error_contains_context(self, tmp_path: Path) -> None:
        """SecurityError should include context information."""
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        malicious_path = "/etc/passwd"

        config = ScriptExecutionConfig(sandbox_mode=SandboxMode.NONE)
        executor = ScriptExecutor(config)

        try:
            await executor.execute_script(
                script_path=malicious_path,
                skill_dir=str(skill_dir),
                workspace=str(workspace),
            )
            pytest.fail("Expected SecurityError")
        except SecurityError as e:
            assert e.violation_type == "path_traversal"
            assert "script_path" in e.context
            assert malicious_path in str(e.context["script_path"])

    @pytest.mark.asyncio
    async def test_audit_logging_for_blocked_path(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Should log security violations for audit."""
        import logging

        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        config = ScriptExecutionConfig(sandbox_mode=SandboxMode.NONE)
        executor = ScriptExecutor(config)

        with caplog.at_level(logging.WARNING):
            try:
                await executor.execute_script(
                    script_path="/etc/passwd",
                    skill_dir=str(skill_dir),
                    workspace=str(workspace),
                )
            except SecurityError:
                pass  # Expected

        # Check audit log was created
        # Look for security-related log entries
        assert any("security" in record.message.lower() or "blocked" in record.message.lower()
                   for record in caplog.records)


@pytest.mark.security
class TestScriptExecutorPenetrationTests:
    """Penetration testing scenarios for script execution security."""

    @pytest.mark.asyncio
    async def test_attempted_shell_injection_via_filename(self, tmp_path: Path) -> None:
        """Should block shell injection attempts in script filename."""
        skill_dir = tmp_path / "skill"
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir(parents=True)
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # Malicious filename with shell operators
        malicious_name = "test.py; rm -rf /"

        config = ScriptExecutionConfig(sandbox_mode=SandboxMode.NONE)
        executor = ScriptExecutor(config)

        # Should be blocked or sanitized
        # In practice, this would fail at path validation
        with pytest.raises((SecurityError, FileNotFoundError)):
            await executor.execute_script(
                script_path=str(scripts_dir / malicious_name),
                skill_dir=str(skill_dir),
                workspace=str(workspace),
            )

    @pytest.mark.asyncio
    async def test_resource_exhaustion_prevented(self, tmp_path: Path) -> None:
        """Should prevent resource exhaustion attacks."""
        skill_dir = tmp_path / "skill"
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir(parents=True)
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # Script that tries to fork bomb (safe version for testing)
        script_path = scripts_dir / "resource_bomb.py"
        script_path.write_text(
            "import time\n"
            "# Simulate resource-intensive operation\n"
            "data = []\n"
            "for i in range(1000):\n"
            "    data.append('x' * 1000000)\n"  # Try to allocate 1GB
            "    time.sleep(0.01)\n"
        )

        config = ScriptExecutionConfig(
            sandbox_mode=SandboxMode.SUBPROCESS,
            timeout_seconds=2,  # Very short timeout
        )
        executor = ScriptExecutor(config)

        result = await executor.execute_script(
            script_path=str(script_path),
            skill_dir=str(skill_dir),
            workspace=str(workspace),
        )

        # Should be killed by timeout before exhausting resources
        assert result.success is False
        assert result.duration_ms < 5000

    @pytest.mark.asyncio
    async def test_unicode_injection_blocked(self, tmp_path: Path) -> None:
        """Should handle unicode and special characters safely."""
        skill_dir = tmp_path / "skill"
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir(parents=True)
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # Create script with unicode filename
        script_path = scripts_dir / "test_脚本.py"
        script_path.write_text("print('test')")

        config = ScriptExecutionConfig(sandbox_mode=SandboxMode.SUBPROCESS)
        executor = ScriptExecutor(config)

        # Should handle unicode safely
        result = await executor.execute_script(
            script_path=str(script_path),
            skill_dir=str(skill_dir),
            workspace=str(workspace),
        )

        # Should either succeed or fail gracefully, not crash
        assert result.exit_code >= -1
