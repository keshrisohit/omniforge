# TASK-502: Implement Cost Tracker for Budget Enforcement

## Description

Create the cost tracking system that records costs from tool executions and enforces per-task budgets. This enables billing, usage analytics, and cost control.

## Requirements

- Create `CostRecord` model:
  - tenant_id, task_id, chain_id, step_id
  - tool_name, cost_usd, tokens, model
  - created_at timestamp
- Create `TaskBudget` model:
  - max_cost_usd: Optional[float]
  - max_tokens: Optional[int]
  - max_llm_calls: Optional[int]
- Create `CostTracker` class:
  - Constructor accepting optional CostRepository
  - In-memory tracking dictionaries for active tasks
  - `record_cost()` async method:
    - Update in-memory tracking
    - Persist to repository if available
  - `get_task_cost(task_id)` method
  - `get_task_tokens(task_id)` method
  - `check_budget(task_id, budget, additional_cost, additional_tokens)` method
  - `get_remaining_budget(task_id, budget)` method
- CostRepository protocol for persistence (optional)

## Acceptance Criteria

- [ ] Costs recorded per task
- [ ] In-memory tracking works without repository
- [ ] Budget checks return True/False correctly
- [ ] Remaining budget calculated accurately
- [ ] LLM call counting works
- [ ] Repository persistence works when configured
- [ ] Unit tests cover tracking and budget checks

## Dependencies

- None (foundational for enterprise)

## Files to Create/Modify

- `src/omniforge/enterprise/cost_tracker.py` (new)
- `tests/enterprise/test_cost_tracker.py` (new)

## Estimated Complexity

Medium (4-5 hours)

## Key Considerations

- Task cleanup when tasks complete (memory management)
- Consider thread safety for concurrent access
- Repository is optional for SDK standalone mode
