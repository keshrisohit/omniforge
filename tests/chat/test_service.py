"""Integration tests for ChatService.

This module tests the ChatService integration with ResponseGenerator,
testing the complete flow of chat processing, event streaming, and
conversation ID management.
"""

from typing import AsyncIterator
from uuid import uuid4

import pytest

from omniforge.chat.models import ChatRequest
from omniforge.chat.response_generator import ResponseGenerator
from omniforge.chat.service import ChatService


class MockResponseGenerator(ResponseGenerator):
    """Mock response generator for testing."""

    def __init__(self, chunks: list[str]) -> None:
        """Initialize mock with predefined chunks.

        Args:
            chunks: List of response chunks to yield
        """
        super().__init__()
        self._chunks = chunks

    async def generate_stream(
        self,
        message: str,
        conversation_history: list | None = None,
        session_id: str = "default",
    ) -> AsyncIterator[str]:
        """Generate predefined chunks.

        Args:
            message: User's input message (ignored in mock)
            conversation_history: Conversation history (ignored in mock)
            session_id: Session identifier (ignored in mock)

        Yields:
            Predefined response chunks
        """
        for chunk in self._chunks:
            yield chunk


class TestChatService:
    """Integration tests for ChatService class."""

    @pytest.mark.asyncio
    async def test_process_chat_yields_chunks(self) -> None:
        """process_chat should yield chunk events for each response chunk."""
        chunks = ["Hello, ", "how ", "are ", "you?"]
        mock_generator = MockResponseGenerator(chunks)
        service = ChatService(response_generator=mock_generator)
        request = ChatRequest(message="Hi")

        events = []
        async for event in service.process_chat(request):
            events.append(event)

        # Should have 4 chunk events + 1 done event = 5 total
        assert len(events) == 5

        # First 4 should be chunk events
        for i in range(4):
            assert events[i].startswith("event: chunk")
            assert chunks[i] in events[i]

    @pytest.mark.asyncio
    async def test_process_chat_ends_with_done(self) -> None:
        """process_chat should end with done event after all chunks."""
        mock_generator = MockResponseGenerator(["Response chunk"])
        service = ChatService(response_generator=mock_generator)
        request = ChatRequest(message="Test")

        events = []
        async for event in service.process_chat(request):
            events.append(event)

        # Last event should be done event
        assert events[-1].startswith("event: done")
        assert "conversation_id" in events[-1]
        assert "usage" in events[-1]

    @pytest.mark.asyncio
    async def test_process_chat_generates_conversation_id(self) -> None:
        """process_chat should generate conversation_id when not provided."""
        mock_generator = MockResponseGenerator(["Response"])
        service = ChatService(response_generator=mock_generator)
        request = ChatRequest(message="Test message")

        events = []
        async for event in service.process_chat(request):
            events.append(event)

        # Done event should contain a generated conversation_id
        done_event = events[-1]
        assert "conversation_id" in done_event
        # Should be a valid UUID format
        assert "-" in done_event  # UUIDs contain hyphens

    @pytest.mark.asyncio
    async def test_process_chat_preserves_conversation_id(self) -> None:
        """process_chat should use provided conversation_id from request."""
        mock_generator = MockResponseGenerator(["Response"])
        service = ChatService(response_generator=mock_generator)
        conversation_id = uuid4()
        request = ChatRequest(message="Test", conversation_id=conversation_id)

        events = []
        async for event in service.process_chat(request):
            events.append(event)

        # Done event should contain the provided conversation_id
        done_event = events[-1]
        assert str(conversation_id) in done_event
