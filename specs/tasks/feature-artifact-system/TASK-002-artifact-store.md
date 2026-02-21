# TASK-002: Artifact Storage Layer

**Status**: Pending
**Complexity**: Medium
**Dependencies**: TASK-001

## Objective

Add `ArtifactStore` protocol and `InMemoryArtifactRepository` implementation to the storage layer.

## Requirements

1. In `src/omniforge/storage/base.py`, add `ArtifactStore(Protocol)` with three methods:
   - `store(artifact) -> str` -- persist artifact, return ID (generate UUID if `artifact.id` is None)
   - `fetch(artifact_id, tenant_id) -> Optional[Artifact]` -- tenant-scoped lookup, return None if not found or wrong tenant
   - `delete(artifact_id, tenant_id) -> None` -- raise `ValueError` if not found within tenant
   - Use `TYPE_CHECKING` guard for the `Artifact` import (same pattern as `BaseAgent`)

2. In `src/omniforge/storage/memory.py`, add `InMemoryArtifactRepository`:
   - Nested dict storage: `{tenant_id: {artifact_id: Artifact}}`
   - `asyncio.Lock()` for thread safety (same pattern as `InMemoryTaskRepository`)
   - `model_copy(deep=True)` on fetch to prevent mutation of stored state
   - `model_copy(update={"id": artifact_id})` in store to set generated ID

3. Update `src/omniforge/storage/__init__.py`: add `ArtifactStore` and `InMemoryArtifactRepository` to `__all__` and the lazy `__getattr__` function.

## Acceptance Criteria

- `store()` generates UUID when `artifact.id is None`, uses existing ID otherwise (upsert)
- `fetch()` returns None for wrong tenant (tenant isolation)
- `delete()` raises `ValueError` for wrong tenant or missing ID
- Returned artifacts are deep copies (mutation does not affect stored state)
- Tests in `tests/storage/test_artifact_store.py` cover all store/fetch/delete/tenant-isolation cases
