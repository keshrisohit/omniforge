"""Integration tests for agent API routes.

This module tests the agent discovery endpoints including agent card
retrieval and agent listing functionality.
"""

from typing import AsyncIterator

import pytest
from fastapi.testclient import TestClient

from omniforge.agents.base import BaseAgent
from omniforge.agents.events import TaskDoneEvent, TaskEvent, TaskStatusEvent
from omniforge.agents.models import (
    AgentCapabilities,
    AgentIdentity,
    AgentSkill,
    SkillInputMode,
    SkillOutputMode,
)
from omniforge.api.app import create_app
from omniforge.api.routes.agents import _agent_repository
from omniforge.tasks.models import Task, TaskState


class TestAgent(BaseAgent):
    """Test agent for API testing."""

    identity = AgentIdentity(
        id="test-agent",
        name="Test Agent",
        description="A test agent for API testing",
        version="1.0.0",
    )
    capabilities = AgentCapabilities(streaming=True, multi_turn=False)
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
    agent = TestAgent()
    await _agent_repository.save(agent)
    yield agent
    # Cleanup
    await _agent_repository.delete("test-agent")


class TestDefaultAgentCard:
    """Tests for the default agent card endpoint."""

    def test_get_default_agent_card_returns_valid_json(self, client: TestClient) -> None:
        """Default agent card should return valid A2A JSON."""
        response = client.get("/.well-known/agent-card.json")

        assert response.status_code == 200
        assert response.headers["Content-Type"] == "application/json"

        data = response.json()
        assert data["protocolVersion"] == "1.0"
        assert data["identity"]["id"] == "omniforge-platform"
        assert data["identity"]["name"] == "OmniForge Platform"
        assert data["identity"]["version"] == "0.1.0"
        assert "capabilities" in data
        assert "skills" in data
        assert len(data["skills"]) > 0

    def test_default_agent_card_has_required_fields(self, client: TestClient) -> None:
        """Default agent card should have all required A2A fields."""
        response = client.get("/.well-known/agent-card.json")
        data = response.json()

        # Check required top-level fields
        required_fields = [
            "protocolVersion",
            "identity",
            "capabilities",
            "skills",
            "serviceEndpoint",
            "security",
        ]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        # Check identity fields
        identity = data["identity"]
        assert "id" in identity
        assert "name" in identity
        assert "description" in identity
        assert "version" in identity

        # Check capabilities
        capabilities = data["capabilities"]
        assert "streaming" in capabilities
        assert capabilities["streaming"] is True


class TestListAgents:
    """Tests for the agent listing endpoint."""

    def test_list_agents_empty_registry(self, client: TestClient) -> None:
        """Listing agents should return empty list when no agents registered."""
        response = client.get("/api/v1/agents")

        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_list_agents_with_registered_agent(
        self, client: TestClient, registered_agent: TestAgent
    ) -> None:
        """Listing agents should return registered agents."""
        response = client.get("/api/v1/agents")

        assert response.status_code == 200
        agents = response.json()
        assert len(agents) == 1
        assert agents[0]["id"] == "test-agent"
        assert agents[0]["name"] == "Test Agent"
        assert agents[0]["description"] == "A test agent for API testing"
        assert agents[0]["version"] == "1.0.0"


class TestGetAgentCard:
    """Tests for the agent card retrieval endpoint."""

    @pytest.mark.asyncio
    async def test_get_agent_card_returns_valid_json(
        self, client: TestClient, registered_agent: TestAgent
    ) -> None:
        """Agent card endpoint should return valid A2A JSON."""
        response = client.get("/api/v1/agents/test-agent")

        assert response.status_code == 200
        assert response.headers["Content-Type"] == "application/json"

        data = response.json()
        assert data["protocolVersion"] == "1.0"
        assert data["identity"]["id"] == "test-agent"
        assert data["identity"]["name"] == "Test Agent"
        assert data["identity"]["version"] == "1.0.0"
        assert "capabilities" in data
        assert "skills" in data
        assert len(data["skills"]) == 1

    @pytest.mark.asyncio
    async def test_get_agent_card_includes_service_endpoint(
        self, client: TestClient, registered_agent: TestAgent
    ) -> None:
        """Agent card should include correct service endpoint."""
        response = client.get("/api/v1/agents/test-agent")
        data = response.json()

        assert "serviceEndpoint" in data
        assert "test-agent" in data["serviceEndpoint"]

    def test_get_agent_card_not_found(self, client: TestClient) -> None:
        """Getting non-existent agent card should return 404."""
        response = client.get("/api/v1/agents/nonexistent-agent")

        assert response.status_code == 404
        data = response.json()
        assert data["code"] == "agent_not_found"
        assert "nonexistent-agent" in data["message"]

    @pytest.mark.asyncio
    async def test_get_agent_card_includes_skills(
        self, client: TestClient, registered_agent: TestAgent
    ) -> None:
        """Agent card should include all agent skills."""
        response = client.get("/api/v1/agents/test-agent")
        data = response.json()

        assert "skills" in data
        skills = data["skills"]
        assert len(skills) == 1
        assert skills[0]["id"] == "test-skill"
        assert skills[0]["name"] == "Test Skill"
        assert "inputModes" in skills[0]
        assert "outputModes" in skills[0]
