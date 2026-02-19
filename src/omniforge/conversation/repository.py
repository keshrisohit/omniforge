"""Conversation repository interface.

Defines the Protocol (abstract interface) for conversation persistence
operations with tenant isolation enforced.
"""

from typing import List, Optional, Protocol
from uuid import UUID

from omniforge.conversation.models import Conversation, Message, MessageRole


class ConversationRepository(Protocol):
    """Repository interface for conversation persistence operations.

    This Protocol defines the contract for conversation storage implementations.
    All read operations MUST include tenant_id for security and multi-tenancy.

    Implementations must enforce tenant isolation to prevent cross-tenant
    data access.
    """

    async def create_conversation(
        self,
        tenant_id: str,
        user_id: str,
        title: Optional[str] = None,
    ) -> Conversation:
        """Create a new conversation.

        Args:
            tenant_id: Tenant identifier for multi-tenancy isolation
            user_id: User who owns this conversation
            title: Optional human-readable title

        Returns:
            Created Conversation instance

        Raises:
            ValueError: If tenant_id or user_id is invalid
        """
        ...

    async def get_conversation(
        self,
        conversation_id: UUID,
        tenant_id: str,
    ) -> Optional[Conversation]:
        """Get a conversation by ID with tenant validation.

        Security critical: MUST validate tenant_id to prevent
        unauthorized cross-tenant access.

        Args:
            conversation_id: Unique conversation identifier
            tenant_id: Tenant ID for validation

        Returns:
            Conversation if found and belongs to tenant, None otherwise

        Raises:
            ValueError: If tenant_id is invalid
        """
        ...

    async def list_conversations(
        self,
        tenant_id: str,
        user_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Conversation]:
        """List conversations with tenant filtering.

        Security critical: MUST filter by tenant_id to prevent
        unauthorized cross-tenant access.

        Args:
            tenant_id: Tenant ID for filtering (required)
            user_id: Optional user ID for additional filtering
            limit: Maximum number of results (default: 50)
            offset: Pagination offset (default: 0)

        Returns:
            List of conversations for the tenant (and optionally user)

        Raises:
            ValueError: If tenant_id is invalid
        """
        ...

    async def update_conversation(
        self,
        conversation_id: UUID,
        tenant_id: str,
        title: Optional[str] = None,
    ) -> Optional[Conversation]:
        """Update conversation metadata.

        Args:
            conversation_id: Unique conversation identifier
            tenant_id: Tenant ID for validation
            title: New title (optional)

        Returns:
            Updated Conversation if found and belongs to tenant, None otherwise

        Raises:
            ValueError: If tenant_id is invalid
        """
        ...

    async def add_message(
        self,
        conversation_id: UUID,
        tenant_id: str,
        role: MessageRole,
        content: str,
    ) -> Message:
        """Add a message to a conversation.

        Args:
            conversation_id: Conversation to add message to
            tenant_id: Tenant ID for validation
            role: Message role (user, assistant, system)
            content: Message text content

        Returns:
            Created Message instance

        Raises:
            ValueError: If conversation not found or tenant_id invalid
        """
        ...

    async def get_messages(
        self,
        conversation_id: UUID,
        tenant_id: str,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[Message]:
        """Get all messages in a conversation with tenant validation.

        Security critical: MUST validate tenant_id to prevent
        unauthorized cross-tenant access.

        Args:
            conversation_id: Conversation to get messages from
            tenant_id: Tenant ID for validation (required)
            limit: Optional maximum number of messages
            offset: Pagination offset (default: 0)

        Returns:
            List of messages in chronological order

        Raises:
            ValueError: If tenant_id is invalid or conversation not found
        """
        ...

    async def get_recent_messages(
        self,
        conversation_id: UUID,
        tenant_id: str,
        count: int = 10,
    ) -> List[Message]:
        """Get the most recent messages from a conversation.

        Security critical: MUST validate tenant_id to prevent
        unauthorized cross-tenant access.

        Args:
            conversation_id: Conversation to get messages from
            tenant_id: Tenant ID for validation (required)
            count: Number of recent messages to return (default: 10)

        Returns:
            List of most recent messages in chronological order

        Raises:
            ValueError: If tenant_id is invalid or conversation not found
        """
        ...
