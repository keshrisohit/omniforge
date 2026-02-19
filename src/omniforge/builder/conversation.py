"""Conversation state machine for agent creation.

DEPRECATED: This module is kept for backward compatibility.
Use omniforge.builder.conversation.manager instead.
"""

# Import from new location for backward compatibility
from omniforge.builder.conversation.manager import (
    ConversationContext,
    ConversationManager,
    ConversationState,
)

__all__ = [
    "ConversationContext",
    "ConversationManager",
    "ConversationState",
]
