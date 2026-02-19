"""Tests for task manager."""

from datetime import datetime, timezone
from typing import AsyncIterator

import pytest

from omniforge.agents.base import BaseAgent
from omniforge.agents.events import TaskDoneEvent, TaskEvent, TaskStatusEvent
from omniforge.agents.models import (
    AgentCapabilities,
    AgentIdentity,
    AgentSkill,
    SkillInputMode,
    SkillOutputMode,
    TextPart,
)
from omniforge.storage.memory import InMemoryAgentRepository, InMemoryTaskRepository
from omniforge.tasks.manager import TaskManager
from omniforge.tasks.models import Task, TaskCreateRequest, TaskState


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

    async def process_task(self, task: Task) -> AsyncIterator[TaskEvent]:
        """Mock process_task implementation that yields test events."""
        yield TaskStatusEvent(
            task_id=task.id,
            timestamp=datetime.now(timezone.utc),
            state=TaskState.WORKING,
        )
        yield TaskDoneEvent(
            task_id=task.id,
            timestamp=datetime.now(timezone.utc),
            final_state=TaskState.COMPLETED,
        )


class TestTaskManager:
    """Tests for TaskManager class."""

    @pytest.fixture
    def task_repo(self) -> InMemoryTaskRepository:
        """Create a fresh task repository for each test."""
        return InMemoryTaskRepository()

    @pytest.fixture
    def agent_repo(self) -> InMemoryAgentRepository:
        """Create a fresh agent repository for each test."""
        return InMemoryAgentRepository()

    @pytest.fixture
    async def manager(
        self, task_repo: InMemoryTaskRepository, agent_repo: InMemoryAgentRepository
    ) -> TaskManager:
        """Create a task manager with repositories."""
        return TaskManager(task_repo, agent_repo)

    @pytest.fixture
    def sample_request(self) -> TaskCreateRequest:
        """Create a sample task creation request."""
        return TaskCreateRequest(
            message_parts=[TextPart(text="Hello, agent!")],
            tenant_id="tenant-1",
            user_id="user-1",
        )

    @pytest.mark.asyncio
    async def test_create_task_success(
        self,
        manager: TaskManager,
        agent_repo: InMemoryAgentRepository,
        sample_request: TaskCreateRequest,
    ) -> None:
        """create_task() should create a new task successfully."""
        # Register the agent first
        agent = MockAgent()
        await agent_repo.save(agent)

        task = await manager.create_task("test-agent", sample_request)

        assert task.id is not None
        assert task.agent_id == "test-agent"
        assert task.state == TaskState.SUBMITTED
        assert task.tenant_id == "tenant-1"
        assert task.user_id == "user-1"
        assert len(task.messages) == 1
        assert task.messages[0].role == "user"
        assert task.messages[0].parts[0].text == "Hello, agent!"  # type: ignore[union-attr]

    @pytest.mark.asyncio
    async def test_create_task_with_nonexistent_agent_raises_error(
        self, manager: TaskManager, sample_request: TaskCreateRequest
    ) -> None:
        """create_task() should raise ValueError if agent doesn't exist."""
        with pytest.raises(ValueError, match="does not exist"):
            await manager.create_task("test-agent", sample_request)

    @pytest.mark.asyncio
    async def test_create_task_saves_to_repository(
        self,
        manager: TaskManager,
        task_repo: InMemoryTaskRepository,
        agent_repo: InMemoryAgentRepository,
        sample_request: TaskCreateRequest,
    ) -> None:
        """create_task() should save task to repository."""
        agent = MockAgent()
        await agent_repo.save(agent)

        task = await manager.create_task("test-agent", sample_request)

        # Verify task is in repository
        retrieved = await task_repo.get(task.id)
        assert retrieved is not None
        assert retrieved.id == task.id

    @pytest.mark.asyncio
    async def test_create_task_with_parent_task_id(
        self,
        manager: TaskManager,
        agent_repo: InMemoryAgentRepository,
    ) -> None:
        """create_task() should handle parent_task_id correctly."""
        agent = MockAgent()
        await agent_repo.save(agent)

        request = TaskCreateRequest(
            message_parts=[TextPart(text="Subtask")],
            tenant_id="tenant-1",
            user_id="user-1",
            parent_task_id="parent-123",
        )

        task = await manager.create_task("test-agent", request)
        assert task.parent_task_id == "parent-123"

    @pytest.mark.asyncio
    async def test_get_task_success(
        self,
        manager: TaskManager,
        agent_repo: InMemoryAgentRepository,
        sample_request: TaskCreateRequest,
    ) -> None:
        """get_task() should retrieve an existing task."""
        agent = MockAgent()
        await agent_repo.save(agent)

        created_task = await manager.create_task("test-agent", sample_request)
        retrieved_task = await manager.get_task(created_task.id)

        assert retrieved_task.id == created_task.id
        assert retrieved_task.agent_id == created_task.agent_id

    @pytest.mark.asyncio
    async def test_get_task_with_nonexistent_id_raises_error(self, manager: TaskManager) -> None:
        """get_task() should raise ValueError for nonexistent task."""
        with pytest.raises(ValueError, match="does not exist"):
            await manager.get_task("nonexistent-id")

    @pytest.mark.asyncio
    async def test_update_task_state_success(
        self,
        manager: TaskManager,
        agent_repo: InMemoryAgentRepository,
        sample_request: TaskCreateRequest,
    ) -> None:
        """update_task_state() should update task state successfully."""
        agent = MockAgent()
        await agent_repo.save(agent)

        task = await manager.create_task("test-agent", sample_request)
        assert task.state == TaskState.SUBMITTED

        updated_task = await manager.update_task_state(task.id, TaskState.WORKING)
        assert updated_task.state == TaskState.WORKING

    @pytest.mark.asyncio
    async def test_update_task_state_with_invalid_transition_raises_error(
        self,
        manager: TaskManager,
        agent_repo: InMemoryAgentRepository,
        sample_request: TaskCreateRequest,
    ) -> None:
        """update_task_state() should raise ValueError for invalid transitions."""
        agent = MockAgent()
        await agent_repo.save(agent)

        task = await manager.create_task("test-agent", sample_request)

        # SUBMITTED -> COMPLETED is not a valid transition
        with pytest.raises(ValueError, match="Invalid state transition"):
            await manager.update_task_state(task.id, TaskState.COMPLETED)

    @pytest.mark.asyncio
    async def test_update_task_state_from_terminal_state_raises_error(
        self,
        manager: TaskManager,
        task_repo: InMemoryTaskRepository,
        agent_repo: InMemoryAgentRepository,
    ) -> None:
        """update_task_state() should not allow transitions from terminal states."""
        agent = MockAgent()
        await agent_repo.save(agent)

        # Create a task in terminal state
        now = datetime.now(timezone.utc)
        completed_task = Task(
            id="completed-task",
            agent_id="test-agent",
            state=TaskState.COMPLETED,
            messages=[],
            created_at=now,
            updated_at=now,
            tenant_id="tenant-1",
            user_id="user-1",
        )
        await task_repo.save(completed_task)

        # Try to transition from terminal state
        with pytest.raises(ValueError, match="Invalid state transition"):
            await manager.update_task_state(completed_task.id, TaskState.WORKING)

    @pytest.mark.asyncio
    async def test_update_task_state_updates_timestamp(
        self,
        manager: TaskManager,
        agent_repo: InMemoryAgentRepository,
        sample_request: TaskCreateRequest,
    ) -> None:
        """update_task_state() should update the updated_at timestamp."""
        agent = MockAgent()
        await agent_repo.save(agent)

        task = await manager.create_task("test-agent", sample_request)
        original_timestamp = task.updated_at

        updated_task = await manager.update_task_state(task.id, TaskState.WORKING)
        assert updated_task.updated_at >= original_timestamp

    @pytest.mark.asyncio
    async def test_process_task_success(
        self,
        manager: TaskManager,
        agent_repo: InMemoryAgentRepository,
        sample_request: TaskCreateRequest,
    ) -> None:
        """process_task() should delegate to agent and yield events."""
        agent = MockAgent()
        await agent_repo.save(agent)

        task = await manager.create_task("test-agent", sample_request)

        events: list[TaskEvent] = []
        async for event in manager.process_task(task):
            events.append(event)

        # MockAgent yields 2 events: status and done
        assert len(events) == 2
        assert isinstance(events[0], TaskStatusEvent)
        assert events[0].state == TaskState.WORKING  # type: ignore[union-attr]
        assert isinstance(events[1], TaskDoneEvent)
        assert events[1].final_state == TaskState.COMPLETED  # type: ignore[union-attr]

    @pytest.mark.asyncio
    async def test_process_task_with_nonexistent_agent_raises_error(
        self,
        manager: TaskManager,
        task_repo: InMemoryTaskRepository,
    ) -> None:
        """process_task() should raise ValueError if agent doesn't exist."""
        # Create task manually without agent
        now = datetime.now(timezone.utc)
        task = Task(
            id="task-123",
            agent_id="nonexistent-agent",
            state=TaskState.SUBMITTED,
            messages=[],
            created_at=now,
            updated_at=now,
            tenant_id="tenant-1",
            user_id="user-1",
        )
        await task_repo.save(task)

        with pytest.raises(ValueError, match="does not exist"):
            async for _ in manager.process_task(task):
                pass

    @pytest.mark.asyncio
    async def test_process_task_yields_events_from_agent(
        self,
        manager: TaskManager,
        agent_repo: InMemoryAgentRepository,
        sample_request: TaskCreateRequest,
    ) -> None:
        """process_task() should yield all events from agent."""
        agent = MockAgent()
        await agent_repo.save(agent)

        task = await manager.create_task("test-agent", sample_request)

        event_count = 0
        async for event in manager.process_task(task):
            assert event.task_id == task.id
            event_count += 1

        assert event_count > 0


class TestTaskManagerApplyEvent:
    """Tests for TaskManager.apply_event() static method."""

    @pytest.fixture
    def base_task(self) -> Task:
        """Create a base task in SUBMITTED state for testing."""
        now = datetime.now(timezone.utc)
        return Task(
            id="task-1",
            agent_id="agent-1",
            state=TaskState.SUBMITTED,
            messages=[],
            artifacts=[],
            created_at=now,
            updated_at=now,
            tenant_id="tenant-1",
            user_id="user-1",
        )

    def test_apply_status_event(self, base_task: Task) -> None:
        """apply_event() with TaskStatusEvent should update state and return new instance."""
        from omniforge.agents.events import TaskStatusEvent

        event = TaskStatusEvent(
            task_id="task-1", timestamp=datetime.now(timezone.utc), state=TaskState.WORKING
        )
        result = TaskManager.apply_event(base_task, event)

        assert result.state == TaskState.WORKING
        assert result is not base_task  # new instance

    def test_apply_message_event_appends_agent_message(self, base_task: Task) -> None:
        """apply_event() with TaskMessageEvent should append an agent message."""
        from omniforge.agents.events import TaskMessageEvent

        event = TaskMessageEvent(
            task_id="task-1",
            timestamp=datetime.now(timezone.utc),
            message_parts=[TextPart(text="Hello!")],
        )
        result = TaskManager.apply_event(base_task, event)

        assert len(result.messages) == 1
        assert result.messages[0].role == "agent"
        assert result.messages[0].parts[0].text == "Hello!"  # type: ignore[union-attr]

    def test_apply_message_event_does_not_mutate_original(self, base_task: Task) -> None:
        """apply_event() with TaskMessageEvent should not mutate the original task."""
        from omniforge.agents.events import TaskMessageEvent

        event = TaskMessageEvent(
            task_id="task-1",
            timestamp=datetime.now(timezone.utc),
            message_parts=[TextPart(text="Hi")],
        )
        TaskManager.apply_event(base_task, event)

        assert len(base_task.messages) == 0  # original unchanged

    def test_apply_artifact_event(self, base_task: Task) -> None:
        """apply_event() with TaskArtifactEvent should append artifact to artifacts list."""
        from omniforge.agents.events import TaskArtifactEvent
        from omniforge.agents.models import Artifact

        artifact = Artifact(id="art-1", type="document", title="Result", content="result text")
        event = TaskArtifactEvent(
            task_id="task-1", timestamp=datetime.now(timezone.utc), artifact=artifact
        )
        result = TaskManager.apply_event(base_task, event)

        assert len(result.artifacts) == 1
        assert result.artifacts[0].id == "art-1"

    def test_apply_done_event_completed(self, base_task: Task) -> None:
        """apply_event() with TaskDoneEvent(COMPLETED) should set state to COMPLETED."""
        from omniforge.agents.events import TaskDoneEvent

        event = TaskDoneEvent(
            task_id="task-1",
            timestamp=datetime.now(timezone.utc),
            final_state=TaskState.COMPLETED,
        )
        result = TaskManager.apply_event(base_task, event)

        assert result.state == TaskState.COMPLETED

    def test_apply_done_event_cancelled(self, base_task: Task) -> None:
        """apply_event() with TaskDoneEvent(CANCELLED) should set state to CANCELLED."""
        from omniforge.agents.events import TaskDoneEvent

        event = TaskDoneEvent(
            task_id="task-1",
            timestamp=datetime.now(timezone.utc),
            final_state=TaskState.CANCELLED,
        )
        result = TaskManager.apply_event(base_task, event)

        assert result.state == TaskState.CANCELLED

    def test_apply_done_event_failed_adds_generic_error(self, base_task: Task) -> None:
        """apply_event() with TaskDoneEvent(FAILED) should add a generic error."""
        from omniforge.agents.events import TaskDoneEvent

        event = TaskDoneEvent(
            task_id="task-1",
            timestamp=datetime.now(timezone.utc),
            final_state=TaskState.FAILED,
        )
        result = TaskManager.apply_event(base_task, event)

        assert result.state == TaskState.FAILED
        assert result.error is not None

    def test_apply_error_event(self, base_task: Task) -> None:
        """apply_event() with TaskErrorEvent should set state to FAILED with error details."""
        from omniforge.agents.events import TaskErrorEvent

        event = TaskErrorEvent(
            task_id="task-1",
            timestamp=datetime.now(timezone.utc),
            error_code="timeout",
            error_message="The agent timed out",
        )
        result = TaskManager.apply_event(base_task, event)

        assert result.state == TaskState.FAILED
        assert result.error is not None
        assert result.error.code == "timeout"
        assert result.error.message == "The agent timed out"

    def test_apply_unknown_event_returns_same_instance(self, base_task: Task) -> None:
        """apply_event() with an unknown event type should return the same task instance."""
        from omniforge.agents.events import BaseTaskEvent

        class UnknownEvent(BaseTaskEvent):
            type: str = "unknown"  # type: ignore[assignment]

        event = UnknownEvent(task_id="task-1", timestamp=datetime.now(timezone.utc))
        result = TaskManager.apply_event(base_task, event)

        assert result is base_task  # unchanged

    @pytest.mark.asyncio
    async def test_process_task_persists_events(self) -> None:
        """process_task() should persist task state for every event."""
        task_repo = InMemoryTaskRepository()
        agent_repo = InMemoryAgentRepository()
        manager = TaskManager(task_repo, agent_repo)

        agent = MockAgent()
        await agent_repo.save(agent)

        request = TaskCreateRequest(
            message_parts=[TextPart(text="Go")],
            tenant_id="t1",
            user_id="u1",
        )
        task = await manager.create_task("test-agent", request)
        assert task.state == TaskState.SUBMITTED

        # Consume all events
        async for _ in manager.process_task(task):
            pass

        # Task in DB should now be COMPLETED (MockAgent yields status+done)
        persisted = await task_repo.get(task.id)
        assert persisted is not None
        assert persisted.state == TaskState.COMPLETED
