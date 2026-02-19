# TASK-303: Advanced Error Recovery Strategies

**Phase**: 3A (Advanced Orchestration)
**Estimated Effort**: 10 hours
**Dependencies**: TASK-301 (Parallel Orchestration)
**Priority**: P1

## Objective

Implement advanced error recovery including circuit breakers, fallback skills, and execution checkpoints for resumable workflows.

## Requirements

- Implement circuit breaker for integration failures
- Create fallback skill mechanism (alternative skill on failure)
- Add execution checkpoints for long workflows
- Implement workflow resume from last successful checkpoint
- Create notification system for persistent failures
- Add manual intervention queue for stuck executions

## Implementation Notes

- Circuit breaker: 5 failures in 1 minute opens circuit for 5 minutes
- Fallback: SkillReference.fallback_skill specifies alternative
- Checkpoint: persist execution state after each skill completion
- Resume: load checkpoint and continue from last successful skill
- Notification: webhook or email for failures requiring attention

## Acceptance Criteria

- [ ] Circuit breaker opens after configurable failure threshold
- [ ] Open circuit skips execution and returns cached/fallback result
- [ ] Fallback skill executes when primary skill fails
- [ ] Execution state persisted after each skill for checkpointing
- [ ] Resume execution continues from last checkpoint
- [ ] Notification sent for executions requiring manual intervention
- [ ] Admin API to view and manage stuck executions
- [ ] 80%+ test coverage for recovery paths

## Files to Create/Modify

- `src/omniforge/execution/resilience/__init__.py` - Resilience package
- `src/omniforge/execution/resilience/circuit_breaker.py` - Circuit breaker
- `src/omniforge/execution/resilience/fallback.py` - Fallback handling
- `src/omniforge/execution/checkpointing.py` - Checkpoint persistence
- `src/omniforge/execution/orchestration/engine.py` - Integrate resilience
- `src/omniforge/builder/models/agent_config.py` - Add fallback_skill
- `tests/execution/resilience/test_circuit_breaker.py` - Circuit breaker tests
- `tests/execution/test_checkpointing.py` - Checkpoint/resume tests
