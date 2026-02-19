# Orchestrator and Handoff Patterns - Task Index

**Spec**: [orchestrator-handoff-patterns-spec.md](../../orchestrator-handoff-patterns-spec.md)
**Plan**: [technical-plan-orchestrator-handoff.md](../../technical-plan-orchestrator-handoff.md) (v2.0 HTTP-Only)
**Timeline**: 4 weeks
**Total Tasks**: 8

## Approach

HTTP/SSE only (no gRPC). Uses existing `A2AClient`, `SQLiteConversationRepository`, and `Permission` enum.
No new dependencies. Simple text concatenation for synthesis. Python stdlib logging only.

## Tasks

| ID | Title | Phase | Complexity | Dependencies | Status |
|----|-------|-------|------------|-------------|--------|
| TASK-001 | A2A Protocol Models + Agent Card Extensions | 1 - Foundation | Simple | None | Pending |
| TASK-002 | ThreadManager | 1 - Foundation | Simple | None | Pending |
| TASK-003 | OrchestrationManager (all strategies + synthesis) | 2 - Orchestrator | Medium | TASK-001 | Pending |
| TASK-004 | HandoffManager + State Persistence | 3 - Handoff | Medium | TASK-001, TASK-002 | Pending |
| TASK-005 | StreamRouter | 3 - Handoff | Simple | TASK-003, TASK-004 | Pending |
| TASK-006 | Security (RBAC + Context Sanitizer) | 4 - Integration | Simple | TASK-004 | Pending |
| TASK-007 | Structured Logging | 4 - Integration | Simple | TASK-003, TASK-004 | Pending |
| TASK-008 | End-to-End Integration Tests | 4 - Integration | Medium | All above | Pending |

## Dependency Graph

```
TASK-001 (A2A Models) ----+---> TASK-003 (OrchestrationManager) --+
                          |                                        |
TASK-002 (ThreadManager) -+---> TASK-004 (HandoffManager) --------+
                                                                   |
                          +-------- TASK-005 (StreamRouter) <------+
                          |
                          +-------- TASK-006 (Security) <--- TASK-004
                          |
                          +-------- TASK-007 (Logging) <--- TASK-003, TASK-004
                          |
                          +-------- TASK-008 (Integration Tests) <--- All
```

## Parallelization

- TASK-001 and TASK-002 can run in parallel (no mutual dependency)
- TASK-003 and TASK-004 can run in parallel after their dependencies complete
- TASK-005, TASK-006, TASK-007 can run in parallel
- TASK-008 must be last

## Files Created/Modified

### New Files
- `src/omniforge/orchestration/a2a_models.py`
- `src/omniforge/orchestration/thread.py`
- `src/omniforge/orchestration/manager.py`
- `src/omniforge/orchestration/handoff.py`
- `src/omniforge/orchestration/stream_router.py`
- `src/omniforge/orchestration/sanitizer.py`

### Modified Files
- `src/omniforge/agents/models.py` (add HandoffCapability, OrchestrationCapability)
- `src/omniforge/security/rbac.py` (add orchestration permissions)

### Test Files
- `tests/orchestration/test_a2a_models.py`
- `tests/orchestration/test_thread.py`
- `tests/orchestration/test_manager.py`
- `tests/orchestration/test_handoff.py`
- `tests/orchestration/test_stream_router.py`
- `tests/orchestration/test_sanitizer.py`
- `tests/orchestration/test_orchestration_integration.py`
- `tests/orchestration/test_handoff_integration.py`

## Key Decisions (v2.0 vs v1.0)

1. No gRPC -- all inter-agent communication uses existing `A2AClient` (HTTP/SSE)
2. No protobuf -- no `.proto` files needed
3. No new DB tables -- handoff state stored in existing `state_metadata` JSON column
4. No external dependencies -- no structlog, prometheus_client, or opentelemetry
5. Simple text concatenation for synthesis (LLM synthesis deferred to Phase 2)
6. Models live in `src/omniforge/orchestration/a2a_models.py` (not a separate `a2a/` package)
