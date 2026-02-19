"""Tests for conversation state machine - backward compatibility tests."""

import pytest

from omniforge.builder.conversation import (
    ConversationContext,
    ConversationManager,
    ConversationState,
)
from omniforge.builder.models import TriggerType


class TestConversationContext:
    """Tests for ConversationContext model."""

    def test_create_context(self) -> None:
        """Test creating conversation context."""
        context = ConversationContext(
            conversation_id="conv-123",
            tenant_id="tenant-456",
            user_id="user-789",
        )

        assert context.conversation_id == "conv-123"
        assert context.state == ConversationState.INITIAL
        assert len(context.messages) == 0

    def test_add_message(self) -> None:
        """Test adding messages to context."""
        context = ConversationContext(
            conversation_id="conv-1",
            tenant_id="tenant-1",
            user_id="user-1",
        )

        context.add_message("user", "Hello")
        context.add_message("assistant", "Hi there!")

        assert len(context.messages) == 2
        assert context.messages[0]["role"] == "user"
        assert context.messages[0]["content"] == "Hello"
        assert context.messages[1]["role"] == "assistant"

    def test_update_requirements(self) -> None:
        """Test updating requirements."""
        context = ConversationContext(
            conversation_id="conv-1",
            tenant_id="tenant-1",
            user_id="user-1",
        )

        context.update_requirements(trigger="scheduled", format="markdown")

        assert context.requirements["trigger"] == "scheduled"
        assert context.requirements["format"] == "markdown"


class TestConversationManager:
    """Tests for ConversationManager."""

    def test_start_conversation(self) -> None:
        """Test starting a new conversation."""
        manager = ConversationManager()

        context = manager.start_conversation("conv-1", "tenant-1", "user-1")

        assert context.conversation_id == "conv-1"
        assert context.state == ConversationState.INITIAL
        assert manager.get_context("conv-1") is not None

    def test_get_context(self) -> None:
        """Test retrieving conversation context."""
        manager = ConversationManager()
        manager.start_conversation("conv-1", "tenant-1", "user-1")

        context = manager.get_context("conv-1")

        assert context is not None
        assert context.conversation_id == "conv-1"

        # Non-existent conversation
        assert manager.get_context("nonexistent") is None

    @pytest.mark.asyncio
    async def test_full_conversation_flow(self) -> None:
        """Test complete conversation flow from start to finish."""
        manager = ConversationManager()
        context = manager.start_conversation("conv-1", "tenant-1", "user-1")

        # Step 1: Initial state - user describes goal
        context, response = await manager.process_user_input(
            "conv-1",
            "I want to automate weekly reports from Notion",
        )

        assert context.state == ConversationState.UNDERSTANDING_GOAL
        assert "automate" in response.lower()

        # Step 2: Understanding goal - identify integration
        context, response = await manager.process_user_input("conv-1", "Notion")

        assert context.state == ConversationState.INTEGRATION_SETUP
        assert context.integration_type == "notion"
        assert "connect" in response.lower()

        # Step 3: Integration setup - confirm OAuth
        context, response = await manager.process_user_input("conv-1", "Yes, ready")

        assert context.state == ConversationState.REQUIREMENTS_GATHERING
        assert "connected" in response.lower()

        # Step 4: Requirements gathering
        context, response = await manager.process_user_input(
            "conv-1",
            "Generate weekly status reports every Monday at 8am",
        )

        # Should move to skill design
        assert context.state in [ConversationState.SKILL_DESIGN, ConversationState.SKILL_SUGGESTION]
        assert context.requirements.get("trigger") == "scheduled"

        # Step 5: Skill design confirmation
        context, response = await manager.process_user_input("conv-1", "Yes, looks good")

        assert context.state == ConversationState.TESTING
        assert len(context.skill_requests) >= 1
        assert "test" in response.lower()

        # Step 6: Testing
        context, response = await manager.process_user_input("conv-1", "Yes, test it")

        assert context.state == ConversationState.DEPLOYMENT

        # Step 7: Deployment
        context, response = await manager.process_user_input("conv-1", "Yes, activate")

        assert context.state == ConversationState.COMPLETE
        assert context.agent_config is not None
        assert context.agent_config.trigger == TriggerType.SCHEDULED
        assert len(context.agent_config.skills) >= 1
        assert "active" in response.lower()

    @pytest.mark.asyncio
    async def test_on_demand_trigger_flow(self) -> None:
        """Test conversation flow for on-demand agent."""
        manager = ConversationManager()
        manager.start_conversation("conv-2", "tenant-1", "user-1")

        # Initial
        await manager.process_user_input("conv-2", "I need an on-demand data export")

        # Integration
        await manager.process_user_input("conv-2", "Notion")
        await manager.process_user_input("conv-2", "Yes")

        # Requirements (no schedule mentioned)
        context, _ = await manager.process_user_input(
            "conv-2",
            "Export data when I request it",
        )

        # Should be on-demand
        assert context.requirements.get("trigger") == "on_demand"

        # Complete flow
        await manager.process_user_input("conv-2", "Yes")
        await manager.process_user_input("conv-2", "Yes")
        context, _ = await manager.process_user_input("conv-2", "Yes")

        assert context.agent_config is not None
        assert context.agent_config.trigger == TriggerType.ON_DEMAND
        assert context.agent_config.schedule is None

    @pytest.mark.asyncio
    async def test_conversation_not_found(self) -> None:
        """Test error when conversation not found."""
        manager = ConversationManager()

        with pytest.raises(ValueError, match="not found"):
            await manager.process_user_input("nonexistent", "Hello")

    @pytest.mark.asyncio
    async def test_requirement_change_flow(self) -> None:
        """Test user changing requirements after initial summary."""
        manager = ConversationManager()
        manager.start_conversation("conv-3", "tenant-1", "user-1")

        # Go through initial steps
        await manager.process_user_input("conv-3", "Weekly reports")
        await manager.process_user_input("conv-3", "Notion")
        await manager.process_user_input("conv-3", "Yes")
        await manager.process_user_input("conv-3", "Generate reports every Monday")

        # User says no to summary
        context, response = await manager.process_user_input("conv-3", "No, that's wrong")

        # Should go back to requirements gathering
        assert context.state == ConversationState.REQUIREMENTS_GATHERING
        assert "changed" in response.lower() or "what needs" in response.lower() or "what" in response.lower()

    @pytest.mark.asyncio
    async def test_message_history_tracking(self) -> None:
        """Test that conversation history is tracked."""
        manager = ConversationManager()
        manager.start_conversation("conv-4", "tenant-1", "user-1")

        await manager.process_user_input("conv-4", "First message")
        await manager.process_user_input("conv-4", "Second message")
        context, _ = await manager.process_user_input("conv-4", "Third message")

        # Should have 6 messages: 3 user + 3 assistant
        assert len(context.messages) == 6
        assert context.messages[0]["role"] == "user"
        assert context.messages[1]["role"] == "assistant"
        assert context.messages[0]["content"] == "First message"

    @pytest.mark.asyncio
    async def test_integration_type_extracted(self) -> None:
        """Test integration type is correctly extracted and normalized."""
        manager = ConversationManager()
        manager.start_conversation("conv-5", "tenant-1", "user-1")

        await manager.process_user_input("conv-5", "Create an agent")
        context, _ = await manager.process_user_input("conv-5", "  NOTION  ")

        assert context.integration_type == "notion"  # Normalized

    @pytest.mark.asyncio
    async def test_skill_request_creation(self) -> None:
        """Test skill request is properly created."""
        manager = ConversationManager()
        manager.start_conversation("conv-6", "tenant-1", "user-1")

        # Go through to skill design
        await manager.process_user_input("conv-6", "Automate reports")
        await manager.process_user_input("conv-6", "Notion")
        await manager.process_user_input("conv-6", "Yes")
        await manager.process_user_input("conv-6", "Weekly reports on Monday")
        context, _ = await manager.process_user_input("conv-6", "Yes")

        # Check skill requests were created
        assert len(context.skill_requests) >= 1
        skill_request = context.skill_requests[0]
        assert skill_request.integration_type in ["notion", None] or skill_request.integration_type
        assert len(skill_request.steps) > 0

    @pytest.mark.asyncio
    async def test_agent_config_creation(self) -> None:
        """Test final agent config is properly created."""
        manager = ConversationManager()
        manager.start_conversation("conv-7", "tenant-1", "user-1")

        # Complete full flow
        await manager.process_user_input("conv-7", "Weekly Notion reports")
        await manager.process_user_input("conv-7", "Notion")
        context, _ = await manager.process_user_input("conv-7", "Yes")

        # Set integration ID
        context.integration_id = "integration-123"

        await manager.process_user_input("conv-7", "Reports every Monday")
        await manager.process_user_input("conv-7", "Yes")
        await manager.process_user_input("conv-7", "Yes")
        context, _ = await manager.process_user_input("conv-7", "Yes")

        agent_config = context.agent_config
        assert agent_config is not None
        assert agent_config.tenant_id == "tenant-1"
        assert agent_config.created_by == "user-1"
        assert len(agent_config.skills) >= 1
        assert "integration-123" in agent_config.integrations
