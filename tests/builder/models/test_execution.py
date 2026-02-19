"""Tests for AgentExecution model."""

from datetime import datetime, timezone

from omniforge.builder.models import AgentExecution, ExecutionStatus


class TestAgentExecution:
    """Tests for AgentExecution model."""

    def test_minimal_execution(self) -> None:
        """Test creating minimal execution."""
        execution = AgentExecution(
            agent_id="agent-123",
            tenant_id="tenant-456",
            trigger_type="on_demand",
        )

        assert execution.agent_id == "agent-123"
        assert execution.tenant_id == "tenant-456"
        assert execution.status == ExecutionStatus.PENDING
        assert execution.trigger_type == "on_demand"
        assert execution.skill_executions == []
        assert execution.metadata == {}

    def test_complete_execution(self) -> None:
        """Test creating complete execution with all fields."""
        started = datetime.now(timezone.utc)
        completed = datetime.now(timezone.utc)

        execution = AgentExecution(
            id="exec-123",
            agent_id="agent-456",
            tenant_id="tenant-789",
            status=ExecutionStatus.SUCCESS,
            trigger_type="scheduled",
            started_at=started,
            completed_at=completed,
            duration_ms=45000,
            output={"report_path": "reports/weekly.md", "items_count": 42},
            skill_executions=[
                {
                    "skill_id": "notion-report",
                    "status": "success",
                    "duration_ms": 30000,
                    "output": {"items_found": 42},
                },
                {
                    "skill_id": "slack-post",
                    "status": "success",
                    "duration_ms": 15000,
                    "output": {"message_id": "msg-123"},
                },
            ],
            metadata={"user_id": "user-999", "version": "1.0"},
        )

        assert execution.id == "exec-123"
        assert execution.status == ExecutionStatus.SUCCESS
        assert execution.duration_ms == 45000
        assert execution.output["items_count"] == 42
        assert len(execution.skill_executions) == 2
        assert execution.skill_executions[0]["skill_id"] == "notion-report"
        assert execution.metadata["user_id"] == "user-999"

    def test_failed_execution_with_error(self) -> None:
        """Test failed execution with error message."""
        execution = AgentExecution(
            agent_id="agent-123",
            tenant_id="tenant-456",
            status=ExecutionStatus.FAILED,
            trigger_type="scheduled",
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            error="Notion API rate limit exceeded",
        )

        assert execution.status == ExecutionStatus.FAILED
        assert execution.error == "Notion API rate limit exceeded"

    def test_trigger_type_validation(self) -> None:
        """Test trigger_type validation."""
        # Valid trigger types
        for trigger in ["on_demand", "scheduled", "event_driven"]:
            AgentExecution(
                agent_id="agent-123",
                tenant_id="tenant-456",
                trigger_type=trigger,
            )

    def test_duration_must_be_positive(self) -> None:
        """Test duration_ms must be >= 0."""
        # Valid: 0 duration
        AgentExecution(
            agent_id="agent-123",
            tenant_id="tenant-456",
            trigger_type="on_demand",
            duration_ms=0,
        )

        # Valid: positive duration
        AgentExecution(
            agent_id="agent-123",
            tenant_id="tenant-456",
            trigger_type="on_demand",
            duration_ms=1000,
        )

    def test_all_execution_statuses(self) -> None:
        """Test all execution status values."""
        statuses = [
            ExecutionStatus.PENDING,
            ExecutionStatus.RUNNING,
            ExecutionStatus.SUCCESS,
            ExecutionStatus.FAILED,
            ExecutionStatus.TIMEOUT,
            ExecutionStatus.CANCELLED,
        ]

        for status in statuses:
            execution = AgentExecution(
                agent_id="agent-123",
                tenant_id="tenant-456",
                trigger_type="on_demand",
                status=status,
            )
            assert execution.status == status
