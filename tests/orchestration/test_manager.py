"""Tests for orchestration manager."""

import asyncio
from datetime import datetime
from typing import AsyncIterator
from unittest.mock import AsyncMock, MagicMock

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
from omniforge.orchestration.manager import (
    DelegationStrategy,
    OrchestrationManager,
    SubAgentResult,
)
from omniforge.tasks.models import TaskState


@pytest.fixture
def mock_client() -> AsyncMock:
    """Create a mock A2A client."""
    return AsyncMock()


@pytest.fixture
def mock_conversation_repo() -> MagicMock:
    """Create a mock conversation repository."""
    return MagicMock()


@pytest.fixture
def orchestration_manager(
    mock_client: AsyncMock, mock_conversation_repo: MagicMock
) -> OrchestrationManager:
    """Create an orchestration manager with mocked dependencies."""
    return OrchestrationManager(mock_client, mock_conversation_repo)


@pytest.fixture
def sample_agent_card() -> AgentCard:
    """Create a sample agent card for testing."""
    return AgentCard(
        protocolVersion="1.0",
        identity=AgentIdentity(
            id="test-agent",
            name="Test Agent",
            description="A test agent",
            version="1.0.0",
        ),
        capabilities=AgentCapabilities(),
        skills=[
            AgentSkill(
                id="skill-1",
                name="Test Skill",
                description="A test skill",
                inputModes=[SkillInputMode.TEXT],
                outputModes=[SkillOutputMode.TEXT],
            )
        ],
        serviceEndpoint="http://localhost:8000",
        security=SecurityConfig(auth_scheme=AuthScheme.NONE),
    )


def create_agent_card(agent_id: str) -> AgentCard:
    """Create an agent card with the given ID."""
    return AgentCard(
        protocolVersion="1.0",
        identity=AgentIdentity(
            id=agent_id,
            name=f"Agent {agent_id}",
            description=f"Agent {agent_id}",
            version="1.0.0",
        ),
        capabilities=AgentCapabilities(),
        skills=[
            AgentSkill(
                id="skill-1",
                name="Test Skill",
                description="A test skill",
                inputModes=[SkillInputMode.TEXT],
                outputModes=[SkillOutputMode.TEXT],
            )
        ],
        serviceEndpoint="http://localhost:8000",
        security=SecurityConfig(auth_scheme=AuthScheme.NONE),
    )


async def create_mock_event_stream(response_text: str, task_id: str = "task-1") -> AsyncIterator:
    """Create a mock event stream with a message and done event."""
    # Message event
    yield TaskMessageEvent(
        task_id=task_id,
        timestamp=datetime.now(),
        message_parts=[TextPart(text=response_text)],
    )
    # Done event
    yield TaskDoneEvent(
        task_id=task_id,
        timestamp=datetime.now(),
        final_state=TaskState.COMPLETED,
    )


async def create_failing_event_stream() -> AsyncIterator:
    """Create an empty event stream (no response)."""
    if False:
        yield  # Make this a generator


class TestSubAgentResult:
    """Tests for SubAgentResult dataclass."""

    def test_successful_result(self) -> None:
        """SubAgentResult should store successful execution data."""
        result = SubAgentResult(
            agent_id="agent-1",
            success=True,
            response="Test response",
            latency_ms=100,
        )

        assert result.agent_id == "agent-1"
        assert result.success is True
        assert result.response == "Test response"
        assert result.error is None
        assert result.latency_ms == 100

    def test_failed_result(self) -> None:
        """SubAgentResult should store failed execution data."""
        result = SubAgentResult(
            agent_id="agent-1",
            success=False,
            error="Connection failed",
            latency_ms=50,
        )

        assert result.agent_id == "agent-1"
        assert result.success is False
        assert result.response is None
        assert result.error == "Connection failed"
        assert result.latency_ms == 50


class TestDelegateToAgents:
    """Tests for delegate_to_agents method."""

    @pytest.mark.asyncio
    async def test_empty_agent_list_raises_error(
        self, orchestration_manager: OrchestrationManager
    ) -> None:
        """Delegate should raise ValueError if no agents provided."""
        with pytest.raises(ValueError, match="at least one target agent"):
            await orchestration_manager.delegate_to_agents(
                thread_id="thread-1",
                tenant_id="tenant-1",
                user_id="user-1",
                message="Test message",
                target_agent_cards=[],
                strategy=DelegationStrategy.PARALLEL,
            )

    @pytest.mark.asyncio
    async def test_unknown_strategy_raises_error(
        self, orchestration_manager: OrchestrationManager, sample_agent_card: AgentCard
    ) -> None:
        """Delegate should raise ValueError for unknown strategy."""
        with pytest.raises(ValueError, match="Unknown delegation strategy"):
            await orchestration_manager.delegate_to_agents(
                thread_id="thread-1",
                tenant_id="tenant-1",
                user_id="user-1",
                message="Test message",
                target_agent_cards=[sample_agent_card],
                strategy="invalid_strategy",  # type: ignore
            )


class TestParallelDelegation:
    """Tests for parallel delegation strategy."""

    @pytest.mark.asyncio
    async def test_parallel_executes_all_agents_concurrently(
        self,
        orchestration_manager: OrchestrationManager,
        mock_client: AsyncMock,
    ) -> None:
        """Parallel delegation should execute all agents concurrently."""
        # Create multiple agent cards
        agent_cards = [create_agent_card(f"agent-{i}") for i in range(3)]

        # Mock send_task to return different responses
        async def mock_send_task(agent_card, request):
            agent_id = agent_card.identity.id
            async for event in create_mock_event_stream(f"Response from {agent_id}"):
                yield event

        mock_client.send_task = mock_send_task

        # Execute parallel delegation
        results = await orchestration_manager.delegate_to_agents(
            thread_id="thread-1",
            tenant_id="tenant-1",
            user_id="user-1",
            message="Test message",
            target_agent_cards=agent_cards,
            strategy=DelegationStrategy.PARALLEL,
        )

        # Verify all agents returned results
        assert len(results) == 3
        for i, result in enumerate(results):
            assert result.success is True
            assert result.response == f"Response from agent-{i}"
            assert result.latency_ms >= 0

    @pytest.mark.asyncio
    async def test_parallel_handles_individual_failures(
        self,
        orchestration_manager: OrchestrationManager,
        mock_client: AsyncMock,
    ) -> None:
        """Parallel delegation should not fail if one agent fails."""
        agent_cards = [create_agent_card(f"agent-{i}") for i in range(3)]

        # Mock send_task - agent-1 fails, others succeed
        async def mock_send_task(agent_card, request):
            agent_id = agent_card.identity.id
            if agent_id == "agent-1":
                raise Exception("Agent failed")
            async for event in create_mock_event_stream(f"Response from {agent_id}"):
                yield event

        mock_client.send_task = mock_send_task

        results = await orchestration_manager.delegate_to_agents(
            thread_id="thread-1",
            tenant_id="tenant-1",
            user_id="user-1",
            message="Test message",
            target_agent_cards=agent_cards,
            strategy=DelegationStrategy.PARALLEL,
        )

        # Verify we got all results
        assert len(results) == 3

        # Check successful agents
        assert results[0].success is True
        assert results[0].response == "Response from agent-0"

        # Check failed agent
        assert results[1].success is False
        assert "Agent failed" in results[1].error

        # Check last successful agent
        assert results[2].success is True
        assert results[2].response == "Response from agent-2"


class TestSequentialDelegation:
    """Tests for sequential delegation strategy."""

    @pytest.mark.asyncio
    async def test_sequential_executes_agents_in_order(
        self,
        orchestration_manager: OrchestrationManager,
        mock_client: AsyncMock,
    ) -> None:
        """Sequential delegation should execute agents one at a time."""
        agent_cards = [create_agent_card(f"agent-{i}") for i in range(3)]
        execution_order = []

        # Mock send_task to track execution order
        async def mock_send_task(agent_card, request):
            agent_id = agent_card.identity.id
            execution_order.append(agent_id)
            # Add small delay to ensure sequential execution
            await asyncio.sleep(0.01)
            async for event in create_mock_event_stream(f"Response from {agent_id}"):
                yield event

        mock_client.send_task = mock_send_task

        results = await orchestration_manager.delegate_to_agents(
            thread_id="thread-1",
            tenant_id="tenant-1",
            user_id="user-1",
            message="Test message",
            target_agent_cards=agent_cards,
            strategy=DelegationStrategy.SEQUENTIAL,
        )

        # Verify execution order
        assert execution_order == ["agent-0", "agent-1", "agent-2"]

        # Verify all results
        assert len(results) == 3
        for i, result in enumerate(results):
            assert result.success is True
            assert result.response == f"Response from agent-{i}"

    @pytest.mark.asyncio
    async def test_sequential_continues_after_failure(
        self,
        orchestration_manager: OrchestrationManager,
        mock_client: AsyncMock,
    ) -> None:
        """Sequential delegation should continue even if one agent fails."""
        agent_cards = [create_agent_card(f"agent-{i}") for i in range(3)]

        # Mock send_task - agent-1 fails
        async def mock_send_task(agent_card, request):
            agent_id = agent_card.identity.id
            if agent_id == "agent-1":
                raise Exception("Agent failed")
            async for event in create_mock_event_stream(f"Response from {agent_id}"):
                yield event

        mock_client.send_task = mock_send_task

        results = await orchestration_manager.delegate_to_agents(
            thread_id="thread-1",
            tenant_id="tenant-1",
            user_id="user-1",
            message="Test message",
            target_agent_cards=agent_cards,
            strategy=DelegationStrategy.SEQUENTIAL,
        )

        # Verify all executed
        assert len(results) == 3
        assert results[0].success is True
        assert results[1].success is False
        assert results[2].success is True


class TestFirstSuccessDelegation:
    """Tests for first-success delegation strategy."""

    @pytest.mark.asyncio
    async def test_first_success_returns_first_successful_result(
        self,
        orchestration_manager: OrchestrationManager,
        mock_client: AsyncMock,
    ) -> None:
        """First-success should return immediately on first success."""
        agent_cards = [create_agent_card(f"agent-{i}") for i in range(3)]

        # Mock send_task - agent-0 succeeds quickly, others delayed
        async def mock_send_task(agent_card, request):
            agent_id = agent_card.identity.id
            if agent_id != "agent-0":
                # Add delay for other agents
                await asyncio.sleep(1.0)
            async for event in create_mock_event_stream(f"Response from {agent_id}"):
                yield event

        mock_client.send_task = mock_send_task

        results = await orchestration_manager.delegate_to_agents(
            thread_id="thread-1",
            tenant_id="tenant-1",
            user_id="user-1",
            message="Test message",
            target_agent_cards=agent_cards,
            strategy=DelegationStrategy.FIRST_SUCCESS,
        )

        # Should return only first success
        assert len(results) == 1
        assert results[0].success is True
        assert results[0].agent_id == "agent-0"
        assert results[0].response == "Response from agent-0"

    @pytest.mark.asyncio
    async def test_first_success_returns_all_if_all_fail(
        self,
        orchestration_manager: OrchestrationManager,
        mock_client: AsyncMock,
    ) -> None:
        """First-success should return all results if all fail."""
        agent_cards = [create_agent_card(f"agent-{i}") for i in range(3)]

        # Mock send_task - all agents fail
        async def mock_send_task(agent_card, request):
            raise Exception("All agents failed")

        mock_client.send_task = mock_send_task

        results = await orchestration_manager.delegate_to_agents(
            thread_id="thread-1",
            tenant_id="tenant-1",
            user_id="user-1",
            message="Test message",
            target_agent_cards=agent_cards,
            strategy=DelegationStrategy.FIRST_SUCCESS,
        )

        # Should return all failed results
        assert len(results) == 3
        for result in results:
            assert result.success is False


class TestExecuteAgent:
    """Tests for _execute_agent method."""

    @pytest.mark.asyncio
    async def test_execute_agent_collects_text_from_events(
        self,
        orchestration_manager: OrchestrationManager,
        mock_client: AsyncMock,
        sample_agent_card: AgentCard,
    ) -> None:
        """Execute agent should collect text from message events."""

        async def mock_send_task(agent_card, request):
            # Multiple message events
            yield TaskMessageEvent(
                task_id="task-1",
                timestamp=datetime.now(),
                message_parts=[TextPart(text="Part 1 ")],
            )
            yield TaskMessageEvent(
                task_id="task-1",
                timestamp=datetime.now(),
                message_parts=[TextPart(text="Part 2")],
            )

        mock_client.send_task = mock_send_task

        result = await orchestration_manager._execute_agent(
            sample_agent_card, "tenant-1", "user-1", "Test message", 5000
        )

        assert result.success is True
        assert result.response == "Part 1 Part 2"
        assert result.latency_ms >= 0

    @pytest.mark.asyncio
    async def test_execute_agent_handles_timeout(
        self,
        orchestration_manager: OrchestrationManager,
        mock_client: AsyncMock,
        sample_agent_card: AgentCard,
    ) -> None:
        """Execute agent should handle timeout errors."""

        async def mock_send_task(agent_card, request):
            # Simulate timeout
            await asyncio.sleep(10)
            yield TaskMessageEvent(
                task_id="task-1",
                timestamp=datetime.now(),
                message_parts=[TextPart(text="Late response")],
            )

        mock_client.send_task = mock_send_task

        result = await orchestration_manager._execute_agent(
            sample_agent_card, "tenant-1", "user-1", "Test message", 100
        )

        assert result.success is False
        assert "timed out" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execute_agent_handles_no_response(
        self,
        orchestration_manager: OrchestrationManager,
        mock_client: AsyncMock,
        sample_agent_card: AgentCard,
    ) -> None:
        """Execute agent should handle empty response."""

        async def mock_send_task(agent_card, request):
            # No message events
            if False:
                yield

        mock_client.send_task = mock_send_task

        result = await orchestration_manager._execute_agent(
            sample_agent_card, "tenant-1", "user-1", "Test message", 5000
        )

        assert result.success is False
        assert "No response" in result.error


class TestSynthesizeResponses:
    """Tests for synthesize_responses method."""

    def test_synthesize_empty_results(self, orchestration_manager: OrchestrationManager) -> None:
        """Synthesize should handle empty results list."""
        result = orchestration_manager.synthesize_responses([])
        assert result == "No responses received from sub-agents."

    def test_synthesize_all_failed_results(
        self, orchestration_manager: OrchestrationManager
    ) -> None:
        """Synthesize should handle all failed results."""
        results = [
            SubAgentResult(
                agent_id="agent-1",
                success=False,
                error="Failed",
                latency_ms=100,
            ),
            SubAgentResult(
                agent_id="agent-2",
                success=False,
                error="Failed",
                latency_ms=100,
            ),
        ]

        result = orchestration_manager.synthesize_responses(results)
        assert result == "All sub-agents failed to provide responses."

    def test_synthesize_single_success(self, orchestration_manager: OrchestrationManager) -> None:
        """Synthesize should return single successful response directly."""
        results = [
            SubAgentResult(
                agent_id="agent-1",
                success=True,
                response="Single response",
                latency_ms=100,
            )
        ]

        result = orchestration_manager.synthesize_responses(results)
        assert result == "Single response"

    def test_synthesize_multiple_successes(
        self, orchestration_manager: OrchestrationManager
    ) -> None:
        """Synthesize should concatenate multiple successful responses."""
        results = [
            SubAgentResult(
                agent_id="agent-1",
                success=True,
                response="Response 1",
                latency_ms=100,
            ),
            SubAgentResult(
                agent_id="agent-2",
                success=True,
                response="Response 2",
                latency_ms=100,
            ),
            SubAgentResult(
                agent_id="agent-3",
                success=False,
                error="Failed",
                latency_ms=100,
            ),
        ]

        result = orchestration_manager.synthesize_responses(results)
        assert "From agent-1:\nResponse 1" in result
        assert "From agent-2:\nResponse 2" in result
        assert result.count("\n\n") == 1  # Single separator between two responses

    def test_synthesize_mixed_results_filters_failures(
        self, orchestration_manager: OrchestrationManager
    ) -> None:
        """Synthesize should only include successful responses."""
        results = [
            SubAgentResult(
                agent_id="agent-1",
                success=False,
                error="Failed",
                latency_ms=100,
            ),
            SubAgentResult(
                agent_id="agent-2",
                success=True,
                response="Success",
                latency_ms=100,
            ),
        ]

        result = orchestration_manager.synthesize_responses(results)
        assert result == "Success"
