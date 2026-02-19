"""Custom exceptions for prompt management module.

This module defines the exception hierarchy for prompt-related errors,
providing structured error handling with status codes and error codes.
"""

from typing import Optional


class PromptError(Exception):
    """Base exception for all prompt-related errors.

    Attributes:
        code: Machine-readable error code
        message: Human-readable error message
        status_code: HTTP status code for API responses
    """

    def __init__(self, message: str, code: str, status_code: int) -> None:
        """Initialize prompt error.

        Args:
            message: Human-readable error description
            code: Machine-readable error code
            status_code: HTTP status code (400, 500, etc.)
        """
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class PromptNotFoundError(PromptError):
    """Raised when a prompt cannot be found.

    This error indicates that the requested prompt does not exist in the system.
    """

    def __init__(self, prompt_id: str) -> None:
        """Initialize prompt not found error.

        Args:
            prompt_id: The ID of the prompt that was not found
        """
        super().__init__(
            message=f"Prompt '{prompt_id}' not found",
            code="prompt_not_found",
            status_code=404,
        )
        self.prompt_id = prompt_id


class PromptVersionNotFoundError(PromptError):
    """Raised when a prompt version cannot be found.

    This error indicates that the requested prompt version does not exist.
    """

    def __init__(self, prompt_id: str, version_number: int) -> None:
        """Initialize prompt version not found error.

        Args:
            prompt_id: The ID of the prompt
            version_number: The version number that was not found
        """
        super().__init__(
            message=f"Prompt '{prompt_id}' version {version_number} not found",
            code="prompt_version_not_found",
            status_code=404,
        )
        self.prompt_id = prompt_id
        self.version_number = version_number


class PromptValidationError(PromptError):
    """Raised when prompt validation fails.

    This error indicates that the prompt content or configuration
    failed validation checks.
    """

    def __init__(
        self, message: str, field: Optional[str] = None, details: Optional[dict] = None
    ) -> None:
        """Initialize prompt validation error.

        Args:
            message: Description of the validation failure
            field: Optional field name that failed validation
            details: Optional dictionary with additional validation details
        """
        if field:
            full_message = f"Validation failed for field '{field}': {message}"
        else:
            full_message = f"Validation failed: {message}"

        super().__init__(
            message=full_message,
            code="prompt_validation_error",
            status_code=400,
        )
        self.field = field
        self.details = details or {}


class PromptCompositionError(PromptError):
    """Raised when prompt composition fails.

    This error indicates that combining prompts from multiple layers
    encountered an error.
    """

    def __init__(self, message: str, layer: Optional[str] = None) -> None:
        """Initialize prompt composition error.

        Args:
            message: Description of the composition failure
            layer: Optional layer where composition failed
        """
        if layer:
            full_message = f"Composition failed at layer '{layer}': {message}"
        else:
            full_message = f"Composition failed: {message}"

        super().__init__(
            message=full_message,
            code="prompt_composition_error",
            status_code=500,
        )
        self.layer = layer


class PromptRenderError(PromptError):
    """Raised when prompt rendering with variables fails.

    This error indicates that variable substitution or template rendering
    encountered an error.
    """

    def __init__(
        self, message: str, variable: Optional[str] = None, details: Optional[dict] = None
    ) -> None:
        """Initialize prompt render error.

        Args:
            message: Description of the render failure
            variable: Optional variable name that caused the error
            details: Optional dictionary with additional render details
        """
        if variable:
            full_message = f"Render failed for variable '{variable}': {message}"
        else:
            full_message = f"Render failed: {message}"

        super().__init__(
            message=full_message,
            code="prompt_render_error",
            status_code=400,
        )
        self.variable = variable
        self.details = details or {}


class ExperimentNotFoundError(PromptError):
    """Raised when an experiment cannot be found.

    This error indicates that the requested experiment does not exist.
    """

    def __init__(self, experiment_id: str) -> None:
        """Initialize experiment not found error.

        Args:
            experiment_id: The ID of the experiment that was not found
        """
        super().__init__(
            message=f"Experiment '{experiment_id}' not found",
            code="experiment_not_found",
            status_code=404,
        )
        self.experiment_id = experiment_id


class ExperimentStateError(PromptError):
    """Raised when an operation is invalid for the current experiment state.

    This error indicates that the requested operation cannot be performed
    because the experiment is in an incompatible state.
    """

    def __init__(self, experiment_id: str, current_state: str, operation: str) -> None:
        """Initialize experiment state error.

        Args:
            experiment_id: The ID of the experiment
            current_state: The current state of the experiment
            operation: The operation that was attempted
        """
        super().__init__(
            message=f"Cannot perform '{operation}' on experiment '{experiment_id}' "
            f"in state '{current_state}'",
            code="experiment_state_error",
            status_code=409,
        )
        self.experiment_id = experiment_id
        self.current_state = current_state
        self.operation = operation


class MergePointConflictError(PromptError):
    """Raised when merge point definitions conflict.

    This error indicates that merge points have incompatible configurations
    across prompt layers.
    """

    def __init__(
        self,
        merge_point_name: str,
        layer1: str,
        layer2: str,
        conflict_reason: str,
    ) -> None:
        """Initialize merge point conflict error.

        Args:
            merge_point_name: Name of the conflicting merge point
            layer1: First layer with the merge point
            layer2: Second layer with the merge point
            conflict_reason: Description of the conflict
        """
        super().__init__(
            message=f"Merge point '{merge_point_name}' conflict between "
            f"layers '{layer1}' and '{layer2}': {conflict_reason}",
            code="merge_point_conflict",
            status_code=409,
        )
        self.merge_point_name = merge_point_name
        self.layer1 = layer1
        self.layer2 = layer2
        self.conflict_reason = conflict_reason


class PromptLockViolationError(PromptError):
    """Raised when attempting to modify a locked prompt.

    This error indicates that a prompt or merge point is locked
    and cannot be modified.
    """

    def __init__(self, resource_type: str, resource_id: str) -> None:
        """Initialize prompt lock violation error.

        Args:
            resource_type: Type of locked resource (e.g., "prompt", "merge_point")
            resource_id: ID of the locked resource
        """
        super().__init__(
            message=f"Cannot modify locked {resource_type} '{resource_id}'",
            code="prompt_lock_violation",
            status_code=409,
        )
        self.resource_type = resource_type
        self.resource_id = resource_id


class PromptConcurrencyError(PromptError):
    """Raised when a concurrent modification conflict occurs.

    This error indicates that the prompt was modified by another process
    since it was last read.
    """

    def __init__(
        self,
        prompt_id: str,
        expected_version: int,
        current_version: int,
    ) -> None:
        """Initialize prompt concurrency error.

        Args:
            prompt_id: The ID of the prompt
            expected_version: The version that was expected
            current_version: The actual current version
        """
        super().__init__(
            message=f"Concurrent modification detected for prompt '{prompt_id}': "
            f"expected version {expected_version}, found version {current_version}",
            code="prompt_concurrency_error",
            status_code=409,
        )
        self.prompt_id = prompt_id
        self.expected_version = expected_version
        self.current_version = current_version
