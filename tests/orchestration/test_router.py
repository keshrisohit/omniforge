"""Tests for task router."""

from datetime import datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from omniforge.agents.events import TaskDoneEvent, TaskStatusEvent
from omniforge.agents.models import (
    AgentCapabilities,
    AgentCard,
    AgentIdentity,
    AgentSkill,
    Artifact,
    ArtifactType,
    SecurityConfig,
    SkillInputMode,
    SkillOutputMode,
    TextPart,
)
from omniforge.orchestration.client import A2AClient
from omniforge.orchestration.router import TaskRouter
from omniforge.storage.memory import InMemoryTaskRepository
from omniforge.tasks.models import Task, TaskError, TaskMessage, TaskState


class TestTaskRouter:
    """Tests for TaskRouter class."""

    @pytest.fixture
    def task_repo(self):
        """Create an in-memory task repository."""
        return InMemoryTaskRepository()

    @pytest.fixture
    def router(self, task_repo):
        """Create a task router instance."""
        return TaskRouter(task_repo=task_repo)

    @pytest.fixture
    def agent_card(self):
        """Create a test agent card."""
        return AgentCard(
            protocol_version="1.0",
            identity=AgentIdentity(
                id="remote-agent",
                name="Remote Agent",
                description="Remote test agent",
                version="1.0.0",
            ),
            capabilities=AgentCapabilities(streaming=True),
            skills=[
                AgentSkill(
                    id="remote-skill",
                    name="Remote Skill",
                    description="Remote agent skill",
                    input_modes=[SkillInputMode.TEXT],
                    output_modes=[SkillOutputMode.TEXT],
                )
            ],
            service_endpoint="https://remote-agent.example.com",
            security=SecurityConfig(auth_scheme="bearer", require_https=True),
        )

    @pytest.fixture
    async def parent_task(self, task_repo):
        """Create a parent task for testing."""
        task = Task(
            id=str(uuid4()),
            agent_id="parent-agent",
            state=TaskState.WORKING,
            messages=[
                TaskMessage(
                    id=str(uuid4()),
                    role="user",
                    parts=[TextPart(text="Parent task")],
                    created_at=datetime.utcnow(),
                )
            ],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            tenant_id="tenant-1",
            user_id="user-1",
        )
        await task_repo.save(task)
        return task

    @pytest.mark.asyncio
    async def test_router_context_manager(self, task_repo):
        """Router should work as async context manager."""
        async with TaskRouter(task_repo=task_repo) as router:
            assert router is not None

    @pytest.mark.asyncio
    async def test_router_close_with_owned_client(self, task_repo):
        """Router should close owned client on close."""
        router = TaskRouter(task_repo=task_repo)

        with patch.object(router._client, "close", new=AsyncMock()) as mock_close:
            await router.close()
            mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_router_close_with_external_client(self, task_repo):
        """Router should not close external client."""
        external_client = A2AClient()
        router = TaskRouter(task_repo=task_repo, client=external_client)

        with patch.object(external_client, "close", new=AsyncMock()) as mock_close:
            await router.close()
            mock_close.assert_not_called()

    @pytest.mark.asyncio
    async def test_delegate_task_sends_to_remote_agent(self, router, parent_task, agent_card):
        """Should delegate task to remote agent with parent relationship."""

        # Mock client to return events
        async def mock_send_task(*args, **kwargs):
            yield TaskStatusEvent(
                task_id="child-123",
                timestamp=datetime.utcnow(),
                state=TaskState.WORKING,
            )
            yield TaskDoneEvent(
                task_id="child-123",
                timestamp=datetime.utcnow(),
                final_state=TaskState.COMPLETED,
            )

        with patch.object(router._client, "send_task", side_effect=mock_send_task):
            events = []
            async for event in router.delegate_task(
                parent_task_id=parent_task.id,
                agent_card=agent_card,
                message_parts=[TextPart(text="Delegated task")],
                tenant_id="tenant-1",
                user_id="user-1",
            ):
                events.append(event)

            assert len(events) == 2
            assert isinstance(events[0], TaskStatusEvent)
            assert isinstance(events[1], TaskDoneEvent)

    @pytest.mark.asyncio
    async def test_delegate_task_with_nonexistent_parent_raises_error(self, router, agent_card):
        """Should raise ValueError if parent task does not exist."""
        with pytest.raises(ValueError, match="does not exist"):
            async for _ in router.delegate_task(
                parent_task_id="nonexistent-parent",
                agent_card=agent_card,
                message_parts=[TextPart(text="Test")],
                tenant_id="tenant-1",
                user_id="user-1",
            ):
                pass

    @pytest.mark.asyncio
    async def test_get_child_tasks(self, router, task_repo, parent_task):
        """Should retrieve all child tasks for a parent."""
        # Create child tasks
        child1 = Task(
            id=str(uuid4()),
            agent_id="child-agent",
            state=TaskState.COMPLETED,
            messages=[],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            tenant_id="tenant-1",
            user_id="user-1",
            parent_task_id=parent_task.id,
        )
        child2 = Task(
            id=str(uuid4()),
            agent_id="child-agent",
            state=TaskState.WORKING,
            messages=[],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            tenant_id="tenant-1",
            user_id="user-1",
            parent_task_id=parent_task.id,
        )

        await task_repo.save(child1)
        await task_repo.save(child2)

        # Get child tasks
        children = await router.get_child_tasks(parent_task.id)

        assert len(children) == 2
        child_ids = {child.id for child in children}
        assert child_ids == {child1.id, child2.id}

    @pytest.mark.asyncio
    async def test_get_child_tasks_empty(self, router, parent_task):
        """Should return empty list when parent has no children."""
        children = await router.get_child_tasks(parent_task.id)

        assert children == []

    @pytest.mark.asyncio
    async def test_get_task_hierarchy(self, router, task_repo, parent_task):
        """Should retrieve complete task hierarchy."""
        # Create child task
        child = Task(
            id=str(uuid4()),
            agent_id="child-agent",
            state=TaskState.COMPLETED,
            messages=[],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            tenant_id="tenant-1",
            user_id="user-1",
            parent_task_id=parent_task.id,
        )
        await task_repo.save(child)

        # Get hierarchy for child
        hierarchy = await router.get_task_hierarchy(child.id)

        assert hierarchy["task"].id == child.id
        assert hierarchy["parent"] is not None
        assert hierarchy["parent"].id == parent_task.id
        assert len(hierarchy["children"]) == 0

    @pytest.mark.asyncio
    async def test_get_task_hierarchy_no_parent(self, router, parent_task):
        """Should return None for parent when task has no parent."""
        hierarchy = await router.get_task_hierarchy(parent_task.id)

        assert hierarchy["task"].id == parent_task.id
        assert hierarchy["parent"] is None
        assert len(hierarchy["children"]) == 0

    @pytest.mark.asyncio
    async def test_get_task_hierarchy_nonexistent_raises_error(self, router):
        """Should raise ValueError for nonexistent task."""
        with pytest.raises(ValueError, match="does not exist"):
            await router.get_task_hierarchy("nonexistent-task")

    @pytest.mark.asyncio
    async def test_aggregate_child_results(self, router, task_repo, parent_task):
        """Should aggregate results from child tasks."""
        # Create child tasks with different states
        child1 = Task(
            id=str(uuid4()),
            agent_id="child-agent",
            state=TaskState.COMPLETED,
            messages=[],
            artifacts=[
                Artifact(
                    id="artifact-1",
                    type=ArtifactType.DOCUMENT,
                    title="Result 1",
                    inline_content="Content 1",
                    tenant_id="test-tenant",
                )
            ],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            tenant_id="tenant-1",
            user_id="user-1",
            parent_task_id=parent_task.id,
        )
        child2 = Task(
            id=str(uuid4()),
            agent_id="child-agent",
            state=TaskState.COMPLETED,
            messages=[],
            artifacts=[
                Artifact(
                    id="artifact-2",
                    type=ArtifactType.DOCUMENT,
                    title="Result 2",
                    inline_content="Content 2",
                    tenant_id="test-tenant",
                )
            ],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            tenant_id="tenant-1",
            user_id="user-1",
            parent_task_id=parent_task.id,
        )
        # Use model_construct to bypass validation order issues
        child3 = Task.model_construct(
            id=str(uuid4()),
            agent_id="child-agent",
            state=TaskState.FAILED,
            messages=[],
            artifacts=[],
            error=TaskError(code="test_error", message="Test failure"),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            tenant_id="tenant-1",
            user_id="user-1",
            parent_task_id=parent_task.id,
        )
        child4 = Task(
            id=str(uuid4()),
            agent_id="child-agent",
            state=TaskState.WORKING,
            messages=[],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            tenant_id="tenant-1",
            user_id="user-1",
            parent_task_id=parent_task.id,
        )

        await task_repo.save(child1)
        await task_repo.save(child2)
        await task_repo.save(child3)
        await task_repo.save(child4)

        # Aggregate results
        results = await router.aggregate_child_results(parent_task.id)

        assert results["total_children"] == 4
        assert results["completed"] == 2
        assert results["failed"] == 1
        assert results["in_progress"] == 1
        assert len(results["artifacts"]) == 2
        artifact_ids = {a.id for a in results["artifacts"]}
        assert artifact_ids == {"artifact-1", "artifact-2"}

    @pytest.mark.asyncio
    async def test_aggregate_child_results_no_children(self, router, parent_task):
        """Should return zero counts when parent has no children."""
        results = await router.aggregate_child_results(parent_task.id)

        assert results["total_children"] == 0
        assert results["completed"] == 0
        assert results["failed"] == 0
        assert results["in_progress"] == 0
        assert results["artifacts"] == []
