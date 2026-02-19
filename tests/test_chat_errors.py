"""Tests for chat error classes."""

import pytest

from omniforge.chat.errors import (
    ChatError,
    InternalError,
    MessageTooLongError,
    ValidationError,
)


class TestChatError:
    """Tests for base ChatError class."""

    def test_create_chat_error_with_all_attributes(self) -> None:
        """ChatError should store message, code, and status_code."""
        # Arrange & Act
        error = ChatError(message="Test error", code="test_code", status_code=418)

        # Assert
        assert error.message == "Test error"
        assert error.code == "test_code"
        assert error.status_code == 418
        assert str(error) == "Test error"

    def test_chat_error_is_exception(self) -> None:
        """ChatError should be an Exception subclass."""
        error = ChatError(message="Test", code="test", status_code=500)
        assert isinstance(error, Exception)


class TestValidationError:
    """Tests for ValidationError class."""

    def test_create_validation_error_sets_correct_defaults(self) -> None:
        """ValidationError should have validation_error code and 400 status."""
        # Arrange & Act
        error = ValidationError(message="Invalid input")

        # Assert
        assert error.message == "Invalid input"
        assert error.code == "validation_error"
        assert error.status_code == 400

    def test_validation_error_is_chat_error(self) -> None:
        """ValidationError should be a ChatError subclass."""
        error = ValidationError(message="Test")
        assert isinstance(error, ChatError)

    def test_validation_error_can_be_raised(self) -> None:
        """ValidationError should be raisable and catchable."""
        with pytest.raises(ValidationError, match="Invalid data"):
            raise ValidationError("Invalid data")


class TestMessageTooLongError:
    """Tests for MessageTooLongError class."""

    def test_create_message_too_long_error_sets_correct_defaults(self) -> None:
        """MessageTooLongError should have message_too_long code and 400 status."""
        # Arrange & Act
        error = MessageTooLongError(message="Message exceeds limit")

        # Assert
        assert error.message == "Message exceeds limit"
        assert error.code == "message_too_long"
        assert error.status_code == 400

    def test_message_too_long_error_is_chat_error(self) -> None:
        """MessageTooLongError should be a ChatError subclass."""
        error = MessageTooLongError(message="Test")
        assert isinstance(error, ChatError)

    def test_message_too_long_error_can_be_raised(self) -> None:
        """MessageTooLongError should be raisable and catchable."""
        with pytest.raises(MessageTooLongError, match="Too long"):
            raise MessageTooLongError("Too long")


class TestInternalError:
    """Tests for InternalError class."""

    def test_create_internal_error_sets_correct_defaults(self) -> None:
        """InternalError should have internal_error code and 500 status."""
        # Arrange & Act
        error = InternalError(message="Something went wrong")

        # Assert
        assert error.message == "Something went wrong"
        assert error.code == "internal_error"
        assert error.status_code == 500

    def test_internal_error_is_chat_error(self) -> None:
        """InternalError should be a ChatError subclass."""
        error = InternalError(message="Test")
        assert isinstance(error, ChatError)

    def test_internal_error_can_be_raised(self) -> None:
        """InternalError should be raisable and catchable."""
        with pytest.raises(InternalError, match="Server failure"):
            raise InternalError("Server failure")


class TestErrorHierarchy:
    """Tests for error hierarchy relationships."""

    def test_all_errors_inherit_from_chat_error(self) -> None:
        """All error types should inherit from ChatError."""
        validation_error = ValidationError("test")
        message_error = MessageTooLongError("test")
        internal_error = InternalError("test")

        assert isinstance(validation_error, ChatError)
        assert isinstance(message_error, ChatError)
        assert isinstance(internal_error, ChatError)

    def test_all_errors_inherit_from_exception(self) -> None:
        """All error types should inherit from Exception."""
        validation_error = ValidationError("test")
        message_error = MessageTooLongError("test")
        internal_error = InternalError("test")

        assert isinstance(validation_error, Exception)
        assert isinstance(message_error, Exception)
        assert isinstance(internal_error, Exception)

    def test_errors_can_be_caught_as_chat_error(self) -> None:
        """All specific errors should be catchable as ChatError."""
        with pytest.raises(ChatError):
            raise ValidationError("test")

        with pytest.raises(ChatError):
            raise MessageTooLongError("test")

        with pytest.raises(ChatError):
            raise InternalError("test")
