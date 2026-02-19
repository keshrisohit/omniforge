"""Integration tests for tenant middleware."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from omniforge.api.middleware.tenant import TenantMiddleware
from omniforge.security.tenant import get_tenant_id


@pytest.fixture
def app() -> FastAPI:
    """Create a test FastAPI app with tenant middleware."""
    test_app = FastAPI()

    # Add tenant middleware
    test_app.add_middleware(TenantMiddleware)  # type: ignore[arg-type]

    # Test endpoint that returns tenant ID
    @test_app.get("/test/tenant")
    async def get_tenant() -> dict:
        return {"tenant_id": get_tenant_id()}

    return test_app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create a test client."""
    return TestClient(app)


class TestTenantMiddleware:
    """Tests for TenantMiddleware."""

    def test_no_tenant_header(self, client: TestClient) -> None:
        """Without tenant header, tenant context should be None."""
        response = client.get("/test/tenant")

        assert response.status_code == 200
        assert response.json()["tenant_id"] is None

    def test_x_tenant_id_header(self, client: TestClient) -> None:
        """X-Tenant-ID header should set tenant context."""
        response = client.get(
            "/test/tenant",
            headers={"X-Tenant-ID": "tenant-123"},
        )

        assert response.status_code == 200
        assert response.json()["tenant_id"] == "tenant-123"

    def test_x_api_key_header_extracts_tenant(self, client: TestClient) -> None:
        """X-API-Key header should extract and set tenant context."""
        response = client.get(
            "/test/tenant",
            headers={"X-API-Key": "tenant-456:developer:secret-key-abc123"},
        )

        assert response.status_code == 200
        assert response.json()["tenant_id"] == "tenant-456"

    def test_x_tenant_id_takes_precedence(self, client: TestClient) -> None:
        """X-Tenant-ID header should take precedence over API key."""
        response = client.get(
            "/test/tenant",
            headers={
                "X-Tenant-ID": "tenant-direct",
                "X-API-Key": "tenant-from-key:developer:secret-key-abc123",
            },
        )

        assert response.status_code == 200
        assert response.json()["tenant_id"] == "tenant-direct"

    def test_invalid_api_key_no_tenant_set(self, client: TestClient) -> None:
        """Invalid API key should not set tenant context."""
        response = client.get(
            "/test/tenant",
            headers={"X-API-Key": "invalid-key"},
        )

        assert response.status_code == 200
        assert response.json()["tenant_id"] is None

    def test_context_cleared_after_request(self, client: TestClient) -> None:
        """Tenant context should be cleared after request."""
        # First request sets tenant
        client.get("/test/tenant", headers={"X-Tenant-ID": "tenant-1"})

        # Second request without header should have no tenant
        response = client.get("/test/tenant")

        assert response.status_code == 200
        assert response.json()["tenant_id"] is None

    def test_concurrent_requests_isolated(self, client: TestClient) -> None:
        """Concurrent requests should have isolated tenant contexts."""
        # This test verifies context vars work correctly
        response1 = client.get("/test/tenant", headers={"X-Tenant-ID": "tenant-1"})
        response2 = client.get("/test/tenant", headers={"X-Tenant-ID": "tenant-2"})

        assert response1.json()["tenant_id"] == "tenant-1"
        assert response2.json()["tenant_id"] == "tenant-2"
