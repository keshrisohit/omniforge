"""End-to-end integration tests for orchestration flows.

Tests the complete orchestration flow with real database persistence
and mocked A2AClient for controlled event streams.
"""

import asyncio
from datetime import datetime
from typing import AsyncIterator
from unittest.mock import AsyncMock

import pytest

from omniforge.agents.events import TaskDoneEvent, TaskMessageEvent
from omniforge.agents.models import (
    AgentCapabilities,
    AgentCard,
    AgentIdentity,
    AgentSkill,
    AuthScheme,
    SecurityConfig,
    SkillInputMode,
    SkillOutputMode,
    TextPart,
)
from omniforge.conversation.models import ConversationType
from omniforge.conversation.sqlite_repository import SQLiteConversationRepository
from omniforge.orchestration.client import A2AClient
from omniforge.orchestration.manager import DelegationStrategy, OrchestrationManager
from omniforge.storage.database import Database, DatabaseConfig
from omniforge.tasks.models import TaskState


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
def mock_a2a_client():
    """Create mock A2A client for controlled event streams."""
    return AsyncMock(spec=A2AClient)


@pytest.fixture
async def orchestration_manager(mock_a2a_client, conversation_repo):
    """Create orchestration manager with mocked client and real database."""
    return OrchestrationManager(mock_a2a_client, conversation_repo)


@pytest.fixture
async def conversation(conversation_repo):
    """Create a test conversation in the database."""
    return await conversation_repo.create_conversation(
        tenant_id="tenant-1",
        user_id="user-1",
        title="Integration Test Conversation",
        conversation_type=ConversationType.CHAT,
    )


def create_agent_card(agent_id: str) -> AgentCard:
    """Create an agent card with the given ID."""
    return AgentCard(
        protocolVersion="1.0",
        identity=AgentIdentity(
            id=agent_id,
            name=f"Agent {agent_id}",
            description=f"Test agent {agent_id}",
            version="1.0.0",
        ),
        capabilities=AgentCapabilities(),
        skills=[
            AgentSkill(
                id="test-skill",
                name="Test Skill",
                description="A test skill",
                inputModes=[SkillInputMode.TEXT],
                outputModes=[SkillOutputMode.TEXT],
            )
        ],
        serviceEndpoint="http://localhost:8000",
        security=SecurityConfig(auth_scheme=AuthScheme.NONE),
    )


async def create_mock_event_stream(
    response_text: str, task_id: str = "task-1"
) -> AsyncIterator:
    """Create a mock event stream with message and done events."""
    yield TaskMessageEvent(
        task_id=task_id,
        timestamp=datetime.now(),
        message_parts=[TextPart(text=response_text)],
    )
    yield TaskDoneEvent(
        task_id=task_id,
        timestamp=datetime.now(),
        final_state=TaskState.COMPLETED,
    )


class TestFullOrchestrationFlow:
    """Test complete Q&A orchestration flow with database persistence."""

    @pytest.mark.asyncio
    async def test_parallel_delegation_with_synthesis(
        self, orchestration_manager, mock_a2a_client, conversation
    ):
        """Should delegate to multiple agents in parallel and synthesize responses."""
        # Create two agent cards
        agent_cards = [
            create_agent_card("research-agent"),
            create_agent_card("analysis-agent"),
        ]

        # Mock A2A client to return different responses for each agent
        async def mock_send_task(agent_card, request):
            agent_id = agent_card.identity.id
            if agent_id == "research-agent":
                async for event in create_mock_event_stream("Research findings here"):
                    yield event
            elif agent_id == "analysis-agent":
                async for event in create_mock_event_stream("Analysis results here"):
                    yield event

        mock_a2a_client.send_task = mock_send_task

        # Execute parallel delegation
        results = await orchestration_manager.delegate_to_agents(
            thread_id=str(conversation.id),
            tenant_id="tenant-1",
            user_id="user-1",
            message="What can you tell me about X?",
            target_agent_cards=agent_cards,
            strategy=DelegationStrategy.PARALLEL,
        )

        # Verify both agents returned successfully
        assert len(results) == 2
        assert all(r.success for r in results)

        # Synthesize responses
        synthesized = orchestration_manager.synthesize_responses(results)

        # Verify synthesis contains both agent outputs
        assert "Research findings here" in synthesized
        assert "Analysis results here" in synthesized

    @pytest.mark.asyncio
    async def test_sequential_delegation_execution_order(
        self, orchestration_manager, mock_a2a_client, conversation
    ):
        """Should execute agents sequentially in order."""
        agent_cards = [
            create_agent_card("agent-1"),
            create_agent_card("agent-2"),
            create_agent_card("agent-3"),
        ]

        execution_order = []

        # Mock send_task to track execution order
        async def mock_send_task(agent_card, request):
            agent_id = agent_card.identity.id
            execution_order.append(agent_id)
            # Add small delay to ensure sequential execution
            await asyncio.sleep(0.01)
            async for event in create_mock_event_stream(f"Response from {agent_id}"):
                yield event

        mock_a2a_client.send_task = mock_send_task

        # Execute sequential delegation
        results = await orchestration_manager.delegate_to_agents(
            thread_id=str(conversation.id),
            tenant_id="tenant-1",
            user_id="user-1",
            message="Test message",
            target_agent_cards=agent_cards,
            strategy=DelegationStrategy.SEQUENTIAL,
        )

        # Verify agents called in order
        assert execution_order == ["agent-1", "agent-2", "agent-3"]

        # Verify all results successful
        assert len(results) == 3
        assert all(r.success for r in results)


class TestFirstSuccessStrategy:
    """Test first-success delegation strategy."""

    @pytest.mark.asyncio
    async def test_first_success_with_one_failure(
        self, orchestration_manager, mock_a2a_client, conversation
    ):
        """Should return first successful result when one agent fails."""
        agent_cards = [
            create_agent_card("slow-agent"),
            create_agent_card("fast-agent"),
        ]

        # Mock send_task - first agent fails, second succeeds
        async def mock_send_task(agent_card, request):
            agent_id = agent_card.identity.id
            if agent_id == "slow-agent":
                raise Exception("Agent failed")
            async for event in create_mock_event_stream("Fast agent response"):
                yield event

        mock_a2a_client.send_task = mock_send_task

        # Execute first-success delegation
        results = await orchestration_manager.delegate_to_agents(
            thread_id=str(conversation.id),
            tenant_id="tenant-1",
            user_id="user-1",
            message="Test message",
            target_agent_cards=agent_cards,
            strategy=DelegationStrategy.FIRST_SUCCESS,
        )

        # Should return only successful result
        assert len(results) == 1
        assert results[0].success is True
        assert results[0].agent_id == "fast-agent"
        assert results[0].response == "Fast agent response"


class TestAllAgentsFail:
    """Test error handling when all agents fail."""

    @pytest.mark.asyncio
    async def test_all_agents_fail_graceful_error(
        self, orchestration_manager, mock_a2a_client, conversation
    ):
        """Should handle all agents failing with graceful error message."""
        agent_cards = [
            create_agent_card("agent-1"),
            create_agent_card("agent-2"),
        ]

        # Mock all agents to fail
        async def mock_send_task(agent_card, request):
            raise Exception("Agent failed")

        mock_a2a_client.send_task = mock_send_task

        # Execute parallel delegation
        results = await orchestration_manager.delegate_to_agents(
            thread_id=str(conversation.id),
            tenant_id="tenant-1",
            user_id="user-1",
            message="Test message",
            target_agent_cards=agent_cards,
            strategy=DelegationStrategy.PARALLEL,
        )

        # Verify all failed
        assert len(results) == 2
        assert all(not r.success for r in results)

        # Synthesize should return graceful error
        synthesized = orchestration_manager.synthesize_responses(results)
        assert synthesized == "All sub-agents failed to provide responses."


class TestTimeoutHandling:
    """Test timeout handling for slow agents."""

    @pytest.mark.asyncio
    async def test_agent_timeout_behavior(
        self, orchestration_manager, mock_a2a_client, conversation
    ):
        """Should handle agent timeout with error result."""
        agent_card = create_agent_card("slow-agent")

        # Mock send_task to simulate timeout
        async def mock_send_task(agent_card, request):
            # Sleep longer than timeout
            await asyncio.sleep(10)
            async for event in create_mock_event_stream("Late response"):
                yield event

        mock_a2a_client.send_task = mock_send_task

        # Execute with short timeout (100ms)
        result = await orchestration_manager._execute_agent(
            agent_card, "tenant-1", "user-1", "Test message", timeout_ms=100
        )

        # Should fail with timeout error
        assert result.success is False
        assert "timed out" in result.error.lower()
