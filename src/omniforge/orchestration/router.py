"""Task routing and parent/child task relationship management.

This module provides the TaskRouter class for routing tasks between agents,
tracking parent/child task relationships, and aggregating results from
delegated subtasks.
"""

from typing import AsyncIterator, Optional

from omniforge.agents.events import TaskEvent
from omniforge.agents.models import AgentCard, MessagePart
from omniforge.orchestration.client import A2AClient
from omniforge.storage.base import TaskRepository
from omniforge.tasks.models import Task, TaskCreateRequest, TaskState


class TaskRouter:
    """Router for managing task delegation and parent/child relationships.

    The TaskRouter enables agents to delegate tasks to other agents while
    maintaining proper parent/child task relationships. It tracks which tasks
    are subtasks of others and can aggregate results from child tasks.

    This class combines the A2AClient for communication with task repository
    for persistence and relationship tracking.

    Attributes:
        _client: HTTP client for agent-to-agent communication
        _task_repo: Repository for task persistence and retrieval
        _owns_client: Whether this router owns the client (for cleanup)

    Example:
        >>> from omniforge.storage.memory import InMemoryTaskRepository
        >>> task_repo = InMemoryTaskRepository()
        >>> router = TaskRouter(task_repo=task_repo)
        >>>
        >>> # Delegate task to another agent
        >>> async for event in router.delegate_task(
        ...     parent_task_id="parent-123",
        ...     agent_card=remote_agent_card,
        ...     message_parts=[TextPart(text="Analyze this")],
        ...     tenant_id="tenant-1",
        ...     user_id="user-1"
        ... ):
        ...     print(f"Event: {event.type}")
        >>>
        >>> # Get child tasks
        >>> children = await router.get_child_tasks("parent-123")
    """

    def __init__(
        self,
        task_repo: TaskRepository,
        client: Optional[A2AClient] = None,
    ) -> None:
        """Initialize the task router.

        Args:
            task_repo: Task repository for persistence
            client: Optional A2AClient instance (creates new one if not provided)
        """
        self._task_repo = task_repo
        self._client = client or A2AClient()
        self._owns_client = client is None

    async def close(self) -> None:
        """Close the router and release resources.

        Closes the HTTP client if it was created by this router.

        Example:
            >>> router = TaskRouter(task_repo=task_repo)
            >>> try:
            ...     # Use router
            ...     pass
            ... finally:
            ...     await router.close()
        """
        if self._owns_client:
            await self._client.close()

    async def __aenter__(self) -> "TaskRouter":
        """Enter async context manager.

        Returns:
            This router instance
        """
        return self

    async def __aexit__(self, exc_type: type, exc_val: Exception, exc_tb: object) -> None:
        """Exit async context manager and close router.

        Args:
            exc_type: Exception type if an error occurred
            exc_val: Exception value if an error occurred
            exc_tb: Exception traceback if an error occurred
        """
        await self.close()

    async def delegate_task(
        self,
        parent_task_id: str,
        agent_card: AgentCard,
        message_parts: list[MessagePart],
        tenant_id: str,
        user_id: str,
    ) -> AsyncIterator[TaskEvent]:
        """Delegate a task to another agent and track the parent/child relationship.

        Creates a new task on the remote agent specified by the agent_card,
        setting the parent_task_id to establish the relationship. The parent
        task must exist in the task repository.

        Args:
            parent_task_id: ID of the parent task that is delegating
            agent_card: Agent card of the target agent
            message_parts: Message parts for the delegated task
            tenant_id: Tenant ID for multi-tenancy
            user_id: User ID who owns the task

        Yields:
            TaskEvent objects from the remote agent's task processing

        Raises:
            ValueError: If parent task does not exist
            httpx.HTTPError: If HTTP communication fails

        Example:
            >>> async for event in router.delegate_task(
            ...     parent_task_id="task-123",
            ...     agent_card=remote_card,
            ...     message_parts=[TextPart(text="Process this data")],
            ...     tenant_id="tenant-1",
            ...     user_id="user-1"
            ... ):
            ...     if event.type == "done":
            ...         print(f"Subtask completed: {event.final_state}")
        """
        # Verify parent task exists
        parent_task = await self._task_repo.get(parent_task_id)
        if parent_task is None:
            raise ValueError(f"Parent task {parent_task_id} does not exist")

        # Create task request with parent relationship
        request = TaskCreateRequest(
            message_parts=message_parts,
            tenant_id=tenant_id,
            user_id=user_id,
            parent_task_id=parent_task_id,
        )

        # Send task to remote agent and stream events
        async for event in self._client.send_task(agent_card, request):
            yield event

    async def get_child_tasks(self, parent_task_id: str) -> list[Task]:
        """Get all child tasks for a given parent task.

        Retrieves all tasks that have the specified task ID as their parent.
        This is useful for tracking all subtasks that were delegated from
        a parent task.

        Args:
            parent_task_id: ID of the parent task

        Returns:
            List of child tasks

        Example:
            >>> children = await router.get_child_tasks("parent-123")
            >>> for child in children:
            ...     print(f"Child task {child.id}: {child.state}")
        """
        return await self._task_repo.list_by_parent(parent_task_id)

    async def get_task_hierarchy(self, task_id: str) -> dict:
        """Get the complete task hierarchy (parent and children) for a task.

        Returns a dictionary containing the task itself, its parent (if any),
        and all its children (if any). This provides a complete view of the
        task's position in the delegation tree.

        Args:
            task_id: ID of the task to get hierarchy for

        Returns:
            Dictionary with keys:
                - task: The task itself
                - parent: Parent task (or None)
                - children: List of child tasks

        Raises:
            ValueError: If task does not exist

        Example:
            >>> hierarchy = await router.get_task_hierarchy("task-123")
            >>> if hierarchy["parent"]:
            ...     print(f"Parent: {hierarchy['parent'].id}")
            >>> print(f"Children: {len(hierarchy['children'])}")
        """
        # Get the task
        task = await self._task_repo.get(task_id)
        if task is None:
            raise ValueError(f"Task {task_id} does not exist")

        # Get parent task if it exists
        parent = None
        if task.parent_task_id:
            parent = await self._task_repo.get(task.parent_task_id)

        # Get child tasks
        children = await self.get_child_tasks(task_id)

        return {
            "task": task,
            "parent": parent,
            "children": children,
        }

    async def aggregate_child_results(self, parent_task_id: str) -> dict:
        """Aggregate results from all child tasks.

        Collects and summarizes the results from all child tasks of a parent.
        Returns statistics about child task states and collects all artifacts
        produced by completed child tasks.

        Args:
            parent_task_id: ID of the parent task

        Returns:
            Dictionary with aggregated results:
                - total_children: Total number of child tasks
                - completed: Number of completed child tasks
                - failed: Number of failed child tasks
                - in_progress: Number of tasks still in progress
                - artifacts: List of all artifacts from completed children

        Example:
            >>> results = await router.aggregate_child_results("parent-123")
            >>> print(f"Completed: {results['completed']}/{results['total_children']}")
            >>> print(f"Total artifacts: {len(results['artifacts'])}")
        """
        children = await self.get_child_tasks(parent_task_id)

        # Initialize counters
        total_children = len(children)
        completed = 0
        failed = 0
        in_progress = 0
        artifacts = []

        # Aggregate child task states and artifacts
        for child in children:
            if child.state == TaskState.COMPLETED:
                completed += 1
                artifacts.extend(child.artifacts)
            elif child.state == TaskState.FAILED:
                failed += 1
            elif not child.state.is_terminal():
                in_progress += 1

        return {
            "total_children": total_children,
            "completed": completed,
            "failed": failed,
            "in_progress": in_progress,
            "artifacts": artifacts,
        }
