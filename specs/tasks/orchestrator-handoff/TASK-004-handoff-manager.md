# TASK-004: HandoffManager + State Persistence

**Phase**: 3 - Handoff
**Complexity**: Medium
**Dependencies**: TASK-001, TASK-002
**Files to create/modify**:
- Create `src/omniforge/orchestration/handoff.py`
- Create `tests/orchestration/test_handoff.py`

## Description

Implement the `HandoffManager` for transferring conversation control between agents, with state persisted in the existing `ConversationModel.state_metadata` JSON column.

### Models (in handoff.py)

- `HandoffState(str, Enum)` - PENDING, ACTIVE, RETURNING, COMPLETED, CANCELLED, ERROR
- `HandoffSession(BaseModel)` - handoff_id, thread_id, tenant_id, user_id, source_agent_id, target_agent_id, state (HandoffState), context_summary, handoff_reason, started_at, completed_at, result_summary, artifacts_created, workflow_state, workflow_metadata

### HandoffManager class

**Constructor**: Takes `A2AClient` and `SQLiteConversationRepository`. Maintains `_active_handoffs: dict[str, HandoffSession]` as in-memory cache (thread_id -> session).

**Methods:**

`initiate_handoff(thread_id, tenant_id, user_id, source_agent_id, target_agent_card, context_summary, handoff_reason) -> HandoffAccept`
1. Check no existing active handoff for this thread (raise `HandoffError` if one exists)
2. Create `HandoffSession` with new UUID handoff_id, state=ACTIVE
3. Phase 1 simplification: assume acceptance (no actual HTTP negotiation with target)
4. Persist session to `state_metadata["handoff_session"]` via `conversation_repo.update_state()`
5. Cache in `_active_handoffs`
6. Return `HandoffAccept(accepted=True)`

`complete_handoff(thread_id, tenant_id, completion_status, result_summary=None, artifacts=None) -> HandoffReturn`
1. Get active session (raise HandoffError if none)
2. Update session state to COMPLETED/CANCELLED/ERROR based on completion_status
3. Set completed_at, result_summary, artifacts_created
4. Persist updated state to state_metadata
5. Remove from in-memory cache
6. Return `HandoffReturn`

`cancel_handoff(thread_id, tenant_id) -> HandoffReturn`
- Calls `complete_handoff` with status="cancelled"

`get_active_handoff(thread_id, tenant_id) -> Optional[HandoffSession]`
- Check cache first, then load from database state_metadata
- Only return if state is ACTIVE

`_persist_handoff_session(session) -> None`
- Load conversation via repo, update `state_metadata["handoff_session"]` with `session.model_dump()`, call `conversation_repo.update_state()`

### Key behaviors

- State persisted in existing `state_metadata` JSON column (no new tables)
- In-memory cache for fast lookups; database is source of truth
- Only one active handoff per thread enforced
- All operations validate tenant_id via conversation repo

## Acceptance Criteria

- `initiate_handoff` creates session and persists to state_metadata
- `initiate_handoff` raises HandoffError if active handoff already exists
- `complete_handoff` transitions state and clears cache
- `get_active_handoff` returns from cache or loads from database
- `get_active_handoff` returns None for completed/cancelled handoffs
- State round-trips correctly through JSON serialization (model_dump / model construction)
- Tests use in-memory SQLite with existing Database and ConversationRepository
