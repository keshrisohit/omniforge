"""Tests for task lifecycle models."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from omniforge.agents.models import Artifact, TextPart
from omniforge.tasks.models import (
    Task,
    TaskCreateRequest,
    TaskError,
    TaskMessage,
    TaskSendRequest,
    TaskState,
)


class TestTaskState:
    """Tests for TaskState enum."""

    def test_terminal_states_returns_correct_set(self) -> None:
        """Terminal states should include completed, failed, cancelled, rejected."""
        terminal = TaskState.terminal_states()
        assert terminal == {
            TaskState.COMPLETED,
            TaskState.FAILED,
            TaskState.CANCELLED,
            TaskState.REJECTED,
        }

    def test_is_terminal_returns_true_for_terminal_states(self) -> None:
        """is_terminal() should return True for terminal states."""
        assert TaskState.COMPLETED.is_terminal() is True
        assert TaskState.FAILED.is_terminal() is True
        assert TaskState.CANCELLED.is_terminal() is True
        assert TaskState.REJECTED.is_terminal() is True

    def test_is_terminal_returns_false_for_non_terminal_states(self) -> None:
        """is_terminal() should return False for non-terminal states."""
        assert TaskState.SUBMITTED.is_terminal() is False
        assert TaskState.WORKING.is_terminal() is False
        assert TaskState.INPUT_REQUIRED.is_terminal() is False
        assert TaskState.AUTH_REQUIRED.is_terminal() is False


class TestTaskMessage:
    """Tests for TaskMessage model."""

    def test_create_message_with_valid_data(self) -> None:
        """TaskMessage should initialize with valid data."""
        now = datetime.now(timezone.utc)
        message = TaskMessage(
            id="msg-123",
            role="user",
            parts=[TextPart(text="Hello")],
            created_at=now,
        )

        assert message.id == "msg-123"
        assert message.role == "user"
        assert len(message.parts) == 1
        assert message.created_at == now

    def test_create_message_with_agent_role(self) -> None:
        """TaskMessage should accept agent role."""
        message = TaskMessage(
            id="msg-456",
            role="agent",
            parts=[TextPart(text="Hi")],
            created_at=datetime.now(timezone.utc),
        )

        assert message.role == "agent"

    def test_create_message_with_invalid_role_raises_error(self) -> None:
        """TaskMessage should reject invalid roles."""
        with pytest.raises(ValidationError):
            TaskMessage(
                id="msg-789",
                role="invalid",
                parts=[TextPart(text="Test")],
                created_at=datetime.now(timezone.utc),
            )

    def test_create_message_with_empty_parts_raises_error(self) -> None:
        """TaskMessage should reject empty parts list."""
        with pytest.raises(ValidationError, match="at least one part"):
            TaskMessage(
                id="msg-999",
                role="user",
                parts=[],
                created_at=datetime.now(timezone.utc),
            )

    def test_create_message_with_multiple_parts(self) -> None:
        """TaskMessage should support multiple message parts."""
        message = TaskMessage(
            id="msg-multi",
            role="user",
            parts=[TextPart(text="Part 1"), TextPart(text="Part 2")],
            created_at=datetime.now(timezone.utc),
        )

        assert len(message.parts) == 2


class TestTaskError:
    """Tests for TaskError model."""

    def test_create_error_with_minimal_data(self) -> None:
        """TaskError should initialize with code and message."""
        error = TaskError(code="ERR001", message="Something went wrong")

        assert error.code == "ERR001"
        assert error.message == "Something went wrong"
        assert error.details is None

    def test_create_error_with_details(self) -> None:
        """TaskError should support optional details."""
        error = TaskError(
            code="ERR002",
            message="Validation failed",
            details={"field": "email", "reason": "invalid format"},
        )

        assert error.details == {"field": "email", "reason": "invalid format"}

    def test_create_error_with_long_code_raises_error(self) -> None:
        """TaskError should reject codes exceeding 100 characters."""
        with pytest.raises(ValidationError):
            TaskError(code="X" * 101, message="Error")

    def test_create_error_with_long_message_raises_error(self) -> None:
        """TaskError should reject messages exceeding 1000 characters."""
        with pytest.raises(ValidationError):
            TaskError(code="ERR003", message="X" * 1001)


class TestTask:
    """Tests for Task model."""

    def test_create_task_with_valid_data(self) -> None:
        """Task should initialize with valid data."""
        now = datetime.now(timezone.utc)
        task = Task(
            id="task-123",
            agent_id="agent-456",
            state=TaskState.SUBMITTED,
            created_at=now,
            updated_at=now,
            tenant_id="tenant-789",
            user_id="user-001",
        )

        assert task.id == "task-123"
        assert task.agent_id == "agent-456"
        assert task.state == TaskState.SUBMITTED
        assert task.messages == []
        assert task.artifacts == []
        assert task.error is None
        assert task.parent_task_id is None

    def test_create_task_with_messages_and_artifacts(self) -> None:
        """Task should support messages and artifacts."""
        now = datetime.now(timezone.utc)
        message = TaskMessage(id="msg-1", role="user", parts=[TextPart(text="Hi")], created_at=now)
        artifact = Artifact(
            id="art-1",
            type="document",
            title="Result",
            content="Output",
        )

        task = Task(
            id="task-123",
            agent_id="agent-456",
            state=TaskState.WORKING,
            messages=[message],
            artifacts=[artifact],
            created_at=now,
            updated_at=now,
            tenant_id="tenant-789",
            user_id="user-001",
        )

        assert len(task.messages) == 1
        assert len(task.artifacts) == 1

    def test_create_task_with_parent_task_id(self) -> None:
        """Task should support parent_task_id for subtasks."""
        now = datetime.now(timezone.utc)
        task = Task(
            id="task-child",
            agent_id="agent-1",
            state=TaskState.SUBMITTED,
            created_at=now,
            updated_at=now,
            tenant_id="tenant-1",
            user_id="user-1",
            parent_task_id="task-parent",
        )

        assert task.parent_task_id == "task-parent"

    def test_can_transition_from_submitted_to_working(self) -> None:
        """Task in submitted state should allow transition to working."""
        task = Task(
            id="task-1",
            agent_id="agent-1",
            state=TaskState.SUBMITTED,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            tenant_id="tenant-1",
            user_id="user-1",
        )

        assert task.can_transition_to(TaskState.WORKING) is True

    def test_can_transition_from_submitted_to_rejected(self) -> None:
        """Task in submitted state should allow transition to rejected."""
        task = Task(
            id="task-1",
            agent_id="agent-1",
            state=TaskState.SUBMITTED,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            tenant_id="tenant-1",
            user_id="user-1",
        )

        assert task.can_transition_to(TaskState.REJECTED) is True

    def test_cannot_transition_from_submitted_to_completed(self) -> None:
        """Task in submitted state should not allow direct transition to completed."""
        task = Task(
            id="task-1",
            agent_id="agent-1",
            state=TaskState.SUBMITTED,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            tenant_id="tenant-1",
            user_id="user-1",
        )

        assert task.can_transition_to(TaskState.COMPLETED) is False

    def test_can_transition_from_working_to_completed(self) -> None:
        """Task in working state should allow transition to completed."""
        task = Task(
            id="task-1",
            agent_id="agent-1",
            state=TaskState.WORKING,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            tenant_id="tenant-1",
            user_id="user-1",
        )

        assert task.can_transition_to(TaskState.COMPLETED) is True

    def test_can_transition_from_working_to_input_required(self) -> None:
        """Task in working state should allow transition to input_required."""
        task = Task(
            id="task-1",
            agent_id="agent-1",
            state=TaskState.WORKING,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            tenant_id="tenant-1",
            user_id="user-1",
        )

        assert task.can_transition_to(TaskState.INPUT_REQUIRED) is True

    def test_can_transition_from_input_required_to_working(self) -> None:
        """Task in input_required state should allow transition to working."""
        task = Task(
            id="task-1",
            agent_id="agent-1",
            state=TaskState.INPUT_REQUIRED,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            tenant_id="tenant-1",
            user_id="user-1",
        )

        assert task.can_transition_to(TaskState.WORKING) is True

    def test_cannot_transition_from_terminal_state(self) -> None:
        """Task in terminal state should not allow any transitions."""
        task = Task(
            id="task-1",
            agent_id="agent-1",
            state=TaskState.COMPLETED,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            tenant_id="tenant-1",
            user_id="user-1",
        )

        assert task.can_transition_to(TaskState.WORKING) is False
        assert task.can_transition_to(TaskState.FAILED) is False


class TestTaskCreateRequest:
    """Tests for TaskCreateRequest model."""

    def test_create_request_with_valid_data(self) -> None:
        """TaskCreateRequest should initialize with valid data."""
        request = TaskCreateRequest(
            agent_id="agent-123",
            message_parts=[TextPart(text="Hello")],
            tenant_id="tenant-456",
            user_id="user-789",
        )

        assert request.agent_id == "agent-123"
        assert len(request.message_parts) == 1
        assert request.tenant_id == "tenant-456"
        assert request.user_id == "user-789"
        assert request.parent_task_id is None

    def test_create_request_with_parent_task_id(self) -> None:
        """TaskCreateRequest should support parent_task_id."""
        request = TaskCreateRequest(
            agent_id="agent-1",
            message_parts=[TextPart(text="Hi")],
            tenant_id="tenant-1",
            user_id="user-1",
            parent_task_id="task-parent",
        )

        assert request.parent_task_id == "task-parent"

    def test_create_request_with_empty_message_parts_raises_error(self) -> None:
        """TaskCreateRequest should reject empty message_parts."""
        with pytest.raises(ValidationError, match="at least one message part"):
            TaskCreateRequest(
                agent_id="agent-1",
                message_parts=[],
                tenant_id="tenant-1",
                user_id="user-1",
            )


class TestTaskSendRequest:
    """Tests for TaskSendRequest model."""

    def test_send_request_with_valid_data(self) -> None:
        """TaskSendRequest should initialize with valid data."""
        request = TaskSendRequest(message_parts=[TextPart(text="Follow-up")])

        assert len(request.message_parts) == 1

    def test_send_request_with_empty_message_parts_raises_error(self) -> None:
        """TaskSendRequest should reject empty message_parts."""
        with pytest.raises(ValidationError, match="at least one part"):
            TaskSendRequest(message_parts=[])

    def test_send_request_with_multiple_parts(self) -> None:
        """TaskSendRequest should support multiple message parts."""
        request = TaskSendRequest(message_parts=[TextPart(text="Part 1"), TextPart(text="Part 2")])

        assert len(request.message_parts) == 2
