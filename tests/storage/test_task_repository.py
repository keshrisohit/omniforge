"""Tests for SQLTaskRepository."""

from datetime import datetime, timezone

import pytest

from omniforge.agents.models import TextPart
from omniforge.storage.database import Database, DatabaseConfig
from omniforge.storage.task_repository import SQLTaskRepository
from omniforge.tasks.models import Task, TaskMessage, TaskState


@pytest.fixture(scope="function")
async def db():
    """Create test database for each test."""
    config = DatabaseConfig(url="sqlite+aiosqlite:///:memory:")
    database = Database(config)
    await database.create_tables()
    yield database
    await database.close()


@pytest.fixture
async def session(db):
    """Create database session shared by repository and test."""
    async with db.session() as s:
        yield s


@pytest.fixture
def repo(session):
    """Create SQLTaskRepository using test session."""
    return SQLTaskRepository(session)


def make_task(
    task_id: str = "task-1",
    agent_id: str = "agent-1",
    tenant_id: str = "tenant-1",
    skill_name: str | None = None,
    state: TaskState = TaskState.SUBMITTED,
) -> Task:
    """Create a test task."""
    now = datetime.now(timezone.utc)
    return Task(
        id=task_id,
        agent_id=agent_id,
        tenant_id=tenant_id,
        user_id="user-1",
        state=state,
        skill_name=skill_name,
        input_summary="Test input",
        messages=[
            TaskMessage(
                id="msg-1",
                role="user",
                parts=[TextPart(text="Hello")],
                created_at=now,
            )
        ],
        created_at=now,
        updated_at=now,
    )


class TestSQLTaskRepositoryCRUD:
    """Tests for basic CRUD operations."""

    @pytest.mark.asyncio
    async def test_save_and_get(self, repo: SQLTaskRepository) -> None:
        """save() + get() round-trip should return equivalent task."""
        task = make_task()
        await repo.save(task)
        retrieved = await repo.get(task.id)
        assert retrieved is not None
        assert retrieved.id == task.id
        assert retrieved.agent_id == task.agent_id
        assert retrieved.tenant_id == task.tenant_id
        assert retrieved.state == task.state
        assert retrieved.skill_name == task.skill_name
        assert retrieved.input_summary == task.input_summary

    @pytest.mark.asyncio
    async def test_save_duplicate_raises(self, repo: SQLTaskRepository) -> None:
        """save() should raise ValueError for duplicate task IDs."""
        task = make_task()
        await repo.save(task)
        with pytest.raises(ValueError, match="already exists"):
            await repo.save(task)

    @pytest.mark.asyncio
    async def test_get_nonexistent_returns_none(self, repo: SQLTaskRepository) -> None:
        """get() should return None for nonexistent task."""
        result = await repo.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_update(self, repo: SQLTaskRepository) -> None:
        """update() should modify an existing task."""
        task = make_task()
        await repo.save(task)

        updated = task.model_copy(update={"state": TaskState.WORKING})
        await repo.update(updated)

        retrieved = await repo.get(task.id)
        assert retrieved is not None
        assert retrieved.state == TaskState.WORKING

    @pytest.mark.asyncio
    async def test_update_nonexistent_raises(self, repo: SQLTaskRepository) -> None:
        """update() should raise ValueError for nonexistent task."""
        task = make_task()
        with pytest.raises(ValueError, match="does not exist"):
            await repo.update(task)

    @pytest.mark.asyncio
    async def test_delete(self, repo: SQLTaskRepository) -> None:
        """delete() should remove a task."""
        task = make_task()
        await repo.save(task)
        await repo.delete(task.id)
        assert await repo.get(task.id) is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_raises(self, repo: SQLTaskRepository) -> None:
        """delete() should raise ValueError for nonexistent task."""
        with pytest.raises(ValueError, match="does not exist"):
            await repo.delete("nonexistent")


class TestSQLTaskRepositoryListByAgent:
    """Tests for list_by_agent."""

    @pytest.mark.asyncio
    async def test_list_by_agent_returns_only_agent_tasks(
        self, repo: SQLTaskRepository
    ) -> None:
        """list_by_agent() should only return tasks for the given agent."""
        await repo.save(make_task("t1", agent_id="agent-1"))
        await repo.save(make_task("t2", agent_id="agent-1"))
        await repo.save(make_task("t3", agent_id="agent-2"))

        tasks = await repo.list_by_agent("agent-1")
        assert len(tasks) == 2
        assert all(t.agent_id == "agent-1" for t in tasks)

    @pytest.mark.asyncio
    async def test_list_by_agent_respects_limit(self, repo: SQLTaskRepository) -> None:
        """list_by_agent() should respect limit."""
        for i in range(5):
            await repo.save(make_task(f"t{i}"))
        tasks = await repo.list_by_agent("agent-1", limit=3)
        assert len(tasks) == 3


class TestSQLTaskRepositoryTenantIsolation:
    """Tests for multi-tenancy enforcement in list_by_tenant."""

    @pytest.mark.asyncio
    async def test_list_by_tenant_isolates_tenants(
        self, repo: SQLTaskRepository
    ) -> None:
        """list_by_tenant() must not return tasks from other tenants."""
        await repo.save(make_task("t1", tenant_id="tenant-a"))
        await repo.save(make_task("t2", tenant_id="tenant-a"))
        await repo.save(make_task("t3", tenant_id="tenant-b"))

        tenant_a_tasks = await repo.list_by_tenant("tenant-a")
        assert len(tenant_a_tasks) == 2
        assert all(t.tenant_id == "tenant-a" for t in tenant_a_tasks)

        tenant_b_tasks = await repo.list_by_tenant("tenant-b")
        assert len(tenant_b_tasks) == 1
        assert tenant_b_tasks[0].id == "t3"

    @pytest.mark.asyncio
    async def test_list_by_tenant_pagination(self, repo: SQLTaskRepository) -> None:
        """list_by_tenant() should support offset/limit pagination."""
        now = datetime.now(timezone.utc)
        from datetime import timedelta

        for i in range(5):
            t = make_task(f"t{i}")
            # Stagger created_at for deterministic ordering
            t = t.model_copy(update={"created_at": now - timedelta(seconds=i)})
            await repo.save(t)

        page1 = await repo.list_by_tenant("tenant-1", limit=2, offset=0)
        page2 = await repo.list_by_tenant("tenant-1", limit=2, offset=2)
        assert len(page1) == 2
        assert len(page2) == 2
        # No overlap
        assert {t.id for t in page1}.isdisjoint({t.id for t in page2})

    @pytest.mark.asyncio
    async def test_list_by_tenant_empty(self, repo: SQLTaskRepository) -> None:
        """list_by_tenant() should return empty list for unknown tenant."""
        result = await repo.list_by_tenant("unknown-tenant")
        assert result == []


class TestSQLTaskRepositoryListBySkill:
    """Tests for list_by_skill."""

    @pytest.mark.asyncio
    async def test_list_by_skill_filters_correctly(
        self, repo: SQLTaskRepository
    ) -> None:
        """list_by_skill() should filter by both tenant and skill."""
        await repo.save(make_task("t1", skill_name="invoice-extraction"))
        await repo.save(make_task("t2", skill_name="invoice-extraction"))
        await repo.save(make_task("t3", skill_name="chat"))
        # Same skill, different tenant — must NOT appear
        await repo.save(
            make_task("t4", tenant_id="tenant-2", skill_name="invoice-extraction")
        )

        tasks = await repo.list_by_skill("tenant-1", "invoice-extraction")
        assert len(tasks) == 2
        assert all(t.skill_name == "invoice-extraction" for t in tasks)
        assert all(t.tenant_id == "tenant-1" for t in tasks)

    @pytest.mark.asyncio
    async def test_list_by_skill_respects_limit(self, repo: SQLTaskRepository) -> None:
        """list_by_skill() should respect limit."""
        for i in range(5):
            await repo.save(make_task(f"t{i}", skill_name="chat"))
        tasks = await repo.list_by_skill("tenant-1", "chat", limit=3)
        assert len(tasks) == 3

    @pytest.mark.asyncio
    async def test_list_by_skill_no_cross_tenant(self, repo: SQLTaskRepository) -> None:
        """list_by_skill() must never return tasks from other tenants."""
        await repo.save(
            make_task("t1", tenant_id="tenant-a", skill_name="invoice-extraction")
        )
        await repo.save(
            make_task("t2", tenant_id="tenant-b", skill_name="invoice-extraction")
        )

        result = await repo.list_by_skill("tenant-a", "invoice-extraction")
        assert len(result) == 1
        assert result[0].id == "t1"
