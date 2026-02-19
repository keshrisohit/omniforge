"""Base interfaces and models for OmniForge tool system.

This module defines the core abstractions that all tools must implement,
including configuration models, execution context, and result structures.
"""

import re
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, AsyncIterator, Optional

from pydantic import BaseModel, Field, field_validator

from omniforge.tools.types import ToolType, VisibilityLevel


class AuditLevel(str, Enum):
    """Audit level for tool execution."""

    NONE = "none"
    BASIC = "basic"
    DETAILED = "detailed"
    FULL = "full"


class ParameterType(str, Enum):
    """Parameter types for tool configuration."""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


class ToolParameter(BaseModel):
    """Specification for a tool parameter."""

    name: str = Field(description="Parameter name")
    type: ParameterType = Field(description="Parameter type")
    description: str = Field(description="Parameter description")
    required: bool = Field(default=False, description="Whether parameter is required")
    default: Optional[Any] = Field(default=None, description="Default value if not required")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate parameter name follows snake_case convention."""
        if not re.match(r"^[a-z][a-z0-9_]*$", v):
            raise ValueError(
                f"Parameter name '{v}' must be snake_case (lowercase letters, "
                "numbers, underscores, starting with a letter)"
            )
        return v


class ToolRetryConfig(BaseModel):
    """Configuration for tool execution retry behavior."""

    max_retries: int = Field(default=3, ge=0, description="Maximum number of retry attempts")
    backoff_ms: int = Field(default=1000, ge=0, description="Initial backoff delay in milliseconds")
    backoff_multiplier: float = Field(
        default=2.0, ge=1.0, description="Multiplier for exponential backoff"
    )
    retryable_errors: list[str] = Field(
        default_factory=list,
        description="List of error types/patterns that should trigger retries",
    )


class ToolVisibilityConfig(BaseModel):
    """Configuration for tool result visibility and summarization."""

    default_level: VisibilityLevel = Field(
        default=VisibilityLevel.FULL,
        description="Default visibility level for tool results",
    )
    summary_template: Optional[str] = Field(
        default=None,
        description="Template for generating result summaries (uses {field} placeholders)",
    )
    sensitive_fields: list[str] = Field(
        default_factory=list,
        description="List of result fields that contain sensitive information",
    )

    @field_validator("summary_template")
    @classmethod
    def validate_template(cls, v: Optional[str]) -> Optional[str]:
        """Validate summary template has balanced braces."""
        if v is None:
            return v
        open_count = v.count("{")
        close_count = v.count("}")
        if open_count != close_count:
            raise ValueError("Summary template has unbalanced braces")
        return v


class ToolPermissions(BaseModel):
    """Permission configuration for tool execution."""

    required_roles: list[str] = Field(
        default_factory=list,
        description="List of roles required to execute this tool",
    )
    audit_level: AuditLevel = Field(
        default=AuditLevel.BASIC,
        description="Level of audit logging for tool execution",
    )


class ToolDefinition(BaseModel):
    """Complete specification for a tool."""

    name: str = Field(description="Unique tool name")
    type: ToolType = Field(description="Type of tool")
    description: str = Field(description="Human-readable tool description")
    version: str = Field(default="1.0.0", description="Tool version (semver)")
    parameters: list[ToolParameter] = Field(
        default_factory=list,
        description="List of parameters the tool accepts",
    )
    timeout_ms: int = Field(default=120000, ge=1000, description="Execution timeout in milliseconds")
    retry_config: ToolRetryConfig = Field(
        default_factory=ToolRetryConfig,
        description="Retry behavior configuration",
    )
    cache_ttl_seconds: Optional[int] = Field(
        default=None, ge=0, description="Cache TTL in seconds (None = no caching)"
    )
    visibility: ToolVisibilityConfig = Field(
        default_factory=ToolVisibilityConfig,
        description="Visibility and summarization configuration",
    )
    permissions: ToolPermissions = Field(
        default_factory=ToolPermissions,
        description="Permission requirements for tool execution",
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate tool name follows snake_case convention."""
        if not re.match(r"^[a-z][a-z0-9_]*$", v):
            raise ValueError(
                f"Tool name '{v}' must be snake_case (lowercase letters, "
                "numbers, underscores, starting with a letter)"
            )
        return v

    @field_validator("version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        """Validate version follows semver format."""
        if not re.match(r"^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?$", v):
            raise ValueError(f"Version '{v}' must follow semver format (e.g., '1.0.0')")
        return v


class ToolCallContext(BaseModel):
    """Execution context for a tool call."""

    correlation_id: str = Field(description="Unique ID to correlate call and result")
    task_id: str = Field(description="ID of the task this call is part of")
    agent_id: str = Field(description="ID of the agent making the call")
    tenant_id: Optional[str] = Field(default=None, description="Tenant ID for multi-tenancy")
    chain_id: Optional[str] = Field(
        default=None, description="ID of the reasoning chain this call belongs to"
    )
    max_tokens: Optional[int] = Field(
        default=None, ge=1, description="Maximum tokens allowed for this call"
    )
    max_cost_usd: Optional[float] = Field(
        default=None, ge=0.0, description="Maximum cost in USD allowed for this call"
    )


class ToolResult(BaseModel):
    """Result of a tool execution."""

    success: bool = Field(description="Whether the tool execution succeeded")
    result: Optional[dict[str, Any]] = Field(
        default=None, description="Result data from successful execution"
    )
    error: Optional[str] = Field(default=None, description="Error message if execution failed")
    duration_ms: int = Field(ge=0, description="Execution duration in milliseconds")
    tokens_used: int = Field(default=0, ge=0, description="Tokens consumed (for LLM tools)")
    cost_usd: float = Field(default=0.0, ge=0.0, description="Cost in USD (for LLM tools)")
    cached: bool = Field(default=False, description="Whether result was served from cache")
    retry_count: int = Field(default=0, ge=0, description="Number of retries attempted")
    truncatable_fields: list[str] = Field(
        default_factory=list,
        description="Fields that can be truncated to save context (others preserved)",
    )

    def model_post_init(self, __context: Any) -> None:
        """Validate error is present when success is False."""
        if not self.success and not self.error:
            raise ValueError("Error message is required when success is False")

    def truncate_for_context(
        self, max_items: int = 10, truncation_message: Optional[str] = None
    ) -> "ToolResult":
        """Truncate result to save context window space.

        Only truncates fields specified in truncatable_fields list, preserving
        all other metadata. Useful for tools that return large lists (e.g., glob matches).

        Args:
            max_items: Maximum items to keep in truncatable fields (default: 10)
            truncation_message: Custom message to add when truncating (optional)

        Returns:
            New ToolResult with truncated data
        """
        if not self.result or not self.truncatable_fields:
            return self

        # Create a copy of the result
        truncated_result = self.result.copy()

        # Truncate only specified fields
        for field_name in self.truncatable_fields:
            if field_name in truncated_result:
                field_value = truncated_result[field_name]

                # Only truncate if it's a list
                if isinstance(field_value, list) and len(field_value) > max_items:
                    truncated_result[field_name] = field_value[:max_items]

                    # Add truncation indicator
                    if truncation_message:
                        truncated_result[f"{field_name}_truncation_note"] = truncation_message
                    else:
                        original_count = len(field_value)
                        truncated_result[f"{field_name}_truncation_note"] = (
                            f"Showing {max_items} of {original_count} items"
                        )

        # Return new result with truncated data
        return ToolResult(
            success=self.success,
            result=truncated_result,
            error=self.error,
            duration_ms=self.duration_ms,
            tokens_used=self.tokens_used,
            cost_usd=self.cost_usd,
            cached=self.cached,
            retry_count=self.retry_count,
            truncatable_fields=self.truncatable_fields,
        )


class BaseTool(ABC):
    """Abstract base class for all tools.

    All tools must implement this interface to be usable in the OmniForge platform.
    Provides standard execution interface with validation and summarization.
    """

    @property
    @abstractmethod
    def definition(self) -> ToolDefinition:
        """Get the tool's definition.

        Returns:
            ToolDefinition describing this tool's capabilities and configuration
        """
        pass

    @abstractmethod
    async def execute(self, context: ToolCallContext, arguments: dict[str, Any]) -> ToolResult:
        """Execute the tool with given arguments.

        Args:
            context: Execution context containing task/agent/tenant information
            arguments: Tool-specific arguments validated against the definition

        Returns:
            ToolResult containing execution outcome and metadata

        Raises:
            ToolValidationError: If arguments are invalid
            ToolExecutionError: If execution fails
            ToolTimeoutError: If execution exceeds timeout
        """
        pass

    def validate_arguments(self, arguments: dict[str, Any]) -> None:
        """Validate arguments against tool definition parameters.

        Args:
            arguments: Arguments to validate

        Raises:
            ToolValidationError: If validation fails
        """
        from omniforge.tools.errors import ToolValidationError

        # Check required parameters
        for param in self.definition.parameters:
            if param.required and param.name not in arguments:
                raise ToolValidationError(
                    tool_name=self.definition.name,
                    validation_error=f"Required parameter '{param.name}' missing",
                )

        # Check for unknown parameters
        known_params = {p.name for p in self.definition.parameters}
        unknown_params = set(arguments.keys()) - known_params
        if unknown_params:
            raise ToolValidationError(
                tool_name=self.definition.name,
                validation_error=(f"Unknown parameters: {', '.join(sorted(unknown_params))}"),
            )

    def generate_summary(self, result: ToolResult) -> str:
        """Generate a human-readable summary of the tool result.

        Args:
            result: The tool result to summarize

        Returns:
            A formatted summary string
        """
        if not result.success:
            return f"Tool '{self.definition.name}' failed: {result.error}"

        # Use template if available
        template = self.definition.visibility.summary_template
        if template and result.result:
            try:
                # Replace {field} placeholders with actual values
                summary = template
                for key, value in result.result.items():
                    placeholder = f"{{{key}}}"
                    if placeholder in summary:
                        summary = summary.replace(placeholder, str(value))

                # Check if there are still unreplaced placeholders
                if "{" in summary and "}" in summary:
                    # Template has missing fields, fall back to default
                    pass
                else:
                    return summary
            except Exception:
                # Fall back to default if template fails
                pass

        # Default summary
        if result.result:
            field_count = len(result.result)
            return (
                f"Tool '{self.definition.name}' succeeded with {field_count} result "
                f"field{'s' if field_count != 1 else ''}"
            )
        return f"Tool '{self.definition.name}' succeeded"


class StreamingTool(BaseTool):
    """Base class for tools that support streaming results.

    Extends BaseTool with async streaming capability for long-running
    operations that produce incremental results.
    """

    @abstractmethod
    async def execute_streaming(
        self, context: ToolCallContext, arguments: dict[str, Any]
    ) -> AsyncIterator[dict[str, Any]]:
        """Execute the tool with streaming results.

        Args:
            context: Execution context containing task/agent/tenant information
            arguments: Tool-specific arguments validated against the definition

        Yields:
            Incremental result chunks as they become available

        Raises:
            ToolValidationError: If arguments are invalid
            ToolExecutionError: If execution fails
            ToolTimeoutError: If execution exceeds timeout
        """
        # This method must be overridden by subclasses
        # The yield statement is needed to make this a generator function
        yield {}  # pragma: no cover
