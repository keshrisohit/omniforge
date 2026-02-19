"""SSE (Server-Sent Events) formatting utilities for chat streaming.

This module provides utilities for formatting streaming events according to
the SSE protocol specification. It includes formatters for chunk events,
done events, error events, and error handling for async streams.
"""

import json
from typing import Any, AsyncIterator

from omniforge.chat.errors import ChatError
from omniforge.chat.models import ChunkEvent, DoneEvent, ErrorEvent


def format_sse_event(event_type: str, data: Any) -> str:
    """Format a Server-Sent Event (SSE) with the given type and data.

    Args:
        event_type: The SSE event type (e.g., "chunk", "done", "error")
        data: The event data to be serialized. Always JSON-serialized to ensure
            proper formatting.

    Returns:
        Formatted SSE string in the format: "event: {type}\ndata: {json}\n\n"

    Examples:
        >>> format_sse_event("message", {"text": "hello"})
        'event: message\\ndata: {"text": "hello"}\\n\\n'

        >>> format_sse_event("status", "connected")
        'event: status\\ndata: "connected"\\n\\n'
    """
    # Always JSON-serialize data for consistent formatting
    data_json = json.dumps(data)
    return f"event: {event_type}\ndata: {data_json}\n\n"


def format_chunk_event(content: str) -> str:
    """Format a chunk event for streaming response content.

    Args:
        content: The partial response content chunk to send

    Returns:
        Formatted SSE event with type "chunk"

    Examples:
        >>> format_chunk_event("Hello, ")
        'event: chunk\\ndata: {"content": "Hello, "}\\n\\n'
    """
    chunk = ChunkEvent(content=content)
    return format_sse_event("chunk", chunk.model_dump())


def format_done_event(done_event: DoneEvent) -> str:
    """Format a done event indicating stream completion.

    Args:
        done_event: The DoneEvent containing conversation_id and usage info

    Returns:
        Formatted SSE event with type "done"

    Examples:
        >>> from uuid import UUID
        >>> from omniforge.chat.models import UsageInfo
        >>> done = DoneEvent(
        ...     conversation_id=UUID('12345678-1234-5678-1234-567812345678'),
        ...     usage=UsageInfo(tokens=42)
        ... )
        >>> event = format_done_event(done)
        >>> 'event: done' in event
        True
    """
    # Use mode="json" to ensure UUID is serialized to string
    return format_sse_event("done", done_event.model_dump(mode="json"))


def format_error_event(error_event: ErrorEvent) -> str:
    """Format an error event for streaming error conditions.

    Args:
        error_event: The ErrorEvent containing error code and message

    Returns:
        Formatted SSE event with type "error"

    Examples:
        >>> error = ErrorEvent(code="validation_error", message="Invalid input")
        >>> event = format_error_event(error)
        >>> 'event: error' in event
        True
        >>> '"code": "validation_error"' in event
        True
    """
    return format_sse_event("error", error_event.model_dump())


async def stream_with_error_handling(stream: AsyncIterator[str]) -> AsyncIterator[str]:
    """Wrap an async stream with error handling.

    This function catches exceptions during stream iteration and yields
    an error event instead of propagating the exception. This ensures
    that streaming clients receive proper error notifications via SSE.

    Args:
        stream: The async iterator to wrap with error handling

    Yields:
        SSE-formatted strings from the original stream, or an error event
        if an exception occurs

    Examples:
        >>> async def failing_stream():
        ...     yield "data1"
        ...     raise ValueError("Something went wrong")
        ...
        >>> async for event in stream_with_error_handling(failing_stream()):
        ...     print(event)  # Will receive error event after "data1"
    """
    try:
        async for item in stream:
            yield item
    except ChatError as e:
        # Convert ChatError to ErrorEvent
        error_event = ErrorEvent(code=e.code, message=e.message)
        yield format_error_event(error_event)
    except Exception as e:
        # Convert unexpected errors to generic internal error
        error_event = ErrorEvent(code="internal_error", message=str(e))
        yield format_error_event(error_event)
