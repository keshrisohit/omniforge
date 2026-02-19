# TASK-002: ThreadManager

**Phase**: 1 - Foundation
**Complexity**: Simple
**Dependencies**: None
**Files to create/modify**:
- Create `src/omniforge/orchestration/thread.py`
- Create `tests/orchestration/test_thread.py`

## Description

Implement `ThreadManager` for thread lifecycle management and context retrieval. This is the security-critical component that validates thread ownership before any orchestration or handoff operation.

### ThreadContext model

Pydantic model: thread_id, tenant_id, user_id, created_at, updated_at, current_active_agent (str), is_handoff_active (bool, default False), handoff_target_agent (Optional[str]), total_messages (int).

### ThreadManager class

**Constructor**: Takes `SQLiteConversationRepository` (from existing `src/omniforge/conversation/sqlite_repository.py`).

**Methods:**
- `validate_thread(thread_id, tenant_id, user_id=None) -> bool` - Validates thread belongs to tenant. If user_id provided, also validates ownership. Returns False on any error (not found, wrong tenant, exception). Must never raise.
- `get_recent_messages(thread_id, tenant_id, count=10, include_system=False) -> list[Message]` - Gets recent messages using existing `conversation_repo.get_recent_messages()`. Filters out system messages unless include_system=True.
- `get_thread_context(thread_id, tenant_id) -> ThreadContext` - Returns a `ThreadContext` model with thread metadata from the conversation record. Reads handoff state from `state_metadata` if present.

### Key behaviors

- All methods validate tenant_id before accessing data (security boundary)
- Use existing `SQLiteConversationRepository` methods only -- no raw SQL
- `validate_thread` must never raise; returns False on any failure
- thread_id strings converted to UUID when calling repo methods

## Acceptance Criteria

- `validate_thread` returns True for valid thread+tenant combinations
- `validate_thread` returns False for wrong tenant, nonexistent thread, or invalid UUID
- `validate_thread` with user_id checks user ownership
- `get_recent_messages` respects count limit and system message filtering
- `get_thread_context` returns correct metadata from conversation record
- Tests use in-memory SQLite database with the existing `Database` class
