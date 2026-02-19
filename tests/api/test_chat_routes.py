"""Tests for chat API routes."""

import pytest
from fastapi.testclient import TestClient

from omniforge.api.app import create_app


class TestChatEndpoint:
    """Tests for /api/v1/chat endpoint."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create test client for the application."""
        app = create_app()
        return TestClient(app)

    def test_chat_endpoint_returns_streaming_response(self, client: TestClient) -> None:
        """Chat endpoint should return SSE streaming response."""
        response = client.post("/api/v1/chat", json={"message": "Hello"})

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
        assert response.headers["cache-control"] == "no-cache"
        assert response.headers["connection"] == "keep-alive"

    def test_chat_endpoint_streams_chunk_and_done_events(self, client: TestClient) -> None:
        """Chat endpoint should stream chunk events followed by done event."""
        response = client.post("/api/v1/chat", json={"message": "Hello"})

        content = response.text
        assert "event: chunk" in content
        assert "event: done" in content
        assert "conversation_id" in content
        assert "usage" in content

    def test_chat_endpoint_with_conversation_id(self, client: TestClient) -> None:
        """Chat endpoint should accept and use provided conversation_id."""
        conversation_id = "550e8400-e29b-41d4-a716-446655440000"

        response = client.post(
            "/api/v1/chat",
            json={"message": "Hello", "conversation_id": conversation_id},
        )

        assert response.status_code == 200
        assert conversation_id in response.text

    def test_chat_endpoint_with_empty_message_fails_validation(self, client: TestClient) -> None:
        """Chat endpoint should reject empty messages."""
        response = client.post("/api/v1/chat", json={"message": ""})

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_chat_endpoint_with_whitespace_only_message_fails_validation(
        self, client: TestClient
    ) -> None:
        """Chat endpoint should reject whitespace-only messages."""
        response = client.post("/api/v1/chat", json={"message": "   "})

        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "validation_error"
        assert "whitespace" in data["message"].lower()

    def test_chat_endpoint_with_missing_message_fails_validation(self, client: TestClient) -> None:
        """Chat endpoint should reject requests without message field."""
        response = client.post("/api/v1/chat", json={})

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_chat_endpoint_with_too_long_message_fails_validation(self, client: TestClient) -> None:
        """Chat endpoint should reject messages exceeding max length."""
        long_message = "a" * 10001  # Max is 10000

        response = client.post("/api/v1/chat", json={"message": long_message})

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_chat_endpoint_with_invalid_conversation_id_format(self, client: TestClient) -> None:
        """Chat endpoint should reject invalid conversation_id format."""
        response = client.post(
            "/api/v1/chat",
            json={"message": "Hello", "conversation_id": "not-a-uuid"},
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
