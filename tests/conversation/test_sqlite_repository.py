"""Tests for SQLite conversation repository implementation.

Tests SQLiteConversationRepository with in-memory SQLite database,
focusing on tenant isolation, data integrity, and error handling.
"""

from uuid import uuid4

import pytest

from omniforge.conversation.models import MessageRole
from omniforge.conversation.sqlite_repository import SQLiteConversationRepository
from omniforge.storage.database import Database, DatabaseConfig


@pytest.fixture
async def db():
    """Create in-memory SQLite database for testing."""
    config = DatabaseConfig(url="sqlite+aiosqlite:///:memory:")
    database = Database(config)
    await database.create_tables()
    yield database
    await database.close()


@pytest.fixture
async def repository(db):
    """Create SQLite repository instance."""
    return SQLiteConversationRepository(db)


class TestSQLiteConversationRepository:
    """Test suite for SQLiteConversationRepository."""

    async def test_create_conversation_success(self, repository):
        """Should create a new conversation with valid inputs."""
        conversation = await repository.create_conversation(
            tenant_id="tenant-1",
            user_id="user-1",
            title="Test Conversation",
        )

        assert conversation.id is not None
        assert conversation.tenant_id == "tenant-1"
        assert conversation.user_id == "user-1"
        assert conversation.title == "Test Conversation"
        assert conversation.created_at is not None
        assert conversation.updated_at is not None
        assert conversation.metadata is None

    async def test_create_conversation_without_title(self, repository):
        """Should create conversation without title."""
        conversation = await repository.create_conversation(
            tenant_id="tenant-1",
            user_id="user-1",
        )

        assert conversation.id is not None
        assert conversation.title is None

    async def test_create_conversation_empty_tenant_id(self, repository):
        """Should raise ValueError for empty tenant_id."""
        with pytest.raises(ValueError, match="tenant_id cannot be empty"):
            await repository.create_conversation(
                tenant_id="",
                user_id="user-1",
            )

    async def test_create_conversation_empty_user_id(self, repository):
        """Should raise ValueError for empty user_id."""
        with pytest.raises(ValueError, match="user_id cannot be empty"):
            await repository.create_conversation(
                tenant_id="tenant-1",
                user_id="",
            )

    async def test_get_conversation_success(self, repository):
        """Should retrieve conversation by ID with correct tenant."""
        created = await repository.create_conversation(
            tenant_id="tenant-1",
            user_id="user-1",
            title="Test",
        )

        retrieved = await repository.get_conversation(created.id, "tenant-1")

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.tenant_id == "tenant-1"
        assert retrieved.user_id == "user-1"
        assert retrieved.title == "Test"

    async def test_get_conversation_wrong_tenant(self, repository):
        """Should return None when requesting with wrong tenant_id."""
        created = await repository.create_conversation(
            tenant_id="tenant-1",
            user_id="user-1",
        )

        # Try to access with different tenant
        retrieved = await repository.get_conversation(created.id, "tenant-2")

        assert retrieved is None

    async def test_get_conversation_not_found(self, repository):
        """Should return None for non-existent conversation."""
        retrieved = await repository.get_conversation(uuid4(), "tenant-1")

        assert retrieved is None

    async def test_get_conversation_empty_tenant_id(self, repository):
        """Should raise ValueError for empty tenant_id."""
        with pytest.raises(ValueError, match="tenant_id cannot be empty"):
            await repository.get_conversation(uuid4(), "")

    async def test_list_conversations_by_tenant(self, repository):
        """Should list all conversations for a tenant."""
        # Create conversations for tenant-1
        conv1 = await repository.create_conversation("tenant-1", "user-1", "Conv 1")
        conv2 = await repository.create_conversation("tenant-1", "user-2", "Conv 2")

        # Create conversation for tenant-2
        await repository.create_conversation("tenant-2", "user-3", "Conv 3")

        # List for tenant-1
        conversations = await repository.list_conversations("tenant-1")

        assert len(conversations) == 2
        assert all(c.tenant_id == "tenant-1" for c in conversations)
        # Should be ordered by updated_at DESC (most recent first)
        assert conversations[0].id == conv2.id
        assert conversations[1].id == conv1.id

    async def test_list_conversations_by_tenant_and_user(self, repository):
        """Should filter conversations by both tenant and user."""
        # Create conversations
        await repository.create_conversation("tenant-1", "user-1", "Conv 1")
        conv2 = await repository.create_conversation("tenant-1", "user-2", "Conv 2")
        await repository.create_conversation("tenant-2", "user-2", "Conv 3")

        # List for tenant-1 and user-2
        conversations = await repository.list_conversations(
            tenant_id="tenant-1",
            user_id="user-2",
        )

        assert len(conversations) == 1
        assert conversations[0].id == conv2.id

    async def test_list_conversations_pagination(self, repository):
        """Should support pagination with limit and offset."""
        # Create 5 conversations
        for i in range(5):
            await repository.create_conversation("tenant-1", "user-1", f"Conv {i}")

        # Get first 2
        page1 = await repository.list_conversations("tenant-1", limit=2, offset=0)
        assert len(page1) == 2

        # Get next 2
        page2 = await repository.list_conversations("tenant-1", limit=2, offset=2)
        assert len(page2) == 2

        # Ensure no overlap
        page1_ids = {c.id for c in page1}
        page2_ids = {c.id for c in page2}
        assert len(page1_ids & page2_ids) == 0

    async def test_list_conversations_empty_tenant_id(self, repository):
        """Should raise ValueError for empty tenant_id."""
        with pytest.raises(ValueError, match="tenant_id cannot be empty"):
            await repository.list_conversations("")

    async def test_update_conversation_title(self, repository):
        """Should update conversation title."""
        conversation = await repository.create_conversation(
            tenant_id="tenant-1",
            user_id="user-1",
            title="Original Title",
        )

        updated = await repository.update_conversation(
            conversation.id,
            "tenant-1",
            title="Updated Title",
        )

        assert updated is not None
        assert updated.title == "Updated Title"
        assert updated.updated_at > conversation.updated_at

    async def test_update_conversation_wrong_tenant(self, repository):
        """Should return None when updating with wrong tenant_id."""
        conversation = await repository.create_conversation(
            tenant_id="tenant-1",
            user_id="user-1",
        )

        updated = await repository.update_conversation(
            conversation.id,
            "tenant-2",
            title="New Title",
        )

        assert updated is None

    async def test_update_conversation_not_found(self, repository):
        """Should return None for non-existent conversation."""
        updated = await repository.update_conversation(
            uuid4(),
            "tenant-1",
            title="New Title",
        )

        assert updated is None

    async def test_update_conversation_empty_tenant_id(self, repository):
        """Should raise ValueError for empty tenant_id."""
        with pytest.raises(ValueError, match="tenant_id cannot be empty"):
            await repository.update_conversation(uuid4(), "", title="Title")

    async def test_add_message_success(self, repository):
        """Should add a message to a conversation."""
        conversation = await repository.create_conversation(
            tenant_id="tenant-1",
            user_id="user-1",
        )

        message = await repository.add_message(
            conversation.id,
            "tenant-1",
            MessageRole.USER,
            "Hello, world!",
        )

        assert message.id is not None
        assert message.conversation_id == conversation.id
        assert message.role == MessageRole.USER
        assert message.content == "Hello, world!"
        assert message.created_at is not None

    async def test_add_message_updates_conversation_updated_at(self, repository):
        """Should update conversation.updated_at when adding message."""
        conversation = await repository.create_conversation(
            tenant_id="tenant-1",
            user_id="user-1",
        )
        original_updated_at = conversation.updated_at

        await repository.add_message(
            conversation.id,
            "tenant-1",
            MessageRole.USER,
            "Test message",
        )

        updated_conversation = await repository.get_conversation(
            conversation.id,
            "tenant-1",
        )

        assert updated_conversation.updated_at > original_updated_at

    async def test_add_message_wrong_tenant(self, repository):
        """Should raise ValueError when adding message with wrong tenant."""
        conversation = await repository.create_conversation(
            tenant_id="tenant-1",
            user_id="user-1",
        )

        with pytest.raises(ValueError, match="not found or does not belong to tenant"):
            await repository.add_message(
                conversation.id,
                "tenant-2",
                MessageRole.USER,
                "Test",
            )

    async def test_add_message_conversation_not_found(self, repository):
        """Should raise ValueError for non-existent conversation."""
        with pytest.raises(ValueError, match="not found or does not belong to tenant"):
            await repository.add_message(
                uuid4(),
                "tenant-1",
                MessageRole.USER,
                "Test",
            )

    async def test_add_message_empty_tenant_id(self, repository):
        """Should raise ValueError for empty tenant_id."""
        with pytest.raises(ValueError, match="tenant_id cannot be empty"):
            await repository.add_message(uuid4(), "", MessageRole.USER, "Test")

    async def test_add_message_empty_content(self, repository):
        """Should raise ValueError for empty content."""
        conversation = await repository.create_conversation("tenant-1", "user-1")

        with pytest.raises(ValueError, match="content cannot be empty"):
            await repository.add_message(
                conversation.id,
                "tenant-1",
                MessageRole.USER,
                "",
            )

    async def test_get_messages_chronological_order(self, repository):
        """Should retrieve messages in chronological order."""
        conversation = await repository.create_conversation("tenant-1", "user-1")

        # Add messages
        msg1 = await repository.add_message(conversation.id, "tenant-1", MessageRole.USER, "First")
        msg2 = await repository.add_message(
            conversation.id, "tenant-1", MessageRole.ASSISTANT, "Second"
        )
        msg3 = await repository.add_message(conversation.id, "tenant-1", MessageRole.USER, "Third")

        messages = await repository.get_messages(conversation.id, "tenant-1")

        assert len(messages) == 3
        assert messages[0].id == msg1.id
        assert messages[1].id == msg2.id
        assert messages[2].id == msg3.id

    async def test_get_messages_with_pagination(self, repository):
        """Should support pagination for messages."""
        conversation = await repository.create_conversation("tenant-1", "user-1")

        # Add 5 messages
        for i in range(5):
            await repository.add_message(
                conversation.id, "tenant-1", MessageRole.USER, f"Message {i}"
            )

        # Get first 2
        page1 = await repository.get_messages(conversation.id, "tenant-1", limit=2)
        assert len(page1) == 2

        # Get next 2
        page2 = await repository.get_messages(conversation.id, "tenant-1", limit=2, offset=2)
        assert len(page2) == 2

    async def test_get_messages_wrong_tenant(self, repository):
        """Should raise ValueError when getting messages with wrong tenant."""
        conversation = await repository.create_conversation("tenant-1", "user-1")
        await repository.add_message(conversation.id, "tenant-1", MessageRole.USER, "Test")

        with pytest.raises(ValueError, match="not found or does not belong to tenant"):
            await repository.get_messages(conversation.id, "tenant-2")

    async def test_get_messages_conversation_not_found(self, repository):
        """Should raise ValueError for non-existent conversation."""
        with pytest.raises(ValueError, match="not found or does not belong to tenant"):
            await repository.get_messages(uuid4(), "tenant-1")

    async def test_get_messages_empty_tenant_id(self, repository):
        """Should raise ValueError for empty tenant_id."""
        with pytest.raises(ValueError, match="tenant_id cannot be empty"):
            await repository.get_messages(uuid4(), "")

    async def test_get_recent_messages_chronological_order(self, repository):
        """Should retrieve recent messages in chronological order."""
        conversation = await repository.create_conversation("tenant-1", "user-1")

        # Add 5 messages
        messages = []
        for i in range(5):
            msg = await repository.add_message(
                conversation.id, "tenant-1", MessageRole.USER, f"Message {i}"
            )
            messages.append(msg)

        # Get 3 most recent
        recent = await repository.get_recent_messages(conversation.id, "tenant-1", count=3)

        assert len(recent) == 3
        # Should be in chronological order (not reversed)
        assert recent[0].id == messages[2].id
        assert recent[1].id == messages[3].id
        assert recent[2].id == messages[4].id

    async def test_get_recent_messages_fewer_than_count(self, repository):
        """Should return all messages if fewer than count requested."""
        conversation = await repository.create_conversation("tenant-1", "user-1")

        # Add 2 messages
        await repository.add_message(conversation.id, "tenant-1", MessageRole.USER, "First")
        await repository.add_message(conversation.id, "tenant-1", MessageRole.USER, "Second")

        # Request 10 recent (but only 2 exist)
        recent = await repository.get_recent_messages(conversation.id, "tenant-1", count=10)

        assert len(recent) == 2

    async def test_get_recent_messages_wrong_tenant(self, repository):
        """Should raise ValueError when getting recent messages with wrong tenant."""
        conversation = await repository.create_conversation("tenant-1", "user-1")

        with pytest.raises(ValueError, match="not found or does not belong to tenant"):
            await repository.get_recent_messages(conversation.id, "tenant-2")

    async def test_get_recent_messages_empty_tenant_id(self, repository):
        """Should raise ValueError for empty tenant_id."""
        with pytest.raises(ValueError, match="tenant_id cannot be empty"):
            await repository.get_recent_messages(uuid4(), "")

    async def test_tenant_isolation_complete_flow(self, repository):
        """Should maintain tenant isolation throughout complete workflow."""
        # Tenant 1 creates conversation and adds messages
        conv1 = await repository.create_conversation("tenant-1", "user-1", "Conv 1")
        await repository.add_message(conv1.id, "tenant-1", MessageRole.USER, "T1 Message")

        # Tenant 2 creates conversation
        conv2 = await repository.create_conversation("tenant-2", "user-2", "Conv 2")
        await repository.add_message(conv2.id, "tenant-2", MessageRole.USER, "T2 Message")

        # Tenant 1 can only see their own conversation
        tenant1_convs = await repository.list_conversations("tenant-1")
        assert len(tenant1_convs) == 1
        assert tenant1_convs[0].id == conv1.id

        # Tenant 2 can only see their own conversation
        tenant2_convs = await repository.list_conversations("tenant-2")
        assert len(tenant2_convs) == 1
        assert tenant2_convs[0].id == conv2.id

        # Tenant 1 cannot access tenant 2's conversation
        assert await repository.get_conversation(conv2.id, "tenant-1") is None

        # Tenant 2 cannot access tenant 1's messages
        with pytest.raises(ValueError, match="not found or does not belong to tenant"):
            await repository.get_messages(conv1.id, "tenant-2")
