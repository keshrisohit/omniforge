# TASK-101: Implement ReasoningChain and ReasoningStep Data Models

## Description

Create the core data structures for chain of thought reasoning. This includes the ReasoningChain and ReasoningStep Pydantic models that form the foundation of the CoT system. All subsequent tasks depend on these models.

## Requirements

- Create enums: `StepType`, `ToolType`, `ChainStatus`, `VisibilityLevel`
- Create models: `ThinkingInfo`, `ToolCallInfo`, `ToolResultInfo`, `SynthesisInfo`
- Create `VisibilityConfig` model for step visibility control
- Create `ChainMetrics` model for aggregated statistics
- Create `ReasoningStep` model with:
  - UUID id, step_number, type, timestamp
  - Optional type-specific info (thinking, tool_call, tool_result, synthesis)
  - Visibility configuration
  - Parent step ID for nested operations
- Create `ReasoningChain` model with:
  - task_id, agent_id, status, started_at, completed_at
  - List of steps with proper ordering
  - Metrics (auto-updated)
  - Child chain IDs for sub-agent delegation
  - tenant_id for multi-tenancy
- Implement `add_step()` method that auto-numbers steps and updates metrics
- Implement `get_step_by_correlation_id()` for linking tool calls to results

## Acceptance Criteria

- [ ] All enums defined with correct values
- [ ] All Pydantic models pass validation
- [ ] add_step() correctly numbers steps sequentially
- [ ] Metrics auto-update when steps are added (total_steps, llm_calls, tool_calls, tokens, cost)
- [ ] Type hints pass mypy strict mode
- [ ] Unit tests cover all model functionality with 80%+ coverage

## Dependencies

- None (foundational task)

## Files to Create/Modify

- `src/omniforge/agents/cot/__init__.py` (new)
- `src/omniforge/agents/cot/chain.py` (new)
- `tests/agents/cot/__init__.py` (new)
- `tests/agents/cot/test_chain.py` (new)

## Estimated Complexity

Medium (4-6 hours)

## Key Considerations

- Use Pydantic v2 features for performance
- Ensure all fields have appropriate defaults
- Consider JSON serialization for storage compatibility
