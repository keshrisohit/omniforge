# TASK-005: StreamRouter

**Phase**: 3 - Handoff
**Complexity**: Simple
**Dependencies**: TASK-003, TASK-004
**Files to create/modify**:
- Create `src/omniforge/orchestration/stream_router.py`
- Create `tests/orchestration/test_stream_router.py`

## Description

Implement the `StreamRouter` that routes incoming messages to the correct handler based on whether an active handoff exists for the thread.

### StreamRouter class

**Constructor**: Takes `HandoffManager` and `OrchestrationManager`.

**Core method:**
`route_message(thread_id, tenant_id, user_id, message) -> AsyncIterator[str]`

Logic:
1. Check `handoff_manager.get_active_handoff(thread_id, tenant_id)`
2. If active handoff with state ACTIVE: yield message prefixed with handoff mode indicator `"[HANDOFF:{target_agent_id}] {message}"` (Phase 1 simplified -- full implementation would forward via A2AClient SSE)
3. If no active handoff: yield message through normal flow (Phase 1 simplified -- full implementation would do delegation via OrchestrationManager)

**Helper method:**
`is_handoff_active(thread_id, tenant_id) -> bool`
- Returns True if there is an active handoff for the thread

### Key behaviors

- This is a routing layer, not a processing layer
- Phase 1 is intentionally simplified (placeholder routing logic)
- The architecture enables Phase 2 to add real SSE forwarding without changing the interface
- AsyncIterator return type supports future streaming

## Acceptance Criteria

- Messages route to handoff path when active handoff exists
- Messages route to normal path when no handoff exists
- `is_handoff_active` returns correct boolean
- Handoff routing includes target agent ID in output
- Router correctly handles the case where handoff was just completed
- Tests mock HandoffManager and OrchestrationManager
