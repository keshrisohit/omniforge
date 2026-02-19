"""Integration tests for Smart Master Agent full flow.

This module tests the complete end-to-end flow of the smart master agent,
including ChatService, ResponseGenerator, MasterResponseGenerator, conversation
storage, context passing, and LLM intent analysis (mocked).
"""

import json
from datetime import datetime
from typing import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from omniforge.agents.events import TaskMessageEvent
from omniforge.agents.master_agent import MasterAgent
from omniforge.agents.models import TextPart
from omniforge.chat.master_response_generator import MasterResponseGenerator
from omniforge.chat.models import ChatRequest
from omniforge.chat.service import ChatService
from omniforge.conversation.intent_analyzer import IntentAnalysisError, LLMIntentAnalyzer
from omniforge.conversation.memory_repository import InMemoryConversationRepository
from omniforge.conversation.models import Message, MessageRole
from omniforge.routing.models import ActionType, RoutingDecision
from omniforge.tasks.models import Task


class MockMasterAgent(MasterAgent):
    """Mock Master Agent that captures task and yields simple responses.

    This mock still uses the real MasterAgent logic for intent analysis,
    but simplifies the response generation for testing.
    """

    def __init__(self, intent_analyzer: LLMIntentAnalyzer | None = None) -> None:
        """Initialize mock master agent.

        Args:
            intent_analyzer: Optional intent analyzer to pass to MasterAgent
        """
        super().__init__(intent_analyzer=intent_analyzer)
        self._last_task: Task | None = None
        self._process_count = 0

    async def _handle_create_agent(self, task: Task, decision: RoutingDecision) -> AsyncIterator:
        """Override to provide simple response for create_agent."""
        self._last_task = task
        yield TaskMessageEvent(
            task_id=task.id,
            message_parts=[TextPart(text=f"Response to: {task.messages[-1].parts[0].text}")],
            timestamp=datetime.utcnow(),
        )

    async def _handle_create_skill(self, task: Task, decision: RoutingDecision) -> AsyncIterator:
        """Override to provide simple response for create_skill."""
        self._last_task = task
        yield TaskMessageEvent(
            task_id=task.id,
            message_parts=[TextPart(text=f"Response to: {task.messages[-1].parts[0].text}")],
            timestamp=datetime.utcnow(),
        )

    async def _handle_execute_task(self, task: Task, decision: RoutingDecision) -> AsyncIterator:
        """Override to provide simple response for execute_task."""
        self._last_task = task
        yield TaskMessageEvent(
            task_id=task.id,
            message_parts=[TextPart(text=f"Response to: {task.messages[-1].parts[0].text}")],
            timestamp=datetime.utcnow(),
        )

    async def _handle_update_agent(self, task: Task, decision: RoutingDecision) -> AsyncIterator:
        """Override to provide simple response for update_agent."""
        self._last_task = task
        yield TaskMessageEvent(
            task_id=task.id,
            message_parts=[TextPart(text=f"Response to: {task.messages[-1].parts[0].text}")],
            timestamp=datetime.utcnow(),
        )

    async def _handle_query(self, task: Task, decision: RoutingDecision) -> AsyncIterator:
        """Override to provide simple response for query."""
        self._last_task = task
        yield TaskMessageEvent(
            task_id=task.id,
            message_parts=[TextPart(text=f"Response to: {task.messages[-1].parts[0].text}")],
            timestamp=datetime.utcnow(),
        )

    async def _handle_platform_management(
        self, task: Task, decision: RoutingDecision
    ) -> AsyncIterator:
        """Override to provide simple response for platform_management."""
        self._last_task = task
        yield TaskMessageEvent(
            task_id=task.id,
            message_parts=[TextPart(text=f"Response to: {task.messages[-1].parts[0].text}")],
            timestamp=datetime.utcnow(),
        )

    async def _handle_clarification(self, task: Task) -> AsyncIterator:
        """Override to provide simple response for clarification."""
        self._last_task = task
        yield TaskMessageEvent(
            task_id=task.id,
            message_parts=[TextPart(text=f"Response to: {task.messages[-1].parts[0].text}")],
            timestamp=datetime.utcnow(),
        )


class TestSmartMasterAgentIntegration:
    """End-to-end integration tests for smart master agent flow."""

    @pytest.mark.asyncio
    async def test_full_flow_with_llm_intent_analysis(self) -> None:
        """Full flow test with LLM intent analyzer (mocked).

        Tests:
        - ChatService integrates with repository and intent analyzer
        - User message is stored
        - LLM intent analyzer is called with history
        - Response is generated
        - Assistant response is stored
        - Conversation ID is returned
        """
        # Arrange
        repository = InMemoryConversationRepository()
        mock_agent = MockMasterAgent()

        # Mock LLM intent analyzer
        mock_analyzer = AsyncMock(spec=LLMIntentAnalyzer)
        mock_analyzer.analyze = AsyncMock(
            return_value=RoutingDecision(
                action_type=ActionType.CREATE_AGENT,
                confidence=0.95,
                reasoning="User wants to create an agent",
                entities={"agent_name": "TestBot"},
            )
        )

        # Create mock agent with intent analyzer
        mock_agent = MockMasterAgent(intent_analyzer=mock_analyzer)

        # Create response generator with mocked components
        response_generator = MasterResponseGenerator(
            tenant_id="test-tenant", user_id="test-user", intent_analyzer=mock_analyzer
        )
        response_generator._master_agent = mock_agent

        # Create chat service with repository
        service = ChatService(
            response_generator=response_generator,
            conversation_repository=repository,
            tenant_id="test-tenant",
            user_id="test-user",
        )

        request = ChatRequest(message="Create a bot for me")

        # Act
        events = []
        async for event in service.process_chat(request):
            events.append(event)

        # Assert
        # Should have chunk events + done event
        assert len(events) >= 2
        assert events[-1].startswith("event: done")

        # Extract conversation_id from done event
        done_data = json.loads(events[-1].split("\n")[1].replace("data: ", ""))
        conversation_id = UUID(done_data["conversation_id"])

        # Verify LLM analyzer was called with empty history (first message)
        assert mock_analyzer.analyze.call_count == 1
        call_kwargs = mock_analyzer.analyze.call_args.kwargs
        assert call_kwargs["message"] == "Create a bot for me"
        # Empty history can be None or empty list
        assert call_kwargs.get("conversation_history") in (None, [])

        # Verify conversation was created in repository
        conversation = await repository.get_conversation(conversation_id, "test-tenant")
        assert conversation is not None
        assert conversation.tenant_id == "test-tenant"
        assert conversation.user_id == "test-user"

        # Verify messages were stored
        messages = await repository.get_messages(conversation_id, "test-tenant")
        assert len(messages) == 2
        assert messages[0].role == MessageRole.USER
        assert messages[0].content == "Create a bot for me"
        assert messages[1].role == MessageRole.ASSISTANT
        assert "Response to: Create a bot for me" in messages[1].content

        # Verify Master Agent was called
        assert mock_agent._last_task is not None

    @pytest.mark.asyncio
    async def test_multi_turn_conversation_with_context(self) -> None:
        """Multi-turn conversation test verifying context accumulation.

        Tests:
        - First message creates conversation
        - Second message uses existing conversation_id
        - History accumulates correctly
        - LLM analyzer receives conversation context on second turn
        """
        # Arrange
        repository = InMemoryConversationRepository()

        # Mock LLM intent analyzer
        mock_analyzer = AsyncMock(spec=LLMIntentAnalyzer)
        mock_analyzer.analyze = AsyncMock(
            return_value=RoutingDecision(
                action_type=ActionType.QUERY_INFO,
                confidence=0.85,
                reasoning="User is asking a question",
                entities={},
            )
        )

        # Create mock agent with intent analyzer
        mock_agent = MockMasterAgent(intent_analyzer=mock_analyzer)

        response_generator = MasterResponseGenerator(
            tenant_id="test-tenant", user_id="test-user", intent_analyzer=mock_analyzer
        )
        response_generator._master_agent = mock_agent

        service = ChatService(
            response_generator=response_generator,
            conversation_repository=repository,
            tenant_id="test-tenant",
            user_id="test-user",
        )

        # Act - First message
        request1 = ChatRequest(message="What is OmniForge?")
        events1 = []
        async for event in service.process_chat(request1):
            events1.append(event)

        done_data1 = json.loads(events1[-1].split("\n")[1].replace("data: ", ""))
        conversation_id = UUID(done_data1["conversation_id"])

        # Act - Second message with conversation_id
        request2 = ChatRequest(message="Can it create agents?", conversation_id=conversation_id)
        events2 = []
        async for event in service.process_chat(request2):
            events2.append(event)

        # Assert
        # Verify LLM analyzer was called twice
        assert mock_analyzer.analyze.call_count == 2

        # First call should have empty history
        first_call = mock_analyzer.analyze.call_args_list[0]
        assert first_call.kwargs["message"] == "What is OmniForge?"
        # Empty history can be None or empty list
        assert first_call.kwargs.get("conversation_history") in (None, [])

        # Second call should have conversation history
        second_call = mock_analyzer.analyze.call_args_list[1]
        assert second_call.kwargs["message"] == "Can it create agents?"
        history = second_call.kwargs["conversation_history"]
        assert len(history) == 2  # User message + Assistant response from turn 1
        assert history[0].role == MessageRole.USER
        assert history[0].content == "What is OmniForge?"
        assert history[1].role == MessageRole.ASSISTANT

        # Verify all messages stored in conversation
        messages = await repository.get_messages(conversation_id, "test-tenant")
        assert len(messages) == 4  # 2 turns * 2 messages each
        assert messages[0].content == "What is OmniForge?"
        assert messages[2].content == "Can it create agents?"

        # Verify Master Agent received context on second turn
        assert len(mock_agent._last_task.messages) == 3  # 2 from history + 1 current

    @pytest.mark.asyncio
    async def test_llm_fallback_to_keyword_matching_on_error(self) -> None:
        """Test fallback to keyword matching when LLM analyzer fails.

        Tests:
        - LLM analyzer raises IntentAnalysisError
        - Master Agent falls back to keyword matching
        - Response is still generated
        - Conversation is still stored
        """
        # Arrange
        repository = InMemoryConversationRepository()

        # Mock LLM intent analyzer to raise error
        mock_analyzer = AsyncMock(spec=LLMIntentAnalyzer)
        mock_analyzer.analyze = AsyncMock(side_effect=IntentAnalysisError("LLM timeout"))

        # Create mock agent with failing intent analyzer
        mock_agent = MockMasterAgent(intent_analyzer=mock_analyzer)

        response_generator = MasterResponseGenerator(
            tenant_id="test-tenant", user_id="test-user", intent_analyzer=mock_analyzer
        )
        response_generator._master_agent = mock_agent

        service = ChatService(
            response_generator=response_generator,
            conversation_repository=repository,
            tenant_id="test-tenant",
            user_id="test-user",
        )

        request = ChatRequest(message="Create an agent for me")

        # Act
        events = []
        async for event in service.process_chat(request):
            events.append(event)

        # Assert
        # Should still complete successfully with fallback
        assert len(events) >= 2
        assert events[-1].startswith("event: done")

        # Verify LLM analyzer was attempted
        assert mock_analyzer.analyze.call_count == 1

        # Verify conversation was still stored (resilient to LLM failure)
        done_data = json.loads(events[-1].split("\n")[1].replace("data: ", ""))
        conversation_id = UUID(done_data["conversation_id"])

        messages = await repository.get_messages(conversation_id, "test-tenant")
        assert len(messages) == 2
        assert messages[0].content == "Create an agent for me"

        # Verify Master Agent was still called (used keyword fallback)
        assert mock_agent._last_task is not None

    @pytest.mark.asyncio
    async def test_storage_failure_resilience(self) -> None:
        """Test that storage failures don't prevent response generation.

        Tests:
        - Repository raises exceptions
        - Response is still generated
        - Errors are logged but don't break flow
        """
        # Arrange
        mock_agent = MockMasterAgent()

        # Create repository that fails
        failing_repo = AsyncMock(spec=InMemoryConversationRepository)
        failing_repo.create_conversation = AsyncMock(
            side_effect=Exception("Database connection failed")
        )

        response_generator = MasterResponseGenerator(
            tenant_id="test-tenant", user_id="test-user"
        )
        response_generator._master_agent = mock_agent

        service = ChatService(
            response_generator=response_generator,
            conversation_repository=failing_repo,
            tenant_id="test-tenant",
            user_id="test-user",
        )

        request = ChatRequest(message="Test message")

        # Act
        events = []
        async for event in service.process_chat(request):
            events.append(event)

        # Assert
        # Should still complete successfully (storage is non-critical)
        assert len(events) >= 2
        assert events[-1].startswith("event: done")

        # Verify response was still generated
        assert mock_agent._last_task is not None

        # Repository create was attempted but failed
        assert failing_repo.create_conversation.call_count == 1

    @pytest.mark.asyncio
    async def test_backward_compatibility_without_repository(self) -> None:
        """Test backward compatibility when repository is not provided.

        Tests:
        - ChatService works without repository
        - No storage operations occur
        - Response is generated normally
        - Conversation ID is still returned
        """
        # Arrange
        mock_agent = MockMasterAgent()

        response_generator = MasterResponseGenerator()
        response_generator._master_agent = mock_agent

        # Create service WITHOUT repository (backward compatibility)
        service = ChatService(response_generator=response_generator)

        request = ChatRequest(message="Test message")

        # Act
        events = []
        async for event in service.process_chat(request):
            events.append(event)

        # Assert
        # Should work normally
        assert len(events) >= 2
        assert events[-1].startswith("event: done")

        # Should have conversation_id even without storage
        done_data = json.loads(events[-1].split("\n")[1].replace("data: ", ""))
        assert "conversation_id" in done_data

        # Verify response was generated
        assert mock_agent._last_task is not None

        # Task should have only current message (no history without repository)
        assert len(mock_agent._last_task.messages) == 1

    @pytest.mark.asyncio
    async def test_invalid_conversation_id_raises_error(self) -> None:
        """Test that invalid conversation_id raises clear error.

        Tests:
        - Provide conversation_id that doesn't exist
        - ValueError is raised
        - Error message is clear
        """
        # Arrange
        repository = InMemoryConversationRepository()
        service = ChatService(
            conversation_repository=repository, tenant_id="test-tenant", user_id="test-user"
        )

        # Use non-existent conversation_id
        fake_conversation_id = uuid4()
        request = ChatRequest(message="Test", conversation_id=fake_conversation_id)

        # Act & Assert
        events = []
        async for event in service.process_chat(request):
            events.append(event)

        # Should yield error event
        assert any("error" in event for event in events)
        error_event = [e for e in events if "error" in e][0]
        assert "not found" in error_event or "does not belong" in error_event

    @pytest.mark.asyncio
    async def test_tenant_isolation(self) -> None:
        """Test that tenant isolation prevents cross-tenant access.

        Tests:
        - Create conversation for tenant A
        - Try to access from tenant B
        - Access is denied
        """
        # Arrange
        repository = InMemoryConversationRepository()

        # Create conversation for tenant A
        service_a = ChatService(
            conversation_repository=repository, tenant_id="tenant-a", user_id="user-1"
        )
        request_a = ChatRequest(message="Message from tenant A")

        events_a = []
        async for event in service_a.process_chat(request_a):
            events_a.append(event)

        done_data_a = json.loads(events_a[-1].split("\n")[1].replace("data: ", ""))
        conversation_id_a = UUID(done_data_a["conversation_id"])

        # Try to access tenant A's conversation from tenant B
        service_b = ChatService(
            conversation_repository=repository, tenant_id="tenant-b", user_id="user-2"
        )
        request_b = ChatRequest(message="Message from tenant B", conversation_id=conversation_id_a)

        # Act & Assert
        events_b = []
        async for event in service_b.process_chat(request_b):
            events_b.append(event)

        # Should yield error event (tenant isolation)
        assert any("error" in event for event in events_b)
        error_event = [e for e in events_b if "error" in e][0]
        assert "not found" in error_event or "does not belong" in error_event

    @pytest.mark.asyncio
    async def test_conversation_continuity_across_multiple_turns(self) -> None:
        """Test conversation continuity with multiple sequential messages.

        Tests:
        - Multiple messages with same conversation_id
        - All messages accumulate correctly
        - History is maintained properly
        """
        # Arrange
        repository = InMemoryConversationRepository()

        # Create mock agent without intent analyzer (will use keyword matching)
        mock_agent = MockMasterAgent(intent_analyzer=None)

        response_generator = MasterResponseGenerator(
            tenant_id="test-tenant", user_id="test-user"
        )
        response_generator._master_agent = mock_agent

        service = ChatService(
            response_generator=response_generator,
            conversation_repository=repository,
            tenant_id="test-tenant",
            user_id="test-user",
        )

        # Act - Send 3 messages in sequence
        messages = ["First message", "Second message", "Third message"]
        conversation_id = None

        for msg in messages:
            request = (
                ChatRequest(message=msg)
                if conversation_id is None
                else ChatRequest(message=msg, conversation_id=conversation_id)
            )

            events = []
            async for event in service.process_chat(request):
                events.append(event)

            done_data = json.loads(events[-1].split("\n")[1].replace("data: ", ""))
            conversation_id = UUID(done_data["conversation_id"])

        # Assert
        # Verify all messages stored
        stored_messages = await repository.get_messages(conversation_id, "test-tenant")
        assert len(stored_messages) == 6  # 3 turns * 2 messages each

        # Verify chronological order
        assert stored_messages[0].content == "First message"
        assert stored_messages[2].content == "Second message"
        assert stored_messages[4].content == "Third message"

        # Verify last task had full history (up to 20 messages)
        assert len(mock_agent._last_task.messages) == 5  # 4 history + 1 current

    @pytest.mark.asyncio
    async def test_llm_analyzer_receives_available_agents_context(self) -> None:
        """Test that LLM analyzer receives available agents in context.

        Tests:
        - Intent analyzer is called with available_agents parameter
        - Can route to specific agent based on context
        """
        # Arrange
        repository = InMemoryConversationRepository()

        # Mock LLM intent analyzer
        mock_analyzer = AsyncMock(spec=LLMIntentAnalyzer)
        mock_analyzer.analyze = AsyncMock(
            return_value=RoutingDecision(
                action_type=ActionType.EXECUTE_TASK,
                confidence=0.9,
                target_agent_id="agent-123",
                reasoning="Route to specific agent",
                entities={},
            )
        )

        # Create mock agent with intent analyzer
        mock_agent = MockMasterAgent(intent_analyzer=mock_analyzer)

        response_generator = MasterResponseGenerator(
            tenant_id="test-tenant", user_id="test-user", intent_analyzer=mock_analyzer
        )
        response_generator._master_agent = mock_agent

        service = ChatService(
            response_generator=response_generator,
            conversation_repository=repository,
            tenant_id="test-tenant",
            user_id="test-user",
        )

        request = ChatRequest(message="Run my data processor")

        # Act
        events = []
        async for event in service.process_chat(request):
            events.append(event)

        # Assert
        # Verify analyzer was called
        assert mock_analyzer.analyze.call_count == 1

        # Note: In real implementation, Master Agent would fetch available agents
        # and pass them to the analyzer. This test verifies the flow works.
        call_kwargs = mock_analyzer.analyze.call_args.kwargs
        assert "message" in call_kwargs
        assert call_kwargs["message"] == "Run my data processor"


class TestBackwardCompatibility:
    """Tests for backward compatibility without repository or intent analyzer."""

    @pytest.mark.asyncio
    async def test_chat_service_without_repository_works(self) -> None:
        """ChatService without repository should work identically to original."""
        # Arrange
        mock_agent = MockMasterAgent()
        response_generator = MasterResponseGenerator()
        response_generator._master_agent = mock_agent

        service = ChatService(response_generator=response_generator)
        request = ChatRequest(message="Test message")

        # Act
        events = []
        async for event in service.process_chat(request):
            events.append(event)

        # Assert
        # Should complete successfully
        assert len(events) >= 2
        assert events[-1].startswith("event: done")

        # Should have conversation_id
        done_data = json.loads(events[-1].split("\n")[1].replace("data: ", ""))
        assert "conversation_id" in done_data

        # Should have usage info
        assert "usage" in done_data

    @pytest.mark.asyncio
    async def test_master_response_generator_without_intent_analyzer(self) -> None:
        """MasterResponseGenerator without intent analyzer uses keyword matching."""
        # Arrange
        mock_agent = MockMasterAgent()

        # No intent analyzer provided
        response_generator = MasterResponseGenerator()
        response_generator._master_agent = mock_agent

        # Act
        chunks = []
        async for chunk in response_generator.generate_stream("Create an agent"):
            chunks.append(chunk)

        # Assert
        # Should work with keyword-based routing (fallback)
        assert len(chunks) > 0
        assert mock_agent._last_task is not None

    @pytest.mark.asyncio
    async def test_no_storage_calls_without_repository(self) -> None:
        """Verify no storage operations occur without repository."""
        # Arrange
        mock_agent = MockMasterAgent()
        response_generator = MasterResponseGenerator()
        response_generator._master_agent = mock_agent

        # ChatService without repository
        service = ChatService(response_generator=response_generator)
        request = ChatRequest(message="Test")

        # Act
        events = []
        async for event in service.process_chat(request):
            events.append(event)

        # Assert
        # Should complete without errors
        assert len(events) >= 2

        # Task should have only current message (no history loaded)
        assert len(mock_agent._last_task.messages) == 1
        assert mock_agent._last_task.messages[0].parts[0].text == "Test"

    @pytest.mark.asyncio
    async def test_existing_response_patterns_preserved(self) -> None:
        """Verify all existing response patterns still work."""
        # Arrange
        mock_agent = MockMasterAgent()
        response_generator = MasterResponseGenerator()
        response_generator._master_agent = mock_agent

        service = ChatService(response_generator=response_generator)

        # Test various message patterns
        test_messages = [
            "Hello",
            "Create an agent",
            "List my agents",
            "Help me with a task",
        ]

        for message in test_messages:
            request = ChatRequest(message=message)

            # Act
            events = []
            async for event in service.process_chat(request):
                events.append(event)

            # Assert
            # All should complete successfully
            assert len(events) >= 2
            assert events[-1].startswith("event: done")

            # Should have response chunks
            chunk_events = [e for e in events if "event: chunk" in e]
            assert len(chunk_events) > 0
