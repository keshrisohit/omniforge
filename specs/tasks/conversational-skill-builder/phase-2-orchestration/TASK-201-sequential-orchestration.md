# TASK-201: Sequential Orchestration Engine

**Phase**: 2 (Multi-Skill)
**Estimated Effort**: 14 hours
**Dependencies**: TASK-105 (Phase 1 Execution Service)
**Priority**: P0

## Objective

Extend the OrchestrationEngine to support sequential multi-skill execution where output from one skill flows as input to the next. This covers 80% of user automation needs.

## Requirements

- Extend `OrchestrationEngine.execute_agent()` to handle multiple skills
- Implement output-to-input data flow between sequential skills
- Create `SkillExecutionResult` model with structured output data
- Add skill-level error handling with configurable strategies (stop, skip, retry)
- Support skill execution order via `SkillReference.order` field
- Emit granular execution events for each skill transition
- Track per-skill execution time and success/failure status

## Implementation Notes

- Reference technical plan Section 8.1 for sequential orchestration spec
- Skills execute in `order` ascending (1, 2, 3...)
- Each skill receives: merged(previous_output, skill_config)
- Stop execution on failure by default (MVP), add skip/retry in this task
- Per review: implement `ErrorStrategy` enum (STOP_ON_ERROR, SKIP_ON_ERROR, RETRY_ON_ERROR)

## Acceptance Criteria

- [ ] Multi-skill agent executes skills in correct order
- [ ] Skill 2 receives output from Skill 1 as input
- [ ] Execution stops on first failure with STOP_ON_ERROR strategy
- [ ] Execution continues past failure with SKIP_ON_ERROR strategy
- [ ] RETRY_ON_ERROR retries failed skill up to max_retries times
- [ ] ExecutionEvents include skill transition details
- [ ] Execution log captures per-skill results
- [ ] 85%+ test coverage for orchestration paths

## Files to Create/Modify

- `src/omniforge/execution/orchestration/engine.py` - Extend execute_agent() for multi-skill
- `src/omniforge/execution/orchestration/strategies.py` - ErrorStrategy enum and handlers
- `src/omniforge/execution/orchestration/models.py` - SkillExecutionResult model
- `src/omniforge/builder/models/agent_config.py` - Add error_strategy to SkillReference
- `tests/execution/orchestration/test_sequential.py` - Multi-skill execution tests
- `tests/execution/orchestration/test_error_strategies.py` - Error handling tests
