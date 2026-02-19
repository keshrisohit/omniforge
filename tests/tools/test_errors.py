"""Tests for tool exception hierarchy."""

import pytest

from omniforge.tools.errors import (
    CostBudgetExceededError,
    ModelNotApprovedError,
    RateLimitExceededError,
    ToolAlreadyRegisteredError,
    ToolError,
    ToolExecutionError,
    ToolNotFoundError,
    ToolTimeoutError,
    ToolValidationError,
)


class TestToolError:
    """Tests for base ToolError exception."""

    def test_tool_error_with_message_only(self) -> None:
        """ToolError should format message with error code."""
        error = ToolError("Something went wrong")

        assert str(error) == "[TOOL_ERROR] Something went wrong"
        assert error.message == "Something went wrong"
        assert error.error_code == "TOOL_ERROR"
        assert error.context == {}

    def test_tool_error_with_context(self) -> None:
        """ToolError should include context in formatted message."""
        error = ToolError("Operation failed", tool_name="test_tool", tenant_id="123")

        assert "[TOOL_ERROR] Operation failed" in str(error)
        assert "tool_name=test_tool" in str(error)
        assert "tenant_id=123" in str(error)
        assert error.context == {"tool_name": "test_tool", "tenant_id": "123"}

    def test_tool_error_inheritance(self) -> None:
        """ToolError should inherit from Exception."""
        error = ToolError("Test error")
        assert isinstance(error, Exception)

    def test_tool_error_can_be_raised(self) -> None:
        """ToolError should be raisable like standard exceptions."""
        with pytest.raises(ToolError, match="Test error"):
            raise ToolError("Test error")


class TestToolNotFoundError:
    """Tests for ToolNotFoundError exception."""

    def test_tool_not_found_error_message(self) -> None:
        """ToolNotFoundError should format message with tool name."""
        error = ToolNotFoundError("my_tool")

        assert "Tool 'my_tool' not found in registry" in str(error)
        assert error.error_code == "TOOL_NOT_FOUND"
        assert error.context["tool_name"] == "my_tool"

    def test_tool_not_found_error_with_context(self) -> None:
        """ToolNotFoundError should include additional context."""
        error = ToolNotFoundError("my_tool", tenant_id="tenant_123")

        assert "my_tool" in str(error)
        assert "tenant_id=tenant_123" in str(error)

    def test_tool_not_found_error_inherits_from_tool_error(self) -> None:
        """ToolNotFoundError should inherit from ToolError."""
        error = ToolNotFoundError("test_tool")
        assert isinstance(error, ToolError)
        assert isinstance(error, Exception)

    def test_tool_not_found_error_unique_code(self) -> None:
        """ToolNotFoundError should have unique error code."""
        error = ToolNotFoundError("test_tool")
        assert error.error_code == "TOOL_NOT_FOUND"
        assert error.error_code != ToolError.error_code


class TestToolAlreadyRegisteredError:
    """Tests for ToolAlreadyRegisteredError exception."""

    def test_tool_already_registered_error_message(self) -> None:
        """ToolAlreadyRegisteredError should format message with tool name."""
        error = ToolAlreadyRegisteredError("duplicate_tool")

        assert "Tool 'duplicate_tool' is already registered" in str(error)
        assert error.error_code == "TOOL_ALREADY_REGISTERED"
        assert error.context["tool_name"] == "duplicate_tool"

    def test_tool_already_registered_error_with_context(self) -> None:
        """ToolAlreadyRegisteredError should include additional context."""
        error = ToolAlreadyRegisteredError("duplicate_tool", registry_id="main")

        assert "duplicate_tool" in str(error)
        assert "registry_id=main" in str(error)

    def test_tool_already_registered_error_inherits_from_tool_error(self) -> None:
        """ToolAlreadyRegisteredError should inherit from ToolError."""
        error = ToolAlreadyRegisteredError("test_tool")
        assert isinstance(error, ToolError)

    def test_tool_already_registered_error_unique_code(self) -> None:
        """ToolAlreadyRegisteredError should have unique error code."""
        error = ToolAlreadyRegisteredError("test_tool")
        assert error.error_code == "TOOL_ALREADY_REGISTERED"


class TestToolValidationError:
    """Tests for ToolValidationError exception."""

    def test_tool_validation_error_message(self) -> None:
        """ToolValidationError should format message with tool and validation error."""
        error = ToolValidationError("calculator", "Missing required argument 'value'")

        assert "Validation failed for tool 'calculator'" in str(error)
        assert "Missing required argument 'value'" in str(error)
        assert error.error_code == "TOOL_VALIDATION_ERROR"
        assert error.context["tool_name"] == "calculator"
        assert error.context["validation_error"] == "Missing required argument 'value'"

    def test_tool_validation_error_with_context(self) -> None:
        """ToolValidationError should include additional context."""
        error = ToolValidationError(
            "calculator",
            "Invalid type for argument 'x'",
            expected_type="int",
            actual_type="str",
        )

        assert "calculator" in str(error)
        assert "Invalid type" in str(error)
        assert "expected_type=int" in str(error)
        assert "actual_type=str" in str(error)

    def test_tool_validation_error_inherits_from_tool_error(self) -> None:
        """ToolValidationError should inherit from ToolError."""
        error = ToolValidationError("test_tool", "Invalid")
        assert isinstance(error, ToolError)

    def test_tool_validation_error_unique_code(self) -> None:
        """ToolValidationError should have unique error code."""
        error = ToolValidationError("test_tool", "Invalid")
        assert error.error_code == "TOOL_VALIDATION_ERROR"


class TestToolExecutionError:
    """Tests for ToolExecutionError exception."""

    def test_tool_execution_error_message(self) -> None:
        """ToolExecutionError should format message with tool and execution error."""
        error = ToolExecutionError("database_query", "Connection timeout")

        assert "Execution failed for tool 'database_query'" in str(error)
        assert "Connection timeout" in str(error)
        assert error.error_code == "TOOL_EXECUTION_ERROR"
        assert error.context["tool_name"] == "database_query"
        assert error.context["execution_error"] == "Connection timeout"

    def test_tool_execution_error_with_context(self) -> None:
        """ToolExecutionError should include additional context."""
        error = ToolExecutionError(
            "api_call", "HTTP 500 error", url="https://api.example.com", status=500
        )

        assert "api_call" in str(error)
        assert "HTTP 500 error" in str(error)
        assert "url=https://api.example.com" in str(error)
        assert "status=500" in str(error)

    def test_tool_execution_error_inherits_from_tool_error(self) -> None:
        """ToolExecutionError should inherit from ToolError."""
        error = ToolExecutionError("test_tool", "Failed")
        assert isinstance(error, ToolError)

    def test_tool_execution_error_unique_code(self) -> None:
        """ToolExecutionError should have unique error code."""
        error = ToolExecutionError("test_tool", "Failed")
        assert error.error_code == "TOOL_EXECUTION_ERROR"


class TestToolTimeoutError:
    """Tests for ToolTimeoutError exception."""

    def test_tool_timeout_error_message(self) -> None:
        """ToolTimeoutError should format message with tool name and timeout."""
        error = ToolTimeoutError("slow_operation", 30.0)

        assert "Tool 'slow_operation' exceeded timeout limit of 30.0s" in str(error)
        assert error.error_code == "TOOL_TIMEOUT"
        assert error.context["tool_name"] == "slow_operation"
        assert error.context["timeout_seconds"] == 30.0

    def test_tool_timeout_error_with_context(self) -> None:
        """ToolTimeoutError should include additional context."""
        error = ToolTimeoutError("batch_process", 60.0, batch_size=1000)

        assert "batch_process" in str(error)
        assert "60.0s" in str(error)
        assert "batch_size=1000" in str(error)

    def test_tool_timeout_error_inherits_from_tool_error(self) -> None:
        """ToolTimeoutError should inherit from ToolError."""
        error = ToolTimeoutError("test_tool", 10.0)
        assert isinstance(error, ToolError)

    def test_tool_timeout_error_unique_code(self) -> None:
        """ToolTimeoutError should have unique error code."""
        error = ToolTimeoutError("test_tool", 10.0)
        assert error.error_code == "TOOL_TIMEOUT"


class TestRateLimitExceededError:
    """Tests for RateLimitExceededError exception."""

    def test_rate_limit_exceeded_error_message(self) -> None:
        """RateLimitExceededError should format message with tenant and limits."""
        error = RateLimitExceededError("tenant_123", 100, 60)

        assert "Rate limit exceeded for tenant 'tenant_123'" in str(error)
        assert "100 requests per 60s" in str(error)
        assert error.error_code == "RATE_LIMIT_EXCEEDED"
        assert error.context["tenant_id"] == "tenant_123"
        assert error.context["limit"] == 100
        assert error.context["window_seconds"] == 60

    def test_rate_limit_exceeded_error_with_context(self) -> None:
        """RateLimitExceededError should include additional context."""
        error = RateLimitExceededError("tenant_456", 50, 30, current_usage=55, tool_name="api_call")

        assert "tenant_456" in str(error)
        assert "50 requests per 30s" in str(error)
        assert "current_usage=55" in str(error)
        assert "tool_name=api_call" in str(error)

    def test_rate_limit_exceeded_error_inherits_from_tool_error(self) -> None:
        """RateLimitExceededError should inherit from ToolError."""
        error = RateLimitExceededError("tenant_123", 100, 60)
        assert isinstance(error, ToolError)

    def test_rate_limit_exceeded_error_unique_code(self) -> None:
        """RateLimitExceededError should have unique error code."""
        error = RateLimitExceededError("tenant_123", 100, 60)
        assert error.error_code == "RATE_LIMIT_EXCEEDED"


class TestCostBudgetExceededError:
    """Tests for CostBudgetExceededError exception."""

    def test_cost_budget_exceeded_error_message(self) -> None:
        """CostBudgetExceededError should format message with task and costs."""
        error = CostBudgetExceededError("task_789", 10.0, 12.5)

        assert "Cost budget exceeded for task 'task_789'" in str(error)
        assert "current cost $12.5000 exceeds budget $10.0000" in str(error)
        assert error.error_code == "COST_BUDGET_EXCEEDED"
        assert error.context["task_id"] == "task_789"
        assert error.context["budget"] == 10.0
        assert error.context["current_cost"] == 12.5

    def test_cost_budget_exceeded_error_with_context(self) -> None:
        """CostBudgetExceededError should include additional context."""
        error = CostBudgetExceededError("task_abc", 5.0, 5.25, tool_name="llm_call", model="gpt-4")

        assert "task_abc" in str(error)
        assert "$5.2500 exceeds budget $5.0000" in str(error)
        assert "tool_name=llm_call" in str(error)
        assert "model=gpt-4" in str(error)

    def test_cost_budget_exceeded_error_inherits_from_tool_error(self) -> None:
        """CostBudgetExceededError should inherit from ToolError."""
        error = CostBudgetExceededError("task_123", 10.0, 11.0)
        assert isinstance(error, ToolError)

    def test_cost_budget_exceeded_error_unique_code(self) -> None:
        """CostBudgetExceededError should have unique error code."""
        error = CostBudgetExceededError("task_123", 10.0, 11.0)
        assert error.error_code == "COST_BUDGET_EXCEEDED"


class TestModelNotApprovedError:
    """Tests for ModelNotApprovedError exception."""

    def test_model_not_approved_error_message(self) -> None:
        """ModelNotApprovedError should format message with model name."""
        error = ModelNotApprovedError("gpt-5-turbo")

        assert "Model 'gpt-5-turbo' is not in the approved models list" in str(error)
        assert error.error_code == "MODEL_NOT_APPROVED"
        assert error.context["model_name"] == "gpt-5-turbo"

    def test_model_not_approved_error_with_approved_list(self) -> None:
        """ModelNotApprovedError should include approved models list."""
        approved = ["gpt-4", "gpt-3.5-turbo", "claude-3"]
        error = ModelNotApprovedError("gpt-5-turbo", approved_models=approved)

        assert "gpt-5-turbo" in str(error)
        assert "Approved models: gpt-4, gpt-3.5-turbo, claude-3" in str(error)
        assert error.context["approved_models"] == approved

    def test_model_not_approved_error_with_context(self) -> None:
        """ModelNotApprovedError should include additional context."""
        error = ModelNotApprovedError("custom-model", tenant_id="tenant_999", tool_name="llm_tool")

        assert "custom-model" in str(error)
        assert "tenant_id=tenant_999" in str(error)
        assert "tool_name=llm_tool" in str(error)

    def test_model_not_approved_error_inherits_from_tool_error(self) -> None:
        """ModelNotApprovedError should inherit from ToolError."""
        error = ModelNotApprovedError("test_model")
        assert isinstance(error, ToolError)

    def test_model_not_approved_error_unique_code(self) -> None:
        """ModelNotApprovedError should have unique error code."""
        error = ModelNotApprovedError("test_model")
        assert error.error_code == "MODEL_NOT_APPROVED"


class TestErrorCodeUniqueness:
    """Tests to verify all error codes are unique."""

    def test_all_error_codes_are_unique(self) -> None:
        """All exception classes should have unique error codes."""
        error_classes = [
            ToolError,
            ToolNotFoundError,
            ToolAlreadyRegisteredError,
            ToolValidationError,
            ToolExecutionError,
            ToolTimeoutError,
            RateLimitExceededError,
            CostBudgetExceededError,
            ModelNotApprovedError,
        ]

        error_codes = [cls.error_code for cls in error_classes]
        assert len(error_codes) == len(set(error_codes)), "Error codes must be unique"

    def test_error_codes_are_uppercase_with_underscores(self) -> None:
        """Error codes should follow UPPER_CASE_WITH_UNDERSCORES convention."""
        error_classes = [
            ToolError,
            ToolNotFoundError,
            ToolAlreadyRegisteredError,
            ToolValidationError,
            ToolExecutionError,
            ToolTimeoutError,
            RateLimitExceededError,
            CostBudgetExceededError,
            ModelNotApprovedError,
        ]

        for cls in error_classes:
            code = cls.error_code
            assert code.isupper(), f"{cls.__name__}.error_code should be uppercase"
            assert " " not in code, f"{cls.__name__}.error_code should not contain spaces"


class TestExceptionImports:
    """Tests to verify exceptions are importable from tools module."""

    def test_exceptions_importable_from_tools_module(self) -> None:
        """All exceptions should be importable from omniforge.tools."""
        from omniforge.tools import (
            CostBudgetExceededError,
            ModelNotApprovedError,
            RateLimitExceededError,
            ToolAlreadyRegisteredError,
            ToolError,
            ToolExecutionError,
            ToolNotFoundError,
            ToolTimeoutError,
            ToolValidationError,
        )

        # Verify imported classes are the correct types
        assert issubclass(ToolError, Exception)
        assert issubclass(ToolNotFoundError, ToolError)
        assert issubclass(ToolAlreadyRegisteredError, ToolError)
        assert issubclass(ToolValidationError, ToolError)
        assert issubclass(ToolExecutionError, ToolError)
        assert issubclass(ToolTimeoutError, ToolError)
        assert issubclass(RateLimitExceededError, ToolError)
        assert issubclass(CostBudgetExceededError, ToolError)
        assert issubclass(ModelNotApprovedError, ToolError)
