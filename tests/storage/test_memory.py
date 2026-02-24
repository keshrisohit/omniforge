"""Tests for in-memory repository implementations."""

from datetime import datetime, timezone

import pytest

from omniforge.agents.base import BaseAgent
from omniforge.agents.events import TaskEvent
from omniforge.agents.models import (
    AgentCapabilities,
    AgentIdentity,
    AgentSkill,
    SkillInputMode,
    SkillOutputMode,
    TextPart,
)
from omniforge.storage.memory import InMemoryAgentRepository, InMemoryTaskRepository
from omniforge.tasks.models import Task, TaskMessage, TaskState


class MockAgent(BaseAgent):
    """Mock agent for testing."""

    identity = AgentIdentity(
        id="test-agent",
        name="Test Agent",
        description="A test agent",
        version="1.0.0",
    )
    capabilities = AgentCapabilities(streaming=True)
    skills = [
        AgentSkill(
            id="test-skill",
            name="Test Skill",
            description="A test skill",
            input_modes=[SkillInputMode.TEXT],
            output_modes=[SkillOutputMode.TEXT],
        )
    ]

    async def process_task(self, task: Task) -> TaskEvent:
        """Mock process_task implementation."""
        if False:  # pragma: no cover
            yield  # type: ignore[unreachable]


class TestInMemoryTaskRepository:
    """Tests for InMemoryTaskRepository."""

    @pytest.fixture
    def repo(self) -> InMemoryTaskRepository:
        """Create a fresh task repository for each test."""
        return InMemoryTaskRepository()

    @pytest.fixture
    def sample_task(self) -> Task:
        """Create a sample task for testing."""
        now = datetime.now(timezone.utc)
        return Task(
            id="task-123",
            agent_id="agent-1",
            state=TaskState.SUBMITTED,
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
            tenant_id="tenant-1",
            user_id="user-1",
        )

    @pytest.mark.asyncio
    async def test_save_task(self, repo: InMemoryTaskRepository, sample_task: Task) -> None:
        """save() should store a task successfully."""
        await repo.save(sample_task)
        retrieved = await repo.get(sample_task.id)
        assert retrieved == sample_task

    @pytest.mark.asyncio
    async def test_save_duplicate_task_raises_error(
        self, repo: InMemoryTaskRepository, sample_task: Task
    ) -> None:
        """save() should raise ValueError for duplicate task IDs."""
        await repo.save(sample_task)
        with pytest.raises(ValueError, match="already exists"):
            await repo.save(sample_task)

    @pytest.mark.asyncio
    async def test_get_nonexistent_task_returns_none(self, repo: InMemoryTaskRepository) -> None:
        """get() should return None for nonexistent task."""
        result = await repo.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_update_task(self, repo: InMemoryTaskRepository, sample_task: Task) -> None:
        """update() should modify an existing task."""
        await repo.save(sample_task)

        updated_task = sample_task.model_copy(update={"state": TaskState.WORKING})
        await repo.update(updated_task)

        retrieved = await repo.get(sample_task.id)
        assert retrieved is not None
        assert retrieved.state == TaskState.WORKING

    @pytest.mark.asyncio
    async def test_update_nonexistent_task_raises_error(
        self, repo: InMemoryTaskRepository, sample_task: Task
    ) -> None:
        """update() should raise ValueError for nonexistent task."""
        with pytest.raises(ValueError, match="does not exist"):
            await repo.update(sample_task)

    @pytest.mark.asyncio
    async def test_delete_task(self, repo: InMemoryTaskRepository, sample_task: Task) -> None:
        """delete() should remove a task."""
        await repo.save(sample_task)
        await repo.delete(sample_task.id)

        result = await repo.get(sample_task.id)
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_task_raises_error(self, repo: InMemoryTaskRepository) -> None:
        """delete() should raise ValueError for nonexistent task."""
        with pytest.raises(ValueError, match="does not exist"):
            await repo.delete("nonexistent")

    @pytest.mark.asyncio
    async def test_list_by_agent(self, repo: InMemoryTaskRepository) -> None:
        """list_by_agent() should return tasks for specific agent."""
        now = datetime.now(timezone.utc)

        # Create tasks for different agents
        task1 = Task(
            id="task-1",
            agent_id="agent-1",
            state=TaskState.SUBMITTED,
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
            tenant_id="tenant-1",
            user_id="user-1",
        )
        task2 = Task(
            id="task-2",
            agent_id="agent-1",
            state=TaskState.WORKING,
            messages=[
                TaskMessage(
                    id="msg-2",
                    role="user",
                    parts=[TextPart(text="Hi")],
                    created_at=now,
                )
            ],
            created_at=now,
            updated_at=now,
            tenant_id="tenant-1",
            user_id="user-1",
        )
        task3 = Task(
            id="task-3",
            agent_id="agent-2",
            state=TaskState.COMPLETED,
            messages=[
                TaskMessage(
                    id="msg-3",
                    role="user",
                    parts=[TextPart(text="Test")],
                    created_at=now,
                )
            ],
            created_at=now,
            updated_at=now,
            tenant_id="tenant-1",
            user_id="user-1",
        )

        await repo.save(task1)
        await repo.save(task2)
        await repo.save(task3)

        # List tasks for agent-1
        agent1_tasks = await repo.list_by_agent("agent-1")
        assert len(agent1_tasks) == 2
        assert all(t.agent_id == "agent-1" for t in agent1_tasks)

        # List tasks for agent-2
        agent2_tasks = await repo.list_by_agent("agent-2")
        assert len(agent2_tasks) == 1
        assert agent2_tasks[0].id == "task-3"

    @pytest.mark.asyncio
    async def test_list_by_agent_respects_limit(self, repo: InMemoryTaskRepository) -> None:
        """list_by_agent() should respect limit parameter."""
        now = datetime.now(timezone.utc)

        # Create multiple tasks for same agent
        for i in range(5):
            task = Task(
                id=f"task-{i}",
                agent_id="agent-1",
                state=TaskState.SUBMITTED,
                messages=[
                    TaskMessage(
                        id=f"msg-{i}",
                        role="user",
                        parts=[TextPart(text="Hello")],
                        created_at=now,
                    )
                ],
                created_at=now,
                updated_at=now,
                tenant_id="tenant-1",
                user_id="user-1",
            )
            await repo.save(task)

        # List with limit
        tasks = await repo.list_by_agent("agent-1", limit=3)
        assert len(tasks) == 3

    @pytest.mark.asyncio
    async def test_list_by_agent_orders_by_created_at_desc(
        self, repo: InMemoryTaskRepository
    ) -> None:
        """list_by_agent() should return tasks ordered by created_at descending."""
        base_time = datetime.now(timezone.utc)

        # Create tasks with different timestamps
        task1 = Task(
            id="task-1",
            agent_id="agent-1",
            state=TaskState.SUBMITTED,
            messages=[
                TaskMessage(
                    id="msg-1",
                    role="user",
                    parts=[TextPart(text="First")],
                    created_at=base_time,
                )
            ],
            created_at=base_time,
            updated_at=base_time,
            tenant_id="tenant-1",
            user_id="user-1",
        )
        task2 = Task(
            id="task-2",
            agent_id="agent-1",
            state=TaskState.SUBMITTED,
            messages=[
                TaskMessage(
                    id="msg-2",
                    role="user",
                    parts=[TextPart(text="Second")],
                    created_at=base_time,
                )
            ],
            created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
            updated_at=base_time,
            tenant_id="tenant-1",
            user_id="user-1",
        )

        await repo.save(task1)
        await repo.save(task2)

        tasks = await repo.list_by_agent("agent-1")
        # Most recent (base_time) should be first
        assert tasks[0].id == "task-1"
        assert tasks[1].id == "task-2"

    @pytest.mark.asyncio
    async def test_list_by_tenant(self, repo: InMemoryTaskRepository) -> None:
        """list_by_tenant() should return only tasks for the given tenant."""
        now = datetime.now(timezone.utc)

        def make(task_id: str, tenant: str) -> Task:
            return Task(
                id=task_id,
                agent_id="agent-1",
                state=TaskState.SUBMITTED,
                messages=[
                    TaskMessage(
                        id="msg-1",
                        role="user",
                        parts=[TextPart(text="Hi")],
                        created_at=now,
                    )
                ],
                created_at=now,
                updated_at=now,
                tenant_id=tenant,
                user_id="user-1",
            )

        await repo.save(make("t1", "tenant-a"))
        await repo.save(make("t2", "tenant-a"))
        await repo.save(make("t3", "tenant-b"))

        result_a = await repo.list_by_tenant("tenant-a")
        assert len(result_a) == 2
        assert all(t.tenant_id == "tenant-a" for t in result_a)

        result_b = await repo.list_by_tenant("tenant-b")
        assert len(result_b) == 1
        assert result_b[0].id == "t3"

    @pytest.mark.asyncio
    async def test_list_by_tenant_pagination(self, repo: InMemoryTaskRepository) -> None:
        """list_by_tenant() should support offset/limit pagination."""
        from datetime import timedelta

        now = datetime.now(timezone.utc)
        for i in range(5):
            t = Task(
                id=f"t{i}",
                agent_id="agent-1",
                state=TaskState.SUBMITTED,
                messages=[
                    TaskMessage(
                        id=f"msg-{i}",
                        role="user",
                        parts=[TextPart(text="Hi")],
                        created_at=now,
                    )
                ],
                created_at=now - timedelta(seconds=i),
                updated_at=now,
                tenant_id="tenant-1",
                user_id="user-1",
            )
            await repo.save(t)

        page1 = await repo.list_by_tenant("tenant-1", limit=2, offset=0)
        page2 = await repo.list_by_tenant("tenant-1", limit=2, offset=2)
        assert len(page1) == 2
        assert len(page2) == 2
        assert {t.id for t in page1}.isdisjoint({t.id for t in page2})

    @pytest.mark.asyncio
    async def test_list_by_skill(self, repo: InMemoryTaskRepository) -> None:
        """list_by_skill() should filter by tenant AND skill name."""
        now = datetime.now(timezone.utc)

        def make(task_id: str, tenant: str, skill: str | None) -> Task:
            return Task(
                id=task_id,
                agent_id="agent-1",
                state=TaskState.SUBMITTED,
                messages=[
                    TaskMessage(
                        id="msg-1",
                        role="user",
                        parts=[TextPart(text="Hi")],
                        created_at=now,
                    )
                ],
                created_at=now,
                updated_at=now,
                tenant_id=tenant,
                user_id="user-1",
                skill_name=skill,
            )

        await repo.save(make("t1", "tenant-1", "invoice-extraction"))
        await repo.save(make("t2", "tenant-1", "invoice-extraction"))
        await repo.save(make("t3", "tenant-1", "chat"))
        # Different tenant, same skill — must NOT be returned
        await repo.save(make("t4", "tenant-2", "invoice-extraction"))

        result = await repo.list_by_skill("tenant-1", "invoice-extraction")
        assert len(result) == 2
        assert all(t.skill_name == "invoice-extraction" for t in result)
        assert all(t.tenant_id == "tenant-1" for t in result)

    @pytest.mark.asyncio
    async def test_list_by_skill_respects_limit(self, repo: InMemoryTaskRepository) -> None:
        """list_by_skill() should respect limit parameter."""
        now = datetime.now(timezone.utc)
        for i in range(5):
            t = Task(
                id=f"t{i}",
                agent_id="agent-1",
                state=TaskState.SUBMITTED,
                messages=[
                    TaskMessage(
                        id=f"msg-{i}",
                        role="user",
                        parts=[TextPart(text="Hi")],
                        created_at=now,
                    )
                ],
                created_at=now,
                updated_at=now,
                tenant_id="tenant-1",
                user_id="user-1",
                skill_name="chat",
            )
            await repo.save(t)

        result = await repo.list_by_skill("tenant-1", "chat", limit=3)
        assert len(result) == 3


class TestInMemoryAgentRepository:
    """Tests for InMemoryAgentRepository."""

    @pytest.fixture
    def repo(self) -> InMemoryAgentRepository:
        """Create a fresh agent repository for each test."""
        return InMemoryAgentRepository()

    @pytest.fixture
    def sample_agent(self) -> MockAgent:
        """Create a sample agent for testing."""
        return MockAgent()

    @pytest.mark.asyncio
    async def test_save_agent(self, repo: InMemoryAgentRepository, sample_agent: MockAgent) -> None:
        """save() should store an agent successfully."""
        await repo.save(sample_agent)
        retrieved = await repo.get(sample_agent.identity.id)
        assert retrieved == sample_agent

    @pytest.mark.asyncio
    async def test_save_duplicate_agent_raises_error(
        self, repo: InMemoryAgentRepository, sample_agent: MockAgent
    ) -> None:
        """save() should raise ValueError for duplicate agent IDs."""
        await repo.save(sample_agent)
        with pytest.raises(ValueError, match="already exists"):
            await repo.save(sample_agent)

    @pytest.mark.asyncio
    async def test_get_nonexistent_agent_returns_none(self, repo: InMemoryAgentRepository) -> None:
        """get() should return None for nonexistent agent."""
        result = await repo.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_agent(
        self, repo: InMemoryAgentRepository, sample_agent: MockAgent
    ) -> None:
        """delete() should remove an agent."""
        await repo.save(sample_agent)
        await repo.delete(sample_agent.identity.id)

        result = await repo.get(sample_agent.identity.id)
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_agent_raises_error(
        self, repo: InMemoryAgentRepository
    ) -> None:
        """delete() should raise ValueError for nonexistent agent."""
        with pytest.raises(ValueError, match="does not exist"):
            await repo.delete("nonexistent")

    @pytest.mark.asyncio
    async def test_list_all(self, repo: InMemoryAgentRepository) -> None:
        """list_all() should return all agents."""
        agent1 = MockAgent()
        agent1.identity = AgentIdentity(
            id="agent-1", name="Agent 1", description="First", version="1.0.0"
        )

        agent2 = MockAgent()
        agent2.identity = AgentIdentity(
            id="agent-2", name="Agent 2", description="Second", version="1.0.0"
        )

        await repo.save(agent1)
        await repo.save(agent2)

        agents = await repo.list_all()
        assert len(agents) == 2

    @pytest.mark.asyncio
    async def test_list_all_respects_limit(self, repo: InMemoryAgentRepository) -> None:
        """list_all() should respect limit parameter."""
        for i in range(5):
            agent = MockAgent()
            agent.identity = AgentIdentity(
                id=f"agent-{i}",
                name=f"Agent {i}",
                description="Test",
                version="1.0.0",
            )
            await repo.save(agent)

        agents = await repo.list_all(limit=3)
        assert len(agents) == 3

    @pytest.mark.asyncio
    async def test_list_by_tenant(self, repo: InMemoryAgentRepository) -> None:
        """list_by_tenant() should return agents for specific tenant."""
        agent1 = MockAgent()
        agent1.identity = AgentIdentity(
            id="agent-1", name="Agent 1", description="First", version="1.0.0"
        )
        agent1.tenant_id = "tenant-1"  # type: ignore[attr-defined]

        agent2 = MockAgent()
        agent2.identity = AgentIdentity(
            id="agent-2", name="Agent 2", description="Second", version="1.0.0"
        )
        agent2.tenant_id = "tenant-1"  # type: ignore[attr-defined]

        agent3 = MockAgent()
        agent3.identity = AgentIdentity(
            id="agent-3", name="Agent 3", description="Third", version="1.0.0"
        )
        agent3.tenant_id = "tenant-2"  # type: ignore[attr-defined]

        await repo.save(agent1)
        await repo.save(agent2)
        await repo.save(agent3)

        tenant1_agents = await repo.list_by_tenant("tenant-1")
        assert len(tenant1_agents) == 2
        assert all(a.tenant_id == "tenant-1" for a in tenant1_agents)  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_list_by_tenant_respects_limit(self, repo: InMemoryAgentRepository) -> None:
        """list_by_tenant() should respect limit parameter."""
        for i in range(5):
            agent = MockAgent()
            agent.identity = AgentIdentity(
                id=f"agent-{i}",
                name=f"Agent {i}",
                description="Test",
                version="1.0.0",
            )
            agent.tenant_id = "tenant-1"  # type: ignore[attr-defined]
            await repo.save(agent)

        agents = await repo.list_by_tenant("tenant-1", limit=3)
        assert len(agents) == 3
