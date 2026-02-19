"""Tests for MasterResponseGenerator conversation context integration.

This module tests the integration of conversation history with MasterResponseGenerator,
including context assembly and intent analyzer integration.
"""

from datetime import datetime
from typing import AsyncIterator
from uuid import uuid4

import pytest

from omniforge.agents.events import TaskMessageEvent
from omniforge.agents.master_agent import MasterAgent
from omniforge.agents.models import TextPart
from omniforge.chat.master_response_generator import MasterResponseGenerator
from omniforge.conversation.intent_analyzer import LLMIntentAnalyzer
from omniforge.conversation.models import Message, MessageRole
from omniforge.tasks.models import Task


class MockMasterAgent(MasterAgent):
    """Mock Master Agent for testing."""

    def __init__(self) -> None:
        """Initialize mock master agent."""
        super().__init__()
        self._last_task: Task | None = None

    async def process_task(self, task: Task) -> AsyncIterator:
        """Process task and capture for testing."""
        self._last_task = task

        # Yield a simple response event
        yield TaskMessageEvent(
            task_id=task.id,
            message_parts=[TextPart(text="Mock response")],
            timestamp=datetime.utcnow(),
        )


class TestMasterResponseGeneratorContext:
    """Tests for MasterResponseGenerator conversation context passing."""

    @pytest.mark.asyncio
    async def test_generate_stream_without_history_works(self) -> None:
        """generate_stream should work without conversation history."""
        generator = MasterResponseGenerator()
        # Inject mock agent to avoid real LLM calls in unit tests
        mock_agent = MockMasterAgent()
        generator._master_agent = mock_agent
        chunks = []

        async for chunk in generator.generate_stream("Test message"):
            chunks.append(chunk)

        # Should receive response chunks from the mock agent
        assert len(chunks) > 0

    @pytest.mark.asyncio
    async def test_generate_stream_passes_empty_list_for_no_history(self) -> None:
        """generate_stream should handle empty conversation history."""
        generator = MasterResponseGenerator()
        mock_agent = MockMasterAgent()
        generator._master_agent = mock_agent
        chunks = []

        async for chunk in generator.generate_stream("Test", conversation_history=[]):
            chunks.append(chunk)

        # Should work with empty history and receive mock response
        assert len(chunks) > 0

    @pytest.mark.asyncio
    async def test_generate_stream_includes_context_in_task_messages(self) -> None:
        """generate_stream should include conversation context in task messages."""
        mock_agent = MockMasterAgent()
        generator = MasterResponseGenerator()
        generator._master_agent = mock_agent

        # Create conversation history
        history = [
            Message(
                id=uuid4(),
                conversation_id=uuid4(),
                role=MessageRole.USER,
                content="Previous question",
                created_at=datetime.utcnow(),
            ),
            Message(
                id=uuid4(),
                conversation_id=uuid4(),
                role=MessageRole.ASSISTANT,
                content="Previous answer",
                created_at=datetime.utcnow(),
            ),
        ]

        # Generate with history
        chunks = []
        async for chunk in generator.generate_stream(
            "Current question", conversation_history=history
        ):
            chunks.append(chunk)

        # Verify task includes context messages
        assert mock_agent._last_task is not None
        assert len(mock_agent._last_task.messages) == 3  # 2 context + 1 current

        # Check context messages
        assert mock_agent._last_task.messages[0].role == "user"
        assert mock_agent._last_task.messages[0].parts[0].text == "Previous question"
        assert mock_agent._last_task.messages[1].role == "agent"  # "assistant" -> "agent"
        assert mock_agent._last_task.messages[1].parts[0].text == "Previous answer"

        # Check current message
        assert mock_agent._last_task.messages[2].role == "user"
        assert mock_agent._last_task.messages[2].parts[0].text == "Current question"

    @pytest.mark.asyncio
    async def test_generate_stream_limits_context_to_20_messages(self) -> None:
        """generate_stream should limit context to most recent 20 messages."""
        mock_agent = MockMasterAgent()
        generator = MasterResponseGenerator()
        generator._master_agent = mock_agent

        # Create 25 messages of history
        conversation_id = uuid4()
        history = []
        for i in range(25):
            role = MessageRole.USER if i % 2 == 0 else MessageRole.ASSISTANT
            history.append(
                Message(
                    id=uuid4(),
                    conversation_id=conversation_id,
                    role=role,
                    content=f"Message {i}",
                    created_at=datetime.utcnow(),
                )
            )

        # Generate with history
        chunks = []
        async for chunk in generator.generate_stream("Current", conversation_history=history):
            chunks.append(chunk)

        # Verify task includes only last 20 + current = 21 messages
        assert mock_agent._last_task is not None
        assert len(mock_agent._last_task.messages) == 21

        # Check it's the last 20 from history (messages 5-24)
        assert mock_agent._last_task.messages[0].parts[0].text == "Message 5"
        assert mock_agent._last_task.messages[19].parts[0].text == "Message 24"
        assert mock_agent._last_task.messages[20].parts[0].text == "Current"

    @pytest.mark.asyncio
    async def test_generate_stream_handles_message_role_enum_values(self) -> None:
        """generate_stream should correctly handle MessageRole enum values."""
        mock_agent = MockMasterAgent()
        generator = MasterResponseGenerator()
        generator._master_agent = mock_agent

        # Create history with MessageRole enums
        history = [
            Message(
                id=uuid4(),
                conversation_id=uuid4(),
                role=MessageRole.USER,  # Enum value
                content="User message",
                created_at=datetime.utcnow(),
            ),
            Message(
                id=uuid4(),
                conversation_id=uuid4(),
                role=MessageRole.ASSISTANT,  # Enum value
                content="Assistant message",
                created_at=datetime.utcnow(),
            ),
        ]

        chunks = []
        async for chunk in generator.generate_stream("New", conversation_history=history):
            chunks.append(chunk)

        # Verify roles are properly converted to task roles (assistant -> agent)
        assert mock_agent._last_task.messages[0].role == "user"
        assert mock_agent._last_task.messages[1].role == "agent"  # "assistant" -> "agent"

    @pytest.mark.asyncio
    async def test_init_accepts_intent_analyzer_parameter(self) -> None:
        """MasterResponseGenerator should accept optional intent_analyzer without error.

        The intent_analyzer parameter is kept for API backward compatibility
        but is no longer used internally (MasterAgent now uses the ReAct loop
        with platform tools for routing instead of keyword/LLM intent analysis).
        """
        analyzer = LLMIntentAnalyzer(model="gpt-4o-mini")

        # Should initialize without error even though analyzer is not used internally
        generator = MasterResponseGenerator(intent_analyzer=analyzer)

        # Master agent should be created successfully
        assert generator._master_agent is not None

    @pytest.mark.asyncio
    async def test_init_without_intent_analyzer_works(self) -> None:
        """MasterResponseGenerator should work without intent_analyzer."""
        # Should initialize without error
        generator = MasterResponseGenerator()

        # Master agent should exist without analyzer
        assert generator._master_agent is not None

    @pytest.mark.asyncio
    async def test_count_tokens_returns_valid_count(self) -> None:
        """count_tokens should return valid token count."""
        generator = MasterResponseGenerator()

        count = generator.count_tokens("Hello, world!")

        assert count > 0
        assert isinstance(count, int)

    @pytest.mark.asyncio
    async def test_context_preserves_message_timestamps(self) -> None:
        """generate_stream should preserve original message timestamps."""
        mock_agent = MockMasterAgent()
        generator = MasterResponseGenerator()
        generator._master_agent = mock_agent

        # Create history with specific timestamps
        timestamp1 = datetime(2024, 1, 1, 12, 0, 0)
        timestamp2 = datetime(2024, 1, 1, 12, 1, 0)

        history = [
            Message(
                id=uuid4(),
                conversation_id=uuid4(),
                role=MessageRole.USER,
                content="Message 1",
                created_at=timestamp1,
            ),
            Message(
                id=uuid4(),
                conversation_id=uuid4(),
                role=MessageRole.ASSISTANT,
                content="Message 2",
                created_at=timestamp2,
            ),
        ]

        chunks = []
        async for chunk in generator.generate_stream("Current", conversation_history=history):
            chunks.append(chunk)

        # Verify timestamps are preserved
        assert mock_agent._last_task.messages[0].created_at == timestamp1
        assert mock_agent._last_task.messages[1].created_at == timestamp2

    @pytest.mark.asyncio
    async def test_generate_stream_with_none_history_uses_empty_context(self) -> None:
        """generate_stream should handle None history as empty context."""
        mock_agent = MockMasterAgent()
        generator = MasterResponseGenerator()
        generator._master_agent = mock_agent

        chunks = []
        async for chunk in generator.generate_stream(
            "Test message", conversation_history=None
        ):
            chunks.append(chunk)

        # Should have only the current message
        assert len(mock_agent._last_task.messages) == 1
        assert mock_agent._last_task.messages[0].parts[0].text == "Test message"
