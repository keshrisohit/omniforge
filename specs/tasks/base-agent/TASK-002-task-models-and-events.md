# TASK-002: Task Models and Events

**Status**: Pending
**Complexity**: Medium
**Dependencies**: TASK-001
**Phase**: 1 - Core Agent Interface

## Objective

Create task lifecycle models and streaming event types for A2A task processing.

## Requirements

1. Create `src/omniforge/tasks/` module with `__init__.py`

2. Create `src/omniforge/tasks/models.py` with:
   - `TaskState` enum (submitted, working, input_required, auth_required, completed, failed, cancelled, rejected)
   - `TaskMessage` - id, role (user/agent), parts, created_at
   - `TaskError` - code, message, details
   - `Task` - id, agent_id, state, messages, artifacts, error, timestamps, tenant/user context, parent_task_id
   - `TaskCreateRequest` and `TaskSendRequest` for API

3. Create `src/omniforge/agents/events.py` with:
   - `BaseTaskEvent` base class with task_id, timestamp
   - `TaskStatusEvent` - state transitions
   - `TaskMessageEvent` - agent messages (partial/complete)
   - `TaskArtifactEvent` - artifact delivery
   - `TaskDoneEvent` - completion
   - `TaskErrorEvent` - error reporting
   - `TaskEvent` union type

## Acceptance Criteria

- [ ] Task state transitions are validated (immutable after terminal state)
- [ ] Events use Literal types for `type` field discrimination
- [ ] All models import MessagePart and Artifact from TASK-001
- [ ] Unit tests in `tests/tasks/test_models.py` and `tests/agents/test_events.py`
- [ ] 80%+ test coverage for models
