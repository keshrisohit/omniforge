"""Custom exceptions for chat module.

This module defines the exception hierarchy for chat-related errors,
providing structured error handling with status codes and error codes.
"""


class ChatError(Exception):
    """Base exception for all chat-related errors.

    Attributes:
        code: Machine-readable error code
        message: Human-readable error message
        status_code: HTTP status code for API responses
    """

    def __init__(self, message: str, code: str, status_code: int) -> None:
        """Initialize chat error.

        Args:
            message: Human-readable error description
            code: Machine-readable error code
            status_code: HTTP status code (400, 500, etc.)
        """
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class ValidationError(ChatError):
    """Raised when input validation fails.

    This error indicates that the request data did not pass validation rules.
    """

    def __init__(self, message: str) -> None:
        """Initialize validation error.

        Args:
            message: Description of the validation failure
        """
        super().__init__(message=message, code="validation_error", status_code=400)


class MessageTooLongError(ChatError):
    """Raised when a message exceeds the maximum allowed length.

    This error indicates that the message content is too long to process.
    """

    def __init__(self, message: str) -> None:
        """Initialize message too long error.

        Args:
            message: Description of the length violation
        """
        super().__init__(message=message, code="message_too_long", status_code=400)


class InternalError(ChatError):
    """Raised when an internal server error occurs.

    This error indicates an unexpected failure in the system that is not
    the client's fault.
    """

    def __init__(self, message: str) -> None:
        """Initialize internal error.

        Args:
            message: Description of the internal failure
        """
        super().__init__(message=message, code="internal_error", status_code=500)
