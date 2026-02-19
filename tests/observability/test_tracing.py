"""Tests for execution tracing."""

from datetime import datetime

from omniforge.observability.tracing import (
    ExecutionTrace,
    SkillTrace,
    get_execution_tracer,
)


class TestSkillTrace:
    """Tests for SkillTrace class."""

    def test_skill_trace_initialization(self) -> None:
        """SkillTrace should initialize with correct values."""
        now = datetime.utcnow()
        trace = SkillTrace(
            skill_id="skill-1",
            skill_name="test_skill",
            started_at=now,
            input_data={"key": "value"},
        )

        assert trace.skill_id == "skill-1"
        assert trace.skill_name == "test_skill"
        assert trace.started_at == now
        assert trace.status == "running"
        assert trace.input_data == {"key": "value"}
        assert trace.completed_at is None
        assert trace.duration_ms is None

    def test_skill_trace_to_dict(self) -> None:
        """to_dict should return complete dictionary representation."""
        now = datetime.utcnow()
        trace = SkillTrace(
            skill_id="skill-1",
            skill_name="test_skill",
            started_at=now,
            input_data={"input": "data"},
        )
        trace.completed_at = now
        trace.duration_ms = 100
        trace.status = "success"
        trace.output_data = {"output": "result"}

        trace_dict = trace.to_dict()

        assert trace_dict["skill_id"] == "skill-1"
        assert trace_dict["skill_name"] == "test_skill"
        assert trace_dict["status"] == "success"
        assert trace_dict["duration_ms"] == 100
        assert "started_at" in trace_dict
        assert "completed_at" in trace_dict
        assert trace_dict["input_size_bytes"] > 0
        assert trace_dict["output_size_bytes"] > 0


class TestExecutionTrace:
    """Tests for ExecutionTrace class."""

    def test_execution_trace_initialization(self) -> None:
        """ExecutionTrace should initialize with correct values."""
        now = datetime.utcnow()
        trace = ExecutionTrace(
            trace_id="trace-1",
            agent_id="agent-1",
            started_at=now,
        )

        assert trace.trace_id == "trace-1"
        assert trace.agent_id == "agent-1"
        assert trace.started_at == now
        assert trace.status == "running"
        assert len(trace.skills) == 0
        assert trace.completed_at is None

    def test_start_skill_adds_skill_trace(self) -> None:
        """start_skill should add a new SkillTrace to the list."""
        trace = ExecutionTrace(
            trace_id="trace-1",
            agent_id="agent-1",
            started_at=datetime.utcnow(),
        )

        skill_trace = trace.start_skill(
            skill_id="skill-1",
            skill_name="test_skill",
            input_data={"key": "value"},
        )

        assert len(trace.skills) == 1
        assert trace.skills[0] is skill_trace
        assert skill_trace.skill_id == "skill-1"
        assert skill_trace.skill_name == "test_skill"

    def test_complete_skill_updates_skill_trace(self) -> None:
        """complete_skill should update skill trace with results."""
        trace = ExecutionTrace(
            trace_id="trace-1",
            agent_id="agent-1",
            started_at=datetime.utcnow(),
        )

        skill_trace = trace.start_skill(
            skill_id="skill-1",
            skill_name="test_skill",
            input_data={},
        )

        trace.complete_skill(
            skill_trace=skill_trace,
            status="success",
            output_data={"result": "done"},
        )

        assert skill_trace.status == "success"
        assert skill_trace.output_data == {"result": "done"}
        assert skill_trace.completed_at is not None
        assert skill_trace.duration_ms is not None
        assert skill_trace.duration_ms >= 0

    def test_complete_skill_with_error(self) -> None:
        """complete_skill should handle errors correctly."""
        trace = ExecutionTrace(
            trace_id="trace-1",
            agent_id="agent-1",
            started_at=datetime.utcnow(),
        )

        skill_trace = trace.start_skill(
            skill_id="skill-1",
            skill_name="test_skill",
            input_data={},
        )

        trace.complete_skill(
            skill_trace=skill_trace,
            status="failed",
            error="Test error message",
        )

        assert skill_trace.status == "failed"
        assert skill_trace.error == "Test error message"
        assert skill_trace.completed_at is not None

    def test_complete_execution_trace(self) -> None:
        """complete should finalize the execution trace."""
        trace = ExecutionTrace(
            trace_id="trace-1",
            agent_id="agent-1",
            started_at=datetime.utcnow(),
        )

        trace.complete(status="success")

        assert trace.status == "success"
        assert trace.completed_at is not None
        assert trace.total_duration_ms is not None
        assert trace.total_duration_ms >= 0

    def test_to_dict_returns_complete_trace(self) -> None:
        """to_dict should return complete trace information."""
        trace = ExecutionTrace(
            trace_id="trace-1",
            agent_id="agent-1",
            started_at=datetime.utcnow(),
        )

        # Add some skills
        skill1 = trace.start_skill("skill-1", "test1", {})
        trace.complete_skill(skill1, "success", {"result": "ok"})

        skill2 = trace.start_skill("skill-2", "test2", {})
        trace.complete_skill(skill2, "failed", error="error")

        trace.complete("success")

        trace_dict = trace.to_dict()

        assert trace_dict["trace_id"] == "trace-1"
        assert trace_dict["agent_id"] == "agent-1"
        assert trace_dict["status"] == "success"
        assert trace_dict["skill_count"] == 2
        assert trace_dict["successful_skills"] == 1
        assert trace_dict["failed_skills"] == 1
        assert len(trace_dict["skills"]) == 2


class TestExecutionTracer:
    """Tests for ExecutionTracer class."""

    def test_get_execution_tracer_returns_singleton(self) -> None:
        """get_execution_tracer should return same instance each time."""
        tracer1 = get_execution_tracer()
        tracer2 = get_execution_tracer()

        assert tracer1 is tracer2

    def test_start_trace_creates_new_trace(self) -> None:
        """start_trace should create and return new ExecutionTrace."""
        tracer = get_execution_tracer()

        trace = tracer.start_trace(trace_id="trace-1", agent_id="agent-1")

        assert trace.trace_id == "trace-1"
        assert trace.agent_id == "agent-1"
        assert trace.status == "running"

    def test_get_current_trace_returns_active_trace(self) -> None:
        """get_current_trace should return the active trace."""
        tracer = get_execution_tracer()

        trace = tracer.start_trace(trace_id="trace-2", agent_id="agent-2")
        current_trace = tracer.get_current_trace()

        assert current_trace is trace
        assert current_trace is not None
        assert current_trace.trace_id == "trace-2"

    def test_clear_trace_removes_current_trace(self) -> None:
        """clear_trace should remove the current trace."""
        tracer = get_execution_tracer()

        tracer.start_trace(trace_id="trace-3", agent_id="agent-3")
        assert tracer.get_current_trace() is not None

        tracer.clear_trace()
        assert tracer.get_current_trace() is None
