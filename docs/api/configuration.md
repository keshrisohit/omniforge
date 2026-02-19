# Configuration API Reference

This document provides comprehensive reference for configuration classes and utilities in the OmniForge autonomous skill execution system.

## Table of Contents

1. [Overview](#overview)
2. [Configuration Classes](#configuration-classes)
3. [Platform Configuration](#platform-configuration)
4. [Utility Functions](#utility-functions)
5. [Configuration Examples](#configuration-examples)

---

## Overview

The configuration system provides flexible, multi-level configuration for autonomous skill execution:

- **Platform-level defaults** - Global configuration via PlatformAutonomousConfig
- **Skill-level overrides** - Per-skill configuration in skill metadata
- **Runtime overrides** - Per-execution configuration via AutonomousConfig
- **Environment variables** - System-wide configuration via env vars

### Configuration Priority

When executing a skill, configuration is resolved in this order (highest to lowest priority):

1. **Runtime config** - Passed to AutonomousSkillExecutor constructor
2. **Skill metadata** - Defined in skill's SKILL.md frontmatter
3. **Platform defaults** - From PlatformAutonomousConfig (YAML or env)
4. **Built-in defaults** - Hardcoded fallback values

---

## Configuration Classes

### AutonomousConfig

Configuration parameters for autonomous skill execution.

```python
from pydantic import BaseModel, Field

class AutonomousConfig(BaseModel):
    """Configuration for autonomous skill execution.

    This model defines the constraints and parameters for autonomous execution
    of skills using the ReAct pattern.
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
```

**Field Descriptions:**

- `max_iterations` (int): Maximum number of ReAct loop iterations before termination
  - Range: 1-100
  - Default: 15
  - Use higher values for complex, multi-step tasks

- `max_retries_per_tool` (int): Maximum retry attempts per tool/approach before switching
  - Range: 1-10
  - Default: 3
  - Prevents infinite retry loops on failed approaches

- `timeout_per_iteration_ms` (int): Timeout for each iteration in milliseconds
  - Range: 1000-300000 (1s - 5min)
  - Default: 30000 (30s)
  - Prevents hanging on slow LLM calls

- `early_termination` (bool): Allow termination when goal is reached before max_iterations
  - Default: True
  - Set to False to force using all iterations (for testing)

- `model` (Optional[str]): LLM model to use for this execution
  - Default: None (uses skill or platform default)
  - Supported values: "claude-haiku-4", "claude-sonnet-4", "claude-opus-4"
  - Can also use short names: "haiku", "sonnet", "opus"

- `temperature` (float): LLM temperature for response generation
  - Range: 0.0-2.0
  - Default: 0.0 (deterministic)
  - Higher values increase randomness/creativity

- `enable_error_recovery` (bool): Enable automatic error recovery and retry logic
  - Default: True
  - Set to False to fail fast on errors (for debugging)

**Example:**

```python
from omniforge.skills.config import AutonomousConfig

# Default configuration
config_default = AutonomousConfig()

# Custom configuration for long-running task
config_long = AutonomousConfig(
    max_iterations=30,
    timeout_per_iteration_ms=120000,  # 2 minutes
    model="claude-opus-4",
)

# Configuration for quick, deterministic task
config_quick = AutonomousConfig(
    max_iterations=5,
    max_retries_per_tool=1,
    temperature=0.0,
    early_termination=True,
)

# Configuration for creative task
config_creative = AutonomousConfig(
    max_iterations=20,
    temperature=0.7,
    model="claude-sonnet-4",
)
```

---

### ExecutionContext

Context for tracking sub-agent execution depth and preventing infinite recursion.

```python
from pydantic import BaseModel, Field

class ExecutionContext(BaseModel):
    """Context for tracking sub-agent execution depth and hierarchy."""

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
```

**Methods:**

```python
def create_child_context(
    self,
    task_id: str,
    skill_name: Optional[str] = None
) -> ExecutionContext:
    """Create child context for sub-agent execution.

    Args:
        task_id: Task ID of the child execution
        skill_name: Optional skill name to add to the chain

    Returns:
        New ExecutionContext with incremented depth

    Raises:
        ValueError: If maximum depth would be exceeded
    """

def can_spawn_sub_agent(self) -> bool:
    """Check if another sub-agent level is allowed.

    Returns:
        True if current depth is below max_depth, False otherwise
    """

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
```

**Example:**

```python
from omniforge.skills.config import ExecutionContext

# Create root context
root_ctx = ExecutionContext(max_depth=2)
print(f"Root depth: {root_ctx.depth}")  # 0

# Create child context for sub-agent
child_ctx = root_ctx.create_child_context(
    task_id="child-task-1",
    skill_name="data-validator",
)
print(f"Child depth: {child_ctx.depth}")  # 1
print(f"Skill chain: {child_ctx.skill_chain}")  # ["data-validator"]

# Check if can spawn another level
if child_ctx.can_spawn_sub_agent():
    grandchild_ctx = child_ctx.create_child_context(
        task_id="grandchild-task-1",
        skill_name="file-reader",
    )
    print(f"Grandchild depth: {grandchild_ctx.depth}")  # 2

# Calculate iteration budget
root_budget = 15
child_budget = child_ctx.get_iteration_budget_for_child(root_budget)
print(f"Child budget: {child_budget}")  # 7 (50% of 15, min 3)

# Attempting to exceed max_depth raises error
try:
    grandchild_ctx.create_child_context("too-deep", "another-skill")
except ValueError as e:
    print(f"Error: {e}")  # Maximum sub-agent depth exceeded
```

---

### ExecutionState

Runtime state tracking across ReAct loop iterations.

```python
from pydantic import BaseModel, Field
from datetime import datetime

class ExecutionState(BaseModel):
    """Runtime state tracking for autonomous skill execution."""

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
```

**Example:**

```python
from omniforge.skills.config import ExecutionState
from datetime import datetime

# Initialize execution state
state = ExecutionState()

# Track iteration progress
state.iteration = 1

# Record tool observations
state.observations.append({
    "tool": "read",
    "result": "File contents...",
    "success": True,
})

# Track failed approaches to avoid retrying
approach_key = "parse_csv:encoding_error"
state.failed_approaches[approach_key] = state.failed_approaches.get(approach_key, 0) + 1

# Record partial results
state.partial_results.append("Loaded data from file")

# Track errors
state.error_count += 1

# Calculate execution duration
duration = (datetime.utcnow() - state.start_time).total_seconds()
print(f"Execution running for {duration:.2f}s")
```

---

### ExecutionResult

Final result wrapper with metrics and outcome.

```python
from pydantic import BaseModel, Field

class ExecutionResult(BaseModel):
    """Final result wrapper for autonomous skill execution."""

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
```

**Example:**

```python
from omniforge.skills.config import ExecutionResult, ExecutionMetrics

# Example successful result
result_success = ExecutionResult(
    success=True,
    result="Data processed successfully. Generated summary report.",
    iterations_used=8,
    chain_id="chain-123",
    metrics=ExecutionMetrics(
        duration_seconds=45.2,
        total_tokens=3500,
        total_cost=0.015,
        tool_calls_successful=12,
        tool_calls_failed=0,
    ),
)

# Example failed result with partial results
result_partial = ExecutionResult(
    success=False,
    result="",
    iterations_used=15,
    chain_id="chain-456",
    metrics=ExecutionMetrics(
        duration_seconds=120.5,
        total_tokens=8000,
        total_cost=0.035,
        tool_calls_successful=8,
        tool_calls_failed=4,
        error_recoveries=3,
    ),
    partial_results=[
        "Loaded data from file",
        "Validated 80% of records",
        "Generated partial summary",
    ],
    error="Maximum iterations reached without completing all objectives",
)
```

---

### ExecutionMetrics

Detailed metrics for cost tracking and performance analysis.

```python
from pydantic import BaseModel, Field

class ExecutionMetrics(BaseModel):
    """Detailed metrics for autonomous skill execution."""

    total_tokens: int = Field(default=0, ge=0)
    prompt_tokens: int = Field(default=0, ge=0)
    completion_tokens: int = Field(default=0, ge=0)
    total_cost: float = Field(default=0.0, ge=0.0)
    duration_seconds: float = Field(default=0.0, ge=0.0)
    tool_calls_successful: int = Field(default=0, ge=0)
    tool_calls_failed: int = Field(default=0, ge=0)
    error_recoveries: int = Field(default=0, ge=0)
    model_used: Optional[str] = Field(default=None)
    estimated_cost_per_call: float = Field(default=0.0, ge=0.0)
```

**Cost Estimates:**

Model costs (per 1M tokens, approximate):

```python
MODEL_COSTS = {
    "claude-haiku-4": {"input": 0.25, "output": 1.25},
    "claude-sonnet-4": {"input": 3.0, "output": 15.0},
    "claude-opus-4": {"input": 15.0, "output": 75.0},
}
```

**Example:**

```python
from omniforge.skills.config import ExecutionMetrics

metrics = ExecutionMetrics(
    total_tokens=5000,
    prompt_tokens=3000,
    completion_tokens=2000,
    duration_seconds=30.5,
    tool_calls_successful=10,
    tool_calls_failed=2,
    error_recoveries=1,
    model_used="claude-sonnet-4",
)

# Calculate cost (approximate)
input_cost = (metrics.prompt_tokens / 1_000_000) * 3.0
output_cost = (metrics.completion_tokens / 1_000_000) * 15.0
metrics.total_cost = input_cost + output_cost

print(f"Total cost: ${metrics.total_cost:.4f}")
print(f"Avg tokens per second: {metrics.total_tokens / metrics.duration_seconds:.1f}")
```

---

## Platform Configuration

### PlatformAutonomousConfig

Platform-wide configuration with defaults and limits.

```python
from pydantic import BaseModel, Field

class PlatformAutonomousConfig(BaseModel):
    """Platform-level autonomous execution configuration."""

    # Execution defaults
    default_max_iterations: int = Field(default=15, ge=1, le=100)
    default_max_retries_per_tool: int = Field(default=3, ge=1, le=10)
    default_timeout_per_iteration_ms: int = Field(default=30000, ge=1000, le=300000)
    enable_error_recovery: bool = Field(default=True)
    default_model: str = Field(default="claude-sonnet-4")

    # Visibility defaults by role
    visibility_end_user: str = Field(default="SUMMARY")
    visibility_developer: str = Field(default="FULL")
    visibility_admin: str = Field(default="FULL")

    # Cost limits (optional)
    cost_limits_enabled: bool = Field(default=False)
    max_cost_per_execution_usd: float = Field(default=1.0, ge=0.0)

    # Rate limits (optional)
    rate_limits_enabled: bool = Field(default=False)
    max_iterations_per_minute: int = Field(default=100, ge=1)
```

**Loading from YAML:**

```python
@classmethod
def from_yaml(cls, path: Union[str, Path]) -> "PlatformAutonomousConfig":
    """Load configuration from YAML file."""
```

**Loading from Environment:**

```python
@classmethod
def from_env(cls) -> "PlatformAutonomousConfig":
    """Load configuration from environment variables."""
```

**Example YAML Configuration:**

```yaml
# config/autonomous.yaml
autonomous:
  # Execution defaults
  default_max_iterations: 20
  default_max_retries_per_tool: 3
  default_timeout_per_iteration_ms: 60000
  enable_error_recovery: true
  default_model: "claude-sonnet-4"

  # Visibility
  visibility_end_user: "SUMMARY"
  visibility_developer: "FULL"
  visibility_admin: "FULL"

  # Cost limits
  cost_limits_enabled: true
  max_cost_per_execution_usd: 0.50

  # Rate limits
  rate_limits_enabled: true
  max_iterations_per_minute: 200
```

**Example Environment Variables:**

```bash
# .env
OMNIFORGE_MAX_ITERATIONS=20
OMNIFORGE_MAX_RETRIES_PER_TOOL=3
OMNIFORGE_TIMEOUT_PER_ITERATION_MS=60000
OMNIFORGE_ENABLE_ERROR_RECOVERY=true
OMNIFORGE_DEFAULT_MODEL=claude-sonnet-4
OMNIFORGE_VISIBILITY_END_USER=SUMMARY
OMNIFORGE_COST_LIMITS_ENABLED=true
OMNIFORGE_MAX_COST_PER_EXECUTION_USD=0.50
```

**Usage:**

```python
from omniforge.skills.config import PlatformAutonomousConfig

# Load from YAML
platform_config = PlatformAutonomousConfig.from_yaml("config/autonomous.yaml")

# Load from environment
platform_config = PlatformAutonomousConfig.from_env()

# Use defaults
platform_config = PlatformAutonomousConfig()
```

---

## Utility Functions

### parse_duration_ms()

Parse duration string to milliseconds.

```python
def parse_duration_ms(duration: Optional[str]) -> Optional[int]:
    """Parse duration string to milliseconds.

    Supports duration strings with units:
    - 'ms' for milliseconds (e.g., '500ms')
    - 's' for seconds (e.g., '30s', '1.5s')
    - 'm' for minutes (e.g., '1m', '2.5m')

    Args:
        duration: Duration string or None

    Returns:
        Duration in milliseconds, or None if invalid

    Examples:
        >>> parse_duration_ms("30s")
        30000
        >>> parse_duration_ms("1m")
        60000
        >>> parse_duration_ms("500ms")
        500
        >>> parse_duration_ms("1.5s")
        1500
    """
```

**Example:**

```python
from omniforge.skills.config import parse_duration_ms

# Parse various duration formats
timeout_30s = parse_duration_ms("30s")      # 30000
timeout_1m = parse_duration_ms("1m")        # 60000
timeout_500ms = parse_duration_ms("500ms")  # 500
timeout_1_5s = parse_duration_ms("1.5s")    # 1500

# Use in config
config = AutonomousConfig(
    timeout_per_iteration_ms=parse_duration_ms("45s"),
)
```

### validate_skill_config()

Validate skill configuration against platform limits.

```python
def validate_skill_config(
    skill_metadata: BaseModel,
    platform_config: PlatformAutonomousConfig,
) -> list[str]:
    """Validate skill configuration against platform limits.

    Args:
        skill_metadata: Skill metadata with autonomous configuration
        platform_config: Platform configuration with limits

    Returns:
        List of validation warning/error messages (empty if valid)
    """
```

**Example:**

```python
from omniforge.skills.config import validate_skill_config, PlatformAutonomousConfig
from omniforge.skills.models import SkillMetadata

# Skill with invalid config
skill_meta = SkillMetadata(
    name="test-skill",
    description="Test",
    max_iterations=200,  # Exceeds maximum (100)
    timeout_per_iteration="invalid",  # Invalid format
)

platform = PlatformAutonomousConfig()

# Validate
warnings = validate_skill_config(skill_meta, platform)

for warning in warnings:
    print(f"Warning: {warning}")
# Output:
# Warning: max_iterations (200) exceeds maximum (100)
# Warning: Invalid timeout format: invalid. Use format like '30s', '1m', '500ms'
```

### merge_configs()

Merge platform defaults with skill-specific overrides.

```python
def merge_configs(
    platform: PlatformAutonomousConfig,
    skill_metadata: BaseModel,
) -> AutonomousConfig:
    """Merge platform defaults with skill-specific overrides.

    Creates an AutonomousConfig by taking platform defaults and applying
    any skill-level overrides from metadata.

    Args:
        platform: Platform configuration with defaults
        skill_metadata: Skill metadata with potential overrides

    Returns:
        AutonomousConfig with merged settings
    """
```

**Example:**

```python
from omniforge.skills.config import merge_configs, PlatformAutonomousConfig
from omniforge.skills.models import SkillMetadata

# Platform defaults
platform = PlatformAutonomousConfig(
    default_max_iterations=15,
    default_max_retries_per_tool=3,
    default_model="claude-sonnet-4",
)

# Skill with overrides
skill_meta = SkillMetadata(
    name="data-processor",
    description="Process data",
    max_iterations=20,  # Override
    model="claude-opus-4",  # Override
    # max_retries_per_tool not set - will use platform default
)

# Merge configurations
config = merge_configs(platform, skill_meta)

print(f"max_iterations: {config.max_iterations}")  # 20 (skill override)
print(f"max_retries_per_tool: {config.max_retries_per_tool}")  # 3 (platform default)
print(f"model: {config.model}")  # claude-opus-4 (skill override)
```

---

## Configuration Examples

### Example 1: Development Environment

Configuration for local development with verbose logging:

```yaml
# config/dev.yaml
autonomous:
  default_max_iterations: 10
  default_max_retries_per_tool: 2
  default_timeout_per_iteration_ms: 30000
  enable_error_recovery: true
  default_model: "claude-haiku-4"  # Faster, cheaper
  visibility_developer: "FULL"
  cost_limits_enabled: false
  rate_limits_enabled: false
```

### Example 2: Production Environment

Configuration for production with limits and monitoring:

```yaml
# config/prod.yaml
autonomous:
  default_max_iterations: 15
  default_max_retries_per_tool: 3
  default_timeout_per_iteration_ms: 60000
  enable_error_recovery: true
  default_model: "claude-sonnet-4"
  visibility_end_user: "SUMMARY"
  visibility_developer: "FULL"
  cost_limits_enabled: true
  max_cost_per_execution_usd: 1.00
  rate_limits_enabled: true
  max_iterations_per_minute: 500
```

### Example 3: High-Performance Environment

Configuration for resource-intensive tasks:

```yaml
# config/high-perf.yaml
autonomous:
  default_max_iterations: 30
  default_max_retries_per_tool: 5
  default_timeout_per_iteration_ms: 120000  # 2 minutes
  enable_error_recovery: true
  default_model: "claude-opus-4"  # Most capable
  visibility_developer: "FULL"
  cost_limits_enabled: true
  max_cost_per_execution_usd: 5.00  # Higher limit
  rate_limits_enabled: true
  max_iterations_per_minute: 200
```

### Example 4: Runtime Override

Override configuration at runtime for specific tasks:

```python
from omniforge.skills.config import AutonomousConfig, PlatformAutonomousConfig
from omniforge.skills.orchestrator import SkillOrchestrator

# Load platform defaults
platform = PlatformAutonomousConfig.from_yaml("config/prod.yaml")

# Create orchestrator with platform defaults
orchestrator = SkillOrchestrator(
    skill_loader=loader,
    tool_registry=registry,
    tool_executor=executor,
    default_config=AutonomousConfig(
        max_iterations=platform.default_max_iterations,
        max_retries_per_tool=platform.default_max_retries_per_tool,
    ),
)

# Override for specific execution
custom_config = AutonomousConfig(
    max_iterations=50,  # Much higher for complex task
    timeout_per_iteration_ms=180000,  # 3 minutes
    model="claude-opus-4",
)

# Use custom config for specific skill
executor = AutonomousSkillExecutor(
    skill=skill,
    tool_registry=registry,
    tool_executor=tool_executor,
    config=custom_config,
)
```

---

## See Also

- [Skills API Reference](./skills.md) - Main API documentation
- [Migration Guide](../migration/autonomous-execution.md) - Migrating configurations
- [Skill Development Guide](../../examples/README.md) - Creating skills with custom configs

---

**Last Updated:** 2026-01-30
