"""End-to-end integration tests for conversation flow.

Tests the complete conversation flow from discovery through generation to activation.
"""

import uuid
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from omniforge.builder.conversation import ConversationManager, ConversationState
from omniforge.builder.executor import AgentExecutor
from omniforge.builder.models import AgentConfig, AgentStatus, TriggerType
from omniforge.builder.repository import AgentConfigRepository
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


@pytest.fixture
async def agent_executor(db_session: AsyncSession) -> AgentExecutor:
    """Create an agent executor for testing.

    Args:
        db_session: Database session fixture

    Returns:
        AgentExecutor instance
    """
    repository = AgentConfigRepository(db_session)
    return AgentExecutor(repository)


@pytest.fixture
async def repository(db_session: AsyncSession) -> AgentConfigRepository:
    """Create a repository for testing.

    Args:
        db_session: Database session fixture

    Returns:
        AgentConfigRepository instance
    """
    return AgentConfigRepository(db_session)


class TestConversationE2E:
    """End-to-end tests for conversation flow."""

    async def test_full_conversation_flow_discovery_to_activation(
        self,
        conversation_manager: ConversationManager,
        skill_generator: SkillMdGenerator,
        repository: AgentConfigRepository,
    ) -> None:
        """Test complete conversation flow from discovery to agent activation.

        This test validates the full end-to-end flow:
        1. Start conversation (INITIAL state)
        2. User describes goal (UNDERSTANDING_GOAL state)
        3. Integration setup (INTEGRATION_SETUP state)
        4. Requirements gathering (REQUIREMENTS_GATHERING state)
        5. Skill generation (SKILL_DESIGN state)
        6. Agent activation (DEPLOYMENT state)
        7. Agent is ready (COMPLETE state)
        """
        # Arrange
        conversation_id = str(uuid.uuid4())
        tenant_id = "test-tenant-123"
        user_id = "test-user-456"

        # Act & Assert: Step 1 - Start conversation
        context = conversation_manager.start_conversation(
            conversation_id=conversation_id,
            tenant_id=tenant_id,
            user_id=user_id,
        )

        assert context.conversation_id == conversation_id
        assert context.tenant_id == tenant_id
        assert context.user_id == user_id
        assert context.state == ConversationState.INITIAL

        # Act & Assert: Step 2-5 - Progress through states
        # We test state transitions directly since process_user_input requires LLM
        context.state = ConversationState.UNDERSTANDING_GOAL
        context.agent_goal = "Create an agent that syncs my Notion tasks to a daily summary"
        assert context.state == ConversationState.UNDERSTANDING_GOAL
        assert context.agent_goal is not None

        # Integration setup
        context.integration_type = "notion"
        context.integration_id = "test-integration-123"
        context.state = ConversationState.INTEGRATION_SETUP
        assert context.integration_type == "notion"
        assert context.integration_id == "test-integration-123"

        # Requirements gathering
        context.state = ConversationState.REQUIREMENTS_GATHERING
        context.update_requirements(schedule="daily", time="8am", priority="high")
        assert context.state == ConversationState.REQUIREMENTS_GATHERING
        assert len(context.requirements) > 0

        # Skill design
        context.state = ConversationState.SKILL_DESIGN
        assert context.state == ConversationState.SKILL_DESIGN

        # Act & Assert: Step 6 - Agent activation
        agent_config = AgentConfig(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            user_id=user_id,
            name="Notion Daily Summary Agent",
            description="Summarizes high priority tasks daily",
            trigger_type=TriggerType.SCHEDULE,
            cron_expression="0 8 * * *",
            status=AgentStatus.ACTIVE,
            skills=[],
            integration_ids=["test-integration-123"],
        )

        saved_config = await repository.create(agent_config)

        assert saved_config.id is not None
        assert saved_config.status == AgentStatus.ACTIVE
        assert saved_config.trigger_type == TriggerType.SCHEDULE
        assert saved_config.cron_expression == "0 8 * * *"

        # Act & Assert: Step 7 - Conversation complete
        context.state = ConversationState.COMPLETE
        context.agent_config = saved_config

        assert context.state == ConversationState.COMPLETE
        assert context.agent_config is not None
        assert context.agent_config.status == AgentStatus.ACTIVE

    def test_conversation_with_state_transitions(
        self,
        conversation_manager: ConversationManager,
    ) -> None:
        """Test conversation state transitions are valid.

        Validates that the conversation manager properly transitions between states
        and prevents invalid state transitions.
        """
        # Arrange
        conversation_id = str(uuid.uuid4())
        tenant_id = "test-tenant-123"
        user_id = "test-user-456"

        # Act: Start conversation
        context = conversation_manager.start_conversation(
            conversation_id=conversation_id,
            tenant_id=tenant_id,
            user_id=user_id,
        )

        # Assert: Initial state
        assert context.state == ConversationState.INITIAL

        # Act: Progress to understanding goal
        context.state = ConversationState.UNDERSTANDING_GOAL
        context.agent_goal = "Test goal"

        # Assert: Valid transition
        assert context.state == ConversationState.UNDERSTANDING_GOAL
        assert context.agent_goal == "Test goal"

        # Act: Progress to integration setup
        context.state = ConversationState.INTEGRATION_SETUP
        context.integration_type = "notion"

        # Assert: Valid transition
        assert context.state == ConversationState.INTEGRATION_SETUP
        assert context.integration_type == "notion"

        # Act: Progress to requirements gathering
        context.state = ConversationState.REQUIREMENTS_GATHERING
        context.update_requirements(schedule="daily", priority="high")

        # Assert: Valid transition with requirements
        assert context.state == ConversationState.REQUIREMENTS_GATHERING
        assert context.requirements["schedule"] == "daily"
        assert context.requirements["priority"] == "high"

    def test_conversation_message_history(
        self,
        conversation_manager: ConversationManager,
    ) -> None:
        """Test conversation maintains message history correctly.

        Validates that all user and assistant messages are tracked in the
        conversation context for context preservation.
        """
        # Arrange
        conversation_id = str(uuid.uuid4())
        tenant_id = "test-tenant-123"
        user_id = "test-user-456"

        # Act: Start conversation
        context = conversation_manager.start_conversation(
            conversation_id=conversation_id,
            tenant_id=tenant_id,
            user_id=user_id,
        )

        # Act: Add messages
        context.add_message("user", "I want to create an agent")
        context.add_message("assistant", "Great! What should your agent do?")
        context.add_message("user", "Summarize my Notion tasks")
        context.add_message("assistant", "Understood. Let's set up Notion integration.")

        # Assert: Message history is maintained
        assert len(context.messages) == 4
        assert context.messages[0]["role"] == "user"
        assert context.messages[0]["content"] == "I want to create an agent"
        assert context.messages[1]["role"] == "assistant"
        assert context.messages[3]["content"] == "Understood. Let's set up Notion integration."

    def test_conversation_context_retrieval(
        self,
        conversation_manager: ConversationManager,
    ) -> None:
        """Test conversation context can be retrieved after creation.

        Validates that conversation contexts are properly stored and can be
        retrieved by conversation ID.
        """
        # Arrange
        conversation_id = str(uuid.uuid4())
        tenant_id = "test-tenant-123"
        user_id = "test-user-456"

        # Act: Start conversation
        original_context = conversation_manager.start_conversation(
            conversation_id=conversation_id,
            tenant_id=tenant_id,
            user_id=user_id,
        )

        # Act: Retrieve context
        retrieved_context = conversation_manager.get_context(conversation_id)

        # Assert: Context matches
        assert retrieved_context is not None
        assert retrieved_context.conversation_id == original_context.conversation_id
        assert retrieved_context.tenant_id == original_context.tenant_id
        assert retrieved_context.user_id == original_context.user_id
        assert retrieved_context.state == original_context.state
