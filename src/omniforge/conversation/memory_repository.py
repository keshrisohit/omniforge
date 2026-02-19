"""In-memory implementation of ConversationRepository.

Provides thread-safe, dictionary-based storage for conversations and messages,
suitable for development and testing.
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from omniforge.conversation.models import Conversation, Message, MessageRole


class InMemoryConversationRepository:
    """Thread-safe in-memory implementation of ConversationRepository.

    Uses dictionaries for storage with asyncio locks for thread safety.
    Enforces tenant isolation just like the SQLite implementation.

    Attributes:
        _conversations: Dictionary mapping conversation_id to Conversation objects
        _messages: Dictionary mapping conversation_id to list of Message objects
        _lock: Asyncio lock for thread-safe operations
    """

    def __init__(self) -> None:
        """Initialize the in-memory conversation repository."""
        self._conversations: Dict[UUID, Conversation] = {}
        self._messages: Dict[UUID, List[Message]] = {}
        self._lock = asyncio.Lock()

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
        if not tenant_id or not tenant_id.strip():
            raise ValueError("tenant_id cannot be empty")
        if not user_id or not user_id.strip():
            raise ValueError("user_id cannot be empty")

        async with self._lock:
            conversation = Conversation(
                id=uuid4(),
                tenant_id=tenant_id,
                user_id=user_id,
                title=title,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                metadata=None,
            )

            self._conversations[conversation.id] = conversation
            self._messages[conversation.id] = []

            return conversation

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
        if not tenant_id or not tenant_id.strip():
            raise ValueError("tenant_id cannot be empty")

        async with self._lock:
            conversation = self._conversations.get(conversation_id)

            # Enforce tenant isolation
            if conversation is None or conversation.tenant_id != tenant_id:
                return None

            return conversation

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
        if not tenant_id or not tenant_id.strip():
            raise ValueError("tenant_id cannot be empty")

        async with self._lock:
            # Filter by tenant_id
            filtered = [c for c in self._conversations.values() if c.tenant_id == tenant_id]

            # Additional user_id filter if provided
            if user_id:
                filtered = [c for c in filtered if c.user_id == user_id]

            # Sort by updated_at DESC (most recent first)
            filtered.sort(key=lambda c: c.updated_at, reverse=True)

            # Apply pagination
            return filtered[offset : offset + limit]

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
        if not tenant_id or not tenant_id.strip():
            raise ValueError("tenant_id cannot be empty")

        async with self._lock:
            conversation = self._conversations.get(conversation_id)

            # Enforce tenant isolation
            if conversation is None or conversation.tenant_id != tenant_id:
                return None

            # Create updated conversation (Pydantic models are immutable)
            updated = conversation.model_copy(
                update={
                    "title": title if title is not None else conversation.title,
                    "updated_at": datetime.utcnow(),
                }
            )

            self._conversations[conversation_id] = updated
            return updated

    async def add_message(
        self,
        conversation_id: UUID,
        tenant_id: str,
        role: MessageRole,
        content: str,
    ) -> Message:
        """Add a message to a conversation.

        Atomically updates conversation.updated_at when adding the message.

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
        if not tenant_id or not tenant_id.strip():
            raise ValueError("tenant_id cannot be empty")
        if not content or not content.strip():
            raise ValueError("content cannot be empty")

        async with self._lock:
            conversation = self._conversations.get(conversation_id)

            # Enforce tenant isolation
            if conversation is None or conversation.tenant_id != tenant_id:
                raise ValueError(
                    f"Conversation {conversation_id} not found or does not belong to tenant"
                )

            # Create message
            message = Message(
                id=uuid4(),
                conversation_id=conversation_id,
                role=role,
                content=content,
                created_at=datetime.utcnow(),
                metadata=None,
            )

            # Add to messages list
            if conversation_id not in self._messages:
                self._messages[conversation_id] = []
            self._messages[conversation_id].append(message)

            # Atomically update conversation.updated_at
            updated_conversation = conversation.model_copy(
                update={
                    "updated_at": datetime.utcnow(),
                }
            )
            self._conversations[conversation_id] = updated_conversation

            return message

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
        if not tenant_id or not tenant_id.strip():
            raise ValueError("tenant_id cannot be empty")

        async with self._lock:
            conversation = self._conversations.get(conversation_id)

            # Enforce tenant isolation
            if conversation is None or conversation.tenant_id != tenant_id:
                raise ValueError(
                    f"Conversation {conversation_id} not found or does not belong to tenant"
                )

            # Get messages (already in chronological order)
            messages = self._messages.get(conversation_id, [])

            # Apply pagination (always return copy to avoid mutation)
            if limit is not None:
                return list(messages[offset : offset + limit])
            else:
                return list(messages[offset:])

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
        if not tenant_id or not tenant_id.strip():
            raise ValueError("tenant_id cannot be empty")

        async with self._lock:
            conversation = self._conversations.get(conversation_id)

            # Enforce tenant isolation
            if conversation is None or conversation.tenant_id != tenant_id:
                raise ValueError(
                    f"Conversation {conversation_id} not found or does not belong to tenant"
                )

            # Get all messages
            messages = self._messages.get(conversation_id, [])

            # Return last N messages (always return a copy to avoid mutation)
            # Use slicing even when len <= count to create a new list
            return messages[-count:] if count < len(messages) else list(messages)
