# TASK-001: Implement AutonomousConfig and ExecutionState models

**Priority:** P0 (Must Have)
**Estimated Effort:** Small (<1 day)
**Dependencies:** None

---

## Description

Create the foundational data models for autonomous skill execution: `AutonomousConfig` for execution configuration and `ExecutionState` for tracking runtime state across iterations. Also create `ExecutionResult` and `ExecutionMetrics` models.

These models will be used by the `AutonomousSkillExecutor` and other components throughout the autonomous execution system.

## Files to Create

- `src/omniforge/skills/config.py` - Configuration and state models

## Implementation Requirements

### AutonomousConfig
- `max_iterations: int = 15` - Maximum ReAct loop iterations
- `max_retries_per_tool: int = 3` - Max retries per tool/approach
- `timeout_per_iteration_ms: int = 30000` - Timeout per iteration
- `early_termination: bool = True` - Allow early termination
- `model: Optional[str] = None` - LLM model override
- `temperature: float = 0.0` - LLM temperature
- `enable_error_recovery: bool = True` - Enable automatic recovery

### ExecutionState
- `iteration: int = 0` - Current iteration number
- `observations: list[dict]` - Tool call observations
- `failed_approaches: dict[str, int]` - Failed approach tracking with retry counts
- `loaded_files: set[str]` - Supporting files loaded on-demand
- `partial_results: list[str]` - Accumulated partial results
- `error_count: int = 0` - Errors encountered
- `start_time: datetime` - Execution start timestamp

### ExecutionResult
- `success: bool` - Execution completed successfully
- `result: str` - Final result text
- `iterations_used: int` - Iterations executed
- `chain_id: str` - Reasoning chain ID for debugging
- `metrics: dict` - Execution metrics
- `partial_results: list[str]` - Partial results if incomplete
- `error: Optional[str]` - Error message if failed

### ExecutionMetrics
- Token usage, cost, duration tracking
- Tool call success/failure counts
- Error recovery count

## Acceptance Criteria

- [ ] All models created with proper type hints
- [ ] Models use dataclass decorator
- [ ] Default values match specification
- [ ] Field validation where appropriate (e.g., max_iterations >= 1, <= 100)
- [ ] Models are importable from `omniforge.skills.config`
- [ ] Unit tests achieve 95% coverage
- [ ] All type hints pass mypy validation

## Testing

```python
def test_autonomous_config_defaults():
    config = AutonomousConfig()
    assert config.max_iterations == 15
    assert config.max_retries_per_tool == 3
    assert config.enable_error_recovery == True

def test_execution_state_initialization():
    state = ExecutionState()
    assert state.iteration == 0
    assert state.observations == []
    assert state.error_count == 0

def test_execution_result_success():
    result = ExecutionResult(success=True, result="Done", iterations_used=3, ...)
    assert result.success == True
```

## Technical Notes

- Use `dataclasses` module for clean model definitions
- Use `field(default_factory=...)` for mutable defaults
- Consider using Pydantic if validation becomes complex
- Follow existing OmniForge coding patterns
