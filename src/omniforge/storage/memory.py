"""In-memory implementations of repository interfaces.

This module provides thread-safe, dictionary-based storage implementations
for tasks and agents, suitable for development and testing.
"""

import asyncio
from typing import Optional
from uuid import uuid4

from omniforge.agents.base import BaseAgent
from omniforge.agents.models import Artifact
from omniforge.tasks.models import Task


class InMemoryTaskRepository:
    """Thread-safe in-memory implementation of TaskRepository.

    Uses a dictionary for storage with asyncio locks for thread safety.
    Suitable for development, testing, and single-instance deployments.

    Attributes:
        _tasks: Dictionary mapping task_id to Task objects
        _lock: Asyncio lock for thread-safe operations
    """

    def __init__(self) -> None:
        """Initialize the in-memory task repository."""
        self._tasks: dict[str, Task] = {}
        self._lock = asyncio.Lock()

    async def get(self, task_id: str) -> Optional[Task]:
        """Retrieve a task by ID.

        Args:
            task_id: Unique identifier of the task

        Returns:
            Task object if found, None otherwise
        """
        async with self._lock:
            return self._tasks.get(task_id)

    async def save(self, task: Task) -> None:
        """Save a new task.

        Args:
            task: Task object to save

        Raises:
            ValueError: If task with same ID already exists
        """
        async with self._lock:
            if task.id in self._tasks:
                raise ValueError(f"Task with ID {task.id} already exists")
            self._tasks[task.id] = task

    async def update(self, task: Task) -> None:
        """Update an existing task.

        Args:
            task: Task object with updated data

        Raises:
            ValueError: If task does not exist
        """
        async with self._lock:
            if task.id not in self._tasks:
                raise ValueError(f"Task with ID {task.id} does not exist")
            self._tasks[task.id] = task

    async def delete(self, task_id: str) -> None:
        """Delete a task by ID.

        Args:
            task_id: Unique identifier of the task to delete

        Raises:
            ValueError: If task does not exist
        """
        async with self._lock:
            if task_id not in self._tasks:
                raise ValueError(f"Task with ID {task_id} does not exist")
            del self._tasks[task_id]

    async def list_by_agent(self, agent_id: str, limit: int = 100) -> list[Task]:
        """List tasks for a specific agent.

        Args:
            agent_id: Agent identifier to filter by
            limit: Maximum number of tasks to return (default: 100)

        Returns:
            List of tasks for the specified agent, ordered by created_at desc
        """
        async with self._lock:
            agent_tasks = [task for task in self._tasks.values() if task.agent_id == agent_id]
            # Sort by created_at descending (most recent first)
            agent_tasks.sort(key=lambda t: t.created_at, reverse=True)
            return agent_tasks[:limit]

    async def list_by_parent(self, parent_task_id: str, limit: int = 100) -> list[Task]:
        """List child tasks for a specific parent task.

        Args:
            parent_task_id: Parent task identifier to filter by
            limit: Maximum number of tasks to return (default: 100)

        Returns:
            List of tasks that have the specified parent_task_id
        """
        async with self._lock:
            child_tasks = [
                task for task in self._tasks.values() if task.parent_task_id == parent_task_id
            ]
            # Sort by created_at ascending (order of creation)
            child_tasks.sort(key=lambda t: t.created_at)
            return child_tasks[:limit]

    async def list_by_tenant(
        self, tenant_id: str, limit: int = 100, offset: int = 0
    ) -> list[Task]:
        """List tasks for a specific tenant with pagination.

        Args:
            tenant_id: Tenant identifier to filter by
            limit: Maximum number of tasks to return (default: 100)
            offset: Number of tasks to skip (default: 0)

        Returns:
            List of tasks for the tenant, ordered by created_at desc
        """
        async with self._lock:
            tenant_tasks = [
                task for task in self._tasks.values() if task.tenant_id == tenant_id
            ]
            tenant_tasks.sort(key=lambda t: t.created_at, reverse=True)
            return tenant_tasks[offset : offset + limit]

    async def list_by_skill(
        self, tenant_id: str, skill_name: str, limit: int = 100
    ) -> list[Task]:
        """List tasks for a specific tenant filtered by skill name.

        Args:
            tenant_id: Tenant identifier to filter by
            skill_name: Skill name to filter by
            limit: Maximum number of tasks to return (default: 100)

        Returns:
            List of tasks matching tenant and skill name, ordered by created_at desc
        """
        async with self._lock:
            skill_tasks = [
                task
                for task in self._tasks.values()
                if task.tenant_id == tenant_id and task.skill_name == skill_name
            ]
            skill_tasks.sort(key=lambda t: t.created_at, reverse=True)
            return skill_tasks[:limit]


class InMemoryAgentRepository:
    """Thread-safe in-memory implementation of AgentRepository.

    Uses a dictionary for storage with asyncio locks for thread safety.
    Suitable for development, testing, and single-instance deployments.

    Note: For tenant filtering, agents must have a tenant_id attribute.
    This implementation stores agents by their identity.id value.

    Attributes:
        _agents: Dictionary mapping agent_id to BaseAgent objects
        _lock: Asyncio lock for thread-safe operations
    """

    def __init__(self) -> None:
        """Initialize the in-memory agent repository."""
        self._agents: dict[str, BaseAgent] = {}
        self._lock = asyncio.Lock()

    async def get(self, agent_id: str) -> Optional[BaseAgent]:
        """Retrieve an agent by ID.

        Args:
            agent_id: Unique identifier of the agent

        Returns:
            BaseAgent object if found, None otherwise
        """
        async with self._lock:
            return self._agents.get(agent_id)

    async def save(self, agent: BaseAgent) -> None:
        """Save a new agent.

        Args:
            agent: BaseAgent object to save

        Raises:
            ValueError: If agent with same ID already exists
        """
        async with self._lock:
            agent_id = agent.identity.id
            if agent_id in self._agents:
                raise ValueError(f"Agent with ID {agent_id} already exists")
            self._agents[agent_id] = agent

    async def update(self, agent: BaseAgent) -> None:
        """Update an existing agent.

        Args:
            agent: BaseAgent object with updated data

        Raises:
            ValueError: If agent does not exist
        """
        async with self._lock:
            agent_id = agent.identity.id
            if agent_id not in self._agents:
                raise ValueError(f"Agent with ID {agent_id} does not exist")
            self._agents[agent_id] = agent

    async def delete(self, agent_id: str) -> None:
        """Delete an agent by ID.

        Args:
            agent_id: Unique identifier of the agent to delete

        Raises:
            ValueError: If agent does not exist
        """
        async with self._lock:
            if agent_id not in self._agents:
                raise ValueError(f"Agent with ID {agent_id} does not exist")
            del self._agents[agent_id]

    async def list_all(self, limit: int = 100) -> list[BaseAgent]:
        """List all agents.

        Args:
            limit: Maximum number of agents to return (default: 100)

        Returns:
            List of all agents, ordered by registration time
        """
        async with self._lock:
            # Return agents in insertion order (dict preserves insertion order in Python 3.7+)
            agents = list(self._agents.values())
            return agents[:limit]

    async def list_by_tenant(self, tenant_id: str, limit: int = 100) -> list[BaseAgent]:
        """List agents for a specific tenant.

        Args:
            tenant_id: Tenant identifier to filter by
            limit: Maximum number of agents to return (default: 100)

        Returns:
            List of agents for the specified tenant

        Note:
            This implementation assumes agents have a tenant_id attribute.
            If not present, the agent will be skipped.
        """
        async with self._lock:
            tenant_agents = [
                agent
                for agent in self._agents.values()
                if hasattr(agent, "tenant_id") and agent.tenant_id == tenant_id
            ]
            return tenant_agents[:limit]


class InMemoryArtifactRepository:
    """Thread-safe in-memory implementation of ArtifactStore.

    Stores artifacts in a nested dict: {tenant_id: {artifact_id: Artifact}}.
    Returns deep copies on fetch to prevent mutation of stored state.

    Attributes:
        _artifacts: Nested dict mapping tenant_id -> artifact_id -> Artifact
        _lock: Asyncio lock for thread-safe operations
    """

    def __init__(self) -> None:
        """Initialize the in-memory artifact repository."""
        self._artifacts: dict[str, dict[str, Artifact]] = {}
        self._lock = asyncio.Lock()

    async def store(self, artifact: Artifact) -> str:
        """Persist an artifact and return its ID.

        Generates a UUID if artifact.id is None. Upserts within the
        tenant namespace, so calling store() with an existing ID overwrites.

        Args:
            artifact: Artifact to persist (tenant_id must be set)

        Returns:
            The artifact ID (generated or existing)
        """
        async with self._lock:
            artifact_id = artifact.id if artifact.id is not None else str(uuid4())
            tenant_id = artifact.tenant_id

            if tenant_id not in self._artifacts:
                self._artifacts[tenant_id] = {}

            stored = artifact.model_copy(update={"id": artifact_id})
            self._artifacts[tenant_id][artifact_id] = stored
            return artifact_id

    async def fetch(self, artifact_id: str, tenant_id: str) -> Optional[Artifact]:
        """Retrieve an artifact by ID within a tenant.

        Returns None if not found or if the artifact belongs to a different tenant,
        making cross-tenant access indistinguishable from not-found.

        Args:
            artifact_id: Unique identifier of the artifact
            tenant_id: Tenant namespace to look up within

        Returns:
            Deep copy of the artifact if found, None otherwise
        """
        async with self._lock:
            tenant_store = self._artifacts.get(tenant_id)
            if tenant_store is None:
                return None
            artifact = tenant_store.get(artifact_id)
            if artifact is None:
                return None
            return artifact.model_copy(deep=True)

    async def delete(self, artifact_id: str, tenant_id: str) -> None:
        """Delete an artifact by ID within a tenant.

        Args:
            artifact_id: Unique identifier of the artifact to delete
            tenant_id: Tenant namespace to delete within

        Raises:
            ValueError: If artifact not found within that tenant
        """
        async with self._lock:
            tenant_store = self._artifacts.get(tenant_id)
            if tenant_store is None or artifact_id not in tenant_store:
                raise ValueError(f"Artifact {artifact_id} not found for tenant {tenant_id}")
            del tenant_store[artifact_id]
