
# Core Chatbot Agent - Task Index

| Task | Title | Deps | Complexity | Status |
|------|-------|------|------------|--------|
| [TASK-001](./TASK-001-setup-infrastructure.md) | Setup Infrastructure | - | Simple | [ ] |
| [TASK-002](./TASK-002-core-models-and-exceptions.md) | Core Models and Exceptions | 001 | Medium | [ ] |
| [TASK-003](./TASK-003-streaming-layer.md) | Streaming Layer | 002 | Medium | [ ] |
| [TASK-004](./TASK-004-chat-service.md) | Chat Service | 003 | Medium | [ ] |
| [TASK-005](./TASK-005-api-layer.md) | API Layer | 004 | Medium | [ ] |
| [TASK-006](./TASK-006-unit-tests.md) | Unit Tests | 003 | Medium | [ ] |
| [TASK-007](./TASK-007-integration-tests.md) | Integration Tests | 005 | Medium | [ ] |
| [TASK-008](./TASK-008-quality-verification.md) | Quality Verification | 007 | Simple | [ ] |

## Task Summary

| # | Task | What It Covers |
|---|------|----------------|
| 1 | Setup Infrastructure | Dependencies, directory structure, pytest config |
| 2 | Core Models and Exceptions | All Pydantic models + custom exception hierarchy |
| 3 | Streaming Layer | SSE formatting + placeholder response generator |
| 4 | Chat Service | Request processing orchestration |
| 5 | API Layer | Chat endpoint + error middleware + app factory |
| 6 | Unit Tests | Model validation + streaming + generator tests |
| 7 | Integration Tests | Fixtures + endpoint + service tests |
| 8 | Quality Verification | pytest, coverage, black, ruff, mypy |

## Critical Path

```
001 -> 002 -> 003 -> 004 -> 005 -> 007 -> 008
                 \-> 006 (parallel with 004+)
```

## Parallel Opportunities

- TASK-006 (Unit Tests) can start after TASK-003 completes
- TASK-006 and TASK-004/005 can run in parallel

## Quality Gates

- `pytest` - all tests pass
- `pytest --cov` - coverage > 80%
- `black --check .` - formatted
- `ruff check .` - no lint errors
- `mypy src/` - no type errors
