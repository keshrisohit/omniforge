# TASK-005: Create Background Session Cleanup Job

## Description

Implement a background asyncio task that periodically marks abandoned sessions and cleans up old sessions per the retention policy. Includes proper lifecycle management (start/stop).

## Dependencies

- TASK-003: Cleanup methods must exist in repository

## Files to Create/Modify

- **Create**: `src/omniforge/skills/creation/session_cleaner.py`

## Key Requirements

- Create `SkillCreationSessionCleaner` class with:
  - Constructor accepting `repository` and optional `cleanup_interval_seconds` (default: 86400 = 24 hours)
  - `async start()` method to start background task
  - `async stop()` method to gracefully stop task
  - Private `_cleanup_loop()` that runs until stopped
  - Private `_run_cleanup()` that calls repository cleanup methods
- Handle `asyncio.CancelledError` gracefully in stop
- Sleep in small increments (60s) to allow quick shutdown
- Log cleanup results (marked, deleted counts)
- Error in cleanup should be logged but not stop the loop

## Acceptance Criteria

- [ ] Cleaner starts background task on `start()`
- [ ] Cleaner stops cleanly on `stop()` (no hanging tasks)
- [ ] Cleanup runs immediately on start, then at interval
- [ ] Cleanup errors are logged but don't stop the loop
- [ ] Multiple `start()` calls are idempotent (no-op if running)

## Testing

Create `tests/skills/creation/test_session_cleaner.py`:
- Test start/stop lifecycle
- Test cleanup runs on start
- Test cleanup error doesn't stop loop (mock repository to raise)
- Test stop cancels task cleanly

## Estimated Complexity

Medium (2 hours)

## Technical Notes

Use `asyncio.create_task()` for background task. Store task reference for cancellation. Check `_running` flag in sleep loop for responsive shutdown.
