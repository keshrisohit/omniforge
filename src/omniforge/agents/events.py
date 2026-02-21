"""Task event models for streaming agent responses.

This module defines event types for streaming task updates from agents,
including status changes, messages, artifacts, completion, and errors.
"""

from datetime import datetime
from typing import Any, Literal, Optional, Union

from pydantic import BaseModel, Field

from omniforge.agents.models import Artifact, MessagePart
from omniforge.tasks.models import TaskState
from omniforge.tools.types import VisibilityLevel


class BaseTaskEvent(BaseModel):
    """Base class for all task events.

    Attributes:
        task_id: ID of the task this event belongs to
        timestamp: When the event occurred
        trace_id: Trace ID propagated across the full delegation chain
    """

    task_id: str = Field(..., min_length=1, max_length=255)
    timestamp: datetime
    trace_id: Optional[str] = None


class TaskStatusEvent(BaseTaskEvent):
    """Event for task state transitions.

    Attributes:
        type: Event type discriminator (always "status")
        task_id: ID of the task
        timestamp: When the event occurred
        state: New state of the task
        message: Optional human-readable status message
        visibility: Visibility level for this event (FULL/SUMMARY/HIDDEN)
    """

    type: Literal["status"] = "status"
    state: TaskState
    message: Optional[str] = None
    visibility: VisibilityLevel = VisibilityLevel.SUMMARY


class TaskMessageEvent(BaseTaskEvent):
    """Event for agent messages (partial or complete).

    Attributes:
        type: Event type discriminator (always "message")
        task_id: ID of the task
        timestamp: When the event occurred
        message_parts: List of message parts in this event
        is_partial: Whether this is a partial message (streaming)
        visibility: Visibility level for this event (FULL/SUMMARY/HIDDEN)
    """

    type: Literal["message"] = "message"
    message_parts: list[MessagePart]
    is_partial: bool = False
    visibility: VisibilityLevel = VisibilityLevel.SUMMARY


class TaskArtifactEvent(BaseTaskEvent):
    """Event for artifact delivery.

    Attributes:
        type: Event type discriminator (always "artifact")
        task_id: ID of the task
        timestamp: When the event occurred
        artifact: The artifact being delivered
    """

    type: Literal["artifact"] = "artifact"
    artifact: Artifact


class TaskDoneEvent(BaseTaskEvent):
    """Event for task completion.

    Attributes:
        type: Event type discriminator (always "done")
        task_id: ID of the task
        timestamp: When the event occurred
        final_state: Final state of the task (completed/failed/cancelled)
    """

    type: Literal["done"] = "done"
    final_state: TaskState

    def __init__(self, **data: Any) -> None:
        """Initialize TaskDoneEvent and validate final state.

        Args:
            **data: Event data

        Raises:
            ValueError: If final_state is not a terminal state
        """
        super().__init__(**data)
        if not self.final_state.is_terminal():
            raise ValueError(f"Done event requires terminal state, got {self.final_state}")


class TaskErrorEvent(BaseTaskEvent):
    """Event for error reporting.

    Attributes:
        type: Event type discriminator (always "error")
        task_id: ID of the task
        timestamp: When the event occurred
        error_code: Machine-readable error code
        error_message: Human-readable error message
        details: Optional additional error details
        visibility: Visibility level for this event (FULL/SUMMARY/HIDDEN)
    """

    type: Literal["error"] = "error"
    error_code: str = Field(..., min_length=1, max_length=100)
    error_message: str = Field(..., min_length=1, max_length=1000)
    details: Optional[dict[str, str]] = None
    visibility: VisibilityLevel = VisibilityLevel.SUMMARY


# Union type for all task events (enables type discrimination)
TaskEvent = Union[
    TaskStatusEvent,
    TaskMessageEvent,
    TaskArtifactEvent,
    TaskDoneEvent,
    TaskErrorEvent,
]
