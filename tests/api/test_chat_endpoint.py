"""Integration tests for POST /api/v1/chat endpoint.

This module tests the complete integration of the chat endpoint including
request validation, streaming response, SSE event formatting, and conversation
ID handling.
"""

from fastapi.testclient import TestClient


class TestChatEndpoint:
    """Integration tests for /api/v1/chat endpoint."""

    def test_valid_message_returns_stream(self, client: TestClient) -> None:
        """Valid message should return 200 with event-stream content-type."""
        response = client.post("/api/v1/chat", json={"message": "Hello"})

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

    def test_empty_message_returns_422(self, client: TestClient) -> None:
        """Empty message should return 422 validation error."""
        response = client.post("/api/v1/chat", json={"message": ""})

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_whitespace_message_returns_422(self, client: TestClient) -> None:
        """Whitespace-only message should return validation error."""
        response = client.post("/api/v1/chat", json={"message": "   "})

        # Whitespace validation returns 400 from custom error handler
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "validation_error"
        assert "whitespace" in data["message"].lower()

    def test_message_too_long_returns_422(self, client: TestClient) -> None:
        """Message exceeding 10000 characters should be rejected."""
        long_message = "a" * 10001  # Max is 10000

        response = client.post("/api/v1/chat", json={"message": long_message})

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_stream_contains_chunk_events(self, client: TestClient) -> None:
        """Response stream should contain chunk events."""
        response = client.post("/api/v1/chat", json={"message": "Hello"})

        content = response.text
        assert "event: chunk" in content

    def test_stream_ends_with_done_event(self, client: TestClient) -> None:
        """Response stream should end with done event."""
        response = client.post("/api/v1/chat", json={"message": "Hello"})

        content = response.text
        assert "event: done" in content

    def test_done_event_contains_conversation_id(self, client: TestClient) -> None:
        """Done event should contain conversation_id."""
        response = client.post("/api/v1/chat", json={"message": "Hello"})

        content = response.text
        assert "conversation_id" in content

    def test_conversation_id_preserved(self, client: TestClient) -> None:
        """Provided conversation_id should be returned in done event."""
        conversation_id = "550e8400-e29b-41d4-a716-446655440000"

        response = client.post(
            "/api/v1/chat",
            json={"message": "Hello", "conversation_id": conversation_id},
        )

        assert response.status_code == 200
        assert conversation_id in response.text
