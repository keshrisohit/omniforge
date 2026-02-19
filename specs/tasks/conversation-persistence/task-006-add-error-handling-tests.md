# TASK-006: Add Error Handling and Edge Case Tests

## Description

Add comprehensive tests for error scenarios, concurrent access, and edge cases to ensure the persistence layer is robust and handles failures gracefully.

## Dependencies

- TASK-004: Agent integration must be complete
- TASK-002: Repository must be implemented

## Files to Create/Modify

- **Modify**: `tests/skills/creation/test_session_repository.py`
- **Modify**: `tests/skills/creation/test_agent_persistence.py`

## Key Requirements

Test scenarios to cover:
- **DB unavailable**: Agent continues in-memory when DB fails
- **Persistence error**: Errors logged but user gets response
- **Concurrent access**: Two saves to same session (last-write-wins)
- **Corrupted JSON**: Load returns None for invalid JSON
- **Large context**: Context with 100+ messages saves/loads correctly
- **Empty fields**: Handle optional fields being None
- **Status transitions**: Verify status updates (active -> completed -> deleted)
- **Retention edge cases**: Sessions exactly at cutoff boundary

## Acceptance Criteria

- [ ] All error scenarios have explicit tests
- [ ] Tests use mocking for DB failures
- [ ] Concurrent access test demonstrates last-write-wins
- [ ] Corrupted data handling is tested
- [ ] Large context handling is verified

## Testing

This task IS the testing task. Focus on:
- Using `unittest.mock.patch` for simulating failures
- Using `asyncio.gather` for concurrent access tests
- Direct DB inserts for corrupted data tests
- Performance assertions for large contexts (< 500ms)

## Estimated Complexity

Medium (2-3 hours)

## Technical Notes

Use pytest fixtures for test database setup. Mock at repository level for agent tests, at DB session level for repository tests.
