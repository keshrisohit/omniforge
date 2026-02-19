# TASK-003: Agent Error Hierarchy

**Status**: Complete
**Complexity**: Simple
**Dependencies**: None
**Phase**: 1 - Core Agent Interface

## Objective

Create agent-specific exception hierarchy following the pattern established in `chat/errors.py`.

## Requirements

1. Create `src/omniforge/agents/errors.py` with:
   - `AgentError` base class (message, code, status_code)
   - `AgentNotFoundError` (404)
   - `TaskNotFoundError` (404)
   - `TaskStateError` (409) - invalid operation for current state
   - `SkillNotFoundError` (404)
   - `AgentProcessingError` (500)

2. Mirror the ChatError pattern exactly for consistency

3. Export errors from `agents/__init__.py`

## Acceptance Criteria

- [x] All errors inherit from AgentError
- [x] Error codes are snake_case strings
- [x] HTTP status codes are appropriate (4xx for client errors, 5xx for server)
- [x] Unit tests in `tests/agents/test_errors.py`
- [x] Error messages include relevant identifiers (agent_id, task_id)
