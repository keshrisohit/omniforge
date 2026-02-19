"""Tests for prompt management errors."""

from omniforge.prompts.errors import (
    ExperimentNotFoundError,
    ExperimentStateError,
    MergePointConflictError,
    PromptCompositionError,
    PromptConcurrencyError,
    PromptError,
    PromptLockViolationError,
    PromptNotFoundError,
    PromptRenderError,
    PromptValidationError,
    PromptVersionNotFoundError,
)


class TestPromptError:
    """Tests for PromptError base exception."""

    def test_error_initialization(self) -> None:
        """PromptError should initialize with message, code, and status code."""
        error = PromptError(
            message="Test error",
            code="test_error",
            status_code=500,
        )

        assert error.message == "Test error"
        assert error.code == "test_error"
        assert error.status_code == 500
        assert str(error) == "Test error"

    def test_error_is_exception(self) -> None:
        """PromptError should be an Exception."""
        error = PromptError("Test", "test", 500)
        assert isinstance(error, Exception)


class TestPromptNotFoundError:
    """Tests for PromptNotFoundError."""

    def test_initialization(self) -> None:
        """Should initialize with prompt ID and appropriate defaults."""
        error = PromptNotFoundError(prompt_id="prompt-123")

        assert error.prompt_id == "prompt-123"
        assert error.message == "Prompt 'prompt-123' not found"
        assert error.code == "prompt_not_found"
        assert error.status_code == 404

    def test_is_prompt_error(self) -> None:
        """Should be a PromptError."""
        error = PromptNotFoundError(prompt_id="prompt-123")
        assert isinstance(error, PromptError)


class TestPromptVersionNotFoundError:
    """Tests for PromptVersionNotFoundError."""

    def test_initialization(self) -> None:
        """Should initialize with prompt ID, version, and appropriate defaults."""
        error = PromptVersionNotFoundError(
            prompt_id="prompt-123",
            version_number=5,
        )

        assert error.prompt_id == "prompt-123"
        assert error.version_number == 5
        assert error.message == "Prompt 'prompt-123' version 5 not found"
        assert error.code == "prompt_version_not_found"
        assert error.status_code == 404


class TestPromptValidationError:
    """Tests for PromptValidationError."""

    def test_initialization_with_field(self) -> None:
        """Should include field name in message when provided."""
        error = PromptValidationError(
            message="Content is empty",
            field="content",
        )

        assert error.field == "content"
        assert error.message == "Validation failed for field 'content': Content is empty"
        assert error.code == "prompt_validation_error"
        assert error.status_code == 400

    def test_initialization_without_field(self) -> None:
        """Should work without field name."""
        error = PromptValidationError(message="Invalid format")

        assert error.field is None
        assert error.message == "Validation failed: Invalid format"

    def test_initialization_with_details(self) -> None:
        """Should store additional details."""
        details = {"expected": "string", "got": "number"}
        error = PromptValidationError(
            message="Type mismatch",
            details=details,
        )

        assert error.details == details


class TestPromptCompositionError:
    """Tests for PromptCompositionError."""

    def test_initialization_with_layer(self) -> None:
        """Should include layer in message when provided."""
        error = PromptCompositionError(
            message="Merge point conflict",
            layer="tenant",
        )

        assert error.layer == "tenant"
        assert error.message == "Composition failed at layer 'tenant': Merge point conflict"
        assert error.code == "prompt_composition_error"
        assert error.status_code == 500

    def test_initialization_without_layer(self) -> None:
        """Should work without layer."""
        error = PromptCompositionError(message="Unknown error")

        assert error.layer is None
        assert error.message == "Composition failed: Unknown error"


class TestPromptRenderError:
    """Tests for PromptRenderError."""

    def test_initialization_with_variable(self) -> None:
        """Should include variable name in message when provided."""
        error = PromptRenderError(
            message="Variable not found",
            variable="user_name",
        )

        assert error.variable == "user_name"
        assert error.message == "Render failed for variable 'user_name': Variable not found"
        assert error.code == "prompt_render_error"
        assert error.status_code == 400

    def test_initialization_without_variable(self) -> None:
        """Should work without variable name."""
        error = PromptRenderError(message="Template syntax error")

        assert error.variable is None
        assert error.message == "Render failed: Template syntax error"

    def test_initialization_with_details(self) -> None:
        """Should store additional details."""
        details = {"line": 5, "column": 12}
        error = PromptRenderError(
            message="Syntax error",
            details=details,
        )

        assert error.details == details


class TestExperimentNotFoundError:
    """Tests for ExperimentNotFoundError."""

    def test_initialization(self) -> None:
        """Should initialize with experiment ID and appropriate defaults."""
        error = ExperimentNotFoundError(experiment_id="exp-456")

        assert error.experiment_id == "exp-456"
        assert error.message == "Experiment 'exp-456' not found"
        assert error.code == "experiment_not_found"
        assert error.status_code == 404


class TestExperimentStateError:
    """Tests for ExperimentStateError."""

    def test_initialization(self) -> None:
        """Should initialize with experiment details and appropriate defaults."""
        error = ExperimentStateError(
            experiment_id="exp-789",
            current_state="completed",
            operation="pause",
        )

        assert error.experiment_id == "exp-789"
        assert error.current_state == "completed"
        assert error.operation == "pause"
        assert (
            error.message == "Cannot perform 'pause' on experiment 'exp-789' in state 'completed'"
        )
        assert error.code == "experiment_state_error"
        assert error.status_code == 409


class TestMergePointConflictError:
    """Tests for MergePointConflictError."""

    def test_initialization(self) -> None:
        """Should initialize with merge point conflict details."""
        error = MergePointConflictError(
            merge_point_name="header",
            layer1="system",
            layer2="tenant",
            conflict_reason="Both layers have locked=True",
        )

        assert error.merge_point_name == "header"
        assert error.layer1 == "system"
        assert error.layer2 == "tenant"
        assert error.conflict_reason == "Both layers have locked=True"
        assert (
            error.message == "Merge point 'header' conflict between layers 'system' "
            "and 'tenant': Both layers have locked=True"
        )
        assert error.code == "merge_point_conflict"
        assert error.status_code == 409


class TestPromptLockViolationError:
    """Tests for PromptLockViolationError."""

    def test_initialization(self) -> None:
        """Should initialize with resource type and ID."""
        error = PromptLockViolationError(
            resource_type="prompt",
            resource_id="prompt-999",
        )

        assert error.resource_type == "prompt"
        assert error.resource_id == "prompt-999"
        assert error.message == "Cannot modify locked prompt 'prompt-999'"
        assert error.code == "prompt_lock_violation"
        assert error.status_code == 409


class TestPromptConcurrencyError:
    """Tests for PromptConcurrencyError."""

    def test_initialization(self) -> None:
        """Should initialize with version conflict details."""
        error = PromptConcurrencyError(
            prompt_id="prompt-555",
            expected_version=3,
            current_version=5,
        )

        assert error.prompt_id == "prompt-555"
        assert error.expected_version == 3
        assert error.current_version == 5
        assert (
            error.message == "Concurrent modification detected for prompt 'prompt-555': "
            "expected version 3, found version 5"
        )
        assert error.code == "prompt_concurrency_error"
        assert error.status_code == 409
