"""Tests for A2A protocol models for orchestration and handoff."""

import pytest
from pydantic import ValidationError

from omniforge.orchestration.a2a_models import (
    CompletionStatus,
    DelegationError,
    HandoffAccept,
    HandoffError,
    HandoffRequest,
    HandoffReturn,
    OrchestrationError,
)


class TestErrorClasses:
    """Tests for orchestration error classes."""

    def test_orchestration_error_is_exception(self) -> None:
        """OrchestrationError should be an Exception."""
        error = OrchestrationError("test error")
        assert isinstance(error, Exception)
        assert str(error) == "test error"

    def test_handoff_error_inherits_from_orchestration_error(self) -> None:
        """HandoffError should inherit from OrchestrationError."""
        error = HandoffError("handoff failed")
        assert isinstance(error, OrchestrationError)
        assert isinstance(error, Exception)
        assert str(error) == "handoff failed"

    def test_delegation_error_inherits_from_orchestration_error(self) -> None:
        """DelegationError should inherit from OrchestrationError."""
        error = DelegationError("delegation failed")
        assert isinstance(error, OrchestrationError)
        assert isinstance(error, Exception)
        assert str(error) == "delegation failed"


class TestHandoffRequest:
    """Tests for HandoffRequest model."""

    def test_create_with_valid_data(self) -> None:
        """HandoffRequest should validate with all required fields."""
        request = HandoffRequest(
            thread_id="thread-123",
            tenant_id="tenant-456",
            user_id="user-789",
            source_agent_id="agent-main",
            target_agent_id="agent-skill",
            context_summary="User wants to create a skill",
            handoff_reason="Skill creation requested",
        )

        assert request.thread_id == "thread-123"
        assert request.tenant_id == "tenant-456"
        assert request.user_id == "user-789"
        assert request.source_agent_id == "agent-main"
        assert request.target_agent_id == "agent-skill"
        assert request.context_summary == "User wants to create a skill"
        assert request.recent_message_count == 5  # default
        assert request.handoff_reason == "Skill creation requested"
        assert request.preserve_state is True  # default
        assert request.return_expected is True  # default
        assert request.handoff_metadata is None  # default

    def test_create_with_custom_recent_message_count(self) -> None:
        """HandoffRequest should accept custom recent_message_count."""
        request = HandoffRequest(
            thread_id="thread-123",
            tenant_id="tenant-456",
            user_id="user-789",
            source_agent_id="agent-main",
            target_agent_id="agent-skill",
            context_summary="Context",
            handoff_reason="Reason",
            recent_message_count=10,
        )

        assert request.recent_message_count == 10

    def test_create_with_metadata(self) -> None:
        """HandoffRequest should accept optional handoff_metadata."""
        metadata = {"skill_type": "slack", "priority": "high"}
        request = HandoffRequest(
            thread_id="thread-123",
            tenant_id="tenant-456",
            user_id="user-789",
            source_agent_id="agent-main",
            target_agent_id="agent-skill",
            context_summary="Context",
            handoff_reason="Reason",
            handoff_metadata=metadata,
        )

        assert request.handoff_metadata == metadata

    def test_reject_empty_thread_id(self) -> None:
        """HandoffRequest should reject empty thread_id."""
        with pytest.raises(ValidationError) as exc_info:
            HandoffRequest(
                thread_id="",
                tenant_id="tenant-456",
                user_id="user-789",
                source_agent_id="agent-main",
                target_agent_id="agent-skill",
                context_summary="Context",
                handoff_reason="Reason",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("thread_id",) for e in errors)

    def test_reject_empty_tenant_id(self) -> None:
        """HandoffRequest should reject empty tenant_id."""
        with pytest.raises(ValidationError) as exc_info:
            HandoffRequest(
                thread_id="thread-123",
                tenant_id="",
                user_id="user-789",
                source_agent_id="agent-main",
                target_agent_id="agent-skill",
                context_summary="Context",
                handoff_reason="Reason",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("tenant_id",) for e in errors)

    def test_reject_missing_required_fields(self) -> None:
        """HandoffRequest should reject missing required fields."""
        with pytest.raises(ValidationError) as exc_info:
            HandoffRequest(
                thread_id="thread-123",
                tenant_id="tenant-456",
            )

        errors = exc_info.value.errors()
        assert len(errors) >= 4  # user_id, source/target agents, context, reason

    def test_reject_recent_message_count_below_min(self) -> None:
        """HandoffRequest should reject recent_message_count < 1."""
        with pytest.raises(ValidationError) as exc_info:
            HandoffRequest(
                thread_id="thread-123",
                tenant_id="tenant-456",
                user_id="user-789",
                source_agent_id="agent-main",
                target_agent_id="agent-skill",
                context_summary="Context",
                handoff_reason="Reason",
                recent_message_count=0,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("recent_message_count",) for e in errors)

    def test_reject_recent_message_count_above_max(self) -> None:
        """HandoffRequest should reject recent_message_count > 20."""
        with pytest.raises(ValidationError) as exc_info:
            HandoffRequest(
                thread_id="thread-123",
                tenant_id="tenant-456",
                user_id="user-789",
                source_agent_id="agent-main",
                target_agent_id="agent-skill",
                context_summary="Context",
                handoff_reason="Reason",
                recent_message_count=21,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("recent_message_count",) for e in errors)

    def test_reject_context_summary_too_long(self) -> None:
        """HandoffRequest should reject context_summary > 2000 chars."""
        with pytest.raises(ValidationError) as exc_info:
            HandoffRequest(
                thread_id="thread-123",
                tenant_id="tenant-456",
                user_id="user-789",
                source_agent_id="agent-main",
                target_agent_id="agent-skill",
                context_summary="x" * 2001,
                handoff_reason="Reason",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("context_summary",) for e in errors)

    def test_serialization_deserialization(self) -> None:
        """HandoffRequest should serialize and deserialize correctly."""
        original = HandoffRequest(
            thread_id="thread-123",
            tenant_id="tenant-456",
            user_id="user-789",
            source_agent_id="agent-main",
            target_agent_id="agent-skill",
            context_summary="Context",
            handoff_reason="Reason",
            recent_message_count=8,
        )

        # Serialize to dict
        data = original.model_dump()

        # Deserialize from dict
        restored = HandoffRequest(**data)

        assert restored.thread_id == original.thread_id
        assert restored.tenant_id == original.tenant_id
        assert restored.recent_message_count == original.recent_message_count


class TestHandoffAccept:
    """Tests for HandoffAccept model."""

    def test_create_accepted_handoff(self) -> None:
        """HandoffAccept should validate accepted handoff."""
        accept = HandoffAccept(
            thread_id="thread-123",
            source_agent_id="agent-main",
            target_agent_id="agent-skill",
            accepted=True,
        )

        assert accept.thread_id == "thread-123"
        assert accept.source_agent_id == "agent-main"
        assert accept.target_agent_id == "agent-skill"
        assert accept.accepted is True
        assert accept.rejection_reason is None
        assert accept.estimated_duration_seconds is None

    def test_create_rejected_handoff(self) -> None:
        """HandoffAccept should validate rejected handoff with reason."""
        accept = HandoffAccept(
            thread_id="thread-123",
            source_agent_id="agent-main",
            target_agent_id="agent-skill",
            accepted=False,
            rejection_reason="Agent is busy",
        )

        assert accept.accepted is False
        assert accept.rejection_reason == "Agent is busy"

    def test_create_with_estimated_duration(self) -> None:
        """HandoffAccept should accept estimated_duration_seconds."""
        accept = HandoffAccept(
            thread_id="thread-123",
            source_agent_id="agent-main",
            target_agent_id="agent-skill",
            accepted=True,
            estimated_duration_seconds=300,
        )

        assert accept.estimated_duration_seconds == 300

    def test_reject_negative_estimated_duration(self) -> None:
        """HandoffAccept should reject negative estimated_duration_seconds."""
        with pytest.raises(ValidationError) as exc_info:
            HandoffAccept(
                thread_id="thread-123",
                source_agent_id="agent-main",
                target_agent_id="agent-skill",
                accepted=True,
                estimated_duration_seconds=-1,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("estimated_duration_seconds",) for e in errors)

    def test_reject_missing_required_fields(self) -> None:
        """HandoffAccept should reject missing required fields."""
        with pytest.raises(ValidationError) as exc_info:
            HandoffAccept(thread_id="thread-123")

        errors = exc_info.value.errors()
        assert len(errors) >= 3  # source/target agents, accepted

    def test_reject_empty_thread_id(self) -> None:
        """HandoffAccept should reject empty thread_id."""
        with pytest.raises(ValidationError) as exc_info:
            HandoffAccept(
                thread_id="",
                source_agent_id="agent-main",
                target_agent_id="agent-skill",
                accepted=True,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("thread_id",) for e in errors)

    def test_serialization_deserialization(self) -> None:
        """HandoffAccept should serialize and deserialize correctly."""
        original = HandoffAccept(
            thread_id="thread-123",
            source_agent_id="agent-main",
            target_agent_id="agent-skill",
            accepted=True,
            estimated_duration_seconds=600,
        )

        # Serialize to dict
        data = original.model_dump()

        # Deserialize from dict
        restored = HandoffAccept(**data)

        assert restored.thread_id == original.thread_id
        assert restored.accepted == original.accepted
        assert restored.estimated_duration_seconds == original.estimated_duration_seconds


class TestHandoffReturn:
    """Tests for HandoffReturn model."""

    def test_create_completed_handoff(self) -> None:
        """HandoffReturn should validate completed handoff."""
        handoff_return = HandoffReturn(
            thread_id="thread-123",
            tenant_id="tenant-456",
            source_agent_id="agent-skill",
            target_agent_id="agent-main",
            completion_status=CompletionStatus.COMPLETED,
            result_summary="Skill created successfully",
            artifacts_created=["artifact-1", "artifact-2"],
        )

        assert handoff_return.thread_id == "thread-123"
        assert handoff_return.tenant_id == "tenant-456"
        assert handoff_return.source_agent_id == "agent-skill"
        assert handoff_return.target_agent_id == "agent-main"
        assert handoff_return.completion_status == CompletionStatus.COMPLETED
        assert handoff_return.result_summary == "Skill created successfully"
        assert handoff_return.artifacts_created == ["artifact-1", "artifact-2"]

    def test_create_cancelled_handoff(self) -> None:
        """HandoffReturn should validate cancelled handoff."""
        handoff_return = HandoffReturn(
            thread_id="thread-123",
            tenant_id="tenant-456",
            source_agent_id="agent-skill",
            target_agent_id="agent-main",
            completion_status=CompletionStatus.CANCELLED,
        )

        assert handoff_return.completion_status == CompletionStatus.CANCELLED
        assert handoff_return.result_summary is None
        assert handoff_return.artifacts_created == []

    def test_create_error_handoff(self) -> None:
        """HandoffReturn should validate error handoff."""
        handoff_return = HandoffReturn(
            thread_id="thread-123",
            tenant_id="tenant-456",
            source_agent_id="agent-skill",
            target_agent_id="agent-main",
            completion_status=CompletionStatus.ERROR,
            result_summary="Failed to create skill: validation error",
        )

        assert handoff_return.completion_status == CompletionStatus.ERROR
        assert "validation error" in handoff_return.result_summary

    def test_completion_status_accepts_valid_values(self) -> None:
        """HandoffReturn should accept valid completion_status values."""
        for status in [
            CompletionStatus.COMPLETED,
            CompletionStatus.CANCELLED,
            CompletionStatus.ERROR,
        ]:
            handoff_return = HandoffReturn(
                thread_id="thread-123",
                tenant_id="tenant-456",
                source_agent_id="agent-skill",
                target_agent_id="agent-main",
                completion_status=status,
            )
            assert handoff_return.completion_status == status

    def test_completion_status_rejects_invalid_values(self) -> None:
        """HandoffReturn should reject invalid completion_status values."""
        with pytest.raises(ValidationError) as exc_info:
            HandoffReturn(
                thread_id="thread-123",
                tenant_id="tenant-456",
                source_agent_id="agent-skill",
                target_agent_id="agent-main",
                completion_status="invalid_status",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("completion_status",) for e in errors)

    def test_reject_empty_thread_id(self) -> None:
        """HandoffReturn should reject empty thread_id."""
        with pytest.raises(ValidationError) as exc_info:
            HandoffReturn(
                thread_id="",
                tenant_id="tenant-456",
                source_agent_id="agent-skill",
                target_agent_id="agent-main",
                completion_status=CompletionStatus.COMPLETED,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("thread_id",) for e in errors)

    def test_reject_missing_required_fields(self) -> None:
        """HandoffReturn should reject missing required fields."""
        with pytest.raises(ValidationError) as exc_info:
            HandoffReturn(thread_id="thread-123")

        errors = exc_info.value.errors()
        assert len(errors) >= 4  # tenant_id, source/target agents, status

    def test_reject_empty_artifact_ids(self) -> None:
        """HandoffReturn should reject empty artifact IDs."""
        with pytest.raises(ValidationError) as exc_info:
            HandoffReturn(
                thread_id="thread-123",
                tenant_id="tenant-456",
                source_agent_id="agent-skill",
                target_agent_id="agent-main",
                completion_status=CompletionStatus.COMPLETED,
                artifacts_created=["artifact-1", "", "artifact-3"],
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("artifacts_created",) for e in errors)

    def test_reject_whitespace_artifact_ids(self) -> None:
        """HandoffReturn should reject whitespace-only artifact IDs."""
        with pytest.raises(ValidationError) as exc_info:
            HandoffReturn(
                thread_id="thread-123",
                tenant_id="tenant-456",
                source_agent_id="agent-skill",
                target_agent_id="agent-main",
                completion_status=CompletionStatus.COMPLETED,
                artifacts_created=["artifact-1", "   ", "artifact-3"],
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("artifacts_created",) for e in errors)

    def test_reject_result_summary_too_long(self) -> None:
        """HandoffReturn should reject result_summary > 2000 chars."""
        with pytest.raises(ValidationError) as exc_info:
            HandoffReturn(
                thread_id="thread-123",
                tenant_id="tenant-456",
                source_agent_id="agent-skill",
                target_agent_id="agent-main",
                completion_status=CompletionStatus.COMPLETED,
                result_summary="x" * 2001,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("result_summary",) for e in errors)

    def test_serialization_deserialization(self) -> None:
        """HandoffReturn should serialize and deserialize correctly."""
        original = HandoffReturn(
            thread_id="thread-123",
            tenant_id="tenant-456",
            source_agent_id="agent-skill",
            target_agent_id="agent-main",
            completion_status=CompletionStatus.COMPLETED,
            result_summary="Success",
            artifacts_created=["art-1", "art-2"],
        )

        # Serialize to dict
        data = original.model_dump()

        # Deserialize from dict
        restored = HandoffReturn(**data)

        assert restored.thread_id == original.thread_id
        assert restored.completion_status == original.completion_status
        assert restored.artifacts_created == original.artifacts_created


class TestCompletionStatus:
    """Tests for CompletionStatus enum."""

    def test_enum_values(self) -> None:
        """CompletionStatus should have expected enum values."""
        assert CompletionStatus.COMPLETED == "completed"
        assert CompletionStatus.CANCELLED == "cancelled"
        assert CompletionStatus.ERROR == "error"

    def test_enum_membership(self) -> None:
        """CompletionStatus should contain expected members."""
        assert "COMPLETED" in CompletionStatus.__members__
        assert "CANCELLED" in CompletionStatus.__members__
        assert "ERROR" in CompletionStatus.__members__
