"""Tests for event filtering with visibility control.

This module tests the EventFilter class for role-based event filtering
and sensitive data redaction (TASK-013).
"""

from datetime import datetime

import pytest

from omniforge.agents.events import (
    TaskDoneEvent,
    TaskErrorEvent,
    TaskMessageEvent,
    TaskStatusEvent,
)
from omniforge.agents.models import TextPart
from omniforge.skills.event_filter import (
    EventFilter,
    VisibilityConfig,
    filter_event_stream,
)
from omniforge.tasks.models import TaskState
from omniforge.tools.types import VisibilityLevel


class TestVisibilityConfig:
    """Test suite for VisibilityConfig."""

    def test_default_level(self) -> None:
        """VisibilityConfig should default to SUMMARY level."""
        config = VisibilityConfig()
        assert config.level == VisibilityLevel.SUMMARY


class TestEventFilter:
    """Test suite for EventFilter class."""

    def test_init_with_end_user_role(self) -> None:
        """END_USER role should get SUMMARY visibility level."""
        event_filter = EventFilter(user_role="END_USER")
        assert event_filter.config.level == VisibilityLevel.SUMMARY

    def test_init_with_developer_role(self) -> None:
        """DEVELOPER role should get FULL visibility level."""
        event_filter = EventFilter(user_role="DEVELOPER")
        assert event_filter.config.level == VisibilityLevel.FULL

    def test_init_with_admin_role(self) -> None:
        """ADMIN role should get FULL visibility level."""
        event_filter = EventFilter(user_role="ADMIN")
        assert event_filter.config.level == VisibilityLevel.FULL

    def test_init_with_unknown_role(self) -> None:
        """Unknown roles should default to SUMMARY visibility level."""
        event_filter = EventFilter(user_role="UNKNOWN")
        assert event_filter.config.level == VisibilityLevel.SUMMARY

    def test_init_with_no_role(self) -> None:
        """No role should default to SUMMARY visibility level."""
        event_filter = EventFilter(user_role=None)
        assert event_filter.config.level == VisibilityLevel.SUMMARY

    def test_should_emit_event_without_visibility_attr(self) -> None:
        """Events without visibility attribute should always be emitted."""
        event_filter = EventFilter(user_role="END_USER")

        # TaskDoneEvent doesn't have visibility attribute by default
        event = TaskDoneEvent(
            task_id="task-1",
            timestamp=datetime.utcnow(),
            final_state=TaskState.COMPLETED,
        )

        assert event_filter.should_emit_event(event) is True

    def test_should_emit_hidden_events(self) -> None:
        """HIDDEN events should never be emitted."""
        event_filter = EventFilter(user_role="DEVELOPER")  # Even with FULL access

        event = TaskMessageEvent(
            task_id="task-1",
            timestamp=datetime.utcnow(),
            message_parts=[TextPart(text="Hidden message")],
            visibility=VisibilityLevel.HIDDEN,
        )

        assert event_filter.should_emit_event(event) is False

    def test_should_emit_summary_events_for_end_user(self) -> None:
        """END_USER should see SUMMARY events."""
        event_filter = EventFilter(user_role="END_USER")

        event = TaskMessageEvent(
            task_id="task-1",
            timestamp=datetime.utcnow(),
            message_parts=[TextPart(text="Summary message")],
            visibility=VisibilityLevel.SUMMARY,
        )

        assert event_filter.should_emit_event(event) is True

    def test_should_not_emit_full_events_for_end_user(self) -> None:
        """END_USER should not see FULL events."""
        event_filter = EventFilter(user_role="END_USER")

        event = TaskMessageEvent(
            task_id="task-1",
            timestamp=datetime.utcnow(),
            message_parts=[TextPart(text="Full detail message")],
            visibility=VisibilityLevel.FULL,
        )

        assert event_filter.should_emit_event(event) is False

    def test_should_emit_all_visible_events_for_developer(self) -> None:
        """DEVELOPER should see both SUMMARY and FULL events."""
        event_filter = EventFilter(user_role="DEVELOPER")

        summary_event = TaskMessageEvent(
            task_id="task-1",
            timestamp=datetime.utcnow(),
            message_parts=[TextPart(text="Summary message")],
            visibility=VisibilityLevel.SUMMARY,
        )

        full_event = TaskMessageEvent(
            task_id="task-1",
            timestamp=datetime.utcnow(),
            message_parts=[TextPart(text="Full detail message")],
            visibility=VisibilityLevel.FULL,
        )

        assert event_filter.should_emit_event(summary_event) is True
        assert event_filter.should_emit_event(full_event) is True

    def test_redact_api_key(self) -> None:
        """API keys should be redacted from messages."""
        event_filter = EventFilter()

        text = 'Using API key: api_key="sk-12345" for authentication'
        redacted = event_filter._redact_sensitive(text)

        assert "sk-12345" not in redacted
        assert "[REDACTED]" in redacted
        assert "api_key" in redacted

    def test_redact_password(self) -> None:
        """Passwords should be redacted from messages."""
        event_filter = EventFilter()

        text = "Login with password: secret123"
        redacted = event_filter._redact_sensitive(text)

        assert "secret123" not in redacted
        assert "[REDACTED]" in redacted

    def test_redact_token(self) -> None:
        """Tokens should be redacted from messages."""
        event_filter = EventFilter()

        text = "Authorization token=bearer_xyz789"
        redacted = event_filter._redact_sensitive(text)

        assert "bearer_xyz789" not in redacted
        assert "[REDACTED]" in redacted

    def test_redact_multiple_secrets(self) -> None:
        """Multiple secrets should all be redacted."""
        event_filter = EventFilter()

        text = 'Config: api_key="key123" password: pass456 token=tok789'
        redacted = event_filter._redact_sensitive(text)

        assert "key123" not in redacted
        assert "pass456" not in redacted
        assert "tok789" not in redacted
        assert redacted.count("[REDACTED]") == 3

    def test_redact_case_insensitive(self) -> None:
        """Redaction should be case-insensitive."""
        event_filter = EventFilter()

        text = 'API_KEY="key123" Password: pass456'
        redacted = event_filter._redact_sensitive(text)

        assert "key123" not in redacted
        assert "pass456" not in redacted

    def test_filter_sensitive_data_from_message_event(self) -> None:
        """Sensitive data should be filtered from TaskMessageEvent."""
        event_filter = EventFilter()

        event = TaskMessageEvent(
            task_id="task-1",
            timestamp=datetime.utcnow(),
            message_parts=[
                TextPart(text='Tool called with api_key="secret123"'),
                TextPart(text="Result obtained successfully"),
            ],
            visibility=VisibilityLevel.FULL,
        )

        filtered_event = event_filter.filter_sensitive_data(event)

        # Original event should be unchanged
        assert "secret123" in event.message_parts[0].text

        # Filtered event should have redacted data
        assert "secret123" not in filtered_event.message_parts[0].text
        assert "[REDACTED]" in filtered_event.message_parts[0].text

        # Non-sensitive part should be unchanged
        assert filtered_event.message_parts[1].text == "Result obtained successfully"

    def test_filter_sensitive_data_from_non_message_event(self) -> None:
        """Non-message events should be returned unchanged."""
        event_filter = EventFilter()

        event = TaskStatusEvent(
            task_id="task-1",
            timestamp=datetime.utcnow(),
            state=TaskState.WORKING,
            message="Processing",
            visibility=VisibilityLevel.SUMMARY,
        )

        filtered_event = event_filter.filter_sensitive_data(event)

        assert filtered_event == event

    def test_filter_preserves_event_metadata(self) -> None:
        """Filtering should preserve all event metadata."""
        event_filter = EventFilter()

        original_timestamp = datetime.utcnow()
        event = TaskMessageEvent(
            task_id="task-123",
            timestamp=original_timestamp,
            message_parts=[TextPart(text="Test message")],
            visibility=VisibilityLevel.FULL,
            is_partial=True,
        )

        filtered_event = event_filter.filter_sensitive_data(event)

        assert filtered_event.task_id == "task-123"
        assert filtered_event.timestamp == original_timestamp
        assert filtered_event.visibility == VisibilityLevel.FULL
        assert filtered_event.is_partial is True


class TestFilterEventStream:
    """Test suite for filter_event_stream async function."""

    @pytest.mark.asyncio
    async def test_end_user_sees_summary_only(self) -> None:
        """END_USER role should only see SUMMARY events."""

        async def mock_event_stream():
            """Mock event stream with mixed visibility levels."""
            yield TaskStatusEvent(
                task_id="task-1",
                timestamp=datetime.utcnow(),
                state=TaskState.WORKING,
                visibility=VisibilityLevel.SUMMARY,
            )
            yield TaskMessageEvent(
                task_id="task-1",
                timestamp=datetime.utcnow(),
                message_parts=[TextPart(text="Iteration 1")],
                visibility=VisibilityLevel.FULL,
            )
            yield TaskMessageEvent(
                task_id="task-1",
                timestamp=datetime.utcnow(),
                message_parts=[TextPart(text="Action: read")],
                visibility=VisibilityLevel.SUMMARY,
            )
            yield TaskMessageEvent(
                task_id="task-1",
                timestamp=datetime.utcnow(),
                message_parts=[TextPart(text="Observation: Data loaded")],
                visibility=VisibilityLevel.FULL,
            )
            yield TaskDoneEvent(
                task_id="task-1",
                timestamp=datetime.utcnow(),
                final_state=TaskState.COMPLETED,
            )

        events = []
        async for event in filter_event_stream(mock_event_stream(), user_role="END_USER"):
            events.append(event)

        # Should have 3 events: status (SUMMARY), message (SUMMARY), done (no visibility)
        assert len(events) == 3
        assert isinstance(events[0], TaskStatusEvent)
        assert isinstance(events[1], TaskMessageEvent)
        assert isinstance(events[2], TaskDoneEvent)

        # Should not include FULL visibility events
        message_texts = [
            part.text for e in events if isinstance(e, TaskMessageEvent) for part in e.message_parts
        ]
        assert "Iteration 1" not in message_texts
        assert "Observation: Data loaded" not in message_texts
        assert "Action: read" in message_texts

    @pytest.mark.asyncio
    async def test_developer_sees_all_events(self) -> None:
        """DEVELOPER role should see all SUMMARY and FULL events."""

        async def mock_event_stream():
            """Mock event stream with mixed visibility levels."""
            yield TaskMessageEvent(
                task_id="task-1",
                timestamp=datetime.utcnow(),
                message_parts=[TextPart(text="Summary message")],
                visibility=VisibilityLevel.SUMMARY,
            )
            yield TaskMessageEvent(
                task_id="task-1",
                timestamp=datetime.utcnow(),
                message_parts=[TextPart(text="Full detail message")],
                visibility=VisibilityLevel.FULL,
            )
            yield TaskMessageEvent(
                task_id="task-1",
                timestamp=datetime.utcnow(),
                message_parts=[TextPart(text="Hidden message")],
                visibility=VisibilityLevel.HIDDEN,
            )

        events = []
        async for event in filter_event_stream(mock_event_stream(), user_role="DEVELOPER"):
            events.append(event)

        # Should have 2 events (SUMMARY and FULL, not HIDDEN)
        assert len(events) == 2
        message_texts = [part.text for e in events for part in e.message_parts]
        assert "Summary message" in message_texts
        assert "Full detail message" in message_texts
        assert "Hidden message" not in message_texts

    @pytest.mark.asyncio
    async def test_sensitive_data_redacted(self) -> None:
        """Sensitive data should be redacted from all events."""

        async def mock_event_stream():
            """Mock event stream with sensitive data."""
            yield TaskMessageEvent(
                task_id="task-1",
                timestamp=datetime.utcnow(),
                message_parts=[TextPart(text='Authenticating with api_key="secret123"')],
                visibility=VisibilityLevel.SUMMARY,
            )

        events = []
        async for event in filter_event_stream(mock_event_stream(), user_role="DEVELOPER"):
            events.append(event)

        assert len(events) == 1
        message_text = events[0].message_parts[0].text
        assert "secret123" not in message_text
        assert "[REDACTED]" in message_text

    @pytest.mark.asyncio
    async def test_empty_stream(self) -> None:
        """Empty event stream should be handled gracefully."""

        async def mock_event_stream():
            """Empty stream."""
            return
            yield  # Make this a generator

        events = []
        async for event in filter_event_stream(mock_event_stream(), user_role="END_USER"):
            events.append(event)

        assert len(events) == 0

    @pytest.mark.asyncio
    async def test_admin_sees_all_events(self) -> None:
        """ADMIN role should see all SUMMARY and FULL events."""

        async def mock_event_stream():
            """Mock event stream."""
            yield TaskMessageEvent(
                task_id="task-1",
                timestamp=datetime.utcnow(),
                message_parts=[TextPart(text="Full detail")],
                visibility=VisibilityLevel.FULL,
            )

        events = []
        async for event in filter_event_stream(mock_event_stream(), user_role="ADMIN"):
            events.append(event)

        assert len(events) == 1


class TestEventVisibilityLevels:
    """Test that events have appropriate visibility levels."""

    def test_status_event_has_default_summary_visibility(self) -> None:
        """TaskStatusEvent should default to SUMMARY visibility."""
        event = TaskStatusEvent(
            task_id="task-1",
            timestamp=datetime.utcnow(),
            state=TaskState.WORKING,
        )
        assert event.visibility == VisibilityLevel.SUMMARY

    def test_message_event_has_default_summary_visibility(self) -> None:
        """TaskMessageEvent should default to SUMMARY visibility."""
        event = TaskMessageEvent(
            task_id="task-1",
            timestamp=datetime.utcnow(),
            message_parts=[TextPart(text="Test")],
        )
        assert event.visibility == VisibilityLevel.SUMMARY

    def test_error_event_has_default_summary_visibility(self) -> None:
        """TaskErrorEvent should default to SUMMARY visibility."""
        event = TaskErrorEvent(
            task_id="task-1",
            timestamp=datetime.utcnow(),
            error_code="TEST_ERROR",
            error_message="Test error",
        )
        assert event.visibility == VisibilityLevel.SUMMARY

    def test_can_override_visibility_level(self) -> None:
        """Visibility level should be overridable."""
        event = TaskMessageEvent(
            task_id="task-1",
            timestamp=datetime.utcnow(),
            message_parts=[TextPart(text="Detailed iteration info")],
            visibility=VisibilityLevel.FULL,
        )
        assert event.visibility == VisibilityLevel.FULL
