"""Unit tests for SkillContext."""

from pathlib import Path

import pytest

from omniforge.skills.context import SkillContext
from omniforge.skills.errors import SkillScriptReadError, SkillToolNotAllowedError
from omniforge.skills.models import Skill, SkillMetadata


class TestSkillContext:
    """Tests for SkillContext class."""

    def test_create_context_with_skill(self) -> None:
        """SkillContext should initialize with skill and executor."""
        metadata = SkillMetadata(name="test-skill", description="Test")
        skill = Skill(
            metadata=metadata,
            content="# Test",
            path=Path("/skills/test.md"),
            base_path=Path("/skills"),
            storage_layer="global",
        )

        context = SkillContext(skill=skill)
        assert context.skill == skill
        assert context.executor is None
        assert context._allowed_tools is None

    def test_context_manager_sets_up_allowed_tools(self) -> None:
        """Context manager should initialize allowed_tools set."""
        metadata = SkillMetadata(
            name="test-skill",
            description="Test",
            allowed_tools=["Bash", "Read", "Write"],
        )
        skill = Skill(
            metadata=metadata,
            content="# Test",
            path=Path("/skills/test.md"),
            base_path=Path("/skills"),
            storage_layer="global",
        )

        context = SkillContext(skill=skill)
        assert context._allowed_tools is None  # Not set yet

        with context:
            # Inside context, allowed_tools should be set as lowercase set
            assert context._allowed_tools == {
                "bash",
                "read",
                "write",
            }  # Case will fail, let me check

    def test_context_manager_clears_state_on_exit(self) -> None:
        """Context manager should clear allowed tools on exit."""
        metadata = SkillMetadata(
            name="test-skill",
            description="Test",
            allowed_tools=["Bash", "Read"],
        )
        skill = Skill(
            metadata=metadata,
            content="# Test",
            path=Path("/skills/test.md"),
            base_path=Path("/skills"),
            storage_layer="global",
        )

        context = SkillContext(skill=skill, executor=None)

        # Before entering context
        assert context._allowed_tools is None

        with context:
            # Inside context, tools should be set
            assert context._allowed_tools is not None

        # After exiting, should be cleared
        assert context._allowed_tools is None

    def test_context_manager_with_no_restrictions(self) -> None:
        """Context manager should handle None allowed_tools (unrestricted)."""
        metadata = SkillMetadata(name="test-skill", description="Test")
        skill = Skill(
            metadata=metadata,
            content="# Test",
            path=Path("/skills/test.md"),
            base_path=Path("/skills"),
            storage_layer="global",
        )

        context = SkillContext(skill=skill)

        with context:
            # Should remain None for unrestricted skills
            assert context._allowed_tools is None

    def test_check_tool_allowed_passes_for_allowed_tool(self) -> None:
        """check_tool_allowed should not raise for tools in allowed_tools."""
        metadata = SkillMetadata(
            name="test-skill",
            description="Test",
            allowed_tools=["Bash", "Read", "Write"],
        )
        skill = Skill(
            metadata=metadata,
            content="# Test",
            path=Path("/skills/test.md"),
            base_path=Path("/skills"),
            storage_layer="global",
        )

        with SkillContext(skill=skill) as context:
            # Should not raise for allowed tools
            context.check_tool_allowed("Bash")
            context.check_tool_allowed("Read")
            context.check_tool_allowed("Write")

    def test_check_tool_allowed_is_case_insensitive(self) -> None:
        """check_tool_allowed should handle case-insensitive matching."""
        metadata = SkillMetadata(
            name="test-skill",
            description="Test",
            allowed_tools=["Bash", "Read"],
        )
        skill = Skill(
            metadata=metadata,
            content="# Test",
            path=Path("/skills/test.md"),
            base_path=Path("/skills"),
            storage_layer="global",
        )

        with SkillContext(skill=skill) as context:
            # All case variations should work
            context.check_tool_allowed("bash")
            context.check_tool_allowed("BASH")
            context.check_tool_allowed("BaSh")
            context.check_tool_allowed("read")
            context.check_tool_allowed("READ")

    def test_check_tool_allowed_raises_for_disallowed_tool(self) -> None:
        """check_tool_allowed should raise SkillToolNotAllowedError for blocked tools."""
        metadata = SkillMetadata(
            name="test-skill",
            description="Test",
            allowed_tools=["Bash", "Read"],
        )
        skill = Skill(
            metadata=metadata,
            content="# Test",
            path=Path("/skills/test.md"),
            base_path=Path("/skills"),
            storage_layer="global",
        )

        with SkillContext(skill=skill) as context:
            with pytest.raises(SkillToolNotAllowedError) as exc_info:
                context.check_tool_allowed("Write")

            error = exc_info.value
            assert error.skill_name == "test-skill"
            assert error.tool_name == "Write"
            assert error.allowed_tools == ["Bash", "Read"]
            assert "Write" in error.message
            assert "Bash, Read" in error.message

    def test_check_tool_allowed_passes_when_no_restrictions(self) -> None:
        """check_tool_allowed should allow all tools when allowed_tools is None."""
        metadata = SkillMetadata(name="test-skill", description="Test")
        skill = Skill(
            metadata=metadata,
            content="# Test",
            path=Path("/skills/test.md"),
            base_path=Path("/skills"),
            storage_layer="global",
        )

        with SkillContext(skill=skill) as context:
            # Should allow any tool when unrestricted
            context.check_tool_allowed("Bash")
            context.check_tool_allowed("Read")
            context.check_tool_allowed("Write")
            context.check_tool_allowed("AnyTool")

    def test_check_tool_arguments_allows_non_read_tools(self) -> None:
        """check_tool_arguments should only validate Read tool."""
        metadata = SkillMetadata(name="test-skill", description="Test")
        skill = Skill(
            metadata=metadata,
            content="# Test",
            path=Path("/skills/test.md"),
            base_path=Path("/skills"),
            storage_layer="global",
            script_paths={"pre": Path("/skills/pre.sh")},
        )

        with SkillContext(skill=skill) as context:
            # Non-Read tools should pass without validation
            context.check_tool_arguments("Bash", {"command": "echo hello"})
            context.check_tool_arguments("Write", {"file_path": "/skills/pre.sh"})

    def test_check_tool_arguments_allows_read_non_script_files(self) -> None:
        """check_tool_arguments should allow Read tool on non-script files."""
        metadata = SkillMetadata(name="test-skill", description="Test")
        skill = Skill(
            metadata=metadata,
            content="# Test",
            path=Path("/skills/test.md"),
            base_path=Path("/skills"),
            storage_layer="global",
            script_paths={"pre": Path("/skills/scripts/pre.sh")},
        )

        with SkillContext(skill=skill) as context:
            # Reading non-script files should be allowed
            context.check_tool_arguments("Read", {"file_path": "/skills/test.md"})
            context.check_tool_arguments("Read", {"file_path": "/skills/other.py"})
            context.check_tool_arguments("read", {"file_path": "/tmp/data.json"})

    def test_check_tool_arguments_blocks_read_on_script_files(self) -> None:
        """check_tool_arguments should block Read tool on skill hook scripts."""
        metadata = SkillMetadata(name="test-skill", description="Test")
        pre_script = Path("/skills/scripts/pre.sh")
        skill = Skill(
            metadata=metadata,
            content="# Test",
            path=Path("/skills/test.md"),
            base_path=Path("/skills"),
            storage_layer="global",
            script_paths={"pre": pre_script},
        )

        with SkillContext(skill=skill) as context:
            with pytest.raises(SkillScriptReadError) as exc_info:
                context.check_tool_arguments("Read", {"file_path": str(pre_script)})

            error = exc_info.value
            assert error.skill_name == "test-skill"
            assert error.script_type == "hook"
            assert str(pre_script) in error.script_path
            assert "context efficiency" in error.message.lower()

    def test_check_tool_arguments_is_case_insensitive_for_tool_name(self) -> None:
        """check_tool_arguments should handle case-insensitive tool name matching."""
        metadata = SkillMetadata(name="test-skill", description="Test")
        pre_script = Path("/skills/scripts/pre.sh")
        skill = Skill(
            metadata=metadata,
            content="# Test",
            path=Path("/skills/test.md"),
            base_path=Path("/skills"),
            storage_layer="global",
            script_paths={"pre": pre_script},
        )

        with SkillContext(skill=skill) as context:
            # All case variations should trigger script check
            for tool_name in ["read", "Read", "READ", "ReAd"]:
                with pytest.raises(SkillScriptReadError):
                    context.check_tool_arguments(tool_name, {"file_path": str(pre_script)})

    def test_check_tool_arguments_handles_missing_file_path(self) -> None:
        """check_tool_arguments should handle Read tool without file_path argument."""
        metadata = SkillMetadata(name="test-skill", description="Test")
        skill = Skill(
            metadata=metadata,
            content="# Test",
            path=Path("/skills/test.md"),
            base_path=Path("/skills"),
            storage_layer="global",
            script_paths={"pre": Path("/skills/pre.sh")},
        )

        with SkillContext(skill=skill) as context:
            # Should not raise when file_path is missing
            context.check_tool_arguments("Read", {})
            context.check_tool_arguments("Read", {"other_arg": "value"})

    def test_check_tool_arguments_handles_skill_without_scripts(self) -> None:
        """check_tool_arguments should handle skills without hook scripts."""
        metadata = SkillMetadata(name="test-skill", description="Test")
        skill = Skill(
            metadata=metadata,
            content="# Test",
            path=Path("/skills/test.md"),
            base_path=Path("/skills"),
            storage_layer="global",
        )

        with SkillContext(skill=skill) as context:
            # Should not raise for any file when no scripts exist
            context.check_tool_arguments("Read", {"file_path": "/any/file.sh"})

    def test_is_restricted_returns_true_when_tools_limited(self) -> None:
        """is_restricted should return True when allowed_tools is set."""
        metadata = SkillMetadata(
            name="test-skill",
            description="Test",
            allowed_tools=["Bash", "Read"],
        )
        skill = Skill(
            metadata=metadata,
            content="# Test",
            path=Path("/skills/test.md"),
            base_path=Path("/skills"),
            storage_layer="global",
        )

        with SkillContext(skill=skill) as context:
            assert context.is_restricted is True

    def test_is_restricted_returns_false_when_no_limits(self) -> None:
        """is_restricted should return False when allowed_tools is None."""
        metadata = SkillMetadata(name="test-skill", description="Test")
        skill = Skill(
            metadata=metadata,
            content="# Test",
            path=Path("/skills/test.md"),
            base_path=Path("/skills"),
            storage_layer="global",
        )

        with SkillContext(skill=skill) as context:
            assert context.is_restricted is False

    def test_allowed_tool_names_returns_set_when_restricted(self) -> None:
        """allowed_tool_names should return original case tool names when restricted."""
        metadata = SkillMetadata(
            name="test-skill",
            description="Test",
            allowed_tools=["Bash", "Read", "Write"],
        )
        skill = Skill(
            metadata=metadata,
            content="# Test",
            path=Path("/skills/test.md"),
            base_path=Path("/skills"),
            storage_layer="global",
        )

        with SkillContext(skill=skill) as context:
            allowed = context.allowed_tool_names
            assert allowed == {"Bash", "Read", "Write"}

    def test_allowed_tool_names_returns_none_when_unrestricted(self) -> None:
        """allowed_tool_names should return None when no restrictions."""
        metadata = SkillMetadata(name="test-skill", description="Test")
        skill = Skill(
            metadata=metadata,
            content="# Test",
            path=Path("/skills/test.md"),
            base_path=Path("/skills"),
            storage_layer="global",
        )

        with SkillContext(skill=skill) as context:
            assert context.allowed_tool_names is None

    def test_context_with_empty_allowed_tools_list(self) -> None:
        """SkillContext should handle empty allowed_tools list (block all tools)."""
        metadata = SkillMetadata(
            name="test-skill",
            description="Test",
            allowed_tools=[],
        )
        skill = Skill(
            metadata=metadata,
            content="# Test",
            path=Path("/skills/test.md"),
            base_path=Path("/skills"),
            storage_layer="global",
        )

        with SkillContext(skill=skill) as context:
            assert context.is_restricted is True
            assert context.allowed_tool_names == set()

            # Should block all tools when list is empty
            with pytest.raises(SkillToolNotAllowedError):
                context.check_tool_allowed("Bash")

    def test_script_read_blocking_with_multiple_scripts(self) -> None:
        """check_tool_arguments should block reads on any hook script."""
        metadata = SkillMetadata(name="test-skill", description="Test")
        pre_script = Path("/skills/scripts/pre.sh")
        post_script = Path("/skills/scripts/post.sh")
        skill = Skill(
            metadata=metadata,
            content="# Test",
            path=Path("/skills/test.md"),
            base_path=Path("/skills"),
            storage_layer="global",
            script_paths={"pre": pre_script, "post": post_script},
        )

        with SkillContext(skill=skill) as context:
            # Both scripts should be blocked
            with pytest.raises(SkillScriptReadError):
                context.check_tool_arguments("Read", {"file_path": str(pre_script)})

            with pytest.raises(SkillScriptReadError):
                context.check_tool_arguments("Read", {"file_path": str(post_script)})

    def test_error_message_provides_helpful_guidance(self) -> None:
        """SkillToolNotAllowedError should provide helpful error message."""
        metadata = SkillMetadata(
            name="test-skill",
            description="Test",
            allowed_tools=["Bash", "Read"],
        )
        skill = Skill(
            metadata=metadata,
            content="# Test",
            path=Path("/skills/test.md"),
            base_path=Path("/skills"),
            storage_layer="global",
        )

        with SkillContext(skill=skill) as context:
            with pytest.raises(SkillToolNotAllowedError) as exc_info:
                context.check_tool_allowed("WebSearch")

            # Check that error provides helpful guidance
            error_msg = str(exc_info.value)
            assert "test-skill" in error_msg
            assert "WebSearch" in error_msg
            assert "Allowed tools" in error_msg
            assert "Bash" in error_msg
            assert "Read" in error_msg

    def test_script_read_error_message_explains_reason(self) -> None:
        """SkillScriptReadError should explain why reading is blocked."""
        metadata = SkillMetadata(name="test-skill", description="Test")
        script_path = Path("/skills/scripts/pre.sh")
        skill = Skill(
            metadata=metadata,
            content="# Test",
            path=Path("/skills/test.md"),
            base_path=Path("/skills"),
            storage_layer="global",
            script_paths={"pre": script_path},
        )

        with SkillContext(skill=skill) as context:
            with pytest.raises(SkillScriptReadError) as exc_info:
                context.check_tool_arguments("Read", {"file_path": str(script_path)})

            # Check that error explains the restriction
            error = exc_info.value
            assert "context efficiency" in error.reason.lower()
            assert "hook scripts" in error.reason.lower()
            assert "executed automatically" in error.reason.lower()
