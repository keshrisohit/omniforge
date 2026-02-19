"""Tests for SSE streaming utilities.

This module tests the Server-Sent Events (SSE) formatting functions
used for streaming chat responses to clients.
"""

import json
from uuid import uuid4

from omniforge.chat.models import DoneEvent, ErrorEvent, UsageInfo
from omniforge.chat.streaming import (
    format_chunk_event,
    format_done_event,
    format_error_event,
    format_sse_event,
)


class TestFormatSSEEvent:
    """Tests for format_sse_event function."""

    def test_format_sse_event(self) -> None:
        """format_sse_event should return correct SSE format."""
        result = format_sse_event("test_type", {"key": "value"})

        # Verify format: "event: {type}\ndata: {json}\n\n"
        assert result.startswith("event: test_type\n")
        assert "data: " in result
        assert result.endswith("\n\n")

        # Verify data is JSON-serialized
        lines = result.split("\n")
        data_line = [line for line in lines if line.startswith("data: ")][0]
        data_json = data_line.replace("data: ", "")
        parsed_data = json.loads(data_json)
        assert parsed_data == {"key": "value"}

    def test_format_sse_event_with_string_data(self) -> None:
        """format_sse_event should JSON-serialize string data."""
        result = format_sse_event("message", "hello")
        assert "event: message\n" in result
        assert 'data: "hello"\n\n' in result


class TestFormatChunkEvent:
    """Tests for format_chunk_event function."""

    def test_format_chunk_event(self) -> None:
        """format_chunk_event should contain 'event: chunk' and content."""
        content = "Hello, world!"
        result = format_chunk_event(content)

        # Verify event type is "chunk"
        assert "event: chunk\n" in result

        # Verify content is present in the data
        assert content in result

        # Verify it ends with SSE terminator
        assert result.endswith("\n\n")

        # Verify data is properly JSON-formatted
        lines = result.split("\n")
        data_line = [line for line in lines if line.startswith("data: ")][0]
        data_json = data_line.replace("data: ", "")
        parsed_data = json.loads(data_json)
        assert parsed_data["content"] == content


class TestFormatDoneEvent:
    """Tests for format_done_event function."""

    def test_format_done_event(self) -> None:
        """format_done_event should contain conversation_id and tokens."""
        conversation_id = uuid4()
        usage = UsageInfo(tokens=150)
        done_event = DoneEvent(conversation_id=conversation_id, usage=usage)

        result = format_done_event(done_event)

        # Verify event type is "done"
        assert "event: done\n" in result

        # Verify it ends with SSE terminator
        assert result.endswith("\n\n")

        # Verify data contains conversation_id and tokens
        lines = result.split("\n")
        data_line = [line for line in lines if line.startswith("data: ")][0]
        data_json = data_line.replace("data: ", "")
        parsed_data = json.loads(data_json)

        assert parsed_data["conversation_id"] == str(conversation_id)
        assert parsed_data["usage"]["tokens"] == 150


class TestFormatErrorEvent:
    """Tests for format_error_event function."""

    def test_format_error_event(self) -> None:
        """format_error_event should contain code and message."""
        error_event = ErrorEvent(code="validation_error", message="Invalid input data")

        result = format_error_event(error_event)

        # Verify event type is "error"
        assert "event: error\n" in result

        # Verify it ends with SSE terminator
        assert result.endswith("\n\n")

        # Verify data contains code and message
        lines = result.split("\n")
        data_line = [line for line in lines if line.startswith("data: ")][0]
        data_json = data_line.replace("data: ", "")
        parsed_data = json.loads(data_json)

        assert parsed_data["code"] == "validation_error"
        assert parsed_data["message"] == "Invalid input data"
