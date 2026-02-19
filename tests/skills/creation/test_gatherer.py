"""Tests for RequirementsGatherer class.

This module tests the requirements gathering functionality including capability analysis,
question generation, requirement extraction, and context sufficiency checking.
"""

from unittest.mock import MagicMock

import pytest

from omniforge.chat.llm_generator import LLMResponseGenerator
from omniforge.skills.creation.gatherer import RequirementsGatherer
from omniforge.skills.creation.models import ConversationContext, SkillCapabilities


class TestAnalyzeSkillRequirements:
    """Tests for skill requirements analysis and capability detection."""

    @pytest.mark.asyncio
    async def test_analyze_simple_skill_capabilities(self) -> None:
        """Should analyze capabilities for simple formatting task."""
        # Setup
        mock_llm = MagicMock(spec=LLMResponseGenerator)
        mock_llm.model = "test-model"
        mock_llm.api_key = "test-key"
        mock_llm.api_base = None

        # Mock streaming response
        async def mock_stream(prompt: str) -> list[str]:
            response = """{
                "capabilities": {
                    "needs_file_operations": false,
                    "needs_external_knowledge": false,
                    "needs_script_execution": false,
                    "needs_multi_step_workflow": false
                },
                "suggested_tools": [],
                "suggested_assets": [],
                "suggested_references": [],
                "suggested_scripts": [],
                "confidence": 0.9,
                "reasoning": "Simple text transformation task"
            }"""
            for char in response:
                yield char

        mock_llm.generate_stream = mock_stream

        gatherer = RequirementsGatherer(mock_llm)
        context = ConversationContext()

        # Execute
        capabilities = await gatherer.analyze_skill_requirements("Format product names", context)

        # Verify
        assert capabilities.needs_file_operations is False
        assert capabilities.needs_external_knowledge is False
        assert capabilities.needs_script_execution is False
        assert capabilities.needs_multi_step_workflow is False
        assert capabilities.confidence > 0.8

    @pytest.mark.asyncio
    async def test_analyze_workflow_capabilities(self) -> None:
        """Should detect multi-step workflow capabilities."""
        # Setup
        mock_llm = MagicMock(spec=LLMResponseGenerator)
        mock_llm.model = "test-model"
        mock_llm.api_key = "test-key"
        mock_llm.api_base = None

        async def mock_stream(prompt: str) -> list[str]:
            response = """{
                "capabilities": {
                    "needs_file_operations": true,
                    "needs_external_knowledge": false,
                    "needs_script_execution": false,
                    "needs_multi_step_workflow": true
                },
                "suggested_tools": ["Read", "Write"],
                "suggested_assets": [],
                "suggested_references": [],
                "suggested_scripts": [],
                "confidence": 0.85,
                "reasoning": "Multi-step process with file operations"
            }"""
            for char in response:
                yield char

        mock_llm.generate_stream = mock_stream

        gatherer = RequirementsGatherer(mock_llm)
        context = ConversationContext()

        # Execute
        capabilities = await gatherer.analyze_skill_requirements(
            "Process approval workflow with multiple steps", context
        )

        # Verify
        assert capabilities.needs_multi_step_workflow is True
        assert capabilities.needs_file_operations is True
        assert "Read" in capabilities.suggested_tools or "Write" in capabilities.suggested_tools

    @pytest.mark.asyncio
    async def test_analyze_reference_knowledge_capabilities(self) -> None:
        """Should detect needs for external knowledge and references."""
        # Setup
        mock_llm = MagicMock(spec=LLMResponseGenerator)
        mock_llm.model = "test-model"
        mock_llm.api_key = "test-key"
        mock_llm.api_base = None

        async def mock_stream(prompt: str) -> list[str]:
            response = """{
                "capabilities": {
                    "needs_file_operations": true,
                    "needs_external_knowledge": true,
                    "needs_script_execution": false,
                    "needs_multi_step_workflow": false
                },
                "suggested_tools": ["Read"],
                "suggested_assets": [],
                "suggested_references": [
                    {"name": "brand-guidelines.md", "purpose": "Brand guidelines"},
                    {"name": "style-guide.md", "purpose": "Style guide"}
                ],
                "suggested_scripts": [],
                "confidence": 0.8,
                "reasoning": "Requires reference documentation"
            }"""
            for char in response:
                yield char

        mock_llm.generate_stream = mock_stream

        gatherer = RequirementsGatherer(mock_llm)
        context = ConversationContext()

        # Execute
        capabilities = await gatherer.analyze_skill_requirements(
            "Answer questions about brand guidelines", context
        )

        # Verify
        assert capabilities.needs_external_knowledge is True
        assert len(capabilities.suggested_references) > 0

    @pytest.mark.asyncio
    async def test_analyze_script_execution_capabilities(self) -> None:
        """Should detect needs for script execution."""
        # Setup
        mock_llm = MagicMock(spec=LLMResponseGenerator)
        mock_llm.model = "test-model"
        mock_llm.api_key = "test-key"
        mock_llm.api_base = None

        async def mock_stream(prompt: str) -> list[str]:
            response = """{
                "capabilities": {
                    "needs_file_operations": false,
                    "needs_external_knowledge": false,
                    "needs_script_execution": true,
                    "needs_multi_step_workflow": true
                },
                "suggested_tools": ["Bash(deploy:*)"],
                "suggested_assets": [],
                "suggested_references": [],
                "suggested_scripts": [
                    {"name": "deploy.sh", "purpose": "Deploy application", "language": "bash"}
                ],
                "confidence": 0.9,
                "reasoning": "Requires script execution for deployment"
            }"""
            for char in response:
                yield char

        mock_llm.generate_stream = mock_stream

        gatherer = RequirementsGatherer(mock_llm)
        context = ConversationContext()

        # Execute
        capabilities = await gatherer.analyze_skill_requirements(
            "Deploy application to production", context
        )

        # Verify
        assert capabilities.needs_script_execution is True
        assert len(capabilities.suggested_scripts) > 0

    @pytest.mark.asyncio
    async def test_analyze_with_markdown_json(self) -> None:
        """Should parse JSON from markdown code blocks."""
        # Setup
        mock_llm = MagicMock(spec=LLMResponseGenerator)
        mock_llm.model = "test-model"
        mock_llm.api_key = "test-key"
        mock_llm.api_base = None

        async def mock_stream(prompt: str) -> list[str]:
            response = """```json
{
    "capabilities": {
        "needs_file_operations": false,
        "needs_external_knowledge": false,
        "needs_script_execution": false,
        "needs_multi_step_workflow": false
    },
    "suggested_tools": [],
    "suggested_assets": [],
    "suggested_references": [],
    "suggested_scripts": [],
    "confidence": 0.9,
    "reasoning": "Simple task"
}
```"""
            for char in response:
                yield char

        mock_llm.generate_stream = mock_stream

        gatherer = RequirementsGatherer(mock_llm)
        context = ConversationContext()

        # Execute
        capabilities = await gatherer.analyze_skill_requirements("Format text", context)

        # Verify
        assert capabilities.confidence > 0.8

    @pytest.mark.asyncio
    async def test_analyze_fallback_on_error(self) -> None:
        """Should fallback to default capabilities if analysis fails."""
        # Setup
        mock_llm = MagicMock(spec=LLMResponseGenerator)
        mock_llm.model = "test-model"
        mock_llm.api_key = "test-key"
        mock_llm.api_base = None

        async def mock_stream(prompt: str) -> list[str]:
            response = "Invalid JSON response"
            for char in response:
                yield char

        mock_llm.generate_stream = mock_stream

        gatherer = RequirementsGatherer(mock_llm)
        context = ConversationContext()

        # Execute
        capabilities = await gatherer.analyze_skill_requirements("Some task", context)

        # Verify - should use defaults
        assert capabilities.needs_file_operations is False
        assert capabilities.needs_external_knowledge is False
        assert capabilities.needs_script_execution is False
        assert capabilities.needs_multi_step_workflow is False
        assert capabilities.confidence < 0.5  # Low confidence on fallback


class TestGenerateClarifyingQuestions:
    """Tests for clarifying question generation."""

    @pytest.mark.asyncio
    async def test_generate_questions_for_simple_skill(self) -> None:
        """Should generate relevant questions for simple formatting skill."""
        # Setup
        mock_llm = MagicMock(spec=LLMResponseGenerator)
        mock_llm.model = "test-model"
        mock_llm.api_key = "test-key"
        mock_llm.api_base = None

        gatherer = RequirementsGatherer(mock_llm)

        capabilities = SkillCapabilities(
            needs_file_operations=False,
            needs_external_knowledge=False,
            needs_script_execution=False,
            needs_multi_step_workflow=False
        )
        context = ConversationContext(
            skill_purpose="Format product names",
            skill_capabilities=capabilities
        )

        # Execute
        questions = await gatherer.generate_clarifying_questions(context)

        # Verify
        assert len(questions) >= 2
        assert len(questions) <= 3
        assert all(isinstance(q, str) for q in questions)
        assert all(len(q) > 0 for q in questions)

    @pytest.mark.asyncio
    async def test_generate_questions_uses_llm_when_context_available(self) -> None:
        """Should use LLM for contextual questions when partial context exists."""
        # Setup
        mock_llm = MagicMock(spec=LLMResponseGenerator)
        mock_llm.model = "test-model"
        mock_llm.api_key = "test-key"
        mock_llm.api_base = None

        async def mock_stream(prompt: str) -> list[str]:
            response = '["What edge cases should be handled?", "Any format preferences?"]'
            for char in response:
                yield char

        mock_llm.generate_stream = mock_stream

        gatherer = RequirementsGatherer(mock_llm)

        capabilities = SkillCapabilities(
            needs_file_operations=False,
            needs_external_knowledge=False,
            needs_script_execution=False,
            needs_multi_step_workflow=False
        )
        context = ConversationContext(
            skill_purpose="Format names",
            skill_capabilities=capabilities,
            examples=["PA -> Pro Analytics"],  # Has some context
        )

        # Execute
        questions = await gatherer.generate_clarifying_questions(context)

        # Verify
        assert len(questions) >= 2

    @pytest.mark.asyncio
    async def test_generate_questions_fallback_on_error(self) -> None:
        """Should fallback to templates if LLM fails."""
        # Setup
        mock_llm = MagicMock(spec=LLMResponseGenerator)
        mock_llm.model = "test-model"
        mock_llm.api_key = "test-key"
        mock_llm.api_base = None

        async def mock_stream(prompt: str) -> list[str]:
            response = "Invalid response"
            for char in response:
                yield char

        mock_llm.generate_stream = mock_stream

        gatherer = RequirementsGatherer(mock_llm)

        capabilities = SkillCapabilities(
            needs_file_operations=False,
            needs_external_knowledge=False,
            needs_script_execution=False,
            needs_multi_step_workflow=False
        )
        context = ConversationContext(skill_capabilities=capabilities)

        # Execute
        questions = await gatherer.generate_clarifying_questions(context)

        # Verify - should fallback to templates
        assert len(questions) >= 2
        assert all(isinstance(q, str) for q in questions)


class TestExtractRequirements:
    """Tests for requirement extraction from user responses."""

    @pytest.mark.asyncio
    async def test_extract_examples_from_input_output_format(self) -> None:
        """Should extract examples from 'input: X, output: Y' format."""
        # Setup
        mock_llm = MagicMock(spec=LLMResponseGenerator)
        mock_llm.model = "test-model"
        mock_llm.api_key = "test-key"
        mock_llm.api_base = None

        async def mock_stream(prompt: str) -> list[str]:
            response = """{
                "examples": ["Input: PA, Output: Pro Analytics", "Input: CE, Output: Cloud Engine"],
                "triggers": [],
                "workflow_steps": [],
                "references_topics": [],
                "scripts_needed": [],
                "extraction_notes": "Extracted 2 examples"
            }"""
            for char in response:
                yield char

        mock_llm.generate_stream = mock_stream

        gatherer = RequirementsGatherer(mock_llm)
        context = ConversationContext(skill_capabilities=SkillCapabilities(needs_file_operations=False, needs_external_knowledge=False, needs_script_execution=False, needs_multi_step_workflow=False))

        user_response = "Input: PA, Output: Pro Analytics. Input: CE, Output: Cloud Engine"

        # Execute
        extracted = await gatherer.extract_requirements(user_response, context)

        # Verify
        assert "examples" in extracted
        assert len(extracted["examples"]) >= 2
        assert any("PA" in ex for ex in extracted["examples"])

    @pytest.mark.asyncio
    async def test_extract_examples_from_arrow_format(self) -> None:
        """Should extract examples from 'X -> Y' format."""
        # Setup
        mock_llm = MagicMock(spec=LLMResponseGenerator)
        mock_llm.model = "test-model"
        mock_llm.api_key = "test-key"
        mock_llm.api_base = None

        async def mock_stream(prompt: str) -> list[str]:
            response = """{
                "examples": ["Input: PA, Output: Pro Analytics", "Input: CE, Output: Cloud Engine"],
                "triggers": [],
                "workflow_steps": [],
                "references_topics": [],
                "scripts_needed": [],
                "extraction_notes": "Extracted 2 examples from arrow format"
            }"""
            for char in response:
                yield char

        mock_llm.generate_stream = mock_stream

        gatherer = RequirementsGatherer(mock_llm)
        context = ConversationContext(skill_capabilities=SkillCapabilities(needs_file_operations=False, needs_external_knowledge=False, needs_script_execution=False, needs_multi_step_workflow=False))

        user_response = "PA -> Pro Analytics, CE -> Cloud Engine"

        # Execute
        extracted = await gatherer.extract_requirements(user_response, context)

        # Verify
        assert "examples" in extracted
        assert len(extracted["examples"]) >= 2

    @pytest.mark.asyncio
    async def test_extract_triggers_from_when_phrases(self) -> None:
        """Should extract triggers from 'when' phrases."""
        # Setup
        mock_llm = MagicMock(spec=LLMResponseGenerator)
        mock_llm.model = "test-model"
        mock_llm.api_key = "test-key"
        mock_llm.api_base = None

        async def mock_stream(prompt: str) -> list[str]:
            response = """{
                "examples": [],
                "triggers": ["writing documentation", "creating presentations"],
                "workflow_steps": [],
                "references_topics": [],
                "scripts_needed": [],
                "extraction_notes": "Extracted 2 usage triggers"
            }"""
            for char in response:
                yield char

        mock_llm.generate_stream = mock_stream

        gatherer = RequirementsGatherer(mock_llm)
        context = ConversationContext(skill_capabilities=SkillCapabilities(needs_file_operations=False, needs_external_knowledge=False, needs_script_execution=False, needs_multi_step_workflow=False))

        user_response = "Use when writing documentation. Also whenever creating presentations."

        # Execute
        extracted = await gatherer.extract_requirements(user_response, context)

        # Verify
        assert "triggers" in extracted
        assert len(extracted["triggers"]) >= 1
        assert any("writing documentation" in t for t in extracted["triggers"])

    @pytest.mark.asyncio
    async def test_extract_workflow_steps_for_workflow_pattern(self) -> None:
        """Should extract workflow steps for WORKFLOW pattern."""
        # Setup
        mock_llm = MagicMock(spec=LLMResponseGenerator)
        mock_llm.model = "test-model"
        mock_llm.api_key = "test-key"
        mock_llm.api_base = None

        async def mock_stream(prompt: str) -> list[str]:
            response = """{
                "examples": [],
                "triggers": [],
                "workflow_steps": ["Validate input", "Process data", "Generate report"],
                "references_topics": [],
                "scripts_needed": [],
                "extraction_notes": "Extracted 3-step workflow"
            }"""
            for char in response:
                yield char

        mock_llm.generate_stream = mock_stream

        gatherer = RequirementsGatherer(mock_llm)
        context = ConversationContext(skill_capabilities=SkillCapabilities(needs_file_operations=False, needs_external_knowledge=False, needs_script_execution=False, needs_multi_step_workflow=True))

        user_response = """1. Validate input
2. Process data
3. Generate report"""

        # Execute
        extracted = await gatherer.extract_requirements(user_response, context)

        # Verify
        assert "workflow_steps" in extracted
        assert len(extracted["workflow_steps"]) >= 3

    @pytest.mark.asyncio
    async def test_extract_references_for_reference_pattern(self) -> None:
        """Should extract reference topics for REFERENCE pattern."""
        # Setup
        mock_llm = MagicMock(spec=LLMResponseGenerator)
        mock_llm.model = "test-model"
        mock_llm.api_key = "test-key"
        mock_llm.api_base = None

        async def mock_stream(prompt: str) -> list[str]:
            response = """{
                "examples": [],
                "triggers": [],
                "workflow_steps": [],
                "references_topics": ["brand guidelines", "API reference"],
                "scripts_needed": [],
                "extraction_notes": "Extracted 2 reference topics"
            }"""
            for char in response:
                yield char

        mock_llm.generate_stream = mock_stream

        gatherer = RequirementsGatherer(mock_llm)
        context = ConversationContext(skill_capabilities=SkillCapabilities(needs_file_operations=True, needs_external_knowledge=True, needs_script_execution=False, needs_multi_step_workflow=False))

        user_response = "Needs documentation for brand guidelines and API reference"

        # Execute
        extracted = await gatherer.extract_requirements(user_response, context)

        # Verify
        assert "references_topics" in extracted

    @pytest.mark.asyncio
    async def test_extract_scripts_for_script_pattern(self) -> None:
        """Should extract scripts for SCRIPT pattern."""
        # Setup
        mock_llm = MagicMock(spec=LLMResponseGenerator)
        mock_llm.model = "test-model"
        mock_llm.api_key = "test-key"
        mock_llm.api_base = None

        async def mock_stream(prompt: str) -> list[str]:
            response = """{
                "examples": [],
                "triggers": [],
                "workflow_steps": [],
                "references_topics": [],
                "scripts_needed": ["npm run deploy", "pm2 restart app"],
                "extraction_notes": "Extracted 2 deployment scripts"
            }"""
            for char in response:
                yield char

        mock_llm.generate_stream = mock_stream

        gatherer = RequirementsGatherer(mock_llm)
        context = ConversationContext(skill_capabilities=SkillCapabilities(needs_file_operations=False, needs_external_knowledge=False, needs_script_execution=True, needs_multi_step_workflow=False))

        user_response = """Run:
$ npm run deploy
$ pm2 restart app"""

        # Execute
        extracted = await gatherer.extract_requirements(user_response, context)

        # Verify
        assert "scripts_needed" in extracted
        assert len(extracted["scripts_needed"]) >= 2

    @pytest.mark.asyncio
    async def test_extract_requirements_handles_llm_failure(self) -> None:
        """Should return empty dict if LLM extraction fails."""
        # Setup
        mock_llm = MagicMock(spec=LLMResponseGenerator)
        mock_llm.model = "test-model"
        mock_llm.api_key = "test-key"
        mock_llm.api_base = None

        async def mock_stream(prompt: str) -> list[str]:
            response = "Invalid JSON response"
            for char in response:
                yield char

        mock_llm.generate_stream = mock_stream

        gatherer = RequirementsGatherer(mock_llm)
        context = ConversationContext(skill_capabilities=SkillCapabilities(needs_file_operations=False, needs_external_knowledge=False, needs_script_execution=False, needs_multi_step_workflow=False))

        # Execute
        extracted = await gatherer.extract_requirements("Some input", context)

        # Verify - should return empty dict on error
        assert isinstance(extracted, dict)
        assert len(extracted) == 0

    @pytest.mark.asyncio
    async def test_extract_requirements_with_markdown_json(self) -> None:
        """Should parse JSON from markdown code blocks."""
        # Setup
        mock_llm = MagicMock(spec=LLMResponseGenerator)
        mock_llm.model = "test-model"
        mock_llm.api_key = "test-key"
        mock_llm.api_base = None

        async def mock_stream(prompt: str) -> list[str]:
            response = """```json
{
    "examples": ["Input: X, Output: Y"],
    "triggers": ["when needed"],
    "workflow_steps": [],
    "references_topics": [],
    "scripts_needed": [],
    "extraction_notes": "Test"
}
```"""
            for char in response:
                yield char

        mock_llm.generate_stream = mock_stream

        gatherer = RequirementsGatherer(mock_llm)
        context = ConversationContext(skill_capabilities=SkillCapabilities(needs_file_operations=False, needs_external_knowledge=False, needs_script_execution=False, needs_multi_step_workflow=False))

        # Execute
        extracted = await gatherer.extract_requirements("Test input", context)

        # Verify
        assert "examples" in extracted
        assert "triggers" in extracted


class TestHasSufficientContext:
    """Tests for context sufficiency checking."""

    def test_sufficient_context_with_examples_and_triggers(self) -> None:
        """Should return True when context has examples and triggers."""
        # Setup
        mock_llm = MagicMock(spec=LLMResponseGenerator)
        gatherer = RequirementsGatherer(mock_llm)

        context = ConversationContext(
            skill_purpose="Format product names",
            skill_capabilities=SkillCapabilities(needs_file_operations=False, needs_external_knowledge=False, needs_script_execution=False, needs_multi_step_workflow=False),
            examples=["PA -> Pro Analytics"],
            triggers=["writing documentation"],
        )

        # Execute & Verify
        assert gatherer.has_sufficient_context(context) is True

    def test_sufficient_context_with_only_examples(self) -> None:
        """Should return True when context has examples (even without triggers)."""
        # Setup
        mock_llm = MagicMock(spec=LLMResponseGenerator)
        gatherer = RequirementsGatherer(mock_llm)

        context = ConversationContext(
            skill_purpose="Format names",
            skill_capabilities=SkillCapabilities(needs_file_operations=False, needs_external_knowledge=False, needs_script_execution=False, needs_multi_step_workflow=False),
            examples=["PA -> Pro Analytics"],
        )

        # Execute & Verify
        assert gatherer.has_sufficient_context(context) is True

    def test_sufficient_context_with_only_triggers(self) -> None:
        """Should return True when context has triggers (even without examples)."""
        # Setup
        mock_llm = MagicMock(spec=LLMResponseGenerator)
        gatherer = RequirementsGatherer(mock_llm)

        context = ConversationContext(
            skill_purpose="Format names",
            skill_capabilities=SkillCapabilities(needs_file_operations=False, needs_external_knowledge=False, needs_script_execution=False, needs_multi_step_workflow=False),
            triggers=["writing docs"],
        )

        # Execute & Verify
        assert gatherer.has_sufficient_context(context) is True

    def test_insufficient_context_missing_purpose(self) -> None:
        """Should return False when purpose is missing."""
        # Setup
        mock_llm = MagicMock(spec=LLMResponseGenerator)
        gatherer = RequirementsGatherer(mock_llm)

        context = ConversationContext(
            skill_capabilities=SkillCapabilities(needs_file_operations=False, needs_external_knowledge=False, needs_script_execution=False, needs_multi_step_workflow=False),
            examples=["PA -> Pro Analytics"],
            triggers=["writing docs"],
        )

        # Execute & Verify
        assert gatherer.has_sufficient_context(context) is False

    def test_insufficient_context_missing_examples_and_triggers(self) -> None:
        """Should return False when both examples and triggers are missing."""
        # Setup
        mock_llm = MagicMock(spec=LLMResponseGenerator)
        gatherer = RequirementsGatherer(mock_llm)

        context = ConversationContext(
            skill_purpose="Format names", skill_capabilities=SkillCapabilities(needs_file_operations=False, needs_external_knowledge=False, needs_script_execution=False, needs_multi_step_workflow=False)
        )

        # Execute & Verify
        assert gatherer.has_sufficient_context(context) is False

    def test_sufficient_context_workflow_with_steps_and_triggers(self) -> None:
        """Should return True for workflow with steps and triggers."""
        # Setup
        mock_llm = MagicMock(spec=LLMResponseGenerator)
        gatherer = RequirementsGatherer(mock_llm)

        context = ConversationContext(
            skill_purpose="Process approval",
            skill_capabilities=SkillCapabilities(needs_file_operations=False, needs_external_knowledge=False, needs_script_execution=False, needs_multi_step_workflow=True),
            workflow_steps=["Validate", "Approve", "Notify"],
            triggers=["new request"],
        )

        # Execute & Verify
        assert gatherer.has_sufficient_context(context) is True

    def test_insufficient_context_workflow_missing_steps(self) -> None:
        """Should return False for workflow without sufficient steps."""
        # Setup
        mock_llm = MagicMock(spec=LLMResponseGenerator)
        gatherer = RequirementsGatherer(mock_llm)

        context = ConversationContext(
            skill_purpose="Process approval",
            skill_capabilities=SkillCapabilities(needs_file_operations=False, needs_external_knowledge=False, needs_script_execution=False, needs_multi_step_workflow=True),
            workflow_steps=["Validate"],  # Only 1 step, needs at least 2
            triggers=["new request"],
        )

        # Execute & Verify
        assert gatherer.has_sufficient_context(context) is False


class TestGenerateSkillName:
    """Tests for skill name generation."""

    @pytest.mark.asyncio
    async def test_generate_valid_kebab_case_name(self) -> None:
        """Should generate valid kebab-case skill name."""
        # Setup
        mock_llm = MagicMock(spec=LLMResponseGenerator)
        mock_llm.model = "test-model"
        mock_llm.api_key = "test-key"
        mock_llm.api_base = None

        async def mock_stream(prompt: str) -> list[str]:
            response = '{"name": "formatting-product-names", "alternatives": ["product-formatter"]}'
            for char in response:
                yield char

        mock_llm.generate_stream = mock_stream

        gatherer = RequirementsGatherer(mock_llm)

        context = ConversationContext(
            skill_purpose="Format product names",
            skill_capabilities=SkillCapabilities(needs_file_operations=False, needs_external_knowledge=False, needs_script_execution=False, needs_multi_step_workflow=False),
            examples=["PA -> Pro Analytics"],
        )

        # Execute
        name = await gatherer.generate_skill_name(context)

        # Verify - either LLM name or fallback from purpose
        assert name.islower()
        assert "-" in name or name.isalpha()
        assert len(name) <= 64
        # Name should be related to formatting or product
        assert any(word in name for word in ["format", "product", "name"])

    @pytest.mark.asyncio
    async def test_generate_name_from_purpose_on_llm_failure(self) -> None:
        """Should generate name from purpose if LLM fails."""
        # Setup
        mock_llm = MagicMock(spec=LLMResponseGenerator)
        mock_llm.model = "test-model"
        mock_llm.api_key = "test-key"
        mock_llm.api_base = None

        async def mock_stream(prompt: str) -> list[str]:
            response = "Invalid JSON"
            for char in response:
                yield char

        mock_llm.generate_stream = mock_stream

        gatherer = RequirementsGatherer(mock_llm)

        context = ConversationContext(
            skill_purpose="Format Product Names",
            skill_capabilities=SkillCapabilities(needs_file_operations=False, needs_external_knowledge=False, needs_script_execution=False, needs_multi_step_workflow=False),
        )

        # Execute
        name = await gatherer.generate_skill_name(context)

        # Verify - should generate from purpose
        assert name.startswith("format")
        assert "-" in name
        assert name.islower()
        assert len(name) <= 64

    @pytest.mark.asyncio
    async def test_generate_name_handles_invalid_llm_name(self) -> None:
        """Should fallback if LLM generates invalid name format."""
        # Setup
        mock_llm = MagicMock(spec=LLMResponseGenerator)
        mock_llm.model = "test-model"
        mock_llm.api_key = "test-key"
        mock_llm.api_base = None

        async def mock_stream(prompt: str) -> list[str]:
            response = '{"name": "Invalid Name With Spaces", "alternatives": []}'
            for char in response:
                yield char

        mock_llm.generate_stream = mock_stream

        gatherer = RequirementsGatherer(mock_llm)

        context = ConversationContext(
            skill_purpose="Format names",
            skill_capabilities=SkillCapabilities(needs_file_operations=False, needs_external_knowledge=False, needs_script_execution=False, needs_multi_step_workflow=False),
        )

        # Execute
        name = await gatherer.generate_skill_name(context)

        # Verify - should fallback to purpose-based generation
        assert name.islower()
        assert " " not in name
        assert len(name) <= 64


class TestGenerateDescription:
    """Tests for skill description generation."""

    @pytest.mark.asyncio
    async def test_generate_valid_description(self) -> None:
        """Should generate valid description with WHAT + WHEN."""
        # Setup
        mock_llm = MagicMock(spec=LLMResponseGenerator)
        mock_llm.model = "test-model"
        mock_llm.api_key = "test-key"
        mock_llm.api_base = None

        async def mock_stream(prompt: str) -> list[str]:
            response = (
                '{"description": "Formats product names into full display form '
                'when writing documentation. Use when abbreviations need consistent expansion."}'
            )
            for char in response:
                yield char

        mock_llm.generate_stream = mock_stream

        gatherer = RequirementsGatherer(mock_llm)

        context = ConversationContext(
            skill_name="formatting-product-names",
            skill_purpose="Format product abbreviations",
            skill_capabilities=SkillCapabilities(needs_file_operations=False, needs_external_knowledge=False, needs_script_execution=False, needs_multi_step_workflow=False),
            examples=["PA -> Pro Analytics"],
            triggers=["writing documentation"],
        )

        # Execute
        description = await gatherer.generate_description(context)

        # Verify
        assert len(description) > 10
        assert len(description) <= 1024
        assert "when" in description.lower()

    @pytest.mark.asyncio
    async def test_generate_description_from_purpose_on_llm_failure(self) -> None:
        """Should generate description from purpose if LLM fails."""
        # Setup
        mock_llm = MagicMock(spec=LLMResponseGenerator)
        mock_llm.model = "test-model"
        mock_llm.api_key = "test-key"
        mock_llm.api_base = None

        async def mock_stream(prompt: str) -> list[str]:
            response = "Invalid response"
            for char in response:
                yield char

        mock_llm.generate_stream = mock_stream

        gatherer = RequirementsGatherer(mock_llm)

        context = ConversationContext(
            skill_name="format-names",
            skill_purpose="Format product names",
            skill_capabilities=SkillCapabilities(needs_file_operations=False, needs_external_knowledge=False, needs_script_execution=False, needs_multi_step_workflow=False),
            triggers=["writing docs"],
        )

        # Execute
        description = await gatherer.generate_description(context)

        # Verify - should fallback to purpose-based generation
        assert len(description) > 10
        assert len(description) <= 1024
        assert "Format product names" in description

    @pytest.mark.asyncio
    async def test_generate_description_truncates_if_too_long(self) -> None:
        """Should truncate description if it exceeds max length."""
        # Setup
        mock_llm = MagicMock(spec=LLMResponseGenerator)
        mock_llm.model = "test-model"
        mock_llm.api_key = "test-key"
        mock_llm.api_base = None

        async def mock_stream(prompt: str) -> list[str]:
            # Return very long description
            long_desc = "Very long description. " * 100
            response = f'{{"description": "{long_desc}"}}'
            for char in response:
                yield char

        mock_llm.generate_stream = mock_stream

        gatherer = RequirementsGatherer(mock_llm)

        context = ConversationContext(
            skill_name="test-skill",
            skill_purpose="Test purpose" * 100,  # Very long purpose
            skill_capabilities=SkillCapabilities(needs_file_operations=False, needs_external_knowledge=False, needs_script_execution=False, needs_multi_step_workflow=False),
        )

        # Execute
        description = await gatherer.generate_description(context)

        # Verify - should be truncated
        assert len(description) <= 1024
