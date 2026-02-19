"""Tests for agent streaming utilities."""

import json
from datetime import datetime

import pytest

from omniforge.agents.errors import AgentProcessingError, TaskNotFoundError
from omniforge.agents.events import (
    TaskArtifactEvent,
    TaskDoneEvent,
    TaskErrorEvent,
    TaskMessageEvent,
    TaskStatusEvent,
)
from omniforge.agents.models import Artifact, TextPart
from omniforge.agents.streaming import (
    format_artifact_event,
    format_done_event,
    format_error_event,
    format_message_event,
    format_status_event,
    format_task_event,
    stream_task_events,
    stream_task_with_error_handling,
)
from omniforge.tasks.models import TaskState


class TestFormatTaskEvent:
    """Tests for format_task_event function."""

    def test_format_status_event(self) -> None:
        """Status event should be formatted as valid SSE."""
        event = TaskStatusEvent(
            task_id="task-123",
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            state=TaskState.WORKING,
            message="Processing request",
        )

        result = format_task_event(event)

        # Should use SSE format
        assert result.startswith("event: status\n")
        assert result.endswith("\n\n")

        # Extract and verify data
        data_line = result.split("\n")[1]
        assert data_line.startswith("data: ")
        data = json.loads(data_line[6:])

        assert data["task_id"] == "task-123"
        assert data["state"] == "working"
        assert data["message"] == "Processing request"
        assert "timestamp" in data

    def test_format_message_event(self) -> None:
        """Message event should be formatted as valid SSE."""
        event = TaskMessageEvent(
            task_id="task-456",
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            message_parts=[TextPart(text="Hello, world!")],
            is_partial=True,
        )

        result = format_task_event(event)

        assert result.startswith("event: message\n")
        data_line = result.split("\n")[1]
        data = json.loads(data_line[6:])

        assert data["task_id"] == "task-456"
        assert data["is_partial"] is True
        assert len(data["message_parts"]) == 1
        assert data["message_parts"][0]["text"] == "Hello, world!"

    def test_format_artifact_event(self) -> None:
        """Artifact event should be formatted as valid SSE."""
        artifact = Artifact(id="art-1", type="document", title="Result", content="Test content")
        event = TaskArtifactEvent(
            task_id="task-789",
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            artifact=artifact,
        )

        result = format_task_event(event)

        assert result.startswith("event: artifact\n")
        data_line = result.split("\n")[1]
        data = json.loads(data_line[6:])

        assert data["task_id"] == "task-789"
        assert data["artifact"]["id"] == "art-1"
        assert data["artifact"]["type"] == "document"

    def test_format_done_event(self) -> None:
        """Done event should be formatted as valid SSE."""
        event = TaskDoneEvent(
            task_id="task-999",
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            final_state=TaskState.COMPLETED,
        )

        result = format_task_event(event)

        assert result.startswith("event: done\n")
        data_line = result.split("\n")[1]
        data = json.loads(data_line[6:])

        assert data["task_id"] == "task-999"
        assert data["final_state"] == "completed"

    def test_format_error_event(self) -> None:
        """Error event should be formatted as valid SSE."""
        event = TaskErrorEvent(
            task_id="task-error",
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            error_code="validation_error",
            error_message="Invalid input provided",
            details={"field": "name"},
        )

        result = format_task_event(event)

        assert result.startswith("event: error\n")
        data_line = result.split("\n")[1]
        data = json.loads(data_line[6:])

        assert data["task_id"] == "task-error"
        assert data["error_code"] == "validation_error"
        assert data["error_message"] == "Invalid input provided"
        assert data["details"]["field"] == "name"


class TestIndividualFormatters:
    """Tests for type-specific formatter functions."""

    def test_format_status_event_wrapper(self) -> None:
        """format_status_event should delegate to format_task_event."""
        event = TaskStatusEvent(
            task_id="task-1",
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            state=TaskState.WORKING,
        )

        result = format_status_event(event)

        assert result.startswith("event: status\n")
        assert "task-1" in result

    def test_format_message_event_wrapper(self) -> None:
        """format_message_event should delegate to format_task_event."""
        event = TaskMessageEvent(
            task_id="task-2",
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            message_parts=[TextPart(text="Test")],
        )

        result = format_message_event(event)

        assert result.startswith("event: message\n")
        assert "task-2" in result

    def test_format_artifact_event_wrapper(self) -> None:
        """format_artifact_event should delegate to format_task_event."""
        artifact = Artifact(id="art-1", type="doc", title="T", content="C")
        event = TaskArtifactEvent(
            task_id="task-3",
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            artifact=artifact,
        )

        result = format_artifact_event(event)

        assert result.startswith("event: artifact\n")
        assert "task-3" in result

    def test_format_done_event_wrapper(self) -> None:
        """format_done_event should delegate to format_task_event."""
        event = TaskDoneEvent(
            task_id="task-4",
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            final_state=TaskState.COMPLETED,
        )

        result = format_done_event(event)

        assert result.startswith("event: done\n")
        assert "task-4" in result

    def test_format_error_event_wrapper(self) -> None:
        """format_error_event should delegate to format_task_event."""
        event = TaskErrorEvent(
            task_id="task-5",
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            error_code="test_error",
            error_message="Test error message",
        )

        result = format_error_event(event)

        assert result.startswith("event: error\n")
        assert "task-5" in result


class TestStreamTaskEvents:
    """Tests for stream_task_events async generator."""

    @pytest.mark.asyncio
    async def test_stream_multiple_events(self) -> None:
        """Should convert multiple events to SSE format."""

        async def event_generator():
            yield TaskStatusEvent(
                task_id="task-1",
                timestamp=datetime(2024, 1, 1, 12, 0, 0),
                state=TaskState.WORKING,
            )
            yield TaskMessageEvent(
                task_id="task-1",
                timestamp=datetime(2024, 1, 1, 12, 0, 1),
                message_parts=[TextPart(text="Processing")],
            )
            yield TaskDoneEvent(
                task_id="task-1",
                timestamp=datetime(2024, 1, 1, 12, 0, 2),
                final_state=TaskState.COMPLETED,
            )

        events = []
        async for sse_event in stream_task_events(event_generator()):
            events.append(sse_event)

        assert len(events) == 3
        assert events[0].startswith("event: status\n")
        assert events[1].startswith("event: message\n")
        assert events[2].startswith("event: done\n")

    @pytest.mark.asyncio
    async def test_stream_empty_events(self) -> None:
        """Should handle empty event stream."""

        async def empty_generator():
            return
            yield  # Make it a generator

        events = []
        async for sse_event in stream_task_events(empty_generator()):
            events.append(sse_event)

        assert len(events) == 0


class TestStreamTaskWithErrorHandling:
    """Tests for stream_task_with_error_handling wrapper."""

    @pytest.mark.asyncio
    async def test_stream_successful_events(self) -> None:
        """Should pass through events without errors."""

        async def event_generator():
            yield TaskStatusEvent(
                task_id="task-1",
                timestamp=datetime(2024, 1, 1, 12, 0, 0),
                state=TaskState.WORKING,
            )
            yield TaskDoneEvent(
                task_id="task-1",
                timestamp=datetime(2024, 1, 1, 12, 0, 1),
                final_state=TaskState.COMPLETED,
            )

        events = []
        async for sse_event in stream_task_with_error_handling(event_generator(), "task-1"):
            events.append(sse_event)

        assert len(events) == 2
        assert events[0].startswith("event: status\n")
        assert events[1].startswith("event: done\n")

    @pytest.mark.asyncio
    async def test_stream_agent_error(self) -> None:
        """Should convert AgentError to TaskErrorEvent."""

        async def failing_generator():
            yield TaskStatusEvent(
                task_id="task-error",
                timestamp=datetime(2024, 1, 1, 12, 0, 0),
                state=TaskState.WORKING,
            )
            raise TaskNotFoundError("task-error")

        events = []
        async for sse_event in stream_task_with_error_handling(failing_generator(), "task-error"):
            events.append(sse_event)

        assert len(events) == 2
        assert events[0].startswith("event: status\n")
        assert events[1].startswith("event: error\n")

        # Verify error content
        error_data_line = events[1].split("\n")[1]
        error_data = json.loads(error_data_line[6:])
        assert error_data["error_code"] == "task_not_found"
        assert "task-error" in error_data["error_message"]

    @pytest.mark.asyncio
    async def test_stream_generic_exception(self) -> None:
        """Should convert generic Exception to internal error event."""

        async def failing_generator():
            yield TaskStatusEvent(
                task_id="task-exc",
                timestamp=datetime(2024, 1, 1, 12, 0, 0),
                state=TaskState.WORKING,
            )
            raise ValueError("Unexpected failure")

        events = []
        async for sse_event in stream_task_with_error_handling(failing_generator(), "task-exc"):
            events.append(sse_event)

        assert len(events) == 2
        assert events[1].startswith("event: error\n")

        # Verify error content
        error_data_line = events[1].split("\n")[1]
        error_data = json.loads(error_data_line[6:])
        assert error_data["error_code"] == "internal_error"
        assert error_data["error_message"] == "Unexpected failure"

    @pytest.mark.asyncio
    async def test_stream_processing_error(self) -> None:
        """Should handle AgentProcessingError with proper code."""

        async def failing_generator():
            yield TaskStatusEvent(
                task_id="task-proc",
                timestamp=datetime(2024, 1, 1, 12, 0, 0),
                state=TaskState.WORKING,
            )
            raise AgentProcessingError("Processing failed", agent_id="agent-1")

        events = []
        async for sse_event in stream_task_with_error_handling(failing_generator(), "task-proc"):
            events.append(sse_event)

        assert len(events) == 2

        error_data_line = events[1].split("\n")[1]
        error_data = json.loads(error_data_line[6:])
        assert error_data["error_code"] == "agent_processing_error"


class TestSSEFormatCompatibility:
    """Integration tests verifying SSE format matches chat streaming."""

    def test_sse_format_structure(self) -> None:
        """Task events should match chat SSE format structure."""
        event = TaskStatusEvent(
            task_id="task-1",
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            state=TaskState.WORKING,
        )

        result = format_task_event(event)

        # Verify SSE structure: "event: {type}\ndata: {json}\n\n"
        lines = result.split("\n")
        assert len(lines) == 4  # event line, data line, empty line, empty string
        assert lines[0].startswith("event: ")
        assert lines[1].startswith("data: ")
        assert lines[2] == ""
        assert lines[3] == ""

    def test_sse_data_is_valid_json(self) -> None:
        """SSE data payload should be valid JSON."""
        event = TaskMessageEvent(
            task_id="task-1",
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            message_parts=[TextPart(text="Test")],
        )

        result = format_task_event(event)

        data_line = result.split("\n")[1]
        json_str = data_line[6:]  # Remove "data: " prefix

        # Should parse without error
        data = json.loads(json_str)
        assert isinstance(data, dict)
        assert "task_id" in data
        assert "timestamp" in data

    def test_event_type_matches_discriminator(self) -> None:
        """SSE event type should match Pydantic discriminator."""
        events = [
            TaskStatusEvent(
                task_id="t1",
                timestamp=datetime.now(),
                state=TaskState.WORKING,
            ),
            TaskMessageEvent(
                task_id="t2",
                timestamp=datetime.now(),
                message_parts=[TextPart(text="Hi")],
            ),
            TaskArtifactEvent(
                task_id="t3",
                timestamp=datetime.now(),
                artifact=Artifact(id="a1", type="doc", title="T", content="C"),
            ),
            TaskDoneEvent(
                task_id="t4",
                timestamp=datetime.now(),
                final_state=TaskState.COMPLETED,
            ),
            TaskErrorEvent(
                task_id="t5",
                timestamp=datetime.now(),
                error_code="test",
                error_message="Test error",
            ),
        ]

        for event in events:
            result = format_task_event(event)
            event_type_line = result.split("\n")[0]
            sse_event_type = event_type_line.split(": ")[1]

            # SSE event type should match Pydantic type discriminator
            assert sse_event_type == event.type
