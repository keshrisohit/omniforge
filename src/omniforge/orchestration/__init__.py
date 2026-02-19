"""Orchestration layer for agent-to-agent communication.

This module provides the core orchestration capabilities for enabling
agents to discover and delegate tasks to other agents. It includes:

- AgentDiscoveryService: Finding agents by skills and capabilities
- A2AClient: HTTP client for agent-to-agent communication
- TaskRouter: Routing and tracking parent/child task relationships
- HandoffManager: Managing conversation handoffs between agents
- StreamRouter: Routing messages based on handoff state
"""

from omniforge.orchestration.client import A2AClient
from omniforge.orchestration.discovery import AgentDiscoveryService
from omniforge.orchestration.handoff import HandoffManager, HandoffSession, HandoffState
from omniforge.orchestration.router import TaskRouter
from omniforge.orchestration.stream_router import StreamRouter

__all__ = [
    "AgentDiscoveryService",
    "A2AClient",
    "TaskRouter",
    "HandoffManager",
    "HandoffSession",
    "HandoffState",
    "StreamRouter",
]
