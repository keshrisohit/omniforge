"""Tests for chat Pydantic models."""

from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError as PydanticValidationError

from omniforge.chat.errors import ValidationError
from omniforge.chat.models import (
    ChatRequest,
    ChunkEvent,
    DoneEvent,
    ErrorEvent,
    UsageInfo,
)


class TestChatRequest:
    """Tests for ChatRequest model."""

    def test_create_chat_request_with_valid_message(self) -> None:
        """ChatRequest should initialize with valid message."""
        # Arrange & Act
        request = ChatRequest(message="Hello, world!")

        # Assert
        assert request.message == "Hello, world!"
        assert request.conversation_id is None

    def test_create_chat_request_with_conversation_id(self) -> None:
        """ChatRequest should accept optional conversation_id."""
        # Arrange
        conv_id = uuid4()

        # Act
        request = ChatRequest(message="Follow-up message", conversation_id=conv_id)

        # Assert
        assert request.message == "Follow-up message"
        assert request.conversation_id == conv_id

    def test_create_chat_request_with_minimum_length_message(self) -> None:
        """ChatRequest should accept message with 1 character."""
        request = ChatRequest(message="x")
        assert request.message == "x"

    def test_create_chat_request_with_maximum_length_message(self) -> None:
        """ChatRequest should accept message with 10000 characters."""
        long_message = "x" * 10000
        request = ChatRequest(message=long_message)
        assert len(request.message) == 10000

    def test_create_chat_request_with_empty_message_raises_error(self) -> None:
        """ChatRequest should reject empty message."""
        with pytest.raises(PydanticValidationError) as exc_info:
            ChatRequest(message="")

        errors = exc_info.value.errors()
        assert any(
            error["type"] == "string_too_short" for error in errors
        ), "Should raise string_too_short error"

    def test_create_chat_request_with_too_long_message_raises_error(self) -> None:
        """ChatRequest should reject message exceeding 10000 characters."""
        too_long_message = "x" * 10001

        with pytest.raises(PydanticValidationError) as exc_info:
            ChatRequest(message=too_long_message)

        errors = exc_info.value.errors()
        assert any(
            error["type"] == "string_too_long" for error in errors
        ), "Should raise string_too_long error"

    def test_create_chat_request_with_whitespace_only_message_raises_error(self) -> None:
        """ChatRequest should reject message containing only whitespace."""
        with pytest.raises(ValidationError, match="only whitespace"):
            ChatRequest(message="   ")

    def test_create_chat_request_with_tabs_and_spaces_raises_error(self) -> None:
        """ChatRequest should reject message with only tabs and spaces."""
        with pytest.raises(ValidationError, match="only whitespace"):
            ChatRequest(message="\t  \n  ")

    def test_create_chat_request_with_newlines_only_raises_error(self) -> None:
        """ChatRequest should reject message containing only newlines."""
        with pytest.raises(ValidationError, match="only whitespace"):
            ChatRequest(message="\n\n\n")

    def test_create_chat_request_with_message_with_leading_trailing_spaces(
        self,
    ) -> None:
        """ChatRequest should accept message with leading/trailing spaces."""
        request = ChatRequest(message="  Hello  ")
        assert request.message == "  Hello  "

    def test_chat_request_json_serialization(self) -> None:
        """ChatRequest should serialize to JSON correctly."""
        conv_id = UUID("12345678-1234-5678-1234-567812345678")
        request = ChatRequest(message="Test", conversation_id=conv_id)

        json_data = request.model_dump()
        assert json_data == {
            "message": "Test",
            "conversation_id": conv_id,
        }

    def test_chat_request_json_deserialization(self) -> None:
        """ChatRequest should deserialize from JSON correctly."""
        conv_id = UUID("12345678-1234-5678-1234-567812345678")
        data = {
            "message": "Test message",
            "conversation_id": str(conv_id),
        }

        request = ChatRequest.model_validate(data)
        assert request.message == "Test message"
        assert request.conversation_id == conv_id


class TestChunkEvent:
    """Tests for ChunkEvent model."""

    def test_create_chunk_event_with_content(self) -> None:
        """ChunkEvent should initialize with content."""
        # Arrange & Act
        chunk = ChunkEvent(content="This is a chunk")

        # Assert
        assert chunk.content == "This is a chunk"

    def test_create_chunk_event_with_empty_content(self) -> None:
        """ChunkEvent should accept empty content."""
        chunk = ChunkEvent(content="")
        assert chunk.content == ""

    def test_chunk_event_json_serialization(self) -> None:
        """ChunkEvent should serialize to JSON correctly."""
        chunk = ChunkEvent(content="Partial response")

        json_data = chunk.model_dump()
        assert json_data == {"content": "Partial response"}


class TestUsageInfo:
    """Tests for UsageInfo model."""

    def test_create_usage_info_with_tokens(self) -> None:
        """UsageInfo should initialize with token count."""
        # Arrange & Act
        usage = UsageInfo(tokens=150)

        # Assert
        assert usage.tokens == 150

    def test_create_usage_info_with_zero_tokens(self) -> None:
        """UsageInfo should accept zero tokens."""
        usage = UsageInfo(tokens=0)
        assert usage.tokens == 0

    def test_create_usage_info_with_large_token_count(self) -> None:
        """UsageInfo should accept large token counts."""
        usage = UsageInfo(tokens=1000000)
        assert usage.tokens == 1000000

    def test_usage_info_json_serialization(self) -> None:
        """UsageInfo should serialize to JSON correctly."""
        usage = UsageInfo(tokens=250)

        json_data = usage.model_dump()
        assert json_data == {"tokens": 250}


class TestDoneEvent:
    """Tests for DoneEvent model."""

    def test_create_done_event_with_all_fields(self) -> None:
        """DoneEvent should initialize with conversation_id and usage."""
        # Arrange
        conv_id = uuid4()
        usage = UsageInfo(tokens=300)

        # Act
        done = DoneEvent(conversation_id=conv_id, usage=usage)

        # Assert
        assert done.conversation_id == conv_id
        assert done.usage == usage
        assert done.usage.tokens == 300

    def test_done_event_json_serialization(self) -> None:
        """DoneEvent should serialize to JSON correctly."""
        conv_id = UUID("12345678-1234-5678-1234-567812345678")
        usage = UsageInfo(tokens=100)
        done = DoneEvent(conversation_id=conv_id, usage=usage)

        json_data = done.model_dump()
        assert json_data == {
            "conversation_id": conv_id,
            "usage": {"tokens": 100},
        }

    def test_done_event_json_deserialization(self) -> None:
        """DoneEvent should deserialize from JSON correctly."""
        conv_id = UUID("12345678-1234-5678-1234-567812345678")
        data = {
            "conversation_id": str(conv_id),
            "usage": {"tokens": 200},
        }

        done = DoneEvent.model_validate(data)
        assert done.conversation_id == conv_id
        assert done.usage.tokens == 200


class TestErrorEvent:
    """Tests for ErrorEvent model."""

    def test_create_error_event_with_code_and_message(self) -> None:
        """ErrorEvent should initialize with code and message."""
        # Arrange & Act
        error = ErrorEvent(code="validation_error", message="Invalid input")

        # Assert
        assert error.code == "validation_error"
        assert error.message == "Invalid input"

    def test_create_error_event_with_empty_strings(self) -> None:
        """ErrorEvent should accept empty strings."""
        error = ErrorEvent(code="", message="")
        assert error.code == ""
        assert error.message == ""

    def test_error_event_json_serialization(self) -> None:
        """ErrorEvent should serialize to JSON correctly."""
        error = ErrorEvent(code="internal_error", message="Something went wrong")

        json_data = error.model_dump()
        assert json_data == {
            "code": "internal_error",
            "message": "Something went wrong",
        }


class TestModelInteroperability:
    """Tests for interactions between different models."""

    def test_done_event_with_usage_info(self) -> None:
        """DoneEvent should properly compose with UsageInfo."""
        usage = UsageInfo(tokens=500)
        done = DoneEvent(conversation_id=uuid4(), usage=usage)

        assert done.usage.tokens == 500

    def test_error_event_from_chat_error(self) -> None:
        """ErrorEvent should be creatable from ChatError attributes."""
        from omniforge.chat.errors import ValidationError as ChatValidationError

        chat_error = ChatValidationError("Invalid field")
        error_event = ErrorEvent(code=chat_error.code, message=chat_error.message)

        assert error_event.code == "validation_error"
        assert error_event.message == "Invalid field"
