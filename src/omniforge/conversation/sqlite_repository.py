"""SQLite-backed implementation of ConversationRepository.

Provides persistent conversation storage using SQLAlchemy with
tenant isolation enforcement on all operations.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import desc, select

from omniforge.conversation.models import Conversation, ConversationType, Message, MessageRole
from omniforge.conversation.orm import ConversationMessageModel, ConversationModel
from omniforge.storage.database import Database


class SQLiteConversationRepository:
    """SQLite implementation of ConversationRepository using SQLAlchemy.

    Provides persistent storage for conversations and messages with
    multi-tenant isolation enforced at the database query level.

    Attributes:
        db: Database instance for session management
    """

    def __init__(self, db: Database):
        """Initialize repository with database connection.

        Args:
            db: Database instance for session management
        """
        self.db = db

    async def create_conversation(
        self,
        tenant_id: str,
        user_id: str,
        title: Optional[str] = None,
        conversation_type: ConversationType = ConversationType.CHAT,
        state: Optional[str] = None,
        state_metadata: Optional[Dict[str, Any]] = None,
        conversation_id: Optional[UUID] = None,
    ) -> Conversation:
        """Create a new conversation.

        Args:
            tenant_id: Tenant identifier for multi-tenancy isolation
            user_id: User who owns this conversation
            title: Optional human-readable title
            conversation_type: Type of conversation (default: CHAT)
            state: Optional initial FSM state for stateful conversations
            state_metadata: Optional state-specific metadata
            conversation_id: Optional conversation ID (generates new UUID if None)

        Returns:
            Created Conversation instance

        Raises:
            ValueError: If tenant_id or user_id is invalid
        """
        if not tenant_id or not tenant_id.strip():
            raise ValueError("tenant_id cannot be empty")
        if not user_id or not user_id.strip():
            raise ValueError("user_id cannot be empty")

        async with self.db.session() as session:
            # Create ORM model
            conversation_orm = ConversationModel(
                id=str(conversation_id) if conversation_id else None,
                tenant_id=tenant_id,
                user_id=user_id,
                title=title,
                conversation_type=conversation_type.value,
                state=state,
                state_metadata=state_metadata,
                conversation_metadata=None,
            )

            session.add(conversation_orm)
            await session.flush()
            await session.refresh(conversation_orm)

            # Convert to domain model
            return self._orm_to_conversation(conversation_orm)

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

        async with self.db.session() as session:
            stmt = select(ConversationModel).where(
                ConversationModel.id == str(conversation_id),
                ConversationModel.tenant_id == tenant_id,
            )
            result = await session.execute(stmt)
            conversation_orm = result.scalar_one_or_none()

            if conversation_orm is None:
                return None

            return self._orm_to_conversation(conversation_orm)

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

        async with self.db.session() as session:
            stmt = select(ConversationModel).where(ConversationModel.tenant_id == tenant_id)

            if user_id:
                stmt = stmt.where(ConversationModel.user_id == user_id)

            # Order by updated_at DESC (most recent first)
            stmt = stmt.order_by(desc(ConversationModel.updated_at))
            stmt = stmt.limit(limit).offset(offset)

            result = await session.execute(stmt)
            conversations_orm = result.scalars().all()

            return [self._orm_to_conversation(c) for c in conversations_orm]

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

        async with self.db.session() as session:
            stmt = select(ConversationModel).where(
                ConversationModel.id == str(conversation_id),
                ConversationModel.tenant_id == tenant_id,
            )
            result = await session.execute(stmt)
            conversation_orm = result.scalar_one_or_none()

            if conversation_orm is None:
                return None

            # Update fields
            if title is not None:
                conversation_orm.title = title
            conversation_orm.updated_at = datetime.utcnow()

            await session.flush()
            await session.refresh(conversation_orm)

            return self._orm_to_conversation(conversation_orm)

    async def update_state(
        self,
        conversation_id: UUID,
        tenant_id: str,
        state: str,
        state_metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Conversation]:
        """Update FSM state for a stateful conversation.

        Args:
            conversation_id: Unique conversation identifier
            tenant_id: Tenant ID for validation
            state: New FSM state
            state_metadata: Optional state-specific metadata

        Returns:
            Updated Conversation if found and belongs to tenant, None otherwise

        Raises:
            ValueError: If tenant_id is invalid
        """
        if not tenant_id or not tenant_id.strip():
            raise ValueError("tenant_id cannot be empty")
        if not state or not state.strip():
            raise ValueError("state cannot be empty")

        async with self.db.session() as session:
            stmt = select(ConversationModel).where(
                ConversationModel.id == str(conversation_id),
                ConversationModel.tenant_id == tenant_id,
            )
            result = await session.execute(stmt)
            conversation_orm = result.scalar_one_or_none()

            if conversation_orm is None:
                return None

            # Update state fields
            conversation_orm.state = state
            if state_metadata is not None:
                conversation_orm.state_metadata = state_metadata
            conversation_orm.updated_at = datetime.utcnow()

            await session.flush()
            await session.refresh(conversation_orm)

            return self._orm_to_conversation(conversation_orm)

    async def get_conversations_by_type(
        self,
        tenant_id: str,
        conversation_type: ConversationType,
        user_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Conversation]:
        """Get conversations by type with tenant filtering.

        Security critical: MUST filter by tenant_id to prevent
        unauthorized cross-tenant access.

        Args:
            tenant_id: Tenant ID for filtering (required)
            conversation_type: Type of conversation to filter by
            user_id: Optional user ID for additional filtering
            limit: Maximum number of results (default: 50)
            offset: Pagination offset (default: 0)

        Returns:
            List of conversations of the specified type

        Raises:
            ValueError: If tenant_id is invalid
        """
        if not tenant_id or not tenant_id.strip():
            raise ValueError("tenant_id cannot be empty")

        async with self.db.session() as session:
            stmt = select(ConversationModel).where(
                ConversationModel.tenant_id == tenant_id,
                ConversationModel.conversation_type == conversation_type.value,
            )

            if user_id:
                stmt = stmt.where(ConversationModel.user_id == user_id)

            stmt = stmt.order_by(desc(ConversationModel.updated_at))
            stmt = stmt.limit(limit).offset(offset)

            result = await session.execute(stmt)
            conversations_orm = result.scalars().all()

            return [self._orm_to_conversation(c) for c in conversations_orm]

    async def get_conversations_by_state(
        self,
        tenant_id: str,
        state: str,
        conversation_type: Optional[ConversationType] = None,
        user_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Conversation]:
        """Get conversations by FSM state with tenant filtering.

        Useful for finding conversations in specific workflow states
        (e.g., all skill creation sessions in "gathering_requirements").

        Security critical: MUST filter by tenant_id to prevent
        unauthorized cross-tenant access.

        Args:
            tenant_id: Tenant ID for filtering (required)
            state: FSM state to filter by
            conversation_type: Optional conversation type filter
            user_id: Optional user ID for additional filtering
            limit: Maximum number of results (default: 50)
            offset: Pagination offset (default: 0)

        Returns:
            List of conversations in the specified state

        Raises:
            ValueError: If tenant_id is invalid
        """
        if not tenant_id or not tenant_id.strip():
            raise ValueError("tenant_id cannot be empty")
        if not state or not state.strip():
            raise ValueError("state cannot be empty")

        async with self.db.session() as session:
            stmt = select(ConversationModel).where(
                ConversationModel.tenant_id == tenant_id,
                ConversationModel.state == state,
            )

            if conversation_type:
                stmt = stmt.where(ConversationModel.conversation_type == conversation_type.value)

            if user_id:
                stmt = stmt.where(ConversationModel.user_id == user_id)

            stmt = stmt.order_by(desc(ConversationModel.updated_at))
            stmt = stmt.limit(limit).offset(offset)

            result = await session.execute(stmt)
            conversations_orm = result.scalars().all()

            return [self._orm_to_conversation(c) for c in conversations_orm]

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

        async with self.db.session() as session:
            # Verify conversation exists and belongs to tenant
            stmt = select(ConversationModel).where(
                ConversationModel.id == str(conversation_id),
                ConversationModel.tenant_id == tenant_id,
            )
            result = await session.execute(stmt)
            conversation_orm = result.scalar_one_or_none()

            if conversation_orm is None:
                raise ValueError(
                    f"Conversation {conversation_id} not found or does not belong to tenant"
                )

            # Create message
            message_orm = ConversationMessageModel(
                conversation_id=str(conversation_id),
                role=role.value,
                content=content,
                message_metadata=None,
            )

            session.add(message_orm)

            # Atomically update conversation.updated_at
            conversation_orm.updated_at = datetime.utcnow()

            await session.flush()
            await session.refresh(message_orm)

            return self._orm_to_message(message_orm)

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

        async with self.db.session() as session:
            # Verify conversation exists and belongs to tenant
            conversation = await self.get_conversation(conversation_id, tenant_id)
            if conversation is None:
                raise ValueError(
                    f"Conversation {conversation_id} not found or does not belong to tenant"
                )

            # Fetch messages
            stmt = (
                select(ConversationMessageModel)
                .where(ConversationMessageModel.conversation_id == str(conversation_id))
                .order_by(ConversationMessageModel.created_at)
                .offset(offset)
            )

            if limit is not None:
                stmt = stmt.limit(limit)

            result = await session.execute(stmt)
            messages_orm = result.scalars().all()

            return [self._orm_to_message(m) for m in messages_orm]

    async def get_recent_messages(
        self,
        conversation_id: UUID,
        tenant_id: str,
        count: int = 10,
    ) -> List[Message]:
        """Get the most recent messages from a conversation.

        Fetches messages in DESC order then reverses for chronological output.

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

        async with self.db.session() as session:
            # Verify conversation exists and belongs to tenant
            conversation = await self.get_conversation(conversation_id, tenant_id)
            if conversation is None:
                raise ValueError(
                    f"Conversation {conversation_id} not found or does not belong to tenant"
                )

            # Fetch recent messages in DESC order
            stmt = (
                select(ConversationMessageModel)
                .where(ConversationMessageModel.conversation_id == str(conversation_id))
                .order_by(desc(ConversationMessageModel.created_at))
                .limit(count)
            )

            result = await session.execute(stmt)
            messages_orm = result.scalars().all()

            # Reverse to chronological order
            messages = [self._orm_to_message(m) for m in reversed(messages_orm)]

            return messages

    def _orm_to_conversation(self, orm: ConversationModel) -> Conversation:
        """Convert ORM model to domain model.

        Args:
            orm: SQLAlchemy ConversationModel instance

        Returns:
            Conversation domain model
        """
        # Type ignore needed for SQLAlchemy ORM attribute access
        return Conversation(
            id=UUID(orm.id) if isinstance(orm.id, str) else orm.id,  # type: ignore[arg-type]
            tenant_id=orm.tenant_id,  # type: ignore[arg-type]
            user_id=orm.user_id,  # type: ignore[arg-type]
            conversation_type=ConversationType(orm.conversation_type),  # type: ignore[arg-type]
            state=orm.state,  # type: ignore[arg-type]
            state_metadata=orm.state_metadata,  # type: ignore[arg-type]
            title=orm.title,  # type: ignore[arg-type]
            created_at=orm.created_at,  # type: ignore[arg-type]
            updated_at=orm.updated_at,  # type: ignore[arg-type]
            metadata=orm.conversation_metadata,  # type: ignore[arg-type]
        )

    def _orm_to_message(self, orm: ConversationMessageModel) -> Message:
        """Convert ORM model to domain model.

        Args:
            orm: SQLAlchemy ConversationMessageModel instance

        Returns:
            Message domain model
        """
        # Type ignore needed for SQLAlchemy ORM attribute access
        return Message(
            id=UUID(orm.id) if isinstance(orm.id, str) else orm.id,  # type: ignore[arg-type]
            conversation_id=(
                UUID(orm.conversation_id)  # type: ignore[arg-type]
                if isinstance(orm.conversation_id, str)
                else orm.conversation_id
            ),
            role=MessageRole(orm.role),  # type: ignore[arg-type]
            content=orm.content,  # type: ignore[arg-type]
            created_at=orm.created_at,  # type: ignore[arg-type]
            metadata=orm.message_metadata,  # type: ignore[arg-type]
        )
