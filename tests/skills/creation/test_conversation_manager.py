"""Tests for ConversationManager class."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from omniforge.skills.creation.conversation import ConversationManager
from omniforge.skills.creation.models import (
    ConversationContext,
    ConversationState,
    SkillCapabilities,
)


class TestConversationManager:
    """Tests for ConversationManager class."""

    @pytest.fixture
    def mock_gatherer(self) -> MagicMock:
        """Create mock RequirementsGatherer."""
        gatherer = MagicMock()
        # Capability analysis
        capabilities = SkillCapabilities(
            needs_file_operations=True,
            confidence=0.95,
            reasoning="Test capabilities"
        )
        gatherer.analyze_skill_requirements = AsyncMock(return_value=capabilities)
        gatherer.determine_required_tools = MagicMock(return_value=["Read", "Write"])
        gatherer.generate_clarifying_questions = AsyncMock(
            return_value=["What are the inputs?", "What are the outputs?"]
        )
        gatherer.extract_requirements = AsyncMock(
            return_value={"examples": ["example1"], "triggers": ["trigger1"]}
        )
        gatherer.has_sufficient_context = MagicMock(return_value=True)
        gatherer.generate_skill_name = AsyncMock(return_value="test-skill")
        gatherer.generate_description = AsyncMock(return_value="Test skill for unit testing")
        # New async methods for intelligent inference
        gatherer.attempt_inference_from_context = AsyncMock(
            return_value={"inferred": False, "confidence": 0.0}
        )
        gatherer.should_ask_clarification = AsyncMock(return_value=True)
        return gatherer

    @pytest.fixture
    def mock_generator(self) -> MagicMock:
        """Create mock SkillMdGenerator."""
        generator = MagicMock()
        generator.generate = AsyncMock(
            return_value="---\nname: test-skill\ndescription: Test skill\n---\n\nContent here"
        )
        generator.fix_validation_errors = AsyncMock(
            return_value="---\nname: test-skill\ndescription: Fixed skill\n---\n\nFixed content"
        )
        return generator

    @pytest.fixture
    def manager(self, mock_gatherer: MagicMock, mock_generator: MagicMock) -> ConversationManager:
        """Create ConversationManager instance."""
        return ConversationManager(gatherer=mock_gatherer, generator=mock_generator)

    @pytest.mark.asyncio
    async def test_initialization(
        self, mock_gatherer: MagicMock, mock_generator: MagicMock
    ) -> None:
        """ConversationManager should initialize with dependencies."""
        manager = ConversationManager(gatherer=mock_gatherer, generator=mock_generator)

        assert manager.gatherer == mock_gatherer
        assert manager.generator == mock_generator

    @pytest.mark.asyncio
    async def test_state_transition_idle_to_gathering_purpose(
        self, manager: ConversationManager
    ) -> None:
        """Should transition from IDLE to GATHERING_PURPOSE."""
        context = ConversationContext(state=ConversationState.IDLE)

        response, new_context = await manager.process_message("Create a skill", context)

        assert new_context.state == ConversationState.GATHERING_PURPOSE
        assert "purpose" in response.lower()
        assert len(new_context.message_history) == 2  # User + Assistant

    @pytest.mark.asyncio
    async def test_state_transition_gathering_purpose_to_gathering_details(
        self, manager: ConversationManager, mock_gatherer: MagicMock
    ) -> None:
        """Should transition from GATHERING_PURPOSE to GATHERING_DETAILS."""
        context = ConversationContext(state=ConversationState.GATHERING_PURPOSE)

        response, new_context = await manager.process_message("Format product names", context)

        assert new_context.state == ConversationState.GATHERING_DETAILS
        assert new_context.skill_purpose == "Format product names"
        assert new_context.skill_capabilities is not None
        # Verify capabilities were analyzed
        # Note: The actual analyze_skill_requirements call is made via the manager

    @pytest.mark.asyncio
    async def test_state_transition_gathering_details_insufficient_context(
        self, manager: ConversationManager, mock_gatherer: MagicMock
    ) -> None:
        """Should stay in GATHERING_DETAILS when context is insufficient."""
        mock_gatherer.has_sufficient_context = MagicMock(return_value=False)

        context = ConversationContext(
            state=ConversationState.GATHERING_DETAILS,
            skill_purpose="Format names",
        )

        response, new_context = await manager.process_message(
            "It should format names nicely", context
        )

        assert new_context.state == ConversationState.GATHERING_DETAILS
        mock_gatherer.has_sufficient_context.assert_called_once()

    @pytest.mark.asyncio
    async def test_state_transition_gathering_details_sufficient_context(
        self, manager: ConversationManager, mock_gatherer: MagicMock
    ) -> None:
        """Should transition to CONFIRMING_SPEC when context is sufficient."""
        mock_gatherer.has_sufficient_context = MagicMock(return_value=True)

        context = ConversationContext(
            state=ConversationState.GATHERING_DETAILS,
            skill_purpose="Format names",
        )

        response, new_context = await manager.process_message(
            "Input: PA, Output: Pro Analytics", context
        )

        assert new_context.state == ConversationState.CONFIRMING_SPEC
        assert new_context.skill_name == "test-skill"
        assert new_context.skill_description == "Test skill for unit testing"
        mock_gatherer.generate_skill_name.assert_called_once()
        mock_gatherer.generate_description.assert_called_once()

    @pytest.mark.asyncio
    async def test_state_transition_confirming_spec_user_confirms(
        self, manager: ConversationManager
    ) -> None:
        """Should transition to GENERATING when user confirms."""
        context = ConversationContext(
            state=ConversationState.CONFIRMING_SPEC,
            skill_name="test-skill",
            skill_description="Test description",
        )

        response, new_context = await manager.process_message("yes", context)

        assert new_context.state == ConversationState.GENERATING
        assert "generate" in response.lower()

    @pytest.mark.asyncio
    async def test_state_transition_confirming_spec_user_requests_changes(
        self, manager: ConversationManager
    ) -> None:
        """Should transition to GATHERING_DETAILS when user requests changes."""
        context = ConversationContext(
            state=ConversationState.CONFIRMING_SPEC,
            skill_name="test-skill",
        )

        response, new_context = await manager.process_message("no, change the name", context)

        assert new_context.state == ConversationState.GATHERING_DETAILS
        assert "change" in response.lower()

    @pytest.mark.asyncio
    async def test_state_transition_generating_to_validating(
        self, manager: ConversationManager, mock_generator: MagicMock
    ) -> None:
        """Should transition from GENERATING to VALIDATING."""
        context = ConversationContext(
            state=ConversationState.GENERATING,
            skill_name="test-skill",
            skill_description="Test description",
        )

        response, new_context = await manager.process_message("", context)

        assert new_context.state == ConversationState.VALIDATING
        assert new_context.generated_content is not None
        mock_generator.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_state_transition_validating_valid_content(
        self, manager: ConversationManager
    ) -> None:
        """Should transition to SELECTING_STORAGE when content is valid."""
        context = ConversationContext(
            state=ConversationState.VALIDATING,
            skill_name="test-skill",
            generated_content="---\nname: test-skill\ndescription: Test\n---\n\nContent",
        )

        response, new_context = await manager.process_message("", context)

        assert new_context.state == ConversationState.SELECTING_STORAGE
        assert "validated" in response.lower()

    @pytest.mark.asyncio
    async def test_state_transition_validating_invalid_with_retries(
        self, manager: ConversationManager
    ) -> None:
        """Should transition to FIXING_ERRORS when validation fails with retries left."""
        context = ConversationContext(
            state=ConversationState.VALIDATING,
            skill_name="test-skill",
            generated_content="",  # Invalid: no content
            validation_attempts=0,
        )

        response, new_context = await manager.process_message("", context)

        assert new_context.state == ConversationState.FIXING_ERRORS
        assert new_context.validation_attempts == 1
        assert "fix" in response.lower()

    @pytest.mark.asyncio
    async def test_state_transition_validating_invalid_no_retries(
        self, manager: ConversationManager
    ) -> None:
        """Should transition to ERROR when validation fails with no retries left."""
        context = ConversationContext(
            state=ConversationState.VALIDATING,
            skill_name="test-skill",
            generated_content="",  # Invalid: no content
            validation_attempts=3,  # Max retries reached
        )

        response, new_context = await manager.process_message("", context)

        assert new_context.state == ConversationState.ERROR
        assert "couldn't fix" in response.lower()

    @pytest.mark.asyncio
    async def test_state_transition_fixing_errors_to_validating(
        self, manager: ConversationManager, mock_generator: MagicMock
    ) -> None:
        """Should transition from FIXING_ERRORS to VALIDATING."""
        context = ConversationContext(
            state=ConversationState.FIXING_ERRORS,
            skill_name="test-skill",
            generated_content="---\nname: test\n---\n",
            validation_errors=["Missing description"],
        )

        response, new_context = await manager.process_message("", context)

        mock_generator.fix_validation_errors.assert_called_once()
        assert new_context.state == ConversationState.VALIDATING
        assert "revalidating" in response.lower()

    @pytest.mark.asyncio
    async def test_state_transition_selecting_storage_to_saving(
        self, manager: ConversationManager
    ) -> None:
        """Should transition from SELECTING_STORAGE to SAVING."""
        context = ConversationContext(
            state=ConversationState.SELECTING_STORAGE,
            skill_name="test-skill",
            generated_content="---\nname: test-skill\ndescription: Test\n---\n\nContent",
        )

        response, new_context = await manager.process_message("project", context)

        assert new_context.state == ConversationState.SAVING
        assert new_context.storage_layer == "project"
        assert "saving" in response.lower()

    @pytest.mark.asyncio
    async def test_state_transition_saving_to_completed(self, manager: ConversationManager) -> None:
        """Should transition from SAVING to COMPLETED."""
        context = ConversationContext(
            state=ConversationState.SAVING,
            skill_name="test-skill",
            storage_layer="project",
        )

        response, new_context = await manager.process_message("", context)

        assert new_context.state == ConversationState.COMPLETED
        assert "success" in response.lower()

    @pytest.mark.asyncio
    async def test_is_complete_for_completed_state(self, manager: ConversationManager) -> None:
        """is_complete should return True for COMPLETED state."""
        context = ConversationContext(state=ConversationState.COMPLETED)

        assert manager.is_complete(context) is True

    @pytest.mark.asyncio
    async def test_is_complete_for_error_state(self, manager: ConversationManager) -> None:
        """is_complete should return True for ERROR state."""
        context = ConversationContext(state=ConversationState.ERROR)

        assert manager.is_complete(context) is True

    @pytest.mark.asyncio
    async def test_is_complete_for_in_progress_state(self, manager: ConversationManager) -> None:
        """is_complete should return False for in-progress states."""
        in_progress_states = [
            ConversationState.IDLE,
            ConversationState.GATHERING_PURPOSE,
            ConversationState.GATHERING_DETAILS,
            ConversationState.CONFIRMING_SPEC,
            ConversationState.GENERATING,
            ConversationState.VALIDATING,
        ]

        for state in in_progress_states:
            context = ConversationContext(state=state)
            assert manager.is_complete(context) is False, f"Failed for state: {state}"

    @pytest.mark.asyncio
    async def test_message_history_tracking(self, manager: ConversationManager) -> None:
        """Should track message history across process_message calls."""
        context = ConversationContext(state=ConversationState.IDLE)

        # First message
        response1, context = await manager.process_message("Create a skill", context)
        assert len(context.message_history) == 2
        assert context.message_history[0]["role"] == "user"
        assert context.message_history[0]["content"] == "Create a skill"
        assert context.message_history[1]["role"] == "assistant"

        # Second message
        response2, context = await manager.process_message("Format names", context)
        assert len(context.message_history) == 4
        assert context.message_history[2]["role"] == "user"
        assert context.message_history[2]["content"] == "Format names"

    @pytest.mark.asyncio
    async def test_error_handling_transitions_to_gathering_details(
        self, manager: ConversationManager, mock_gatherer: MagicMock
    ) -> None:
        """Should transition to GATHERING_DETAILS when exception occurs to allow recovery."""
        # Make gatherer raise an exception
        mock_gatherer.analyze_skill_requirements = AsyncMock(side_effect=Exception("Test error"))

        context = ConversationContext(state=ConversationState.GATHERING_PURPOSE)

        response, new_context = await manager.process_message("Format names", context)

        # Should transition to GATHERING_DETAILS for recovery, not ERROR
        assert new_context.state == ConversationState.GATHERING_DETAILS
        assert "error" in response.lower()
        # Should ask for more details to help recover
        assert "detail" in response.lower() or "rephrase" in response.lower()

    @pytest.mark.asyncio
    async def test_get_next_state_idle(self, manager: ConversationManager) -> None:
        """get_next_state should return correct next state for IDLE."""
        context = ConversationContext(state=ConversationState.IDLE)

        next_state = manager.get_next_state(context, "Create a skill")

        assert next_state == ConversationState.CHECKING_EXISTING

    @pytest.mark.asyncio
    async def test_get_next_state_confirming_spec_yes(self, manager: ConversationManager) -> None:
        """get_next_state should return GENERATING for confirmation."""
        context = ConversationContext(state=ConversationState.CONFIRMING_SPEC)

        next_state = manager.get_next_state(context, "yes")

        assert next_state == ConversationState.GENERATING

    @pytest.mark.asyncio
    async def test_get_next_state_confirming_spec_no(self, manager: ConversationManager) -> None:
        """get_next_state should return GATHERING_DETAILS for rejection."""
        context = ConversationContext(state=ConversationState.CONFIRMING_SPEC)

        next_state = manager.get_next_state(context, "no")

        assert next_state == ConversationState.GATHERING_DETAILS

    @pytest.mark.asyncio
    async def test_get_next_state_terminal_states(self, manager: ConversationManager) -> None:
        """get_next_state should return same state for terminal states."""
        terminal_states = [ConversationState.COMPLETED, ConversationState.ERROR]

        for state in terminal_states:
            context = ConversationContext(state=state)
            next_state = manager.get_next_state(context, "any message")
            assert next_state == state, f"Failed for terminal state: {state}"

    @pytest.mark.asyncio
    async def test_validate_generated_content_valid(self, manager: ConversationManager) -> None:
        """_validate_generated_content should return True for valid content."""
        context = ConversationContext(
            skill_name="test-skill",
            generated_content="---\nname: test-skill\ndescription: Test\n---\n\nContent here",
        )

        is_valid = manager._validate_generated_content(context)

        assert is_valid is True
        assert len(context.validation_errors) == 0

    @pytest.mark.asyncio
    async def test_validate_generated_content_missing_content(
        self, manager: ConversationManager
    ) -> None:
        """_validate_generated_content should return False for missing content."""
        context = ConversationContext(skill_name="test-skill", generated_content=None)

        is_valid = manager._validate_generated_content(context)

        assert is_valid is False
        assert len(context.validation_errors) > 0
        assert "No content generated" in context.validation_errors[0]

    @pytest.mark.asyncio
    async def test_validate_generated_content_missing_frontmatter(
        self, manager: ConversationManager
    ) -> None:
        """_validate_generated_content should return False for missing frontmatter."""
        context = ConversationContext(
            skill_name="test-skill",
            generated_content="Just content without frontmatter",
        )

        is_valid = manager._validate_generated_content(context)

        assert is_valid is False
        assert any("frontmatter" in error.lower() for error in context.validation_errors)

    @pytest.mark.asyncio
    async def test_validate_generated_content_excessive_lines(
        self, manager: ConversationManager
    ) -> None:
        """_validate_generated_content should return False for content over 500 lines."""
        long_content = "---\nname: test-skill\n---\n" + "\n".join(["Line"] * 600)
        context = ConversationContext(
            skill_name="test-skill",
            generated_content=long_content,
        )

        is_valid = manager._validate_generated_content(context)

        assert is_valid is False
        assert any("500 lines" in error for error in context.validation_errors)

    @pytest.mark.asyncio
    async def test_extract_requirements_updates_context(
        self, manager: ConversationManager, mock_gatherer: MagicMock
    ) -> None:
        """Should update context with extracted requirements."""
        mock_gatherer.extract_requirements = AsyncMock(
            return_value={
                "examples": ["example1", "example2"],
                "triggers": ["trigger1"],
                "workflow_steps": ["step1"],
            }
        )

        context = ConversationContext(state=ConversationState.GATHERING_DETAILS)

        response, new_context = await manager.process_message("Some details", context)

        assert "example1" in new_context.examples
        assert "example2" in new_context.examples
        assert "trigger1" in new_context.triggers
        assert "step1" in new_context.workflow_steps

    @pytest.mark.asyncio
    async def test_completed_state_message(self, manager: ConversationManager) -> None:
        """Should inform user that conversation is already completed."""
        context = ConversationContext(state=ConversationState.COMPLETED)

        response, new_context = await manager.process_message("More changes", context)

        assert "already completed" in response.lower()
        assert new_context.state == ConversationState.COMPLETED

    @pytest.mark.asyncio
    async def test_error_state_message(self, manager: ConversationManager) -> None:
        """Should allow recovery from ERROR state by accepting additional context."""
        context = ConversationContext(
            state=ConversationState.ERROR,
            skill_purpose="Format names",
            skill_name="name-formatter",
            skill_description="Format product names",
        )

        response, new_context = await manager.process_message(
            "Make it format names like PA -> Pro Analytics", context
        )

        # Should accept the additional context and try to regenerate
        assert "context" in response.lower() or "regenerate" in response.lower()
        # Should transition to GENERATING to try again with updated context
        assert new_context.state == ConversationState.GENERATING

    @pytest.mark.asyncio
    async def test_error_state_start_over(self, manager: ConversationManager) -> None:
        """Should allow user to start over from ERROR state."""
        context = ConversationContext(
            state=ConversationState.ERROR,
            skill_purpose="Old purpose",
            skill_name="old-skill",
        )

        response, new_context = await manager.process_message("start over", context)

        # Should reset and start fresh
        assert "start fresh" in response.lower() or "purpose" in response.lower()
        # Should transition to IDLE or ask for purpose
        assert new_context.state == ConversationState.IDLE
        # Context should be reset (except session_id)
        assert new_context.skill_purpose is None

    @pytest.mark.asyncio
    async def test_storage_layer_defaults_to_project(self, manager: ConversationManager) -> None:
        """Storage layer should default to 'project' for MVP."""
        context = ConversationContext(
            state=ConversationState.SELECTING_STORAGE,
            skill_name="test-skill",
            generated_content="---\nname: test-skill\ndescription: Test\n---\n\nContent",
        )

        response, new_context = await manager.process_message("", context)

        assert new_context.storage_layer == "project"
        assert new_context.state == ConversationState.SAVING
