"""Tests for builder agent API endpoints.

This module tests agent CRUD operations including listing, retrieval,
execution, and deletion of conversational-built agents.
"""

import pytest
from fastapi.testclient import TestClient

from omniforge.api.app import create_app


@pytest.fixture
def client() -> TestClient:
    """Create test client with app instance.

    Returns:
        TestClient configured for testing
    """
    app = create_app()
    return TestClient(app)


@pytest.fixture
def mock_tenant_id() -> str:
    """Provide test tenant ID.

    Returns:
        Test tenant identifier
    """
    return "test-tenant-123"


class TestListAgents:
    """Tests for GET /api/v1/builder/agents endpoint."""

    def test_list_agents_success(self, client: TestClient, mock_tenant_id: str) -> None:
        """Should return list of agents for tenant."""
        response = client.get("/api/v1/builder/agents", headers={"X-Tenant-ID": mock_tenant_id})

        assert response.status_code == 200
        data = response.json()

        assert "agents" in data
        assert isinstance(data["agents"], list)

    def test_list_agents_without_tenant_fails(self, client: TestClient) -> None:
        """Should return 401 if tenant_id not available."""
        response = client.get("/api/v1/builder/agents")

        assert response.status_code == 401
        assert "Tenant ID required" in response.json()["detail"]


class TestGetAgent:
    """Tests for GET /api/v1/builder/agents/{agent_id} endpoint."""

    def test_get_agent_not_found(self, client: TestClient, mock_tenant_id: str) -> None:
        """Should return 404 for non-existent agent."""
        response = client.get(
            "/api/v1/builder/agents/nonexistent-agent-id",
            headers={"X-Tenant-ID": mock_tenant_id},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_get_agent_without_tenant_fails(self, client: TestClient) -> None:
        """Should return 401 if tenant_id not available."""
        response = client.get("/api/v1/builder/agents/some-agent-id")

        assert response.status_code == 401


class TestRunAgent:
    """Tests for POST /api/v1/builder/agents/{agent_id}/run endpoint."""

    def test_run_agent_returns_execution_id(self, client: TestClient, mock_tenant_id: str) -> None:
        """Should return execution_id and pending status."""
        response = client.post(
            "/api/v1/builder/agents/test-agent/run",
            json={"input_data": {"timeframe": "7 days"}},
            headers={"X-Tenant-ID": mock_tenant_id},
        )

        # Returns placeholder response even for non-existent agent
        # In production, this should validate agent exists first
        assert response.status_code == 200
        data = response.json()

        assert "execution_id" in data
        assert data["status"] == "pending"
        assert len(data["execution_id"]) > 0

    def test_run_agent_without_tenant_fails(self, client: TestClient) -> None:
        """Should return 401 if tenant_id not available."""
        response = client.post(
            "/api/v1/builder/agents/test-agent/run",
            json={"input_data": {}},
        )

        assert response.status_code == 401

    def test_run_agent_with_empty_input_data(self, client: TestClient, mock_tenant_id: str) -> None:
        """Should accept empty input_data."""
        response = client.post(
            "/api/v1/builder/agents/test-agent/run",
            json={"input_data": {}},
            headers={"X-Tenant-ID": mock_tenant_id},
        )

        assert response.status_code == 200


class TestListAgentExecutions:
    """Tests for GET /api/v1/builder/agents/{agent_id}/executions endpoint."""

    def test_list_executions_success(self, client: TestClient, mock_tenant_id: str) -> None:
        """Should return list of executions for agent."""
        response = client.get(
            "/api/v1/builder/agents/test-agent/executions",
            headers={"X-Tenant-ID": mock_tenant_id},
        )

        assert response.status_code == 200
        data = response.json()

        assert "executions" in data
        assert isinstance(data["executions"], list)

    def test_list_executions_with_pagination(self, client: TestClient, mock_tenant_id: str) -> None:
        """Should accept pagination parameters."""
        response = client.get(
            "/api/v1/builder/agents/test-agent/executions?limit=10&offset=20",
            headers={"X-Tenant-ID": mock_tenant_id},
        )

        assert response.status_code == 200

    def test_list_executions_without_tenant_fails(self, client: TestClient) -> None:
        """Should return 401 if tenant_id not available."""
        response = client.get("/api/v1/builder/agents/test-agent/executions")

        assert response.status_code == 401


class TestDeleteAgent:
    """Tests for DELETE /api/v1/builder/agents/{agent_id} endpoint."""

    def test_delete_agent_not_found(self, client: TestClient, mock_tenant_id: str) -> None:
        """Should return 404 for non-existent agent."""
        response = client.delete(
            "/api/v1/builder/agents/nonexistent-agent",
            headers={"X-Tenant-ID": mock_tenant_id},
        )

        assert response.status_code == 404

    def test_delete_agent_without_tenant_fails(self, client: TestClient) -> None:
        """Should return 401 if tenant_id not available."""
        response = client.delete("/api/v1/builder/agents/test-agent")

        assert response.status_code == 401
