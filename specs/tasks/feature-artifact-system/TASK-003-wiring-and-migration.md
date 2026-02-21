# TASK-003: Base Agent Wiring and Construction Site Migration

**Status**: Pending  |  **Complexity**: Medium  |  **Dependencies**: TASK-001, TASK-002

## Objective

Wire `artifact_store` into `BaseAgent` and update all `Artifact(...)` construction sites to the new field names.

## Requirements

1. In `src/omniforge/agents/base.py`, add `artifact_store: Optional[Any] = None` to `BaseAgent.__init__()` and store as `self.artifact_store` (same `Any` pattern as `prompt_config`).

2. Update `src/omniforge/agents/streaming.py` docstring examples to use new Artifact fields.

3. Update all test files constructing `Artifact(...)`. Known sites:
   - `tests/agents/test_events.py`, `tests/agents/test_models.py`, `tests/agents/test_streaming.py`
   - `tests/tools/builtin/test_subagent.py`, `tests/tasks/test_manager.py`, `tests/tasks/test_models.py`
   - `tests/orchestration/test_router.py`

   For each: rename `content` -> `inline_content`, use `ArtifactType` enum for `type`, add `tenant_id="test-tenant"`, set `id=None` where store-generated.

4. Run full test suite (`pytest --no-cov -q`) and fix any remaining breakage.

## Acceptance Criteria

- `BaseAgent(artifact_store=store)` works; defaults to `None` when omitted
- All existing tests pass with updated `Artifact(...)` calls
- No regressions in full test suite
