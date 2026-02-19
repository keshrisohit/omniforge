"""Tests for HandoffManager and handoff state persistence.

Tests HandoffManager with in-memory SQLite database, focusing on
handoff lifecycle, state transitions, persistence, and error handling.
"""

from uuid import uuid4

import pytest

from omniforge.agents.models import (
    AgentCapabilities,
    AgentCard,
    AgentIdentity,
    AgentSkill,
    AuthScheme,
    SecurityConfig,
    SkillInputMode,
    SkillOutputMode,
)
from omniforge.conversation.models import ConversationType
from omniforge.conversation.sqlite_repository import SQLiteConversationRepository
from omniforge.orchestration.a2a_models import CompletionStatus, HandoffError
from omniforge.orchestration.client import A2AClient
from omniforge.orchestration.handoff import HandoffManager, HandoffSession, HandoffState
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
async def conversation_repo(db):
    """Create conversation repository instance."""
    return SQLiteConversationRepository(db)


@pytest.fixture
def a2a_client():
    """Create A2A client instance."""
    return A2AClient()


@pytest.fixture
async def handoff_manager(a2a_client, conversation_repo):
    """Create HandoffManager instance."""
    return HandoffManager(a2a_client, conversation_repo)


@pytest.fixture
async def conversation(conversation_repo):
    """Create a test conversation."""
    return await conversation_repo.create_conversation(
        tenant_id="tenant-1",
        user_id="user-1",
        title="Test Conversation",
        conversation_type=ConversationType.CHAT,
    )


@pytest.fixture
def target_agent_card():
    """Create a target agent card for handoffs."""
    return AgentCard(
        protocol_version="1.0",
        identity=AgentIdentity(
            id="specialized-agent",
            name="Specialized Agent",
            description="A specialized agent for testing",
            version="1.0.0",
        ),
        capabilities=AgentCapabilities(streaming=True, multi_turn=True),
        skills=[
            AgentSkill(
                id="specialized-skill",
                name="Specialized Skill",
                description="A specialized skill for testing",
                input_modes=[SkillInputMode.TEXT],
                output_modes=[SkillOutputMode.TEXT],
            )
        ],
        service_endpoint="http://localhost:8001",
        security=SecurityConfig(auth_scheme=AuthScheme.BEARER, require_https=True),
    )


class TestHandoffSession:
    """Test suite for HandoffSession model."""

    def test_create_handoff_session_with_defaults(self):
        """Should create HandoffSession with default values."""
        session = HandoffSession(
            thread_id=str(uuid4()),
            tenant_id="tenant-1",
            user_id="user-1",
            source_agent_id="orchestrator",
            target_agent_id="specialist",
            context_summary="User needs help with specialized task",
            handoff_reason="Requires specialist expertise",
        )

        assert session.handoff_id is not None
        assert session.state == HandoffState.PENDING
        assert session.started_at is not None
        assert session.completed_at is None
        assert session.result_summary is None
        assert session.artifacts_created == []

    def test_handoff_session_serialization(self):
        """Should serialize and deserialize HandoffSession correctly."""
        session = HandoffSession(
            thread_id=str(uuid4()),
            tenant_id="tenant-1",
            user_id="user-1",
            source_agent_id="orchestrator",
            target_agent_id="specialist",
            context_summary="Test context",
            handoff_reason="Testing",
            state=HandoffState.ACTIVE,
        )

        # Serialize to dict
        data = session.model_dump(mode="json")

        # Deserialize back
        restored = HandoffSession(**data)

        assert restored.handoff_id == session.handoff_id
        assert restored.thread_id == session.thread_id
        assert restored.state == session.state
        assert restored.tenant_id == session.tenant_id


class TestHandoffManagerInitiateHandoff:
    """Test suite for HandoffManager.initiate_handoff()."""

    async def test_initiate_handoff_success(self, handoff_manager, conversation, target_agent_card):
        """Should successfully initiate a handoff."""
        result = await handoff_manager.initiate_handoff(
            thread_id=str(conversation.id),
            tenant_id="tenant-1",
            user_id="user-1",
            source_agent_id="orchestrator",
            target_agent_card=target_agent_card,
            context_summary="User needs specialized help",
            handoff_reason="Requires domain expertise",
        )

        assert result.accepted is True
        assert result.thread_id == str(conversation.id)
        assert result.source_agent_id == "orchestrator"
        assert result.target_agent_id == "specialized-agent"

    async def test_initiate_handoff_creates_active_session(
        self, handoff_manager, conversation, target_agent_card
    ):
        """Should create session with ACTIVE state (Phase 1 auto-accept)."""
        await handoff_manager.initiate_handoff(
            thread_id=str(conversation.id),
            tenant_id="tenant-1",
            user_id="user-1",
            source_agent_id="orchestrator",
            target_agent_card=target_agent_card,
            context_summary="Test context",
            handoff_reason="Testing",
        )

        # Verify session is active
        session = await handoff_manager.get_active_handoff(str(conversation.id), "tenant-1")

        assert session is not None
        assert session.state == HandoffState.ACTIVE
        assert session.source_agent_id == "orchestrator"
        assert session.target_agent_id == "specialized-agent"

    async def test_initiate_handoff_persists_to_database(
        self, handoff_manager, conversation_repo, conversation, target_agent_card
    ):
        """Should persist handoff session to state_metadata."""
        await handoff_manager.initiate_handoff(
            thread_id=str(conversation.id),
            tenant_id="tenant-1",
            user_id="user-1",
            source_agent_id="orchestrator",
            target_agent_card=target_agent_card,
            context_summary="Test context",
            handoff_reason="Testing",
        )

        # Load conversation from database
        loaded = await conversation_repo.get_conversation(conversation.id, "tenant-1")

        assert loaded is not None
        assert loaded.state_metadata is not None
        assert "handoff_session" in loaded.state_metadata

        session_data = loaded.state_metadata["handoff_session"]
        assert session_data["state"] == "active"
        assert session_data["source_agent_id"] == "orchestrator"

    async def test_initiate_handoff_raises_error_if_active_exists(
        self, handoff_manager, conversation, target_agent_card
    ):
        """Should raise HandoffError if active handoff already exists."""
        # First handoff succeeds
        await handoff_manager.initiate_handoff(
            thread_id=str(conversation.id),
            tenant_id="tenant-1",
            user_id="user-1",
            source_agent_id="orchestrator",
            target_agent_card=target_agent_card,
            context_summary="Test context",
            handoff_reason="Testing",
        )

        # Second handoff should fail
        with pytest.raises(HandoffError, match="Active handoff already exists"):
            await handoff_manager.initiate_handoff(
                thread_id=str(conversation.id),
                tenant_id="tenant-1",
                user_id="user-1",
                source_agent_id="orchestrator",
                target_agent_card=target_agent_card,
                context_summary="Another context",
                handoff_reason="Another reason",
            )

    async def test_initiate_handoff_validates_empty_thread_id(
        self, handoff_manager, target_agent_card
    ):
        """Should raise ValueError for empty thread_id."""
        with pytest.raises(ValueError, match="thread_id cannot be empty"):
            await handoff_manager.initiate_handoff(
                thread_id="",
                tenant_id="tenant-1",
                user_id="user-1",
                source_agent_id="orchestrator",
                target_agent_card=target_agent_card,
                context_summary="Test",
                handoff_reason="Test",
            )

    async def test_initiate_handoff_validates_empty_tenant_id(
        self, handoff_manager, target_agent_card
    ):
        """Should raise ValueError for empty tenant_id."""
        with pytest.raises(ValueError, match="tenant_id cannot be empty"):
            await handoff_manager.initiate_handoff(
                thread_id=str(uuid4()),
                tenant_id="",
                user_id="user-1",
                source_agent_id="orchestrator",
                target_agent_card=target_agent_card,
                context_summary="Test",
                handoff_reason="Test",
            )


class TestHandoffManagerGetActiveHandoff:
    """Test suite for HandoffManager.get_active_handoff()."""

    async def test_get_active_handoff_from_cache(
        self, handoff_manager, conversation, target_agent_card
    ):
        """Should retrieve active handoff from cache."""
        # Create handoff
        await handoff_manager.initiate_handoff(
            thread_id=str(conversation.id),
            tenant_id="tenant-1",
            user_id="user-1",
            source_agent_id="orchestrator",
            target_agent_card=target_agent_card,
            context_summary="Test context",
            handoff_reason="Testing",
        )

        # Retrieve from cache
        session = await handoff_manager.get_active_handoff(str(conversation.id), "tenant-1")

        assert session is not None
        assert session.state == HandoffState.ACTIVE

    async def test_get_active_handoff_from_database(
        self, conversation_repo, conversation, target_agent_card
    ):
        """Should load active handoff from database if not in cache."""
        # Create manager and initiate handoff
        manager1 = HandoffManager(A2AClient(), conversation_repo)
        await manager1.initiate_handoff(
            thread_id=str(conversation.id),
            tenant_id="tenant-1",
            user_id="user-1",
            source_agent_id="orchestrator",
            target_agent_card=target_agent_card,
            context_summary="Test context",
            handoff_reason="Testing",
        )

        # Create new manager (empty cache) and retrieve
        manager2 = HandoffManager(A2AClient(), conversation_repo)
        session = await manager2.get_active_handoff(str(conversation.id), "tenant-1")

        assert session is not None
        assert session.state == HandoffState.ACTIVE
        assert session.source_agent_id == "orchestrator"

    async def test_get_active_handoff_returns_none_if_not_exists(self, handoff_manager):
        """Should return None if no active handoff exists."""
        session = await handoff_manager.get_active_handoff(str(uuid4()), "tenant-1")

        assert session is None

    async def test_get_active_handoff_returns_none_if_completed(
        self, handoff_manager, conversation, target_agent_card
    ):
        """Should return None for completed handoffs."""
        # Create and complete handoff
        await handoff_manager.initiate_handoff(
            thread_id=str(conversation.id),
            tenant_id="tenant-1",
            user_id="user-1",
            source_agent_id="orchestrator",
            target_agent_card=target_agent_card,
            context_summary="Test context",
            handoff_reason="Testing",
        )

        await handoff_manager.complete_handoff(
            thread_id=str(conversation.id),
            tenant_id="tenant-1",
            completion_status=CompletionStatus.COMPLETED,
        )

        # Should return None
        session = await handoff_manager.get_active_handoff(str(conversation.id), "tenant-1")

        assert session is None

    async def test_get_active_handoff_validates_tenant_id_mismatch(
        self, handoff_manager, conversation, target_agent_card
    ):
        """Should raise ValueError when cached session tenant doesn't match."""
        # Create handoff for tenant-1
        await handoff_manager.initiate_handoff(
            thread_id=str(conversation.id),
            tenant_id="tenant-1",
            user_id="user-1",
            source_agent_id="orchestrator",
            target_agent_card=target_agent_card,
            context_summary="Test context",
            handoff_reason="Testing",
        )

        # Try to access with different tenant
        with pytest.raises(ValueError, match="does not belong to tenant"):
            await handoff_manager.get_active_handoff(str(conversation.id), "tenant-2")


class TestHandoffManagerCompleteHandoff:
    """Test suite for HandoffManager.complete_handoff()."""

    async def test_complete_handoff_with_completed_status(
        self, handoff_manager, conversation, target_agent_card
    ):
        """Should complete handoff successfully with COMPLETED status."""
        # Initiate handoff
        await handoff_manager.initiate_handoff(
            thread_id=str(conversation.id),
            tenant_id="tenant-1",
            user_id="user-1",
            source_agent_id="orchestrator",
            target_agent_card=target_agent_card,
            context_summary="Test context",
            handoff_reason="Testing",
        )

        # Complete handoff
        result = await handoff_manager.complete_handoff(
            thread_id=str(conversation.id),
            tenant_id="tenant-1",
            completion_status=CompletionStatus.COMPLETED,
            result_summary="Task completed successfully",
            artifacts=["artifact-1", "artifact-2"],
        )

        assert result.completion_status == CompletionStatus.COMPLETED
        assert result.result_summary == "Task completed successfully"
        assert result.artifacts_created == ["artifact-1", "artifact-2"]
        assert result.source_agent_id == "specialized-agent"
        assert result.target_agent_id == "orchestrator"

    async def test_complete_handoff_removes_from_cache(
        self, handoff_manager, conversation, target_agent_card
    ):
        """Should remove handoff from cache after completion."""
        # Initiate handoff
        await handoff_manager.initiate_handoff(
            thread_id=str(conversation.id),
            tenant_id="tenant-1",
            user_id="user-1",
            source_agent_id="orchestrator",
            target_agent_card=target_agent_card,
            context_summary="Test context",
            handoff_reason="Testing",
        )

        # Complete handoff
        await handoff_manager.complete_handoff(
            thread_id=str(conversation.id),
            tenant_id="tenant-1",
            completion_status=CompletionStatus.COMPLETED,
        )

        # Should return None (no active handoff)
        session = await handoff_manager.get_active_handoff(str(conversation.id), "tenant-1")
        assert session is None

    async def test_complete_handoff_persists_to_database(
        self, handoff_manager, conversation_repo, conversation, target_agent_card
    ):
        """Should persist completion state to database."""
        # Initiate handoff
        await handoff_manager.initiate_handoff(
            thread_id=str(conversation.id),
            tenant_id="tenant-1",
            user_id="user-1",
            source_agent_id="orchestrator",
            target_agent_card=target_agent_card,
            context_summary="Test context",
            handoff_reason="Testing",
        )

        # Complete handoff
        await handoff_manager.complete_handoff(
            thread_id=str(conversation.id),
            tenant_id="tenant-1",
            completion_status=CompletionStatus.COMPLETED,
            result_summary="Done",
        )

        # Load from database
        loaded = await conversation_repo.get_conversation(conversation.id, "tenant-1")
        session_data = loaded.state_metadata["handoff_session"]

        assert session_data["state"] == "completed"
        assert session_data["result_summary"] == "Done"
        assert session_data["completed_at"] is not None

    async def test_complete_handoff_with_cancelled_status(
        self, handoff_manager, conversation, target_agent_card
    ):
        """Should complete handoff with CANCELLED status."""
        # Initiate handoff
        await handoff_manager.initiate_handoff(
            thread_id=str(conversation.id),
            tenant_id="tenant-1",
            user_id="user-1",
            source_agent_id="orchestrator",
            target_agent_card=target_agent_card,
            context_summary="Test context",
            handoff_reason="Testing",
        )

        # Complete with cancelled
        result = await handoff_manager.complete_handoff(
            thread_id=str(conversation.id),
            tenant_id="tenant-1",
            completion_status=CompletionStatus.CANCELLED,
        )

        assert result.completion_status == CompletionStatus.CANCELLED

    async def test_complete_handoff_with_error_status(
        self, handoff_manager, conversation, target_agent_card
    ):
        """Should complete handoff with ERROR status."""
        # Initiate handoff
        await handoff_manager.initiate_handoff(
            thread_id=str(conversation.id),
            tenant_id="tenant-1",
            user_id="user-1",
            source_agent_id="orchestrator",
            target_agent_card=target_agent_card,
            context_summary="Test context",
            handoff_reason="Testing",
        )

        # Complete with error
        result = await handoff_manager.complete_handoff(
            thread_id=str(conversation.id),
            tenant_id="tenant-1",
            completion_status=CompletionStatus.ERROR,
            result_summary="An error occurred",
        )

        assert result.completion_status == CompletionStatus.ERROR

    async def test_complete_handoff_raises_error_if_no_active(self, handoff_manager):
        """Should raise HandoffError if no active handoff exists."""
        with pytest.raises(HandoffError, match="No active handoff found"):
            await handoff_manager.complete_handoff(
                thread_id=str(uuid4()),
                tenant_id="tenant-1",
                completion_status=CompletionStatus.COMPLETED,
            )


class TestHandoffManagerCancelHandoff:
    """Test suite for HandoffManager.cancel_handoff()."""

    async def test_cancel_handoff_success(self, handoff_manager, conversation, target_agent_card):
        """Should cancel active handoff successfully."""
        # Initiate handoff
        await handoff_manager.initiate_handoff(
            thread_id=str(conversation.id),
            tenant_id="tenant-1",
            user_id="user-1",
            source_agent_id="orchestrator",
            target_agent_card=target_agent_card,
            context_summary="Test context",
            handoff_reason="Testing",
        )

        # Cancel handoff
        result = await handoff_manager.cancel_handoff(str(conversation.id), "tenant-1")

        assert result.completion_status == CompletionStatus.CANCELLED
        assert result.result_summary == "Handoff cancelled"

    async def test_cancel_handoff_removes_from_cache(
        self, handoff_manager, conversation, target_agent_card
    ):
        """Should remove cancelled handoff from cache."""
        # Initiate handoff
        await handoff_manager.initiate_handoff(
            thread_id=str(conversation.id),
            tenant_id="tenant-1",
            user_id="user-1",
            source_agent_id="orchestrator",
            target_agent_card=target_agent_card,
            context_summary="Test context",
            handoff_reason="Testing",
        )

        # Cancel handoff
        await handoff_manager.cancel_handoff(str(conversation.id), "tenant-1")

        # Should return None
        session = await handoff_manager.get_active_handoff(str(conversation.id), "tenant-1")
        assert session is None


class TestHandoffManagerPersistence:
    """Test suite for handoff state persistence."""

    async def test_persistence_round_trip(self, conversation_repo, conversation, target_agent_card):
        """Should persist and restore handoff session correctly."""
        # Create first manager and initiate handoff
        manager1 = HandoffManager(A2AClient(), conversation_repo)
        await manager1.initiate_handoff(
            thread_id=str(conversation.id),
            tenant_id="tenant-1",
            user_id="user-1",
            source_agent_id="orchestrator",
            target_agent_card=target_agent_card,
            context_summary="Test context",
            handoff_reason="Testing persistence",
        )

        # Create second manager and retrieve handoff
        manager2 = HandoffManager(A2AClient(), conversation_repo)
        session = await manager2.get_active_handoff(str(conversation.id), "tenant-1")

        assert session is not None
        assert session.state == HandoffState.ACTIVE
        assert session.handoff_reason == "Testing persistence"
        assert session.context_summary == "Test context"

    async def test_multiple_handoff_lifecycle(
        self, handoff_manager, conversation, target_agent_card
    ):
        """Should handle multiple handoff lifecycles on same thread."""
        # First handoff
        await handoff_manager.initiate_handoff(
            thread_id=str(conversation.id),
            tenant_id="tenant-1",
            user_id="user-1",
            source_agent_id="orchestrator",
            target_agent_card=target_agent_card,
            context_summary="First handoff",
            handoff_reason="First task",
        )

        await handoff_manager.complete_handoff(
            thread_id=str(conversation.id),
            tenant_id="tenant-1",
            completion_status=CompletionStatus.COMPLETED,
        )

        # Second handoff should succeed
        await handoff_manager.initiate_handoff(
            thread_id=str(conversation.id),
            tenant_id="tenant-1",
            user_id="user-1",
            source_agent_id="orchestrator",
            target_agent_card=target_agent_card,
            context_summary="Second handoff",
            handoff_reason="Second task",
        )

        session = await handoff_manager.get_active_handoff(str(conversation.id), "tenant-1")
        assert session is not None
        assert session.context_summary == "Second handoff"
