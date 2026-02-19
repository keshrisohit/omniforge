# TASK-301: Parallel Skill Orchestration

**Phase**: 3A (Advanced Orchestration)
**Estimated Effort**: 16 hours
**Dependencies**: TASK-201 (Sequential Orchestration)
**Priority**: P1

## Objective

Add parallel skill execution for independent skills that don't have data dependencies. This improves execution time when multiple data sources need to be queried simultaneously.

## Requirements

- Extend OrchestrationEngine with `execute_parallel()` method
- Create `OrchestrationMode` enum: SEQUENTIAL, PARALLEL
- Implement parallel skill grouping based on order field (same order = parallel)
- Use asyncio.gather() for concurrent execution
- Handle partial failures in parallel execution
- Combine results from parallel skills into unified output

## Implementation Notes

- Reference product spec "Parallel Orchestration" example
- Skills with same `order` value execute in parallel
- Example: order=1 skills run parallel, then order=2 skills run parallel
- Parallel execution requires no data dependencies between skills
- AgentGenerator should detect parallelizable skill compositions

## Acceptance Criteria

- [ ] Skills with same order value execute concurrently via asyncio.gather()
- [ ] Parallel execution is faster than sequential for independent skills
- [ ] Partial failure handling: capture all results, report failures
- [ ] Results from parallel skills merged correctly
- [ ] OrchestrationMode configurable per agent
- [ ] Execution events include parallel group information
- [ ] Performance test shows parallel speedup
- [ ] 85%+ test coverage for parallel execution paths

## Files to Create/Modify

- `src/omniforge/execution/orchestration/engine.py` - Add execute_parallel()
- `src/omniforge/execution/orchestration/models.py` - OrchestrationMode enum
- `src/omniforge/execution/orchestration/grouping.py` - Parallel group detection
- `src/omniforge/builder/models/agent_config.py` - Add orchestration_mode
- `tests/execution/orchestration/test_parallel.py` - Parallel execution tests
- `tests/performance/test_parallel_speedup.py` - Performance comparison tests
