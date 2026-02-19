# TASK-001: A2A Protocol Models + Agent Card Extensions

**Phase**: 1 - Foundation
**Complexity**: Simple
**Dependencies**: None
**Files to create/modify**:
- Create `src/omniforge/orchestration/a2a_models.py`
- Modify `src/omniforge/agents/models.py` (add capability models)
- Create `tests/orchestration/test_a2a_models.py`

## Description

Create Pydantic models for orchestration and handoff protocol messages, and extend the existing `AgentCard` with orchestration/handoff capabilities.

### A2A Models (`a2a_models.py`)

**Handoff protocol models:**
- `HandoffRequest` - thread_id, tenant_id, user_id, source/target agent IDs, context_summary, recent_message_count (default 5), handoff_reason, preserve_state, return_expected, handoff_metadata
- `HandoffAccept` - thread_id, source/target agent IDs, accepted boolean, rejection_reason, estimated_duration_seconds
- `HandoffReturn` - thread_id, tenant_id, source/target agent IDs, completion_status (completed/cancelled/error), result_summary, artifacts_created

**Error types:**
- `OrchestrationError(Exception)` - base exception
- `HandoffError(OrchestrationError)` - handoff operations
- `DelegationError(OrchestrationError)` - task delegation

Use Pydantic v2 Field constraints (min_length, max_length) on all string fields. See technical plan Section 1 for exact field definitions.

### Agent Card Extensions (modify `models.py`)

Add to existing `src/omniforge/agents/models.py`:
- `HandoffCapability` - supports_handoff (bool), handoff_triggers (list[str]), workflow_states (list[str]), requires_exclusive_control (bool), max_session_duration_seconds (int)
- `OrchestrationCapability` - can_orchestrate (bool), can_be_orchestrated (bool), supported_delegation_strategies (list[str]), max_concurrent_delegations (int)
- Add both as optional fields on existing `AgentCapabilities` with defaults (handoff disabled, orchestration as sub-agent only)

## Acceptance Criteria

- All models validate correctly with valid data
- All models reject invalid data (empty strings, missing required fields)
- `HandoffRequest` validates thread_id, tenant_id are non-empty
- `HandoffReturn.completion_status` accepts only: completed, cancelled, error
- `AgentCapabilities` remains backward compatible (new fields have defaults)
- Error classes inherit properly: `HandoffError` and `DelegationError` are both `OrchestrationError`
- Unit tests cover validation, serialization/deserialization, and edge cases
