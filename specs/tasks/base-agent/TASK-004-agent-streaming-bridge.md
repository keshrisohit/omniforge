# TASK-004: Agent Streaming Bridge

**Status**: Complete
**Complexity**: Medium
**Dependencies**: TASK-002, TASK-003
**Phase**: 1 - Core Agent Interface

## Objective

Create streaming utilities for agent task events that reuse `chat/streaming.py` infrastructure.

## Requirements

1. Create `src/omniforge/agents/streaming.py` with:
   - `format_task_event(event: TaskEvent) -> str` - uses `format_sse_event` from chat/streaming
   - Individual formatters for each event type (for type-specific handling if needed)
   - `stream_task_events(events: AsyncIterator[TaskEvent]) -> AsyncIterator[str]` - converts event stream to SSE
   - `stream_task_with_error_handling(events, task_id)` - wraps stream with error handling

2. Key constraint: MUST import and reuse `format_sse_event` from `chat/streaming.py`

3. Handle async iteration properly with try/except for error events

## Acceptance Criteria

- [x] Reuses `format_sse_event` from `chat/streaming.py` (no duplication)
- [x] All event types produce valid SSE format: `event: {type}\ndata: {json}\n\n`
- [x] Error handling yields TaskErrorEvent on exceptions
- [x] Unit tests in `tests/agents/test_streaming.py` with async fixtures
- [x] Integration test verifies SSE format matches chat streaming output
