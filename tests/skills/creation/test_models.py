"""Tests for skill creation data models."""

import pytest
from pydantic import ValidationError

from omniforge.skills.creation.models import (
    ConversationContext,
    ConversationState,
    OfficialSkillSpec,
    SkillCapabilities,
    ValidationResult,
)


class TestConversationState:
    """Tests for ConversationState enum."""

    def test_all_states_present(self) -> None:
        """ConversationState should have all 12 required states."""
        expected_states = {
            "idle",
            "intent_detection",
            "checking_existing",
            "gathering_purpose",
            "gathering_details",
            "confirming_spec",
            "generating",
            "validating",
            "fixing_errors",
            "selecting_storage",
            "saving",
            "completed",
            "error",
        }
        actual_states = {state.value for state in ConversationState}
        assert actual_states == expected_states

    def test_state_values(self) -> None:
        """ConversationState values should match their names in snake_case."""
        assert ConversationState.IDLE.value == "idle"
        assert ConversationState.INTENT_DETECTION.value == "intent_detection"
        assert ConversationState.GATHERING_PURPOSE.value == "gathering_purpose"
        assert ConversationState.CONFIRMING_SPEC.value == "confirming_spec"
        assert ConversationState.COMPLETED.value == "completed"


class TestSkillCapabilities:
    """Tests for SkillCapabilities model."""

    def test_default_capabilities(self) -> None:
        """Should create capabilities with all flags False by default."""
        caps = SkillCapabilities()
        assert caps.needs_file_operations is False
        assert caps.needs_external_knowledge is False
        assert caps.needs_script_execution is False
        assert caps.needs_multi_step_workflow is False
        assert caps.suggested_tools == []
        assert caps.suggested_assets == []
        assert caps.suggested_references == []
        assert caps.suggested_scripts == []
        assert caps.reasoning == ""
        assert caps.confidence == 0.0

    def test_capabilities_with_flags(self) -> None:
        """Should create capabilities with specific flags."""
        caps = SkillCapabilities(
            needs_file_operations=True,
            needs_script_execution=True,
            confidence=0.9,
            reasoning="Needs to run scripts and read files"
        )
        assert caps.needs_file_operations is True
        assert caps.needs_script_execution is True
        assert caps.needs_external_knowledge is False
        assert caps.needs_multi_step_workflow is False
        assert caps.confidence == 0.9
        assert caps.reasoning == "Needs to run scripts and read files"

    def test_capabilities_with_suggestions(self) -> None:
        """Should create capabilities with LLM suggestions."""
        caps = SkillCapabilities(
            needs_file_operations=True,
            suggested_tools=["Read", "Write"],
            suggested_assets=[{"name": "config.json", "purpose": "Configuration", "type": "config"}],
            suggested_references=[{"topic": "api-docs", "purpose": "API documentation"}],
            suggested_scripts=[{"name": "deploy.sh", "purpose": "Deploy script", "language": "bash"}],
            confidence=0.85
        )
        assert len(caps.suggested_tools) == 2
        assert "Read" in caps.suggested_tools
        assert len(caps.suggested_assets) == 1
        assert caps.suggested_assets[0]["name"] == "config.json"
        assert len(caps.suggested_references) == 1
        assert caps.suggested_references[0]["topic"] == "api-docs"
        assert len(caps.suggested_scripts) == 1
        assert caps.suggested_scripts[0]["language"] == "bash"


class TestOfficialSkillSpec:
    """Tests for OfficialSkillSpec model."""

    def test_valid_skill_spec(self) -> None:
        """Should create valid skill spec with kebab-case name."""
        spec = OfficialSkillSpec(
            name="format-products", description="Formats product data"
        )
        assert spec.name == "format-products"
        assert spec.description == "Formats product data"

    def test_valid_name_with_numbers(self) -> None:
        """Should accept kebab-case name with numbers."""
        spec = OfficialSkillSpec(name="skill-v2-format", description="Test skill")
        assert spec.name == "skill-v2-format"

    def test_valid_single_word_name(self) -> None:
        """Should accept single-word lowercase name."""
        spec = OfficialSkillSpec(name="formatter", description="Test skill")
        assert spec.name == "formatter"

    def test_invalid_name_uppercase(self) -> None:
        """Should reject name with uppercase letters."""
        with pytest.raises(ValidationError, match="kebab-case"):
            OfficialSkillSpec(name="Format-Products", description="Test")

    def test_invalid_name_starts_with_number(self) -> None:
        """Should reject name starting with number."""
        with pytest.raises(ValidationError, match="kebab-case"):
            OfficialSkillSpec(name="2-format-products", description="Test")

    def test_invalid_name_with_underscore(self) -> None:
        """Should reject name with underscore (snake_case)."""
        with pytest.raises(ValidationError, match="kebab-case"):
            OfficialSkillSpec(name="format_products", description="Test")

    def test_invalid_name_with_space(self) -> None:
        """Should reject name with spaces."""
        with pytest.raises(ValidationError, match="kebab-case"):
            OfficialSkillSpec(name="format products", description="Test")

    def test_invalid_name_with_special_chars(self) -> None:
        """Should reject name with special characters."""
        with pytest.raises(ValidationError, match="kebab-case"):
            OfficialSkillSpec(name="format@products", description="Test")

    def test_name_too_long(self) -> None:
        """Should reject name exceeding 64 characters."""
        long_name = "a" * 65
        with pytest.raises(ValidationError):
            OfficialSkillSpec(name=long_name, description="Test")

    def test_name_empty(self) -> None:
        """Should reject empty name."""
        with pytest.raises(ValidationError):
            OfficialSkillSpec(name="", description="Test")

    def test_description_empty(self) -> None:
        """Should reject empty description."""
        with pytest.raises(ValidationError):
            OfficialSkillSpec(name="test-skill", description="")

    def test_description_too_long(self) -> None:
        """Should reject description exceeding 1024 characters."""
        long_description = "a" * 1025
        with pytest.raises(ValidationError):
            OfficialSkillSpec(name="test-skill", description=long_description)

    def test_description_at_max_length(self) -> None:
        """Should accept description at exactly 1024 characters."""
        max_description = "a" * 1024
        spec = OfficialSkillSpec(name="test-skill", description=max_description)
        assert len(spec.description) == 1024


class TestConversationContext:
    """Tests for ConversationContext model."""

    def test_default_initialization(self) -> None:
        """Should initialize with default values."""
        ctx = ConversationContext()
        assert ctx.state == ConversationState.IDLE
        assert ctx.skill_name is None
        assert ctx.skill_description is None
        assert ctx.skill_purpose is None
        assert ctx.skill_capabilities is None
        assert ctx.examples == []
        assert ctx.workflow_steps == []
        assert ctx.validation_attempts == 0
        assert ctx.max_validation_retries == 3
        assert len(ctx.session_id) > 0

    def test_initialization_with_values(self) -> None:
        """Should initialize with provided values."""
        caps = SkillCapabilities(needs_file_operations=True, confidence=0.9)
        ctx = ConversationContext(
            state=ConversationState.GATHERING_PURPOSE,
            skill_name="test-skill",
            skill_description="Test description",
            skill_purpose="Test purpose",
            skill_capabilities=caps,
        )
        assert ctx.state == ConversationState.GATHERING_PURPOSE
        assert ctx.skill_name == "test-skill"
        assert ctx.skill_description == "Test description"
        assert ctx.skill_purpose == "Test purpose"
        assert ctx.skill_capabilities is not None
        assert ctx.skill_capabilities.needs_file_operations is True
        assert ctx.skill_capabilities.confidence == 0.9

    def test_to_official_spec_with_valid_data(self) -> None:
        """Should convert to OfficialSkillSpec with valid name and description."""
        ctx = ConversationContext(
            skill_name="test-skill", skill_description="Test description"
        )
        spec = ctx.to_official_spec()
        assert spec is not None
        assert spec.name == "test-skill"
        assert spec.description == "Test description"

    def test_to_official_spec_without_name(self) -> None:
        """Should return None when name is missing."""
        ctx = ConversationContext(skill_description="Test description")
        spec = ctx.to_official_spec()
        assert spec is None

    def test_to_official_spec_without_description(self) -> None:
        """Should return None when description is missing."""
        ctx = ConversationContext(skill_name="test-skill")
        spec = ctx.to_official_spec()
        assert spec is None

    def test_to_official_spec_with_invalid_name(self) -> None:
        """Should return None when name format is invalid."""
        ctx = ConversationContext(
            skill_name="Invalid_Name", skill_description="Test description"
        )
        spec = ctx.to_official_spec()
        assert spec is None

    def test_can_retry_validation_initially(self) -> None:
        """Should allow validation retries initially."""
        ctx = ConversationContext()
        assert ctx.can_retry_validation() is True

    def test_can_retry_validation_at_max(self) -> None:
        """Should not allow validation when at max retries."""
        ctx = ConversationContext(validation_attempts=3, max_validation_retries=3)
        assert ctx.can_retry_validation() is False

    def test_can_retry_validation_below_max(self) -> None:
        """Should allow validation when below max retries."""
        ctx = ConversationContext(validation_attempts=2, max_validation_retries=3)
        assert ctx.can_retry_validation() is True

    def test_increment_validation_attempt(self) -> None:
        """Should increment validation attempt counter."""
        ctx = ConversationContext()
        assert ctx.validation_attempts == 0
        ctx.increment_validation_attempt()
        assert ctx.validation_attempts == 1
        ctx.increment_validation_attempt()
        assert ctx.validation_attempts == 2

    def test_reset_validation(self) -> None:
        """Should reset validation tracking."""
        ctx = ConversationContext(validation_attempts=2)
        ctx.validation_errors.extend(["error1", "error2"])
        ctx.reset_validation()
        assert ctx.validation_attempts == 0
        assert ctx.validation_errors == []

    def test_accumulate_examples(self) -> None:
        """Should accumulate examples in list."""
        ctx = ConversationContext()
        ctx.examples.append("Example 1")
        ctx.examples.append("Example 2")
        assert len(ctx.examples) == 2
        assert ctx.examples == ["Example 1", "Example 2"]

    def test_accumulate_workflow_steps(self) -> None:
        """Should accumulate workflow steps in list."""
        ctx = ConversationContext()
        ctx.workflow_steps.extend(["Step 1", "Step 2", "Step 3"])
        assert len(ctx.workflow_steps) == 3

    def test_generated_resources_dict(self) -> None:
        """Should store generated resources in dictionary."""
        ctx = ConversationContext()
        ctx.generated_resources["script.py"] = "print('hello')"
        ctx.generated_resources["config.yaml"] = "key: value"
        assert len(ctx.generated_resources) == 2
        assert "script.py" in ctx.generated_resources


class TestValidationResult:
    """Tests for ValidationResult model."""

    def test_valid_result(self) -> None:
        """Should create valid result."""
        result = ValidationResult(is_valid=True, skill_path="/path/to/skill.md")
        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == []
        assert result.skill_path == "/path/to/skill.md"

    def test_invalid_result_with_errors(self) -> None:
        """Should create invalid result with errors."""
        result = ValidationResult(
            is_valid=False, errors=["Error 1", "Error 2"], warnings=["Warning 1"]
        )
        assert result.is_valid is False
        assert len(result.errors) == 2
        assert len(result.warnings) == 1

    def test_has_errors(self) -> None:
        """Should detect presence of errors."""
        result = ValidationResult(is_valid=False, errors=["Error 1"])
        assert result.has_errors() is True

        result_no_errors = ValidationResult(is_valid=True)
        assert result_no_errors.has_errors() is False

    def test_has_warnings(self) -> None:
        """Should detect presence of warnings."""
        result = ValidationResult(is_valid=True, warnings=["Warning 1"])
        assert result.has_warnings() is True

        result_no_warnings = ValidationResult(is_valid=True)
        assert result_no_warnings.has_warnings() is False

    def test_add_error(self) -> None:
        """Should add error and set is_valid to False."""
        result = ValidationResult(is_valid=True)
        result.add_error("New error")
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert result.errors[0] == "New error"

    def test_add_multiple_errors(self) -> None:
        """Should accumulate multiple errors."""
        result = ValidationResult(is_valid=True)
        result.add_error("Error 1")
        result.add_error("Error 2")
        assert len(result.errors) == 2

    def test_add_warning(self) -> None:
        """Should add warning without affecting is_valid."""
        result = ValidationResult(is_valid=True)
        result.add_warning("New warning")
        assert result.is_valid is True
        assert len(result.warnings) == 1
        assert result.warnings[0] == "New warning"

    def test_add_multiple_warnings(self) -> None:
        """Should accumulate multiple warnings."""
        result = ValidationResult(is_valid=True)
        result.add_warning("Warning 1")
        result.add_warning("Warning 2")
        assert len(result.warnings) == 2

    def test_combined_errors_and_warnings(self) -> None:
        """Should handle both errors and warnings."""
        result = ValidationResult(is_valid=True)
        result.add_warning("Warning 1")
        result.add_error("Error 1")
        result.add_warning("Warning 2")
        assert result.is_valid is False
        assert result.has_errors() is True
        assert result.has_warnings() is True
        assert len(result.errors) == 1
        assert len(result.warnings) == 2
