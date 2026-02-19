"""Tests for visibility control system."""

from datetime import datetime
from uuid import uuid4

import pytest

from omniforge.agents.cot.chain import (
    ChainStatus,
    ReasoningChain,
    ReasoningStep,
    StepType,
    ThinkingInfo,
    ToolCallInfo,
    ToolResultInfo,
    VisibilityConfig,
)
from omniforge.agents.cot.visibility import (
    VisibilityConfiguration,
    VisibilityController,
    VisibilityRule,
    generate_summary,
    redact_sensitive_fields,
)
from omniforge.security.rbac import Role
from omniforge.tools.types import ToolType, VisibilityLevel


def create_test_step(
    step_type: StepType = StepType.THINKING,
    visibility_level: VisibilityLevel = VisibilityLevel.FULL,
) -> ReasoningStep:
    """Create a test reasoning step."""
    step = ReasoningStep(
        step_number=0,
        type=step_type,
        visibility=VisibilityConfig(level=visibility_level),
    )

    if step_type == StepType.THINKING:
        step.thinking = ThinkingInfo(content="Analyzing the problem...")

    elif step_type == StepType.TOOL_CALL:
        step.tool_call = ToolCallInfo(
            tool_name="calculator",
            tool_type=ToolType.FUNCTION,
            parameters={"operation": "add", "a": 1, "b": 2, "api_key": "secret123"},
        )

    elif step_type == StepType.TOOL_RESULT:
        step.tool_result = ToolResultInfo(
            correlation_id="test-id", success=True, result={"answer": 3, "token": "xyz"}
        )

    return step


def test_visibility_rule_creation():
    """Test VisibilityRule creation."""
    rule = VisibilityRule(
        level=VisibilityLevel.SUMMARY, role=Role.END_USER, tool_type=ToolType.LLM
    )

    assert rule.level == VisibilityLevel.SUMMARY
    assert rule.role == Role.END_USER
    assert rule.tool_type == ToolType.LLM
    assert rule.summary_template is None


def test_visibility_configuration_defaults():
    """Test VisibilityConfiguration default values."""
    config = VisibilityConfiguration()

    assert config.default_level == VisibilityLevel.FULL
    assert config.rules_by_tool_type == {}
    assert config.rules_by_role == {}
    assert config.child_chain_visibility == VisibilityLevel.SUMMARY
    assert "password" in config.sensitive_fields
    assert "api_key" in config.sensitive_fields


def test_visibility_controller_initialization():
    """Test VisibilityController initialization."""
    config = VisibilityConfiguration()
    controller = VisibilityController(config)

    assert controller.config == config


def test_get_effective_level_default():
    """Test getting effective level returns default."""
    config = VisibilityConfiguration(default_level=VisibilityLevel.SUMMARY)
    controller = VisibilityController(config)

    step = create_test_step()
    level = controller.get_effective_level(step, Role.DEVELOPER)

    assert level == VisibilityLevel.SUMMARY


def test_get_effective_level_step_security():
    """Test step-level security visibility takes precedence."""
    config = VisibilityConfiguration(default_level=VisibilityLevel.FULL)
    controller = VisibilityController(config)

    # Step has HIDDEN visibility
    step = create_test_step(visibility_level=VisibilityLevel.HIDDEN)
    level = controller.get_effective_level(step, Role.ADMIN)

    # Should be HIDDEN even for admin
    assert level == VisibilityLevel.HIDDEN


def test_get_effective_level_role_rule():
    """Test role-specific rules apply."""
    config = VisibilityConfiguration(
        default_level=VisibilityLevel.FULL,
        rules_by_role={Role.END_USER: VisibilityLevel.SUMMARY},
    )
    controller = VisibilityController(config)

    step = create_test_step()

    # END_USER should get SUMMARY
    assert controller.get_effective_level(step, Role.END_USER) == VisibilityLevel.SUMMARY

    # DEVELOPER should get FULL (default)
    assert controller.get_effective_level(step, Role.DEVELOPER) == VisibilityLevel.FULL


def test_get_effective_level_tool_type_rule():
    """Test tool-type-specific rules apply."""
    config = VisibilityConfiguration(
        default_level=VisibilityLevel.FULL,
        rules_by_tool_type={ToolType.FUNCTION: VisibilityLevel.HIDDEN},
    )
    controller = VisibilityController(config)

    # Tool call step with FUNCTION type
    step = create_test_step(step_type=StepType.TOOL_CALL)

    assert controller.get_effective_level(step, Role.DEVELOPER) == VisibilityLevel.HIDDEN


def test_get_effective_level_resolution_order():
    """Test resolution order: security > role > tool > default."""
    config = VisibilityConfiguration(
        default_level=VisibilityLevel.FULL,
        rules_by_role={Role.END_USER: VisibilityLevel.SUMMARY},
        rules_by_tool_type={ToolType.FUNCTION: VisibilityLevel.HIDDEN},
    )
    controller = VisibilityController(config)

    # 1. Step security takes precedence
    step1 = create_test_step(
        step_type=StepType.TOOL_CALL, visibility_level=VisibilityLevel.HIDDEN
    )
    assert controller.get_effective_level(step1, Role.END_USER) == VisibilityLevel.HIDDEN

    # 2. Role rule applies when step visibility is FULL
    step2 = create_test_step(step_type=StepType.THINKING)
    assert controller.get_effective_level(step2, Role.END_USER) == VisibilityLevel.SUMMARY

    # 3. Tool type rule applies when no role rule
    step3 = create_test_step(step_type=StepType.TOOL_CALL)
    assert controller.get_effective_level(step3, Role.DEVELOPER) == VisibilityLevel.HIDDEN


def test_apply_visibility_full():
    """Test applying FULL visibility returns step unchanged."""
    config = VisibilityConfiguration(default_level=VisibilityLevel.FULL)
    controller = VisibilityController(config)

    step = create_test_step()
    filtered = controller.apply_visibility(step, Role.DEVELOPER)

    assert filtered.thinking.content == "Analyzing the problem..."


def test_apply_visibility_hidden():
    """Test applying HIDDEN visibility redacts content."""
    config = VisibilityConfiguration(
        rules_by_role={Role.END_USER: VisibilityLevel.HIDDEN}
    )
    controller = VisibilityController(config)

    step = create_test_step()
    filtered = controller.apply_visibility(step, Role.END_USER)

    assert filtered.thinking.content == "[Hidden]"
    assert filtered.visibility.level == VisibilityLevel.HIDDEN


def test_apply_visibility_summary():
    """Test applying SUMMARY visibility creates summary."""
    config = VisibilityConfiguration(
        rules_by_role={Role.END_USER: VisibilityLevel.SUMMARY}
    )
    controller = VisibilityController(config)

    step = create_test_step()
    filtered = controller.apply_visibility(step, Role.END_USER)

    # Should have summary content
    assert "Performed reasoning step" == filtered.thinking.content
    assert filtered.visibility.level == VisibilityLevel.SUMMARY


def test_filter_chain_removes_hidden_steps():
    """Test filter_chain removes hidden steps."""
    config = VisibilityConfiguration(
        rules_by_role={Role.END_USER: VisibilityLevel.HIDDEN}
    )
    controller = VisibilityController(config)

    chain = ReasoningChain(task_id="task-1", agent_id="agent-1")
    chain.add_step(create_test_step())
    chain.add_step(create_test_step())
    chain.add_step(create_test_step())

    filtered = controller.filter_chain(chain, Role.END_USER)

    # All steps should be removed (hidden)
    assert len(filtered.steps) == 0


def test_filter_chain_keeps_visible_steps():
    """Test filter_chain keeps visible steps."""
    config = VisibilityConfiguration(default_level=VisibilityLevel.SUMMARY)
    controller = VisibilityController(config)

    chain = ReasoningChain(task_id="task-1", agent_id="agent-1")
    chain.add_step(create_test_step())
    chain.add_step(create_test_step())

    filtered = controller.filter_chain(chain, Role.DEVELOPER)

    # Steps should be kept
    assert len(filtered.steps) == 2


def test_filter_chain_mixed_visibility():
    """Test filter_chain with mixed visibility levels."""
    config = VisibilityConfiguration(default_level=VisibilityLevel.FULL)
    controller = VisibilityController(config)

    chain = ReasoningChain(task_id="task-1", agent_id="agent-1")
    chain.add_step(create_test_step(visibility_level=VisibilityLevel.FULL))
    chain.add_step(create_test_step(visibility_level=VisibilityLevel.HIDDEN))
    chain.add_step(create_test_step(visibility_level=VisibilityLevel.SUMMARY))

    filtered = controller.filter_chain(chain, Role.DEVELOPER)

    # Only FULL and SUMMARY steps should remain
    assert len(filtered.steps) == 2


def test_redact_sensitive_fields():
    """Test redacting sensitive fields from dictionary."""
    data = {
        "username": "alice",
        "password": "secret123",
        "api_key": "key123",
        "result": "success",
    }

    redacted = redact_sensitive_fields(data, ["password", "api_key"])

    assert redacted["username"] == "alice"
    assert redacted["password"] == "[REDACTED]"
    assert redacted["api_key"] == "[REDACTED]"
    assert redacted["result"] == "success"


def test_redact_sensitive_fields_nested():
    """Test redacting nested dictionaries."""
    data = {
        "user": {"name": "alice", "token": "xyz"},
        "config": {"timeout": 30, "secret": "abc"},
    }

    redacted = redact_sensitive_fields(data, ["token", "secret"])

    assert redacted["user"]["name"] == "alice"
    assert redacted["user"]["token"] == "[REDACTED]"
    assert redacted["config"]["timeout"] == 30
    assert redacted["config"]["secret"] == "[REDACTED]"


def test_redact_sensitive_fields_case_insensitive():
    """Test redaction is case-insensitive."""
    data = {"API_KEY": "key123", "ApiKey": "key456", "api_key": "key789"}

    redacted = redact_sensitive_fields(data, ["api_key"])

    assert redacted["API_KEY"] == "[REDACTED]"
    assert redacted["ApiKey"] == "[REDACTED]"
    assert redacted["api_key"] == "[REDACTED]"


def test_redact_sensitive_fields_in_list():
    """Test redacting fields in lists."""
    data = {"items": [{"id": 1, "password": "abc"}, {"id": 2, "password": "def"}]}

    redacted = redact_sensitive_fields(data, ["password"])

    assert redacted["items"][0]["id"] == 1
    assert redacted["items"][0]["password"] == "[REDACTED]"
    assert redacted["items"][1]["id"] == 2
    assert redacted["items"][1]["password"] == "[REDACTED]"


def test_generate_summary_with_template():
    """Test generating summary with custom template."""
    step = create_test_step()
    summary = generate_summary(step, template="Custom summary")

    assert summary == "Custom summary"


def test_generate_summary_thinking_step():
    """Test generating summary for thinking step."""
    step = create_test_step(step_type=StepType.THINKING)
    step.step_number = 5
    summary = generate_summary(step)

    assert "Reasoning step #5" in summary


def test_generate_summary_tool_call():
    """Test generating summary for tool call."""
    step = create_test_step(step_type=StepType.TOOL_CALL)
    summary = generate_summary(step)

    assert "Called calculator" in summary


def test_generate_summary_tool_result_success():
    """Test generating summary for successful tool result."""
    step = create_test_step(step_type=StepType.TOOL_RESULT)
    summary = generate_summary(step)

    assert "succeeded" in summary


def test_generate_summary_tool_result_failure():
    """Test generating summary for failed tool result."""
    step = create_test_step(step_type=StepType.TOOL_RESULT)
    step.tool_result.success = False
    summary = generate_summary(step)

    assert "failed" in summary


def test_hidden_step_clears_tool_call_parameters():
    """Test hidden step clears tool call parameters."""
    config = VisibilityConfiguration()
    controller = VisibilityController(config)

    step = create_test_step(step_type=StepType.TOOL_CALL)
    hidden = controller._create_hidden_step(step)

    assert hidden.tool_call.parameters == {}


def test_hidden_step_clears_tool_result():
    """Test hidden step clears tool result."""
    config = VisibilityConfiguration()
    controller = VisibilityController(config)

    step = create_test_step(step_type=StepType.TOOL_RESULT)
    hidden = controller._create_hidden_step(step)

    assert hidden.tool_result.result is None


def test_summary_step_redacts_parameters():
    """Test summary step redacts sensitive parameters."""
    config = VisibilityConfiguration()
    controller = VisibilityController(config)

    step = create_test_step(step_type=StepType.TOOL_CALL)
    summary = controller._create_summary_step(step)

    # api_key should be redacted
    assert summary.tool_call.parameters["api_key"] == "[REDACTED]"
    # Other parameters should remain
    assert summary.tool_call.parameters["operation"] == "add"


def test_summary_step_redacts_result():
    """Test summary step redacts sensitive result data."""
    config = VisibilityConfiguration()
    controller = VisibilityController(config)

    step = create_test_step(step_type=StepType.TOOL_RESULT)
    summary = controller._create_summary_step(step)

    # token should be redacted
    assert summary.tool_result.result["token"] == "[REDACTED]"
    # Other fields should remain
    assert summary.tool_result.result["answer"] == 3


def test_get_step_tool_type():
    """Test extracting tool type from step."""
    config = VisibilityConfiguration()
    controller = VisibilityController(config)

    # Tool call step has tool type
    tool_step = create_test_step(step_type=StepType.TOOL_CALL)
    assert controller._get_step_tool_type(tool_step) == ToolType.FUNCTION

    # Thinking step has no tool type
    thinking_step = create_test_step(step_type=StepType.THINKING)
    assert controller._get_step_tool_type(thinking_step) is None


def test_filter_chain_preserves_chain_metadata():
    """Test filter_chain preserves chain metadata."""
    config = VisibilityConfiguration()
    controller = VisibilityController(config)

    chain = ReasoningChain(
        task_id="task-1",
        agent_id="agent-1",
        status=ChainStatus.COMPLETED,
        tenant_id="tenant-1",
    )
    chain.add_step(create_test_step())

    filtered = controller.filter_chain(chain, Role.DEVELOPER)

    assert filtered.task_id == "task-1"
    assert filtered.agent_id == "agent-1"
    assert filtered.status == ChainStatus.COMPLETED
    assert filtered.tenant_id == "tenant-1"


def test_visibility_level_none_role():
    """Test getting effective level with None role."""
    config = VisibilityConfiguration(default_level=VisibilityLevel.SUMMARY)
    controller = VisibilityController(config)

    step = create_test_step()
    level = controller.get_effective_level(step, None)

    # Should use default level
    assert level == VisibilityLevel.SUMMARY


def test_custom_sensitive_fields():
    """Test using custom sensitive fields list."""
    config = VisibilityConfiguration(sensitive_fields=["custom_secret", "private_data"])
    controller = VisibilityController(config)

    step = create_test_step(step_type=StepType.TOOL_CALL)
    step.tool_call.parameters = {"custom_secret": "value", "public_data": "visible"}

    summary = controller._create_summary_step(step)

    assert summary.tool_call.parameters["custom_secret"] == "[REDACTED]"
    assert summary.tool_call.parameters["public_data"] == "visible"
