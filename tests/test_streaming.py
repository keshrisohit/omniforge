"""Tests for chat streaming utilities."""

from uuid import UUID

import pytest

from omniforge.chat.errors import InternalError, ValidationError
from omniforge.chat.models import DoneEvent, ErrorEvent, UsageInfo
from omniforge.chat.streaming import (
    format_chunk_event,
    format_done_event,
    format_error_event,
    format_sse_event,
    stream_with_error_handling,
)


class TestFormatSSEEvent:
    """Tests for format_sse_event function."""

    def test_format_sse_event_with_dict(self) -> None:
        """Should format SSE event with dictionary data."""
        result = format_sse_event("test", {"key": "value"})
        assert result == 'event: test\ndata: {"key": "value"}\n\n'

    def test_format_sse_event_with_string(self) -> None:
        """Should format SSE event with string data."""
        result = format_sse_event("message", "hello")
        assert result == 'event: message\ndata: "hello"\n\n'

    def test_format_sse_event_with_list(self) -> None:
        """Should format SSE event with list data."""
        result = format_sse_event("items", [1, 2, 3])
        assert result == "event: items\ndata: [1, 2, 3]\n\n"


class TestFormatChunkEvent:
    """Tests for format_chunk_event function."""

    def test_format_chunk_event_with_text(self) -> None:
        """Should format chunk event with content."""
        result = format_chunk_event("Hello, world!")
        assert "event: chunk\n" in result
        assert '"content": "Hello, world!"' in result
        assert result.endswith("\n\n")

    def test_format_chunk_event_with_empty_string(self) -> None:
        """Should format chunk event even with empty content."""
        result = format_chunk_event("")
        assert "event: chunk\n" in result
        assert '"content": ""' in result

    def test_format_chunk_event_with_special_chars(self) -> None:
        """Should properly escape special characters in JSON."""
        result = format_chunk_event('Line 1\nLine 2\t"quoted"')
        assert "event: chunk\n" in result
        # JSON should escape the newline and tab
        assert r"\n" in result
        assert r"\t" in result


class TestFormatDoneEvent:
    """Tests for format_done_event function."""

    def test_format_done_event_serializes_uuid(self) -> None:
        """Should serialize UUID to string in JSON."""
        conversation_id = UUID("12345678-1234-5678-1234-567812345678")
        usage = UsageInfo(tokens=42)
        done = DoneEvent(conversation_id=conversation_id, usage=usage)

        result = format_done_event(done)

        assert "event: done\n" in result
        assert '"conversation_id": "12345678-1234-5678-1234-567812345678"' in result
        assert '"tokens": 42' in result

    def test_format_done_event_includes_usage_info(self) -> None:
        """Should include usage information in done event."""
        conversation_id = UUID("12345678-1234-5678-1234-567812345678")
        usage = UsageInfo(tokens=100)
        done = DoneEvent(conversation_id=conversation_id, usage=usage)

        result = format_done_event(done)

        assert '"usage"' in result
        assert '"tokens": 100' in result


class TestFormatErrorEvent:
    """Tests for format_error_event function."""

    def test_format_error_event_includes_code_and_message(self) -> None:
        """Should format error event with code and message."""
        error = ErrorEvent(code="validation_error", message="Invalid input")

        result = format_error_event(error)

        assert "event: error\n" in result
        assert '"code": "validation_error"' in result
        assert '"message": "Invalid input"' in result

    def test_format_error_event_with_internal_error(self) -> None:
        """Should format internal error event."""
        error = ErrorEvent(code="internal_error", message="Something went wrong")

        result = format_error_event(error)

        assert "event: error\n" in result
        assert '"code": "internal_error"' in result
        assert '"message": "Something went wrong"' in result


class TestStreamWithErrorHandling:
    """Tests for stream_with_error_handling function."""

    @pytest.mark.asyncio
    async def test_stream_yields_items_from_successful_stream(self) -> None:
        """Should yield all items from successful stream."""

        async def successful_stream():
            yield "item1"
            yield "item2"
            yield "item3"

        items = []
        async for item in stream_with_error_handling(successful_stream()):
            items.append(item)

        assert items == ["item1", "item2", "item3"]

    @pytest.mark.asyncio
    async def test_stream_yields_error_event_on_chat_error(self) -> None:
        """Should convert ChatError to error event."""

        async def failing_stream():
            yield "item1"
            raise ValidationError("Invalid data")

        items = []
        async for item in stream_with_error_handling(failing_stream()):
            items.append(item)

        assert items[0] == "item1"
        assert "event: error\n" in items[1]
        assert '"code": "validation_error"' in items[1]
        assert '"message": "Invalid data"' in items[1]

    @pytest.mark.asyncio
    async def test_stream_yields_error_event_on_internal_error(self) -> None:
        """Should convert InternalError to error event."""

        async def failing_stream():
            yield "item1"
            raise InternalError("System failure")

        items = []
        async for item in stream_with_error_handling(failing_stream()):
            items.append(item)

        assert items[0] == "item1"
        assert "event: error\n" in items[1]
        assert '"code": "internal_error"' in items[1]
        assert '"message": "System failure"' in items[1]

    @pytest.mark.asyncio
    async def test_stream_handles_unexpected_exceptions(self) -> None:
        """Should convert unexpected exceptions to internal error event."""

        async def failing_stream():
            yield "item1"
            raise ValueError("Unexpected error")

        items = []
        async for item in stream_with_error_handling(failing_stream()):
            items.append(item)

        assert items[0] == "item1"
        assert "event: error\n" in items[1]
        assert '"code": "internal_error"' in items[1]
        assert '"message": "Unexpected error"' in items[1]

    @pytest.mark.asyncio
    async def test_stream_handles_empty_stream(self) -> None:
        """Should handle empty stream without errors."""

        async def empty_stream():
            return
            yield  # Make it an async generator

        items = []
        async for item in stream_with_error_handling(empty_stream()):
            items.append(item)

        assert items == []
