# TASK-002: Implement Session Repository with CRUD Operations

## Description

Create the repository class that provides async CRUD operations for skill creation sessions. This follows the established repository pattern in the codebase and enforces tenant isolation on all operations.

## Dependencies

- TASK-001: ORM model must exist

## Files to Create/Modify

- **Create**: `src/omniforge/skills/creation/session_repository.py`

## Key Requirements

- Create `SkillCreationSessionRepository` class with `Database` dependency injection
- Implement `save()` method with upsert semantics (insert or update)
- Implement `load()` method returning `Optional[ConversationContext]`
- Implement `delete()` method with soft delete (status="deleted")
- Implement `list_by_tenant()` with pagination and status filtering
- All methods must validate `tenant_id` is not empty (raise `ValueError`)
- Use `context.model_dump_json()` for serialization and `model_validate_json()` for deserialization
- Update `status` based on `ConversationState` (completed, error)

## Acceptance Criteria

- [ ] Repository initializes with `Database` instance
- [ ] `save()` creates new session or updates existing
- [ ] `load()` returns `None` for non-existent sessions
- [ ] Tenant isolation enforced (different tenant cannot access session)
- [ ] Empty `tenant_id` raises `ValueError`
- [ ] Soft delete sets `status="deleted"`

## Testing

Create `tests/skills/creation/test_session_repository.py`:
- Test save and load round-trip
- Test tenant isolation (tenant A cannot load tenant B's session)
- Test update existing session
- Test list by tenant with pagination
- Test soft delete
- Test empty tenant_id raises ValueError

## Estimated Complexity

Medium (2-3 hours)

## Technical Notes

Follow `ConversationRepository` pattern. Use `async with self.db.session()` for database operations. The session context manager handles commit/rollback automatically.
