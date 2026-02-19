"""Conversation domain models.

Provides core data models for conversations and messages using Pydantic
for validation and serialization. Supports multiple conversation types including
regular chat and stateful conversations with FSM state tracking.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class ConversationType(str, Enum):
    """Type of conversation.

    Defines the purpose and behavior of a conversation, enabling different
    conversation modes with specialized handling.
    """

    CHAT = "chat"
    SKILL_CREATION = "skill_creation"
    AGENT_BUILDING = "agent_building"
    DEBUGGING_SESSION = "debugging_session"


class MessageRole(str, Enum):
    """Role of a message sender in a conversation.

    Defines who sent the message - the user, assistant (AI), or system.
    """

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Message(BaseModel):
    """A single message within a conversation.

    Represents one message exchange in a conversation thread,
    with role, content, and metadata tracking.

    Attributes:
        id: Unique identifier for the message
        conversation_id: ID of the parent conversation
        role: Who sent the message (user, assistant, system)
        content: The message text content
        created_at: Timestamp when message was created
        metadata: Additional message metadata (optional)
    """

    id: UUID = Field(default_factory=uuid4)
    conversation_id: UUID
    role: MessageRole
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(use_enum_values=True)


class Conversation(BaseModel):
    """A conversation thread between user and assistant with type and state support.

    Unified model supporting both regular chat and stateful conversations (like
    skill creation with FSM states). Represents a complete conversation session
    with metadata, tenant isolation, and user ownership tracking.

    Attributes:
        id: Unique identifier for the conversation
        tenant_id: Tenant this conversation belongs to (for multi-tenancy)
        user_id: ID of the user who owns this conversation
        conversation_type: Type of conversation (chat, skill_creation, etc.)
        state: Optional FSM state for stateful conversations
        state_metadata: Optional state-specific data
        title: Optional human-readable title
        created_at: Timestamp when conversation was created
        updated_at: Timestamp when conversation was last modified
        metadata: Additional conversation metadata (optional)
    """

    id: UUID = Field(default_factory=uuid4)
    tenant_id: str
    user_id: str
    conversation_type: ConversationType = ConversationType.CHAT
    state: Optional[str] = None
    state_metadata: Optional[Dict[str, Any]] = None
    title: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(use_enum_values=True)
