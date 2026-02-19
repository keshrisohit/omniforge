"""Integration tests for health check endpoint.

This module tests the /health endpoint used for monitoring and load balancer
health checks.
"""

import pytest
from fastapi.testclient import TestClient

from omniforge.api.app import create_app


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI application.

    Returns:
        TestClient instance
    """
    app = create_app()
    return TestClient(app)


class TestHealthEndpoint:
    """Integration tests for /health endpoint."""

    def test_health_returns_status(self, client: TestClient) -> None:
        """GET /health should return status with components."""
        response = client.get("/health")

        # Should return either 200 (healthy/degraded) or 503 (unhealthy)
        assert response.status_code in [200, 503]

        data = response.json()
        assert "status" in data
        assert "components" in data
        assert "version" in data

        # Check components structure
        components = data["components"]
        assert "database" in components
        assert "scheduler" in components
        assert "llm" in components

        # Each component should have status
        for component_name, component_data in components.items():
            assert "status" in component_data
            assert component_data["status"] in ["healthy", "unhealthy", "degraded"]

    def test_health_components_have_messages(self, client: TestClient) -> None:
        """Health check components should include status messages."""
        response = client.get("/health")

        data = response.json()
        components = data["components"]

        # Each component should optionally have a message
        for component_name, component_data in components.items():
            assert isinstance(component_data.get("message"), (str, type(None)))
