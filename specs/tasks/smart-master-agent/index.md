# Smart Master Agent - Task Index

**Feature**: Transform master agent from stateless keyword matcher to context-aware, LLM-powered orchestrator
**Technical Plan**: `specs/smart-master-agent-technical-plan.md`
**Review**: `specs/plan-review/smart-master-agent-technical-plan-review.md`
**Total Tasks**: 8
**Estimated Effort**: 7-10 days

---

## Review Issues Addressed

| Review Issue | Severity | Addressed In |
|-------------|----------|-------------|
| ISSUE 1: Circular dependency (conversation -> agents) | CRITICAL | TASK-001 (extract to routing/models.py) |
| ISSUE 2: Missing tenant validation on get_recent_messages | HIGH | TASK-001 (Protocol), TASK-002 (implementations) |
| ISSUE 3: Silent new conversation on invalid ID | HIGH | TASK-006 (ChatService validation) |
| ISSUE 4: Over-engineered context assembler | MEDIUM | TASK-003 (simplified to message count for v1) |
| ISSUE 5: Missing storage error handling | MEDIUM | TASK-006 (try/except wrappers) |
| ISSUE 6: Missing LLM timeout | MEDIUM | TASK-004 (asyncio.wait_for) |

---

## Task List

### Phase 1: Storage Foundation

| Task | Title | Status | Dependencies | Complexity |
|------|-------|--------|-------------|-----------|
| TASK-001 | Extract Routing Models + Conversation Domain Models | Pending | None | Medium |
| TASK-002 | Conversation Repositories (SQLite + InMemory) | Pending | TASK-001 | Medium |

### Phase 2: Context Passing

| Task | Title | Status | Dependencies | Complexity |
|------|-------|--------|-------------|-----------|
| TASK-003 | Context Assembler (pure functions) | Pending | TASK-001 | Simple |
| TASK-006 | Update Chat Pipeline (Service + Generators) | Pending | TASK-001, TASK-002, TASK-003 | Medium |

### Phase 3: LLM Intent Analysis

| Task | Title | Status | Dependencies | Complexity |
|------|-------|--------|-------------|-----------|
| TASK-004 | LLM Intent Analyzer | Pending | TASK-001, TASK-003 | Medium |
| TASK-005 | Update MasterAgent (LLM + keyword fallback) | Pending | TASK-001, TASK-004 | Medium |

### Phase 4: Verification

| Task | Title | Status | Dependencies | Complexity |
|------|-------|--------|-------------|-----------|
| TASK-007 | Integration Tests (full flow) | Pending | TASK-001 through TASK-006 | Medium |
| TASK-008 | Intent Eval Test Set (30+ cases) | Pending | TASK-004, TASK-005 | Simple |

---

## Dependency Graph

```
TASK-001 (routing models + conversation domain)
  |
  +---> TASK-002 (repositories)
  |       |
  +---> TASK-003 (context assembler)
  |       |
  |   TASK-002 + TASK-003
  |       |
  |       +---> TASK-006 (chat pipeline)
  |
  +---> TASK-004 (LLM intent analyzer) [also depends on TASK-003]
          |
          +---> TASK-005 (update master agent)
          |
          +---> TASK-008 (eval test set)

TASK-001 through TASK-006
  |
  +---> TASK-007 (integration tests)
```

## Parallelization Opportunities

After TASK-001 is complete, the following can be worked on in parallel:
- **Track A**: TASK-002 (repos) -> TASK-006 (chat pipeline)
- **Track B**: TASK-003 (context) -> TASK-004 (LLM analyzer) -> TASK-005 (master agent)

TASK-003 is needed by both tracks so it should be prioritized early.

---

## New Files Created

```
src/omniforge/routing/
    __init__.py
    models.py                        # ActionType, RoutingDecision (extracted)

src/omniforge/conversation/
    __init__.py
    models.py                        # Conversation, Message, MessageRole
    repository.py                    # ConversationRepository Protocol
    orm.py                           # SQLAlchemy ORM models
    sqlite_repository.py             # SQLAlchemy implementation
    memory_repository.py             # In-memory implementation
    context.py                       # Context assembly pure functions
    intent_analyzer.py               # LLMIntentAnalyzer

tests/routing/
    __init__.py
    test_models.py

tests/conversation/
    __init__.py
    test_models.py
    test_context.py
    test_intent_analyzer.py
    test_sqlite_repository.py
    test_memory_repository.py
    test_intent_eval.py

tests/integration/
    test_smart_master_agent.py
    test_backward_compat.py

tests/agents/
    test_master_agent_intent.py      # New LLM + fallback tests
```

## Modified Files

```
src/omniforge/agents/master_agent.py         # Import from routing.models, add analyzer
src/omniforge/chat/service.py                # Add repo + tenant params
src/omniforge/chat/response_generator.py     # Forward history param
src/omniforge/chat/master_response_generator.py  # Accept + assemble context
```
