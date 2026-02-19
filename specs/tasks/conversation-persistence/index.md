# Conversation History Persistence - Task Index

**Feature**: Persistent conversation history for skill creation chatbot
**Spec**: `specs/conversation-history-persistence-spec.md`
**Technical Plan**: `specs/conversation-history-persistence-plan.md`
**Created**: 2026-02-04

## Task Summary

| ID | Title | Status | Dependencies | Complexity | Est. Time |
|----|-------|--------|--------------|------------|-----------|
| 001 | Create ORM Model | Pending | None | Simple | 1-2h |
| 002 | Implement Repository CRUD | Pending | 001 | Medium | 2-3h |
| 003 | Add Cleanup Methods to Repository | Pending | 002 | Simple | 1-2h |
| 004 | Integrate Persistence into Agent | Pending | 002 | Medium | 2-3h |
| 005 | Create Background Cleanup Job | Pending | 003 | Medium | 2h |
| 006 | Add Error Handling Tests | Pending | 002, 004 | Medium | 2-3h |
| 007 | Add Logging and Observability | Pending | 002, 004 | Simple | 1-2h |
| 008 | Integration Test and Documentation | Pending | All | Medium | 2-3h |

**Total Estimated Time**: 14-20 hours

## Dependency Graph

```
TASK-001 (ORM Model)
    |
    v
TASK-002 (Repository CRUD)
    |
    +---> TASK-003 (Cleanup Methods) ---> TASK-005 (Cleanup Job)
    |
    +---> TASK-004 (Agent Integration)
    |         |
    |         v
    +---> TASK-006 (Error Tests) <---+
    |                                |
    +---> TASK-007 (Logging) --------+
                                     |
                                     v
                              TASK-008 (Integration)
```

## Implementation Phases

### Phase 1: Database Foundation (Tasks 001-003)
Build the persistence layer: ORM model, repository with CRUD, and cleanup methods.

### Phase 2: Agent Integration (Task 004)
Modify the agent to use the repository for auto-save and session restoration.

### Phase 3: Background Cleanup (Task 005)
Add the background job for automated session cleanup.

### Phase 4: Quality Assurance (Tasks 006-008)
Comprehensive testing, logging, and documentation.

## Files Created/Modified

**New Files**:
- `src/omniforge/skills/creation/orm.py` - ORM model
- `src/omniforge/skills/creation/session_repository.py` - Repository
- `src/omniforge/skills/creation/session_cleaner.py` - Background job
- `tests/skills/creation/test_orm.py` - ORM tests
- `tests/skills/creation/test_session_repository.py` - Repository tests
- `tests/skills/creation/test_session_cleaner.py` - Cleaner tests
- `tests/skills/creation/test_agent_persistence.py` - Agent persistence tests
- `tests/skills/creation/test_persistence_integration.py` - Integration tests

**Modified Files**:
- `src/omniforge/skills/creation/agent.py` - Add persistence support

## Notes

- Tasks are designed to be completed in order for optimal development flow
- Each task is independently testable
- Phase 1 and Phase 2 are critical path; Phase 3-4 can be parallelized after Phase 2
- Breaking change: `handle_message()` will require `tenant_id` parameter
