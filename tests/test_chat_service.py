"""Tests for chat service request processing orchestration.

This module tests the ChatService class that coordinates chat request
processing, response generation, and SSE event streaming.
"""

from typing import AsyncIterator
from uuid import uuid4

import pytest

from omniforge.chat.models import ChatRequest
from omniforge.chat.response_generator import ResponseGenerator
from omniforge.chat.service import ChatService


class MockResponseGenerator(ResponseGenerator):
    """Mock response generator for testing."""

    def __init__(self, chunks: list[str], should_raise: bool = False) -> None:
        """Initialize mock with predefined chunks.

        Args:
            chunks: List of response chunks to yield
            should_raise: If True, raises an exception during streaming
        """
        super().__init__()
        self._chunks = chunks
        self._should_raise = should_raise

    async def generate_stream(
        self,
        message: str,
        conversation_history: list | None = None,
        session_id: str = "default",
    ) -> AsyncIterator[str]:
        """Generate predefined chunks or raise an exception.

        Args:
            message: User's input message (ignored in mock)
            conversation_history: Optional conversation history (ignored in mock)
            session_id: Session identifier (ignored in mock)

        Yields:
            Predefined response chunks

        Raises:
            RuntimeError: If should_raise is True
        """
        if self._should_raise:
            # Yield first chunk, then raise
            if self._chunks:
                yield self._chunks[0]
            raise RuntimeError("Mock stream error")

        for chunk in self._chunks:
            yield chunk


class TestChatService:
    """Tests for ChatService class."""

    def test_init_with_default_response_generator(self) -> None:
        """ChatService should create default response generator if none provided."""
        from omniforge.chat.master_response_generator import MasterResponseGenerator

        service = ChatService()
        assert service._response_generator is not None
        assert isinstance(service._response_generator, MasterResponseGenerator)

    def test_init_with_custom_response_generator(self) -> None:
        """ChatService should use provided ResponseGenerator."""
        mock_generator = MockResponseGenerator(["test"])
        service = ChatService(response_generator=mock_generator)
        assert service._response_generator is mock_generator

    @pytest.mark.asyncio
    async def test_process_chat_generates_conversation_id_when_not_provided(self) -> None:
        """process_chat should generate UUID when conversation_id not in request."""
        mock_generator = MockResponseGenerator(["Hello"])
        service = ChatService(response_generator=mock_generator)
        request = ChatRequest(message="Test message")

        events = []
        async for event in service.process_chat(request):
            events.append(event)

        # Should have chunk event and done event
        assert len(events) == 2
        # Done event should contain a generated conversation_id
        assert "conversation_id" in events[1]
        assert events[1].startswith("event: done")

    @pytest.mark.asyncio
    async def test_process_chat_uses_provided_conversation_id(self) -> None:
        """process_chat should use conversation_id from request if provided."""
        mock_generator = MockResponseGenerator(["Response"])
        service = ChatService(response_generator=mock_generator)
        conversation_id = uuid4()
        request = ChatRequest(message="Test", conversation_id=conversation_id)

        events = []
        async for event in service.process_chat(request):
            events.append(event)

        # Done event should contain the provided conversation_id
        assert len(events) == 2
        done_event = events[1]
        assert str(conversation_id) in done_event

    @pytest.mark.asyncio
    async def test_process_chat_yields_chunk_events_for_each_chunk(self) -> None:
        """process_chat should yield chunk event for each response chunk."""
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

        # Last should be done event
        assert events[4].startswith("event: done")

    @pytest.mark.asyncio
    async def test_process_chat_formats_chunk_events_as_sse(self) -> None:
        """process_chat should format chunks as proper SSE events."""
        mock_generator = MockResponseGenerator(["Test chunk"])
        service = ChatService(response_generator=mock_generator)
        request = ChatRequest(message="Test")

        events = []
        async for event in service.process_chat(request):
            events.append(event)

        chunk_event = events[0]
        # SSE format: event: chunk\ndata: {...}\n\n
        assert chunk_event.startswith("event: chunk\n")
        assert "data:" in chunk_event
        assert chunk_event.endswith("\n\n")
        assert '"content": "Test chunk"' in chunk_event

    @pytest.mark.asyncio
    async def test_process_chat_yields_done_event_with_conversation_id(self) -> None:
        """process_chat should yield done event with conversation_id."""
        mock_generator = MockResponseGenerator(["Response"])
        service = ChatService(response_generator=mock_generator)
        conversation_id = uuid4()
        request = ChatRequest(message="Test", conversation_id=conversation_id)

        events = []
        async for event in service.process_chat(request):
            events.append(event)

        done_event = events[1]
        assert done_event.startswith("event: done")
        assert "conversation_id" in done_event
        assert str(conversation_id) in done_event

    @pytest.mark.asyncio
    async def test_process_chat_yields_done_event_with_usage_info(self) -> None:
        """process_chat should yield done event with token usage information."""
        mock_generator = MockResponseGenerator(["Response text here"])
        service = ChatService(response_generator=mock_generator)
        request = ChatRequest(message="Test")

        events = []
        async for event in service.process_chat(request):
            events.append(event)

        done_event = events[1]
        assert done_event.startswith("event: done")
        assert "usage" in done_event
        assert "tokens" in done_event

    @pytest.mark.asyncio
    async def test_process_chat_accumulates_content_for_token_counting(self) -> None:
        """process_chat should accumulate all chunks for token counting."""
        chunks = ["Part1", "Part2", "Part3"]
        mock_generator = MockResponseGenerator(chunks)
        service = ChatService(response_generator=mock_generator)
        request = ChatRequest(message="Test")

        events = []
        async for event in service.process_chat(request):
            events.append(event)

        done_event = events[-1]
        # Token count should be based on total accumulated content
        # "Part1Part2Part3" = 15 chars -> ~3-4 tokens
        assert "tokens" in done_event
        assert '"tokens": 3' in done_event or '"tokens": 4' in done_event

    @pytest.mark.asyncio
    async def test_process_chat_yields_error_event_on_exception(self) -> None:
        """process_chat should yield error event when exception occurs."""
        mock_generator = MockResponseGenerator(["Chunk1", "Chunk2"], should_raise=True)
        service = ChatService(response_generator=mock_generator)
        request = ChatRequest(message="Test")

        events = []
        async for event in service.process_chat(request):
            events.append(event)

        # Should have 1 chunk event before error + 1 error event
        assert len(events) == 2
        assert events[0].startswith("event: chunk")
        assert events[1].startswith("event: error")

    @pytest.mark.asyncio
    async def test_process_chat_error_event_has_processing_error_code(self) -> None:
        """process_chat error event should use 'processing_error' code."""
        mock_generator = MockResponseGenerator(["Test"], should_raise=True)
        service = ChatService(response_generator=mock_generator)
        request = ChatRequest(message="Test")

        events = []
        async for event in service.process_chat(request):
            events.append(event)

        error_event = events[-1]
        assert '"code": "processing_error"' in error_event

    @pytest.mark.asyncio
    async def test_process_chat_error_event_includes_exception_message(self) -> None:
        """process_chat error event should include exception message."""
        mock_generator = MockResponseGenerator(["Test"], should_raise=True)
        service = ChatService(response_generator=mock_generator)
        request = ChatRequest(message="Test")

        events = []
        async for event in service.process_chat(request):
            events.append(event)

        error_event = events[-1]
        assert "Mock stream error" in error_event
        assert '"message"' in error_event

    @pytest.mark.asyncio
    async def test_process_chat_with_empty_response(self) -> None:
        """process_chat should handle empty response (no chunks)."""
        mock_generator = MockResponseGenerator([])
        service = ChatService(response_generator=mock_generator)
        request = ChatRequest(message="Test")

        events = []
        async for event in service.process_chat(request):
            events.append(event)

        # Should only have done event (no chunks)
        assert len(events) == 1
        assert events[0].startswith("event: done")
        # Token count should be at least 1 (minimum)
        assert "tokens" in events[0]

    @pytest.mark.asyncio
    async def test_process_chat_with_single_chunk(self) -> None:
        """process_chat should work correctly with single chunk."""
        mock_generator = MockResponseGenerator(["Single chunk response"])
        service = ChatService(response_generator=mock_generator)
        request = ChatRequest(message="Test")

        events = []
        async for event in service.process_chat(request):
            events.append(event)

        # Should have 1 chunk + 1 done = 2 events
        assert len(events) == 2
        assert events[0].startswith("event: chunk")
        assert "Single chunk response" in events[0]
        assert events[1].startswith("event: done")

    @pytest.mark.asyncio
    async def test_process_chat_formats_done_event_as_sse(self) -> None:
        """process_chat should format done event as proper SSE."""
        mock_generator = MockResponseGenerator(["Response"])
        service = ChatService(response_generator=mock_generator)
        request = ChatRequest(message="Test")

        events = []
        async for event in service.process_chat(request):
            events.append(event)

        done_event = events[1]
        # SSE format: event: done\ndata: {...}\n\n
        assert done_event.startswith("event: done\n")
        assert "data:" in done_event
        assert done_event.endswith("\n\n")

    @pytest.mark.asyncio
    async def test_process_chat_formats_error_event_as_sse(self) -> None:
        """process_chat should format error event as proper SSE."""
        mock_generator = MockResponseGenerator(["Test"], should_raise=True)
        service = ChatService(response_generator=mock_generator)
        request = ChatRequest(message="Test")

        events = []
        async for event in service.process_chat(request):
            events.append(event)

        error_event = events[-1]
        # SSE format: event: error\ndata: {...}\n\n
        assert error_event.startswith("event: error\n")
        assert "data:" in error_event
        assert error_event.endswith("\n\n")
