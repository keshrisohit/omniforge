"""Tests for conversation repository Protocol.

These tests verify that the Protocol interface is properly defined
and can be used for type checking and runtime validation.
"""

from typing import List, Optional
from uuid import UUID

import pytest

from omniforge.conversation.models import Conversation, Message, MessageRole
from omniforge.conversation.repository import ConversationRepository


class MockConversationRepository:
    """Mock implementation of ConversationRepository for testing.

    This verifies that the Protocol can be implemented and used.
    """

    def __init__(self) -> None:
        """Initialize mock repository with in-memory storage."""
        self.conversations: dict[UUID, Conversation] = {}
        self.messages: dict[UUID, list[Message]] = {}

    async def create_conversation(
        self,
        tenant_id: str,
        user_id: str,
        title: Optional[str] = None,
    ) -> Conversation:
        """Create a new conversation."""
        conversation = Conversation(
            tenant_id=tenant_id,
            user_id=user_id,
            title=title,
        )
        self.conversations[conversation.id] = conversation
        self.messages[conversation.id] = []
        return conversation

    async def get_conversation(
        self,
        conversation_id: UUID,
        tenant_id: str,
    ) -> Optional[Conversation]:
        """Get a conversation by ID with tenant validation."""
        conversation = self.conversations.get(conversation_id)
        if conversation and conversation.tenant_id == tenant_id:
            return conversation
        return None

    async def list_conversations(
        self,
        tenant_id: str,
        user_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Conversation]:
        """List conversations with tenant filtering."""
        filtered = [
            conv
            for conv in self.conversations.values()
            if conv.tenant_id == tenant_id and (user_id is None or conv.user_id == user_id)
        ]
        return filtered[offset : offset + limit]

    async def update_conversation(
        self,
        conversation_id: UUID,
        tenant_id: str,
        title: Optional[str] = None,
    ) -> Optional[Conversation]:
        """Update conversation metadata."""
        conversation = await self.get_conversation(conversation_id, tenant_id)
        if conversation and title is not None:
            conversation.title = title
        return conversation

    async def add_message(
        self,
        conversation_id: UUID,
        tenant_id: str,
        role: MessageRole,
        content: str,
    ) -> Message:
        """Add a message to a conversation."""
        conversation = await self.get_conversation(conversation_id, tenant_id)
        if not conversation:
            raise ValueError("Conversation not found or tenant mismatch")

        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
        )
        self.messages[conversation_id].append(message)
        return message

    async def get_messages(
        self,
        conversation_id: UUID,
        tenant_id: str,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[Message]:
        """Get all messages in a conversation with tenant validation."""
        conversation = await self.get_conversation(conversation_id, tenant_id)
        if not conversation:
            raise ValueError("Conversation not found or tenant mismatch")

        messages = self.messages.get(conversation_id, [])
        if limit is None:
            return messages[offset:]
        return messages[offset : offset + limit]

    async def get_recent_messages(
        self,
        conversation_id: UUID,
        tenant_id: str,
        count: int = 10,
    ) -> List[Message]:
        """Get the most recent messages from a conversation."""
        conversation = await self.get_conversation(conversation_id, tenant_id)
        if not conversation:
            raise ValueError("Conversation not found or tenant mismatch")

        messages = self.messages.get(conversation_id, [])
        return messages[-count:] if len(messages) > count else messages


class TestConversationRepositoryProtocol:
    """Tests for ConversationRepository Protocol interface."""

    @pytest.fixture
    def repository(self) -> MockConversationRepository:
        """Create a mock repository instance."""
        return MockConversationRepository()

    @pytest.mark.asyncio
    async def test_repository_implements_protocol(
        self, repository: MockConversationRepository
    ) -> None:
        """Mock repository should implement ConversationRepository Protocol."""
        # Type checking should pass - this validates Protocol implementation
        repo: ConversationRepository = repository
        assert repo is not None

    @pytest.mark.asyncio
    async def test_create_conversation(self, repository: MockConversationRepository) -> None:
        """Repository should create conversations."""
        conversation = await repository.create_conversation(
            tenant_id="tenant-1",
            user_id="user-1",
            title="Test Conversation",
        )

        assert isinstance(conversation, Conversation)
        assert conversation.tenant_id == "tenant-1"
        assert conversation.user_id == "user-1"
        assert conversation.title == "Test Conversation"

    @pytest.mark.asyncio
    async def test_get_conversation_with_valid_tenant(
        self, repository: MockConversationRepository
    ) -> None:
        """Repository should get conversation with correct tenant_id."""
        created = await repository.create_conversation(
            tenant_id="tenant-1",
            user_id="user-1",
        )

        retrieved = await repository.get_conversation(
            conversation_id=created.id,
            tenant_id="tenant-1",
        )

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.tenant_id == "tenant-1"

    @pytest.mark.asyncio
    async def test_get_conversation_with_wrong_tenant_returns_none(
        self, repository: MockConversationRepository
    ) -> None:
        """Repository should return None for wrong tenant_id (security)."""
        created = await repository.create_conversation(
            tenant_id="tenant-1",
            user_id="user-1",
        )

        retrieved = await repository.get_conversation(
            conversation_id=created.id,
            tenant_id="tenant-2",  # Wrong tenant
        )

        assert retrieved is None

    @pytest.mark.asyncio
    async def test_list_conversations_filters_by_tenant(
        self, repository: MockConversationRepository
    ) -> None:
        """Repository should filter conversations by tenant_id."""
        await repository.create_conversation(
            tenant_id="tenant-1",
            user_id="user-1",
        )
        await repository.create_conversation(
            tenant_id="tenant-1",
            user_id="user-2",
        )
        await repository.create_conversation(
            tenant_id="tenant-2",
            user_id="user-3",
        )

        tenant1_convs = await repository.list_conversations(tenant_id="tenant-1")
        tenant2_convs = await repository.list_conversations(tenant_id="tenant-2")

        assert len(tenant1_convs) == 2
        assert len(tenant2_convs) == 1
        assert all(conv.tenant_id == "tenant-1" for conv in tenant1_convs)
        assert all(conv.tenant_id == "tenant-2" for conv in tenant2_convs)

    @pytest.mark.asyncio
    async def test_list_conversations_filters_by_user(
        self, repository: MockConversationRepository
    ) -> None:
        """Repository should filter conversations by user_id when provided."""
        await repository.create_conversation(
            tenant_id="tenant-1",
            user_id="user-1",
        )
        await repository.create_conversation(
            tenant_id="tenant-1",
            user_id="user-2",
        )

        user1_convs = await repository.list_conversations(
            tenant_id="tenant-1",
            user_id="user-1",
        )

        assert len(user1_convs) == 1
        assert user1_convs[0].user_id == "user-1"

    @pytest.mark.asyncio
    async def test_list_conversations_pagination(
        self, repository: MockConversationRepository
    ) -> None:
        """Repository should support pagination."""
        for i in range(5):
            await repository.create_conversation(
                tenant_id="tenant-1",
                user_id=f"user-{i}",
            )

        page1 = await repository.list_conversations(
            tenant_id="tenant-1",
            limit=2,
            offset=0,
        )
        page2 = await repository.list_conversations(
            tenant_id="tenant-1",
            limit=2,
            offset=2,
        )

        assert len(page1) == 2
        assert len(page2) == 2
        assert page1[0].id != page2[0].id

    @pytest.mark.asyncio
    async def test_update_conversation(self, repository: MockConversationRepository) -> None:
        """Repository should update conversation metadata."""
        created = await repository.create_conversation(
            tenant_id="tenant-1",
            user_id="user-1",
            title="Original Title",
        )

        updated = await repository.update_conversation(
            conversation_id=created.id,
            tenant_id="tenant-1",
            title="Updated Title",
        )

        assert updated is not None
        assert updated.title == "Updated Title"

    @pytest.mark.asyncio
    async def test_add_message(self, repository: MockConversationRepository) -> None:
        """Repository should add messages to conversations."""
        conversation = await repository.create_conversation(
            tenant_id="tenant-1",
            user_id="user-1",
        )

        message = await repository.add_message(
            conversation_id=conversation.id,
            tenant_id="tenant-1",
            role=MessageRole.USER,
            content="Hello, world!",
        )

        assert isinstance(message, Message)
        assert message.conversation_id == conversation.id
        assert message.role == MessageRole.USER
        assert message.content == "Hello, world!"

    @pytest.mark.asyncio
    async def test_add_message_with_wrong_tenant_raises_error(
        self, repository: MockConversationRepository
    ) -> None:
        """Repository should raise error when adding message with wrong tenant."""
        conversation = await repository.create_conversation(
            tenant_id="tenant-1",
            user_id="user-1",
        )

        with pytest.raises(ValueError, match="Conversation not found or tenant mismatch"):
            await repository.add_message(
                conversation_id=conversation.id,
                tenant_id="tenant-2",  # Wrong tenant
                role=MessageRole.USER,
                content="Should fail",
            )

    @pytest.mark.asyncio
    async def test_get_messages(self, repository: MockConversationRepository) -> None:
        """Repository should retrieve messages from conversations."""
        conversation = await repository.create_conversation(
            tenant_id="tenant-1",
            user_id="user-1",
        )

        await repository.add_message(conversation.id, "tenant-1", MessageRole.USER, "Message 1")
        await repository.add_message(
            conversation.id, "tenant-1", MessageRole.ASSISTANT, "Message 2"
        )
        await repository.add_message(conversation.id, "tenant-1", MessageRole.USER, "Message 3")

        messages = await repository.get_messages(
            conversation_id=conversation.id,
            tenant_id="tenant-1",
        )

        assert len(messages) == 3
        assert messages[0].content == "Message 1"
        assert messages[1].content == "Message 2"
        assert messages[2].content == "Message 3"

    @pytest.mark.asyncio
    async def test_get_messages_with_limit(self, repository: MockConversationRepository) -> None:
        """Repository should support limiting message retrieval."""
        conversation = await repository.create_conversation(
            tenant_id="tenant-1",
            user_id="user-1",
        )

        for i in range(5):
            await repository.add_message(
                conversation.id, "tenant-1", MessageRole.USER, f"Message {i}"
            )

        messages = await repository.get_messages(
            conversation_id=conversation.id,
            tenant_id="tenant-1",
            limit=2,
        )

        assert len(messages) == 2

    @pytest.mark.asyncio
    async def test_get_messages_with_wrong_tenant_raises_error(
        self, repository: MockConversationRepository
    ) -> None:
        """Repository should raise error when getting messages with wrong tenant."""
        conversation = await repository.create_conversation(
            tenant_id="tenant-1",
            user_id="user-1",
        )

        with pytest.raises(ValueError, match="Conversation not found or tenant mismatch"):
            await repository.get_messages(
                conversation_id=conversation.id,
                tenant_id="tenant-2",  # Wrong tenant
            )

    @pytest.mark.asyncio
    async def test_get_recent_messages(self, repository: MockConversationRepository) -> None:
        """Repository should retrieve recent messages."""
        conversation = await repository.create_conversation(
            tenant_id="tenant-1",
            user_id="user-1",
        )

        for i in range(15):
            await repository.add_message(
                conversation.id, "tenant-1", MessageRole.USER, f"Message {i}"
            )

        recent = await repository.get_recent_messages(
            conversation_id=conversation.id,
            tenant_id="tenant-1",
            count=5,
        )

        assert len(recent) == 5
        assert recent[-1].content == "Message 14"  # Most recent

    @pytest.mark.asyncio
    async def test_get_recent_messages_fewer_than_count(
        self, repository: MockConversationRepository
    ) -> None:
        """Repository should return all messages if fewer than count."""
        conversation = await repository.create_conversation(
            tenant_id="tenant-1",
            user_id="user-1",
        )

        await repository.add_message(conversation.id, "tenant-1", MessageRole.USER, "Message 1")
        await repository.add_message(conversation.id, "tenant-1", MessageRole.USER, "Message 2")

        recent = await repository.get_recent_messages(
            conversation_id=conversation.id,
            tenant_id="tenant-1",
            count=10,
        )

        assert len(recent) == 2

    @pytest.mark.asyncio
    async def test_tenant_isolation_across_all_operations(
        self, repository: MockConversationRepository
    ) -> None:
        """All repository operations should enforce tenant isolation."""
        # Create conversations for different tenants
        conv1 = await repository.create_conversation(
            tenant_id="tenant-1",
            user_id="user-1",
        )
        conv2 = await repository.create_conversation(
            tenant_id="tenant-2",
            user_id="user-2",
        )

        # Add messages
        await repository.add_message(conv1.id, "tenant-1", MessageRole.USER, "Tenant 1 message")
        await repository.add_message(conv2.id, "tenant-2", MessageRole.USER, "Tenant 2 message")

        # Verify tenant 1 cannot access tenant 2 data
        assert await repository.get_conversation(conv2.id, "tenant-1") is None

        # Verify tenant 2 cannot access tenant 1 data
        assert await repository.get_conversation(conv1.id, "tenant-2") is None

        # Verify list operations are isolated
        tenant1_convs = await repository.list_conversations("tenant-1")
        tenant2_convs = await repository.list_conversations("tenant-2")

        assert len(tenant1_convs) == 1
        assert len(tenant2_convs) == 1
        assert tenant1_convs[0].id == conv1.id
        assert tenant2_convs[0].id == conv2.id
