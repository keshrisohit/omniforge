"""Handoff manager for transferring conversation control between agents.

This module provides the HandoffManager class for coordinating conversation
control transfer between agents, with state persistence in the conversation
state_metadata JSON column.
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from omniforge.agents.models import AgentCard
from omniforge.conversation.sqlite_repository import SQLiteConversationRepository
from omniforge.orchestration.a2a_models import (
    CompletionStatus,
    HandoffAccept,
    HandoffError,
    HandoffReturn,
)
from omniforge.orchestration.client import A2AClient

logger = logging.getLogger("omniforge.orchestration")


class HandoffState(str, Enum):
    """State of a handoff session.

    Tracks the lifecycle of a conversation handoff from initiation
    through completion or cancellation.
    """

    PENDING = "pending"
    ACTIVE = "active"
    RETURNING = "returning"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ERROR = "error"


class HandoffSession(BaseModel):
    """Session data for a conversation handoff.

    Tracks all information about an active or completed handoff session,
    including participants, state, timing, and results.

    Attributes:
        handoff_id: Unique identifier for this handoff session
        thread_id: Conversation thread identifier
        tenant_id: Tenant identifier for multi-tenancy isolation
        user_id: User identifier who owns the conversation
        source_agent_id: ID of agent initiating the handoff
        target_agent_id: ID of agent receiving control
        state: Current state of the handoff
        context_summary: Brief summary of conversation context
        handoff_reason: Reason for the handoff
        started_at: Timestamp when handoff was initiated
        completed_at: Timestamp when handoff completed (if finished)
        result_summary: Summary of what was accomplished (if completed)
        artifacts_created: List of artifact IDs created during handoff
        workflow_state: Optional workflow state data
        workflow_metadata: Optional workflow-specific metadata
    """

    handoff_id: str = Field(default_factory=lambda: str(uuid4()))
    thread_id: str = Field(..., min_length=1, max_length=255)
    tenant_id: str = Field(..., min_length=1, max_length=255)
    user_id: str = Field(..., min_length=1, max_length=255)
    source_agent_id: str = Field(..., min_length=1, max_length=255)
    target_agent_id: str = Field(..., min_length=1, max_length=255)
    state: HandoffState = HandoffState.PENDING
    context_summary: str = Field(..., min_length=1, max_length=2000)
    handoff_reason: str = Field(..., min_length=1, max_length=500)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    result_summary: Optional[str] = Field(None, max_length=2000)
    artifacts_created: list[str] = Field(default_factory=list)
    workflow_state: Optional[str] = None
    workflow_metadata: Optional[Dict[str, Any]] = None


class HandoffManager:
    """Manager for handoff operations between agents.

    Coordinates conversation control transfer between agents with state
    persistence in the conversation database. Maintains an in-memory cache
    for fast lookups while using the database as source of truth.

    Phase 1 Implementation: Auto-accepts handoffs without HTTP negotiation.

    Attributes:
        _a2a_client: Client for agent-to-agent communication
        _conversation_repo: Repository for conversation persistence
        _active_handoffs: In-memory cache of active handoff sessions
    """

    def __init__(
        self, a2a_client: A2AClient, conversation_repo: SQLiteConversationRepository
    ) -> None:
        """Initialize the handoff manager.

        Args:
            a2a_client: Client for agent-to-agent communication
            conversation_repo: Repository for conversation persistence
        """
        self._a2a_client = a2a_client
        self._conversation_repo = conversation_repo
        self._active_handoffs: dict[str, HandoffSession] = {}

    async def initiate_handoff(
        self,
        thread_id: str,
        tenant_id: str,
        user_id: str,
        source_agent_id: str,
        target_agent_card: AgentCard,
        context_summary: str,
        handoff_reason: str,
    ) -> HandoffAccept:
        """Initiate a handoff to a specialized agent.

        Phase 1: Auto-accepts handoffs without HTTP negotiation.

        Args:
            thread_id: Conversation thread identifier
            tenant_id: Tenant identifier for validation
            user_id: User identifier who owns the conversation
            source_agent_id: ID of agent initiating handoff
            target_agent_card: Agent card of target agent
            context_summary: Brief summary of conversation context
            handoff_reason: Reason for the handoff

        Returns:
            HandoffAccept indicating acceptance

        Raises:
            HandoffError: If active handoff already exists for this thread
            ValueError: If conversation not found or tenant_id invalid
        """
        # Validate inputs
        if not thread_id or not thread_id.strip():
            raise ValueError("thread_id cannot be empty")
        if not tenant_id or not tenant_id.strip():
            raise ValueError("tenant_id cannot be empty")
        if not user_id or not user_id.strip():
            raise ValueError("user_id cannot be empty")
        if not source_agent_id or not source_agent_id.strip():
            raise ValueError("source_agent_id cannot be empty")
        if not context_summary or not context_summary.strip():
            raise ValueError("context_summary cannot be empty")
        if not handoff_reason or not handoff_reason.strip():
            raise ValueError("handoff_reason cannot be empty")

        # Check for existing active handoff
        existing = await self.get_active_handoff(thread_id, tenant_id)
        if existing is not None:
            raise HandoffError(
                f"Active handoff already exists for thread {thread_id} "
                f"(handoff_id: {existing.handoff_id}, state: {existing.state})"
            )

        # Create new handoff session with ACTIVE state (Phase 1: auto-accept)
        session = HandoffSession(
            thread_id=thread_id,
            tenant_id=tenant_id,
            user_id=user_id,
            source_agent_id=source_agent_id,
            target_agent_id=target_agent_card.identity.id,
            state=HandoffState.ACTIVE,
            context_summary=context_summary,
            handoff_reason=handoff_reason,
            result_summary=None,
        )

        # Log handoff initiation
        logger.info(
            "Handoff initiated",
            extra={
                "thread_id": thread_id,
                "tenant_id": tenant_id,
                "source_agent": source_agent_id,
                "target_agent": target_agent_card.identity.id,
                "reason": handoff_reason,
                "handoff_id": session.handoff_id,
            },
        )

        # Persist to database
        await self._persist_handoff_session(session)

        # Cache in memory
        self._active_handoffs[thread_id] = session

        # Return acceptance (Phase 1: always accept)
        return HandoffAccept(
            thread_id=thread_id,
            source_agent_id=source_agent_id,
            target_agent_id=target_agent_card.identity.id,
            accepted=True,
            rejection_reason=None,
            estimated_duration_seconds=None,
        )

    async def get_active_handoff(self, thread_id: str, tenant_id: str) -> Optional[HandoffSession]:
        """Get active handoff session for a thread.

        Checks in-memory cache first, then loads from database if needed.
        Only returns sessions in ACTIVE state.

        Args:
            thread_id: Conversation thread identifier
            tenant_id: Tenant identifier for validation

        Returns:
            Active HandoffSession if exists, None otherwise

        Raises:
            ValueError: If tenant_id is invalid
        """
        if not tenant_id or not tenant_id.strip():
            raise ValueError("tenant_id cannot be empty")
        if not thread_id or not thread_id.strip():
            raise ValueError("thread_id cannot be empty")

        # Check cache first
        if thread_id in self._active_handoffs:
            session = self._active_handoffs[thread_id]
            # Validate tenant_id matches
            if session.tenant_id != tenant_id:
                raise ValueError(f"Thread {thread_id} does not belong to tenant {tenant_id}")
            if session.state == HandoffState.ACTIVE:
                return session
            # Remove from cache if not active
            del self._active_handoffs[thread_id]
            return None

        # Load from database
        conversation_id = UUID(thread_id)
        conversation = await self._conversation_repo.get_conversation(conversation_id, tenant_id)

        if conversation is None:
            return None

        # Extract handoff session from state_metadata
        if (
            conversation.state_metadata is None
            or "handoff_session" not in conversation.state_metadata
        ):
            return None

        session_data = conversation.state_metadata["handoff_session"]
        session = HandoffSession(**session_data)

        # Only return and cache if state is ACTIVE
        if session.state == HandoffState.ACTIVE:
            self._active_handoffs[thread_id] = session
            return session

        return None

    async def complete_handoff(
        self,
        thread_id: str,
        tenant_id: str,
        completion_status: CompletionStatus,
        result_summary: Optional[str] = None,
        artifacts: Optional[list[str]] = None,
    ) -> HandoffReturn:
        """Complete an active handoff and return control.

        Updates handoff state to terminal state (COMPLETED, CANCELLED, or ERROR)
        and removes from in-memory cache.

        Args:
            thread_id: Conversation thread identifier
            tenant_id: Tenant identifier for validation
            completion_status: Status of completion (completed/cancelled/error)
            result_summary: Optional summary of what was accomplished
            artifacts: Optional list of artifact IDs created

        Returns:
            HandoffReturn object with completion details

        Raises:
            HandoffError: If no active handoff exists
            ValueError: If tenant_id is invalid
        """
        # Get active session
        session = await self.get_active_handoff(thread_id, tenant_id)
        if session is None:
            raise HandoffError(f"No active handoff found for thread {thread_id}")

        # Map completion status to handoff state
        state_map = {
            CompletionStatus.COMPLETED: HandoffState.COMPLETED,
            CompletionStatus.CANCELLED: HandoffState.CANCELLED,
            CompletionStatus.ERROR: HandoffState.ERROR,
        }

        # Calculate duration
        duration_seconds = (datetime.utcnow() - session.started_at).total_seconds()

        # Update session
        session.state = state_map[completion_status]
        session.completed_at = datetime.utcnow()
        if result_summary is not None:
            session.result_summary = result_summary
        if artifacts is not None:
            session.artifacts_created = artifacts

        # Log handoff completion
        if completion_status == CompletionStatus.COMPLETED:
            logger.info(
                "Handoff completed",
                extra={
                    "thread_id": thread_id,
                    "tenant_id": tenant_id,
                    "handoff_id": session.handoff_id,
                    "completion_status": completion_status.value,
                    "duration_seconds": duration_seconds,
                },
            )
        elif completion_status == CompletionStatus.CANCELLED:
            logger.info(
                "Handoff cancelled",
                extra={
                    "thread_id": thread_id,
                    "tenant_id": tenant_id,
                    "handoff_id": session.handoff_id,
                    "duration_seconds": duration_seconds,
                },
            )
        else:
            logger.warning(
                "Handoff error",
                extra={
                    "thread_id": thread_id,
                    "tenant_id": tenant_id,
                    "handoff_id": session.handoff_id,
                    "error_summary": result_summary,
                    "duration_seconds": duration_seconds,
                },
            )

        # Persist updated state
        await self._persist_handoff_session(session)

        # Remove from cache
        if thread_id in self._active_handoffs:
            del self._active_handoffs[thread_id]

        # Return handoff return message
        return HandoffReturn(
            thread_id=thread_id,
            tenant_id=tenant_id,
            source_agent_id=session.target_agent_id,
            target_agent_id=session.source_agent_id,
            completion_status=completion_status,
            result_summary=result_summary,
            artifacts_created=artifacts or [],
        )

    async def cancel_handoff(self, thread_id: str, tenant_id: str) -> HandoffReturn:
        """Cancel an active handoff.

        Convenience method that calls complete_handoff with CANCELLED status.

        Args:
            thread_id: Conversation thread identifier
            tenant_id: Tenant identifier for validation

        Returns:
            HandoffReturn object with cancellation details

        Raises:
            HandoffError: If no active handoff exists
            ValueError: If tenant_id is invalid
        """
        return await self.complete_handoff(
            thread_id=thread_id,
            tenant_id=tenant_id,
            completion_status=CompletionStatus.CANCELLED,
            result_summary="Handoff cancelled",
        )

    async def _persist_handoff_session(self, session: HandoffSession) -> None:
        """Persist handoff session to database state_metadata.

        Loads conversation, updates state_metadata["handoff_session"],
        and saves back to database.

        Args:
            session: HandoffSession to persist

        Raises:
            ValueError: If conversation not found or tenant_id invalid
        """
        conversation_id = UUID(session.thread_id)

        # Load current conversation
        conversation = await self._conversation_repo.get_conversation(
            conversation_id, session.tenant_id
        )

        if conversation is None:
            raise ValueError(
                f"Conversation {session.thread_id} not found or does not belong to tenant"
            )

        # Update state_metadata with handoff session
        state_metadata = conversation.state_metadata or {}
        state_metadata["handoff_session"] = session.model_dump(mode="json")

        # Persist to database
        await self._conversation_repo.update_state(
            conversation_id=conversation_id,
            tenant_id=session.tenant_id,
            state=conversation.state or "active",  # Preserve existing state
            state_metadata=state_metadata,
        )
