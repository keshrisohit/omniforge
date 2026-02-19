"""Tests for tool base interfaces and models."""

from typing import Any, AsyncIterator

import pytest

from omniforge.tools import (
    AuditLevel,
    BaseTool,
    ParameterType,
    StreamingTool,
    ToolCallContext,
    ToolDefinition,
    ToolParameter,
    ToolPermissions,
    ToolResult,
    ToolRetryConfig,
    ToolType,
    ToolValidationError,
    ToolVisibilityConfig,
    VisibilityLevel,
)


class TestToolParameter:
    """Tests for ToolParameter model."""

    def test_create_required_parameter(self) -> None:
        """Should create a required parameter with valid configuration."""
        param = ToolParameter(
            name="input_text",
            type=ParameterType.STRING,
            description="Text to process",
            required=True,
        )
        assert param.name == "input_text"
        assert param.type == ParameterType.STRING
        assert param.required is True
        assert param.default is None

    def test_create_optional_parameter_with_default(self) -> None:
        """Should create an optional parameter with default value."""
        param = ToolParameter(
            name="max_retries",
            type=ParameterType.INTEGER,
            description="Maximum retry attempts",
            required=False,
            default=3,
        )
        assert param.name == "max_retries"
        assert param.default == 3
        assert param.required is False

    def test_invalid_parameter_name_raises_error(self) -> None:
        """Should raise error for invalid parameter names."""
        with pytest.raises(ValueError, match="must be snake_case"):
            ToolParameter(
                name="InvalidName",
                type=ParameterType.STRING,
                description="Test",
                required=True,
            )

    def test_parameter_name_with_numbers_allowed(self) -> None:
        """Should allow parameter names with numbers."""
        param = ToolParameter(
            name="param_123",
            type=ParameterType.STRING,
            description="Test",
            required=True,
        )
        assert param.name == "param_123"


class TestToolRetryConfig:
    """Tests for ToolRetryConfig model."""

    def test_default_retry_config(self) -> None:
        """Should create retry config with sensible defaults."""
        config = ToolRetryConfig()
        assert config.max_retries == 3
        assert config.backoff_ms == 1000
        assert config.backoff_multiplier == 2.0
        assert config.retryable_errors == []

    def test_custom_retry_config(self) -> None:
        """Should create retry config with custom values."""
        config = ToolRetryConfig(
            max_retries=5,
            backoff_ms=500,
            backoff_multiplier=1.5,
            retryable_errors=["TimeoutError", "ConnectionError"],
        )
        assert config.max_retries == 5
        assert config.backoff_ms == 500
        assert config.backoff_multiplier == 1.5
        assert len(config.retryable_errors) == 2

    def test_negative_max_retries_raises_error(self) -> None:
        """Should raise error for negative max_retries."""
        with pytest.raises(ValueError):
            ToolRetryConfig(max_retries=-1)

    def test_backoff_multiplier_less_than_one_raises_error(self) -> None:
        """Should raise error for backoff multiplier less than 1."""
        with pytest.raises(ValueError):
            ToolRetryConfig(backoff_multiplier=0.5)


class TestToolVisibilityConfig:
    """Tests for ToolVisibilityConfig model."""

    def test_default_visibility_config(self) -> None:
        """Should create visibility config with defaults."""
        config = ToolVisibilityConfig()
        assert config.default_level == VisibilityLevel.FULL
        assert config.summary_template is None
        assert config.sensitive_fields == []

    def test_visibility_config_with_template(self) -> None:
        """Should create visibility config with summary template."""
        config = ToolVisibilityConfig(
            default_level=VisibilityLevel.SUMMARY,
            summary_template="Processed {count} items in {duration}ms",
            sensitive_fields=["api_key", "password"],
        )
        assert config.default_level == VisibilityLevel.SUMMARY
        assert config.summary_template is not None
        assert len(config.sensitive_fields) == 2

    def test_unbalanced_braces_in_template_raises_error(self) -> None:
        """Should raise error for template with unbalanced braces."""
        with pytest.raises(ValueError, match="unbalanced braces"):
            ToolVisibilityConfig(summary_template="Missing closing brace {field")


class TestToolPermissions:
    """Tests for ToolPermissions model."""

    def test_default_permissions(self) -> None:
        """Should create permissions with defaults."""
        perms = ToolPermissions()
        assert perms.required_roles == []
        assert perms.audit_level == AuditLevel.BASIC

    def test_permissions_with_roles(self) -> None:
        """Should create permissions with required roles."""
        perms = ToolPermissions(required_roles=["admin", "power_user"], audit_level=AuditLevel.FULL)
        assert len(perms.required_roles) == 2
        assert perms.audit_level == AuditLevel.FULL


class TestToolDefinition:
    """Tests for ToolDefinition model."""

    def test_minimal_tool_definition(self) -> None:
        """Should create tool definition with minimal required fields."""
        definition = ToolDefinition(
            name="test_tool",
            type=ToolType.FUNCTION,
            description="A test tool",
        )
        assert definition.name == "test_tool"
        assert definition.type == ToolType.FUNCTION
        assert definition.version == "1.0.0"
        assert len(definition.parameters) == 0

    def test_complete_tool_definition(self) -> None:
        """Should create tool definition with all fields."""
        param = ToolParameter(
            name="input", type=ParameterType.STRING, description="Input", required=True
        )
        definition = ToolDefinition(
            name="complex_tool",
            type=ToolType.API,
            description="A complex tool",
            version="2.1.0",
            parameters=[param],
            timeout_ms=5000,
            retry_config=ToolRetryConfig(max_retries=5),
            cache_ttl_seconds=300,
            visibility=ToolVisibilityConfig(default_level=VisibilityLevel.SUMMARY),
            permissions=ToolPermissions(required_roles=["admin"]),
        )
        assert definition.name == "complex_tool"
        assert definition.timeout_ms == 5000
        assert len(definition.parameters) == 1
        assert definition.cache_ttl_seconds == 300

    def test_invalid_tool_name_raises_error(self) -> None:
        """Should raise error for invalid tool name."""
        with pytest.raises(ValueError, match="must be snake_case"):
            ToolDefinition(name="InvalidToolName", type=ToolType.FUNCTION, description="Test")

    def test_invalid_version_format_raises_error(self) -> None:
        """Should raise error for invalid version format."""
        with pytest.raises(ValueError, match="must follow semver"):
            ToolDefinition(
                name="test_tool",
                type=ToolType.FUNCTION,
                description="Test",
                version="invalid",
            )

    def test_valid_semver_with_prerelease(self) -> None:
        """Should accept valid semver with prerelease identifier."""
        definition = ToolDefinition(
            name="test_tool",
            type=ToolType.FUNCTION,
            description="Test",
            version="1.0.0-alpha.1",
        )
        assert definition.version == "1.0.0-alpha.1"


class TestToolCallContext:
    """Tests for ToolCallContext model."""

    def test_minimal_context(self) -> None:
        """Should create context with required fields only."""
        context = ToolCallContext(
            correlation_id="corr-123", task_id="task-456", agent_id="agent-789"
        )
        assert context.correlation_id == "corr-123"
        assert context.task_id == "task-456"
        assert context.agent_id == "agent-789"
        assert context.tenant_id is None

    def test_complete_context(self) -> None:
        """Should create context with all fields."""
        context = ToolCallContext(
            correlation_id="corr-123",
            task_id="task-456",
            agent_id="agent-789",
            tenant_id="tenant-001",
            chain_id="chain-999",
            max_tokens=1000,
            max_cost_usd=0.50,
        )
        assert context.tenant_id == "tenant-001"
        assert context.chain_id == "chain-999"
        assert context.max_tokens == 1000
        assert context.max_cost_usd == 0.50


class TestToolResult:
    """Tests for ToolResult model."""

    def test_successful_result(self) -> None:
        """Should create successful result with data."""
        result = ToolResult(
            success=True,
            result={"output": "processed data", "count": 42},
            duration_ms=150,
            tokens_used=100,
            cost_usd=0.002,
        )
        assert result.success is True
        assert result.result is not None
        assert result.result["count"] == 42
        assert result.error is None
        assert result.tokens_used == 100

    def test_failed_result_with_error(self) -> None:
        """Should create failed result with error message."""
        result = ToolResult(
            success=False, error="Connection timeout", duration_ms=5000, retry_count=3
        )
        assert result.success is False
        assert result.error == "Connection timeout"
        assert result.result is None
        assert result.retry_count == 3

    def test_cached_result(self) -> None:
        """Should create result from cache with metadata."""
        result = ToolResult(
            success=True,
            result={"cached_data": "value"},
            duration_ms=5,
            cached=True,
        )
        assert result.cached is True
        assert result.duration_ms == 5

    def test_failed_result_without_error_raises_error(self) -> None:
        """Should raise error when success is False but no error message."""
        with pytest.raises(ValueError, match="Error message is required"):
            ToolResult(success=False, duration_ms=100)

    def test_truncate_for_context_no_truncatable_fields(self) -> None:
        """Should return self when no truncatable fields specified."""
        result = ToolResult(
            success=True,
            result={"data": [1, 2, 3, 4, 5]},
            duration_ms=100,
        )
        truncated = result.truncate_for_context(max_items=2)
        assert truncated is result
        assert truncated.result["data"] == [1, 2, 3, 4, 5]

    def test_truncate_for_context_preserves_metadata(self) -> None:
        """Should truncate only specified fields while preserving metadata."""
        result = ToolResult(
            success=True,
            result={
                "matches": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
                "match_count": 12,
                "pattern": "*.py",
                "base_path": "/src",
            },
            duration_ms=150,
            truncatable_fields=["matches"],
        )
        truncated = result.truncate_for_context(max_items=3)

        # Matches should be truncated
        assert len(truncated.result["matches"]) == 3
        assert truncated.result["matches"] == [1, 2, 3]

        # Metadata should be preserved
        assert truncated.result["match_count"] == 12
        assert truncated.result["pattern"] == "*.py"
        assert truncated.result["base_path"] == "/src"

        # Should add truncation note
        assert "matches_truncation_note" in truncated.result
        assert "Showing 3 of 12 items" in truncated.result["matches_truncation_note"]

    def test_truncate_for_context_custom_message(self) -> None:
        """Should use custom truncation message when provided."""
        result = ToolResult(
            success=True,
            result={"matches": list(range(100))},
            duration_ms=100,
            truncatable_fields=["matches"],
        )
        truncated = result.truncate_for_context(
            max_items=5, truncation_message="Results limited for display"
        )

        assert len(truncated.result["matches"]) == 5
        assert truncated.result["matches_truncation_note"] == "Results limited for display"

    def test_truncate_for_context_no_truncation_needed(self) -> None:
        """Should not truncate when list is within limit."""
        result = ToolResult(
            success=True,
            result={"matches": [1, 2, 3]},
            duration_ms=100,
            truncatable_fields=["matches"],
        )
        truncated = result.truncate_for_context(max_items=10)

        # Should not truncate
        assert len(truncated.result["matches"]) == 3
        # Should not add truncation note
        assert "matches_truncation_note" not in truncated.result

    def test_truncate_for_context_multiple_fields(self) -> None:
        """Should truncate multiple specified fields."""
        result = ToolResult(
            success=True,
            result={
                "matches": list(range(20)),
                "errors": list(range(15)),
                "metadata": {"count": 20},
            },
            duration_ms=100,
            truncatable_fields=["matches", "errors"],
        )
        truncated = result.truncate_for_context(max_items=5)

        # Both fields should be truncated
        assert len(truncated.result["matches"]) == 5
        assert len(truncated.result["errors"]) == 5

        # Metadata should be preserved
        assert truncated.result["metadata"]["count"] == 20

        # Both should have truncation notes
        assert "matches_truncation_note" in truncated.result
        assert "errors_truncation_note" in truncated.result

    def test_truncate_for_context_non_list_field_ignored(self) -> None:
        """Should ignore non-list fields in truncatable_fields."""
        result = ToolResult(
            success=True,
            result={
                "matches": list(range(20)),
                "count": 20,  # Not a list
                "name": "test",  # Not a list
            },
            duration_ms=100,
            truncatable_fields=["matches", "count", "name"],
        )
        truncated = result.truncate_for_context(max_items=5)

        # Only matches should be truncated (it's a list)
        assert len(truncated.result["matches"]) == 5

        # Non-list fields should remain unchanged
        assert truncated.result["count"] == 20
        assert truncated.result["name"] == "test"

        # Only matches should have truncation note
        assert "matches_truncation_note" in truncated.result
        assert "count_truncation_note" not in truncated.result
        assert "name_truncation_note" not in truncated.result

    def test_truncate_for_context_missing_field(self) -> None:
        """Should handle missing truncatable fields gracefully."""
        result = ToolResult(
            success=True,
            result={"matches": list(range(20))},
            duration_ms=100,
            truncatable_fields=["matches", "nonexistent_field"],
        )
        # Should not raise error
        truncated = result.truncate_for_context(max_items=5)

        assert len(truncated.result["matches"]) == 5
        # Should only have note for existing field
        assert "matches_truncation_note" in truncated.result
        assert "nonexistent_field_truncation_note" not in truncated.result


# Concrete test implementation of BaseTool for testing
class MockTool(BaseTool):
    """Mock tool implementation for testing."""

    def __init__(self, definition: ToolDefinition) -> None:
        """Initialize mock tool with definition."""
        self._definition = definition

    @property
    def definition(self) -> ToolDefinition:
        """Get tool definition."""
        return self._definition

    async def execute(self, context: ToolCallContext, arguments: dict[str, Any]) -> ToolResult:
        """Mock execution that returns success."""
        return ToolResult(
            success=True,
            result={"executed": True, "args": arguments},
            duration_ms=100,
        )


class TestBaseTool:
    """Tests for BaseTool abstract class."""

    def test_validate_arguments_success(self) -> None:
        """Should validate arguments that match definition."""
        param = ToolParameter(
            name="input", type=ParameterType.STRING, description="Input", required=True
        )
        definition = ToolDefinition(
            name="test_tool",
            type=ToolType.FUNCTION,
            description="Test",
            parameters=[param],
        )
        tool = MockTool(definition)

        # Should not raise
        tool.validate_arguments({"input": "test value"})

    def test_validate_arguments_missing_required_raises_error(self) -> None:
        """Should raise error when required parameter is missing."""
        param = ToolParameter(
            name="required_param",
            type=ParameterType.STRING,
            description="Required",
            required=True,
        )
        definition = ToolDefinition(
            name="test_tool",
            type=ToolType.FUNCTION,
            description="Test",
            parameters=[param],
        )
        tool = MockTool(definition)

        with pytest.raises(ToolValidationError, match="Required parameter"):
            tool.validate_arguments({})

    def test_validate_arguments_unknown_parameter_raises_error(self) -> None:
        """Should raise error for unknown parameters."""
        definition = ToolDefinition(
            name="test_tool", type=ToolType.FUNCTION, description="Test", parameters=[]
        )
        tool = MockTool(definition)

        with pytest.raises(ToolValidationError, match="Unknown parameters"):
            tool.validate_arguments({"unknown_param": "value"})

    def test_validate_arguments_optional_parameter_allowed(self) -> None:
        """Should allow missing optional parameters."""
        param = ToolParameter(
            name="optional",
            type=ParameterType.STRING,
            description="Optional",
            required=False,
        )
        definition = ToolDefinition(
            name="test_tool",
            type=ToolType.FUNCTION,
            description="Test",
            parameters=[param],
        )
        tool = MockTool(definition)

        # Should not raise
        tool.validate_arguments({})

    def test_generate_summary_for_success(self) -> None:
        """Should generate summary for successful result."""
        definition = ToolDefinition(name="test_tool", type=ToolType.FUNCTION, description="Test")
        tool = MockTool(definition)

        result = ToolResult(
            success=True, result={"field1": "value1", "field2": "value2"}, duration_ms=100
        )
        summary = tool.generate_summary(result)

        assert "test_tool" in summary
        assert "succeeded" in summary
        assert "2 result fields" in summary

    def test_generate_summary_for_failure(self) -> None:
        """Should generate summary for failed result."""
        definition = ToolDefinition(name="test_tool", type=ToolType.FUNCTION, description="Test")
        tool = MockTool(definition)

        result = ToolResult(success=False, error="Something went wrong", duration_ms=100)
        summary = tool.generate_summary(result)

        assert "test_tool" in summary
        assert "failed" in summary
        assert "Something went wrong" in summary

    def test_generate_summary_with_template(self) -> None:
        """Should use template when available for summary."""
        visibility = ToolVisibilityConfig(summary_template="Processed {count} items successfully")
        definition = ToolDefinition(
            name="test_tool",
            type=ToolType.FUNCTION,
            description="Test",
            visibility=visibility,
        )
        tool = MockTool(definition)

        result = ToolResult(success=True, result={"count": 42}, duration_ms=100)
        summary = tool.generate_summary(result)

        assert summary == "Processed 42 items successfully"

    def test_generate_summary_template_fallback_on_error(self) -> None:
        """Should fall back to default summary if template fails."""
        visibility = ToolVisibilityConfig(summary_template="Missing field: {nonexistent}")
        definition = ToolDefinition(
            name="test_tool",
            type=ToolType.FUNCTION,
            description="Test",
            visibility=visibility,
        )
        tool = MockTool(definition)

        result = ToolResult(success=True, result={"other": "value"}, duration_ms=100)
        summary = tool.generate_summary(result)

        # Should fall back to default
        assert "test_tool" in summary
        assert "succeeded" in summary

    @pytest.mark.asyncio
    async def test_execute_returns_result(self) -> None:
        """Should execute tool and return result."""
        definition = ToolDefinition(name="test_tool", type=ToolType.FUNCTION, description="Test")
        tool = MockTool(definition)

        context = ToolCallContext(
            correlation_id="corr-123", task_id="task-456", agent_id="agent-789"
        )
        result = await tool.execute(context, {"input": "test"})

        assert result.success is True
        assert result.result is not None
        assert result.result["executed"] is True


# Concrete test implementation of StreamingTool
class MockStreamingTool(StreamingTool):
    """Mock streaming tool implementation for testing."""

    def __init__(self, definition: ToolDefinition) -> None:
        """Initialize mock streaming tool."""
        self._definition = definition

    @property
    def definition(self) -> ToolDefinition:
        """Get tool definition."""
        return self._definition

    async def execute(self, context: ToolCallContext, arguments: dict[str, Any]) -> ToolResult:
        """Mock execution that aggregates streaming results."""
        chunks = []
        async for chunk in self.execute_streaming(context, arguments):
            chunks.append(chunk)

        return ToolResult(
            success=True,
            result={"chunks": len(chunks), "data": chunks},
            duration_ms=200,
        )

    async def execute_streaming(
        self, context: ToolCallContext, arguments: dict[str, Any]
    ) -> AsyncIterator[dict[str, Any]]:
        """Mock streaming execution that yields chunks."""
        for i in range(3):
            yield {"chunk": i, "data": f"chunk_{i}"}


class TestStreamingTool:
    """Tests for StreamingTool abstract class."""

    @pytest.mark.asyncio
    async def test_execute_streaming_yields_chunks(self) -> None:
        """Should yield multiple chunks from streaming execution."""
        definition = ToolDefinition(
            name="streaming_tool", type=ToolType.FUNCTION, description="Streaming test"
        )
        tool = MockStreamingTool(definition)

        context = ToolCallContext(
            correlation_id="corr-123", task_id="task-456", agent_id="agent-789"
        )

        chunks = []
        async for chunk in tool.execute_streaming(context, {}):
            chunks.append(chunk)

        assert len(chunks) == 3
        assert chunks[0]["chunk"] == 0
        assert chunks[2]["chunk"] == 2

    @pytest.mark.asyncio
    async def test_execute_aggregates_streaming_results(self) -> None:
        """Should aggregate streaming results in execute method."""
        definition = ToolDefinition(
            name="streaming_tool", type=ToolType.FUNCTION, description="Streaming test"
        )
        tool = MockStreamingTool(definition)

        context = ToolCallContext(
            correlation_id="corr-123", task_id="task-456", agent_id="agent-789"
        )
        result = await tool.execute(context, {})

        assert result.success is True
        assert result.result["chunks"] == 3

    @pytest.mark.asyncio
    async def test_streaming_tool_inherits_validation(self) -> None:
        """Should inherit validation from BaseTool."""
        param = ToolParameter(
            name="required", type=ParameterType.STRING, description="Required", required=True
        )
        definition = ToolDefinition(
            name="streaming_tool",
            type=ToolType.FUNCTION,
            description="Test",
            parameters=[param],
        )
        tool = MockStreamingTool(definition)

        # Should raise validation error for missing required parameter
        with pytest.raises(ToolValidationError):
            tool.validate_arguments({})
