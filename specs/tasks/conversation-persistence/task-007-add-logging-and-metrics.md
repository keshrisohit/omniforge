# TASK-007: Add Logging and Observability

## Description

Add comprehensive logging throughout the persistence layer for debugging, monitoring, and operational visibility. Include timing for latency tracking.

## Dependencies

- TASK-004: Agent integration must be complete
- TASK-002: Repository must be implemented

## Files to Create/Modify

- **Modify**: `src/omniforge/skills/creation/session_repository.py`
- **Modify**: `src/omniforge/skills/creation/agent.py`
- **Modify**: `src/omniforge/skills/creation/session_cleaner.py`

## Key Requirements

Add logging for:
- **Repository**:
  - DEBUG: Save/load operations with session_id and tenant_id
  - DEBUG: Context size in bytes after serialization
  - INFO: Cleanup operations with counts
  - WARNING: Failed deserializations
  - ERROR: Database operation failures
- **Agent**:
  - INFO: Session restored from database
  - DEBUG: Session created new
  - WARNING: Failed to persist session
  - DEBUG: Persist latency (measure time)
- **Cleaner**:
  - INFO: Cleanup job started/stopped
  - INFO: Cleanup cycle completed with stats
  - ERROR: Cleanup cycle failed

## Acceptance Criteria

- [ ] All significant operations have appropriate log level
- [ ] Session IDs and tenant IDs included in log context
- [ ] Persist latency is measurable from logs
- [ ] No sensitive data (context content) logged

## Testing

Verify via log inspection during existing tests:
- Enable debug logging in test fixtures
- Assert expected log messages appear

## Estimated Complexity

Simple (1-2 hours)

## Technical Notes

Use `logger = logging.getLogger(__name__)` pattern. Use f-strings for log messages. Measure time with `datetime.utcnow()` or `time.perf_counter()`.
