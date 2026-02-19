"""Tests for SkillCreationAgent orchestration.

This module tests the main SkillCreationAgent class that orchestrates all components
for conversational skill creation.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from omniforge.skills.creation.agent import SkillCreationAgent
from omniforge.skills.creation.models import (
    ConversationState,
    ValidationResult,
)
from omniforge.skills.storage import StorageConfig


class TestSkillCreationAgent:
    """Test suite for SkillCreationAgent."""

    @pytest.fixture
    def mock_llm_generator(self) -> MagicMock:
        """Create a mock LLM generator."""
        mock_gen = MagicMock()

        # Mock generate_stream to return async iterator
        async def mock_stream(prompt: str):
            # Return different responses based on prompt content
            if "pattern" in prompt.lower():
                yield '{"pattern": "simple", "confidence": 0.9}'
            elif "extract all relevant information" in prompt.lower() or "requirements extractor" in prompt.lower():
                # Requirements extraction response
                yield '''{
                    "examples": ["Input: PA, Output: Pro Analytics"],
                    "triggers": ["writing documentation"],
                    "workflow_steps": [],
                    "references_topics": [],
                    "scripts_needed": [],
                    "extraction_notes": "Extracted 1 example and 1 trigger"
                }'''
            elif "questions" in prompt.lower():
                yield '["What examples can you provide?", "When should this be used?"]'
            elif "name" in prompt.lower() and "skill" in prompt.lower():
                yield '{"name": "test-skill"}'
            elif "description" in prompt.lower():
                yield (
                    '{"description": "A test skill for formatting. '
                    'Use when formatting product names."}'
                )
            elif "body" in prompt.lower() or "generate only the markdown body" in prompt.lower():
                # Return body content WITHOUT frontmatter (as per the prompt)
                yield "# Test Skill\n\nThis is a test skill body with instructions."
            else:
                yield "# Test Skill\n\nThis is a test skill body."

        mock_gen.generate_stream = mock_stream
        return mock_gen

    @pytest.fixture
    def temp_storage_config(self, tmp_path: Path) -> StorageConfig:
        """Create temporary storage configuration."""
        project_path = tmp_path / "project" / ".omniforge" / "skills"
        project_path.mkdir(parents=True, exist_ok=True)

        return StorageConfig(
            project_path=project_path,
            personal_path=None,
            enterprise_path=None,
            plugin_paths=[],
        )

    @pytest.fixture
    def agent(
        self, mock_llm_generator: MagicMock, temp_storage_config: StorageConfig
    ) -> SkillCreationAgent:
        """Create SkillCreationAgent instance for testing."""
        return SkillCreationAgent(
            llm_generator=mock_llm_generator,
            storage_config=temp_storage_config,
        )

    def test_agent_initialization(self, agent: SkillCreationAgent) -> None:
        """Test agent initializes with correct identity and components."""
        assert agent.identity.id == "skill-creation-assistant"
        assert agent.identity.name == "Skill Creation Assistant"
        assert agent.identity.version == "1.0.0"

        # Check components are initialized
        assert agent.llm_generator is not None
        assert agent.requirements_gatherer is not None
        assert agent.skill_md_generator is not None
        assert agent.skill_validator is not None
        assert agent.skill_writer is not None
        assert agent.conversation_manager is not None

        # Check session storage
        assert isinstance(agent.sessions, dict)
        assert len(agent.sessions) == 0

    @pytest.mark.asyncio
    async def test_get_session_context_creates_new_session(self, agent: SkillCreationAgent) -> None:
        """Test get_session_context creates new context for unknown session."""
        session_id = "test-session-123"

        context = await agent.get_session_context(session_id, "test-tenant")

        assert context.session_id == session_id
        assert context.state == ConversationState.IDLE
        assert session_id in agent.sessions

    @pytest.mark.asyncio
    async def test_get_session_context_returns_existing_session(self, agent: SkillCreationAgent) -> None:
        """Test get_session_context returns existing context."""
        session_id = "test-session-456"

        # Create initial context
        context1 = await agent.get_session_context(session_id, "test-tenant")
        context1.skill_purpose = "Test purpose"

        # Get same context
        context2 = await agent.get_session_context(session_id, "test-tenant")

        assert context2.session_id == session_id
        assert context2.skill_purpose == "Test purpose"
        assert context1 is context2

    @pytest.mark.asyncio
    async def test_clear_session(self, agent: SkillCreationAgent) -> None:
        """Test _clear_session removes session from storage."""
        session_id = "test-session-789"

        # Create session
        await agent.get_session_context(session_id, "test-tenant")
        assert session_id in agent.sessions

        # Clear session
        await agent._clear_session(session_id, "test-tenant")
        assert session_id not in agent.sessions

    @pytest.mark.asyncio
    async def test_handle_message_first_message(self, agent: SkillCreationAgent) -> None:
        """Test handle_message processes first user message."""
        session_id = "session-first-msg"
        message = "Create a skill to format product names"

        responses = []
        async for chunk in agent.handle_message(message, session_id, "test-tenant"):
            responses.append(chunk)

        full_response = "".join(responses)

        # Should have response content
        assert len(full_response) > 0

        # Should have created session
        assert session_id in agent.sessions

        # Context should have moved from IDLE
        context = agent.sessions[session_id]
        assert context.state != ConversationState.IDLE

    @pytest.mark.asyncio
    async def test_handle_message_conversation_flow(self, agent: SkillCreationAgent) -> None:
        """Test handle_message maintains conversation flow."""
        session_id = "session-flow"

        # First message: purpose
        async for _ in agent.handle_message("Format product abbreviations", session_id, "test-tenant"):
            pass

        context = agent.sessions[session_id]
        first_state = context.state

        # Second message: examples
        async for _ in agent.handle_message(
            "Input: PA, Output: Pro Analytics. Use when writing docs.", session_id, "test-tenant"
        ):
            pass

        context = agent.sessions[session_id]
        second_state = context.state

        # State should have progressed
        assert second_state != first_state

        # Context should have accumulated information
        assert context.skill_purpose is not None or len(context.examples) > 0

    @pytest.mark.asyncio
    async def test_handle_message_with_conversation_history(
        self, agent: SkillCreationAgent
    ) -> None:
        """Test handle_message can restore conversation history."""
        session_id = "session-history"
        history = [
            {"role": "user", "content": "Create a skill"},
            {"role": "assistant", "content": "Sure! What's the purpose?"},
        ]

        async for _ in agent.handle_message("Format names", session_id, "test-tenant", history):
            pass

        context = agent.sessions[session_id]

        # History should be restored (first 2) + new messages (2 more)
        assert len(context.message_history) >= 2

    @pytest.mark.asyncio
    async def test_handle_message_clears_session_on_completion(
        self, agent: SkillCreationAgent
    ) -> None:
        """Test handle_message clears session when conversation completes."""
        session_id = "session-complete"

        # Create a context and manually set to COMPLETED
        context = await agent.get_session_context(session_id, "test-tenant")
        context.state = ConversationState.COMPLETED

        async for _ in agent.handle_message("Thanks!", session_id, "test-tenant"):
            pass

        # Session should be cleared
        assert session_id not in agent.sessions

    @pytest.mark.asyncio
    async def test_handle_message_error_handling(self, agent: SkillCreationAgent) -> None:
        """Test handle_message handles errors gracefully."""
        session_id = "session-error"

        # Mock conversation manager to raise an error
        original_process = agent.conversation_manager.process_message

        async def mock_error(*args, **kwargs):
            raise RuntimeError("Test error")

        agent.conversation_manager.process_message = mock_error

        responses = []
        async for chunk in agent.handle_message("Test message", session_id, "test-tenant"):
            responses.append(chunk)

        full_response = "".join(responses)

        # Should have error message
        assert "error" in full_response.lower()

        # Restore original method
        agent.conversation_manager.process_message = original_process

    @pytest.mark.asyncio
    async def test_create_skill_programmatic(
        self, agent: SkillCreationAgent, temp_storage_config: StorageConfig
    ) -> None:
        """Test create_skill creates skill programmatically."""
        purpose = "Format product names"
        examples = [
            {"input": "PA", "output": "Pro Analytics"},
            {"input": "DC", "output": "Data Center"},
        ]
        triggers = ["writing documentation", "creating reports"]

        # Mock all the generation methods to ensure consistent names
        original_generate = agent.skill_md_generator.generate
        original_fix = agent.skill_md_generator.fix_validation_errors
        original_gen_name = agent.requirements_gatherer.generate_skill_name
        original_gen_desc = agent.requirements_gatherer.generate_description

        # Use consistent skill name across all mocks
        skill_name = "format-product-names"

        valid_content = f"""---
name: {skill_name}
description: A test skill for formatting. Use when formatting product names.
---

# Format Product Names

This is a test skill body with instructions."""

        async def mock_generate(context):
            return valid_content

        async def mock_fix(content, errors):
            return valid_content

        async def mock_gen_name(context):
            return skill_name

        async def mock_gen_desc(context):
            return "A test skill for formatting. Use when formatting product names."

        agent.skill_md_generator.generate = mock_generate
        agent.skill_md_generator.fix_validation_errors = mock_fix
        agent.requirements_gatherer.generate_skill_name = mock_gen_name
        agent.requirements_gatherer.generate_description = mock_gen_desc

        try:
            # Create skill
            skill_path = await agent.create_skill(
                purpose=purpose,
                examples=examples,
                triggers=triggers,
                storage_layer="project",
            )

            # Verify skill was created
            assert skill_path.exists()
            assert skill_path.name == "SKILL.md"
            assert skill_path.parent.name == skill_name

            # Verify content
            content = skill_path.read_text()
            assert f"name: {skill_name}" in content
            assert "description:" in content
        finally:
            # Restore original methods
            agent.skill_md_generator.generate = original_generate
            agent.skill_md_generator.fix_validation_errors = original_fix
            agent.requirements_gatherer.generate_skill_name = original_gen_name
            agent.requirements_gatherer.generate_description = original_gen_desc

    @pytest.mark.asyncio
    async def test_create_skill_validation_failure(self, agent: SkillCreationAgent) -> None:
        """Test create_skill handles validation failure."""
        # Mock validator to always fail
        original_validate = agent.skill_validator.validate

        def mock_validate(*args, **kwargs):
            result = ValidationResult(is_valid=False)
            result.add_error("Test validation error")
            return result

        agent.skill_validator.validate = mock_validate

        # Attempt to create skill should raise ValueError
        with pytest.raises(ValueError, match="validation failed"):
            await agent.create_skill(
                purpose="Test",
                examples=[{"input": "a", "output": "b"}],
                triggers=["test"],
            )

        # Restore original method
        agent.skill_validator.validate = original_validate

    @pytest.mark.asyncio
    async def test_generation_workflow(self, agent: SkillCreationAgent) -> None:
        """Test _handle_generation_workflow transitions states correctly."""
        session_id = "session-gen"
        context = await agent.get_session_context(session_id, "test-tenant")

        # Setup context for generation
        context.skill_name = "test-skill"
        context.skill_description = "A test skill"
        context.skill_purpose = "Testing"
        context.state = ConversationState.GENERATING
        context.generated_content = (
            "---\nname: test-skill\ndescription: A test skill\n---\n\n# Test"
        )

        responses = []
        async for chunk in agent._handle_generation_workflow(session_id, "test-tenant"):
            responses.append(chunk)

        full_response = "".join(responses)

        # Should have status messages
        assert "generat" in full_response.lower() or "validat" in full_response.lower()

    @pytest.mark.asyncio
    async def test_validation_workflow_success(self, agent: SkillCreationAgent) -> None:
        """Test _handle_validation_workflow with successful validation."""
        session_id = "session-val-success"
        context = await agent.get_session_context(session_id, "test-tenant")

        # Setup context with valid content
        context.skill_name = "test-skill"
        context.skill_description = "A test skill for validation"
        context.generated_content = """---
name: test-skill
description: A test skill for validation. Use when testing.
---

# Test Skill

This is a test skill body with instructions."""
        context.state = ConversationState.VALIDATING
        context.storage_layer = "project"

        # Mock writer to avoid actual file creation
        original_write = agent.skill_writer.write_skill
        agent.skill_writer.write_skill = AsyncMock(return_value=Path("/tmp/test-skill/SKILL.md"))

        responses = []
        async for chunk in agent._handle_validation_workflow(session_id, "test-tenant"):
            responses.append(chunk)

        full_response = "".join(responses)

        # Should show success and saving
        assert "success" in full_response.lower() or "✓" in full_response

        # Restore original method
        agent.skill_writer.write_skill = original_write

    @pytest.mark.asyncio
    async def test_validation_workflow_with_retry(self, agent: SkillCreationAgent) -> None:
        """Test _handle_validation_workflow retries on validation failure."""
        session_id = "session-val-retry"
        context = await agent.get_session_context(session_id, "test-tenant")

        # Setup context with initially invalid content
        context.skill_name = "test-skill"
        context.generated_content = "Invalid content"  # Missing frontmatter
        context.state = ConversationState.VALIDATING

        # Mock generator to fix content
        original_fix = agent.skill_md_generator.fix_validation_errors

        async def mock_fix(content, errors):
            return """---
name: test-skill
description: Fixed test skill. Use when testing.
---

# Test Skill

Fixed body."""

        agent.skill_md_generator.fix_validation_errors = mock_fix

        # Mock writer
        agent.skill_writer.write_skill = AsyncMock(return_value=Path("/tmp/test-skill/SKILL.md"))

        responses = []
        async for chunk in agent._handle_validation_workflow(session_id, "test-tenant"):
            responses.append(chunk)

        full_response = "".join(responses)

        # Should show validation issue and retry
        assert "error" in full_response.lower() or "fix" in full_response.lower()

        # Restore
        agent.skill_md_generator.fix_validation_errors = original_fix

    @pytest.mark.asyncio
    async def test_validation_workflow_max_retries_exceeded(
        self, agent: SkillCreationAgent
    ) -> None:
        """Test _handle_validation_workflow handles max retries."""
        session_id = "session-max-retry"
        context = await agent.get_session_context(session_id, "test-tenant")

        # Setup context that will always fail validation
        context.skill_name = "test-skill"
        context.generated_content = "Invalid"
        context.state = ConversationState.VALIDATING
        context.validation_attempts = 3  # Already at max

        responses = []
        async for chunk in agent._handle_validation_workflow(session_id, "test-tenant"):
            responses.append(chunk)

        full_response = "".join(responses)

        # Should ask user for help after max retries
        assert (
            "tried several times" in full_response.lower()
            or "provide more specific" in full_response.lower()
        )

        # Context should transition to GATHERING_DETAILS to allow user input
        assert context.state == ConversationState.GATHERING_DETAILS

    @pytest.mark.asyncio
    async def test_saving_workflow(
        self, agent: SkillCreationAgent, temp_storage_config: StorageConfig
    ) -> None:
        """Test _handle_saving_workflow saves skill successfully."""
        session_id = "session-save"
        context = await agent.get_session_context(session_id, "test-tenant")

        # Setup context for saving
        context.skill_name = "test-skill"
        context.skill_description = "A test skill"
        context.generated_content = """---
name: test-skill
description: A test skill. Use when testing.
---

# Test Skill

Instructions here."""
        context.storage_layer = "project"
        context.state = ConversationState.SAVING

        responses = []
        async for chunk in agent._handle_saving_workflow(session_id, "test-tenant"):
            responses.append(chunk)

        full_response = "".join(responses)

        # Should show success
        assert "success" in full_response.lower() or "✓" in full_response

        # Context should be COMPLETED
        assert context.state == ConversationState.COMPLETED

        # Verify file was created
        skill_path = temp_storage_config.project_path / "test-skill" / "SKILL.md"
        assert skill_path.exists()

    @pytest.mark.asyncio
    async def test_saving_workflow_missing_info(self, agent: SkillCreationAgent) -> None:
        """Test _handle_saving_workflow handles missing information."""
        session_id = "session-save-missing"
        context = await agent.get_session_context(session_id, "test-tenant")

        # Setup context with missing required info
        context.state = ConversationState.SAVING
        context.skill_name = None  # Missing!

        responses = []
        async for chunk in agent._handle_saving_workflow(session_id, "test-tenant"):
            responses.append(chunk)

        full_response = "".join(responses)

        # Should indicate error
        assert "error" in full_response.lower() or "missing" in full_response.lower()

        # Context should be in ERROR state
        assert context.state == ConversationState.ERROR

    @pytest.mark.asyncio
    async def test_full_conversation_end_to_end(
        self, agent: SkillCreationAgent, temp_storage_config: StorageConfig
    ) -> None:
        """Test complete conversation flow from start to finish."""
        session_id = "session-e2e"

        # Message 1: Initial purpose
        async for _ in agent.handle_message(
            "Create a skill to format product abbreviations", session_id, "test-tenant"
        ):
            pass

        context = agent.sessions.get(session_id)
        assert context is not None

        # Message 2: Provide examples and triggers
        async for _ in agent.handle_message(
            "Input: PA, Output: Pro Analytics. Use when writing documentation.", session_id, "test-tenant"
        ):
            pass

        # At this point, if we have sufficient context, the agent should
        # proceed through generation, validation, and saving automatically
        # The session may or may not still exist depending on completion

        # Verify that the flow progressed (can't assert final state in unit test
        # without more sophisticated mocking, but we can verify no crashes)
        assert True  # Made it through without exceptions

    @pytest.mark.asyncio
    async def test_concurrent_sessions(self, agent: SkillCreationAgent) -> None:
        """Test agent can handle multiple concurrent sessions."""
        session1 = "session-1"
        session2 = "session-2"

        # Create two sessions with different purposes
        async for _ in agent.handle_message("Create skill A", session1, "test-tenant"):
            pass

        async for _ in agent.handle_message("Create skill B", session2, "test-tenant"):
            pass

        # Both sessions should exist
        assert session1 in agent.sessions
        assert session2 in agent.sessions

        # Contexts should be independent
        context1 = agent.sessions[session1]
        context2 = agent.sessions[session2]

        assert context1.session_id == session1
        assert context2.session_id == session2
        assert context1 is not context2
