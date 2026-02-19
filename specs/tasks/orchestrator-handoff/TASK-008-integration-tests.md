# TASK-008: End-to-End Integration Tests

**Phase**: 4 - Integration
**Complexity**: Medium
**Dependencies**: All previous tasks (TASK-001 through TASK-007)
**Files to create/modify**:
- Create `tests/orchestration/test_orchestration_integration.py`
- Create `tests/orchestration/test_handoff_integration.py`

## Description

Write integration tests that exercise the full orchestration and handoff flows with real database persistence (in-memory SQLite) and mocked A2AClient.

### Orchestration Integration Tests (`test_orchestration_integration.py`)

1. **Full Q&A orchestration flow**: Create conversation -> delegate to 2 mock sub-agents (parallel) -> collect results -> synthesize -> verify response text contains both agent outputs
2. **Sequential delegation**: Same flow but with SEQUENTIAL strategy, verify agents called in order
3. **First-success strategy**: Mock one agent to fail, one to succeed, verify only successful result returned
4. **All agents fail**: Mock all agents to raise exceptions, verify graceful error message from synthesize
5. **Timeout handling**: Mock agent with slow response, verify timeout behavior

### Handoff Integration Tests (`test_handoff_integration.py`)

1. **Full handoff lifecycle**: Create conversation -> initiate handoff -> verify state_metadata persisted in DB -> complete handoff -> verify state cleared from cache
2. **Concurrent handoff prevention**: Initiate handoff -> attempt second handoff on same thread -> verify HandoffError raised
3. **Handoff cancellation**: Initiate -> cancel -> verify state is CANCELLED and cache cleared
4. **Handoff recovery from database**: Initiate handoff -> clear in-memory cache manually -> call get_active_handoff -> verify session loaded from DB
5. **StreamRouter routing**: Create active handoff -> route message -> verify handoff path. Complete handoff -> route message -> verify normal path.
6. **Tenant isolation**: Create handoff in tenant A -> attempt to access from tenant B -> verify None/failure

### Test infrastructure

- Use existing `Database` class with `sqlite+aiosqlite:///:memory:`
- Use existing `SQLiteConversationRepository`
- Mock `A2AClient.send_task()` to yield controlled `TaskEvent` sequences (status -> message -> done)
- Use `pytest` with `pytest-asyncio` for async tests

## Acceptance Criteria

- All integration tests pass with in-memory SQLite
- Tests verify database persistence (not just in-memory state)
- Tests verify tenant isolation across all operations
- Tests cover error scenarios (agent failure, duplicate handoff, wrong tenant)
- Tests are deterministic (no flaky timing dependencies)
- Mock A2AClient produces realistic event sequences
