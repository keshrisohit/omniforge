"""Tests for StreamRouter message routing based on handoff state.

Tests StreamRouter with mocked HandoffManager and OrchestrationManager,
focusing on routing logic based on handoff state.
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
from omniforge.orchestration.a2a_models import CompletionStatus
from omniforge.orchestration.client import A2AClient
from omniforge.orchestration.handoff import HandoffManager
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
def handoff_manager(a2a_client, conversation_repo):
    """Create HandoffManager instance."""
    return HandoffManager(a2a_client, conversation_repo)


@pytest.fixture
def orchestration_manager(a2a_client, conversation_repo):
    """Create OrchestrationManager instance."""
    return OrchestrationManager(a2a_client, conversation_repo)


@pytest.fixture
def stream_router(handoff_manager, orchestration_manager):
    """Create StreamRouter instance."""
    return StreamRouter(handoff_manager, orchestration_manager)


@pytest.fixture
def agent_card():
    """Create a sample agent card for testing."""
    return AgentCard(
        protocol_version="1.0",
        identity=AgentIdentity(
            id="test-agent-123",
            name="Test Agent",
            description="A test agent",
            version="1.0.0",
        ),
        capabilities=AgentCapabilities(streaming=True, multi_turn=True),
        skills=[
            AgentSkill(
                id="test-skill",
                name="Test Skill",
                description="A test skill",
                input_modes=[SkillInputMode.TEXT],
                output_modes=[SkillOutputMode.TEXT],
            )
        ],
        service_endpoint="http://localhost:8001",
        security=SecurityConfig(auth_scheme=AuthScheme.BEARER, require_https=True),
    )


class TestStreamRouter:
    """Tests for StreamRouter class."""

    @pytest.mark.asyncio
    async def test_route_message_no_handoff(self, stream_router, conversation_repo, db) -> None:
        """Message should route to orchestrator when no active handoff exists."""
        # Arrange
        thread_id = str(uuid4())
        tenant_id = "tenant-1"
        user_id = "user-1"
        message = "Hello, how can you help?"

        # Create conversation in database
        await conversation_repo.create_conversation(
            conversation_id=thread_id,
            tenant_id=tenant_id,
            user_id=user_id,
            conversation_type=ConversationType.CHAT,
        )

        # Act
        results = []
        async for result in stream_router.route_message(thread_id, tenant_id, user_id, message):
            results.append(result)

        # Assert
        assert len(results) == 1
        assert results[0] == f"[ORCHESTRATOR] {message}"

    @pytest.mark.asyncio
    async def test_route_message_with_active_handoff(
        self, stream_router, handoff_manager, conversation_repo, agent_card, db
    ) -> None:
        """Message should route to handoff path when active handoff exists."""
        # Arrange
        thread_id = str(uuid4())
        tenant_id = "tenant-1"
        user_id = "user-1"
        source_agent_id = "orchestrator-agent"
        message = "Please analyze this code"

        # Create conversation in database
        await conversation_repo.create_conversation(
            conversation_id=thread_id,
            tenant_id=tenant_id,
            user_id=user_id,
            conversation_type=ConversationType.CHAT,
        )

        # Initiate handoff
        await handoff_manager.initiate_handoff(
            thread_id=thread_id,
            tenant_id=tenant_id,
            user_id=user_id,
            source_agent_id=source_agent_id,
            target_agent_card=agent_card,
            context_summary="User needs code analysis",
            handoff_reason="Specialized code analysis required",
        )

        # Act
        results = []
        async for result in stream_router.route_message(thread_id, tenant_id, user_id, message):
            results.append(result)

        # Assert
        assert len(results) == 1
        assert results[0] == f"[HANDOFF:{agent_card.identity.id}] {message}"
        assert agent_card.identity.id in results[0]

    @pytest.mark.asyncio
    async def test_route_message_after_handoff_completed(
        self, stream_router, handoff_manager, conversation_repo, agent_card, db
    ) -> None:
        """Message should route to orchestrator after handoff is completed."""
        # Arrange
        thread_id = str(uuid4())
        tenant_id = "tenant-1"
        user_id = "user-1"
        source_agent_id = "orchestrator-agent"
        message = "What's the status?"

        # Create conversation in database
        await conversation_repo.create_conversation(
            conversation_id=thread_id,
            tenant_id=tenant_id,
            user_id=user_id,
            conversation_type=ConversationType.CHAT,
        )

        # Initiate and complete handoff
        await handoff_manager.initiate_handoff(
            thread_id=thread_id,
            tenant_id=tenant_id,
            user_id=user_id,
            source_agent_id=source_agent_id,
            target_agent_card=agent_card,
            context_summary="User needs code analysis",
            handoff_reason="Specialized code analysis required",
        )

        await handoff_manager.complete_handoff(
            thread_id=thread_id,
            tenant_id=tenant_id,
            completion_status=CompletionStatus.COMPLETED,
            result_summary="Analysis completed successfully",
        )

        # Act
        results = []
        async for result in stream_router.route_message(thread_id, tenant_id, user_id, message):
            results.append(result)

        # Assert
        assert len(results) == 1
        assert results[0] == f"[ORCHESTRATOR] {message}"

    @pytest.mark.asyncio
    async def test_is_handoff_active_returns_false_no_handoff(
        self, stream_router, conversation_repo, db
    ) -> None:
        """is_handoff_active should return False when no handoff exists."""
        # Arrange
        thread_id = str(uuid4())
        tenant_id = "tenant-1"
        user_id = "user-1"

        # Create conversation in database
        await conversation_repo.create_conversation(
            conversation_id=thread_id,
            tenant_id=tenant_id,
            user_id=user_id,
            conversation_type=ConversationType.CHAT,
        )

        # Act
        is_active = await stream_router.is_handoff_active(thread_id, tenant_id)

        # Assert
        assert is_active is False

    @pytest.mark.asyncio
    async def test_is_handoff_active_returns_true_with_active_handoff(
        self, stream_router, handoff_manager, conversation_repo, agent_card, db
    ) -> None:
        """is_handoff_active should return True when active handoff exists."""
        # Arrange
        thread_id = str(uuid4())
        tenant_id = "tenant-1"
        user_id = "user-1"
        source_agent_id = "orchestrator-agent"

        # Create conversation in database
        await conversation_repo.create_conversation(
            conversation_id=thread_id,
            tenant_id=tenant_id,
            user_id=user_id,
            conversation_type=ConversationType.CHAT,
        )

        # Initiate handoff
        await handoff_manager.initiate_handoff(
            thread_id=thread_id,
            tenant_id=tenant_id,
            user_id=user_id,
            source_agent_id=source_agent_id,
            target_agent_card=agent_card,
            context_summary="User needs code analysis",
            handoff_reason="Specialized code analysis required",
        )

        # Act
        is_active = await stream_router.is_handoff_active(thread_id, tenant_id)

        # Assert
        assert is_active is True

    @pytest.mark.asyncio
    async def test_is_handoff_active_returns_false_after_completion(
        self, stream_router, handoff_manager, conversation_repo, agent_card, db
    ) -> None:
        """is_handoff_active should return False after handoff completion."""
        # Arrange
        thread_id = str(uuid4())
        tenant_id = "tenant-1"
        user_id = "user-1"
        source_agent_id = "orchestrator-agent"

        # Create conversation in database
        await conversation_repo.create_conversation(
            conversation_id=thread_id,
            tenant_id=tenant_id,
            user_id=user_id,
            conversation_type=ConversationType.CHAT,
        )

        # Initiate and complete handoff
        await handoff_manager.initiate_handoff(
            thread_id=thread_id,
            tenant_id=tenant_id,
            user_id=user_id,
            source_agent_id=source_agent_id,
            target_agent_card=agent_card,
            context_summary="User needs code analysis",
            handoff_reason="Specialized code analysis required",
        )

        await handoff_manager.complete_handoff(
            thread_id=thread_id,
            tenant_id=tenant_id,
            completion_status=CompletionStatus.COMPLETED,
            result_summary="Analysis completed successfully",
        )

        # Act
        is_active = await stream_router.is_handoff_active(thread_id, tenant_id)

        # Assert
        assert is_active is False

    @pytest.mark.asyncio
    async def test_route_message_with_cancelled_handoff(
        self, stream_router, handoff_manager, conversation_repo, agent_card, db
    ) -> None:
        """Message should route to orchestrator after handoff cancellation."""
        # Arrange
        thread_id = str(uuid4())
        tenant_id = "tenant-1"
        user_id = "user-1"
        source_agent_id = "orchestrator-agent"
        message = "Let's try something else"

        # Create conversation in database
        await conversation_repo.create_conversation(
            conversation_id=thread_id,
            tenant_id=tenant_id,
            user_id=user_id,
            conversation_type=ConversationType.CHAT,
        )

        # Initiate and cancel handoff
        await handoff_manager.initiate_handoff(
            thread_id=thread_id,
            tenant_id=tenant_id,
            user_id=user_id,
            source_agent_id=source_agent_id,
            target_agent_card=agent_card,
            context_summary="User needs code analysis",
            handoff_reason="Specialized code analysis required",
        )

        await handoff_manager.cancel_handoff(thread_id=thread_id, tenant_id=tenant_id)

        # Act
        results = []
        async for result in stream_router.route_message(thread_id, tenant_id, user_id, message):
            results.append(result)

        # Assert
        assert len(results) == 1
        assert results[0] == f"[ORCHESTRATOR] {message}"

    @pytest.mark.asyncio
    async def test_route_message_includes_target_agent_id(
        self, stream_router, handoff_manager, conversation_repo, agent_card, db
    ) -> None:
        """Handoff routing should include target agent ID in output."""
        # Arrange
        thread_id = str(uuid4())
        tenant_id = "tenant-1"
        user_id = "user-1"
        source_agent_id = "orchestrator-agent"
        message = "Analyze this function"

        # Create conversation in database
        await conversation_repo.create_conversation(
            conversation_id=thread_id,
            tenant_id=tenant_id,
            user_id=user_id,
            conversation_type=ConversationType.CHAT,
        )

        # Initiate handoff
        await handoff_manager.initiate_handoff(
            thread_id=thread_id,
            tenant_id=tenant_id,
            user_id=user_id,
            source_agent_id=source_agent_id,
            target_agent_card=agent_card,
            context_summary="User needs code analysis",
            handoff_reason="Specialized code analysis required",
        )

        # Act
        results = []
        async for result in stream_router.route_message(thread_id, tenant_id, user_id, message):
            results.append(result)

        # Assert
        assert len(results) == 1
        # Verify target agent ID is present in the output
        assert f"[HANDOFF:{agent_card.identity.id}]" in results[0]
        assert message in results[0]
