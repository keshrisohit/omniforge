# TASK-202: APScheduler Integration for Scheduled Execution

**Phase**: 2 (Multi-Skill)
**Estimated Effort**: 10 hours
**Dependencies**: TASK-201 (Sequential Orchestration)
**Priority**: P0

## Objective

Integrate APScheduler for scheduled agent execution. Agents with `trigger_type=scheduled` will execute automatically based on their cron expression.

## Requirements

- Create `AgentScheduler` class wrapping APScheduler AsyncIOScheduler
- Implement `add_schedule()`, `remove_schedule()`, `update_schedule()` methods
- Create `ScheduleConfig` model with agent_id, cron_expression, timezone
- Register scheduler as application lifecycle hook (start/stop with FastAPI)
- Persist schedules to database for recovery after restart
- Handle schedule conflicts and missed executions

## Implementation Notes

- Reference technical plan Section 5.2.2 for scheduler specification
- Use `CronTrigger.from_crontab()` for cron parsing
- Job IDs format: `agent_{agent_id}` for easy lookup
- Scheduler runs in-process (no external Redis/Celery for MVP)
- On startup, reload schedules from agent_configs where trigger_type=scheduled

## Acceptance Criteria

- [ ] `AgentScheduler.add_schedule()` creates APScheduler job with cron trigger
- [ ] `AgentScheduler.remove_schedule()` removes job by agent_id
- [ ] Scheduler starts with FastAPI application
- [ ] Schedules persist: restart app and jobs resume
- [ ] Execution logged with triggered_by='scheduler'
- [ ] Timezone-aware scheduling works correctly
- [ ] Missed execution detection with configurable behavior
- [ ] Unit tests verify schedule CRUD operations

## Files to Create/Modify

- `src/omniforge/execution/scheduler.py` - AgentScheduler, ScheduleConfig
- `src/omniforge/execution/lifecycle.py` - FastAPI lifecycle hooks for scheduler
- `src/omniforge/api/app.py` - Register scheduler lifecycle hooks
- `src/omniforge/builder/repository.py` - Add query for scheduled agents
- `tests/execution/test_scheduler.py` - Scheduler unit tests
- `tests/execution/test_scheduler_integration.py` - Integration with app lifecycle
