"""Exception hierarchy for tool-related errors.

This module defines a comprehensive exception hierarchy for all tool operations,
including registration, validation, execution, and resource management.
"""

from typing import Any, Optional


class ToolError(Exception):
    """Base exception for all tool-related errors.

    All tool exceptions inherit from this class and include an error code
    for programmatic handling and error classification.

    Attributes:
        message: Human-readable error description
        error_code: Unique code for programmatic error handling
        context: Additional context information
    """

    error_code: str = "TOOL_ERROR"

    def __init__(self, message: str, **context: Any) -> None:
        """Initialize tool error with message and optional context.

        Args:
            message: Human-readable error description
            **context: Additional context information (tool_name, tenant_id, etc.)
        """
        super().__init__(message)
        self.message = message
        self.context = context

    def __str__(self) -> str:
        """Return formatted error message with context."""
        if not self.context:
            return f"[{self.error_code}] {self.message}"

        context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
        return f"[{self.error_code}] {self.message} ({context_str})"


class ToolNotFoundError(ToolError):
    """Raised when a requested tool is not found in the registry.

    This error occurs when attempting to retrieve or execute a tool
    that has not been registered.
    """

    error_code = "TOOL_NOT_FOUND"

    def __init__(self, tool_name: str, **context: Any) -> None:
        """Initialize with tool name and optional context.

        Args:
            tool_name: Name of the tool that was not found
            **context: Additional context information
        """
        message = f"Tool '{tool_name}' not found in registry"
        super().__init__(message, tool_name=tool_name, **context)


class ToolAlreadyRegisteredError(ToolError):
    """Raised when attempting to register a tool that already exists.

    This error prevents duplicate tool registration and name conflicts
    in the tool registry.
    """

    error_code = "TOOL_ALREADY_REGISTERED"

    def __init__(self, tool_name: str, **context: Any) -> None:
        """Initialize with tool name and optional context.

        Args:
            tool_name: Name of the tool that is already registered
            **context: Additional context information
        """
        message = f"Tool '{tool_name}' is already registered"
        super().__init__(message, tool_name=tool_name, **context)


class ToolValidationError(ToolError):
    """Raised when tool argument validation fails.

    This error occurs when tool arguments do not match the expected
    schema or fail validation rules.
    """

    error_code = "TOOL_VALIDATION_ERROR"

    def __init__(self, tool_name: str, validation_error: str, **context: Any) -> None:
        """Initialize with tool name, validation error, and optional context.

        Args:
            tool_name: Name of the tool being validated
            validation_error: Description of the validation failure
            **context: Additional context information
        """
        message = f"Validation failed for tool '{tool_name}': {validation_error}"
        super().__init__(message, tool_name=tool_name, validation_error=validation_error, **context)


class ToolExecutionError(ToolError):
    """Raised when tool execution fails.

    This error wraps exceptions that occur during tool execution,
    providing context about the tool and execution environment.
    """

    error_code = "TOOL_EXECUTION_ERROR"

    def __init__(self, tool_name: str, execution_error: str, **context: Any) -> None:
        """Initialize with tool name, execution error, and optional context.

        Args:
            tool_name: Name of the tool that failed
            execution_error: Description of the execution failure
            **context: Additional context information
        """
        message = f"Execution failed for tool '{tool_name}': {execution_error}"
        super().__init__(message, tool_name=tool_name, execution_error=execution_error, **context)


class ToolTimeoutError(ToolError):
    """Raised when tool execution exceeds the timeout limit.

    This error prevents long-running tools from blocking system resources
    and ensures predictable execution times.
    """

    error_code = "TOOL_TIMEOUT"

    def __init__(self, tool_name: str, timeout_seconds: float, **context: Any) -> None:
        """Initialize with tool name, timeout value, and optional context.

        Args:
            tool_name: Name of the tool that timed out
            timeout_seconds: The timeout limit that was exceeded
            **context: Additional context information
        """
        message = f"Tool '{tool_name}' exceeded timeout limit of {timeout_seconds}s"
        super().__init__(
            message,
            tool_name=tool_name,
            timeout_seconds=timeout_seconds,
            **context,
        )


class RateLimitExceededError(ToolError):
    """Raised when tenant's tool usage rate limit is exceeded.

    This error enforces fair resource allocation and prevents
    individual tenants from monopolizing system resources.
    """

    error_code = "RATE_LIMIT_EXCEEDED"

    def __init__(
        self,
        tenant_id: str,
        limit: int,
        window_seconds: int,
        **context: Any,
    ) -> None:
        """Initialize with tenant ID, rate limit, and optional context.

        Args:
            tenant_id: ID of the tenant that exceeded the limit
            limit: Maximum number of requests allowed
            window_seconds: Time window for the rate limit
            **context: Additional context information
        """
        message = (
            f"Rate limit exceeded for tenant '{tenant_id}': "
            f"{limit} requests per {window_seconds}s"
        )
        super().__init__(
            message,
            tenant_id=tenant_id,
            limit=limit,
            window_seconds=window_seconds,
            **context,
        )


class CostBudgetExceededError(ToolError):
    """Raised when task's cost budget is exceeded.

    This error prevents runaway costs by enforcing budget limits
    on task execution, particularly for LLM-based tools.
    """

    error_code = "COST_BUDGET_EXCEEDED"

    def __init__(
        self,
        task_id: str,
        budget: float,
        current_cost: float,
        **context: Any,
    ) -> None:
        """Initialize with task ID, budget limit, and optional context.

        Args:
            task_id: ID of the task that exceeded the budget
            budget: Maximum allowed cost
            current_cost: Current accumulated cost
            **context: Additional context information
        """
        message = (
            f"Cost budget exceeded for task '{task_id}': "
            f"current cost ${current_cost:.4f} exceeds budget ${budget:.4f}"
        )
        super().__init__(
            message,
            task_id=task_id,
            budget=budget,
            current_cost=current_cost,
            **context,
        )


class ModelNotApprovedError(ToolError):
    """Raised when attempting to use an LLM model not in the approved list.

    This error enforces security and cost controls by restricting
    tool usage to pre-approved LLM models.
    """

    error_code = "MODEL_NOT_APPROVED"

    def __init__(
        self,
        model_name: str,
        approved_models: Optional[list[str]] = None,
        **context: Any,
    ) -> None:
        """Initialize with model name, approved list, and optional context.

        Args:
            model_name: Name of the model that was not approved
            approved_models: List of approved model names (optional)
            **context: Additional context information
        """
        message = f"Model '{model_name}' is not in the approved models list"
        if approved_models:
            message += f". Approved models: {', '.join(approved_models)}"

        super().__init__(
            message,
            model_name=model_name,
            approved_models=approved_models,
            **context,
        )
