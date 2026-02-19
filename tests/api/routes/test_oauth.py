"""Tests for OAuth callback endpoints.

This module tests OAuth integration flows for providers like Notion and Slack.
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


class TestNotionOAuthCallback:
    """Tests for GET /oauth/callback/notion endpoint."""

    def test_notion_callback_redirects_to_frontend(self, client: TestClient) -> None:
        """Should redirect to frontend with session and success params."""
        response = client.get(
            "/oauth/callback/notion",
            params={"code": "test-code-123", "state": "session-456"},
            follow_redirects=False,
        )

        assert response.status_code == 307  # Redirect status
        assert "Location" in response.headers

        location = response.headers["Location"]
        assert "session=session-456" in location
        assert "integration=notion" in location
        assert "success=true" in location

    def test_notion_callback_requires_code(self, client: TestClient) -> None:
        """Should return 422 if code parameter missing."""
        response = client.get(
            "/oauth/callback/notion",
            params={"state": "session-123"},
        )

        assert response.status_code == 422

    def test_notion_callback_requires_state(self, client: TestClient) -> None:
        """Should return 422 if state parameter missing."""
        response = client.get(
            "/oauth/callback/notion",
            params={"code": "test-code"},
        )

        assert response.status_code == 422


class TestSlackOAuthCallback:
    """Tests for GET /oauth/callback/slack endpoint."""

    def test_slack_callback_redirects_to_frontend(self, client: TestClient) -> None:
        """Should redirect to frontend with session and success params."""
        response = client.get(
            "/oauth/callback/slack",
            params={"code": "test-code-789", "state": "session-abc"},
            follow_redirects=False,
        )

        assert response.status_code == 307
        assert "Location" in response.headers

        location = response.headers["Location"]
        assert "session=session-abc" in location
        assert "integration=slack" in location
        assert "success=true" in location

    def test_slack_callback_requires_code(self, client: TestClient) -> None:
        """Should return 422 if code parameter missing."""
        response = client.get(
            "/oauth/callback/slack",
            params={"state": "session-123"},
        )

        assert response.status_code == 422


class TestInitiateOAuth:
    """Tests for GET /oauth/authorize/{integration} endpoint."""

    def test_initiate_notion_oauth_redirects(self, client: TestClient) -> None:
        """Should redirect to Notion OAuth authorization page."""
        response = client.get(
            "/oauth/authorize/notion",
            params={"session": "session-123"},
            follow_redirects=False,
        )

        assert response.status_code == 307
        assert "Location" in response.headers

        location = response.headers["Location"]
        assert "api.notion.com" in location
        assert "state=session-123" in location
        assert "client_id" in location

    def test_initiate_slack_oauth_redirects(self, client: TestClient) -> None:
        """Should redirect to Slack OAuth authorization page."""
        response = client.get(
            "/oauth/authorize/slack",
            params={"session": "session-456"},
            follow_redirects=False,
        )

        assert response.status_code == 307
        assert "Location" in response.headers

        location = response.headers["Location"]
        assert "slack.com" in location
        assert "state=session-456" in location

    def test_initiate_oauth_unsupported_integration(self, client: TestClient) -> None:
        """Should return 400 for unsupported integration type."""
        response = client.get(
            "/oauth/authorize/unsupported",
            params={"session": "session-789"},
        )

        assert response.status_code == 400
        assert "Unsupported integration" in response.json()["detail"]

    def test_initiate_oauth_requires_session(self, client: TestClient) -> None:
        """Should return 422 if session parameter missing."""
        response = client.get("/oauth/authorize/notion")

        assert response.status_code == 422
