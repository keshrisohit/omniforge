# TASK-007: Structured Logging

**Phase**: 4 - Integration
**Complexity**: Simple
**Dependencies**: TASK-003, TASK-004
**Files to create/modify**:
- Modify `src/omniforge/orchestration/manager.py` (add logging)
- Modify `src/omniforge/orchestration/handoff.py` (add logging)
- Modify `src/omniforge/orchestration/stream_router.py` (add logging)

## Description

Add structured logging using Python stdlib `logging` module to all orchestration components. No external dependencies (no Prometheus, no OpenTelemetry).

### Logging approach

Use `logging.getLogger("omniforge.orchestration")` with structured data in `extra` dict.

### Where to add logging

**OrchestrationManager:**
- INFO: delegation started (extra: thread_id, strategy, target_agents, tenant_id)
- INFO: delegation completed (extra: thread_id, total_agents, successful_count, total_latency_ms)
- WARNING: individual agent failure (extra: thread_id, agent_id, error)
- DEBUG: per-agent result details

**HandoffManager:**
- INFO: handoff initiated (extra: thread_id, source_agent, target_agent, reason, tenant_id)
- INFO: handoff completed (extra: thread_id, completion_status, duration_seconds)
- WARNING: handoff error (extra: thread_id, error details)
- INFO: handoff cancelled (extra: thread_id)

**StreamRouter:**
- DEBUG: message routed (extra: thread_id, route_type "handoff" or "normal")

### Key behaviors

- Use `extra` dict for structured fields (not string interpolation in the message)
- Logger name: `omniforge.orchestration` (dot-separated for hierarchy)
- No new dependencies -- stdlib logging only
- Log levels: DEBUG for routine operations, INFO for state transitions, WARNING for recoverable errors

## Acceptance Criteria

- All orchestration operations produce log entries at appropriate levels
- Log entries include thread_id, tenant_id, and agent IDs in extra dict
- No sensitive user data in logs (use sanitizer from TASK-006 if context is logged)
- Tests can verify logging output using pytest `caplog` fixture
