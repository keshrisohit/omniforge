"""Pydantic schemas for conversation API requests and responses.

This module defines data models for conversation endpoints used in
the conversational agent builder flow.
"""

from typing import Optional

from pydantic import BaseModel, Field


class ConversationStartResponse(BaseModel):
    """Response for starting a new conversation session.

    Attributes:
        session_id: Unique identifier for the conversation session
        message: Initial greeting message from the assistant
        phase: Current conversation phase (always "discovery" initially)
    """

    session_id: str = Field(..., description="Unique conversation session ID")
    message: str = Field(..., description="Initial assistant greeting message")
    phase: str = Field(default="discovery", description="Current conversation phase")


class ConversationMessageRequest(BaseModel):
    """Request for sending a message in an ongoing conversation.

    Attributes:
        message: User's message content
    """

    message: str = Field(..., min_length=1, max_length=10000, description="User message")


class ConversationMessageResponse(BaseModel):
    """Response streamed during conversation message processing.

    This model represents individual streaming events sent via SSE.

    Attributes:
        text: Assistant's response text
        phase: Current conversation phase
        actions: Available actions user can take
        oauth_url: OAuth authorization URL if integration setup needed
    """

    text: str = Field(..., description="Assistant response text")
    phase: str = Field(..., description="Current conversation phase")
    actions: list[str] = Field(default_factory=list, description="Available actions for user")
    oauth_url: Optional[str] = Field(None, description="OAuth URL if integration setup required")


class ConversationOAuthCompleteRequest(BaseModel):
    """Request to complete OAuth flow and resume conversation.

    Attributes:
        integration: Integration type (e.g., "notion", "slack")
        code: OAuth authorization code from provider
        state: OAuth state parameter for CSRF protection
    """

    integration: str = Field(
        ..., min_length=1, max_length=50, description="Integration type identifier"
    )
    code: str = Field(..., min_length=1, description="OAuth authorization code")
    state: str = Field(..., min_length=1, description="OAuth state parameter")


class ConversationOAuthCompleteResponse(BaseModel):
    """Response after completing OAuth flow.

    Attributes:
        success: Whether OAuth flow completed successfully
        workspace_name: Name of connected workspace/account
        message: Next step message from assistant
    """

    success: bool = Field(..., description="OAuth completion status")
    workspace_name: Optional[str] = Field(None, description="Connected workspace/account name")
    message: str = Field(..., description="Next step guidance message")
