"""End-to-end integration tests for handoff flows.

Tests the complete handoff lifecycle with real database persistence,
cache management, tenant isolation, and StreamRouter integration.
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
from omniforge.orchestration.handoff import HandoffManager, HandoffState
from omniforge.orchestration.manager import OrchestrationManager
from omniforge.orchestration.stream_router import StreamRouter
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
async def orchestration_manager(a2a_client, conversation_repo):
    """Create OrchestrationManager instance."""
    return OrchestrationManager(a2a_client, conversation_repo)


@pytest.fixture
async def stream_router(handoff_manager, orchestration_manager):
    """Create StreamRouter instance."""
    return StreamRouter(handoff_manager, orchestration_manager)


@pytest.fixture
async def conversation(conversation_repo):
    """Create a test conversation in the database."""
    return await conversation_repo.create_conversation(
        tenant_id="tenant-1",
        user_id="user-1",
        title="Handoff Test Conversation",
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
                description="A specialized skill",
                input_modes=[SkillInputMode.TEXT],
                output_modes=[SkillOutputMode.TEXT],
            )
        ],
        service_endpoint="http://localhost:8001",
        security=SecurityConfig(auth_scheme=AuthScheme.BEARER, require_https=True),
    )


class TestFullHandoffLifecycle:
    """Test complete handoff lifecycle with database persistence."""

    @pytest.mark.asyncio
    async def test_handoff_lifecycle_with_persistence(
        self, handoff_manager, conversation_repo, conversation, target_agent_card
    ):
        """Should complete full handoff lifecycle: initiate → persist → complete → clear."""
        # Step 1: Initiate handoff
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
        assert result.target_agent_id == "specialized-agent"

        # Step 2: Verify persistence in database
        loaded_conv = await conversation_repo.get_conversation(conversation.id, "tenant-1")
        assert loaded_conv.state_metadata is not None
        assert "handoff_session" in loaded_conv.state_metadata

        session_data = loaded_conv.state_metadata["handoff_session"]
        assert session_data["state"] == "active"
        assert session_data["target_agent_id"] == "specialized-agent"

        # Step 3: Verify session retrievable from cache
        active_session = await handoff_manager.get_active_handoff(
            str(conversation.id), "tenant-1"
        )
        assert active_session is not None
        assert active_session.state == HandoffState.ACTIVE

        # Step 4: Complete handoff
        completion_result = await handoff_manager.complete_handoff(
            thread_id=str(conversation.id),
            tenant_id="tenant-1",
            completion_status=CompletionStatus.COMPLETED,
            result_summary="Task completed successfully",
            artifacts=["doc-1", "doc-2"],
        )

        assert completion_result.completion_status == CompletionStatus.COMPLETED
        assert completion_result.result_summary == "Task completed successfully"

        # Step 5: Verify cache cleared
        cleared_session = await handoff_manager.get_active_handoff(
            str(conversation.id), "tenant-1"
        )
        assert cleared_session is None

        # Step 6: Verify completion persisted to database
        final_conv = await conversation_repo.get_conversation(conversation.id, "tenant-1")
        final_session_data = final_conv.state_metadata["handoff_session"]
        assert final_session_data["state"] == "completed"
        assert final_session_data["result_summary"] == "Task completed successfully"
        assert final_session_data["completed_at"] is not None


class TestConcurrentHandoffPrevention:
    """Test prevention of concurrent handoffs on same thread."""

    @pytest.mark.asyncio
    async def test_concurrent_handoff_raises_error(
        self, handoff_manager, conversation, target_agent_card
    ):
        """Should prevent second handoff when one is already active."""
        # First handoff succeeds
        await handoff_manager.initiate_handoff(
            thread_id=str(conversation.id),
            tenant_id="tenant-1",
            user_id="user-1",
            source_agent_id="orchestrator",
            target_agent_card=target_agent_card,
            context_summary="First handoff",
            handoff_reason="Testing",
        )

        # Second handoff should raise error
        with pytest.raises(HandoffError, match="Active handoff already exists"):
            await handoff_manager.initiate_handoff(
                thread_id=str(conversation.id),
                tenant_id="tenant-1",
                user_id="user-1",
                source_agent_id="orchestrator",
                target_agent_card=target_agent_card,
                context_summary="Second handoff",
                handoff_reason="Should fail",
            )


class TestHandoffCancellation:
    """Test handoff cancellation flow."""

    @pytest.mark.asyncio
    async def test_cancel_handoff_clears_state(
        self, handoff_manager, conversation_repo, conversation, target_agent_card
    ):
        """Should cancel handoff and clear both cache and database state."""
        # Initiate handoff
        await handoff_manager.initiate_handoff(
            thread_id=str(conversation.id),
            tenant_id="tenant-1",
            user_id="user-1",
            source_agent_id="orchestrator",
            target_agent_card=target_agent_card,
            context_summary="Test context",
            handoff_reason="Testing cancellation",
        )

        # Cancel handoff
        result = await handoff_manager.cancel_handoff(str(conversation.id), "tenant-1")

        assert result.completion_status == CompletionStatus.CANCELLED
        assert result.result_summary == "Handoff cancelled"

        # Verify cache cleared
        session = await handoff_manager.get_active_handoff(str(conversation.id), "tenant-1")
        assert session is None

        # Verify state persisted as CANCELLED
        loaded_conv = await conversation_repo.get_conversation(conversation.id, "tenant-1")
        session_data = loaded_conv.state_metadata["handoff_session"]
        assert session_data["state"] == "cancelled"


class TestHandoffRecoveryFromDatabase:
    """Test recovery of handoff state from database after cache miss."""

    @pytest.mark.asyncio
    async def test_recovery_from_database_after_cache_clear(
        self, conversation_repo, conversation, target_agent_card
    ):
        """Should load handoff from database when not in cache."""
        # Create first manager and initiate handoff
        manager1 = HandoffManager(A2AClient(), conversation_repo)
        await manager1.initiate_handoff(
            thread_id=str(conversation.id),
            tenant_id="tenant-1",
            user_id="user-1",
            source_agent_id="orchestrator",
            target_agent_card=target_agent_card,
            context_summary="Original context",
            handoff_reason="Testing recovery",
        )

        # Create second manager (empty cache)
        manager2 = HandoffManager(A2AClient(), conversation_repo)

        # Should load from database
        recovered_session = await manager2.get_active_handoff(
            str(conversation.id), "tenant-1"
        )

        assert recovered_session is not None
        assert recovered_session.state == HandoffState.ACTIVE
        assert recovered_session.context_summary == "Original context"
        assert recovered_session.handoff_reason == "Testing recovery"
        assert recovered_session.target_agent_id == "specialized-agent"


class TestStreamRouterIntegration:
    """Test StreamRouter message routing based on handoff state."""

    @pytest.mark.asyncio
    async def test_route_message_to_handoff_when_active(
        self, stream_router, handoff_manager, conversation, target_agent_card
    ):
        """Should route message to handoff path when handoff is active."""
        # Initiate handoff
        await handoff_manager.initiate_handoff(
            thread_id=str(conversation.id),
            tenant_id="tenant-1",
            user_id="user-1",
            source_agent_id="orchestrator",
            target_agent_card=target_agent_card,
            context_summary="Test context",
            handoff_reason="Testing routing",
        )

        # Route message
        messages = []
        async for msg in stream_router.route_message(
            str(conversation.id), "tenant-1", "user-1", "Hello"
        ):
            messages.append(msg)

        # Should route to handoff
        assert len(messages) == 1
        assert messages[0].startswith("[HANDOFF:specialized-agent]")
        assert "Hello" in messages[0]

    @pytest.mark.asyncio
    async def test_route_message_to_orchestrator_after_completion(
        self, stream_router, handoff_manager, conversation, target_agent_card
    ):
        """Should route to orchestrator after handoff completion."""
        # Initiate and complete handoff
        await handoff_manager.initiate_handoff(
            thread_id=str(conversation.id),
            tenant_id="tenant-1",
            user_id="user-1",
            source_agent_id="orchestrator",
            target_agent_card=target_agent_card,
            context_summary="Test context",
            handoff_reason="Testing routing",
        )

        await handoff_manager.complete_handoff(
            thread_id=str(conversation.id),
            tenant_id="tenant-1",
            completion_status=CompletionStatus.COMPLETED,
        )

        # Route message
        messages = []
        async for msg in stream_router.route_message(
            str(conversation.id), "tenant-1", "user-1", "Hello"
        ):
            messages.append(msg)

        # Should route to orchestrator
        assert len(messages) == 1
        assert messages[0].startswith("[ORCHESTRATOR]")
        assert "Hello" in messages[0]

    @pytest.mark.asyncio
    async def test_is_handoff_active_check(
        self, stream_router, handoff_manager, conversation, target_agent_card
    ):
        """Should correctly check handoff active state."""
        # Initially no handoff
        is_active = await stream_router.is_handoff_active(str(conversation.id), "tenant-1")
        assert is_active is False

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

        # Should be active
        is_active = await stream_router.is_handoff_active(str(conversation.id), "tenant-1")
        assert is_active is True

        # Complete handoff
        await handoff_manager.complete_handoff(
            thread_id=str(conversation.id),
            tenant_id="tenant-1",
            completion_status=CompletionStatus.COMPLETED,
        )

        # Should be inactive
        is_active = await stream_router.is_handoff_active(str(conversation.id), "tenant-1")
        assert is_active is False


class TestTenantIsolation:
    """Test tenant isolation across all handoff operations."""

    @pytest.mark.asyncio
    async def test_tenant_isolation_for_handoff_access(
        self, conversation_repo, target_agent_card
    ):
        """Should prevent accessing handoff from wrong tenant."""
        # Create conversations for two tenants
        conv_tenant1 = await conversation_repo.create_conversation(
            tenant_id="tenant-1",
            user_id="user-1",
            title="Tenant 1 Conversation",
            conversation_type=ConversationType.CHAT,
        )

        # Create handoff for tenant-1
        manager = HandoffManager(A2AClient(), conversation_repo)
        await manager.initiate_handoff(
            thread_id=str(conv_tenant1.id),
            tenant_id="tenant-1",
            user_id="user-1",
            source_agent_id="orchestrator",
            target_agent_card=target_agent_card,
            context_summary="Tenant 1 context",
            handoff_reason="Testing isolation",
        )

        # Attempt to access from tenant-2 should fail
        with pytest.raises(ValueError, match="does not belong to tenant"):
            await manager.get_active_handoff(str(conv_tenant1.id), "tenant-2")

    @pytest.mark.asyncio
    async def test_tenant_isolation_prevents_cross_tenant_completion(
        self, conversation_repo, target_agent_card
    ):
        """Should prevent completing handoff from wrong tenant."""
        # Create conversation for tenant-1
        conv = await conversation_repo.create_conversation(
            tenant_id="tenant-1",
            user_id="user-1",
            title="Tenant 1 Conversation",
            conversation_type=ConversationType.CHAT,
        )

        # Create handoff for tenant-1
        manager = HandoffManager(A2AClient(), conversation_repo)
        await manager.initiate_handoff(
            thread_id=str(conv.id),
            tenant_id="tenant-1",
            user_id="user-1",
            source_agent_id="orchestrator",
            target_agent_card=target_agent_card,
            context_summary="Test context",
            handoff_reason="Testing",
        )

        # Attempt to complete from tenant-2 should fail with ValueError
        # (tenant validation happens before HandoffError check)
        with pytest.raises(ValueError, match="does not belong to tenant"):
            await manager.complete_handoff(
                thread_id=str(conv.id),
                tenant_id="tenant-2",
                completion_status=CompletionStatus.COMPLETED,
            )


class TestConcurrentOperations:
    """Test concurrent operations across multiple threads."""

    @pytest.mark.asyncio
    async def test_multiple_handoffs_on_different_threads(
        self, handoff_manager, conversation_repo, target_agent_card
    ):
        """Should handle multiple handoffs on different threads concurrently."""
        # Create two conversations
        conv1 = await conversation_repo.create_conversation(
            tenant_id="tenant-1",
            user_id="user-1",
            title="Conversation 1",
            conversation_type=ConversationType.CHAT,
        )

        conv2 = await conversation_repo.create_conversation(
            tenant_id="tenant-1",
            user_id="user-1",
            title="Conversation 2",
            conversation_type=ConversationType.CHAT,
        )

        # Initiate handoffs on both threads
        await handoff_manager.initiate_handoff(
            thread_id=str(conv1.id),
            tenant_id="tenant-1",
            user_id="user-1",
            source_agent_id="orchestrator",
            target_agent_card=target_agent_card,
            context_summary="Context 1",
            handoff_reason="Reason 1",
        )

        await handoff_manager.initiate_handoff(
            thread_id=str(conv2.id),
            tenant_id="tenant-1",
            user_id="user-1",
            source_agent_id="orchestrator",
            target_agent_card=target_agent_card,
            context_summary="Context 2",
            handoff_reason="Reason 2",
        )

        # Verify both handoffs active
        session1 = await handoff_manager.get_active_handoff(str(conv1.id), "tenant-1")
        session2 = await handoff_manager.get_active_handoff(str(conv2.id), "tenant-1")

        assert session1 is not None
        assert session2 is not None
        assert session1.context_summary == "Context 1"
        assert session2.context_summary == "Context 2"

        # Complete first handoff
        await handoff_manager.complete_handoff(
            thread_id=str(conv1.id),
            tenant_id="tenant-1",
            completion_status=CompletionStatus.COMPLETED,
        )

        # Verify first handoff cleared, second still active
        session1_after = await handoff_manager.get_active_handoff(str(conv1.id), "tenant-1")
        session2_after = await handoff_manager.get_active_handoff(str(conv2.id), "tenant-1")

        assert session1_after is None
        assert session2_after is not None
