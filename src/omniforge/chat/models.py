"""Pydantic models for chat requests and responses.

This module defines the data models for chat interactions, including
requests, streaming events, and response payloads.
"""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from omniforge.chat.errors import ValidationError


class ChatRequest(BaseModel):
    """Request model for chat interactions.

    Attributes:
        message: User's chat message (1-10000 characters)
        conversation_id: Optional UUID for continuing an existing conversation
    """

    message: str = Field(..., min_length=1, max_length=10000)
    conversation_id: Optional[UUID] = None

    @field_validator("message")
    @classmethod
    def validate_message_not_whitespace(cls, value: str) -> str:
        """Validate that message is not only whitespace.

        Args:
            value: The message string to validate

        Returns:
            The validated message string

        Raises:
            ValidationError: If message contains only whitespace
        """
        if not value.strip():
            raise ValidationError("Message cannot be empty or contain only whitespace")
        return value


class ChunkEvent(BaseModel):
    """Streaming event containing a content chunk.

    Used for server-sent events (SSE) when streaming chat responses.

    Attributes:
        content: Partial response content chunk
    """

    content: str


class UsageInfo(BaseModel):
    """Information about token usage for a chat interaction.

    Attributes:
        tokens: Total number of tokens consumed
    """

    tokens: int


class DoneEvent(BaseModel):
    """Final event in a streaming response indicating completion.

    Attributes:
        conversation_id: UUID of the conversation
        usage: Token usage information for the interaction
    """

    conversation_id: UUID
    usage: UsageInfo


class ErrorEvent(BaseModel):
    """Event indicating an error occurred during processing.

    Attributes:
        code: Machine-readable error code
        message: Human-readable error description
    """

    code: str
    message: str
