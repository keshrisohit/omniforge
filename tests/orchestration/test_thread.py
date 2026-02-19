"""Tests for ThreadManager and ThreadContext."""

from uuid import uuid4

import pytest

from omniforge.conversation.models import ConversationType, MessageRole
from omniforge.conversation.sqlite_repository import SQLiteConversationRepository
from omniforge.orchestration.thread import ThreadContext, ThreadManager
from omniforge.storage.database import Database, DatabaseConfig


@pytest.fixture
async def db() -> Database:
    """Create in-memory database for testing."""
    config = DatabaseConfig(url="sqlite+aiosqlite:///:memory:")
    database = Database(config)
    await database.create_tables()
    return database


@pytest.fixture
async def conversation_repo(db: Database) -> SQLiteConversationRepository:
    """Create conversation repository."""
    return SQLiteConversationRepository(db)


@pytest.fixture
async def thread_manager(conversation_repo: SQLiteConversationRepository) -> ThreadManager:
    """Create ThreadManager instance."""
    return ThreadManager(conversation_repo)


@pytest.fixture
async def sample_conversation(conversation_repo: SQLiteConversationRepository):
    """Create a sample conversation for testing."""
    conversation = await conversation_repo.create_conversation(
        tenant_id="tenant-1",
        user_id="user-1",
        title="Test Thread",
        conversation_type=ConversationType.CHAT,
        state_metadata={
            "current_active_agent": "agent-a",
            "is_handoff_active": False,
        },
    )

    # Add some messages
    await conversation_repo.add_message(
        conversation_id=conversation.id,
        tenant_id="tenant-1",
        role=MessageRole.USER,
        content="Hello",
    )
    await conversation_repo.add_message(
        conversation_id=conversation.id,
        tenant_id="tenant-1",
        role=MessageRole.ASSISTANT,
        content="Hi there!",
    )
    await conversation_repo.add_message(
        conversation_id=conversation.id,
        tenant_id="tenant-1",
        role=MessageRole.SYSTEM,
        content="System message",
    )

    return conversation


class TestThreadContext:
    """Tests for ThreadContext model."""

    def test_thread_context_creation(self) -> None:
        """ThreadContext should initialize with required fields."""
        thread_id = uuid4()
        from datetime import datetime

        context = ThreadContext(
            thread_id=thread_id,
            tenant_id="tenant-1",
            user_id="user-1",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            current_active_agent="agent-a",
            total_messages=5,
        )

        assert context.thread_id == thread_id
        assert context.tenant_id == "tenant-1"
        assert context.user_id == "user-1"
        assert context.current_active_agent == "agent-a"
        assert context.is_handoff_active is False
        assert context.handoff_target_agent is None
        assert context.total_messages == 5

    def test_thread_context_with_handoff(self) -> None:
        """ThreadContext should support handoff state."""
        thread_id = uuid4()
        from datetime import datetime

        context = ThreadContext(
            thread_id=thread_id,
            tenant_id="tenant-1",
            user_id="user-1",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            current_active_agent="agent-a",
            is_handoff_active=True,
            handoff_target_agent="agent-b",
            total_messages=5,
        )

        assert context.is_handoff_active is True
        assert context.handoff_target_agent == "agent-b"


class TestValidateThread:
    """Tests for ThreadManager.validate_thread()."""

    async def test_validate_thread_valid(
        self,
        thread_manager: ThreadManager,
        sample_conversation,
    ) -> None:
        """validate_thread should return True for valid thread+tenant."""
        result = await thread_manager.validate_thread(
            thread_id=str(sample_conversation.id),
            tenant_id="tenant-1",
        )

        assert result is True

    async def test_validate_thread_valid_with_user_id(
        self,
        thread_manager: ThreadManager,
        sample_conversation,
    ) -> None:
        """validate_thread should return True when user_id matches."""
        result = await thread_manager.validate_thread(
            thread_id=str(sample_conversation.id),
            tenant_id="tenant-1",
            user_id="user-1",
        )

        assert result is True

    async def test_validate_thread_wrong_tenant(
        self,
        thread_manager: ThreadManager,
        sample_conversation,
    ) -> None:
        """validate_thread should return False for wrong tenant."""
        result = await thread_manager.validate_thread(
            thread_id=str(sample_conversation.id),
            tenant_id="tenant-2",
        )

        assert result is False

    async def test_validate_thread_wrong_user(
        self,
        thread_manager: ThreadManager,
        sample_conversation,
    ) -> None:
        """validate_thread should return False when user_id doesn't match."""
        result = await thread_manager.validate_thread(
            thread_id=str(sample_conversation.id),
            tenant_id="tenant-1",
            user_id="user-2",
        )

        assert result is False

    async def test_validate_thread_nonexistent(
        self,
        thread_manager: ThreadManager,
    ) -> None:
        """validate_thread should return False for nonexistent thread."""
        result = await thread_manager.validate_thread(
            thread_id=str(uuid4()),
            tenant_id="tenant-1",
        )

        assert result is False

    async def test_validate_thread_invalid_uuid(
        self,
        thread_manager: ThreadManager,
    ) -> None:
        """validate_thread should return False for invalid UUID."""
        result = await thread_manager.validate_thread(
            thread_id="not-a-uuid",
            tenant_id="tenant-1",
        )

        assert result is False

    async def test_validate_thread_never_raises(
        self,
        thread_manager: ThreadManager,
    ) -> None:
        """validate_thread should never raise exceptions."""
        # Test various invalid inputs
        result1 = await thread_manager.validate_thread(
            thread_id="",
            tenant_id="tenant-1",
        )
        result2 = await thread_manager.validate_thread(
            thread_id="invalid",
            tenant_id="",
        )

        assert result1 is False
        assert result2 is False


class TestGetRecentMessages:
    """Tests for ThreadManager.get_recent_messages()."""

    async def test_get_recent_messages_default_count(
        self,
        thread_manager: ThreadManager,
        sample_conversation,
    ) -> None:
        """get_recent_messages should return recent messages excluding system."""
        messages = await thread_manager.get_recent_messages(
            thread_id=str(sample_conversation.id),
            tenant_id="tenant-1",
        )

        # Should have 2 messages (user + assistant, system filtered)
        assert len(messages) == 2
        assert messages[0].role == MessageRole.USER
        assert messages[0].content == "Hello"
        assert messages[1].role == MessageRole.ASSISTANT
        assert messages[1].content == "Hi there!"

    async def test_get_recent_messages_with_system(
        self,
        thread_manager: ThreadManager,
        sample_conversation,
    ) -> None:
        """get_recent_messages should include system messages when requested."""
        messages = await thread_manager.get_recent_messages(
            thread_id=str(sample_conversation.id),
            tenant_id="tenant-1",
            include_system=True,
        )

        # Should have all 3 messages
        assert len(messages) == 3
        assert messages[2].role == MessageRole.SYSTEM
        assert messages[2].content == "System message"

    async def test_get_recent_messages_custom_count(
        self,
        thread_manager: ThreadManager,
        conversation_repo: SQLiteConversationRepository,
    ) -> None:
        """get_recent_messages should respect count limit."""
        # Create conversation with 5 messages
        conversation = await conversation_repo.create_conversation(
            tenant_id="tenant-1",
            user_id="user-1",
        )

        for i in range(5):
            await conversation_repo.add_message(
                conversation_id=conversation.id,
                tenant_id="tenant-1",
                role=MessageRole.USER,
                content=f"Message {i}",
            )

        # Get only 3 most recent
        messages = await thread_manager.get_recent_messages(
            thread_id=str(conversation.id),
            tenant_id="tenant-1",
            count=3,
        )

        assert len(messages) == 3
        assert messages[0].content == "Message 2"
        assert messages[1].content == "Message 3"
        assert messages[2].content == "Message 4"

    async def test_get_recent_messages_invalid_thread_id(
        self,
        thread_manager: ThreadManager,
    ) -> None:
        """get_recent_messages should raise ValueError for invalid UUID."""
        with pytest.raises(ValueError, match="Invalid thread_id format"):
            await thread_manager.get_recent_messages(
                thread_id="not-a-uuid",
                tenant_id="tenant-1",
            )

    async def test_get_recent_messages_nonexistent_thread(
        self,
        thread_manager: ThreadManager,
    ) -> None:
        """get_recent_messages should raise ValueError for nonexistent thread."""
        with pytest.raises(ValueError, match="not found"):
            await thread_manager.get_recent_messages(
                thread_id=str(uuid4()),
                tenant_id="tenant-1",
            )

    async def test_get_recent_messages_wrong_tenant(
        self,
        thread_manager: ThreadManager,
        sample_conversation,
    ) -> None:
        """get_recent_messages should raise ValueError for wrong tenant."""
        with pytest.raises(ValueError, match="not found"):
            await thread_manager.get_recent_messages(
                thread_id=str(sample_conversation.id),
                tenant_id="tenant-2",
            )


class TestGetThreadContext:
    """Tests for ThreadManager.get_thread_context()."""

    async def test_get_thread_context_basic(
        self,
        thread_manager: ThreadManager,
        sample_conversation,
    ) -> None:
        """get_thread_context should return correct metadata."""
        context = await thread_manager.get_thread_context(
            thread_id=str(sample_conversation.id),
            tenant_id="tenant-1",
        )

        assert isinstance(context, ThreadContext)
        assert context.thread_id == sample_conversation.id
        assert context.tenant_id == "tenant-1"
        assert context.user_id == "user-1"
        assert context.current_active_agent == "agent-a"
        assert context.is_handoff_active is False
        assert context.handoff_target_agent is None
        assert context.total_messages == 3

    async def test_get_thread_context_with_handoff_state(
        self,
        thread_manager: ThreadManager,
        conversation_repo: SQLiteConversationRepository,
    ) -> None:
        """get_thread_context should read handoff state from state_metadata."""
        conversation = await conversation_repo.create_conversation(
            tenant_id="tenant-1",
            user_id="user-1",
            state_metadata={
                "current_active_agent": "agent-a",
                "is_handoff_active": True,
                "handoff_target_agent": "agent-b",
            },
        )

        context = await thread_manager.get_thread_context(
            thread_id=str(conversation.id),
            tenant_id="tenant-1",
        )

        assert context.current_active_agent == "agent-a"
        assert context.is_handoff_active is True
        assert context.handoff_target_agent == "agent-b"

    async def test_get_thread_context_default_agent(
        self,
        thread_manager: ThreadManager,
        conversation_repo: SQLiteConversationRepository,
    ) -> None:
        """get_thread_context should default to 'default' agent if not specified."""
        conversation = await conversation_repo.create_conversation(
            tenant_id="tenant-1",
            user_id="user-1",
            state_metadata={},  # No agent specified
        )

        context = await thread_manager.get_thread_context(
            thread_id=str(conversation.id),
            tenant_id="tenant-1",
        )

        assert context.current_active_agent == "default"
        assert context.is_handoff_active is False

    async def test_get_thread_context_no_metadata(
        self,
        thread_manager: ThreadManager,
        conversation_repo: SQLiteConversationRepository,
    ) -> None:
        """get_thread_context should handle missing state_metadata."""
        conversation = await conversation_repo.create_conversation(
            tenant_id="tenant-1",
            user_id="user-1",
            state_metadata=None,
        )

        context = await thread_manager.get_thread_context(
            thread_id=str(conversation.id),
            tenant_id="tenant-1",
        )

        assert context.current_active_agent == "default"
        assert context.is_handoff_active is False
        assert context.handoff_target_agent is None

    async def test_get_thread_context_invalid_thread_id(
        self,
        thread_manager: ThreadManager,
    ) -> None:
        """get_thread_context should raise ValueError for invalid UUID."""
        with pytest.raises(ValueError, match="Invalid thread_id format"):
            await thread_manager.get_thread_context(
                thread_id="not-a-uuid",
                tenant_id="tenant-1",
            )

    async def test_get_thread_context_nonexistent_thread(
        self,
        thread_manager: ThreadManager,
    ) -> None:
        """get_thread_context should raise ValueError for nonexistent thread."""
        with pytest.raises(ValueError, match="not found"):
            await thread_manager.get_thread_context(
                thread_id=str(uuid4()),
                tenant_id="tenant-1",
            )

    async def test_get_thread_context_wrong_tenant(
        self,
        thread_manager: ThreadManager,
        sample_conversation,
    ) -> None:
        """get_thread_context should raise ValueError for wrong tenant."""
        with pytest.raises(ValueError, match="not found"):
            await thread_manager.get_thread_context(
                thread_id=str(sample_conversation.id),
                tenant_id="tenant-2",
            )


class TestSecurityValidation:
    """Security-focused tests for tenant isolation."""

    async def test_cross_tenant_access_blocked(
        self,
        thread_manager: ThreadManager,
        conversation_repo: SQLiteConversationRepository,
    ) -> None:
        """Thread validation should prevent cross-tenant access."""
        # Create conversation for tenant-1
        conv1 = await conversation_repo.create_conversation(
            tenant_id="tenant-1",
            user_id="user-1",
        )

        # Try to access from tenant-2
        result = await thread_manager.validate_thread(
            thread_id=str(conv1.id),
            tenant_id="tenant-2",
        )

        assert result is False

    async def test_cross_user_access_with_validation(
        self,
        thread_manager: ThreadManager,
        conversation_repo: SQLiteConversationRepository,
    ) -> None:
        """Thread validation should prevent cross-user access when user_id specified."""
        # Create conversation for user-1
        conv = await conversation_repo.create_conversation(
            tenant_id="tenant-1",
            user_id="user-1",
        )

        # Try to access as user-2
        result = await thread_manager.validate_thread(
            thread_id=str(conv.id),
            tenant_id="tenant-1",
            user_id="user-2",
        )

        assert result is False

    async def test_messages_respect_tenant_boundary(
        self,
        thread_manager: ThreadManager,
        conversation_repo: SQLiteConversationRepository,
    ) -> None:
        """get_recent_messages should enforce tenant isolation."""
        # Create conversation for tenant-1
        conv = await conversation_repo.create_conversation(
            tenant_id="tenant-1",
            user_id="user-1",
        )
        await conversation_repo.add_message(
            conversation_id=conv.id,
            tenant_id="tenant-1",
            role=MessageRole.USER,
            content="Secret message",
        )

        # Try to access from tenant-2
        with pytest.raises(ValueError):
            await thread_manager.get_recent_messages(
                thread_id=str(conv.id),
                tenant_id="tenant-2",
            )

    async def test_context_respects_tenant_boundary(
        self,
        thread_manager: ThreadManager,
        conversation_repo: SQLiteConversationRepository,
    ) -> None:
        """get_thread_context should enforce tenant isolation."""
        # Create conversation for tenant-1
        conv = await conversation_repo.create_conversation(
            tenant_id="tenant-1",
            user_id="user-1",
            state_metadata={"secret": "data"},
        )

        # Try to access from tenant-2
        with pytest.raises(ValueError):
            await thread_manager.get_thread_context(
                thread_id=str(conv.id),
                tenant_id="tenant-2",
            )
