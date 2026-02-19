# TASK-003: Add Cleanup Methods to Repository

## Description

Extend the session repository with methods for marking abandoned sessions and cleaning up old sessions per the retention policy (90 days for completed, 30 days for abandoned).

## Dependencies

- TASK-002: Base repository must exist

## Files to Create/Modify

- **Modify**: `src/omniforge/skills/creation/session_repository.py`

## Key Requirements

- Implement `mark_abandoned()` method:
  - Mark sessions as abandoned if `updated_at < cutoff_date` and status is "active"
  - Only mark non-terminal states (not "completed" or "error")
  - Optional `tenant_id` filter (None means all tenants)
  - Return count of marked sessions
- Implement `cleanup_old_sessions()` method:
  - Delete completed sessions older than `completed_retention_days` (default: 90)
  - Delete abandoned/deleted sessions older than `abandoned_retention_days` (default: 30)
  - Optional `tenant_id` filter
  - Return total count of deleted sessions
- Add appropriate logging for cleanup operations

## Acceptance Criteria

- [ ] `mark_abandoned()` only affects active, non-terminal sessions
- [ ] `mark_abandoned()` updates `updated_at` timestamp
- [ ] `cleanup_old_sessions()` respects different retention periods
- [ ] Both methods work with or without `tenant_id` filter
- [ ] Cleanup is a hard delete (not soft delete)

## Testing

Add to `tests/skills/creation/test_session_repository.py`:
- Test `mark_abandoned()` marks only eligible sessions
- Test `mark_abandoned()` doesn't affect completed/error sessions
- Test `cleanup_old_sessions()` deletes past retention period
- Test tenant filtering works correctly

## Estimated Complexity

Simple (1-2 hours)

## Technical Notes

Use `datetime.utcnow() - timedelta(days=N)` for cutoff calculations. Use SQLAlchemy `delete()` for hard deletes.
