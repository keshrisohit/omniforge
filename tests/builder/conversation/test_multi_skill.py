"""Tests for multi-skill conversation flows."""

import pytest

from omniforge.builder.conversation.manager import ConversationManager, ConversationState
from omniforge.builder.discovery.service import SkillDiscoveryService
from omniforge.builder.generation.agent_generator import AgentGenerator
from omniforge.builder.models import TriggerType


class TestMultiSkillConversation:
    """Tests for multi-skill conversation flows."""

    @pytest.mark.asyncio
    async def test_multi_skill_detection_in_conversation(self) -> None:
        """Test multi-skill detection during conversation."""
        manager = ConversationManager(agent_generator=AgentGenerator())
        context = manager.start_conversation("conv-1", "tenant-1", "user-1")

        # Initial state
        context, _ = await manager.process_user_input(
            "conv-1",
            "Generate report from Notion and post to Slack",
        )

        # Integration
        context, _ = await manager.process_user_input("conv-1", "Notion")
        context, _ = await manager.process_user_input("conv-1", "Yes")

        # Requirements with multi-skill description
        context, response = await manager.process_user_input(
            "conv-1",
            "Fetch weekly data from Notion then post summary to Slack",
        )

        # Should detect multi-skill and suggest
        assert context.skill_needs_analysis is not None
        assert context.skill_needs_analysis.is_multi_skill
        assert len(context.skill_needs_analysis.skills_needed) >= 2

    @pytest.mark.asyncio
    async def test_single_skill_flow_unchanged(self) -> None:
        """Test single skill flow still works."""
        manager = ConversationManager(agent_generator=AgentGenerator())
        context = manager.start_conversation("conv-2", "tenant-1", "user-1")

        # Go through single skill flow
        await manager.process_user_input("conv-2", "Generate Notion reports")
        await manager.process_user_input("conv-2", "Notion")
        await manager.process_user_input("conv-2", "Yes")
        context, response = await manager.process_user_input(
            "conv-2",
            "Generate weekly summary every Monday",
        )

        # Should detect single skill
        assert context.skill_needs_analysis is not None
        assert not context.skill_needs_analysis.is_multi_skill
        assert context.state == ConversationState.SKILL_DESIGN

    @pytest.mark.asyncio
    async def test_skill_suggestion_state_transition(self) -> None:
        """Test transition to skill suggestion state."""
        # Mock skill discovery service
        from unittest.mock import AsyncMock, MagicMock

        mock_repo = MagicMock()
        discovery = SkillDiscoveryService(repository=mock_repo)
        discovery.discover_by_context = AsyncMock(return_value=[])

        from omniforge.builder.conversation.skill_suggestion import SkillSuggestionManager

        suggestion_manager = SkillSuggestionManager(discovery_service=discovery)

        manager = ConversationManager(
            agent_generator=AgentGenerator(),
            skill_suggestion_manager=suggestion_manager,
        )

        context = manager.start_conversation("conv-3", "tenant-1", "user-1")

        # Go through to multi-skill detection
        await manager.process_user_input("conv-3", "Automate workflow")
        await manager.process_user_input("conv-3", "Notion")
        await manager.process_user_input("conv-3", "Yes")
        context, _ = await manager.process_user_input(
            "conv-3",
            "Get data from Notion and then post to Slack",
        )

        # Should be in skill suggestion state
        assert context.state == ConversationState.SKILL_SUGGESTION

    @pytest.mark.asyncio
    async def test_custom_skill_choice(self) -> None:
        """Test user choosing custom skills."""
        from unittest.mock import AsyncMock, MagicMock

        mock_repo = MagicMock()
        discovery = SkillDiscoveryService(repository=mock_repo)
        discovery.discover_by_context = AsyncMock(return_value=[])

        from omniforge.builder.conversation.skill_suggestion import SkillSuggestionManager

        suggestion_manager = SkillSuggestionManager(discovery_service=discovery)

        manager = ConversationManager(
            agent_generator=AgentGenerator(),
            skill_suggestion_manager=suggestion_manager,
        )

        context = manager.start_conversation("conv-4", "tenant-1", "user-1")

        # Go through to skill suggestion
        await manager.process_user_input("conv-4", "Automate workflow")
        await manager.process_user_input("conv-4", "Notion")
        await manager.process_user_input("conv-4", "Yes")
        await manager.process_user_input(
            "conv-4",
            "Fetch from Notion and post to Slack",
        )

        # Choose custom skills
        context, response = await manager.process_user_input("conv-4", "create custom")

        # Should move to skill design
        assert context.state == ConversationState.SKILL_DESIGN

    @pytest.mark.asyncio
    async def test_plain_language_flow_description(self) -> None:
        """Test plain language flow descriptions."""
        manager = ConversationManager(agent_generator=AgentGenerator())
        context = manager.start_conversation("conv-5", "tenant-1", "user-1")

        # Multi-skill scenario
        await manager.process_user_input("conv-5", "Automate reports")
        await manager.process_user_input("conv-5", "Notion")
        await manager.process_user_input("conv-5", "Yes")
        context, response = await manager.process_user_input(
            "conv-5",
            "Generate report from Notion and then post to Slack",
        )

        # Response should be plain language (no technical jargon)
        assert "sequential" not in response.lower()
        assert "orchestration" not in response.lower()

        # Should have summary or be in skill design state
        assert "skill" in response.lower() or context.state == ConversationState.SKILL_DESIGN

    @pytest.mark.asyncio
    async def test_skill_ordering_captured(self) -> None:
        """Test skill ordering is properly captured."""
        manager = ConversationManager(agent_generator=AgentGenerator())
        context = manager.start_conversation("conv-6", "tenant-1", "user-1")

        # Complete multi-skill flow
        await manager.process_user_input("conv-6", "Multi-step workflow")
        await manager.process_user_input("conv-6", "Notion")
        await manager.process_user_input("conv-6", "Yes")
        await manager.process_user_input(
            "conv-6",
            "Fetch data from Notion then analyze then post to Slack",
        )
        await manager.process_user_input("conv-6", "Yes")
        await manager.process_user_input("conv-6", "Yes")
        context, _ = await manager.process_user_input("conv-6", "Yes")

        # Check agent config has ordered skills
        assert context.agent_config is not None
        orders = [skill.order for skill in context.agent_config.skills]
        assert orders == sorted(orders)
        assert orders[0] == 1

    @pytest.mark.asyncio
    async def test_user_changing_mind(self) -> None:
        """Test handling user changing their mind."""
        manager = ConversationManager(agent_generator=AgentGenerator())
        context = manager.start_conversation("conv-7", "tenant-1", "user-1")

        # Go through flow
        await manager.process_user_input("conv-7", "Workflow automation")
        await manager.process_user_input("conv-7", "Notion")
        await manager.process_user_input("conv-7", "Yes")
        await manager.process_user_input(
            "conv-7",
            "Fetch from Notion and post to Slack",
        )

        # User says no to summary
        context, response = await manager.process_user_input("conv-7", "No, that's wrong")

        # Should go back to requirements gathering
        assert context.state == ConversationState.REQUIREMENTS_GATHERING
        assert "change" in response.lower() or "what" in response.lower()

    @pytest.mark.asyncio
    async def test_multi_skill_agent_creation(self) -> None:
        """Test complete multi-skill agent creation."""
        manager = ConversationManager(agent_generator=AgentGenerator())
        context = manager.start_conversation("conv-8", "tenant-1", "user-1")

        # Complete flow
        await manager.process_user_input("conv-8", "Multi-skill agent")
        await manager.process_user_input("conv-8", "Notion")
        await manager.process_user_input("conv-8", "Yes")
        await manager.process_user_input(
            "conv-8",
            "Get data from Notion and then send to Slack",
        )
        await manager.process_user_input("conv-8", "Yes")
        await manager.process_user_input("conv-8", "Yes")
        context, _ = await manager.process_user_input("conv-8", "Yes")

        # Verify agent config
        assert context.state == ConversationState.COMPLETE
        assert context.agent_config is not None
        assert len(context.agent_config.skills) >= 1

    @pytest.mark.asyncio
    async def test_conversation_context_preservation(self) -> None:
        """Test conversation context is preserved across states."""
        manager = ConversationManager(agent_generator=AgentGenerator())
        manager.start_conversation("conv-9", "tenant-1", "user-1")

        # Go through states
        await manager.process_user_input("conv-9", "Automate work")
        await manager.process_user_input("conv-9", "Notion")

        # Check context preserved
        retrieved_context = manager.get_context("conv-9")
        assert retrieved_context is not None
        assert retrieved_context.agent_goal == "Automate work"
        assert retrieved_context.integration_type == "notion"

    @pytest.mark.asyncio
    async def test_message_history_tracking(self) -> None:
        """Test message history is properly tracked."""
        manager = ConversationManager(agent_generator=AgentGenerator())
        context = manager.start_conversation("conv-10", "tenant-1", "user-1")

        await manager.process_user_input("conv-10", "First message")
        await manager.process_user_input("conv-10", "Second message")
        context, _ = await manager.process_user_input("conv-10", "Third message")

        # Should have 6 messages (3 user + 3 assistant)
        assert len(context.messages) == 6

    @pytest.mark.asyncio
    async def test_scheduled_trigger_detection(self) -> None:
        """Test scheduled trigger detection in multi-skill flow."""
        manager = ConversationManager(agent_generator=AgentGenerator())
        context = manager.start_conversation("conv-11", "tenant-1", "user-1")

        await manager.process_user_input("conv-11", "Weekly automation")
        await manager.process_user_input("conv-11", "Notion")
        await manager.process_user_input("conv-11", "Yes")
        await manager.process_user_input(
            "conv-11",
            "Generate report every Monday and post to Slack",
        )
        await manager.process_user_input("conv-11", "Yes")
        await manager.process_user_input("conv-11", "Yes")
        context, _ = await manager.process_user_input("conv-11", "Yes")

        # Should have scheduled trigger
        assert context.agent_config is not None
        assert context.agent_config.trigger == TriggerType.SCHEDULED
        assert context.agent_config.schedule is not None

    @pytest.mark.asyncio
    async def test_on_demand_trigger_default(self) -> None:
        """Test on-demand trigger is default."""
        manager = ConversationManager(agent_generator=AgentGenerator())
        context = manager.start_conversation("conv-12", "tenant-1", "user-1")

        await manager.process_user_input("conv-12", "Data processing")
        await manager.process_user_input("conv-12", "Notion")
        await manager.process_user_input("conv-12", "Yes")
        await manager.process_user_input(
            "conv-12",
            "Process data when I ask",
        )
        await manager.process_user_input("conv-12", "Yes")
        await manager.process_user_input("conv-12", "Yes")
        context, _ = await manager.process_user_input("conv-12", "Yes")

        # Should be on-demand
        assert context.agent_config is not None
        assert context.agent_config.trigger == TriggerType.ON_DEMAND

    @pytest.mark.asyncio
    async def test_skill_needs_analysis_stored(self) -> None:
        """Test skill needs analysis is stored in context."""
        manager = ConversationManager(agent_generator=AgentGenerator())
        context = manager.start_conversation("conv-13", "tenant-1", "user-1")

        await manager.process_user_input("conv-13", "Automation task")
        await manager.process_user_input("conv-13", "Notion")
        await manager.process_user_input("conv-13", "Yes")
        context, _ = await manager.process_user_input(
            "conv-13",
            "Fetch from Notion and post to Slack",
        )

        # Analysis should be stored
        assert context.skill_needs_analysis is not None
        assert context.skill_needs_analysis.is_multi_skill
        assert context.skill_needs_analysis.suggested_flow

    @pytest.mark.asyncio
    async def test_integration_id_in_agent_config(self) -> None:
        """Test integration ID is included in agent config."""
        manager = ConversationManager(agent_generator=AgentGenerator())
        context = manager.start_conversation("conv-14", "tenant-1", "user-1")

        # Set integration ID manually
        await manager.process_user_input("conv-14", "Test agent")
        await manager.process_user_input("conv-14", "Notion")
        await manager.process_user_input("conv-14", "Yes")

        context.integration_id = "integration-123"

        await manager.process_user_input("conv-14", "Simple task")
        await manager.process_user_input("conv-14", "Yes")
        await manager.process_user_input("conv-14", "Yes")
        context, _ = await manager.process_user_input("conv-14", "Yes")

        # Integration ID should be in config
        assert context.agent_config is not None
        assert "integration-123" in context.agent_config.integrations
