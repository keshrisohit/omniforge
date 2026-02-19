"""SSE streaming utilities for agent task events.

This module provides utilities for converting task events into Server-Sent Events
(SSE) format, reusing the core SSE formatting from chat/streaming.py.
"""

from datetime import datetime
from typing import AsyncIterator

from omniforge.agents.errors import AgentError
from omniforge.agents.events import (
    TaskArtifactEvent,
    TaskDoneEvent,
    TaskErrorEvent,
    TaskEvent,
    TaskMessageEvent,
    TaskStatusEvent,
)
from omniforge.chat.streaming import format_sse_event


def format_task_event(event: TaskEvent) -> str:
    """Format a task event as an SSE event.

    Args:
        event: The task event to format

    Returns:
        Formatted SSE string in the format: "event: {type}\ndata: {json}\n\n"

    Examples:
        >>> from datetime import datetime
        >>> from omniforge.tasks.models import TaskState
        >>> event = TaskStatusEvent(
        ...     task_id="task-123",
        ...     timestamp=datetime.now(),
        ...     state=TaskState.WORKING,
        ...     message="Processing request"
        ... )
        >>> sse = format_task_event(event)
        >>> 'event: status' in sse
        True
        >>> '"state": "working"' in sse
        True
    """
    # Use mode="json" to ensure datetime and enums are serialized properly
    event_data = event.model_dump(mode="json")
    return format_sse_event(event.type, event_data)


def format_status_event(event: TaskStatusEvent) -> str:
    """Format a task status event.

    Args:
        event: The status event to format

    Returns:
        Formatted SSE event with type "status"

    Examples:
        >>> from datetime import datetime
        >>> from omniforge.tasks.models import TaskState
        >>> event = TaskStatusEvent(
        ...     task_id="task-123",
        ...     timestamp=datetime.now(),
        ...     state=TaskState.WORKING
        ... )
        >>> sse = format_status_event(event)
        >>> 'event: status' in sse
        True
    """
    return format_task_event(event)


def format_message_event(event: TaskMessageEvent) -> str:
    """Format a task message event.

    Args:
        event: The message event to format

    Returns:
        Formatted SSE event with type "message"

    Examples:
        >>> from datetime import datetime
        >>> from omniforge.agents.models import TextPart
        >>> event = TaskMessageEvent(
        ...     task_id="task-123",
        ...     timestamp=datetime.now(),
        ...     message_parts=[TextPart(text="Hello")],
        ...     is_partial=True
        ... )
        >>> sse = format_message_event(event)
        >>> 'event: message' in sse
        True
    """
    return format_task_event(event)


def format_artifact_event(event: TaskArtifactEvent) -> str:
    """Format a task artifact event.

    Args:
        event: The artifact event to format

    Returns:
        Formatted SSE event with type "artifact"

    Examples:
        >>> from datetime import datetime
        >>> from omniforge.agents.models import Artifact
        >>> artifact = Artifact(
        ...     id="art-1",
        ...     type="document",
        ...     title="Result",
        ...     content="data"
        ... )
        >>> event = TaskArtifactEvent(
        ...     task_id="task-123",
        ...     timestamp=datetime.now(),
        ...     artifact=artifact
        ... )
        >>> sse = format_artifact_event(event)
        >>> 'event: artifact' in sse
        True
    """
    return format_task_event(event)


def format_done_event(event: TaskDoneEvent) -> str:
    """Format a task done event.

    Args:
        event: The done event to format

    Returns:
        Formatted SSE event with type "done"

    Examples:
        >>> from datetime import datetime
        >>> from omniforge.tasks.models import TaskState
        >>> event = TaskDoneEvent(
        ...     task_id="task-123",
        ...     timestamp=datetime.now(),
        ...     final_state=TaskState.COMPLETED
        ... )
        >>> sse = format_done_event(event)
        >>> 'event: done' in sse
        True
    """
    return format_task_event(event)


def format_error_event(event: TaskErrorEvent) -> str:
    """Format a task error event.

    Args:
        event: The error event to format

    Returns:
        Formatted SSE event with type "error"

    Examples:
        >>> from datetime import datetime
        >>> event = TaskErrorEvent(
        ...     task_id="task-123",
        ...     timestamp=datetime.now(),
        ...     error_code="validation_error",
        ...     error_message="Invalid input"
        ... )
        >>> sse = format_error_event(event)
        >>> 'event: error' in sse
        True
        >>> '"error_code": "validation_error"' in sse
        True
    """
    return format_task_event(event)


async def stream_task_events(events: AsyncIterator[TaskEvent]) -> AsyncIterator[str]:
    """Convert a stream of task events into SSE-formatted strings.

    Args:
        events: Async iterator of task events

    Yields:
        SSE-formatted strings for each event

    Examples:
        >>> async def event_stream():
        ...     from datetime import datetime
        ...     from omniforge.tasks.models import TaskState
        ...     yield TaskStatusEvent(
        ...         task_id="task-123",
        ...         timestamp=datetime.now(),
        ...         state=TaskState.WORKING
        ...     )
        ...
        >>> async for sse_event in stream_task_events(event_stream()):
        ...     print(sse_event)  # Prints SSE-formatted event
    """
    async for event in events:
        yield format_task_event(event)


async def stream_task_with_error_handling(
    events: AsyncIterator[TaskEvent], task_id: str
) -> AsyncIterator[str]:
    """Wrap a task event stream with error handling.

    This function catches exceptions during stream iteration and yields
    a TaskErrorEvent instead of propagating the exception. This ensures
    that streaming clients receive proper error notifications via SSE.

    Args:
        events: The async iterator of task events to wrap
        task_id: The ID of the task being streamed

    Yields:
        SSE-formatted strings from the original stream, or an error event
        if an exception occurs

    Examples:
        >>> async def failing_stream():
        ...     from datetime import datetime
        ...     from omniforge.tasks.models import TaskState
        ...     yield TaskStatusEvent(
        ...         task_id="task-123",
        ...         timestamp=datetime.now(),
        ...         state=TaskState.WORKING
        ...     )
        ...     raise ValueError("Something went wrong")
        ...
        >>> async for event in stream_task_with_error_handling(
        ...     failing_stream(), "task-123"
        ... ):
        ...     print(event)  # Will receive error event after status event
    """
    try:
        async for event in events:
            yield format_task_event(event)
    except AgentError as e:
        # Convert AgentError to TaskErrorEvent
        error_event = TaskErrorEvent(
            task_id=task_id,
            timestamp=datetime.utcnow(),
            error_code=e.code,
            error_message=e.message,
        )
        yield format_error_event(error_event)
    except Exception as e:
        # Convert unexpected errors to generic error event
        error_event = TaskErrorEvent(
            task_id=task_id,
            timestamp=datetime.utcnow(),
            error_code="internal_error",
            error_message=str(e),
        )
        yield format_error_event(error_event)
