"""Integration tests for event streaming with visibility filtering.

This module tests the complete event streaming pipeline with visibility
filtering in autonomous skill execution (TASK-013).
"""

from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from omniforge.agents.events import (
    TaskDoneEvent,
    TaskErrorEvent,
    TaskMessageEvent,
    TaskStatusEvent,
)
from omniforge.skills.autonomous_executor import AutonomousSkillExecutor
from omniforge.skills.config import AutonomousConfig
from omniforge.skills.context_loader import ContextLoader, LoadedContext
from omniforge.skills.event_filter import filter_event_stream
from omniforge.skills.models import Skill, SkillMetadata
from omniforge.skills.string_substitutor import StringSubstitutor, SubstitutedContent
from omniforge.tools.base import ToolDefinition
from omniforge.tools.executor import ToolExecutor
from omniforge.tools.registry import ToolRegistry
from omniforge.tools.types import ToolType, VisibilityLevel


@pytest.fixture
def mock_skill() -> Skill:
    """Create a mock skill for testing."""
    return Skill(
        metadata=SkillMetadata(
            name="test-skill",
            description="A test skill for integration testing",
            allowed_tools=["read", "write"],
        ),
        content="Test skill instructions.\n\nProcess: $ARGUMENTS",
        path=Path("/tmp/test-skill/SKILL.md"),
        base_path=Path("/tmp/test-skill"),
        storage_layer="global",
    )


@pytest.fixture
def mock_tool_registry() -> ToolRegistry:
    """Create a mock tool registry."""
    registry = Mock(spec=ToolRegistry)
    registry.list_tools.return_value = ["read", "write"]

    def_read = ToolDefinition(
        name="read",
        type=ToolType.FILE_READ,
        description="Read a file",
        parameters=[],
    )
    def_write = ToolDefinition(
        name="write",
        type=ToolType.FILE_WRITE,
        description="Write to a file",
        parameters=[],
    )

    registry.get_definition.side_effect = lambda name: {
        "read": def_read,
        "write": def_write,
    }[name]

    return registry


@pytest.fixture
def mock_tool_executor() -> ToolExecutor:
    """Create a mock tool executor."""
    return Mock(spec=ToolExecutor)


@pytest.fixture
def mock_context_loader(mock_skill: Skill) -> Mock:
    """Create a mock context loader."""
    loader = Mock()
    loader.load_initial_context.return_value = LoadedContext(
        skill_content=mock_skill.content,
        available_files={},
        skill_dir=Path("/tmp/test-skill"),
        line_count=10,
    )
    return loader


@pytest.fixture
def mock_string_substitutor() -> Mock:
    """Create a mock string substitutor."""
    substitutor = Mock()
    substitutor.substitute.return_value = SubstitutedContent(
        content="Test skill instructions.\n\nProcess: test request",
        substitutions_made=1,
        undefined_vars=[],
    )
    return substitutor


class TestEventStreamingWithVisibilityFiltering:
    """Integration tests for event streaming with visibility filtering."""

    @pytest.mark.asyncio
    async def test_end_user_sees_summary_events_only(
        self,
        mock_skill: Skill,
        mock_tool_registry: ToolRegistry,
        mock_tool_executor: ToolExecutor,
        mock_context_loader: ContextLoader,
        mock_string_substitutor: StringSubstitutor,
    ) -> None:
        """END_USER should only see SUMMARY events, not detailed FULL events."""
        executor = AutonomousSkillExecutor(
            skill=mock_skill,
            tool_registry=mock_tool_registry,
            tool_executor=mock_tool_executor,
            context_loader=mock_context_loader,
            string_substitutor=mock_string_substitutor,
        )

        # Mock the ReasoningEngine
        with patch("omniforge.skills.autonomous_executor.ReasoningEngine") as mock_engine_class:
            mock_engine = Mock()
            mock_engine_class.return_value = mock_engine

            call_count = 0

            async def mock_llm_call(*args, **kwargs):
                nonlocal call_count
                call_count += 1

                if call_count == 1:
                    # First iteration: return action
                    mock_result = Mock()
                    mock_result.success = True
                    content = (
                        '{"thought": "Need to read file", "action": "read", '
                        '"action_input": {}, "is_final": false}'
                    )
                    mock_result.value = {"content": content}
                    return mock_result
                else:
                    # Second iteration: return final answer
                    mock_result = Mock()
                    mock_result.success = True
                    content = '{"thought": "Done", "final_answer": "Success", "is_final": true}'
                    mock_result.value = {"content": content}
                    return mock_result

            mock_engine.call_llm = AsyncMock(side_effect=mock_llm_call)

            # Mock tool call to succeed
            mock_tool_result = Mock()
            mock_tool_result.success = True
            mock_tool_result.value = {"data": "test"}
            mock_tool_result.error = None
            mock_engine.call_tool = AsyncMock(return_value=mock_tool_result)

            # Filter events for END_USER
            events = []
            event_stream = executor.execute("test request", "task-1", "session-1")
            async for event in filter_event_stream(event_stream, user_role="END_USER"):
                events.append(event)

        # END_USER should see:
        # - TaskStatusEvent (SUMMARY)
        # - TaskMessageEvent for "Action: read" (SUMMARY)
        # - TaskMessageEvent for "Final answer" (SUMMARY)
        # - TaskDoneEvent (no visibility)

        # Should NOT see:
        # - Iteration progress (FULL)
        # - Thought messages (FULL)
        # - Observation messages (FULL)

        message_events = [e for e in events if isinstance(e, TaskMessageEvent)]
        message_texts = [part.text for e in message_events for part in e.message_parts]

        # Verify SUMMARY events are present
        assert any("Action: read" in text for text in message_texts)
        assert any("Final answer" in text for text in message_texts)

        # Verify FULL events are filtered out
        assert not any("Iteration" in text for text in message_texts)
        assert not any("Thought:" in text for text in message_texts)
        assert not any("Observation:" in text for text in message_texts)

    @pytest.mark.asyncio
    async def test_developer_sees_all_events(
        self,
        mock_skill: Skill,
        mock_tool_registry: ToolRegistry,
        mock_tool_executor: ToolExecutor,
        mock_context_loader: ContextLoader,
        mock_string_substitutor: StringSubstitutor,
    ) -> None:
        """DEVELOPER should see all SUMMARY and FULL events."""
        executor = AutonomousSkillExecutor(
            skill=mock_skill,
            tool_registry=mock_tool_registry,
            tool_executor=mock_tool_executor,
            context_loader=mock_context_loader,
            string_substitutor=mock_string_substitutor,
        )

        # Mock the ReasoningEngine
        with patch("omniforge.skills.autonomous_executor.ReasoningEngine") as mock_engine_class:
            mock_engine = Mock()
            mock_engine_class.return_value = mock_engine

            # Mock LLM call to return final answer immediately
            mock_llm_result = Mock()
            mock_llm_result.success = True
            mock_llm_result.value = {
                "content": '{"thought": "Done", "final_answer": "Success", "is_final": true}'
            }
            mock_engine.call_llm = AsyncMock(return_value=mock_llm_result)

            # Filter events for DEVELOPER
            events = []
            event_stream = executor.execute("test request", "task-1", "session-1")
            async for event in filter_event_stream(event_stream, user_role="DEVELOPER"):
                events.append(event)

        # DEVELOPER should see all events including FULL visibility
        message_events = [e for e in events if isinstance(e, TaskMessageEvent)]
        message_texts = [part.text for e in message_events for part in e.message_parts]

        # Verify all event types are present
        assert any("Iteration" in text for text in message_texts)
        assert any("Thought:" in text for text in message_texts)
        assert any("Final answer" in text for text in message_texts)

    @pytest.mark.asyncio
    async def test_sensitive_data_redacted_in_stream(
        self,
        mock_skill: Skill,
        mock_tool_registry: ToolRegistry,
        mock_tool_executor: ToolExecutor,
        mock_context_loader: ContextLoader,
        mock_string_substitutor: StringSubstitutor,
    ) -> None:
        """Sensitive data should be automatically redacted from event stream."""
        executor = AutonomousSkillExecutor(
            skill=mock_skill,
            tool_registry=mock_tool_registry,
            tool_executor=mock_tool_executor,
            context_loader=mock_context_loader,
            string_substitutor=mock_string_substitutor,
        )

        # Mock the ReasoningEngine
        with patch("omniforge.skills.autonomous_executor.ReasoningEngine") as mock_engine_class:
            mock_engine = Mock()
            mock_engine_class.return_value = mock_engine

            call_count = 0

            async def mock_llm_call(*args, **kwargs):
                nonlocal call_count
                call_count += 1

                if call_count == 1:
                    # Return action with sensitive data in thought
                    mock_result = Mock()
                    mock_result.success = True
                    content = (
                        '{"thought": "Authenticating with api_key=secret123", '
                        '"action": "read", "action_input": {}, "is_final": false}'
                    )
                    mock_result.value = {"content": content}
                    return mock_result
                else:
                    # Return final answer
                    mock_result = Mock()
                    mock_result.success = True
                    content = '{"final_answer": "Done", "is_final": true}'
                    mock_result.value = {"content": content}
                    return mock_result

            mock_engine.call_llm = AsyncMock(side_effect=mock_llm_call)

            # Mock tool call
            mock_tool_result = Mock()
            mock_tool_result.success = True
            mock_tool_result.value = "Data with password: secret456"
            mock_tool_result.error = None
            mock_engine.call_tool = AsyncMock(return_value=mock_tool_result)

            # Filter events for DEVELOPER (so we see all events)
            events = []
            event_stream = executor.execute("test request", "task-1", "session-1")
            async for event in filter_event_stream(event_stream, user_role="DEVELOPER"):
                events.append(event)

        # Verify sensitive data is redacted
        message_events = [e for e in events if isinstance(e, TaskMessageEvent)]
        all_text = " ".join(part.text for e in message_events for part in e.message_parts)

        # Sensitive values should be redacted
        assert "secret123" not in all_text
        assert "secret456" not in all_text
        assert "[REDACTED]" in all_text

    @pytest.mark.asyncio
    async def test_events_have_visibility_levels(
        self,
        mock_skill: Skill,
        mock_tool_registry: ToolRegistry,
        mock_tool_executor: ToolExecutor,
        mock_context_loader: ContextLoader,
        mock_string_substitutor: StringSubstitutor,
    ) -> None:
        """All relevant events should have visibility levels set."""
        executor = AutonomousSkillExecutor(
            skill=mock_skill,
            tool_registry=mock_tool_registry,
            tool_executor=mock_tool_executor,
            context_loader=mock_context_loader,
            string_substitutor=mock_string_substitutor,
        )

        # Mock the ReasoningEngine
        with patch("omniforge.skills.autonomous_executor.ReasoningEngine") as mock_engine_class:
            mock_engine = Mock()
            mock_engine_class.return_value = mock_engine

            # Mock LLM call
            mock_llm_result = Mock()
            mock_llm_result.success = True
            mock_llm_result.value = {
                "content": '{"thought": "Done", "final_answer": "Success", "is_final": true}'
            }
            mock_engine.call_llm = AsyncMock(return_value=mock_llm_result)

            # Collect all events (no filtering)
            events = []
            async for event in executor.execute("test request", "task-1", "session-1"):
                events.append(event)

        # Verify events have visibility attribute
        status_events = [e for e in events if isinstance(e, TaskStatusEvent)]
        message_events = [e for e in events if isinstance(e, TaskMessageEvent)]
        error_events = [e for e in events if isinstance(e, TaskErrorEvent)]

        # All TaskStatusEvent should have visibility
        for event in status_events:
            assert hasattr(event, "visibility")
            assert isinstance(event.visibility, VisibilityLevel)

        # All TaskMessageEvent should have visibility
        for event in message_events:
            assert hasattr(event, "visibility")
            assert isinstance(event.visibility, VisibilityLevel)

        # All TaskErrorEvent should have visibility (if any)
        for event in error_events:
            assert hasattr(event, "visibility")
            assert isinstance(event.visibility, VisibilityLevel)

    @pytest.mark.asyncio
    async def test_visibility_levels_are_appropriate(
        self,
        mock_skill: Skill,
        mock_tool_registry: ToolRegistry,
        mock_tool_executor: ToolExecutor,
        mock_context_loader: ContextLoader,
        mock_string_substitutor: StringSubstitutor,
    ) -> None:
        """Events should have appropriate visibility levels based on their content."""
        executor = AutonomousSkillExecutor(
            skill=mock_skill,
            tool_registry=mock_tool_registry,
            tool_executor=mock_tool_executor,
            context_loader=mock_context_loader,
            string_substitutor=mock_string_substitutor,
        )

        # Mock the ReasoningEngine
        with patch("omniforge.skills.autonomous_executor.ReasoningEngine") as mock_engine_class:
            mock_engine = Mock()
            mock_engine_class.return_value = mock_engine

            call_count = 0

            async def mock_llm_call(*args, **kwargs):
                nonlocal call_count
                call_count += 1

                if call_count == 1:
                    # Return action
                    mock_result = Mock()
                    mock_result.success = True
                    content = (
                        '{"thought": "Reading file", "action": "read", '
                        '"action_input": {}, "is_final": false}'
                    )
                    mock_result.value = {"content": content}
                    return mock_result
                else:
                    # Return final answer
                    mock_result = Mock()
                    mock_result.success = True
                    content = '{"final_answer": "Done", "is_final": true}'
                    mock_result.value = {"content": content}
                    return mock_result

            mock_engine.call_llm = AsyncMock(side_effect=mock_llm_call)

            # Mock tool call
            mock_tool_result = Mock()
            mock_tool_result.success = True
            mock_tool_result.value = {"data": "test"}
            mock_tool_result.error = None
            mock_engine.call_tool = AsyncMock(return_value=mock_tool_result)

            # Collect all events
            events = []
            async for event in executor.execute("test request", "task-1", "session-1"):
                events.append(event)

        # Check visibility levels
        for event in events:
            if isinstance(event, TaskMessageEvent):
                text = " ".join(part.text for part in event.message_parts)

                # Iteration and detailed messages should be FULL
                if "Iteration" in text or "Thought:" in text or "Observation:" in text:
                    assert event.visibility == VisibilityLevel.FULL

                # High-level progress should be SUMMARY
                elif "Action:" in text or "Final answer" in text:
                    assert event.visibility == VisibilityLevel.SUMMARY
