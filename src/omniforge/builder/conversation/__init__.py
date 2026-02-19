"""Conversation management for agent creation."""

from omniforge.builder.conversation.manager import ConversationContext, ConversationManager
from omniforge.builder.conversation.skill_suggestion import SkillSuggestionManager

# Define ConversationState as alias to maintain compatibility
ConversationState = type(
    "ConversationState",
    (),
    {
        "INITIAL": "initial",
        "UNDERSTANDING_GOAL": "understanding_goal",
        "INTEGRATION_SETUP": "integration_setup",
        "REQUIREMENTS_GATHERING": "requirements_gathering",
        "SKILL_SUGGESTION": "skill_suggestion",
        "SKILL_DESIGN": "skill_design",
        "TESTING": "testing",
        "DEPLOYMENT": "deployment",
        "COMPLETE": "complete",
    },
)

__all__ = [
    "ConversationContext",
    "ConversationManager",
    "ConversationState",
    "SkillSuggestionManager",
]
