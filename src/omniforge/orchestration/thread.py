"""Thread lifecycle management and context retrieval for orchestration.

This module provides security-critical thread validation and context management
for agent orchestration and handoff operations.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from omniforge.conversation.models import Message, MessageRole
from omniforge.conversation.sqlite_repository import SQLiteConversationRepository


class ThreadContext(BaseModel):
    """Thread context information for orchestration.

    Contains metadata about a conversation thread including handoff state.

    Attributes:
        thread_id: Unique thread identifier
        tenant_id: Tenant this thread belongs to
        user_id: User who owns this thread
        created_at: Thread creation timestamp
        updated_at: Thread last update timestamp
        current_active_agent: Currently active agent handling the thread
        is_handoff_active: Whether a handoff is in progress
        handoff_target_agent: Target agent for active handoff (if any)
        total_messages: Total number of messages in the thread
    """

    thread_id: UUID
    tenant_id: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    current_active_agent: str
    is_handoff_active: bool = Field(default=False)
    handoff_target_agent: Optional[str] = None
    total_messages: int


class ThreadManager:
    """Thread lifecycle manager for orchestration operations.

    Security-critical component that validates thread ownership and retrieves
    thread context before any orchestration or handoff operation.

    Attributes:
        conversation_repo: Repository for conversation persistence
    """

    def __init__(self, conversation_repo: SQLiteConversationRepository):
        """Initialize ThreadManager with conversation repository.

        Args:
            conversation_repo: SQLite conversation repository instance
        """
        self.conversation_repo = conversation_repo

    async def validate_thread(
        self,
        thread_id: str,
        tenant_id: str,
        user_id: Optional[str] = None,
    ) -> bool:
        """Validate thread belongs to tenant and optionally to user.

        Security critical: Prevents cross-tenant access and unauthorized operations.
        Never raises exceptions - returns False on any error.

        Args:
            thread_id: Thread ID to validate
            tenant_id: Tenant ID for validation
            user_id: Optional user ID for ownership validation

        Returns:
            True if thread is valid and belongs to tenant (and user if specified),
            False otherwise (not found, wrong tenant, invalid UUID, or exception)
        """
        try:
            # Convert thread_id string to UUID
            thread_uuid = UUID(thread_id)
        except (ValueError, AttributeError):
            # Invalid UUID format
            return False

        try:
            # Get conversation with tenant validation
            conversation = await self.conversation_repo.get_conversation(
                conversation_id=thread_uuid,
                tenant_id=tenant_id,
            )

            # Not found or wrong tenant
            if conversation is None:
                return False

            # If user_id provided, validate ownership
            if user_id is not None and conversation.user_id != user_id:
                return False

            return True

        except Exception:
            # Any exception means validation failed
            return False

    async def get_recent_messages(
        self,
        thread_id: str,
        tenant_id: str,
        count: int = 10,
        include_system: bool = False,
    ) -> list[Message]:
        """Get recent messages from a thread.

        Retrieves the most recent messages using the conversation repository,
        with optional system message filtering.

        Args:
            thread_id: Thread ID to get messages from
            tenant_id: Tenant ID for validation
            count: Number of recent messages to return (default: 10)
            include_system: Whether to include system messages (default: False)

        Returns:
            List of recent messages in chronological order

        Raises:
            ValueError: If thread_id is invalid UUID, tenant_id is invalid,
                       or conversation not found
        """
        # Convert thread_id to UUID
        try:
            thread_uuid = UUID(thread_id)
        except (ValueError, AttributeError) as e:
            raise ValueError(f"Invalid thread_id format: {thread_id}") from e

        # Get recent messages from repository
        messages = await self.conversation_repo.get_recent_messages(
            conversation_id=thread_uuid,
            tenant_id=tenant_id,
            count=count,
        )

        # Filter out system messages unless include_system=True
        if not include_system:
            messages = [msg for msg in messages if msg.role != MessageRole.SYSTEM]

        return messages

    async def get_thread_context(
        self,
        thread_id: str,
        tenant_id: str,
    ) -> ThreadContext:
        """Get thread context metadata.

        Retrieves thread metadata from the conversation record, including
        handoff state from state_metadata if present.

        Args:
            thread_id: Thread ID to get context for
            tenant_id: Tenant ID for validation

        Returns:
            ThreadContext with thread metadata

        Raises:
            ValueError: If thread_id is invalid UUID, tenant_id is invalid,
                       or conversation not found
        """
        # Convert thread_id to UUID
        try:
            thread_uuid = UUID(thread_id)
        except (ValueError, AttributeError) as e:
            raise ValueError(f"Invalid thread_id format: {thread_id}") from e

        # Get conversation with tenant validation
        conversation = await self.conversation_repo.get_conversation(
            conversation_id=thread_uuid,
            tenant_id=tenant_id,
        )

        if conversation is None:
            raise ValueError(f"Conversation {thread_id} not found or does not belong to tenant")

        # Get all messages to count total
        all_messages = await self.conversation_repo.get_messages(
            conversation_id=thread_uuid,
            tenant_id=tenant_id,
        )
        total_messages = len(all_messages)

        # Extract handoff state from state_metadata
        state_metadata = conversation.state_metadata or {}
        current_active_agent = state_metadata.get("current_active_agent", "default")
        is_handoff_active = state_metadata.get("is_handoff_active", False)
        handoff_target_agent = state_metadata.get("handoff_target_agent")

        # Build ThreadContext
        return ThreadContext(
            thread_id=conversation.id,
            tenant_id=conversation.tenant_id,
            user_id=conversation.user_id,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            current_active_agent=current_active_agent,
            is_handoff_active=is_handoff_active,
            handoff_target_agent=handoff_target_agent,
            total_messages=total_messages,
        )
