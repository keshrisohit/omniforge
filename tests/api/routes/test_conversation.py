"""Tests for conversation API endpoints.

This module tests the conversational agent builder API, including
session management, message streaming, and OAuth integration.
"""

import json
from unittest.mock import MagicMock, patch

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


class TestStartConversation:
    """Tests for POST /api/v1/conversation/start endpoint."""

    def test_start_conversation_success(self, client: TestClient, mock_tenant_id: str) -> None:
        """Should create new conversation session and return session_id."""
        response = client.post(
            "/api/v1/conversation/start",
            json={},
            headers={"X-Tenant-ID": mock_tenant_id},
        )

        assert response.status_code == 200
        data = response.json()

        assert "session_id" in data
        assert "message" in data
        assert "phase" in data
        assert data["phase"] == "initial"
        assert len(data["session_id"]) > 0

    def test_start_conversation_without_tenant_fails(self, client: TestClient) -> None:
        """Should return 401 if tenant_id not available."""
        response = client.post("/api/v1/conversation/start", json={})

        assert response.status_code == 401
        assert "Tenant ID required" in response.json()["detail"]


class TestSendMessage:
    """Tests for POST /api/v1/conversation/{session_id}/message endpoint."""

    def test_send_message_streams_response(self, client: TestClient, mock_tenant_id: str) -> None:
        """Should stream SSE response for conversation message."""
        headers = {"X-Tenant-ID": mock_tenant_id}

        # Start conversation first
        start_response = client.post("/api/v1/conversation/start", json={}, headers=headers)
        session_id = start_response.json()["session_id"]

        # Send message
        response = client.post(
            f"/api/v1/conversation/{session_id}/message",
            json={"message": "I want to create weekly Notion reports"},
            headers=headers,
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

        # Parse SSE events
        events = []
        for line in response.text.split("\n"):
            if line.startswith("event:"):
                events.append(line.split(": ")[1])

        # Should have message and done events
        assert "message" in events
        assert "done" in events

    def test_send_message_without_tenant_fails(
        self, client: TestClient, mock_tenant_id: str
    ) -> None:
        """Should return 401 if tenant_id not available."""
        headers = {"X-Tenant-ID": mock_tenant_id}

        # Start conversation
        start_response = client.post("/api/v1/conversation/start", json={}, headers=headers)
        session_id = start_response.json()["session_id"]

        # Try to send message without tenant
        response = client.post(
            f"/api/v1/conversation/{session_id}/message",
            json={"message": "Test message"},
        )

        assert response.status_code == 401

    def test_send_message_with_invalid_session(
        self, client: TestClient, mock_tenant_id: str
    ) -> None:
        """Should return error event for invalid session_id."""
        response = client.post(
            "/api/v1/conversation/invalid-session-id/message",
            json={"message": "Test message"},
            headers={"X-Tenant-ID": mock_tenant_id},
        )

        assert response.status_code == 200
        # Should contain error event in stream
        assert "event: error" in response.text


class TestCompleteOAuth:
    """Tests for POST /api/v1/conversation/{session_id}/oauth-complete endpoint."""

    def test_oauth_complete_success(self, client: TestClient, mock_tenant_id: str) -> None:
        """Should complete OAuth flow and return success response."""
        headers = {"X-Tenant-ID": mock_tenant_id}

        # Start conversation
        start_response = client.post("/api/v1/conversation/start", json={}, headers=headers)
        session_id = start_response.json()["session_id"]

        # Complete OAuth
        response = client.post(
            f"/api/v1/conversation/{session_id}/oauth-complete",
            json={
                "integration": "notion",
                "code": "test-auth-code-123",
                "state": session_id,
            },
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "workspace_name" in data
        assert "message" in data

    def test_oauth_complete_without_tenant_fails(
        self, client: TestClient, mock_tenant_id: str
    ) -> None:
        """Should return 401 if tenant_id not available."""
        headers = {"X-Tenant-ID": mock_tenant_id}

        # Start conversation
        start_response = client.post("/api/v1/conversation/start", json={}, headers=headers)
        session_id = start_response.json()["session_id"]

        # Try OAuth without tenant
        response = client.post(
            f"/api/v1/conversation/{session_id}/oauth-complete",
            json={
                "integration": "notion",
                "code": "test-code",
                "state": session_id,
            },
        )

        assert response.status_code == 401

    def test_oauth_complete_with_invalid_session(
        self, client: TestClient, mock_tenant_id: str
    ) -> None:
        """Should return 404 for invalid session_id."""
        response = client.post(
            "/api/v1/conversation/invalid-session/oauth-complete",
            json={
                "integration": "notion",
                "code": "test-code",
                "state": "invalid-session",
            },
            headers={"X-Tenant-ID": mock_tenant_id},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
