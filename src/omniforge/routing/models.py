"""Core routing models for request routing and decision making.

This module provides pure routing types with no internal dependencies
to prevent circular imports.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class ActionType(str, Enum):
    """User intent action types for routing decisions.

    Defines the different types of actions that can be performed
    in the system, used by routing logic to determine handlers.
    """

    CREATE_AGENT = "create_agent"
    CREATE_SKILL = "create_skill"
    ADD_SKILL_TO_AGENT = "add_skill_to_agent"
    EXECUTE_TASK = "execute_task"
    UPDATE_AGENT = "update_agent"
    QUERY_INFO = "query_info"
    MANAGE_PLATFORM = "manage_platform"
    UNKNOWN = "unknown"


@dataclass
class RoutingDecision:
    """Routing decision made by master agent or router.

    Contains the determined action type, confidence level, and additional
    context for routing the request to appropriate handlers.

    Attributes:
        action_type: The type of action to perform
        confidence: Confidence level (0.0-1.0) in the routing decision
        target_agent_id: Optional ID of specific agent to route to
        reasoning: Human-readable explanation of routing decision
        entities: Additional extracted entities and context
    """

    action_type: ActionType
    confidence: float
    target_agent_id: Optional[str] = None
    reasoning: str = ""
    entities: Dict[str, Any] = field(default_factory=dict)
