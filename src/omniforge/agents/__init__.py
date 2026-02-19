"""Agent-to-Agent (A2A) protocol implementation.

This module provides the core A2A protocol models and interfaces for
agent identity, capabilities, skills, and communication.
"""

from omniforge.agents.autonomous_simple import (
    SimpleAutonomousAgent,
    run_autonomous_agent,
)
from omniforge.agents.base import BaseAgent
from omniforge.agents.errors import (
    AgentError,
    AgentNotFoundError,
    AgentProcessingError,
    SkillNotFoundError,
    TaskNotFoundError,
    TaskStateError,
)
from omniforge.agents.events import (
    BaseTaskEvent,
    TaskArtifactEvent,
    TaskDoneEvent,
    TaskErrorEvent,
    TaskEvent,
    TaskMessageEvent,
    TaskStatusEvent,
)
from omniforge.agents.models import (
    AgentCapabilities,
    AgentCard,
    AgentIdentity,
    AgentSkill,
    Artifact,
    AuthScheme,
    DataPart,
    FilePart,
    MessagePart,
    SecurityConfig,
    SkillInputMode,
    SkillOutputMode,
    TextPart,
)
from omniforge.agents.registry import AgentRegistry
from omniforge.agents.simple import SimpleAgent
from omniforge.agents.streaming import (
    format_artifact_event,
    format_done_event,
    format_error_event,
    format_message_event,
    format_status_event,
    format_task_event,
    stream_task_events,
    stream_task_with_error_handling,
)

__all__ = [
    # Agents
    "BaseAgent",
    "SimpleAgent",
    "SimpleAutonomousAgent",
    "run_autonomous_agent",
    # Errors
    "AgentError",
    "AgentNotFoundError",
    "AgentProcessingError",
    "SkillNotFoundError",
    "TaskNotFoundError",
    "TaskStateError",
    # Events
    "BaseTaskEvent",
    "TaskArtifactEvent",
    "TaskDoneEvent",
    "TaskErrorEvent",
    "TaskEvent",
    "TaskMessageEvent",
    "TaskStatusEvent",
    # Models
    "AgentCapabilities",
    "AgentCard",
    "AgentIdentity",
    "AgentSkill",
    "Artifact",
    "AuthScheme",
    "DataPart",
    "FilePart",
    "MessagePart",
    "SecurityConfig",
    "SkillInputMode",
    "SkillOutputMode",
    "TextPart",
    # Registry
    "AgentRegistry",
    # Streaming
    "format_artifact_event",
    "format_done_event",
    "format_error_event",
    "format_message_event",
    "format_status_event",
    "format_task_event",
    "stream_task_events",
    "stream_task_with_error_handling",
]
