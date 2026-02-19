# TASK-105: Agent Execution Service (Single-Skill)

**Phase**: 1 (MVP)
**Estimated Effort**: 12 hours
**Dependencies**: TASK-101, TASK-102
**Priority**: P0

## Objective

Implement the agent execution service that runs single-skill agents using the existing SkillTool infrastructure. This establishes the execution pattern that will be extended for multi-skill orchestration in Phase 2.

## Requirements

- Create `OrchestrationEngine` class that uses existing `SkillLoader` and `SkillTool`
- Implement `execute_single_skill()` method for MVP single-skill agents
- Create `ExecutionEvent` model for execution status streaming
- Implement `AgentTestRunner` with `dry_run()` for pre-activation testing
- Create storage config for tenant-based skill resolution
- Log execution results to `agent_executions` table
- Support execution timeout with graceful termination

## Implementation Notes

- Reference technical plan Section 5.2.1 for OrchestrationEngine specification
- Use existing `SkillTool.execute()` from `src/omniforge/skills/tool.py`
- Use existing `SkillLoader` from `src/omniforge/skills/loader.py`
- Storage layer priority: agent skills -> tenant skills -> public skills -> global
- Emit execution events: skill_started, skill_completed, skill_failed
- 85%+ test coverage for sequential execution (per review requirements)

## Acceptance Criteria

- [ ] `OrchestrationEngine` correctly initializes with SkillLoader and SkillTool
- [ ] `execute_single_skill()` runs skill via existing SkillTool.execute()
- [ ] ExecutionEvents stream correctly (started, completed, failed)
- [ ] Execution results logged to agent_executions table
- [ ] `AgentTestRunner.dry_run()` executes with mock integration responses
- [ ] Execution timeout terminates gracefully after configured limit
- [ ] Storage config resolves skills from correct tenant directory
- [ ] 85%+ test coverage for execution paths

## Files to Create/Modify

- `src/omniforge/execution/__init__.py` - Execution package init
- `src/omniforge/execution/orchestration/__init__.py` - Orchestration package init
- `src/omniforge/execution/orchestration/engine.py` - OrchestrationEngine, ExecutionEvent
- `src/omniforge/execution/orchestration/storage_config.py` - Builder storage config factory
- `src/omniforge/execution/testing.py` - AgentTestRunner class
- `src/omniforge/builder/repository.py` - Add execution log methods (extend from TASK-101)
- `tests/execution/__init__.py` - Test package
- `tests/execution/orchestration/test_engine.py` - Engine tests
- `tests/execution/test_testing.py` - TestRunner tests
