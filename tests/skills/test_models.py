"""Unit tests for Skills System models."""

import warnings
from pathlib import Path

import pytest
from pydantic import ValidationError

from omniforge.skills.models import (
    ContextMode,
    HookDefinition,
    HookMatcher,
    Skill,
    SkillHooks,
    SkillIndexEntry,
    SkillMetadata,
    SkillScope,
)


class TestContextMode:
    """Tests for ContextMode enum."""

    def test_context_mode_values(self) -> None:
        """ContextMode should have INHERIT and FORK values."""
        assert ContextMode.INHERIT == "inherit"
        assert ContextMode.FORK == "fork"


class TestHookDefinition:
    """Tests for HookDefinition model."""

    def test_create_hook_definition_minimal(self) -> None:
        """HookDefinition should initialize with command only."""
        hook = HookDefinition(command="./scripts/test.sh")
        assert hook.type == "command"
        assert hook.command == "./scripts/test.sh"
        assert hook.once is False

    def test_create_hook_definition_with_once(self) -> None:
        """HookDefinition should accept once flag."""
        hook = HookDefinition(command="./scripts/test.sh", once=True)
        assert hook.once is True

    def test_create_hook_definition_with_custom_type(self) -> None:
        """HookDefinition should accept custom type."""
        hook = HookDefinition(type="custom", command="./scripts/test.sh")
        assert hook.type == "custom"


class TestHookMatcher:
    """Tests for HookMatcher model."""

    def test_create_hook_matcher_without_matcher(self) -> None:
        """HookMatcher should work without a matcher (applies to all tools)."""
        hook = HookDefinition(command="./scripts/test.sh")
        matcher = HookMatcher(hooks=[hook])
        assert matcher.matcher is None
        assert len(matcher.hooks) == 1
        assert matcher.hooks[0].command == "./scripts/test.sh"

    def test_create_hook_matcher_with_tool_matcher(self) -> None:
        """HookMatcher should accept tool matcher."""
        hook = HookDefinition(command="./scripts/security-check.sh")
        matcher = HookMatcher(matcher="Bash", hooks=[hook])
        assert matcher.matcher == "Bash"
        assert len(matcher.hooks) == 1

    def test_create_hook_matcher_with_multiple_hooks(self) -> None:
        """HookMatcher should accept multiple hooks."""
        hooks = [
            HookDefinition(command="./scripts/check1.sh"),
            HookDefinition(command="./scripts/check2.sh", once=True),
        ]
        matcher = HookMatcher(matcher="Read", hooks=hooks)
        assert len(matcher.hooks) == 2
        assert matcher.hooks[1].once is True


class TestSkillHooks:
    """Tests for SkillHooks model."""

    def test_create_empty_hooks(self) -> None:
        """SkillHooks should initialize with no scripts."""
        hooks = SkillHooks()
        assert hooks.pre is None
        assert hooks.post is None
        assert hooks.PreToolUse is None
        assert hooks.PostToolUse is None
        assert hooks.Stop is None

    # Legacy format tests (deprecated but still supported)
    def test_create_hooks_with_pre_script_legacy(self) -> None:
        """SkillHooks should accept legacy pre script path."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            hooks = SkillHooks(pre="scripts/pre.sh")
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "deprecated" in str(w[0].message).lower()

        assert hooks.pre == "scripts/pre.sh"
        assert hooks.post is None
        # Should auto-migrate to new format
        assert hooks.PreToolUse is not None
        assert len(hooks.PreToolUse) == 1
        assert hooks.PreToolUse[0].hooks[0].command == "scripts/pre.sh"

    def test_create_hooks_with_post_script_legacy(self) -> None:
        """SkillHooks should accept legacy post script path."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            hooks = SkillHooks(post="scripts/post.sh")
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)

        assert hooks.pre is None
        assert hooks.post == "scripts/post.sh"
        # Should auto-migrate to new format
        assert hooks.PostToolUse is not None
        assert len(hooks.PostToolUse) == 1
        assert hooks.PostToolUse[0].hooks[0].command == "scripts/post.sh"

    def test_create_hooks_with_both_scripts_legacy(self) -> None:
        """SkillHooks should accept both legacy pre and post scripts."""
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            hooks = SkillHooks(pre="scripts/pre.sh", post="scripts/post.sh")

        assert hooks.pre == "scripts/pre.sh"
        assert hooks.post == "scripts/post.sh"
        # Should auto-migrate both to new format
        assert hooks.PreToolUse is not None
        assert hooks.PostToolUse is not None

    # New Claude Code format tests
    def test_create_hooks_with_pretooluse(self) -> None:
        """SkillHooks should accept PreToolUse hooks."""
        hook_def = HookDefinition(command="./scripts/pre.sh")
        matcher = HookMatcher(hooks=[hook_def])
        hooks = SkillHooks(PreToolUse=[matcher])

        assert hooks.PreToolUse is not None
        assert len(hooks.PreToolUse) == 1
        assert hooks.PreToolUse[0].hooks[0].command == "./scripts/pre.sh"

    def test_create_hooks_with_posttooluse(self) -> None:
        """SkillHooks should accept PostToolUse hooks."""
        hook_def = HookDefinition(command="./scripts/post.sh")
        matcher = HookMatcher(matcher="Bash", hooks=[hook_def])
        hooks = SkillHooks(PostToolUse=[matcher])

        assert hooks.PostToolUse is not None
        assert len(hooks.PostToolUse) == 1
        assert hooks.PostToolUse[0].matcher == "Bash"

    def test_create_hooks_with_stop(self) -> None:
        """SkillHooks should accept Stop hooks."""
        hook_def = HookDefinition(command="./scripts/cleanup.sh")
        matcher = HookMatcher(hooks=[hook_def])
        hooks = SkillHooks(Stop=[matcher])

        assert hooks.Stop is not None
        assert len(hooks.Stop) == 1

    def test_create_hooks_with_all_event_types(self) -> None:
        """SkillHooks should accept all event types together."""
        pre_hook = HookMatcher(hooks=[HookDefinition(command="./pre.sh")])
        post_hook = HookMatcher(
            matcher="Read", hooks=[HookDefinition(command="./post.sh", once=True)]
        )
        stop_hook = HookMatcher(hooks=[HookDefinition(command="./cleanup.sh")])

        hooks = SkillHooks(PreToolUse=[pre_hook], PostToolUse=[post_hook], Stop=[stop_hook])

        assert hooks.PreToolUse is not None
        assert hooks.PostToolUse is not None
        assert hooks.Stop is not None
        assert hooks.PostToolUse[0].matcher == "Read"
        assert hooks.PostToolUse[0].hooks[0].once is True

    def test_new_format_takes_precedence_over_legacy(self) -> None:
        """New format should not be overridden by legacy migration."""
        new_hook = HookMatcher(hooks=[HookDefinition(command="./new-pre.sh")])

        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            hooks = SkillHooks(pre="./legacy-pre.sh", PreToolUse=[new_hook])

        # New format should be preserved, not overridden by legacy
        assert hooks.PreToolUse[0].hooks[0].command == "./new-pre.sh"


class TestSkillScope:
    """Tests for SkillScope model."""

    def test_create_empty_scope(self) -> None:
        """SkillScope should initialize with no restrictions."""
        scope = SkillScope()
        assert scope.agents is None
        assert scope.tenants is None
        assert scope.environments is None

    def test_create_scope_with_agents(self) -> None:
        """SkillScope should accept agent restrictions."""
        scope = SkillScope(agents=["agent-1", "agent-2"])
        assert scope.agents == ["agent-1", "agent-2"]
        assert scope.tenants is None
        assert scope.environments is None

    def test_create_scope_with_tenants(self) -> None:
        """SkillScope should accept tenant restrictions."""
        scope = SkillScope(tenants=["tenant-123", "tenant-456"])
        assert scope.tenants == ["tenant-123", "tenant-456"]
        assert scope.agents is None
        assert scope.environments is None

    def test_create_scope_with_environments(self) -> None:
        """SkillScope should accept environment restrictions."""
        scope = SkillScope(environments=["production", "staging"])
        assert scope.environments == ["production", "staging"]
        assert scope.agents is None
        assert scope.tenants is None

    def test_create_scope_with_all_restrictions(self) -> None:
        """SkillScope should accept all restriction types."""
        scope = SkillScope(
            agents=["agent-1"],
            tenants=["tenant-123"],
            environments=["production"],
        )
        assert scope.agents == ["agent-1"]
        assert scope.tenants == ["tenant-123"]
        assert scope.environments == ["production"]


class TestSkillMetadata:
    """Tests for SkillMetadata model."""

    def test_create_minimal_metadata(self) -> None:
        """SkillMetadata should initialize with only required fields."""
        metadata = SkillMetadata(name="test-skill", description="Test skill")
        assert metadata.name == "test-skill"
        assert metadata.description == "Test skill"
        assert metadata.allowed_tools is None
        assert metadata.model is None
        assert metadata.context == ContextMode.INHERIT
        assert metadata.agent is None
        assert metadata.hooks is None
        assert metadata.user_invocable is True  # Default
        assert metadata.disable_model_invocation is False  # Default
        assert metadata.priority == 0
        assert metadata.tags is None
        assert metadata.scope is None

    def test_create_metadata_with_kebab_case_name(self) -> None:
        """SkillMetadata should accept valid kebab-case names."""
        valid_names = ["test", "test-skill", "test-skill-123", "a", "abc-123-xyz"]
        for name in valid_names:
            metadata = SkillMetadata(name=name, description="Test")
            assert metadata.name == name

    def test_create_metadata_with_invalid_name_raises_error(self) -> None:
        """SkillMetadata should reject invalid skill names."""
        invalid_names = [
            "Test",  # uppercase
            "TEST",  # uppercase
            "test_skill",  # underscore
            "test skill",  # space
            "123-test",  # starts with number
            "-test",  # starts with hyphen
        ]
        for name in invalid_names:
            with pytest.raises(ValidationError) as exc_info:
                SkillMetadata(name=name, description="Test")
            assert "kebab-case" in str(exc_info.value).lower()

    def test_create_metadata_with_allowed_tools(self) -> None:
        """SkillMetadata should accept allowed_tools list."""
        metadata = SkillMetadata(
            name="test-skill",
            description="Test",
            allowed_tools=["tool1", "tool2"],
        )
        assert metadata.allowed_tools == ["tool1", "tool2"]

    def test_create_metadata_with_allowed_tools_alias(self) -> None:
        """SkillMetadata should accept allowed-tools with hyphen alias."""
        # Test using model_validate to handle alias
        data = {
            "name": "test-skill",
            "description": "Test",
            "allowed-tools": ["tool1", "tool2"],
        }
        metadata = SkillMetadata.model_validate(data)
        assert metadata.allowed_tools == ["tool1", "tool2"]

    def test_create_metadata_with_model_override(self) -> None:
        """SkillMetadata should accept model override."""
        metadata = SkillMetadata(
            name="test-skill",
            description="Test",
            model="gpt-4",
        )
        assert metadata.model == "gpt-4"

    def test_create_metadata_with_context_mode(self) -> None:
        """SkillMetadata should accept context mode."""
        metadata = SkillMetadata(
            name="test-skill",
            description="Test",
            context=ContextMode.FORK,
        )
        assert metadata.context == ContextMode.FORK

    def test_create_metadata_with_hooks(self) -> None:
        """SkillMetadata should accept hooks configuration."""
        hooks = SkillHooks(pre="scripts/pre.sh", post="scripts/post.sh")
        metadata = SkillMetadata(
            name="test-skill",
            description="Test",
            hooks=hooks,
        )
        assert metadata.hooks == hooks
        assert metadata.hooks.pre == "scripts/pre.sh"
        assert metadata.hooks.post == "scripts/post.sh"

    def test_create_metadata_with_priority(self) -> None:
        """SkillMetadata should accept priority value."""
        metadata = SkillMetadata(
            name="test-skill",
            description="Test",
            priority=10,
        )
        assert metadata.priority == 10

    def test_create_metadata_with_tags(self) -> None:
        """SkillMetadata should accept tags list."""
        metadata = SkillMetadata(
            name="test-skill",
            description="Test",
            tags=["testing", "example"],
        )
        assert metadata.tags == ["testing", "example"]

    def test_create_metadata_with_scope(self) -> None:
        """SkillMetadata should accept scope configuration."""
        scope = SkillScope(agents=["agent-1"], tenants=["tenant-123"])
        metadata = SkillMetadata(
            name="test-skill",
            description="Test",
            scope=scope,
        )
        assert metadata.scope == scope
        assert metadata.scope.agents == ["agent-1"]
        assert metadata.scope.tenants == ["tenant-123"]

    def test_create_metadata_with_all_fields(self) -> None:
        """SkillMetadata should accept all fields together."""
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            hooks = SkillHooks(pre="pre.sh", post="post.sh")

        scope = SkillScope(agents=["agent-1"], environments=["prod"])
        metadata = SkillMetadata(
            name="full-skill",
            description="Full test skill",
            allowed_tools=["tool1", "tool2"],
            model="gpt-4",
            context=ContextMode.FORK,
            agent="agent-1",
            hooks=hooks,
            user_invocable=False,
            disable_model_invocation=True,
            priority=5,
            tags=["tag1", "tag2"],
            scope=scope,
        )
        assert metadata.name == "full-skill"
        assert metadata.description == "Full test skill"
        assert metadata.allowed_tools == ["tool1", "tool2"]
        assert metadata.model == "gpt-4"
        assert metadata.context == ContextMode.FORK
        assert metadata.agent == "agent-1"
        assert metadata.hooks == hooks
        assert metadata.user_invocable is False
        assert metadata.disable_model_invocation is True
        assert metadata.priority == 5
        assert metadata.tags == ["tag1", "tag2"]
        assert metadata.scope == scope

    def test_create_metadata_with_user_invocable_false(self) -> None:
        """SkillMetadata should accept user_invocable=False (model-only skill)."""
        metadata = SkillMetadata(
            name="model-only",
            description="Model-only skill",
            user_invocable=False,
        )
        assert metadata.user_invocable is False

    def test_create_metadata_with_user_invocable_alias(self) -> None:
        """SkillMetadata should accept user-invocable with hyphen alias."""
        data = {
            "name": "test-skill",
            "description": "Test",
            "user-invocable": False,
        }
        metadata = SkillMetadata.model_validate(data)
        assert metadata.user_invocable is False

    def test_create_metadata_with_disable_model_invocation(self) -> None:
        """SkillMetadata should accept disable_model_invocation=True."""
        metadata = SkillMetadata(
            name="manual-only",
            description="Manual-only skill",
            disable_model_invocation=True,
        )
        assert metadata.disable_model_invocation is True

    def test_create_metadata_with_disable_model_invocation_alias(self) -> None:
        """SkillMetadata should accept disable-model-invocation alias."""
        data = {
            "name": "test-skill",
            "description": "Test",
            "disable-model-invocation": True,
        }
        metadata = SkillMetadata.model_validate(data)
        assert metadata.disable_model_invocation is True

    def test_name_length_validation_accepts_max_64_chars(self) -> None:
        """SkillMetadata should accept names up to 64 characters."""
        # Exactly 64 characters
        name_64 = "a" * 64
        metadata = SkillMetadata(name=name_64, description="Test")
        assert len(metadata.name) == 64

    def test_name_length_validation_rejects_over_64_chars(self) -> None:
        """SkillMetadata should reject names longer than 64 characters."""
        # 65 characters (one over limit)
        name_65 = "a" * 65
        with pytest.raises(ValidationError) as exc_info:
            SkillMetadata(name=name_65, description="Test")
        assert "65" in str(exc_info.value) or "64" in str(exc_info.value)

    def test_description_length_validation_accepts_max_1024_chars(self) -> None:
        """SkillMetadata should accept descriptions up to 1024 characters."""
        # Exactly 1024 characters
        desc_1024 = "x" * 1024
        metadata = SkillMetadata(name="test", description=desc_1024)
        assert len(metadata.description) == 1024

    def test_description_length_validation_rejects_over_1024_chars(self) -> None:
        """SkillMetadata should reject descriptions longer than 1024 characters."""
        # 1025 characters (one over limit)
        desc_1025 = "x" * 1025
        with pytest.raises(ValidationError) as exc_info:
            SkillMetadata(name="test", description=desc_1025)
        assert "1025" in str(exc_info.value) or "1024" in str(exc_info.value)

    def test_description_requires_at_least_one_char(self) -> None:
        """SkillMetadata should reject empty descriptions."""
        with pytest.raises(ValidationError):
            SkillMetadata(name="test", description="")

    def test_execution_mode_defaults_to_autonomous(self) -> None:
        """SkillMetadata should default execution_mode to 'autonomous'."""
        metadata = SkillMetadata(name="test", description="Test")
        assert metadata.execution_mode == "autonomous"

    def test_execution_mode_accepts_custom_value(self) -> None:
        """SkillMetadata should accept custom execution_mode."""
        metadata = SkillMetadata(name="test", description="Test", execution_mode="simple")
        assert metadata.execution_mode == "simple"

    def test_execution_mode_alias(self) -> None:
        """SkillMetadata should accept execution-mode with hyphen alias."""
        data = {
            "name": "test",
            "description": "Test",
            "execution-mode": "autonomous",
        }
        metadata = SkillMetadata.model_validate(data)
        assert metadata.execution_mode == "autonomous"

    def test_max_iterations_defaults_to_none(self) -> None:
        """SkillMetadata should default max_iterations to None."""
        metadata = SkillMetadata(name="test", description="Test")
        assert metadata.max_iterations is None

    def test_max_iterations_accepts_valid_value(self) -> None:
        """SkillMetadata should accept valid max_iterations."""
        metadata = SkillMetadata(name="test", description="Test", max_iterations=20)
        assert metadata.max_iterations == 20

    def test_max_iterations_accepts_boundary_values(self) -> None:
        """SkillMetadata should accept boundary values 1 and 100."""
        metadata_min = SkillMetadata(name="test", description="Test", max_iterations=1)
        assert metadata_min.max_iterations == 1

        metadata_max = SkillMetadata(name="test", description="Test", max_iterations=100)
        assert metadata_max.max_iterations == 100

    def test_max_iterations_rejects_value_below_minimum(self) -> None:
        """SkillMetadata should reject max_iterations below 1."""
        with pytest.raises(ValidationError) as exc_info:
            SkillMetadata(name="test", description="Test", max_iterations=0)
        assert "greater than or equal to 1" in str(exc_info.value).lower()

    def test_max_iterations_rejects_value_above_maximum(self) -> None:
        """SkillMetadata should reject max_iterations above 100."""
        with pytest.raises(ValidationError) as exc_info:
            SkillMetadata(name="test", description="Test", max_iterations=101)
        assert "less than or equal to 100" in str(exc_info.value).lower()

    def test_max_iterations_alias(self) -> None:
        """SkillMetadata should accept max-iterations with hyphen alias."""
        data = {"name": "test", "description": "Test", "max-iterations": 25}
        metadata = SkillMetadata.model_validate(data)
        assert metadata.max_iterations == 25

    def test_max_retries_per_tool_defaults_to_none(self) -> None:
        """SkillMetadata should default max_retries_per_tool to None."""
        metadata = SkillMetadata(name="test", description="Test")
        assert metadata.max_retries_per_tool is None

    def test_max_retries_per_tool_accepts_valid_value(self) -> None:
        """SkillMetadata should accept valid max_retries_per_tool."""
        metadata = SkillMetadata(name="test", description="Test", max_retries_per_tool=5)
        assert metadata.max_retries_per_tool == 5

    def test_max_retries_per_tool_accepts_boundary_values(self) -> None:
        """SkillMetadata should accept boundary values 0 and 10."""
        metadata_min = SkillMetadata(name="test", description="Test", max_retries_per_tool=0)
        assert metadata_min.max_retries_per_tool == 0

        metadata_max = SkillMetadata(name="test", description="Test", max_retries_per_tool=10)
        assert metadata_max.max_retries_per_tool == 10

    def test_max_retries_per_tool_rejects_value_below_minimum(self) -> None:
        """SkillMetadata should reject max_retries_per_tool below 0."""
        with pytest.raises(ValidationError) as exc_info:
            SkillMetadata(name="test", description="Test", max_retries_per_tool=-1)
        assert "greater than or equal to 0" in str(exc_info.value).lower()

    def test_max_retries_per_tool_rejects_value_above_maximum(self) -> None:
        """SkillMetadata should reject max_retries_per_tool above 10."""
        with pytest.raises(ValidationError) as exc_info:
            SkillMetadata(name="test", description="Test", max_retries_per_tool=11)
        assert "less than or equal to 10" in str(exc_info.value).lower()

    def test_max_retries_per_tool_alias(self) -> None:
        """SkillMetadata should accept max-retries-per-tool with hyphen alias."""
        data = {"name": "test", "description": "Test", "max-retries-per-tool": 3}
        metadata = SkillMetadata.model_validate(data)
        assert metadata.max_retries_per_tool == 3

    def test_timeout_per_iteration_defaults_to_none(self) -> None:
        """SkillMetadata should default timeout_per_iteration to None."""
        metadata = SkillMetadata(name="test", description="Test")
        assert metadata.timeout_per_iteration is None

    def test_timeout_per_iteration_accepts_valid_value(self) -> None:
        """SkillMetadata should accept valid timeout_per_iteration."""
        metadata = SkillMetadata(name="test", description="Test", timeout_per_iteration="30s")
        assert metadata.timeout_per_iteration == "30s"

    def test_timeout_per_iteration_accepts_various_formats(self) -> None:
        """SkillMetadata should accept various timeout formats."""
        formats = ["30s", "1m", "500ms", "2h"]
        for fmt in formats:
            metadata = SkillMetadata(name="test", description="Test", timeout_per_iteration=fmt)
            assert metadata.timeout_per_iteration == fmt

    def test_timeout_per_iteration_alias(self) -> None:
        """SkillMetadata should accept timeout-per-iteration with hyphen alias."""
        data = {"name": "test", "description": "Test", "timeout-per-iteration": "45s"}
        metadata = SkillMetadata.model_validate(data)
        assert metadata.timeout_per_iteration == "45s"

    def test_early_termination_defaults_to_none(self) -> None:
        """SkillMetadata should default early_termination to None."""
        metadata = SkillMetadata(name="test", description="Test")
        assert metadata.early_termination is None

    def test_early_termination_accepts_true(self) -> None:
        """SkillMetadata should accept early_termination=True."""
        metadata = SkillMetadata(name="test", description="Test", early_termination=True)
        assert metadata.early_termination is True

    def test_early_termination_accepts_false(self) -> None:
        """SkillMetadata should accept early_termination=False."""
        metadata = SkillMetadata(name="test", description="Test", early_termination=False)
        assert metadata.early_termination is False

    def test_early_termination_alias(self) -> None:
        """SkillMetadata should accept early-termination with hyphen alias."""
        data = {"name": "test", "description": "Test", "early-termination": True}
        metadata = SkillMetadata.model_validate(data)
        assert metadata.early_termination is True

    def test_all_autonomous_execution_fields_together(self) -> None:
        """SkillMetadata should accept all autonomous execution fields."""
        metadata = SkillMetadata(
            name="autonomous-skill",
            description="Autonomous test skill",
            execution_mode="autonomous",
            max_iterations=30,
            max_retries_per_tool=5,
            timeout_per_iteration="60s",
            early_termination=True,
        )
        assert metadata.execution_mode == "autonomous"
        assert metadata.max_iterations == 30
        assert metadata.max_retries_per_tool == 5
        assert metadata.timeout_per_iteration == "60s"
        assert metadata.early_termination is True

    def test_all_autonomous_execution_fields_with_aliases(self) -> None:
        """SkillMetadata should accept all autonomous fields with kebab-case aliases."""
        data = {
            "name": "autonomous-skill",
            "description": "Autonomous test skill",
            "execution-mode": "autonomous",
            "max-iterations": 30,
            "max-retries-per-tool": 5,
            "timeout-per-iteration": "60s",
            "early-termination": True,
        }
        metadata = SkillMetadata.model_validate(data)
        assert metadata.execution_mode == "autonomous"
        assert metadata.max_iterations == 30
        assert metadata.max_retries_per_tool == 5
        assert metadata.timeout_per_iteration == "60s"
        assert metadata.early_termination is True

    def test_backward_compatibility_without_autonomous_fields(self) -> None:
        """Existing skills without autonomous fields should work unchanged."""
        # Simulate an existing skill without new fields
        metadata = SkillMetadata(
            name="legacy-skill",
            description="Legacy skill without autonomous fields",
            allowed_tools=["Read", "Write"],
            model="gpt-4",
        )
        # Should have default values
        assert metadata.execution_mode == "autonomous"
        assert metadata.max_iterations is None
        assert metadata.max_retries_per_tool is None
        assert metadata.timeout_per_iteration is None
        assert metadata.early_termination is None
        # Other fields should work as before
        assert metadata.allowed_tools == ["Read", "Write"]
        assert metadata.model == "gpt-4"


class TestSkill:
    """Tests for Skill model."""

    def test_create_minimal_skill(self) -> None:
        """Skill should initialize with required fields."""
        metadata = SkillMetadata(name="test-skill", description="Test")
        skill = Skill(
            metadata=metadata,
            content="# Test content",
            path=Path("/skills/test-skill.md"),
            base_path=Path("/skills"),
            storage_layer="global",
        )
        assert skill.metadata == metadata
        assert skill.content == "# Test content"
        assert skill.path == Path("/skills/test-skill.md")
        assert skill.base_path == Path("/skills")
        assert skill.storage_layer == "global"
        assert skill.script_paths is None

    def test_create_skill_with_script_paths(self) -> None:
        """Skill should accept script paths dictionary."""
        metadata = SkillMetadata(name="test-skill", description="Test")
        script_paths = {
            "pre": Path("/skills/scripts/pre.sh"),
            "post": Path("/skills/scripts/post.sh"),
        }
        skill = Skill(
            metadata=metadata,
            content="# Test content",
            path=Path("/skills/test-skill.md"),
            base_path=Path("/skills"),
            storage_layer="tenant-123",
            script_paths=script_paths,
        )
        assert skill.script_paths == script_paths

    def test_is_script_file_returns_true_for_hook_scripts(self) -> None:
        """is_script_file should return True for hook script paths."""
        metadata = SkillMetadata(name="test-skill", description="Test")
        pre_script = Path("/skills/scripts/pre.sh")
        post_script = Path("/skills/scripts/post.sh")
        script_paths = {"pre": pre_script, "post": post_script}

        skill = Skill(
            metadata=metadata,
            content="# Test",
            path=Path("/skills/test-skill.md"),
            base_path=Path("/skills"),
            storage_layer="global",
            script_paths=script_paths,
        )

        assert skill.is_script_file(pre_script) is True
        assert skill.is_script_file(post_script) is True

    def test_is_script_file_returns_false_for_non_hook_scripts(self) -> None:
        """is_script_file should return False for non-hook script paths."""
        metadata = SkillMetadata(name="test-skill", description="Test")
        script_paths = {
            "pre": Path("/skills/scripts/pre.sh"),
            "post": Path("/skills/scripts/post.sh"),
        }

        skill = Skill(
            metadata=metadata,
            content="# Test",
            path=Path("/skills/test-skill.md"),
            base_path=Path("/skills"),
            storage_layer="global",
            script_paths=script_paths,
        )

        assert skill.is_script_file(Path("/skills/test-skill.md")) is False
        assert skill.is_script_file(Path("/skills/other-script.sh")) is False

    def test_is_script_file_returns_false_when_no_scripts(self) -> None:
        """is_script_file should return False when skill has no scripts."""
        metadata = SkillMetadata(name="test-skill", description="Test")
        skill = Skill(
            metadata=metadata,
            content="# Test",
            path=Path("/skills/test-skill.md"),
            base_path=Path("/skills"),
            storage_layer="global",
        )

        assert skill.is_script_file(Path("/skills/scripts/pre.sh")) is False


class TestSkillIndexEntry:
    """Tests for SkillIndexEntry model."""

    def test_create_minimal_index_entry(self) -> None:
        """SkillIndexEntry should initialize with required fields."""
        entry = SkillIndexEntry(
            name="test-skill",
            description="Test skill",
            path=Path("/skills/test-skill.md"),
            storage_layer="global",
        )
        assert entry.name == "test-skill"
        assert entry.description == "Test skill"
        assert entry.path == Path("/skills/test-skill.md")
        assert entry.storage_layer == "global"
        assert entry.tags is None
        assert entry.priority == 0

    def test_create_index_entry_with_tags(self) -> None:
        """SkillIndexEntry should accept tags list."""
        entry = SkillIndexEntry(
            name="test-skill",
            description="Test skill",
            path=Path("/skills/test-skill.md"),
            storage_layer="global",
            tags=["testing", "example"],
        )
        assert entry.tags == ["testing", "example"]

    def test_create_index_entry_with_priority(self) -> None:
        """SkillIndexEntry should accept priority value."""
        entry = SkillIndexEntry(
            name="test-skill",
            description="Test skill",
            path=Path("/skills/test-skill.md"),
            storage_layer="tenant-123",
            priority=10,
        )
        assert entry.priority == 10

    def test_create_index_entry_with_all_fields(self) -> None:
        """SkillIndexEntry should accept all fields."""
        entry = SkillIndexEntry(
            name="full-skill",
            description="Full test skill",
            path=Path("/skills/full-skill.md"),
            storage_layer="tenant-456",
            tags=["tag1", "tag2"],
            priority=5,
        )
        assert entry.name == "full-skill"
        assert entry.description == "Full test skill"
        assert entry.path == Path("/skills/full-skill.md")
        assert entry.storage_layer == "tenant-456"
        assert entry.tags == ["tag1", "tag2"]
        assert entry.priority == 5

    def test_index_entry_name_max_64_chars(self) -> None:
        """SkillIndexEntry should accept names up to 64 characters."""
        name_64 = "a" * 64
        entry = SkillIndexEntry(
            name=name_64,
            description="Test",
            path=Path("/test.md"),
            storage_layer="global",
        )
        assert len(entry.name) == 64

    def test_index_entry_name_rejects_over_64_chars(self) -> None:
        """SkillIndexEntry should reject names over 64 characters."""
        name_65 = "a" * 65
        with pytest.raises(ValidationError):
            SkillIndexEntry(
                name=name_65,
                description="Test",
                path=Path("/test.md"),
                storage_layer="global",
            )

    def test_index_entry_description_max_1024_chars(self) -> None:
        """SkillIndexEntry should accept descriptions up to 1024 characters."""
        desc_1024 = "x" * 1024
        entry = SkillIndexEntry(
            name="test",
            description=desc_1024,
            path=Path("/test.md"),
            storage_layer="global",
        )
        assert len(entry.description) == 1024

    def test_index_entry_description_rejects_over_1024_chars(self) -> None:
        """SkillIndexEntry should reject descriptions over 1024 characters."""
        desc_1025 = "x" * 1025
        with pytest.raises(ValidationError):
            SkillIndexEntry(
                name="test",
                description=desc_1025,
                path=Path("/test.md"),
                storage_layer="global",
            )
