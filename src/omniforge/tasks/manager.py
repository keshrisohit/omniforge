"""Task lifecycle management.

This module provides the TaskManager class for creating, retrieving,
updating, and processing tasks through their lifecycle.
"""

from datetime import datetime
from typing import AsyncIterator, cast
from uuid import uuid4

from omniforge.agents.base import BaseAgent
from omniforge.agents.events import (
    TaskArtifactEvent,
    TaskDoneEvent,
    TaskErrorEvent,
    TaskEvent,
    TaskMessageEvent,
    TaskStatusEvent,
)
from omniforge.storage.base import AgentRepository, TaskRepository
from omniforge.tasks.models import Task, TaskCreateRequest, TaskError, TaskMessage, TaskState


class TaskManager:
    """Manages task lifecycle and coordinates with agents.

    The TaskManager is responsible for:
    - Creating new tasks from requests
    - Storing and retrieving tasks via repository
    - Updating task state
    - Delegating task processing to agents
    - Managing task-agent coordination

    Attributes:
        _task_repo: Repository for task persistence
        _agent_repo: Repository for agent retrieval
    """

    def __init__(self, task_repo: TaskRepository, agent_repo: AgentRepository) -> None:
        """Initialize the task manager.

        Args:
            task_repo: Repository implementation for task storage
            agent_repo: Repository implementation for agent retrieval
        """
        self._task_repo = task_repo
        self._agent_repo = agent_repo

    async def create_task(self, agent_id: str, request: TaskCreateRequest) -> Task:
        """Create a new task from a request.

        Args:
            agent_id: ID of the agent to handle this task
            request: Task creation request containing message_parts, user_id, etc.

        Returns:
            Newly created Task object in SUBMITTED state

        Raises:
            ValueError: If agent_id does not exist in agent repository
        """
        # Verify agent exists
        agent = await self._agent_repo.get(agent_id)
        if agent is None:
            raise ValueError(f"Agent with ID {agent_id} does not exist")

        # Generate unique task ID
        task_id = str(uuid4())
        message_id = str(uuid4())
        now = datetime.utcnow()

        # Create initial user message
        initial_message = TaskMessage(
            id=message_id,
            role="user",
            parts=request.message_parts,
            created_at=now,
        )

        # Create task in SUBMITTED state
        task = Task(
            id=task_id,
            agent_id=agent_id,
            state=TaskState.SUBMITTED,
            messages=[initial_message],
            artifacts=[],
            created_at=now,
            updated_at=now,
            tenant_id=request.tenant_id,
            user_id=request.user_id,
            parent_task_id=request.parent_task_id,
        )

        # Save to repository
        await self._task_repo.save(task)

        return task

    async def get_task(self, task_id: str) -> Task:
        """Retrieve a task by ID.

        Args:
            task_id: Unique identifier of the task

        Returns:
            Task object

        Raises:
            ValueError: If task does not exist
        """
        task = await self._task_repo.get(task_id)
        if task is None:
            raise ValueError(f"Task with ID {task_id} does not exist")
        return task

    async def update_task_state(self, task_id: str, state: TaskState) -> Task:
        """Update the state of an existing task.

        Args:
            task_id: Unique identifier of the task
            state: New state to transition to

        Returns:
            Updated Task object

        Raises:
            ValueError: If task does not exist or state transition is invalid
        """
        task = await self.get_task(task_id)

        # Validate state transition
        if not task.can_transition_to(state):
            raise ValueError(
                f"Invalid state transition from {task.state} to {state} " f"for task {task_id}"
            )

        # Create updated task with new state
        updated_task = task.model_copy(
            update={
                "state": state,
                "updated_at": datetime.utcnow(),
            }
        )

        # Save updated task
        await self._task_repo.update(updated_task)

        return updated_task

    @staticmethod
    def apply_event(task: Task, event: TaskEvent) -> Task:
        """Return a new Task with the event's effects applied.

        Maps each event type to the corresponding task mutation:
        - TaskStatusEvent  → update state
        - TaskMessageEvent → append agent message to messages[]
        - TaskArtifactEvent → append artifact to artifacts[]
        - TaskDoneEvent    → update state to final_state
        - TaskErrorEvent   → transition to FAILED with error details

        Args:
            task: Current task snapshot
            event: The event to apply

        Returns:
            New Task instance with mutations applied; same instance if event type is unknown.
        """
        now = datetime.utcnow()

        if isinstance(event, TaskStatusEvent):
            return task.model_copy(update={"state": event.state, "updated_at": now})

        if isinstance(event, TaskMessageEvent):
            new_message = TaskMessage(
                id=str(uuid4()),
                role="agent",
                parts=event.message_parts,
                created_at=now,
            )
            return task.model_copy(
                update={"messages": [*task.messages, new_message], "updated_at": now}
            )

        if isinstance(event, TaskArtifactEvent):
            return task.model_copy(
                update={"artifacts": [*task.artifacts, event.artifact], "updated_at": now}
            )

        if isinstance(event, TaskDoneEvent):
            if event.final_state == TaskState.FAILED:
                # TaskDoneEvent carries no error details; use a generic error so the
                # validator (failed task must have error) is satisfied.
                error = TaskError(
                    code="agent_failed",
                    message="Agent reported failure via TaskDoneEvent",
                )
                return task.model_copy(
                    update={"state": TaskState.FAILED, "error": error, "updated_at": now}
                )
            return task.model_copy(update={"state": event.final_state, "updated_at": now})

        if isinstance(event, TaskErrorEvent):
            error = TaskError(
                code=event.error_code,
                message=event.error_message,
                details=event.details,
            )
            return task.model_copy(
                update={"state": TaskState.FAILED, "error": error, "updated_at": now}
            )

        return task  # unknown event type — pass through unchanged

    async def process_task(self, task: Task) -> AsyncIterator[TaskEvent]:
        """Process a task by delegating to its assigned agent, persisting every event.

        Yields events as they arrive while keeping the task in the repository
        up-to-date so crash recovery, polling, and auditing work correctly.

        Args:
            task: Task to process

        Yields:
            TaskEvent objects from the agent processing the task

        Raises:
            ValueError: If agent does not exist
        """
        # Retrieve the agent
        agent = await self._agent_repo.get(task.agent_id)
        if agent is None:
            raise ValueError(f"Agent with ID {task.agent_id} does not exist")

        # Type narrow agent to BaseAgent for mypy
        agent = cast(BaseAgent, agent)

        current_task = task
        # Note: mypy has issues with AsyncIterator return type on async generators
        async for event in agent.process_task(task):  # type: ignore[attr-defined]
            updated = self.apply_event(current_task, event)
            if updated is not current_task:
                await self._task_repo.update(updated)
                current_task = updated
            yield event
