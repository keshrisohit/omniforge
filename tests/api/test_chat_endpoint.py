"""Tests for POST /api/v1/chat endpoint."""

from fastapi.testclient import TestClient


class TestChatEndpoint:
    """Tests for /api/v1/chat endpoint."""

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

        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "validation_error"
        assert "whitespace" in data["message"].lower()

    def test_message_too_long_returns_422(self, client: TestClient) -> None:
        """Message exceeding 10000 characters should be rejected."""
        response = client.post("/api/v1/chat", json={"message": "a" * 10001})

        assert response.status_code == 422
        assert "detail" in response.json()

    def test_stream_contains_reasoning_step_events(self, client: TestClient) -> None:
        """Response stream should contain reasoning_step events."""
        response = client.post("/api/v1/chat", json={"message": "Hello"})

        assert "event: reasoning_step" in response.text

    def test_stream_contains_message_event(self, client: TestClient) -> None:
        """Response stream should contain a message event with the agent's answer."""
        response = client.post("/api/v1/chat", json={"message": "Hello"})

        assert "event: message" in response.text

    def test_stream_ends_with_done_event(self, client: TestClient) -> None:
        """Response stream should end with a done event."""
        response = client.post("/api/v1/chat", json={"message": "Hello"})

        assert "event: done" in response.text

    def test_done_event_has_final_state(self, client: TestClient) -> None:
        """Done event should carry final_state."""
        response = client.post("/api/v1/chat", json={"message": "Hello"})

        assert "final_state" in response.text

    def test_conversation_id_routes_to_same_session(self, client: TestClient) -> None:
        """Requests with the same conversation_id reuse the same agent session."""
        conversation_id = "550e8400-e29b-41d4-a716-446655440000"

        response = client.post(
            "/api/v1/chat",
            json={"message": "Hello", "conversation_id": conversation_id},
        )

        assert response.status_code == 200
