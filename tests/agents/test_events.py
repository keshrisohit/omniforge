"""Tests for task event models."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from omniforge.agents.events import (
    TaskArtifactEvent,
    TaskDoneEvent,
    TaskErrorEvent,
    TaskMessageEvent,
    TaskStatusEvent,
)
from omniforge.agents.models import Artifact, TextPart
from omniforge.tasks.models import TaskState


class TestTaskStatusEvent:
    """Tests for TaskStatusEvent model."""

    def test_create_status_event_with_valid_data(self) -> None:
        """TaskStatusEvent should initialize with valid data."""
        now = datetime.now(timezone.utc)
        event = TaskStatusEvent(
            task_id="task-123",
            timestamp=now,
            state=TaskState.WORKING,
        )

        assert event.type == "status"
        assert event.task_id == "task-123"
        assert event.timestamp == now
        assert event.state == TaskState.WORKING
        assert event.message is None

    def test_create_status_event_with_message(self) -> None:
        """TaskStatusEvent should support optional message."""
        event = TaskStatusEvent(
            task_id="task-456",
            timestamp=datetime.now(timezone.utc),
            state=TaskState.COMPLETED,
            message="Task completed successfully",
        )

        assert event.message == "Task completed successfully"

    def test_status_event_type_is_literal(self) -> None:
        """TaskStatusEvent type field should always be 'status'."""
        event = TaskStatusEvent(
            task_id="task-789",
            timestamp=datetime.now(timezone.utc),
            state=TaskState.SUBMITTED,
        )

        assert event.type == "status"


class TestTaskMessageEvent:
    """Tests for TaskMessageEvent model."""

    def test_create_message_event_with_valid_data(self) -> None:
        """TaskMessageEvent should initialize with valid data."""
        now = datetime.now(timezone.utc)
        event = TaskMessageEvent(
            task_id="task-123",
            timestamp=now,
            message_parts=[TextPart(text="Agent response")],
        )

        assert event.type == "message"
        assert event.task_id == "task-123"
        assert event.timestamp == now
        assert len(event.message_parts) == 1
        assert event.is_partial is False

    def test_create_message_event_with_partial_flag(self) -> None:
        """TaskMessageEvent should support is_partial flag for streaming."""
        event = TaskMessageEvent(
            task_id="task-456",
            timestamp=datetime.now(timezone.utc),
            message_parts=[TextPart(text="Partial...")],
            is_partial=True,
        )

        assert event.is_partial is True

    def test_create_message_event_with_multiple_parts(self) -> None:
        """TaskMessageEvent should support multiple message parts."""
        event = TaskMessageEvent(
            task_id="task-789",
            timestamp=datetime.now(timezone.utc),
            message_parts=[TextPart(text="Part 1"), TextPart(text="Part 2")],
        )

        assert len(event.message_parts) == 2

    def test_message_event_type_is_literal(self) -> None:
        """TaskMessageEvent type field should always be 'message'."""
        event = TaskMessageEvent(
            task_id="task-001",
            timestamp=datetime.now(timezone.utc),
            message_parts=[TextPart(text="Test")],
        )

        assert event.type == "message"


class TestTaskArtifactEvent:
    """Tests for TaskArtifactEvent model."""

    def test_create_artifact_event_with_valid_data(self) -> None:
        """TaskArtifactEvent should initialize with valid data."""
        now = datetime.now(timezone.utc)
        artifact = Artifact(
            id="art-123",
            type="document",
            title="Generated Report",
            content="Report content here",
        )
        event = TaskArtifactEvent(
            task_id="task-123",
            timestamp=now,
            artifact=artifact,
        )

        assert event.type == "artifact"
        assert event.task_id == "task-123"
        assert event.timestamp == now
        assert event.artifact.id == "art-123"

    def test_artifact_event_type_is_literal(self) -> None:
        """TaskArtifactEvent type field should always be 'artifact'."""
        artifact = Artifact(id="art-456", type="image", title="Chart", content="base64data")
        event = TaskArtifactEvent(
            task_id="task-456",
            timestamp=datetime.now(timezone.utc),
            artifact=artifact,
        )

        assert event.type == "artifact"


class TestTaskDoneEvent:
    """Tests for TaskDoneEvent model."""

    def test_create_done_event_with_completed_state(self) -> None:
        """TaskDoneEvent should initialize with completed state."""
        now = datetime.now(timezone.utc)
        event = TaskDoneEvent(
            task_id="task-123",
            timestamp=now,
            final_state=TaskState.COMPLETED,
        )

        assert event.type == "done"
        assert event.task_id == "task-123"
        assert event.timestamp == now
        assert event.final_state == TaskState.COMPLETED

    def test_create_done_event_with_failed_state(self) -> None:
        """TaskDoneEvent should accept failed as final state."""
        event = TaskDoneEvent(
            task_id="task-456",
            timestamp=datetime.now(timezone.utc),
            final_state=TaskState.FAILED,
        )

        assert event.final_state == TaskState.FAILED

    def test_create_done_event_with_cancelled_state(self) -> None:
        """TaskDoneEvent should accept cancelled as final state."""
        event = TaskDoneEvent(
            task_id="task-789",
            timestamp=datetime.now(timezone.utc),
            final_state=TaskState.CANCELLED,
        )

        assert event.final_state == TaskState.CANCELLED

    def test_create_done_event_with_non_terminal_state_raises_error(self) -> None:
        """TaskDoneEvent should reject non-terminal states."""
        with pytest.raises(ValueError, match="terminal state"):
            TaskDoneEvent(
                task_id="task-999",
                timestamp=datetime.now(timezone.utc),
                final_state=TaskState.WORKING,
            )

    def test_create_done_event_with_submitted_state_raises_error(self) -> None:
        """TaskDoneEvent should reject submitted state."""
        with pytest.raises(ValueError, match="terminal state"):
            TaskDoneEvent(
                task_id="task-001",
                timestamp=datetime.now(timezone.utc),
                final_state=TaskState.SUBMITTED,
            )

    def test_done_event_type_is_literal(self) -> None:
        """TaskDoneEvent type field should always be 'done'."""
        event = TaskDoneEvent(
            task_id="task-002",
            timestamp=datetime.now(timezone.utc),
            final_state=TaskState.COMPLETED,
        )

        assert event.type == "done"


class TestTaskErrorEvent:
    """Tests for TaskErrorEvent model."""

    def test_create_error_event_with_valid_data(self) -> None:
        """TaskErrorEvent should initialize with valid data."""
        now = datetime.now(timezone.utc)
        event = TaskErrorEvent(
            task_id="task-123",
            timestamp=now,
            error_code="ERR001",
            error_message="Something went wrong",
        )

        assert event.type == "error"
        assert event.task_id == "task-123"
        assert event.timestamp == now
        assert event.error_code == "ERR001"
        assert event.error_message == "Something went wrong"
        assert event.details is None

    def test_create_error_event_with_details(self) -> None:
        """TaskErrorEvent should support optional details."""
        event = TaskErrorEvent(
            task_id="task-456",
            timestamp=datetime.now(timezone.utc),
            error_code="ERR002",
            error_message="Validation failed",
            details={"field": "email", "reason": "invalid format"},
        )

        assert event.details == {"field": "email", "reason": "invalid format"}

    def test_create_error_event_with_long_code_raises_error(self) -> None:
        """TaskErrorEvent should reject error codes exceeding 100 characters."""
        with pytest.raises(ValidationError):
            TaskErrorEvent(
                task_id="task-789",
                timestamp=datetime.now(timezone.utc),
                error_code="X" * 101,
                error_message="Error",
            )

    def test_create_error_event_with_long_message_raises_error(self) -> None:
        """TaskErrorEvent should reject error messages exceeding 1000 characters."""
        with pytest.raises(ValidationError):
            TaskErrorEvent(
                task_id="task-999",
                timestamp=datetime.now(timezone.utc),
                error_code="ERR003",
                error_message="X" * 1001,
            )

    def test_error_event_type_is_literal(self) -> None:
        """TaskErrorEvent type field should always be 'error'."""
        event = TaskErrorEvent(
            task_id="task-001",
            timestamp=datetime.now(timezone.utc),
            error_code="ERR004",
            error_message="Test error",
        )

        assert event.type == "error"
