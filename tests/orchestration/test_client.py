"""Tests for A2A HTTP client."""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from omniforge.agents.events import (
    TaskDoneEvent,
    TaskErrorEvent,
    TaskMessageEvent,
    TaskStatusEvent,
)
from omniforge.agents.models import (
    AgentCapabilities,
    AgentCard,
    AgentIdentity,
    AgentSkill,
    SecurityConfig,
    SkillInputMode,
    SkillOutputMode,
    TextPart,
)
from omniforge.orchestration.client import A2AClient
from omniforge.tasks.models import TaskCreateRequest, TaskState


class TestA2AClient:
    """Tests for A2AClient class."""

    @pytest.fixture
    def agent_card(self):
        """Create a test agent card."""
        return AgentCard(
            protocol_version="1.0",
            identity=AgentIdentity(
                id="remote-agent",
                name="Remote Agent",
                description="Remote test agent",
                version="1.0.0",
            ),
            capabilities=AgentCapabilities(streaming=True),
            skills=[
                AgentSkill(
                    id="remote-skill",
                    name="Remote Skill",
                    description="Remote agent skill",
                    input_modes=[SkillInputMode.TEXT],
                    output_modes=[SkillOutputMode.TEXT],
                )
            ],
            service_endpoint="https://remote-agent.example.com",
            security=SecurityConfig(auth_scheme="bearer", require_https=True),
        )

    @pytest.fixture
    def task_request(self):
        """Create a test task creation request."""
        return TaskCreateRequest(
            message_parts=[TextPart(text="Test message")],
            tenant_id="tenant-1",
            user_id="user-1",
        )

    @pytest.mark.asyncio
    async def test_client_context_manager(self):
        """Client should work as async context manager."""
        async with A2AClient() as client:
            assert client is not None
            assert client._http_client is not None

    @pytest.mark.asyncio
    async def test_client_close(self):
        """Client should close HTTP client properly."""
        client = A2AClient()

        with patch.object(client._http_client, "aclose", new=AsyncMock()) as mock_close:
            await client.close()
            mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_task_builds_correct_url(self, agent_card, task_request):
        """Should build correct URL for task creation."""
        client = A2AClient()

        # Mock HTTP response with SSE data
        mock_response = Mock()
        mock_response.raise_for_status = Mock()

        async def mock_aiter_lines():
            yield "event: done"
            yield f'data: {{"type": "done", "task_id": "123", "timestamp": "{datetime.utcnow().isoformat()}Z", "final_state": "completed"}}'
            yield ""

        mock_response.aiter_lines = mock_aiter_lines

        mock_stream = AsyncMock()
        mock_stream.__aenter__.return_value = mock_response
        mock_stream.__aexit__.return_value = None

        with patch.object(client._http_client, "stream", return_value=mock_stream) as mock_req:
            events = []
            async for event in client.send_task(agent_card, task_request):
                events.append(event)

            # Verify URL was called correctly
            expected_url = "https://remote-agent.example.com/api/v1/agents/remote-agent/tasks"
            mock_req.assert_called_once()
            call_args = mock_req.call_args
            assert call_args[0][1] == expected_url

    @pytest.mark.asyncio
    async def test_send_task_includes_correct_headers(self, agent_card, task_request):
        """Should include correct headers in request."""
        client = A2AClient()

        # Mock HTTP response
        mock_response = Mock()
        mock_response.raise_for_status = Mock()

        async def mock_aiter_lines():
            yield "event: done"
            yield f'data: {{"type": "done", "task_id": "123", "timestamp": "{datetime.utcnow().isoformat()}Z", "final_state": "completed"}}'
            yield ""

        mock_response.aiter_lines = mock_aiter_lines

        mock_stream = AsyncMock()
        mock_stream.__aenter__.return_value = mock_response
        mock_stream.__aexit__.return_value = None

        with patch.object(client._http_client, "stream", return_value=mock_stream) as mock_req:
            async for _ in client.send_task(agent_card, task_request):
                pass

            # Verify headers
            call_args = mock_req.call_args
            headers = call_args[1]["headers"]
            assert headers["Accept"] == "text/event-stream"
            assert headers["Content-Type"] == "application/json"

    @pytest.mark.asyncio
    async def test_parse_sse_status_event(self, agent_card, task_request):
        """Should parse SSE status events correctly."""
        client = A2AClient()

        # Mock SSE response with status event
        mock_response = Mock()
        mock_response.raise_for_status = Mock()

        async def mock_aiter_lines():
            yield "event: status"
            yield f'data: {{"type": "status", "task_id": "123", "timestamp": "{datetime.utcnow().isoformat()}Z", "state": "working"}}'
            yield ""

        mock_response.aiter_lines = mock_aiter_lines

        mock_stream = AsyncMock()
        mock_stream.__aenter__.return_value = mock_response
        mock_stream.__aexit__.return_value = None

        with patch.object(client._http_client, "stream", return_value=mock_stream):
            events = []
            async for event in client.send_task(agent_card, task_request):
                events.append(event)

            assert len(events) == 1
            assert isinstance(events[0], TaskStatusEvent)
            assert events[0].state == TaskState.WORKING

    @pytest.mark.asyncio
    async def test_parse_sse_message_event(self, agent_card, task_request):
        """Should parse SSE message events correctly."""
        client = A2AClient()

        # Mock SSE response with message event
        mock_response = Mock()
        mock_response.raise_for_status = Mock()

        async def mock_aiter_lines():
            yield "event: message"
            yield f'data: {{"type": "message", "task_id": "123", "timestamp": "{datetime.utcnow().isoformat()}Z", "message_parts": [{{"type": "text", "text": "Hello"}}], "is_partial": false}}'
            yield ""

        mock_response.aiter_lines = mock_aiter_lines

        mock_stream = AsyncMock()
        mock_stream.__aenter__.return_value = mock_response
        mock_stream.__aexit__.return_value = None

        with patch.object(client._http_client, "stream", return_value=mock_stream):
            events = []
            async for event in client.send_task(agent_card, task_request):
                events.append(event)

            assert len(events) == 1
            assert isinstance(events[0], TaskMessageEvent)
            assert len(events[0].message_parts) == 1

    @pytest.mark.asyncio
    async def test_parse_sse_done_event(self, agent_card, task_request):
        """Should parse SSE done events correctly."""
        client = A2AClient()

        # Mock SSE response with done event
        mock_response = Mock()
        mock_response.raise_for_status = Mock()

        async def mock_aiter_lines():
            yield "event: done"
            yield f'data: {{"type": "done", "task_id": "123", "timestamp": "{datetime.utcnow().isoformat()}Z", "final_state": "completed"}}'
            yield ""

        mock_response.aiter_lines = mock_aiter_lines

        mock_stream = AsyncMock()
        mock_stream.__aenter__.return_value = mock_response
        mock_stream.__aexit__.return_value = None

        with patch.object(client._http_client, "stream", return_value=mock_stream):
            events = []
            async for event in client.send_task(agent_card, task_request):
                events.append(event)

            assert len(events) == 1
            assert isinstance(events[0], TaskDoneEvent)
            assert events[0].final_state == TaskState.COMPLETED

    @pytest.mark.asyncio
    async def test_parse_sse_error_event(self, agent_card, task_request):
        """Should parse SSE error events correctly."""
        client = A2AClient()

        # Mock SSE response with error event
        mock_response = Mock()
        mock_response.raise_for_status = Mock()

        async def mock_aiter_lines():
            yield "event: error"
            yield f'data: {{"type": "error", "task_id": "123", "timestamp": "{datetime.utcnow().isoformat()}Z", "error_code": "test_error", "error_message": "Test error message"}}'
            yield ""

        mock_response.aiter_lines = mock_aiter_lines

        mock_stream = AsyncMock()
        mock_stream.__aenter__.return_value = mock_response
        mock_stream.__aexit__.return_value = None

        with patch.object(client._http_client, "stream", return_value=mock_stream):
            events = []
            async for event in client.send_task(agent_card, task_request):
                events.append(event)

            assert len(events) == 1
            assert isinstance(events[0], TaskErrorEvent)
            assert events[0].error_code == "test_error"
            assert events[0].error_message == "Test error message"

    @pytest.mark.asyncio
    async def test_parse_multiple_sse_events(self, agent_card, task_request):
        """Should parse multiple SSE events in sequence."""
        client = A2AClient()

        # Mock SSE response with multiple events
        mock_response = Mock()
        mock_response.raise_for_status = Mock()

        async def mock_aiter_lines():
            # Status event
            yield "event: status"
            yield f'data: {{"type": "status", "task_id": "123", "timestamp": "{datetime.utcnow().isoformat()}Z", "state": "working"}}'
            yield ""
            # Message event
            yield "event: message"
            yield f'data: {{"type": "message", "task_id": "123", "timestamp": "{datetime.utcnow().isoformat()}Z", "message_parts": [{{"type": "text", "text": "Result"}}], "is_partial": false}}'
            yield ""
            # Done event
            yield "event: done"
            yield f'data: {{"type": "done", "task_id": "123", "timestamp": "{datetime.utcnow().isoformat()}Z", "final_state": "completed"}}'
            yield ""

        mock_response.aiter_lines = mock_aiter_lines

        mock_stream = AsyncMock()
        mock_stream.__aenter__.return_value = mock_response
        mock_stream.__aexit__.return_value = None

        with patch.object(client._http_client, "stream", return_value=mock_stream):
            events = []
            async for event in client.send_task(agent_card, task_request):
                events.append(event)

            assert len(events) == 3
            assert isinstance(events[0], TaskStatusEvent)
            assert isinstance(events[1], TaskMessageEvent)
            assert isinstance(events[2], TaskDoneEvent)

    @pytest.mark.asyncio
    async def test_parse_invalid_json_raises_error(self, agent_card, task_request):
        """Should raise ValueError for invalid JSON in SSE data."""
        client = A2AClient()

        # Mock SSE response with invalid JSON
        mock_response = Mock()
        mock_response.raise_for_status = Mock()

        async def mock_aiter_lines():
            yield "event: status"
            yield "data: {invalid json}"
            yield ""

        mock_response.aiter_lines = mock_aiter_lines

        mock_stream = AsyncMock()
        mock_stream.__aenter__.return_value = mock_response
        mock_stream.__aexit__.return_value = None

        with patch.object(client._http_client, "stream", return_value=mock_stream):
            with pytest.raises(ValueError, match="Invalid JSON"):
                async for _ in client.send_task(agent_card, task_request):
                    pass

    @pytest.mark.asyncio
    async def test_parse_unknown_event_type_raises_error(self, agent_card, task_request):
        """Should raise ValueError for unknown event type."""
        client = A2AClient()

        # Mock SSE response with unknown event type
        mock_response = Mock()
        mock_response.raise_for_status = Mock()

        async def mock_aiter_lines():
            yield "event: unknown"
            yield 'data: {"type": "unknown", "task_id": "123"}'
            yield ""

        mock_response.aiter_lines = mock_aiter_lines

        mock_stream = AsyncMock()
        mock_stream.__aenter__.return_value = mock_response
        mock_stream.__aexit__.return_value = None

        with patch.object(client._http_client, "stream", return_value=mock_stream):
            with pytest.raises(ValueError, match="Unknown event type"):
                async for _ in client.send_task(agent_card, task_request):
                    pass
