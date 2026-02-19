"""Configuration and state models for autonomous skill execution.

This module provides data models for configuring and tracking autonomous skill execution:
- AutonomousConfig: Configuration parameters for execution
- PlatformAutonomousConfig: Platform-level configuration with defaults
- ExecutionContext: Context for tracking sub-agent depth and hierarchy
- ExecutionState: Runtime state tracking across iterations
- ExecutionResult: Final execution result wrapper
- ExecutionMetrics: Detailed metrics for execution tracking

Also provides utility functions for:
- parse_duration_ms: Parse duration strings to milliseconds
- validate_skill_config: Validate skill config against platform limits
- merge_configs: Merge platform and skill-level configurations
"""

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class ExecutionContext(BaseModel):
    """Context for tracking sub-agent execution depth and hierarchy.

    This model prevents infinite sub-agent recursion by tracking the depth
    of nested sub-agent calls and enforcing a maximum depth limit.

    Attributes:
        depth: Current execution depth (0 = root, 1 = first sub-agent, etc.)
        max_depth: Maximum allowed depth for sub-agent spawning
        parent_task_id: Task ID of the parent that spawned this context
        root_task_id: Task ID of the root execution (top-level)
        skill_chain: List of skill names in the execution chain (for debugging)
    """

    depth: int = Field(
        default=0,
        ge=0,
        description="Current execution depth (0 = root)",
    )
    max_depth: int = Field(
        default=2,
        ge=0,
        description="Maximum allowed depth for sub-agent spawning",
    )
    parent_task_id: Optional[str] = Field(
        default=None,
        description="Task ID of the parent that spawned this context",
    )
    root_task_id: Optional[str] = Field(
        default=None,
        description="Task ID of the root execution (top-level)",
    )
    skill_chain: list[str] = Field(
        default_factory=list,
        description="List of skill names in the execution chain",
    )

    def create_child_context(
        self, task_id: str, skill_name: Optional[str] = None
    ) -> "ExecutionContext":
        """Create child context for sub-agent execution.

        Args:
            task_id: Task ID of the child execution
            skill_name: Optional skill name to add to the chain

        Returns:
            New ExecutionContext with incremented depth

        Raises:
            ValueError: If maximum depth would be exceeded
        """
        if not self.can_spawn_sub_agent():
            chain_str = " -> ".join(self.skill_chain) if self.skill_chain else "unknown"
            raise ValueError(
                f"Maximum sub-agent depth ({self.max_depth}) exceeded. "
                f"Cannot spawn sub-agent at depth {self.depth}. "
                f"Current skill chain: {chain_str}"
            )

        # Build updated skill chain
        new_chain = list(self.skill_chain)
        if skill_name:
            new_chain.append(skill_name)

        return ExecutionContext(
            depth=self.depth + 1,
            max_depth=self.max_depth,
            parent_task_id=task_id,
            root_task_id=self.root_task_id or task_id,
            skill_chain=new_chain,
        )

    def can_spawn_sub_agent(self) -> bool:
        """Check if another sub-agent level is allowed.

        Returns:
            True if current depth is below max_depth, False otherwise
        """
        return self.depth < self.max_depth

    def get_iteration_budget_for_child(self, base_iterations: int) -> int:
        """Calculate iteration budget for child based on depth.

        Sub-agents get reduced iteration budget:
        - Level 0 (root): 100% of base
        - Level 1 (sub-agent): 50% of base
        - Level 2 (sub-sub-agent): 25% of base

        Args:
            base_iterations: Base iteration budget

        Returns:
            Iteration budget for child (minimum 3)
        """
        child_depth = self.depth + 1
        budget: int = max(3, base_iterations // (2**child_depth))
        return budget


class AutonomousConfig(BaseModel):
    """Configuration for autonomous skill execution.

    This model defines the constraints and parameters for autonomous execution
    of skills using the ReAct pattern.

    Attributes:
        max_iterations: Maximum ReAct loop iterations (1-100)
        max_retries_per_tool: Max retries per tool/approach (1-10)
        timeout_per_iteration_ms: Timeout per iteration in milliseconds (1000-300000)
        early_termination: Allow early termination when goal is reached
        model: Optional LLM model override for skill execution
        temperature: LLM temperature for generation (0.0-2.0)
        enable_error_recovery: Enable automatic error recovery mechanisms
    """

    max_iterations: int = Field(
        default=15,
        ge=1,
        le=100,
        description="Maximum number of ReAct loop iterations",
    )
    max_retries_per_tool: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum retries per tool or approach",
    )
    timeout_per_iteration_ms: int = Field(
        default=30000,
        ge=1000,
        le=300000,
        description="Timeout per iteration in milliseconds",
    )
    early_termination: bool = Field(
        default=True,
        description="Allow early termination when goal is reached",
    )
    model: Optional[str] = Field(
        default=None,
        description="LLM model override for skill execution",
    )
    temperature: float = Field(
        default=0.0,
        ge=0.0,
        le=2.0,
        description="LLM temperature for generation",
    )
    enable_error_recovery: bool = Field(
        default=True,
        description="Enable automatic error recovery mechanisms",
    )


class ExecutionState(BaseModel):
    """Runtime state tracking for autonomous skill execution.

    Tracks the current state of execution across iterations, including
    observations, failures, and partial results.

    Attributes:
        iteration: Current iteration number (0-indexed)
        observations: List of tool call observations/results
        failed_approaches: Mapping of failed approaches to retry counts
        loaded_files: Set of supporting files loaded on-demand
        partial_results: Accumulated partial results from iterations
        error_count: Total number of errors encountered
        start_time: Execution start timestamp
    """

    iteration: int = Field(
        default=0,
        ge=0,
        description="Current iteration number",
    )
    observations: list[dict] = Field(
        default_factory=list,
        description="Tool call observations and results",
    )
    failed_approaches: dict[str, int] = Field(
        default_factory=dict,
        description="Failed approaches with retry counts",
    )
    loaded_files: set[str] = Field(
        default_factory=set,
        description="Supporting files loaded on-demand",
    )
    partial_results: list[str] = Field(
        default_factory=list,
        description="Accumulated partial results",
    )
    error_count: int = Field(
        default=0,
        ge=0,
        description="Total errors encountered",
    )
    start_time: datetime = Field(
        default_factory=datetime.utcnow,
        description="Execution start timestamp",
    )

    model_config = ConfigDict(arbitrary_types_allowed=True)


class ExecutionMetrics(BaseModel):
    """Detailed metrics for autonomous skill execution.

    Tracks token usage, costs, timing, and success/failure rates for
    tool calls and error recovery attempts.

    Attributes:
        total_tokens: Total tokens consumed across all LLM calls
        prompt_tokens: Tokens used in prompts
        completion_tokens: Tokens used in completions
        total_cost: Total cost in USD
        duration_seconds: Total execution duration in seconds
        tool_calls_successful: Number of successful tool calls
        tool_calls_failed: Number of failed tool calls
        error_recoveries: Number of successful error recoveries
        model_used: LLM model used for execution
        estimated_cost_per_call: Estimated cost per LLM call based on model
    """

    total_tokens: int = Field(
        default=0,
        ge=0,
        description="Total tokens consumed",
    )
    prompt_tokens: int = Field(
        default=0,
        ge=0,
        description="Tokens used in prompts",
    )
    completion_tokens: int = Field(
        default=0,
        ge=0,
        description="Tokens used in completions",
    )
    total_cost: float = Field(
        default=0.0,
        ge=0.0,
        description="Total cost in USD",
    )
    duration_seconds: float = Field(
        default=0.0,
        ge=0.0,
        description="Total execution duration in seconds",
    )
    tool_calls_successful: int = Field(
        default=0,
        ge=0,
        description="Number of successful tool calls",
    )
    tool_calls_failed: int = Field(
        default=0,
        ge=0,
        description="Number of failed tool calls",
    )
    error_recoveries: int = Field(
        default=0,
        ge=0,
        description="Number of successful error recoveries",
    )
    model_used: Optional[str] = Field(
        default=None,
        description="LLM model used for execution",
    )
    estimated_cost_per_call: float = Field(
        default=0.0,
        ge=0.0,
        description="Estimated cost per LLM call based on model",
    )


class ExecutionResult(BaseModel):
    """Final result wrapper for autonomous skill execution.

    Contains the execution outcome, metrics, and any error information.

    Attributes:
        success: Whether execution completed successfully
        result: Final result text/output
        iterations_used: Number of iterations executed
        chain_id: Reasoning chain ID for debugging and tracing
        metrics: Detailed execution metrics
        partial_results: Partial results if execution incomplete
        error: Error message if execution failed
    """

    success: bool = Field(
        description="Whether execution completed successfully",
    )
    result: str = Field(
        description="Final result text or output",
    )
    iterations_used: int = Field(
        ge=0,
        description="Number of iterations executed",
    )
    chain_id: str = Field(
        description="Reasoning chain ID for debugging",
    )
    metrics: ExecutionMetrics = Field(
        description="Detailed execution metrics",
    )
    partial_results: list[str] = Field(
        default_factory=list,
        description="Partial results if incomplete",
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if execution failed",
    )


class PlatformAutonomousConfig(BaseModel):
    """Platform-level autonomous execution configuration.

    This model defines platform-wide defaults for autonomous skill execution.
    Skills can override these defaults with their own metadata configuration.

    Attributes:
        default_max_iterations: Default maximum ReAct loop iterations
        default_max_retries_per_tool: Default max retries per tool/approach
        default_timeout_per_iteration_ms: Default timeout per iteration in milliseconds
        enable_error_recovery: Enable automatic error recovery mechanisms
        default_model: Default LLM model for skill execution
        visibility_end_user: Default visibility level for end users
        visibility_developer: Default visibility level for developers
        visibility_admin: Default visibility level for administrators
        cost_limits_enabled: Enable cost tracking and limits
        max_cost_per_execution_usd: Maximum cost per execution in USD
        rate_limits_enabled: Enable rate limiting
        max_iterations_per_minute: Maximum iterations across all executions per minute
    """

    # Default execution settings
    default_max_iterations: int = Field(
        default=15,
        ge=1,
        le=100,
        description="Default maximum ReAct loop iterations",
    )
    default_max_retries_per_tool: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Default max retries per tool or approach",
    )
    default_timeout_per_iteration_ms: int = Field(
        default=30000,
        ge=1000,
        le=300000,
        description="Default timeout per iteration in milliseconds",
    )
    enable_error_recovery: bool = Field(
        default=True,
        description="Enable automatic error recovery mechanisms",
    )
    default_model: str = Field(
        default="claude-sonnet-4",
        description="Default LLM model for skill execution",
    )

    # Visibility defaults by role
    visibility_end_user: str = Field(
        default="SUMMARY",
        description="Default visibility level for end users",
    )
    visibility_developer: str = Field(
        default="FULL",
        description="Default visibility level for developers",
    )
    visibility_admin: str = Field(
        default="FULL",
        description="Default visibility level for administrators",
    )

    # Cost limits (optional)
    cost_limits_enabled: bool = Field(
        default=False,
        description="Enable cost tracking and limits",
    )
    max_cost_per_execution_usd: float = Field(
        default=1.0,
        ge=0.0,
        description="Maximum cost per execution in USD",
    )

    # Rate limits (optional)
    rate_limits_enabled: bool = Field(
        default=False,
        description="Enable rate limiting",
    )
    max_iterations_per_minute: int = Field(
        default=100,
        ge=1,
        description="Maximum iterations across all executions per minute",
    )

    @classmethod
    def from_yaml(cls, path: Union[str, Path]) -> "PlatformAutonomousConfig":
        """Load configuration from YAML file.

        Args:
            path: Path to YAML configuration file

        Returns:
            PlatformAutonomousConfig instance loaded from YAML

        Raises:
            FileNotFoundError: If configuration file doesn't exist
            ValueError: If YAML format is invalid
        """
        import yaml  # type: ignore[import-untyped]

        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")

        try:
            with open(config_path) as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML format in {path}: {e}") from e

        # Extract 'autonomous' section if present
        config_data = data.get("autonomous", {}) if isinstance(data, dict) else {}

        return cls(**config_data)

    @classmethod
    def from_env(cls) -> "PlatformAutonomousConfig":
        """Load configuration from environment variables.

        Environment variables follow the pattern: OMNIFORGE_<SETTING_NAME>
        For example: OMNIFORGE_MAX_ITERATIONS, OMNIFORGE_DEFAULT_MODEL

        Returns:
            PlatformAutonomousConfig instance with environment overrides
        """
        return cls(
            default_max_iterations=int(
                os.getenv(
                    "OMNIFORGE_MAX_ITERATIONS", cls.model_fields["default_max_iterations"].default
                )
            ),
            default_max_retries_per_tool=int(
                os.getenv(
                    "OMNIFORGE_MAX_RETRIES_PER_TOOL",
                    cls.model_fields["default_max_retries_per_tool"].default,
                )
            ),
            default_timeout_per_iteration_ms=int(
                os.getenv(
                    "OMNIFORGE_TIMEOUT_PER_ITERATION_MS",
                    cls.model_fields["default_timeout_per_iteration_ms"].default,
                )
            ),
            enable_error_recovery=os.getenv(
                "OMNIFORGE_ENABLE_ERROR_RECOVERY",
                str(cls.model_fields["enable_error_recovery"].default),
            ).lower()
            in ("true", "1", "yes"),
            default_model=os.getenv(
                "OMNIFORGE_DEFAULT_MODEL", cls.model_fields["default_model"].default
            ),
            visibility_end_user=os.getenv(
                "OMNIFORGE_VISIBILITY_END_USER", cls.model_fields["visibility_end_user"].default
            ),
            visibility_developer=os.getenv(
                "OMNIFORGE_VISIBILITY_DEVELOPER",
                cls.model_fields["visibility_developer"].default,
            ),
            visibility_admin=os.getenv(
                "OMNIFORGE_VISIBILITY_ADMIN", cls.model_fields["visibility_admin"].default
            ),
            cost_limits_enabled=os.getenv(
                "OMNIFORGE_COST_LIMITS_ENABLED",
                str(cls.model_fields["cost_limits_enabled"].default),
            ).lower()
            in ("true", "1", "yes"),
            max_cost_per_execution_usd=float(
                os.getenv(
                    "OMNIFORGE_MAX_COST_PER_EXECUTION_USD",
                    cls.model_fields["max_cost_per_execution_usd"].default,
                )
            ),
            rate_limits_enabled=os.getenv(
                "OMNIFORGE_RATE_LIMITS_ENABLED",
                str(cls.model_fields["rate_limits_enabled"].default),
            ).lower()
            in ("true", "1", "yes"),
            max_iterations_per_minute=int(
                os.getenv(
                    "OMNIFORGE_MAX_ITERATIONS_PER_MINUTE",
                    cls.model_fields["max_iterations_per_minute"].default,
                )
            ),
        )


def parse_duration_ms(duration: Optional[str]) -> Optional[int]:
    """Parse duration string to milliseconds.

    Supports duration strings with units:
    - 'ms' for milliseconds (e.g., '500ms')
    - 's' for seconds (e.g., '30s', '1.5s')
    - 'm' for minutes (e.g., '1m', '2.5m')

    Args:
        duration: Duration string (e.g., '30s', '1m', '500ms') or None

    Returns:
        Duration in milliseconds, or None if input is None or invalid

    Examples:
        >>> parse_duration_ms("30s")
        30000
        >>> parse_duration_ms("1m")
        60000
        >>> parse_duration_ms("500ms")
        500
        >>> parse_duration_ms("1.5s")
        1500
        >>> parse_duration_ms("invalid")
        None
    """
    if not duration:
        return None

    # Match pattern: number (int or float) + unit (ms, s, m)
    match = re.match(r"^(\d+(?:\.\d+)?)\s*(ms|s|m)$", duration.lower().strip())
    if not match:
        return None

    value = float(match.group(1))
    unit = match.group(2)

    if unit == "ms":
        return int(value)
    elif unit == "s":
        return int(value * 1000)
    elif unit == "m":
        return int(value * 60 * 1000)

    return None


def is_valid_duration(duration: str) -> bool:
    """Check if duration string is valid.

    Args:
        duration: Duration string to validate

    Returns:
        True if duration is valid, False otherwise

    Examples:
        >>> is_valid_duration("30s")
        True
        >>> is_valid_duration("invalid")
        False
    """
    return parse_duration_ms(duration) is not None


def validate_skill_config(
    skill_metadata: "BaseModel",
    platform_config: PlatformAutonomousConfig,
) -> list[str]:
    """Validate skill configuration against platform limits.

    Checks skill metadata for configuration issues and returns a list of
    validation warnings/errors.

    Args:
        skill_metadata: Skill metadata with autonomous configuration
        platform_config: Platform configuration with limits

    Returns:
        List of validation warning/error messages (empty if valid)

    Examples:
        >>> from omniforge.skills.models import SkillMetadata
        >>> metadata = SkillMetadata(name="test", description="test", max_iterations=200)
        >>> platform = PlatformAutonomousConfig()
        >>> warnings = validate_skill_config(metadata, platform)
        >>> any("exceeds maximum" in w for w in warnings)
        True
    """
    warnings: list[str] = []

    # Check if skill has metadata attributes
    if not hasattr(skill_metadata, "max_iterations"):
        return warnings

    # Check max_iterations bounds
    if skill_metadata.max_iterations is not None:
        if skill_metadata.max_iterations > 100:
            warnings.append(
                f"max_iterations ({skill_metadata.max_iterations}) exceeds maximum (100)"
            )
        if skill_metadata.max_iterations < 1:
            warnings.append(f"max_iterations ({skill_metadata.max_iterations}) must be at least 1")

    # Check max_retries_per_tool bounds
    if (
        hasattr(skill_metadata, "max_retries_per_tool")
        and skill_metadata.max_retries_per_tool is not None
    ):
        if skill_metadata.max_retries_per_tool > 10:
            warnings.append(
                f"max_retries_per_tool ({skill_metadata.max_retries_per_tool}) exceeds maximum (10)"
            )
        if skill_metadata.max_retries_per_tool < 0:
            warnings.append(
                f"max_retries_per_tool ({skill_metadata.max_retries_per_tool}) must be at least 0"
            )

    # Check timeout format
    if hasattr(skill_metadata, "timeout_per_iteration") and skill_metadata.timeout_per_iteration:
        if not is_valid_duration(skill_metadata.timeout_per_iteration):
            warnings.append(
                f"Invalid timeout format: {skill_metadata.timeout_per_iteration}. "
                f"Use format like '30s', '1m', '500ms'"
            )

    return warnings


def merge_configs(
    platform: PlatformAutonomousConfig,
    skill_metadata: "BaseModel",
) -> AutonomousConfig:
    """Merge platform defaults with skill-specific overrides.

    Creates an AutonomousConfig by taking platform defaults and applying
    any skill-level overrides from metadata.

    Args:
        platform: Platform configuration with defaults
        skill_metadata: Skill metadata with potential overrides

    Returns:
        AutonomousConfig with merged settings

    Examples:
        >>> from omniforge.skills.models import SkillMetadata
        >>> platform = PlatformAutonomousConfig(default_max_iterations=15)
        >>> metadata = SkillMetadata(name="test", description="test", max_iterations=20)
        >>> config = merge_configs(platform, metadata)
        >>> config.max_iterations
        20
    """
    # Start with platform defaults
    max_iterations = platform.default_max_iterations
    max_retries_per_tool = platform.default_max_retries_per_tool
    timeout_per_iteration_ms = platform.default_timeout_per_iteration_ms
    model = platform.default_model

    # Apply skill overrides if present
    if hasattr(skill_metadata, "max_iterations") and skill_metadata.max_iterations is not None:
        max_iterations = skill_metadata.max_iterations

    if (
        hasattr(skill_metadata, "max_retries_per_tool")
        and skill_metadata.max_retries_per_tool is not None
    ):
        max_retries_per_tool = skill_metadata.max_retries_per_tool

    if hasattr(skill_metadata, "timeout_per_iteration") and skill_metadata.timeout_per_iteration:
        parsed_timeout = parse_duration_ms(skill_metadata.timeout_per_iteration)
        if parsed_timeout is not None:
            timeout_per_iteration_ms = parsed_timeout

    if hasattr(skill_metadata, "model") and skill_metadata.model:
        model = skill_metadata.model

    # Get early_termination from skill or use default
    early_termination = True
    if (
        hasattr(skill_metadata, "early_termination")
        and skill_metadata.early_termination is not None
    ):
        early_termination = skill_metadata.early_termination

    return AutonomousConfig(
        max_iterations=max_iterations,
        max_retries_per_tool=max_retries_per_tool,
        timeout_per_iteration_ms=timeout_per_iteration_ms,
        model=model,
        early_termination=early_termination,
        enable_error_recovery=platform.enable_error_recovery,
    )
