# TASK-004: Integrate Persistence into SkillCreationAgent

## Description

Modify `SkillCreationAgent` to accept an optional session repository and integrate persistence into the message handling flow. This includes loading from DB on session restore and auto-saving after each message.

## Dependencies

- TASK-002: Repository must be implemented

## Files to Create/Modify

- **Modify**: `src/omniforge/skills/creation/agent.py`

## Key Requirements

- Add `session_repository: Optional[SkillCreationSessionRepository]` parameter to `__init__`
- Add `tenant_id: str` parameter to `handle_message()` method signature
- Modify `get_session_context()` to:
  - Accept `tenant_id` parameter
  - Check in-memory cache first
  - Fall back to database load if repository exists
  - Log session restoration
- Add `_persist_context()` private method:
  - Non-blocking persistence (logs errors, doesn't raise by default)
  - Accept `ignore_errors: bool` parameter for error path persistence
- Call `_persist_context()` after successful message processing
- Call `_persist_context()` with `ignore_errors=True` in exception handler
- Update `_clear_session()` to accept `tenant_id` (for future audit trail)

## Acceptance Criteria

- [ ] Agent works without repository (backward compatible)
- [ ] Agent loads session from DB if not in memory
- [ ] Agent saves session after each message
- [ ] Persistence failure doesn't block user response
- [ ] Error path still persists context for recovery
- [ ] `tenant_id` is required for `handle_message()`

## Testing

Create `tests/skills/creation/test_agent_persistence.py`:
- Test agent works without repository (None)
- Test session restored after memory clear
- Test persistence error logged but doesn't crash
- Test tenant isolation in agent

## Estimated Complexity

Medium (2-3 hours)

## Technical Notes

Keep in-memory cache for performance. DB is fallback + durability. The agent signature change for `tenant_id` is breaking - document in comments.
