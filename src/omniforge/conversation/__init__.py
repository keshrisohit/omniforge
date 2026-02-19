"""Conversation domain models and repository interfaces.

This module provides the core conversation and message models,
along with the repository interface for persistence operations.
"""

from omniforge.conversation.models import Conversation, Message, MessageRole
from omniforge.conversation.repository import ConversationRepository

# Lazy imports for implementations to avoid circular dependencies
# Import directly when needed:
# from omniforge.conversation.sqlite_repository import SQLiteConversationRepository
# from omniforge.conversation.memory_repository import InMemoryConversationRepository
# from omniforge.conversation.orm import ConversationModel, ConversationMessageModel

__all__ = [
    "Conversation",
    "Message",
    "MessageRole",
    "ConversationRepository",
]
