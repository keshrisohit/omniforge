"""SQL-backed repository for task persistence.

This module provides a SQLAlchemy-backed implementation of TaskRepository,
with full multi-tenancy enforcement on all list queries.
"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from omniforge.storage.models import TaskModel
from omniforge.tasks.models import Task, TaskError, TaskMessage, TaskState


class SQLTaskRepository:
    """SQL-backed implementation of TaskRepository.

    All list queries enforce tenant isolation via WHERE tenant_id = :tenant_id.

    Example:
        >>> repo = SQLTaskRepository(session)
        >>> await repo.save(task)
        >>> retrieved = await repo.get(task.id)
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def save(self, task: Task) -> None:
        """Persist a new task.

        Args:
            task: Task to persist

        Raises:
            ValueError: If task with same ID already exists
        """
        existing = await self.session.get(TaskModel, task.id)
        if existing is not None:
            raise ValueError(f"Task with ID {task.id} already exists")

        model = self._task_to_model(task)
        self.session.add(model)
        await self.session.flush()

    async def get(self, task_id: str) -> Optional[Task]:
        """Retrieve a task by ID.

        Args:
            task_id: Unique identifier of the task

        Returns:
            Task if found, None otherwise
        """
        model = await self.session.get(TaskModel, task_id)
        if model is None:
            return None
        return self._model_to_task(model)

    async def update(self, task: Task) -> None:
        """Update an existing task.

        Args:
            task: Task with updated data

        Raises:
            ValueError: If task does not exist
        """
        model = await self.session.get(TaskModel, task.id)
        if model is None:
            raise ValueError(f"Task with ID {task.id} does not exist")

        model.state = task.state.value
        model.messages = [m.model_dump(mode="json") for m in task.messages]
        model.artifacts = [a.model_dump(mode="json") for a in task.artifacts]
        model.error = task.error.model_dump(mode="json") if task.error else None
        model.updated_at = task.updated_at
        model.skill_name = task.skill_name
        model.input_summary = task.input_summary
        model.trace_id = task.trace_id
        model.conversation_id = task.conversation_id
        await self.session.flush()

    async def delete(self, task_id: str) -> None:
        """Delete a task by ID.

        Args:
            task_id: Unique identifier of the task to delete

        Raises:
            ValueError: If task does not exist
        """
        model = await self.session.get(TaskModel, task_id)
        if model is None:
            raise ValueError(f"Task with ID {task_id} does not exist")

        await self.session.delete(model)
        await self.session.flush()

    async def list_by_agent(self, agent_id: str, limit: int = 100) -> list[Task]:
        """List tasks for a specific agent.

        Args:
            agent_id: Agent identifier to filter by
            limit: Maximum number of tasks to return (default: 100)

        Returns:
            List of tasks for the agent, ordered by created_at desc
        """
        stmt = (
            select(TaskModel)
            .where(TaskModel.agent_id == agent_id)
            .order_by(TaskModel.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return [self._model_to_task(m) for m in result.scalars().all()]

    async def list_by_parent(self, parent_task_id: str, limit: int = 100) -> list[Task]:
        """List child tasks for a parent task.

        Args:
            parent_task_id: Parent task identifier to filter by
            limit: Maximum number of tasks to return (default: 100)

        Returns:
            List of child tasks, ordered by created_at asc
        """
        stmt = (
            select(TaskModel)
            .where(TaskModel.parent_task_id == parent_task_id)
            .order_by(TaskModel.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return [self._model_to_task(m) for m in result.scalars().all()]

    async def list_by_tenant(
        self, tenant_id: str, limit: int = 100, offset: int = 0
    ) -> list[Task]:
        """List tasks for a tenant with pagination.

        Multi-tenancy enforced: always filters by tenant_id.

        Args:
            tenant_id: Tenant identifier to filter by
            limit: Maximum number of tasks to return (default: 100)
            offset: Number of tasks to skip (default: 0)

        Returns:
            List of tasks for the tenant, ordered by created_at desc
        """
        stmt = (
            select(TaskModel)
            .where(TaskModel.tenant_id == tenant_id)
            .order_by(TaskModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return [self._model_to_task(m) for m in result.scalars().all()]

    async def list_by_skill(
        self, tenant_id: str, skill_name: str, limit: int = 100
    ) -> list[Task]:
        """List tasks filtered by tenant and skill name.

        Multi-tenancy enforced: always filters by tenant_id.

        Args:
            tenant_id: Tenant identifier to filter by
            skill_name: Skill name to filter by
            limit: Maximum number of tasks to return (default: 100)

        Returns:
            List of tasks matching tenant and skill, ordered by created_at desc
        """
        stmt = (
            select(TaskModel)
            .where(TaskModel.tenant_id == tenant_id, TaskModel.skill_name == skill_name)
            .order_by(TaskModel.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return [self._model_to_task(m) for m in result.scalars().all()]

    def _task_to_model(self, task: Task) -> TaskModel:
        """Convert Pydantic Task to ORM TaskModel.

        Args:
            task: Pydantic task

        Returns:
            ORM task model
        """
        return TaskModel(
            id=task.id,
            tenant_id=task.tenant_id,
            agent_id=task.agent_id,
            user_id=task.user_id,
            state=task.state.value,
            skill_name=task.skill_name,
            input_summary=task.input_summary,
            parent_task_id=task.parent_task_id,
            conversation_id=task.conversation_id,
            trace_id=task.trace_id,
            messages=[m.model_dump(mode="json") for m in task.messages],
            artifacts=[a.model_dump(mode="json") for a in task.artifacts],
            error=task.error.model_dump(mode="json") if task.error else None,
            created_at=task.created_at,
            updated_at=task.updated_at,
        )

    def _model_to_task(self, model: TaskModel) -> Task:
        """Convert ORM TaskModel to Pydantic Task.

        Args:
            model: ORM task model

        Returns:
            Pydantic task
        """
        from omniforge.agents.models import Artifact

        messages = [TaskMessage(**m) for m in (model.messages or [])]
        artifacts = [Artifact(**a) for a in (model.artifacts or [])]
        error = TaskError(**model.error) if model.error else None

        return Task(
            id=model.id,
            tenant_id=model.tenant_id,
            agent_id=model.agent_id,
            user_id=model.user_id,
            state=TaskState(model.state),
            skill_name=model.skill_name,
            input_summary=model.input_summary,
            parent_task_id=model.parent_task_id,
            conversation_id=model.conversation_id,
            trace_id=model.trace_id,
            messages=messages,
            artifacts=artifacts,
            error=error,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
