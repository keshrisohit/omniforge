"""Tests for structured logging in orchestration components.

This module tests that all orchestration components properly emit
structured log entries with appropriate context data.
"""

import asyncio
import logging
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from omniforge.agents.events import TaskMessageEvent
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
from omniforge.conversation.models import Conversation
from omniforge.conversation.sqlite_repository import SQLiteConversationRepository
from omniforge.orchestration.a2a_models import CompletionStatus
from omniforge.orchestration.client import A2AClient
from omniforge.orchestration.handoff import HandoffManager, HandoffState
from omniforge.orchestration.manager import DelegationStrategy, OrchestrationManager
from omniforge.orchestration.stream_router import StreamRouter


class TestOrchestrationManagerLogging:
    """Test structured logging in OrchestrationManager."""

    @pytest.fixture
    def mock_client(self) -> A2AClient:
        """Create a mock A2A client."""
        client = MagicMock(spec=A2AClient)

        async def mock_send_task(*args, **kwargs):
            # Yield a message event
            yield TaskMessageEvent(
                task_id="task-123",
                message_parts=[TextPart(text="test response")],
                timestamp=datetime.utcnow(),
            )

        client.send_task = AsyncMock(side_effect=mock_send_task)
        return client

    @pytest.fixture
    def mock_repo(self) -> SQLiteConversationRepository:
        """Create a mock conversation repository."""
        return MagicMock(spec=SQLiteConversationRepository)

    @pytest.fixture
    def manager(
        self, mock_client: A2AClient, mock_repo: SQLiteConversationRepository
    ) -> OrchestrationManager:
        """Create an OrchestrationManager instance."""
        return OrchestrationManager(mock_client, mock_repo)

    @pytest.fixture
    def agent_cards(self) -> list[AgentCard]:
        """Create test agent cards."""
        return [
            AgentCard(
                protocol_version="1.0",
                identity=AgentIdentity(
                    id="agent-1",
                    name="Agent 1",
                    description="Test agent 1",
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
            ),
            AgentCard(
                protocol_version="1.0",
                identity=AgentIdentity(
                    id="agent-2",
                    name="Agent 2",
                    description="Test agent 2",
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
                service_endpoint="http://localhost:8002",
                security=SecurityConfig(auth_scheme=AuthScheme.BEARER, require_https=True),
            ),
        ]

    @pytest.mark.asyncio
    async def test_delegation_started_logged(
        self, manager: OrchestrationManager, agent_cards: list[AgentCard], caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that delegation start is logged with context."""
        caplog.set_level(logging.INFO, logger="omniforge.orchestration")

        await manager.delegate_to_agents(
            thread_id="thread-123",
            tenant_id="tenant-1",
            user_id="user-1",
            message="test message",
            target_agent_cards=agent_cards,
            strategy=DelegationStrategy.PARALLEL,
        )

        # Verify delegation started log
        started_logs = [r for r in caplog.records if "Delegation started" in r.message]
        assert len(started_logs) == 1

        log_record = started_logs[0]
        assert log_record.levelname == "INFO"
        assert log_record.thread_id == "thread-123"
        assert log_record.tenant_id == "tenant-1"
        assert log_record.strategy == "parallel"
        assert log_record.target_agents == ["agent-1", "agent-2"]
        assert log_record.total_agents == 2

    @pytest.mark.asyncio
    async def test_delegation_completed_logged(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that delegation completion is logged with context."""
        caplog.set_level(logging.INFO, logger="omniforge.orchestration")

        # Create mock client with proper async generator
        mock_client = MagicMock(spec=A2AClient)

        async def success_task(*args, **kwargs):
            yield TaskMessageEvent(
                task_id="task-123",
                message_parts=[TextPart(text="test response")],
                timestamp=datetime.utcnow(),
            )

        mock_client.send_task = MagicMock(side_effect=success_task)
        manager = OrchestrationManager(mock_client, MagicMock())

        agent_cards = [
            AgentCard(
                protocol_version="1.0",
                identity=AgentIdentity(
                    id="agent-1",
                    name="Agent 1",
                    description="Test agent 1",
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
            ),
            AgentCard(
                protocol_version="1.0",
                identity=AgentIdentity(
                    id="agent-2",
                    name="Agent 2",
                    description="Test agent 2",
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
                service_endpoint="http://localhost:8002",
                security=SecurityConfig(auth_scheme=AuthScheme.BEARER, require_https=True),
            ),
        ]

        await manager.delegate_to_agents(
            thread_id="thread-123",
            tenant_id="tenant-1",
            user_id="user-1",
            message="test message",
            target_agent_cards=agent_cards,
            strategy=DelegationStrategy.PARALLEL,
        )

        # Verify delegation completed log
        completed_logs = [r for r in caplog.records if "Delegation completed" in r.message]
        assert len(completed_logs) == 1

        log_record = completed_logs[0]
        assert log_record.levelname == "INFO"
        assert log_record.thread_id == "thread-123"
        assert log_record.tenant_id == "tenant-1"
        assert log_record.total_agents == 2
        assert log_record.successful_count == 2
        assert hasattr(log_record, "total_latency_ms")
        assert log_record.total_latency_ms >= 0

    @pytest.mark.asyncio
    async def test_agent_results_logged_at_debug(
        self, manager: OrchestrationManager, agent_cards: list[AgentCard], caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that per-agent results are logged at DEBUG level."""
        caplog.set_level(logging.DEBUG, logger="omniforge.orchestration")

        await manager.delegate_to_agents(
            thread_id="thread-123",
            tenant_id="tenant-1",
            user_id="user-1",
            message="test message",
            target_agent_cards=agent_cards,
            strategy=DelegationStrategy.PARALLEL,
        )

        # Verify per-agent result logs
        result_logs = [r for r in caplog.records if "Agent result" in r.message]
        assert len(result_logs) == 2

        for log_record in result_logs:
            assert log_record.levelname == "DEBUG"
            assert log_record.thread_id == "thread-123"
            assert hasattr(log_record, "agent_id")
            assert hasattr(log_record, "success")
            assert hasattr(log_record, "latency_ms")

    @pytest.mark.asyncio
    async def test_agent_failure_logged_as_warning(
        self, manager: OrchestrationManager, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that individual agent failures are logged as warnings."""
        caplog.set_level(logging.WARNING, logger="omniforge.orchestration")

        # Create mock client that raises an error
        mock_client = MagicMock(spec=A2AClient)

        async def error_task(*args, **kwargs):
            raise Exception("Test error")
            yield  # Make it a generator (unreachable but makes it async generator)

        mock_client.send_task = MagicMock(side_effect=error_task)

        manager = OrchestrationManager(mock_client, MagicMock())

        agent_cards = [
            AgentCard(
                protocol_version="1.0",
                identity=AgentIdentity(
                    id="agent-1",
                    name="Agent 1",
                    description="Test agent",
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
            ),
        ]

        await manager.delegate_to_agents(
            thread_id="thread-123",
            tenant_id="tenant-1",
            user_id="user-1",
            message="test message",
            target_agent_cards=agent_cards,
            strategy=DelegationStrategy.PARALLEL,
        )

        # Verify failure log
        failure_logs = [r for r in caplog.records if "Agent execution failed" in r.message]
        assert len(failure_logs) == 1

        log_record = failure_logs[0]
        assert log_record.levelname == "WARNING"
        assert log_record.agent_id == "agent-1"
        assert log_record.tenant_id == "tenant-1"
        assert "Test error" in log_record.error

    @pytest.mark.asyncio
    async def test_agent_timeout_logged_as_warning(
        self, manager: OrchestrationManager, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that agent timeout is logged as warning."""
        caplog.set_level(logging.WARNING, logger="omniforge.orchestration")

        # Create mock client that times out
        mock_client = MagicMock(spec=A2AClient)

        async def slow_task(*args, **kwargs):
            await asyncio.sleep(10)
            yield TaskMessageEvent(
                task_id="task-123",
                message_parts=[TextPart(text="late response")],
                timestamp=datetime.utcnow(),
            )

        mock_client.send_task = MagicMock(side_effect=slow_task)
        manager = OrchestrationManager(mock_client, MagicMock())

        agent_cards = [
            AgentCard(
                protocol_version="1.0",
                identity=AgentIdentity(
                    id="agent-1",
                    name="Agent 1",
                    description="Test agent",
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
            ),
        ]

        await manager.delegate_to_agents(
            thread_id="thread-123",
            tenant_id="tenant-1",
            user_id="user-1",
            message="test message",
            target_agent_cards=agent_cards,
            strategy=DelegationStrategy.PARALLEL,
            timeout_ms=100,
        )

        # Verify timeout log
        timeout_logs = [r for r in caplog.records if "Agent execution timed out" in r.message]
        assert len(timeout_logs) == 1

        log_record = timeout_logs[0]
        assert log_record.levelname == "WARNING"
        assert log_record.agent_id == "agent-1"
        assert log_record.tenant_id == "tenant-1"
        assert log_record.timeout_ms == 100


class TestHandoffManagerLogging:
    """Test structured logging in HandoffManager."""

    @pytest.fixture
    def mock_client(self) -> A2AClient:
        """Create a mock A2A client."""
        return MagicMock(spec=A2AClient)

    @pytest.fixture
    def mock_repo(self) -> SQLiteConversationRepository:
        """Create a mock conversation repository."""
        repo = MagicMock(spec=SQLiteConversationRepository)
        repo.get_conversation = AsyncMock(
            return_value=Conversation(
                id=uuid4(),
                tenant_id="tenant-1",
                user_id="user-1",
                agent_id="agent-1",
                state="active",
                state_metadata={},
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        )
        repo.update_state = AsyncMock()
        return repo

    @pytest.fixture
    def handoff_manager(
        self, mock_client: A2AClient, mock_repo: SQLiteConversationRepository
    ) -> HandoffManager:
        """Create a HandoffManager instance."""
        return HandoffManager(mock_client, mock_repo)

    @pytest.fixture
    def target_agent_card(self) -> AgentCard:
        """Create a test agent card."""
        return AgentCard(
            protocol_version="1.0",
            identity=AgentIdentity(
                id="target-agent",
                name="Target Agent",
                description="Test target agent",
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
            service_endpoint="http://localhost:8003",
            security=SecurityConfig(auth_scheme=AuthScheme.BEARER, require_https=True),
        )

    @pytest.mark.asyncio
    async def test_handoff_initiation_logged(
        self,
        handoff_manager: HandoffManager,
        target_agent_card: AgentCard,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test that handoff initiation is logged with context."""
        caplog.set_level(logging.INFO, logger="omniforge.orchestration")

        thread_id = str(uuid4())
        await handoff_manager.initiate_handoff(
            thread_id=thread_id,
            tenant_id="tenant-1",
            user_id="user-1",
            source_agent_id="source-agent",
            target_agent_card=target_agent_card,
            context_summary="Test context",
            handoff_reason="Test reason",
        )

        # Verify handoff initiated log
        initiated_logs = [r for r in caplog.records if "Handoff initiated" in r.message]
        assert len(initiated_logs) == 1

        log_record = initiated_logs[0]
        assert log_record.levelname == "INFO"
        assert log_record.thread_id == thread_id
        assert log_record.tenant_id == "tenant-1"
        assert log_record.source_agent == "source-agent"
        assert log_record.target_agent == "target-agent"
        assert log_record.reason == "Test reason"
        assert hasattr(log_record, "handoff_id")

    @pytest.mark.asyncio
    async def test_handoff_completion_logged(
        self,
        handoff_manager: HandoffManager,
        target_agent_card: AgentCard,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test that handoff completion is logged with context."""
        caplog.set_level(logging.INFO, logger="omniforge.orchestration")

        thread_id = str(uuid4())
        await handoff_manager.initiate_handoff(
            thread_id=thread_id,
            tenant_id="tenant-1",
            user_id="user-1",
            source_agent_id="source-agent",
            target_agent_card=target_agent_card,
            context_summary="Test context",
            handoff_reason="Test reason",
        )

        # Clear logs to focus on completion
        caplog.clear()

        await handoff_manager.complete_handoff(
            thread_id=thread_id,
            tenant_id="tenant-1",
            completion_status=CompletionStatus.COMPLETED,
            result_summary="Task completed successfully",
        )

        # Verify handoff completed log
        completed_logs = [r for r in caplog.records if "Handoff completed" in r.message]
        assert len(completed_logs) == 1

        log_record = completed_logs[0]
        assert log_record.levelname == "INFO"
        assert log_record.thread_id == thread_id
        assert log_record.tenant_id == "tenant-1"
        assert log_record.completion_status == "completed"
        assert hasattr(log_record, "duration_seconds")
        assert log_record.duration_seconds >= 0

    @pytest.mark.asyncio
    async def test_handoff_cancellation_logged(
        self,
        handoff_manager: HandoffManager,
        target_agent_card: AgentCard,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test that handoff cancellation is logged with context."""
        caplog.set_level(logging.INFO, logger="omniforge.orchestration")

        thread_id = str(uuid4())
        await handoff_manager.initiate_handoff(
            thread_id=thread_id,
            tenant_id="tenant-1",
            user_id="user-1",
            source_agent_id="source-agent",
            target_agent_card=target_agent_card,
            context_summary="Test context",
            handoff_reason="Test reason",
        )

        # Clear logs to focus on cancellation
        caplog.clear()

        await handoff_manager.cancel_handoff(thread_id=thread_id, tenant_id="tenant-1")

        # Verify handoff cancelled log
        cancelled_logs = [r for r in caplog.records if "Handoff cancelled" in r.message]
        assert len(cancelled_logs) == 1

        log_record = cancelled_logs[0]
        assert log_record.levelname == "INFO"
        assert log_record.thread_id == thread_id
        assert log_record.tenant_id == "tenant-1"

    @pytest.mark.asyncio
    async def test_handoff_error_logged_as_warning(
        self,
        handoff_manager: HandoffManager,
        target_agent_card: AgentCard,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test that handoff errors are logged as warnings."""
        caplog.set_level(logging.WARNING, logger="omniforge.orchestration")

        thread_id = str(uuid4())
        await handoff_manager.initiate_handoff(
            thread_id=thread_id,
            tenant_id="tenant-1",
            user_id="user-1",
            source_agent_id="source-agent",
            target_agent_card=target_agent_card,
            context_summary="Test context",
            handoff_reason="Test reason",
        )

        # Clear logs to focus on error
        caplog.clear()

        await handoff_manager.complete_handoff(
            thread_id=thread_id,
            tenant_id="tenant-1",
            completion_status=CompletionStatus.ERROR,
            result_summary="Something went wrong",
        )

        # Verify handoff error log
        error_logs = [r for r in caplog.records if "Handoff error" in r.message]
        assert len(error_logs) == 1

        log_record = error_logs[0]
        assert log_record.levelname == "WARNING"
        assert log_record.thread_id == thread_id
        assert log_record.tenant_id == "tenant-1"
        assert log_record.error_summary == "Something went wrong"


class TestStreamRouterLogging:
    """Test structured logging in StreamRouter."""

    @pytest.fixture
    def mock_handoff_manager(self) -> HandoffManager:
        """Create a mock handoff manager."""
        return MagicMock(spec=HandoffManager)

    @pytest.fixture
    def mock_orchestration_manager(self) -> OrchestrationManager:
        """Create a mock orchestration manager."""
        return MagicMock(spec=OrchestrationManager)

    @pytest.fixture
    def stream_router(
        self,
        mock_handoff_manager: HandoffManager,
        mock_orchestration_manager: OrchestrationManager,
    ) -> StreamRouter:
        """Create a StreamRouter instance."""
        return StreamRouter(mock_handoff_manager, mock_orchestration_manager)

    @pytest.mark.asyncio
    async def test_handoff_routing_logged(
        self,
        stream_router: StreamRouter,
        mock_handoff_manager: HandoffManager,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test that handoff routing is logged at DEBUG level."""
        caplog.set_level(logging.DEBUG, logger="omniforge.orchestration")

        # Mock active handoff
        mock_session = MagicMock()
        mock_session.target_agent_id = "target-agent"
        mock_handoff_manager.get_active_handoff = AsyncMock(return_value=mock_session)

        # Route message
        async for _ in stream_router.route_message(
            thread_id="thread-123",
            tenant_id="tenant-1",
            user_id="user-1",
            message="test message",
        ):
            pass

        # Verify routing log
        routing_logs = [r for r in caplog.records if "Message routed to handoff" in r.message]
        assert len(routing_logs) == 1

        log_record = routing_logs[0]
        assert log_record.levelname == "DEBUG"
        assert log_record.thread_id == "thread-123"
        assert log_record.tenant_id == "tenant-1"
        assert log_record.route_type == "handoff"
        assert log_record.target_agent == "target-agent"

    @pytest.mark.asyncio
    async def test_normal_routing_logged(
        self,
        stream_router: StreamRouter,
        mock_handoff_manager: HandoffManager,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test that normal routing is logged at DEBUG level."""
        caplog.set_level(logging.DEBUG, logger="omniforge.orchestration")

        # Mock no active handoff
        mock_handoff_manager.get_active_handoff = AsyncMock(return_value=None)

        # Route message
        async for _ in stream_router.route_message(
            thread_id="thread-123",
            tenant_id="tenant-1",
            user_id="user-1",
            message="test message",
        ):
            pass

        # Verify routing log
        routing_logs = [r for r in caplog.records if "Message routed to orchestrator" in r.message]
        assert len(routing_logs) == 1

        log_record = routing_logs[0]
        assert log_record.levelname == "DEBUG"
        assert log_record.thread_id == "thread-123"
        assert log_record.tenant_id == "tenant-1"
        assert log_record.route_type == "normal"
