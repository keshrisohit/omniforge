"""Integration tests for task API routes.

This module tests the task management endpoints including task creation,
status retrieval, message sending, cancellation, and listing.
"""

from typing import AsyncIterator

import pytest
from fastapi.testclient import TestClient

from omniforge.agents.base import BaseAgent
from omniforge.agents.events import (
    TaskDoneEvent,
    TaskEvent,
    TaskMessageEvent,
    TaskStatusEvent,
)
from omniforge.agents.models import (
    AgentCapabilities,
    AgentIdentity,
    AgentSkill,
    SkillInputMode,
    SkillOutputMode,
    TextPart,
)
from omniforge.api.app import create_app
from omniforge.api.routes.agents import _agent_repository
from omniforge.api.routes.tasks import _task_repository
from omniforge.tasks.models import Task, TaskState


class TestAgent(BaseAgent):
    """Test agent for API testing."""

    identity = AgentIdentity(
        id="test-agent",
        name="Test Agent",
        description="A test agent for API testing",
        version="1.0.0",
    )
    capabilities = AgentCapabilities(streaming=True, multi_turn=True)
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
        """Process a task and return events."""
        from datetime import datetime

        yield TaskStatusEvent(
            task_id=task.id,
            timestamp=datetime.utcnow(),
            state=TaskState.WORKING,
        )
        yield TaskMessageEvent(
            task_id=task.id,
            timestamp=datetime.utcnow(),
            message_parts=[TextPart(text="Hello from agent")],
            is_partial=False,
        )
        yield TaskDoneEvent(
            task_id=task.id,
            timestamp=datetime.utcnow(),
            final_state=TaskState.COMPLETED,
        )


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI app.

    Returns:
        TestClient configured with the FastAPI app
    """
    app = create_app()
    return TestClient(app)


@pytest.fixture
async def registered_agent() -> AsyncIterator[TestAgent]:
    """Create and register a test agent.

    Yields:
        TestAgent instance that is registered in the repository
    """
    # Clear task repository before each test to prevent data leakage
    _task_repository._tasks.clear()

    agent = TestAgent()
    await _agent_repository.save(agent)
    yield agent
    # Cleanup
    await _agent_repository.delete("test-agent")
    _task_repository._tasks.clear()


class TestCreateTask:
    """Tests for the task creation endpoint."""

    @pytest.mark.asyncio
    async def test_create_task_returns_sse_stream(
        self, client: TestClient, registered_agent: TestAgent
    ) -> None:
        """Task creation should return SSE stream with proper headers."""
        response = client.post(
            "/api/v1/agents/test-agent/tasks",
            json={
                "message_parts": [{"type": "text", "text": "Hello"}],
                "tenant_id": "tenant-1",
                "user_id": "user-1",
            },
            headers={"Accept": "text/event-stream"},
        )

        assert response.status_code == 200
        assert response.headers["Content-Type"] == "text/event-stream; charset=utf-8"
        assert response.headers["Cache-Control"] == "no-cache"
        assert response.headers["Connection"] == "keep-alive"
        assert response.headers["X-Accel-Buffering"] == "no"

    @pytest.mark.asyncio
    async def test_create_task_streams_events(
        self, client: TestClient, registered_agent: TestAgent
    ) -> None:
        """Task creation should stream task events."""
        response = client.post(
            "/api/v1/agents/test-agent/tasks",
            json={
                "message_parts": [{"type": "text", "text": "Hello"}],
                "tenant_id": "tenant-1",
                "user_id": "user-1",
            },
            headers={"Accept": "text/event-stream"},
        )

        content = response.text
        assert "event: status" in content
        assert "event: message" in content
        assert "event: done" in content
        assert "working" in content
        assert "completed" in content

    def test_create_task_agent_not_found(self, client: TestClient) -> None:
        """Creating task for non-existent agent should return 404."""
        response = client.post(
            "/api/v1/agents/nonexistent-agent/tasks",
            json={
                "message_parts": [{"type": "text", "text": "Hello"}],
                "tenant_id": "tenant-1",
                "user_id": "user-1",
            },
        )

        assert response.status_code == 404
        data = response.json()
        assert data["code"] == "agent_not_found"

    @pytest.mark.asyncio
    async def test_create_task_invalid_request(
        self, client: TestClient, registered_agent: TestAgent
    ) -> None:
        """Creating task with invalid request should return 422 (FastAPI validation)."""
        response = client.post(
            "/api/v1/agents/test-agent/tasks",
            json={
                "message_parts": [],  # Empty parts - invalid
                "tenant_id": "tenant-1",
                "user_id": "user-1",
            },
        )

        # FastAPI returns 422 for Pydantic validation errors
        assert response.status_code == 422


class TestGetTaskStatus:
    """Tests for the task status retrieval endpoint."""

    @pytest.mark.asyncio
    async def test_get_task_status_returns_task_info(
        self, client: TestClient, registered_agent: TestAgent
    ) -> None:
        """Task status endpoint should return task information."""
        from datetime import datetime
        from uuid import uuid4

        from omniforge.tasks.models import TaskMessage

        # Create a task manually
        task_id = str(uuid4())
        task = Task(
            id=task_id,
            agent_id="test-agent",
            state=TaskState.COMPLETED,
            messages=[
                TaskMessage(
                    id=str(uuid4()),
                    role="user",
                    parts=[TextPart(text="Hello")],
                    created_at=datetime.utcnow(),
                )
            ],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            tenant_id="tenant-1",
            user_id="user-1",
        )
        await _task_repository.save(task)

        response = client.get(f"/api/v1/agents/test-agent/tasks/{task_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == task_id
        assert data["agent_id"] == "test-agent"
        assert data["state"] == "completed"
        assert "created_at" in data
        assert "updated_at" in data
        assert data["message_count"] == 1
        assert "skill_name" in data
        assert "input_summary" in data
        assert "trace_id" in data

        # Cleanup
        await _task_repository.delete(task_id)

    def test_get_task_status_not_found(self, client: TestClient) -> None:
        """Getting non-existent task should return 404."""
        response = client.get("/api/v1/agents/test-agent/tasks/nonexistent-task")

        assert response.status_code == 404
        data = response.json()
        assert data["code"] == "task_not_found"


class TestSendMessage:
    """Tests for the send message endpoint."""

    @pytest.mark.asyncio
    async def test_send_message_returns_sse_stream(
        self, client: TestClient, registered_agent: TestAgent
    ) -> None:
        """Send message should return SSE stream."""
        from datetime import datetime
        from uuid import uuid4

        from omniforge.tasks.models import TaskMessage

        # Create a task in working state
        task_id = str(uuid4())
        task = Task(
            id=task_id,
            agent_id="test-agent",
            state=TaskState.WORKING,
            messages=[
                TaskMessage(
                    id=str(uuid4()),
                    role="user",
                    parts=[TextPart(text="Hello")],
                    created_at=datetime.utcnow(),
                )
            ],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            tenant_id="tenant-1",
            user_id="user-1",
        )
        await _task_repository.save(task)

        response = client.post(
            f"/api/v1/agents/test-agent/tasks/{task_id}/send",
            json={"message_parts": [{"type": "text", "text": "Continue"}]},
            headers={"Accept": "text/event-stream"},
        )

        assert response.status_code == 200
        assert response.headers["Content-Type"] == "text/event-stream; charset=utf-8"

        # Cleanup
        await _task_repository.delete(task_id)

    @pytest.mark.asyncio
    async def test_send_message_terminal_state_fails(
        self, client: TestClient, registered_agent: TestAgent
    ) -> None:
        """Sending message to completed task should fail."""
        from datetime import datetime
        from uuid import uuid4

        from omniforge.tasks.models import TaskMessage

        # Create a task in completed state
        task_id = str(uuid4())
        task = Task(
            id=task_id,
            agent_id="test-agent",
            state=TaskState.COMPLETED,
            messages=[
                TaskMessage(
                    id=str(uuid4()),
                    role="user",
                    parts=[TextPart(text="Hello")],
                    created_at=datetime.utcnow(),
                )
            ],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            tenant_id="tenant-1",
            user_id="user-1",
        )
        await _task_repository.save(task)

        response = client.post(
            f"/api/v1/agents/test-agent/tasks/{task_id}/send",
            json={"message_parts": [{"type": "text", "text": "Continue"}]},
        )

        assert response.status_code == 409
        data = response.json()
        assert data["code"] == "task_state_error"

        # Cleanup
        await _task_repository.delete(task_id)


class TestCancelTask:
    """Tests for the task cancellation endpoint."""

    @pytest.mark.asyncio
    async def test_cancel_task_success(
        self, client: TestClient, registered_agent: TestAgent
    ) -> None:
        """Cancelling a working task should succeed."""
        from datetime import datetime
        from uuid import uuid4

        from omniforge.tasks.models import TaskMessage

        # Create a task in working state
        task_id = str(uuid4())
        task = Task(
            id=task_id,
            agent_id="test-agent",
            state=TaskState.WORKING,
            messages=[
                TaskMessage(
                    id=str(uuid4()),
                    role="user",
                    parts=[TextPart(text="Hello")],
                    created_at=datetime.utcnow(),
                )
            ],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            tenant_id="tenant-1",
            user_id="user-1",
        )
        await _task_repository.save(task)

        response = client.post(f"/api/v1/agents/test-agent/tasks/{task_id}/cancel")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == task_id
        assert data["state"] == "cancelled"

        # Cleanup
        await _task_repository.delete(task_id)

    @pytest.mark.asyncio
    async def test_cancel_terminal_task_fails(
        self, client: TestClient, registered_agent: TestAgent
    ) -> None:
        """Cancelling a completed task should fail."""
        from datetime import datetime
        from uuid import uuid4

        from omniforge.tasks.models import TaskMessage

        # Create a task in completed state
        task_id = str(uuid4())
        task = Task(
            id=task_id,
            agent_id="test-agent",
            state=TaskState.COMPLETED,
            messages=[
                TaskMessage(
                    id=str(uuid4()),
                    role="user",
                    parts=[TextPart(text="Hello")],
                    created_at=datetime.utcnow(),
                )
            ],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            tenant_id="tenant-1",
            user_id="user-1",
        )
        await _task_repository.save(task)

        response = client.post(f"/api/v1/agents/test-agent/tasks/{task_id}/cancel")

        assert response.status_code == 409
        data = response.json()
        assert data["code"] == "task_state_error"

        # Cleanup
        await _task_repository.delete(task_id)


class TestListTasks:
    """Tests for the task listing endpoint."""

    def test_list_tasks_agent_not_found(self, client: TestClient) -> None:
        """Listing tasks for non-existent agent should return 404."""
        response = client.get("/api/v1/agents/nonexistent-agent/tasks")

        assert response.status_code == 404
        data = response.json()
        assert data["code"] == "agent_not_found"

    @pytest.mark.asyncio
    async def test_list_tasks_empty(self, client: TestClient, registered_agent: TestAgent) -> None:
        """Listing tasks should return empty list when no tasks exist."""
        response = client.get("/api/v1/agents/test-agent/tasks")

        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_list_tasks_with_tasks(
        self, client: TestClient, registered_agent: TestAgent
    ) -> None:
        """Listing tasks should return all tasks for agent."""
        from datetime import datetime
        from uuid import uuid4

        from omniforge.tasks.models import TaskMessage

        # Create two tasks
        task1_id = str(uuid4())
        task1 = Task(
            id=task1_id,
            agent_id="test-agent",
            state=TaskState.COMPLETED,
            messages=[
                TaskMessage(
                    id=str(uuid4()),
                    role="user",
                    parts=[TextPart(text="Hello")],
                    created_at=datetime.utcnow(),
                )
            ],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            tenant_id="tenant-1",
            user_id="user-1",
        )
        await _task_repository.save(task1)

        task2_id = str(uuid4())
        task2 = Task(
            id=task2_id,
            agent_id="test-agent",
            state=TaskState.WORKING,
            messages=[
                TaskMessage(
                    id=str(uuid4()),
                    role="user",
                    parts=[TextPart(text="World")],
                    created_at=datetime.utcnow(),
                )
            ],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            tenant_id="tenant-1",
            user_id="user-1",
        )
        await _task_repository.save(task2)

        response = client.get("/api/v1/agents/test-agent/tasks")

        assert response.status_code == 200
        tasks = response.json()
        assert len(tasks) == 2

        # Verify task data
        task_ids = [t["id"] for t in tasks]
        assert task1_id in task_ids
        assert task2_id in task_ids

        # Verify new fields present
        for t in tasks:
            assert "skill_name" in t
            assert "input_summary" in t

        # Cleanup
        await _task_repository.delete(task1_id)
        await _task_repository.delete(task2_id)


class TestTenantTaskList:
    """Tests for the GET /api/v1/tasks tenant-scoped endpoint."""

    @pytest.mark.asyncio
    async def test_list_tenant_tasks_returns_only_tenant_tasks(
        self, client: TestClient, registered_agent: TestAgent
    ) -> None:
        """GET /api/v1/tasks should return only tasks for the current tenant."""
        from datetime import datetime
        from uuid import uuid4

        from omniforge.tasks.models import TaskMessage

        now = datetime.utcnow()

        def make(task_id: str, tenant: str, skill: str | None = None) -> Task:
            return Task(
                id=task_id,
                agent_id="test-agent",
                state=TaskState.COMPLETED,
                messages=[
                    TaskMessage(
                        id=str(uuid4()),
                        role="user",
                        parts=[TextPart(text="Hello")],
                        created_at=now,
                    )
                ],
                created_at=now,
                updated_at=now,
                tenant_id=tenant,
                user_id="user-1",
                skill_name=skill,
            )

        t1 = make(str(uuid4()), "tenant-1", skill="chat")
        t2 = make(str(uuid4()), "tenant-1", skill="invoice-extraction")
        t3 = make(str(uuid4()), "tenant-2")

        await _task_repository.save(t1)
        await _task_repository.save(t2)
        await _task_repository.save(t3)

        # Request with tenant-1 header
        response = client.get(
            "/api/v1/tasks",
            headers={"X-Tenant-ID": "tenant-1"},
        )

        assert response.status_code == 200
        tasks = response.json()
        returned_ids = {t["id"] for t in tasks}
        assert t1.id in returned_ids
        assert t2.id in returned_ids
        assert t3.id not in returned_ids

        # Cleanup
        await _task_repository.delete(t1.id)
        await _task_repository.delete(t2.id)
        await _task_repository.delete(t3.id)

    @pytest.mark.asyncio
    async def test_list_tenant_tasks_skill_filter(
        self, client: TestClient, registered_agent: TestAgent
    ) -> None:
        """GET /api/v1/tasks?skill_name= should filter by skill."""
        from datetime import datetime
        from uuid import uuid4

        from omniforge.tasks.models import TaskMessage

        now = datetime.utcnow()

        def make(task_id: str, skill: str | None) -> Task:
            return Task(
                id=task_id,
                agent_id="test-agent",
                state=TaskState.COMPLETED,
                messages=[
                    TaskMessage(
                        id=str(uuid4()),
                        role="user",
                        parts=[TextPart(text="Hello")],
                        created_at=now,
                    )
                ],
                created_at=now,
                updated_at=now,
                tenant_id="tenant-1",
                user_id="user-1",
                skill_name=skill,
            )

        t1 = make(str(uuid4()), "chat")
        t2 = make(str(uuid4()), "chat")
        t3 = make(str(uuid4()), "invoice-extraction")

        await _task_repository.save(t1)
        await _task_repository.save(t2)
        await _task_repository.save(t3)

        response = client.get(
            "/api/v1/tasks?skill_name=chat",
            headers={"X-Tenant-ID": "tenant-1"},
        )

        assert response.status_code == 200
        tasks = response.json()
        assert len(tasks) == 2
        assert all(t["skill_name"] == "chat" for t in tasks)

        # Cleanup
        await _task_repository.delete(t1.id)
        await _task_repository.delete(t2.id)
        await _task_repository.delete(t3.id)

    def test_list_tenant_tasks_no_tenant_returns_empty(
        self, client: TestClient
    ) -> None:
        """GET /api/v1/tasks with no tenant should return empty list."""
        response = client.get("/api/v1/tasks")
        assert response.status_code == 200
        assert response.json() == []
