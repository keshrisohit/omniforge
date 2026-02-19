"""A2A protocol models for orchestration and handoff patterns.

This module defines Pydantic models for orchestration and handoff protocol messages,
error types, and agent card capability extensions.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# Error Classes
class OrchestrationError(Exception):
    """Base exception for orchestration-related errors."""

    pass


class HandoffError(OrchestrationError):
    """Exception raised during handoff operations."""

    pass


class DelegationError(OrchestrationError):
    """Exception raised during task delegation operations."""

    pass


# Handoff Protocol Models
class HandoffRequest(BaseModel):
    """Request to hand off conversation control to another agent.

    Attributes:
        thread_id: Unique identifier for the conversation thread
        tenant_id: Tenant identifier for multi-tenancy isolation
        user_id: User identifier who initiated the conversation
        source_agent_id: ID of the agent initiating the handoff
        target_agent_id: ID of the agent receiving control
        context_summary: Brief summary of conversation context
        recent_message_count: Number of recent messages to include (1-20)
        handoff_reason: Reason for the handoff
        preserve_state: Whether to preserve conversation state
        return_expected: Whether the source agent expects control to return
        handoff_metadata: Optional additional metadata for handoff
    """

    thread_id: str = Field(..., min_length=1, max_length=255)
    tenant_id: str = Field(..., min_length=1, max_length=255)
    user_id: str = Field(..., min_length=1, max_length=255)
    source_agent_id: str = Field(..., min_length=1, max_length=255)
    target_agent_id: str = Field(..., min_length=1, max_length=255)
    context_summary: str = Field(..., min_length=1, max_length=2000)
    recent_message_count: int = Field(default=5, ge=1, le=20)
    handoff_reason: str = Field(..., min_length=1, max_length=500)
    preserve_state: bool = True
    return_expected: bool = True
    handoff_metadata: Optional[dict] = None


class HandoffAccept(BaseModel):
    """Acknowledgment of handoff acceptance or rejection.

    Attributes:
        thread_id: Unique identifier for the conversation thread
        source_agent_id: ID of the agent that initiated the handoff
        target_agent_id: ID of the agent that received the handoff request
        accepted: Whether the handoff was accepted
        rejection_reason: Optional reason if handoff was rejected
        estimated_duration_seconds: Optional estimated duration of handoff session
    """

    thread_id: str = Field(..., min_length=1, max_length=255)
    source_agent_id: str = Field(..., min_length=1, max_length=255)
    target_agent_id: str = Field(..., min_length=1, max_length=255)
    accepted: bool
    rejection_reason: Optional[str] = Field(None, max_length=500)
    estimated_duration_seconds: Optional[int] = Field(None, ge=0)


class CompletionStatus(str, Enum):
    """Status of handoff completion."""

    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ERROR = "error"


class HandoffReturn(BaseModel):
    """Signal to return control from specialized agent to source agent.

    Attributes:
        thread_id: Unique identifier for the conversation thread
        tenant_id: Tenant identifier for multi-tenancy isolation
        source_agent_id: ID of the agent returning control
        target_agent_id: ID of the agent receiving control back
        completion_status: Status of the handoff completion
        result_summary: Optional summary of what was accomplished
        artifacts_created: List of artifact IDs created during handoff
    """

    thread_id: str = Field(..., min_length=1, max_length=255)
    tenant_id: str = Field(..., min_length=1, max_length=255)
    source_agent_id: str = Field(..., min_length=1, max_length=255)
    target_agent_id: str = Field(..., min_length=1, max_length=255)
    completion_status: CompletionStatus
    result_summary: Optional[str] = Field(None, max_length=2000)
    artifacts_created: list[str] = Field(default_factory=list)

    @field_validator("artifacts_created")
    @classmethod
    def validate_artifact_ids(cls, value: list[str]) -> list[str]:
        """Validate artifact IDs are non-empty strings.

        Args:
            value: List of artifact IDs to validate

        Returns:
            The validated list of artifact IDs

        Raises:
            ValueError: If any artifact ID is empty
        """
        for artifact_id in value:
            if not artifact_id or not artifact_id.strip():
                raise ValueError("Artifact IDs must be non-empty strings")
        return value
