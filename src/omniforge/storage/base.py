"""Abstract repository interfaces for storage layer.

This module defines Protocol classes for task and agent repositories,
enabling different storage backend implementations while maintaining
a consistent interface.
"""

from typing import TYPE_CHECKING, Optional, Protocol

if TYPE_CHECKING:
    from omniforge.agents.base import BaseAgent

from omniforge.tasks.models import Task


class TaskRepository(Protocol):
    """Protocol for task storage operations.

    This protocol defines the interface that all task repository implementations
    must follow, enabling storage backend swapping without code changes.
    """

    async def get(self, task_id: str) -> Optional[Task]:
        """Retrieve a task by ID.

        Args:
            task_id: Unique identifier of the task

        Returns:
            Task object if found, None otherwise
        """
        ...

    async def save(self, task: Task) -> None:
        """Save a new task.

        Args:
            task: Task object to save

        Raises:
            ValueError: If task with same ID already exists
        """
        ...

    async def update(self, task: Task) -> None:
        """Update an existing task.

        Args:
            task: Task object with updated data

        Raises:
            ValueError: If task does not exist
        """
        ...

    async def delete(self, task_id: str) -> None:
        """Delete a task by ID.

        Args:
            task_id: Unique identifier of the task to delete

        Raises:
            ValueError: If task does not exist
        """
        ...

    async def list_by_agent(self, agent_id: str, limit: int = 100) -> list[Task]:
        """List tasks for a specific agent.

        Args:
            agent_id: Agent identifier to filter by
            limit: Maximum number of tasks to return (default: 100)

        Returns:
            List of tasks for the specified agent, ordered by created_at desc
        """
        ...

    async def list_by_parent(self, parent_task_id: str, limit: int = 100) -> list[Task]:
        """List child tasks for a specific parent task.

        Args:
            parent_task_id: Parent task identifier to filter by
            limit: Maximum number of tasks to return (default: 100)

        Returns:
            List of tasks that have the specified parent_task_id
        """
        ...


class AgentRepository(Protocol):
    """Protocol for agent storage operations.

    This protocol defines the interface that all agent repository implementations
    must follow, enabling storage backend swapping without code changes.
    """

    async def get(self, agent_id: str) -> Optional["BaseAgent"]:
        """Retrieve an agent by ID.

        Args:
            agent_id: Unique identifier of the agent

        Returns:
            BaseAgent object if found, None otherwise
        """
        ...

    async def save(self, agent: "BaseAgent") -> None:
        """Save a new agent.

        Args:
            agent: "BaseAgent" object to save

        Raises:
            ValueError: If agent with same ID already exists
        """
        ...

    async def delete(self, agent_id: str) -> None:
        """Delete an agent by ID.

        Args:
            agent_id: Unique identifier of the agent to delete

        Raises:
            ValueError: If agent does not exist
        """
        ...

    async def list_all(self, limit: int = 100) -> list["BaseAgent"]:
        """List all agents.

        Args:
            limit: Maximum number of agents to return (default: 100)

        Returns:
            List of all agents, ordered by registration time
        """
        ...

    async def list_by_tenant(self, tenant_id: str, limit: int = 100) -> list["BaseAgent"]:
        """List agents for a specific tenant.

        Args:
            tenant_id: Tenant identifier to filter by
            limit: Maximum number of agents to return (default: 100)

        Returns:
            List of agents for the specified tenant
        """
        ...
