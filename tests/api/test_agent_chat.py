"""Integration tests for simplified chat endpoint at /api/v1/agents/{agent_id}/chat.

This module tests the simplified chat endpoint that provides an easier alternative
to the full task creation endpoint, supporting both streaming (SSE) and non-streaming
(JSON) responses.
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


class TestChatAgent(BaseAgent):
    """Test agent for chat endpoint testing."""

    identity = AgentIdentity(
        id="chat-test-agent",
        name="Chat Test Agent",
        description="A test agent for chat endpoint testing",
        version="1.0.0",
    )
    capabilities = AgentCapabilities(streaming=True, multi_turn=False)
    skills = [
        AgentSkill(
            id="chat-test-skill",
            name="Chat Test Skill",
            description="A test skill for chat",
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
            message_parts=[TextPart(text="Chat response: Hello!")],
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
async def registered_chat_agent() -> AsyncIterator[TestChatAgent]:
    """Create and register a test chat agent.

    Yields:
        TestChatAgent instance that is registered in the repository
    """
    # Clear task repository before each test to prevent data leakage
    _task_repository._tasks.clear()

    agent = TestChatAgent()
    await _agent_repository.save(agent)
    yield agent
    # Cleanup
    await _agent_repository.delete("chat-test-agent")
    _task_repository._tasks.clear()


class TestChatEndpointStreaming:
    """Tests for the chat endpoint with streaming responses (SSE)."""

    @pytest.mark.asyncio
    async def test_chat_streaming_returns_sse(
        self, client: TestClient, registered_chat_agent: TestChatAgent
    ) -> None:
        """Chat with stream=true should return SSE stream with proper headers."""
        response = client.post(
            "/api/v1/agents/chat-test-agent/chat",
            json={
                "message": "Hello, agent!",
                "stream": True,
            },
            headers={"Accept": "text/event-stream"},
        )

        assert response.status_code == 200
        assert response.headers["Content-Type"] == "text/event-stream; charset=utf-8"
        assert response.headers["Cache-Control"] == "no-cache"
        assert response.headers["Connection"] == "keep-alive"
        assert response.headers["X-Accel-Buffering"] == "no"

    @pytest.mark.asyncio
    async def test_chat_streaming_contains_events(
        self, client: TestClient, registered_chat_agent: TestChatAgent
    ) -> None:
        """Chat streaming should contain status, message, and done events."""
        response = client.post(
            "/api/v1/agents/chat-test-agent/chat",
            json={
                "message": "Hello, agent!",
                "stream": True,
            },
            headers={"Accept": "text/event-stream"},
        )

        content = response.text
        assert "event: status" in content
        assert "event: message" in content
        assert "event: done" in content
        assert "working" in content
        assert "completed" in content

    @pytest.mark.asyncio
    async def test_chat_default_stream_is_true(
        self, client: TestClient, registered_chat_agent: TestChatAgent
    ) -> None:
        """Chat endpoint should default to streaming if stream not specified."""
        response = client.post(
            "/api/v1/agents/chat-test-agent/chat",
            json={
                "message": "Hello, agent!",
                # stream not specified, should default to True
            },
            headers={"Accept": "text/event-stream"},
        )

        assert response.status_code == 200
        assert response.headers["Content-Type"] == "text/event-stream; charset=utf-8"


class TestChatEndpointNonStreaming:
    """Tests for the chat endpoint with non-streaming responses (JSON)."""

    @pytest.mark.asyncio
    async def test_chat_non_streaming_returns_json(
        self, client: TestClient, registered_chat_agent: TestChatAgent
    ) -> None:
        """Chat with stream=false should return JSON response."""
        response = client.post(
            "/api/v1/agents/chat-test-agent/chat",
            json={
                "message": "Hello, agent!",
                "stream": False,
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert "task_id" in data
        assert "response" in data
        assert "state" in data

        # Check response content
        assert data["response"] == "Chat response: Hello!"
        assert data["state"] == "completed"
        assert len(data["task_id"]) > 0

    @pytest.mark.asyncio
    async def test_chat_non_streaming_with_user_id(
        self, client: TestClient, registered_chat_agent: TestChatAgent
    ) -> None:
        """Chat should support custom user_id."""
        response = client.post(
            "/api/v1/agents/chat-test-agent/chat",
            json={
                "message": "Hello!",
                "stream": False,
                "user_id": "custom-user-123",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["state"] == "completed"

        # Verify task was created with correct user_id
        task = await _task_repository.get(data["task_id"])
        assert task is not None
        assert task.user_id == "custom-user-123"

    @pytest.mark.asyncio
    async def test_chat_non_streaming_with_tenant_id(
        self, client: TestClient, registered_chat_agent: TestChatAgent
    ) -> None:
        """Chat should support tenant_id for multi-tenancy."""
        response = client.post(
            "/api/v1/agents/chat-test-agent/chat",
            json={
                "message": "Hello!",
                "stream": False,
                "tenant_id": "tenant-456",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["state"] == "completed"

        # Verify task was created with correct tenant_id
        task = await _task_repository.get(data["task_id"])
        assert task is not None
        assert task.tenant_id == "tenant-456"


class TestChatEndpointValidation:
    """Tests for chat endpoint validation."""

    def test_chat_empty_message_returns_422(self, client: TestClient) -> None:
        """Empty message should return 422 validation error."""
        response = client.post(
            "/api/v1/agents/chat-test-agent/chat",
            json={
                "message": "",
                "stream": False,
            },
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_chat_message_too_long_returns_422(self, client: TestClient) -> None:
        """Message exceeding max length should return 422 validation error."""
        long_message = "a" * 10001  # Max is 10000

        response = client.post(
            "/api/v1/agents/chat-test-agent/chat",
            json={
                "message": long_message,
                "stream": False,
            },
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_chat_agent_not_found_returns_404(self, client: TestClient) -> None:
        """Chat with non-existent agent should return 404."""
        response = client.post(
            "/api/v1/agents/non-existent-agent/chat",
            json={
                "message": "Hello!",
                "stream": False,
            },
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_chat_missing_message_returns_422(self, client: TestClient) -> None:
        """Request without message field should return 422."""
        response = client.post(
            "/api/v1/agents/chat-test-agent/chat",
            json={
                "stream": False,
                # message field missing
            },
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
