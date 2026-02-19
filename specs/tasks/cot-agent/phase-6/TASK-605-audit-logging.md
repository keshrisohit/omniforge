# TASK-605: Implement Audit Logging for Compliance

## Description

Create the audit logging system that records all agent operations for compliance and investigation purposes. This provides immutable records of what agents did, when, and why.

## Requirements

- Create `AuditEvent` model:
  - id, timestamp
  - tenant_id, user_id, agent_id, task_id
  - event_type (tool_call, tool_result, chain_start, chain_complete, etc.)
  - resource_type, resource_id
  - action, outcome (success/failure)
  - metadata (JSON for additional context)
  - ip_address, user_agent (optional)
- Create `AuditLogger` class:
  - `log_tool_call(context, tool_name, arguments, result)` method
  - `log_chain_event(chain, event_type)` method
  - `log_access(user, resource_type, resource_id, action)` method
  - Redact sensitive fields before logging
  - Support async logging (non-blocking)
- Create `AuditRepository` for persistence:
  - Append-only design (no updates/deletes)
  - `save(event)` async method
  - `query(tenant_id, filters, date_range)` method
- Integrate with ToolExecutor for automatic logging

## Acceptance Criteria

- [ ] All tool calls logged automatically
- [ ] Chain lifecycle events logged
- [ ] Sensitive data redacted in logs
- [ ] Append-only - no modification of past events
- [ ] Query by tenant, date range, event type
- [ ] Async logging doesn't block execution
- [ ] Unit tests verify logging behavior

## Dependencies

- TASK-102 (for ToolCallContext)
- TASK-105 (for ToolExecutor integration)
- TASK-603 (for chain events)

## Files to Create/Modify

- `src/omniforge/enterprise/audit.py` (new)
- `src/omniforge/storage/audit_repository.py` (new)
- `tests/enterprise/test_audit.py` (new)

## Estimated Complexity

Medium (4-5 hours)

## Key Considerations

- Immutability is critical for compliance
- Consider log rotation/archival
- Sensitive field redaction must be thorough
