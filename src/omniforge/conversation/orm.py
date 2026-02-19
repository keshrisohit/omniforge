"""SQLAlchemy ORM models for conversation persistence.

This module defines database models for conversations and messages with
proper tenant isolation and indexing for efficient queries.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship  # type: ignore[attr-defined]

from omniforge.storage.base_model import Base


class ConversationModel(Base):  # type: ignore[valid-type,misc]
    """ORM model for conversations with support for multiple conversation types.

    Unified model supporting both regular chat and stateful conversations (like
    skill creation with FSM states). Stores conversation metadata with tenant
    isolation for multi-tenancy support.

    Attributes:
        id: Unique conversation identifier (UUID string)
        tenant_id: Tenant identifier for multi-tenancy isolation
        user_id: User who owns this conversation
        conversation_type: Type of conversation (chat, skill_creation, etc.)
        state: Optional FSM state for stateful conversations
        state_metadata: Optional state-specific data (JSON)
        title: Optional human-readable conversation title
        created_at: Timestamp when conversation was created
        updated_at: Timestamp when conversation was last updated
        conversation_metadata: Additional metadata stored as JSON
        messages: Relationship to associated messages
    """

    __tablename__ = "conversations"

    # Primary key
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Tenant and user identifiers (indexed for multi-tenancy queries)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # NEW: Conversation type and FSM state support
    conversation_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="chat", index=True
    )
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    state_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Conversation metadata
    title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, index=True
    )

    # Metadata stored as JSON (avoid 'metadata' - SQLAlchemy reserved word)
    conversation_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationship to messages
    messages: Mapped[list["ConversationMessageModel"]] = relationship(
        "ConversationMessageModel",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ConversationMessageModel.created_at",
    )

    # Composite indexes for common query patterns
    __table_args__ = (
        Index("idx_conversation_tenant_user", "tenant_id", "user_id"),
        Index("idx_conversation_tenant_updated", "tenant_id", "updated_at"),
        Index("idx_conversation_tenant_type", "tenant_id", "conversation_type"),
        Index("idx_conversation_type_state", "conversation_type", "state"),
    )


class ConversationMessageModel(Base):  # type: ignore[valid-type,misc]
    """ORM model for conversation messages.

    Stores individual messages within conversations with proper foreign key
    constraints and indexing for efficient retrieval.

    Attributes:
        id: Unique message identifier (UUID string)
        conversation_id: Foreign key to parent conversation
        role: Message role (user, assistant, system)
        content: Message text content
        created_at: Timestamp when message was created
        message_metadata: Additional metadata stored as JSON
        conversation: Relationship to parent conversation
    """

    __tablename__ = "conversation_messages"

    # Primary key
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Foreign key to conversation
    conversation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )

    # Message content
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, index=True
    )

    # Metadata stored as JSON (avoid 'metadata' - SQLAlchemy reserved word)
    message_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationship to parent conversation
    conversation: Mapped["ConversationModel"] = relationship(
        "ConversationModel", back_populates="messages"
    )

    # Composite index for efficient message retrieval
    __table_args__ = (Index("idx_conversation_created", "conversation_id", "created_at"),)
