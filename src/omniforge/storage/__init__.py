"""Storage layer for OmniForge task and agent persistence.

This module provides repository pattern interfaces and implementations
for storing tasks and agents with support for different storage backends.
"""

# NOTE: Lazy imports to avoid circular dependencies
# Import these directly when needed:
# from omniforge.storage.base import AgentRepository, TaskRepository
# from omniforge.storage.memory import InMemoryAgentRepository, InMemoryTaskRepository
# from omniforge.storage.database import Database, DatabaseConfig, Base
# from omniforge.storage.cost_repository import CostRecordRepository, ModelUsageRepository
# from omniforge.storage.models import CostRecordModel, ModelUsageModel

__all__ = [
    "AgentRepository",
    "TaskRepository",
    "InMemoryAgentRepository",
    "InMemoryTaskRepository",
]


def __getattr__(name: str):
    """Lazy load attributes to avoid circular imports."""
    if name == "AgentRepository":
        from omniforge.storage.base import AgentRepository

        return AgentRepository
    elif name == "TaskRepository":
        from omniforge.storage.base import TaskRepository

        return TaskRepository
    elif name == "InMemoryAgentRepository":
        from omniforge.storage.memory import InMemoryAgentRepository

        return InMemoryAgentRepository
    elif name == "InMemoryTaskRepository":
        from omniforge.storage.memory import InMemoryTaskRepository

        return InMemoryTaskRepository
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
