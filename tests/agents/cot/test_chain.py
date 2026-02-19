"""Tests for chain of thought data models."""

from datetime import datetime
from uuid import UUID, uuid4

import pytest

from omniforge.agents.cot import (
    ChainMetrics,
    ChainStatus,
    ReasoningChain,
    ReasoningStep,
    StepType,
    SynthesisInfo,
    ThinkingInfo,
    ToolCallInfo,
    ToolResultInfo,
    ToolType,
    VisibilityConfig,
    VisibilityLevel,
)


class TestEnums:
    """Tests for enum definitions."""

    def test_step_type_values(self) -> None:
        """StepType enum should have all expected values."""
        assert StepType.THINKING == "thinking"
        assert StepType.TOOL_CALL == "tool_call"
        assert StepType.TOOL_RESULT == "tool_result"
        assert StepType.SYNTHESIS == "synthesis"

    def test_tool_type_values(self) -> None:
        """ToolType enum should have all expected values."""
        assert ToolType.FUNCTION == "function"
        assert ToolType.API == "api"
        assert ToolType.DATABASE == "database"
        assert ToolType.FILE_SYSTEM == "file_system"
        assert ToolType.SEARCH == "search"
        assert ToolType.OTHER == "other"

    def test_chain_status_values(self) -> None:
        """ChainStatus enum should have all expected values."""
        assert ChainStatus.RUNNING == "running"
        assert ChainStatus.COMPLETED == "completed"
        assert ChainStatus.FAILED == "failed"
        assert ChainStatus.PAUSED == "paused"

    def test_visibility_level_values(self) -> None:
        """VisibilityLevel enum should have all expected values."""
        assert VisibilityLevel.FULL == "full"
        assert VisibilityLevel.SUMMARY == "summary"
        assert VisibilityLevel.HIDDEN == "hidden"


class TestVisibilityConfig:
    """Tests for VisibilityConfig model."""

    def test_default_visibility_config(self) -> None:
        """VisibilityConfig should have sensible defaults."""
        config = VisibilityConfig()
        assert config.level == VisibilityLevel.FULL
        assert config.reason is None

    def test_visibility_config_with_reason(self) -> None:
        """VisibilityConfig should store visibility reason."""
        config = VisibilityConfig(level=VisibilityLevel.HIDDEN, reason="contains PII")
        assert config.level == VisibilityLevel.HIDDEN
        assert config.reason == "contains PII"

    def test_visibility_config_serialization(self) -> None:
        """VisibilityConfig should serialize to JSON."""
        config = VisibilityConfig(level=VisibilityLevel.SUMMARY, reason="redacted")
        data = config.model_dump()
        assert data == {"level": "summary", "reason": "redacted"}


class TestThinkingInfo:
    """Tests for ThinkingInfo model."""

    def test_thinking_info_required_fields(self) -> None:
        """ThinkingInfo should require content field."""
        info = ThinkingInfo(content="Analyzing the problem...")
        assert info.content == "Analyzing the problem..."
        assert info.confidence is None

    def test_thinking_info_with_confidence(self) -> None:
        """ThinkingInfo should accept confidence value."""
        info = ThinkingInfo(content="High certainty answer", confidence=0.95)
        assert info.confidence == 0.95

    def test_thinking_info_confidence_validation(self) -> None:
        """ThinkingInfo should validate confidence range."""
        with pytest.raises(ValueError):
            ThinkingInfo(content="test", confidence=1.5)
        with pytest.raises(ValueError):
            ThinkingInfo(content="test", confidence=-0.1)


class TestToolCallInfo:
    """Tests for ToolCallInfo model."""

    def test_tool_call_info_required_fields(self) -> None:
        """ToolCallInfo should require tool_name and tool_type."""
        info = ToolCallInfo(tool_name="search", tool_type=ToolType.SEARCH)
        assert info.tool_name == "search"
        assert info.tool_type == ToolType.SEARCH
        assert info.parameters == {}
        assert isinstance(info.correlation_id, str)

    def test_tool_call_info_with_parameters(self) -> None:
        """ToolCallInfo should accept parameters."""
        params = {"query": "test", "limit": 10}
        info = ToolCallInfo(tool_name="db_query", tool_type=ToolType.DATABASE, parameters=params)
        assert info.parameters == params

    def test_tool_call_info_auto_correlation_id(self) -> None:
        """ToolCallInfo should auto-generate unique correlation IDs."""
        info1 = ToolCallInfo(tool_name="test", tool_type=ToolType.FUNCTION)
        info2 = ToolCallInfo(tool_name="test", tool_type=ToolType.FUNCTION)
        assert info1.correlation_id != info2.correlation_id


class TestToolResultInfo:
    """Tests for ToolResultInfo model."""

    def test_tool_result_info_success(self) -> None:
        """ToolResultInfo should handle successful results."""
        info = ToolResultInfo(correlation_id="test-123", success=True, result={"data": "result"})
        assert info.correlation_id == "test-123"
        assert info.success is True
        assert info.result == {"data": "result"}
        assert info.error is None

    def test_tool_result_info_failure(self) -> None:
        """ToolResultInfo should handle failed results."""
        info = ToolResultInfo(correlation_id="test-456", success=False, error="Connection failed")
        assert info.correlation_id == "test-456"
        assert info.success is False
        assert info.error == "Connection failed"
        assert info.result is None


class TestSynthesisInfo:
    """Tests for SynthesisInfo model."""

    def test_synthesis_info_required_fields(self) -> None:
        """SynthesisInfo should require content field."""
        info = SynthesisInfo(content="Based on the analysis...")
        assert info.content == "Based on the analysis..."
        assert info.sources == []

    def test_synthesis_info_with_sources(self) -> None:
        """SynthesisInfo should track source step IDs."""
        step_ids = [uuid4(), uuid4()]
        info = SynthesisInfo(content="Conclusion", sources=step_ids)
        assert info.sources == step_ids


class TestChainMetrics:
    """Tests for ChainMetrics model."""

    def test_chain_metrics_defaults(self) -> None:
        """ChainMetrics should initialize with zero values."""
        metrics = ChainMetrics()
        assert metrics.total_steps == 0
        assert metrics.llm_calls == 0
        assert metrics.tool_calls == 0
        assert metrics.total_tokens == 0
        assert metrics.total_cost == 0.0

    def test_chain_metrics_with_values(self) -> None:
        """ChainMetrics should accept custom values."""
        metrics = ChainMetrics(
            total_steps=10, llm_calls=3, tool_calls=2, total_tokens=500, total_cost=0.05
        )
        assert metrics.total_steps == 10
        assert metrics.llm_calls == 3
        assert metrics.tool_calls == 2
        assert metrics.total_tokens == 500
        assert metrics.total_cost == 0.05


class TestReasoningStep:
    """Tests for ReasoningStep model."""

    def test_reasoning_step_minimal(self) -> None:
        """ReasoningStep should work with minimal required fields."""
        step = ReasoningStep(step_number=0, type=StepType.THINKING)
        assert isinstance(step.id, UUID)
        assert step.step_number == 0
        assert step.type == StepType.THINKING
        assert isinstance(step.timestamp, datetime)
        assert step.parent_step_id is None
        assert step.visibility.level == VisibilityLevel.FULL
        assert step.tokens_used == 0
        assert step.cost == 0.0

    def test_reasoning_step_thinking(self) -> None:
        """ReasoningStep should store thinking info."""
        thinking = ThinkingInfo(content="Let me think...", confidence=0.8)
        step = ReasoningStep(step_number=1, type=StepType.THINKING, thinking=thinking)
        assert step.thinking == thinking
        assert step.thinking.content == "Let me think..."
        assert step.thinking.confidence == 0.8

    def test_reasoning_step_tool_call(self) -> None:
        """ReasoningStep should store tool call info."""
        tool_call = ToolCallInfo(
            tool_name="search", tool_type=ToolType.SEARCH, parameters={"q": "test"}
        )
        step = ReasoningStep(step_number=2, type=StepType.TOOL_CALL, tool_call=tool_call)
        assert step.tool_call == tool_call
        assert step.tool_call.tool_name == "search"

    def test_reasoning_step_tool_result(self) -> None:
        """ReasoningStep should store tool result info."""
        tool_result = ToolResultInfo(correlation_id="abc", success=True, result={"found": True})
        step = ReasoningStep(step_number=3, type=StepType.TOOL_RESULT, tool_result=tool_result)
        assert step.tool_result == tool_result
        assert step.tool_result.success is True

    def test_reasoning_step_synthesis(self) -> None:
        """ReasoningStep should store synthesis info."""
        synthesis = SynthesisInfo(content="Final answer", sources=[uuid4()])
        step = ReasoningStep(step_number=4, type=StepType.SYNTHESIS, synthesis=synthesis)
        assert step.synthesis == synthesis
        assert step.synthesis.content == "Final answer"

    def test_reasoning_step_with_parent(self) -> None:
        """ReasoningStep should support parent-child relationships."""
        parent_id = uuid4()
        step = ReasoningStep(step_number=1, type=StepType.THINKING, parent_step_id=parent_id)
        assert step.parent_step_id == parent_id

    def test_reasoning_step_with_visibility(self) -> None:
        """ReasoningStep should support custom visibility."""
        visibility = VisibilityConfig(level=VisibilityLevel.HIDDEN, reason="sensitive data")
        step = ReasoningStep(step_number=1, type=StepType.THINKING, visibility=visibility)
        assert step.visibility.level == VisibilityLevel.HIDDEN
        assert step.visibility.reason == "sensitive data"

    def test_reasoning_step_with_tokens_and_cost(self) -> None:
        """ReasoningStep should track tokens and cost."""
        step = ReasoningStep(step_number=1, type=StepType.THINKING, tokens_used=150, cost=0.003)
        assert step.tokens_used == 150
        assert step.cost == 0.003

    def test_reasoning_step_serialization(self) -> None:
        """ReasoningStep should serialize to JSON."""
        step = ReasoningStep(
            step_number=0,
            type=StepType.THINKING,
            thinking=ThinkingInfo(content="test"),
            tokens_used=100,
            cost=0.002,
        )
        data = step.model_dump()
        assert data["step_number"] == 0
        assert data["type"] == "thinking"
        assert data["thinking"]["content"] == "test"
        assert data["tokens_used"] == 100
        assert data["cost"] == 0.002


class TestReasoningChain:
    """Tests for ReasoningChain model."""

    def test_reasoning_chain_minimal(self) -> None:
        """ReasoningChain should work with minimal required fields."""
        chain = ReasoningChain(task_id="task-123", agent_id="agent-456")
        assert chain.task_id == "task-123"
        assert chain.agent_id == "agent-456"
        assert chain.status == ChainStatus.RUNNING
        assert isinstance(chain.started_at, datetime)
        assert chain.completed_at is None
        assert chain.steps == []
        assert chain.metrics.total_steps == 0
        assert chain.child_chain_ids == []
        assert chain.tenant_id is None

    def test_reasoning_chain_with_tenant(self) -> None:
        """ReasoningChain should support multi-tenancy."""
        chain = ReasoningChain(task_id="task-123", agent_id="agent-456", tenant_id="tenant-789")
        assert chain.tenant_id == "tenant-789"

    def test_add_step_auto_numbers_steps(self) -> None:
        """add_step should automatically number steps sequentially."""
        chain = ReasoningChain(task_id="task-1", agent_id="agent-1")

        step1 = ReasoningStep(step_number=0, type=StepType.THINKING)
        step2 = ReasoningStep(step_number=0, type=StepType.TOOL_CALL)
        step3 = ReasoningStep(step_number=0, type=StepType.SYNTHESIS)

        chain.add_step(step1)
        chain.add_step(step2)
        chain.add_step(step3)

        assert len(chain.steps) == 3
        assert chain.steps[0].step_number == 0
        assert chain.steps[1].step_number == 1
        assert chain.steps[2].step_number == 2

    def test_add_step_updates_total_steps(self) -> None:
        """add_step should update total_steps metric."""
        chain = ReasoningChain(task_id="task-1", agent_id="agent-1")
        assert chain.metrics.total_steps == 0

        chain.add_step(ReasoningStep(step_number=0, type=StepType.THINKING))
        assert chain.metrics.total_steps == 1

        chain.add_step(ReasoningStep(step_number=0, type=StepType.SYNTHESIS))
        assert chain.metrics.total_steps == 2

    def test_add_step_updates_llm_calls_for_thinking(self) -> None:
        """add_step should increment llm_calls for thinking steps."""
        chain = ReasoningChain(task_id="task-1", agent_id="agent-1")
        assert chain.metrics.llm_calls == 0

        chain.add_step(ReasoningStep(step_number=0, type=StepType.THINKING))
        assert chain.metrics.llm_calls == 1

    def test_add_step_updates_llm_calls_for_synthesis(self) -> None:
        """add_step should increment llm_calls for synthesis steps."""
        chain = ReasoningChain(task_id="task-1", agent_id="agent-1")
        assert chain.metrics.llm_calls == 0

        chain.add_step(ReasoningStep(step_number=0, type=StepType.SYNTHESIS))
        assert chain.metrics.llm_calls == 1

    def test_add_step_updates_tool_calls(self) -> None:
        """add_step should increment tool_calls for tool_call steps."""
        chain = ReasoningChain(task_id="task-1", agent_id="agent-1")
        assert chain.metrics.tool_calls == 0

        chain.add_step(ReasoningStep(step_number=0, type=StepType.TOOL_CALL))
        assert chain.metrics.tool_calls == 1

        chain.add_step(ReasoningStep(step_number=0, type=StepType.TOOL_CALL))
        assert chain.metrics.tool_calls == 2

    def test_add_step_does_not_update_counters_for_tool_result(self) -> None:
        """add_step should not increment llm_calls or tool_calls for tool_result steps."""
        chain = ReasoningChain(task_id="task-1", agent_id="agent-1")

        chain.add_step(ReasoningStep(step_number=0, type=StepType.TOOL_RESULT))
        assert chain.metrics.llm_calls == 0
        assert chain.metrics.tool_calls == 0
        assert chain.metrics.total_steps == 1

    def test_add_step_updates_tokens(self) -> None:
        """add_step should accumulate token usage."""
        chain = ReasoningChain(task_id="task-1", agent_id="agent-1")
        assert chain.metrics.total_tokens == 0

        chain.add_step(ReasoningStep(step_number=0, type=StepType.THINKING, tokens_used=100))
        assert chain.metrics.total_tokens == 100

        chain.add_step(ReasoningStep(step_number=0, type=StepType.SYNTHESIS, tokens_used=50))
        assert chain.metrics.total_tokens == 150

    def test_add_step_updates_cost(self) -> None:
        """add_step should accumulate cost."""
        chain = ReasoningChain(task_id="task-1", agent_id="agent-1")
        assert chain.metrics.total_cost == 0.0

        chain.add_step(ReasoningStep(step_number=0, type=StepType.THINKING, cost=0.01))
        assert chain.metrics.total_cost == 0.01

        chain.add_step(ReasoningStep(step_number=0, type=StepType.SYNTHESIS, cost=0.005))
        assert chain.metrics.total_cost == 0.015

    def test_add_step_complete_scenario(self) -> None:
        """add_step should correctly update all metrics in a complete scenario."""
        chain = ReasoningChain(task_id="task-1", agent_id="agent-1")

        # Add thinking step
        chain.add_step(
            ReasoningStep(step_number=0, type=StepType.THINKING, tokens_used=100, cost=0.002)
        )

        # Add tool call step
        chain.add_step(
            ReasoningStep(step_number=0, type=StepType.TOOL_CALL, tokens_used=50, cost=0.001)
        )

        # Add tool result step
        chain.add_step(
            ReasoningStep(step_number=0, type=StepType.TOOL_RESULT, tokens_used=0, cost=0.0)
        )

        # Add synthesis step
        chain.add_step(
            ReasoningStep(step_number=0, type=StepType.SYNTHESIS, tokens_used=75, cost=0.0015)
        )

        # Verify all metrics
        assert chain.metrics.total_steps == 4
        assert chain.metrics.llm_calls == 2  # thinking + synthesis
        assert chain.metrics.tool_calls == 1  # tool_call only
        assert chain.metrics.total_tokens == 225  # 100 + 50 + 0 + 75
        assert chain.metrics.total_cost == pytest.approx(0.0045)  # 0.002 + 0.001 + 0 + 0.0015

    def test_get_step_by_correlation_id_finds_matching_step(self) -> None:
        """get_step_by_correlation_id should find tool_call step by correlation ID."""
        chain = ReasoningChain(task_id="task-1", agent_id="agent-1")

        tool_call = ToolCallInfo(
            tool_name="search", tool_type=ToolType.SEARCH, correlation_id="corr-123"
        )
        step = ReasoningStep(step_number=0, type=StepType.TOOL_CALL, tool_call=tool_call)
        chain.add_step(step)

        found_step = chain.get_step_by_correlation_id("corr-123")
        assert found_step is not None
        assert found_step.id == step.id
        assert found_step.tool_call.correlation_id == "corr-123"

    def test_get_step_by_correlation_id_returns_none_if_not_found(self) -> None:
        """get_step_by_correlation_id should return None if correlation ID not found."""
        chain = ReasoningChain(task_id="task-1", agent_id="agent-1")

        tool_call = ToolCallInfo(
            tool_name="search", tool_type=ToolType.SEARCH, correlation_id="corr-123"
        )
        chain.add_step(ReasoningStep(step_number=0, type=StepType.TOOL_CALL, tool_call=tool_call))

        found_step = chain.get_step_by_correlation_id("non-existent")
        assert found_step is None

    def test_get_step_by_correlation_id_ignores_non_tool_call_steps(self) -> None:
        """get_step_by_correlation_id should only search tool_call steps."""
        chain = ReasoningChain(task_id="task-1", agent_id="agent-1")

        # Add non-tool-call steps
        chain.add_step(ReasoningStep(step_number=0, type=StepType.THINKING))
        chain.add_step(ReasoningStep(step_number=0, type=StepType.SYNTHESIS))

        found_step = chain.get_step_by_correlation_id("any-id")
        assert found_step is None

    def test_reasoning_chain_with_child_chains(self) -> None:
        """ReasoningChain should track child chain IDs for delegation."""
        chain = ReasoningChain(
            task_id="task-1", agent_id="agent-1", child_chain_ids=["child-1", "child-2"]
        )
        assert chain.child_chain_ids == ["child-1", "child-2"]

    def test_reasoning_chain_serialization(self) -> None:
        """ReasoningChain should serialize to JSON."""
        chain = ReasoningChain(task_id="task-1", agent_id="agent-1", tenant_id="tenant-1")
        chain.add_step(
            ReasoningStep(step_number=0, type=StepType.THINKING, tokens_used=100, cost=0.002)
        )

        data = chain.model_dump()
        assert data["task_id"] == "task-1"
        assert data["agent_id"] == "agent-1"
        assert data["tenant_id"] == "tenant-1"
        assert data["status"] == "running"
        assert len(data["steps"]) == 1
        assert data["metrics"]["total_steps"] == 1
        assert data["metrics"]["total_tokens"] == 100
        assert data["metrics"]["total_cost"] == 0.002
