"""Tests for ChatService conversation storage and context passing.

This module tests the integration of conversation repository with ChatService,
including storage, retrieval, error handling, and backward compatibility.
"""

from typing import AsyncIterator
from uuid import UUID, uuid4

import pytest

from omniforge.chat.models import ChatRequest
from omniforge.chat.response_generator import ResponseGenerator
from omniforge.chat.service import ChatService
from omniforge.conversation.memory_repository import InMemoryConversationRepository
from omniforge.conversation.models import MessageRole


class MockResponseGenerator(ResponseGenerator):
    """Mock response generator for testing."""

    def __init__(self, chunks: list[str]) -> None:
        """Initialize mock with predefined chunks.

        Args:
            chunks: List of response chunks to yield
        """
        super().__init__()
        self._chunks = chunks
        self._last_conversation_history: list = []

    async def generate_stream(
        self,
        message: str,
        conversation_history: list | None = None,
        session_id: str = "default",
    ) -> AsyncIterator[str]:
        """Generate predefined chunks and capture conversation history.

        Args:
            message: User's input message (ignored in mock)
            conversation_history: Conversation history passed to generator
            session_id: Session identifier (ignored in mock)

        Yields:
            Predefined response chunks
        """
        # Capture the conversation history for testing
        self._last_conversation_history = conversation_history or []

        for chunk in self._chunks:
            yield chunk


class FailingRepository(InMemoryConversationRepository):
    """Mock repository that fails on specific operations."""

    def __init__(
        self,
        fail_create: bool = False,
        fail_get_messages: bool = False,
        fail_add_message: bool = False,
    ) -> None:
        """Initialize failing repository.

        Args:
            fail_create: Whether to fail on create_conversation
            fail_get_messages: Whether to fail on get_recent_messages
            fail_add_message: Whether to fail on add_message
        """
        super().__init__()
        self._fail_create = fail_create
        self._fail_get_messages = fail_get_messages
        self._fail_add_message = fail_add_message

    async def create_conversation(self, tenant_id: str, user_id: str, **kwargs):
        """Create conversation or fail if configured."""
        if self._fail_create:
            raise RuntimeError("Simulated create_conversation failure")
        return await super().create_conversation(tenant_id, user_id, **kwargs)

    async def get_recent_messages(self, conversation_id: UUID, tenant_id: str, **kwargs):
        """Get messages or fail if configured."""
        if self._fail_get_messages:
            raise RuntimeError("Simulated get_recent_messages failure")
        return await super().get_recent_messages(conversation_id, tenant_id, **kwargs)

    async def add_message(
        self, conversation_id: UUID, tenant_id: str, role: MessageRole, content: str
    ):
        """Add message or fail if configured."""
        if self._fail_add_message:
            raise RuntimeError("Simulated add_message failure")
        return await super().add_message(conversation_id, tenant_id, role, content)


class TestChatServiceConversationStorage:
    """Tests for ChatService conversation storage integration."""

    @pytest.mark.asyncio
    async def test_process_chat_without_repository_works_as_before(self) -> None:
        """ChatService without repository should work as before (backward compat)."""
        chunks = ["Hello, ", "world!"]
        mock_generator = MockResponseGenerator(chunks)
        service = ChatService(response_generator=mock_generator)
        request = ChatRequest(message="Hi")

        events = []
        async for event in service.process_chat(request):
            events.append(event)

        # Should work normally without repository
        assert len(events) == 3  # 2 chunks + 1 done
        assert events[0].startswith("event: chunk")
        assert events[-1].startswith("event: done")

    @pytest.mark.asyncio
    async def test_process_chat_creates_conversation_when_no_id_provided(self) -> None:
        """ChatService should create new conversation when conversation_id not provided."""
        chunks = ["Response"]
        mock_generator = MockResponseGenerator(chunks)
        repository = InMemoryConversationRepository()
        service = ChatService(
            response_generator=mock_generator,
            conversation_repository=repository,
            tenant_id="test-tenant",
            user_id="test-user",
        )
        request = ChatRequest(message="Hello")

        events = []
        async for event in service.process_chat(request):
            events.append(event)

        # Should successfully process
        assert len(events) == 2  # 1 chunk + 1 done

        # Verify conversation was created (check repository)
        conversations = await repository.list_conversations(tenant_id="test-tenant")
        assert len(conversations) == 1
        assert conversations[0].user_id == "test-user"

    @pytest.mark.asyncio
    async def test_process_chat_validates_conversation_id_exists(self) -> None:
        """ChatService should raise error when conversation_id is invalid."""
        chunks = ["Response"]
        mock_generator = MockResponseGenerator(chunks)
        repository = InMemoryConversationRepository()
        service = ChatService(
            response_generator=mock_generator,
            conversation_repository=repository,
            tenant_id="test-tenant",
        )

        # Use non-existent conversation_id
        invalid_id = uuid4()
        request = ChatRequest(message="Hello", conversation_id=invalid_id)

        events = []
        async for event in service.process_chat(request):
            events.append(event)

        # Should yield error event
        assert len(events) == 1
        assert events[0].startswith("event: error")
        assert "not found" in events[0]

    @pytest.mark.asyncio
    async def test_process_chat_uses_existing_conversation_when_id_provided(self) -> None:
        """ChatService should use existing conversation when valid conversation_id provided."""
        chunks = ["Response"]
        mock_generator = MockResponseGenerator(chunks)
        repository = InMemoryConversationRepository()
        service = ChatService(
            response_generator=mock_generator,
            conversation_repository=repository,
            tenant_id="test-tenant",
        )

        # Create conversation first
        conversation = await repository.create_conversation(
            tenant_id="test-tenant", user_id="test-user"
        )

        # Use existing conversation_id
        request = ChatRequest(message="Hello", conversation_id=conversation.id)

        events = []
        async for event in service.process_chat(request):
            events.append(event)

        # Should successfully process
        assert len(events) == 2  # 1 chunk + 1 done
        assert str(conversation.id) in events[-1]

    @pytest.mark.asyncio
    async def test_process_chat_stores_user_and_assistant_messages(self) -> None:
        """ChatService should store both user and assistant messages."""
        chunks = ["Hello, ", "how are you?"]
        mock_generator = MockResponseGenerator(chunks)
        repository = InMemoryConversationRepository()
        service = ChatService(
            response_generator=mock_generator,
            conversation_repository=repository,
            tenant_id="test-tenant",
        )

        request = ChatRequest(message="Hi there")

        events = []
        async for event in service.process_chat(request):
            events.append(event)

        # Get conversation that was created
        conversations = await repository.list_conversations(tenant_id="test-tenant")
        assert len(conversations) == 1

        # Get messages
        messages = await repository.get_messages(
            conversations[0].id, tenant_id="test-tenant"
        )

        # Should have 2 messages: user + assistant
        assert len(messages) == 2
        assert messages[0].role == MessageRole.USER
        assert messages[0].content == "Hi there"
        assert messages[1].role == MessageRole.ASSISTANT
        assert messages[1].content == "Hello, how are you?"

    @pytest.mark.asyncio
    async def test_process_chat_passes_conversation_history_to_generator(self) -> None:
        """ChatService should pass conversation history to response generator."""
        chunks = ["Response"]
        mock_generator = MockResponseGenerator(chunks)
        repository = InMemoryConversationRepository()
        service = ChatService(
            response_generator=mock_generator,
            conversation_repository=repository,
            tenant_id="test-tenant",
        )

        # Create conversation with existing messages
        conversation = await repository.create_conversation(
            tenant_id="test-tenant", user_id="test-user"
        )
        await repository.add_message(
            conversation.id, "test-tenant", MessageRole.USER, "Previous question"
        )
        await repository.add_message(
            conversation.id, "test-tenant", MessageRole.ASSISTANT, "Previous answer"
        )

        # Send new message
        request = ChatRequest(message="New question", conversation_id=conversation.id)

        events = []
        async for event in service.process_chat(request):
            events.append(event)

        # Verify history was passed to generator
        assert len(mock_generator._last_conversation_history) == 2
        assert mock_generator._last_conversation_history[0].content == "Previous question"
        assert mock_generator._last_conversation_history[1].content == "Previous answer"

    @pytest.mark.asyncio
    async def test_process_chat_handles_storage_failure_gracefully(self) -> None:
        """ChatService should continue processing even when storage fails."""
        chunks = ["Response chunk"]
        mock_generator = MockResponseGenerator(chunks)
        repository = FailingRepository(fail_add_message=True)
        service = ChatService(
            response_generator=mock_generator,
            conversation_repository=repository,
            tenant_id="test-tenant",
        )

        request = ChatRequest(message="Test message")

        events = []
        async for event in service.process_chat(request):
            events.append(event)

        # Should still yield response despite storage failure
        assert len(events) == 2  # 1 chunk + 1 done
        assert events[0].startswith("event: chunk")
        assert "Response chunk" in events[0]
        assert events[1].startswith("event: done")

    @pytest.mark.asyncio
    async def test_process_chat_handles_create_conversation_failure(self) -> None:
        """ChatService should fallback to UUID generation when create fails."""
        chunks = ["Response"]
        mock_generator = MockResponseGenerator(chunks)
        repository = FailingRepository(fail_create=True)
        service = ChatService(
            response_generator=mock_generator,
            conversation_repository=repository,
            tenant_id="test-tenant",
        )

        request = ChatRequest(message="Test")

        events = []
        async for event in service.process_chat(request):
            events.append(event)

        # Should still complete successfully with fallback UUID
        assert len(events) == 2  # 1 chunk + 1 done
        assert events[-1].startswith("event: done")
        assert "conversation_id" in events[-1]

    @pytest.mark.asyncio
    async def test_process_chat_handles_get_messages_failure_gracefully(self) -> None:
        """ChatService should continue with empty history when retrieval fails."""
        chunks = ["Response"]
        mock_generator = MockResponseGenerator(chunks)
        repository = FailingRepository(fail_get_messages=True)
        service = ChatService(
            response_generator=mock_generator,
            conversation_repository=repository,
            tenant_id="test-tenant",
        )

        # Create conversation first
        conversation = await repository.create_conversation(
            tenant_id="test-tenant", user_id="test-user"
        )

        request = ChatRequest(message="Test", conversation_id=conversation.id)

        events = []
        async for event in service.process_chat(request):
            events.append(event)

        # Should still complete successfully with empty history
        assert len(events) == 2  # 1 chunk + 1 done
        assert events[-1].startswith("event: done")

        # Verify generator received empty history (fallback)
        assert len(mock_generator._last_conversation_history) == 0

    @pytest.mark.asyncio
    async def test_process_chat_enforces_tenant_isolation(self) -> None:
        """ChatService should enforce tenant isolation on conversation access."""
        chunks = ["Response"]
        mock_generator = MockResponseGenerator(chunks)
        repository = InMemoryConversationRepository()

        # Create conversation for tenant-A
        conversation = await repository.create_conversation(
            tenant_id="tenant-a", user_id="user-1"
        )

        # Try to access with tenant-B
        service = ChatService(
            response_generator=mock_generator,
            conversation_repository=repository,
            tenant_id="tenant-b",
        )

        request = ChatRequest(message="Test", conversation_id=conversation.id)

        events = []
        async for event in service.process_chat(request):
            events.append(event)

        # Should yield error event due to tenant mismatch
        assert len(events) == 1
        assert events[0].startswith("event: error")
        assert "not found" in events[0]

    @pytest.mark.asyncio
    async def test_process_chat_limits_conversation_history_to_20_messages(self) -> None:
        """ChatService should retrieve only last 20 messages for context."""
        chunks = ["Response"]
        mock_generator = MockResponseGenerator(chunks)
        repository = InMemoryConversationRepository()
        service = ChatService(
            response_generator=mock_generator,
            conversation_repository=repository,
            tenant_id="test-tenant",
        )

        # Create conversation with 25 messages
        conversation = await repository.create_conversation(
            tenant_id="test-tenant", user_id="test-user"
        )

        for i in range(25):
            role = MessageRole.USER if i % 2 == 0 else MessageRole.ASSISTANT
            await repository.add_message(
                conversation.id, "test-tenant", role, f"Message {i}"
            )

        # Send new message
        request = ChatRequest(message="New message", conversation_id=conversation.id)

        events = []
        async for event in service.process_chat(request):
            events.append(event)

        # Verify only last 20 messages were passed
        assert len(mock_generator._last_conversation_history) == 20
        # Should be messages 5-24 (last 20 of 25)
        assert mock_generator._last_conversation_history[0].content == "Message 5"
        assert mock_generator._last_conversation_history[-1].content == "Message 24"
