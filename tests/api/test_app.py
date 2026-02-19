"""Tests for FastAPI application factory."""

from fastapi.testclient import TestClient

from omniforge.api.app import create_app


class TestAppFactory:
    """Tests for create_app factory function."""

    def test_create_app_returns_fastapi_instance(self) -> None:
        """create_app should return a configured FastAPI instance."""
        app = create_app()

        assert app.title == "OmniForge Chat API"
        assert app.version == "0.1.0"

    def test_health_endpoint_returns_healthy_status(self) -> None:
        """Health endpoint should return healthy status."""
        app = create_app()
        client = TestClient(app)

        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    def test_cors_middleware_allows_all_origins(self) -> None:
        """CORS middleware should be configured to allow all origins in development."""
        app = create_app()
        client = TestClient(app)

        response = client.options(
            "/health",
            headers={
                "Origin": "http://example.com",
                "Access-Control-Request-Method": "GET",
            },
        )

        assert response.status_code == 200
        # CORS middleware returns the origin back when allow_origins=["*"]
        assert "access-control-allow-origin" in response.headers
        assert response.headers["access-control-allow-origin"] in [
            "*",
            "http://example.com",
        ]
