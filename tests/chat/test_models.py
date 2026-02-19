"""Tests for chat request and response models.

This module tests the Pydantic models used for chat interactions,
including validation logic for ChatRequest.
"""

from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError as PydanticValidationError

from omniforge.chat.errors import ValidationError
from omniforge.chat.models import ChatRequest, ChunkEvent, DoneEvent, ErrorEvent, UsageInfo


class TestChatRequest:
    """Tests for ChatRequest model validation."""

    def test_valid_message(self) -> None:
        """ChatRequest should accept a valid message."""
        request = ChatRequest(message="Hello, how are you?")
        assert request.message == "Hello, how are you?"
        assert request.conversation_id is None

    def test_empty_message_rejected(self) -> None:
        """ChatRequest should raise ValidationError for empty string."""
        with pytest.raises(PydanticValidationError) as exc_info:
            ChatRequest(message="")

        # Verify it's caught by pydantic's min_length validation
        errors = exc_info.value.errors()
        assert len(errors) > 0
        assert any(
            error["type"] == "string_too_short" for error in errors
        ), "Expected string_too_short validation error"

    def test_whitespace_message_rejected(self) -> None:
        """ChatRequest should raise ValidationError for whitespace-only message."""
        with pytest.raises(
            ValidationError, match="Message cannot be empty or contain only whitespace"
        ):
            ChatRequest(message="   ")

    def test_max_length_enforced(self) -> None:
        """ChatRequest should raise ValidationError for messages exceeding 10000 characters."""
        long_message = "a" * 10001
        with pytest.raises(PydanticValidationError) as exc_info:
            ChatRequest(message=long_message)

        # Verify it's caught by pydantic's max_length validation
        errors = exc_info.value.errors()
        assert len(errors) > 0
        assert any(
            error["type"] == "string_too_long" for error in errors
        ), "Expected string_too_long validation error"

    def test_optional_conversation_id(self) -> None:
        """ChatRequest conversation_id should default to None."""
        request = ChatRequest(message="Test message")
        assert request.conversation_id is None

    def test_valid_conversation_id(self) -> None:
        """ChatRequest should accept a valid UUID as conversation_id."""
        conversation_id = uuid4()
        request = ChatRequest(message="Test message", conversation_id=conversation_id)
        assert request.conversation_id == conversation_id
        assert isinstance(request.conversation_id, UUID)


class TestChunkEvent:
    """Tests for ChunkEvent model."""

    def test_chunk_event_creation(self) -> None:
        """ChunkEvent should accept content string."""
        event = ChunkEvent(content="Hello, ")
        assert event.content == "Hello, "


class TestDoneEvent:
    """Tests for DoneEvent model."""

    def test_done_event_creation(self) -> None:
        """DoneEvent should accept conversation_id and usage."""
        conversation_id = uuid4()
        usage = UsageInfo(tokens=42)
        event = DoneEvent(conversation_id=conversation_id, usage=usage)
        assert event.conversation_id == conversation_id
        assert event.usage.tokens == 42


class TestErrorEvent:
    """Tests for ErrorEvent model."""

    def test_error_event_creation(self) -> None:
        """ErrorEvent should accept code and message."""
        event = ErrorEvent(code="validation_error", message="Invalid input")
        assert event.code == "validation_error"
        assert event.message == "Invalid input"
