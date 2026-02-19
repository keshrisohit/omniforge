"""Task lifecycle models and state management.

This module defines the core models for task management in the OmniForge platform,
including task states, messages, errors, and lifecycle tracking.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

from omniforge.agents.models import Artifact, MessagePart


class TaskState(str, Enum):
    """Possible states in a task lifecycle.

    State transitions:
        submitted -> working | rejected | cancelled
        working -> input_required | auth_required | completed | failed | cancelled
        input_required -> working | cancelled
        auth_required -> working | cancelled
        completed (terminal)
        failed (terminal)
        cancelled (terminal)
        rejected (terminal)
    """

    SUBMITTED = "submitted"
    WORKING = "working"
    INPUT_REQUIRED = "input_required"
    AUTH_REQUIRED = "auth_required"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REJECTED = "rejected"

    @classmethod
    def terminal_states(cls) -> set["TaskState"]:
        """Return set of terminal states that cannot be transitioned from.

        Returns:
            Set of terminal TaskState values
        """
        return {cls.COMPLETED, cls.FAILED, cls.CANCELLED, cls.REJECTED}

    def is_terminal(self) -> bool:
        """Check if this state is terminal.

        Returns:
            True if state is terminal, False otherwise
        """
        return self in self.terminal_states()


class TaskMessage(BaseModel):
    """A message in a task conversation.

    Attributes:
        id: Unique identifier for the message
        role: Message sender role (user or agent)
        parts: List of message parts (text, file, data)
        created_at: Timestamp when message was created
    """

    id: str = Field(..., min_length=1, max_length=255)
    role: str = Field(..., pattern="^(user|agent)$")
    parts: list[MessagePart]
    created_at: datetime

    @field_validator("parts")
    @classmethod
    def validate_parts_not_empty(cls, value: list[MessagePart]) -> list[MessagePart]:
        """Validate that parts list is not empty.

        Args:
            value: The parts list to validate

        Returns:
            The validated parts list

        Raises:
            ValueError: If parts list is empty
        """
        if not value:
            raise ValueError("Message must have at least one part")
        return value


class TaskError(BaseModel):
    """Error information for failed tasks.

    Attributes:
        code: Machine-readable error code
        message: Human-readable error message
        details: Optional additional error details
    """

    code: str = Field(..., min_length=1, max_length=100)
    message: str = Field(..., min_length=1, max_length=1000)
    details: Optional[dict[str, str]] = None


class Task(BaseModel):
    """A task in the agent-to-agent system.

    Attributes:
        id: Unique identifier for the task
        agent_id: ID of the agent handling this task
        state: Current state of the task
        messages: Conversation history for this task
        artifacts: List of artifacts produced by the agent
        error: Error information if task failed
        created_at: Timestamp when task was created
        updated_at: Timestamp of last update
        tenant_id: Multi-tenancy identifier
        user_id: ID of the user who created the task
        parent_task_id: Optional ID of parent task for subtasks
    """

    id: str = Field(..., min_length=1, max_length=255)
    agent_id: str = Field(..., min_length=1, max_length=255)
    state: TaskState
    messages: list[TaskMessage] = Field(default_factory=list)
    artifacts: list[Artifact] = Field(default_factory=list)
    error: Optional[TaskError] = None
    created_at: datetime
    updated_at: datetime
    tenant_id: Optional[str] = Field(None, max_length=255)
    user_id: str = Field(..., min_length=1, max_length=255)
    parent_task_id: Optional[str] = Field(None, max_length=255)

    @field_validator("state")
    @classmethod
    def validate_state_error_consistency(cls, value: TaskState, info: Any) -> TaskState:
        """Validate that failed state has error and others don't.

        Args:
            value: The state to validate
            info: Validation context containing other field values

        Returns:
            The validated state

        Raises:
            ValueError: If failed state lacks error or non-failed state has error
        """
        if hasattr(info, "data"):
            error = info.data.get("error")
            if value == TaskState.FAILED and error is None:
                raise ValueError("Failed task must have error information")
            if value != TaskState.FAILED and error is not None:
                raise ValueError("Only failed tasks can have error information")
        return value

    def can_transition_to(self, new_state: TaskState) -> bool:
        """Check if task can transition to the given state.

        Args:
            new_state: The target state to transition to

        Returns:
            True if transition is allowed, False otherwise
        """
        if self.state.is_terminal():
            return False

        valid_transitions = {
            TaskState.SUBMITTED: {
                TaskState.WORKING,
                TaskState.REJECTED,
                TaskState.CANCELLED,
            },
            TaskState.WORKING: {
                TaskState.INPUT_REQUIRED,
                TaskState.AUTH_REQUIRED,
                TaskState.COMPLETED,
                TaskState.FAILED,
                TaskState.CANCELLED,
            },
            TaskState.INPUT_REQUIRED: {TaskState.WORKING, TaskState.CANCELLED},
            TaskState.AUTH_REQUIRED: {TaskState.WORKING, TaskState.CANCELLED},
        }

        return new_state in valid_transitions.get(self.state, set())


class TaskCreateRequest(BaseModel):
    """Request model for creating a new task.

    Attributes:
        message_parts: Initial message parts from the user
        tenant_id: Multi-tenancy identifier
        user_id: ID of the user creating the task
        parent_task_id: Optional ID of parent task for subtasks

    Note:
        agent_id is passed as a path parameter, not in the request body
    """

    message_parts: list[MessagePart]
    tenant_id: str = Field(..., min_length=1, max_length=255)
    user_id: str = Field(..., min_length=1, max_length=255)
    parent_task_id: Optional[str] = Field(None, max_length=255)

    @field_validator("message_parts")
    @classmethod
    def validate_message_parts_not_empty(cls, value: list[MessagePart]) -> list[MessagePart]:
        """Validate that message_parts list is not empty.

        Args:
            value: The message_parts list to validate

        Returns:
            The validated message_parts list

        Raises:
            ValueError: If message_parts list is empty
        """
        if not value:
            raise ValueError("Task must have at least one message part")
        return value


class TaskSendRequest(BaseModel):
    """Request model for sending a message to an existing task.

    Attributes:
        message_parts: Message parts to send to the task
    """

    message_parts: list[MessagePart]

    @field_validator("message_parts")
    @classmethod
    def validate_message_parts_not_empty(cls, value: list[MessagePart]) -> list[MessagePart]:
        """Validate that message_parts list is not empty.

        Args:
            value: The message_parts list to validate

        Returns:
            The validated message_parts list

        Raises:
            ValueError: If message_parts list is empty
        """
        if not value:
            raise ValueError("Message must have at least one part")
        return value


class ChatRequest(BaseModel):
    """Simplified request model for chat-style interactions.

    This is a simplified alternative to TaskCreateRequest that accepts
    a simple text message string instead of message_parts.

    Attributes:
        message: The text message to send to the agent
        tenant_id: Optional multi-tenancy identifier
        user_id: Optional ID of the user (defaults to "default-user")
        stream: Whether to stream response via SSE (default True)
    """

    message: str = Field(..., min_length=1, max_length=10000)
    tenant_id: Optional[str] = Field(None, max_length=255)
    user_id: str = Field(default="default-user", min_length=1, max_length=255)
    stream: bool = Field(default=True)


class ChatResponse(BaseModel):
    """Response model for non-streaming chat interactions.

    Attributes:
        task_id: ID of the created task
        response: The agent's text response
        state: Final state of the task
    """

    task_id: str
    response: str
    state: str
