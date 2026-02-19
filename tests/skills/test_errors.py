"""Unit tests for Skills System exceptions."""

import pytest

from omniforge.skills.errors import (
    SkillActivationError,
    SkillError,
    SkillNotFoundError,
    SkillParseError,
    SkillScriptReadError,
    SkillToolNotAllowedError,
)


class TestSkillError:
    """Tests for SkillError base exception."""

    def test_create_skill_error_with_required_fields(self) -> None:
        """SkillError should initialize with message and error_code."""
        error = SkillError(message="Test error", error_code="test_error")
        assert error.message == "Test error"
        assert error.error_code == "test_error"
        assert error.context == {}
        assert str(error) == "Test error"

    def test_create_skill_error_with_context(self) -> None:
        """SkillError should accept optional context dictionary."""
        context = {"skill_name": "test-skill", "layer": "global"}
        error = SkillError(
            message="Test error",
            error_code="test_error",
            context=context,
        )
        assert error.context == context
        assert error.context["skill_name"] == "test-skill"
        assert error.context["layer"] == "global"

    def test_skill_error_is_exception(self) -> None:
        """SkillError should be an instance of Exception."""
        error = SkillError(message="Test", error_code="test")
        assert isinstance(error, Exception)


class TestSkillNotFoundError:
    """Tests for SkillNotFoundError exception."""

    def test_create_error_with_skill_name_only(self) -> None:
        """SkillNotFoundError should initialize with skill name."""
        error = SkillNotFoundError(skill_name="test-skill")
        assert error.skill_name == "test-skill"
        assert error.storage_layer is None
        assert error.error_code == "skill_not_found"
        assert "test-skill" in error.message
        assert "not found" in error.message

    def test_create_error_with_storage_layer(self) -> None:
        """SkillNotFoundError should include storage layer in message."""
        error = SkillNotFoundError(skill_name="test-skill", storage_layer="tenant-123")
        assert error.skill_name == "test-skill"
        assert error.storage_layer == "tenant-123"
        assert "test-skill" in error.message
        assert "tenant-123" in error.message

    def test_error_context_contains_skill_name(self) -> None:
        """SkillNotFoundError context should contain skill_name."""
        error = SkillNotFoundError(skill_name="test-skill")
        assert error.context["skill_name"] == "test-skill"

    def test_error_context_contains_storage_layer(self) -> None:
        """SkillNotFoundError context should contain storage_layer when provided."""
        error = SkillNotFoundError(skill_name="test-skill", storage_layer="global")
        assert error.context["skill_name"] == "test-skill"
        assert error.context["storage_layer"] == "global"

    def test_error_is_skill_error(self) -> None:
        """SkillNotFoundError should be an instance of SkillError."""
        error = SkillNotFoundError(skill_name="test-skill")
        assert isinstance(error, SkillError)


class TestSkillParseError:
    """Tests for SkillParseError exception."""

    def test_create_error_with_path_and_reason(self) -> None:
        """SkillParseError should initialize with path and reason."""
        error = SkillParseError(
            skill_path="/skills/test.md",
            reason="Invalid YAML frontmatter",
        )
        assert error.skill_path == "/skills/test.md"
        assert error.reason == "Invalid YAML frontmatter"
        assert error.line_number is None
        assert error.error_code == "skill_parse_error"
        assert "/skills/test.md" in error.message
        assert "Invalid YAML frontmatter" in error.message

    def test_create_error_with_line_number(self) -> None:
        """SkillParseError should include line number in message when provided."""
        error = SkillParseError(
            skill_path="/skills/test.md",
            reason="Unexpected token",
            line_number=42,
        )
        assert error.line_number == 42
        assert "line 42" in error.message
        assert "Unexpected token" in error.message

    def test_error_context_contains_all_fields(self) -> None:
        """SkillParseError context should contain all relevant fields."""
        error = SkillParseError(
            skill_path="/skills/test.md",
            reason="Parse failure",
            line_number=10,
        )
        assert error.context["skill_path"] == "/skills/test.md"
        assert error.context["reason"] == "Parse failure"
        assert error.context["line_number"] == 10

    def test_error_is_skill_error(self) -> None:
        """SkillParseError should be an instance of SkillError."""
        error = SkillParseError(skill_path="/test.md", reason="Test")
        assert isinstance(error, SkillError)


class TestSkillToolNotAllowedError:
    """Tests for SkillToolNotAllowedError exception."""

    def test_create_error_with_skill_and_tool(self) -> None:
        """SkillToolNotAllowedError should initialize with skill and tool names."""
        error = SkillToolNotAllowedError(skill_name="test-skill", tool_name="forbidden-tool")
        assert error.skill_name == "test-skill"
        assert error.tool_name == "forbidden-tool"
        assert error.allowed_tools is None
        assert error.error_code == "skill_tool_not_allowed"
        assert "test-skill" in error.message
        assert "forbidden-tool" in error.message

    def test_create_error_with_allowed_tools_list(self) -> None:
        """SkillToolNotAllowedError should include allowed tools in message."""
        error = SkillToolNotAllowedError(
            skill_name="test-skill",
            tool_name="forbidden-tool",
            allowed_tools=["tool1", "tool2"],
        )
        assert error.allowed_tools == ["tool1", "tool2"]
        assert "tool1" in error.message
        assert "tool2" in error.message

    def test_error_message_when_no_tools_allowed(self) -> None:
        """SkillToolNotAllowedError should indicate when no tools are allowed."""
        error = SkillToolNotAllowedError(
            skill_name="test-skill",
            tool_name="any-tool",
            allowed_tools=[],
        )
        assert "No tools are allowed" in error.message

    def test_error_context_contains_all_fields(self) -> None:
        """SkillToolNotAllowedError context should contain relevant fields."""
        error = SkillToolNotAllowedError(
            skill_name="test-skill",
            tool_name="tool-x",
            allowed_tools=["tool1", "tool2"],
        )
        assert error.context["skill_name"] == "test-skill"
        assert error.context["tool_name"] == "tool-x"
        assert error.context["allowed_tools"] == ["tool1", "tool2"]

    def test_error_is_skill_error(self) -> None:
        """SkillToolNotAllowedError should be an instance of SkillError."""
        error = SkillToolNotAllowedError(skill_name="test", tool_name="tool")
        assert isinstance(error, SkillError)


class TestSkillActivationError:
    """Tests for SkillActivationError exception."""

    def test_create_error_with_skill_and_reason(self) -> None:
        """SkillActivationError should initialize with skill name and reason."""
        error = SkillActivationError(
            skill_name="test-skill",
            reason="Scope restriction: not available for this agent",
        )
        assert error.skill_name == "test-skill"
        assert error.reason == "Scope restriction: not available for this agent"
        assert error.error_code == "skill_activation_error"
        assert "test-skill" in error.message
        assert "Scope restriction" in error.message

    def test_error_context_contains_skill_and_reason(self) -> None:
        """SkillActivationError context should contain skill_name and reason."""
        error = SkillActivationError(
            skill_name="test-skill",
            reason="Missing dependency",
        )
        assert error.context["skill_name"] == "test-skill"
        assert error.context["reason"] == "Missing dependency"

    def test_error_is_skill_error(self) -> None:
        """SkillActivationError should be an instance of SkillError."""
        error = SkillActivationError(skill_name="test", reason="Test reason")
        assert isinstance(error, SkillError)


class TestSkillScriptReadError:
    """Tests for SkillScriptReadError exception."""

    def test_create_error_with_all_fields(self) -> None:
        """SkillScriptReadError should initialize with all required fields."""
        error = SkillScriptReadError(
            skill_name="test-skill",
            script_type="pre",
            script_path="/skills/scripts/pre.sh",
            reason="Permission denied",
        )
        assert error.skill_name == "test-skill"
        assert error.script_type == "pre"
        assert error.script_path == "/skills/scripts/pre.sh"
        assert error.reason == "Permission denied"
        assert error.error_code == "skill_script_read_error"
        assert "test-skill" in error.message
        assert "pre" in error.message
        assert "/skills/scripts/pre.sh" in error.message
        assert "Permission denied" in error.message

    def test_create_error_for_post_hook(self) -> None:
        """SkillScriptReadError should work with post hook scripts."""
        error = SkillScriptReadError(
            skill_name="test-skill",
            script_type="post",
            script_path="/skills/scripts/post.sh",
            reason="File not found",
        )
        assert error.script_type == "post"
        assert "post" in error.message

    def test_error_context_contains_all_fields(self) -> None:
        """SkillScriptReadError context should contain all relevant fields."""
        error = SkillScriptReadError(
            skill_name="test-skill",
            script_type="pre",
            script_path="/path/to/script.sh",
            reason="Encoding error",
        )
        assert error.context["skill_name"] == "test-skill"
        assert error.context["script_type"] == "pre"
        assert error.context["script_path"] == "/path/to/script.sh"
        assert error.context["reason"] == "Encoding error"

    def test_error_is_skill_error(self) -> None:
        """SkillScriptReadError should be an instance of SkillError."""
        error = SkillScriptReadError(
            skill_name="test",
            script_type="pre",
            script_path="/test.sh",
            reason="Test",
        )
        assert isinstance(error, SkillError)


class TestExceptionHierarchy:
    """Tests for exception inheritance hierarchy."""

    def test_all_skill_exceptions_inherit_from_skill_error(self) -> None:
        """All skill exceptions should inherit from SkillError."""
        exceptions = [
            SkillNotFoundError("test"),
            SkillParseError("/test.md", "reason"),
            SkillToolNotAllowedError("skill", "tool"),
            SkillActivationError("skill", "reason"),
            SkillScriptReadError("skill", "pre", "/script.sh", "reason"),
        ]
        for exc in exceptions:
            assert isinstance(exc, SkillError)
            assert isinstance(exc, Exception)

    def test_all_skill_exceptions_have_error_code(self) -> None:
        """All skill exceptions should have an error_code attribute."""
        exceptions = [
            SkillNotFoundError("test"),
            SkillParseError("/test.md", "reason"),
            SkillToolNotAllowedError("skill", "tool"),
            SkillActivationError("skill", "reason"),
            SkillScriptReadError("skill", "pre", "/script.sh", "reason"),
        ]
        for exc in exceptions:
            assert hasattr(exc, "error_code")
            assert isinstance(exc.error_code, str)
            assert len(exc.error_code) > 0

    def test_all_skill_exceptions_have_context(self) -> None:
        """All skill exceptions should have a context attribute."""
        exceptions = [
            SkillNotFoundError("test"),
            SkillParseError("/test.md", "reason"),
            SkillToolNotAllowedError("skill", "tool"),
            SkillActivationError("skill", "reason"),
            SkillScriptReadError("skill", "pre", "/script.sh", "reason"),
        ]
        for exc in exceptions:
            assert hasattr(exc, "context")
            assert isinstance(exc.context, dict)

    def test_skill_exceptions_can_be_caught_as_skill_error(self) -> None:
        """All skill exceptions should be catchable as SkillError."""
        with pytest.raises(SkillError):
            raise SkillNotFoundError("test")

        with pytest.raises(SkillError):
            raise SkillParseError("/test.md", "reason")

        with pytest.raises(SkillError):
            raise SkillToolNotAllowedError("skill", "tool")

        with pytest.raises(SkillError):
            raise SkillActivationError("skill", "reason")

        with pytest.raises(SkillError):
            raise SkillScriptReadError("skill", "pre", "/script.sh", "reason")
