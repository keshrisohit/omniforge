"""Performance tests for conversation response latency.

Tests that conversation responses meet the < 3 second latency requirement.
"""

import time
import uuid
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from omniforge.builder.conversation import ConversationManager, ConversationState
from omniforge.builder.skill_generator import SkillMdGenerator


@pytest.fixture
def conversation_manager() -> ConversationManager:
    """Create a conversation manager for testing.

    Returns:
        ConversationManager instance
    """
    return ConversationManager()


@pytest.fixture
def skill_generator() -> SkillMdGenerator:
    """Create a skill generator for testing.

    Returns:
        SkillMdGenerator instance
    """
    return SkillMdGenerator()


class TestResponseLatency:
    """Performance tests for response latency."""

    @pytest.mark.timeout(5)  # Fail if test takes longer than 5 seconds
    def test_conversation_start_latency(
        self,
        conversation_manager: ConversationManager,
    ) -> None:
        """Test that starting a conversation completes within latency target.

        Target: < 3 seconds
        Validates: Conversation initialization performance
        """
        # Arrange
        conversation_id = str(uuid.uuid4())
        tenant_id = "test-tenant-123"
        user_id = "test-user-456"

        # Act: Measure start time
        start_time = time.perf_counter()

        context = conversation_manager.start_conversation(
            conversation_id=conversation_id,
            tenant_id=tenant_id,
            user_id=user_id,
        )

        end_time = time.perf_counter()
        duration = end_time - start_time

        # Assert: Latency is within target
        assert duration < 3.0, f"Conversation start took {duration:.3f}s (target: < 3s)"
        assert context.conversation_id == conversation_id

    @pytest.mark.timeout(5)
    def test_message_processing_latency(
        self,
        conversation_manager: ConversationManager,
    ) -> None:
        """Test that processing a user message completes within latency target.

        Target: < 3 seconds (excluding LLM call)
        Validates: Message processing and state transition performance
        """
        # Arrange: Start conversation
        conversation_id = str(uuid.uuid4())
        tenant_id = "test-tenant-123"
        user_id = "test-user-456"

        context = conversation_manager.start_conversation(
            conversation_id=conversation_id,
            tenant_id=tenant_id,
            user_id=user_id,
        )

        # Act: Measure state update time (no LLM calls)
        start_time = time.perf_counter()

        context.state = ConversationState.UNDERSTANDING_GOAL
        context.agent_goal = "Summarize Notion tasks"

        end_time = time.perf_counter()
        duration = end_time - start_time

        # Assert: Latency is within target
        assert duration < 3.0, f"State update took {duration:.3f}s (target: < 3s)"
        assert context.state == ConversationState.UNDERSTANDING_GOAL

    @pytest.mark.timeout(5)
    def test_requirements_gathering_latency(
        self,
        conversation_manager: ConversationManager,
    ) -> None:
        """Test that requirements gathering operations complete within latency target.

        Target: < 3 seconds
        Validates: Requirements update performance
        """
        # Arrange: Start conversation
        conversation_id = str(uuid.uuid4())
        tenant_id = "test-tenant-123"
        user_id = "test-user-456"

        context = conversation_manager.start_conversation(
            conversation_id=conversation_id,
            tenant_id=tenant_id,
            user_id=user_id,
        )

        # Act: Measure requirements gathering time
        start_time = time.perf_counter()

        context.update_requirements(
            schedule="daily",
            priority="high",
            output_format="summary",
            integration="notion",
        )

        end_time = time.perf_counter()
        duration = end_time - start_time

        # Assert: Latency is within target
        assert duration < 3.0, f"Requirements gathering took {duration:.3f}s (target: < 3s)"
        assert len(context.requirements) == 4

    @pytest.mark.timeout(10)
    def test_concurrent_conversation_performance(
        self,
        conversation_manager: ConversationManager,
    ) -> None:
        """Test that handling multiple concurrent conversations maintains performance.

        Target: < 3 seconds for 10 sequential conversation starts
        Validates: System scalability under load
        """
        # Arrange: Create multiple conversation sessions
        num_conversations = 10
        durations = []

        # Act: Start conversations and measure each
        for i in range(num_conversations):
            conversation_id = str(uuid.uuid4())
            tenant_id = f"test-tenant-{i}"
            user_id = f"test-user-{i}"

            start_time = time.perf_counter()

            conversation_manager.start_conversation(
                conversation_id=conversation_id,
                tenant_id=tenant_id,
                user_id=user_id,
            )

            end_time = time.perf_counter()
            durations.append(end_time - start_time)

        # Assert: All conversations completed within target
        max_duration = max(durations)
        avg_duration = sum(durations) / len(durations)

        assert max_duration < 3.0, (
            f"Slowest conversation took {max_duration:.3f}s (target: < 3s)"
        )
        assert avg_duration < 1.0, (
            f"Average conversation start time {avg_duration:.3f}s (target: < 1s for efficiency)"
        )

    @pytest.mark.timeout(5)
    def test_context_retrieval_latency(
        self,
        conversation_manager: ConversationManager,
    ) -> None:
        """Test that retrieving conversation context is fast.

        Target: < 100ms
        Validates: In-memory context storage performance
        """
        # Arrange: Create a conversation
        conversation_id = str(uuid.uuid4())
        tenant_id = "test-tenant-123"
        user_id = "test-user-456"

        conversation_manager.start_conversation(
            conversation_id=conversation_id,
            tenant_id=tenant_id,
            user_id=user_id,
        )

        # Act: Measure context retrieval time
        start_time = time.perf_counter()

        context = conversation_manager.get_context(conversation_id)

        end_time = time.perf_counter()
        duration = end_time - start_time

        # Assert: Retrieval is very fast (< 100ms)
        assert duration < 0.1, f"Context retrieval took {duration*1000:.1f}ms (target: < 100ms)"
        assert context is not None
        assert context.conversation_id == conversation_id

    @pytest.mark.timeout(5)
    def test_state_transition_latency(
        self,
        conversation_manager: ConversationManager,
    ) -> None:
        """Test that state transitions are performant.

        Target: < 10ms per transition
        Validates: State machine performance
        """
        # Arrange: Create a conversation
        conversation_id = str(uuid.uuid4())
        tenant_id = "test-tenant-123"
        user_id = "test-user-456"

        context = conversation_manager.start_conversation(
            conversation_id=conversation_id,
            tenant_id=tenant_id,
            user_id=user_id,
        )

        # Act: Measure state transition time
        start_time = time.perf_counter()

        context.state = ConversationState.UNDERSTANDING_GOAL
        context.state = ConversationState.INTEGRATION_SETUP
        context.state = ConversationState.REQUIREMENTS_GATHERING
        context.state = ConversationState.SKILL_DESIGN

        end_time = time.perf_counter()
        duration = end_time - start_time

        # Assert: Transitions are very fast (< 10ms for 4 transitions)
        assert duration < 0.01, (
            f"State transitions took {duration*1000:.1f}ms (target: < 10ms)"
        )

    @pytest.mark.timeout(5)
    def test_message_history_performance(
        self,
        conversation_manager: ConversationManager,
    ) -> None:
        """Test that message history operations are performant.

        Target: < 50ms for adding 100 messages
        Validates: Message storage performance
        """
        # Arrange: Create a conversation
        conversation_id = str(uuid.uuid4())
        tenant_id = "test-tenant-123"
        user_id = "test-user-456"

        context = conversation_manager.start_conversation(
            conversation_id=conversation_id,
            tenant_id=tenant_id,
            user_id=user_id,
        )

        # Act: Add many messages and measure time
        start_time = time.perf_counter()

        for i in range(100):
            role = "user" if i % 2 == 0 else "assistant"
            context.add_message(role, f"Message {i}")

        end_time = time.perf_counter()
        duration = end_time - start_time

        # Assert: Adding messages is fast
        assert duration < 0.05, (
            f"Adding 100 messages took {duration*1000:.1f}ms (target: < 50ms)"
        )
        assert len(context.messages) == 100

    @pytest.mark.timeout(5)
    def test_requirements_update_performance(
        self,
        conversation_manager: ConversationManager,
    ) -> None:
        """Test that updating requirements is performant.

        Target: < 10ms for 50 requirement updates
        Validates: Dictionary update performance
        """
        # Arrange: Create a conversation
        conversation_id = str(uuid.uuid4())
        tenant_id = "test-tenant-123"
        user_id = "test-user-456"

        context = conversation_manager.start_conversation(
            conversation_id=conversation_id,
            tenant_id=tenant_id,
            user_id=user_id,
        )

        # Act: Update requirements many times
        start_time = time.perf_counter()

        for i in range(50):
            context.update_requirements(**{f"requirement_{i}": f"value_{i}"})

        end_time = time.perf_counter()
        duration = end_time - start_time

        # Assert: Updates are fast
        assert duration < 0.01, (
            f"Updating 50 requirements took {duration*1000:.1f}ms (target: < 10ms)"
        )
        assert len(context.requirements) == 50
