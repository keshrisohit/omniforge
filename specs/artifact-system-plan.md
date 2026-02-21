# Technical Implementation Plan: Artifact System

**Created**: 2026-02-21
**Spec**: `specs/artifact-system-spec.md`
**Status**: Draft

---

## Executive Summary

This plan adds a first-class artifact storage layer to OmniForge so agents can produce, persist, and consume artifacts independently of task lifecycle. The change touches four areas: (1) model enrichment in `agents/models.py`, (2) a new `ArtifactStore` protocol in `storage/base.py`, (3) an `InMemoryArtifactRepository` in `storage/memory.py`, and (4) DI wiring in `agents/base.py`. No new API endpoints, no external storage backends, no changes to SSE event types or task states.

---

## 1. Model Changes (`src/omniforge/agents/models.py`)

### 1.1 ArtifactType Enum

Add after `SkillOutputMode`:

```python
class ArtifactType(str, Enum):
    """Closed set of artifact categories."""
    DOCUMENT = "document"
    DATASET = "dataset"
    CODE = "code"
    IMAGE = "image"
    STRUCTURED = "structured"
```

**Rationale**: Replaces the free-form `type: str` on `Artifact`. Keeps the set small and intentional. `str, Enum` so it serializes to its value string (consistent with `SkillInputMode`, `SkillOutputMode`, etc.).

### 1.2 Artifact Model Refactor

Replace the existing `Artifact` class. Key changes:

| Field | Before | After | Notes |
|---|---|---|---|
| `id` | `str` (required) | `Optional[str] = None` | `None` means store generates a UUID |
| `type` | `str` (free-form) | `ArtifactType` | Enum-typed |
| `title` | `str` (required) | `str` (required) | Unchanged |
| `content` | `Union[str, dict, list]` (required) | Removed | Renamed below |
| `inline_content` | -- | `Optional[Union[str, dict, list]]` | Renamed from `content` |
| `metadata` | `Optional[dict[...]]` | `Optional[dict[...]]` | Unchanged |
| `tenant_id` | -- | `str` (required) | For store-level tenant isolation |
| `storage_url` | -- | `Optional[str]` | External content location |
| `mime_type` | -- | `Optional[str]` | IANA media type |
| `size_bytes` | -- | `Optional[int]` (ge=0) | Content size hint |
| `schema_url` | -- | `Optional[str]` | JSON Schema URL for structured types |
| `created_by_agent_id` | -- | `Optional[str]` | Producing agent ID |
| `created_at` | -- | `Optional[datetime]` | Creation timestamp |

**Validation rule** (Pydantic `model_validator(mode="after")`):

```python
@model_validator(mode="after")
def validate_content_present(self) -> "Artifact":
    if self.inline_content is None and self.storage_url is None:
        raise ValueError("Artifact must have at least one of inline_content or storage_url")
    return self
```

**Breaking change (intentional)**: `content` → `inline_content`, `id` → `Optional[str] = None`, `tenant_id` required. All existing `Artifact(...)` construction sites must be updated. No backward compatibility shims.

**Import additions**: `model_validator` from pydantic, `datetime` from datetime.

### 1.3 ArtifactPart Model

Add after `DataPart`:

```python
class ArtifactPart(BaseModel):
    """Reference to a stored artifact, used as a message part.

    Attributes:
        type: Message part type identifier (always "artifact")
        artifact_id: ID of the stored artifact
        title: Optional human-readable hint
    """
    type: str = Field(default="artifact", frozen=True)
    artifact_id: str = Field(..., min_length=1, max_length=255)
    title: Optional[str] = None
```

Follows the exact same pattern as `TextPart`, `FilePart`, `DataPart`: frozen `type` field, required content field, optional metadata.

### 1.4 MessagePart Union Update

```python
# Before
MessagePart = Union[TextPart, FilePart, DataPart]

# After
MessagePart = Union[TextPart, FilePart, DataPart, ArtifactPart]
```

**Backward-compatible**: Existing code that constructs or pattern-matches on `TextPart | FilePart | DataPart` continues to work. `ArtifactPart` is additive. Pydantic discriminates via the `type` field value.

### 1.5 Impact on Downstream Models

These files import `Artifact` or `MessagePart` and will automatically pick up the changes without code modification (unless they construct `Artifact` instances):

- `src/omniforge/agents/events.py` -- `TaskArtifactEvent.artifact` field. Type is `Artifact`, so the enriched model flows through. No code change needed.
- `src/omniforge/tasks/models.py` -- `Task.artifacts: list[Artifact]` and `MessagePart` in `TaskMessage.parts`, `TaskCreateRequest.message_parts`, `TaskSendRequest.message_parts`. No code change needed; the union expansion is automatic.

**Sites that construct `Artifact` directly** need updating to provide `tenant_id` and rename `content` to `inline_content`. These must be found via grep and updated as part of implementation.

---

## 2. Artifact Store (`src/omniforge/storage/`)

### 2.1 Protocol (`src/omniforge/storage/base.py`)

Add `ArtifactStore` protocol alongside `TaskRepository` and `AgentRepository`:

```python
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from omniforge.agents.models import Artifact

class ArtifactStore(Protocol):
    """Protocol for artifact storage operations.

    All operations are tenant-scoped. Cross-tenant access returns None
    (indistinguishable from not-found).
    """

    async def store(self, artifact: "Artifact") -> str:
        """Persist an artifact. Returns its ID.

        If artifact.id is None, generates a UUID and returns it.
        If artifact.id is set, uses it (upsert within tenant).
        Uses artifact.tenant_id as the namespace.
        """
        ...

    async def fetch(self, artifact_id: str, tenant_id: str) -> "Optional[Artifact]":
        """Retrieve an artifact by ID within a tenant.

        Returns None if not found or if the artifact belongs to a different tenant.
        """
        ...

    async def delete(self, artifact_id: str, tenant_id: str) -> None:
        """Delete an artifact by ID within a tenant.

        Raises ValueError if not found within that tenant.
        """
        ...
```

**Design decisions**:
- Three methods only. No `list()` or `search()` in V1.
- `store()` takes the full `Artifact` (not separate fields) -- consistent with how `TaskRepository.save()` takes a `Task`.
- `fetch()` returns `Optional` rather than raising -- consistent with `TaskRepository.get()`.
- `delete()` raises `ValueError` on not-found -- consistent with `TaskRepository.delete()`.
- Tenant isolation is enforced at the store level: `fetch` and `delete` require `tenant_id` as a parameter and only look within that namespace.

**Import note**: `Artifact` is imported from `omniforge.agents.models`. The existing `base.py` already imports from `omniforge.tasks.models` which in turn imports from `omniforge.agents.models`, so no new circular dependency is introduced. However, to be safe and consistent with the existing `TYPE_CHECKING` pattern used for `BaseAgent`, use a direct import since `Artifact` is a Pydantic model (data, not logic) and does not create cycles.

### 2.2 InMemoryArtifactRepository (`src/omniforge/storage/memory.py`)

Add to the existing `memory.py` file alongside `InMemoryTaskRepository` and `InMemoryAgentRepository`:

```python
from uuid import uuid4
from omniforge.agents.models import Artifact

class InMemoryArtifactRepository:
    """Thread-safe in-memory implementation of ArtifactStore.

    Stores artifacts in a nested dict: {tenant_id: {artifact_id: Artifact}}.
    Returns deep copies on fetch to prevent mutation of stored state.
    """

    def __init__(self) -> None:
        self._artifacts: dict[str, dict[str, Artifact]] = {}
        self._lock = asyncio.Lock()

    async def store(self, artifact: Artifact) -> str:
        async with self._lock:
            artifact_id = artifact.id if artifact.id is not None else str(uuid4())
            tenant_id = artifact.tenant_id

            if tenant_id not in self._artifacts:
                self._artifacts[tenant_id] = {}

            # Update the artifact's id if it was generated
            stored = artifact.model_copy(update={"id": artifact_id})
            self._artifacts[tenant_id][artifact_id] = stored
            return artifact_id

    async def fetch(self, artifact_id: str, tenant_id: str) -> Optional[Artifact]:
        async with self._lock:
            tenant_store = self._artifacts.get(tenant_id)
            if tenant_store is None:
                return None
            artifact = tenant_store.get(artifact_id)
            if artifact is None:
                return None
            return artifact.model_copy(deep=True)

    async def delete(self, artifact_id: str, tenant_id: str) -> None:
        async with self._lock:
            tenant_store = self._artifacts.get(tenant_id)
            if tenant_store is None or artifact_id not in tenant_store:
                raise ValueError(
                    f"Artifact {artifact_id} not found for tenant {tenant_id}"
                )
            del tenant_store[artifact_id]
```

**Pattern alignment**:
- `__init__` with `_lock = asyncio.Lock()` -- same as `InMemoryTaskRepository`.
- `async with self._lock` in every method -- same pattern.
- `model_copy(deep=True)` on fetch -- prevents callers from mutating stored state. This is more robust than the existing `InMemoryTaskRepository` (which returns direct references) but is explicitly called out in the spec.
- `ValueError` on delete-not-found -- matches `InMemoryTaskRepository.delete()`.
- No `copy` module needed; Pydantic's `model_copy(deep=True)` handles it.

### 2.3 Storage `__init__.py` Update

Add `ArtifactStore` and `InMemoryArtifactRepository` to `__all__` and the lazy `__getattr__` function in `src/omniforge/storage/__init__.py`.

---

## 3. Base Agent Wiring (`src/omniforge/agents/base.py`)

### 3.1 Injection Approach

Add an optional `artifact_store` parameter to `BaseAgent.__init__()`:

```python
def __init__(
    self,
    agent_id: Optional[UUID] = None,
    tenant_id: Optional[str] = None,
    prompt_config: Optional[Any] = None,
    artifact_store: Optional[Any] = None,  # ArtifactStore protocol
) -> None:
    self._id: UUID = agent_id if agent_id is not None else uuid4()
    self.tenant_id: Optional[str] = tenant_id
    self.prompt_config: Optional[Any] = prompt_config
    self.artifact_store: Optional[Any] = artifact_store
```

**Why `Optional[Any]` instead of `Optional[ArtifactStore]`**: The existing codebase uses `Optional[Any]` for `prompt_config` with a comment "Type is Any to avoid circular import". Follow the same convention. The `ArtifactStore` protocol lives in `storage/base.py` which imports from `agents/models.py` -- importing `ArtifactStore` back into `agents/base.py` could create a circular dependency chain. Using `Any` keeps it simple and matches the established pattern.

**Alternative considered**: Using `TYPE_CHECKING` guard. The codebase already does this for `BaseAgent` in `storage/base.py`. However, `prompt_config` set the precedent of using `Any` directly, so follow that for consistency. If the team later wants to tighten types, both `prompt_config` and `artifact_store` can be updated together.

### 3.2 Usage in Agents

Agents that produce artifacts call:

```python
# In process_task():
artifact = Artifact(
    id=None,  # store generates UUID
    type=ArtifactType.CODE,
    title="generated_module.py",
    inline_content="def hello(): ...",
    tenant_id=task.tenant_id,
    mime_type="text/x-python",
)
artifact_id = await self.artifact_store.store(artifact)
# Patch artifact with the store-assigned ID before emitting the event
artifact = artifact.model_copy(update={"id": artifact_id})
yield TaskArtifactEvent(artifact=artifact)
```

Agents that consume artifacts:

```python
# When encountering ArtifactPart in task input:
for part in task.messages[-1].parts:
    if isinstance(part, ArtifactPart):
        artifact = await self.artifact_store.fetch(part.artifact_id, task.tenant_id)
```

No base class methods are added for this -- agents interact with `self.artifact_store` directly. This keeps `BaseAgent` thin.

---

## 4. Files Modified (Summary)

| File | Change |
|---|---|
| `src/omniforge/agents/models.py` | Add `ArtifactType` enum, refactor `Artifact`, add `ArtifactPart`, update `MessagePart` union |
| `src/omniforge/storage/base.py` | Add `ArtifactStore` protocol |
| `src/omniforge/storage/memory.py` | Add `InMemoryArtifactRepository` class |
| `src/omniforge/storage/__init__.py` | Add lazy imports for `ArtifactStore`, `InMemoryArtifactRepository` |
| `src/omniforge/agents/base.py` | Add `artifact_store` parameter to `__init__` |
| `src/omniforge/agents/streaming.py` | Update `Artifact(content=...)` → `Artifact(inline_content=..., tenant_id=..., id=None)` |
| Test files (multiple) | Update all `Artifact(...)` construction calls to new field names |

**Files NOT modified**: `events.py`, `tasks/models.py`, any API/HTTP layer.

---

## 5. Test Plan

### 5.1 Model Tests (`tests/agents/test_models.py`)

**ArtifactType**:
- Verify all five enum values serialize to their string values.

**Artifact refactored model**:
- Construction with `id=None` (valid -- store generates UUID).
- Construction with `inline_content` only (valid).
- Construction with `storage_url` only (valid).
- Construction with both `inline_content` and `storage_url` (valid).
- Construction with neither `inline_content` nor `storage_url` (raises `ValidationError`).
- `tenant_id` is required -- omitting raises `ValidationError`.
- `type` field accepts `ArtifactType` enum values, rejects arbitrary strings.
- Optional fields (`mime_type`, `size_bytes`, `schema_url`, `created_by_agent_id`, `created_at`) default to `None`.
- `size_bytes` with negative value raises `ValidationError` (if `ge=0` constraint is added).
- Serialization round-trip (`model_dump()` / `model_validate()`).

**ArtifactPart**:
- Construction with `artifact_id` only (valid, `title` defaults to `None`).
- `type` field is frozen at `"artifact"`.
- `artifact_id` is required, empty string rejected (`min_length=1`).

**MessagePart union**:
- Pydantic discriminates `ArtifactPart` from `TextPart`/`FilePart`/`DataPart` correctly when deserializing from dict with `type: "artifact"`.
- Existing `TextPart`/`FilePart`/`DataPart` deserialization still works (backward compat).

### 5.2 Store Tests (`tests/storage/test_artifact_store.py`)

**InMemoryArtifactRepository**:

`store()`:
- Stores artifact and returns a non-empty ID.
- If `artifact.id` is empty, generates a UUID.
- If `artifact.id` is set, uses that ID (idempotent upsert).
- Upsert overwrites existing artifact with same ID and tenant.

`fetch()`:
- Fetches stored artifact by ID and tenant.
- Returns `None` for non-existent ID.
- Returns `None` for valid ID but wrong tenant (tenant isolation).
- Returns a deep copy (mutating returned artifact does not affect stored state).

`delete()`:
- Deletes existing artifact.
- Raises `ValueError` for non-existent ID.
- Raises `ValueError` for valid ID but wrong tenant.
- After delete, `fetch()` returns `None`.

**Tenant isolation (cross-cutting)**:
- Store artifact under tenant A, fetch under tenant B returns `None`.
- Store artifact under tenant A, delete under tenant B raises `ValueError`.
- Two tenants can store artifacts with the same ID without collision.

### 5.3 Base Agent Tests (`tests/agents/test_base.py`)

- `BaseAgent.__init__` accepts `artifact_store` parameter.
- `artifact_store` defaults to `None` when not provided.
- `artifact_store` is accessible as `self.artifact_store` on agent instance.
- Existing tests continue to pass (no regression from new optional parameter).

---

## 6. Implementation Order

1. **Models** (`agents/models.py`) -- `ArtifactType`, `Artifact` refactor, `ArtifactPart`, `MessagePart` union. Run model tests.
2. **Protocol** (`storage/base.py`) -- `ArtifactStore`. No tests needed for a Protocol definition.
3. **InMemory implementation** (`storage/memory.py`) -- `InMemoryArtifactRepository`. Run store tests.
4. **Storage init** (`storage/__init__.py`) -- Lazy imports.
5. **Base agent wiring** (`agents/base.py`) -- `artifact_store` param. Run base agent tests.
6. **Fix existing Artifact construction sites** -- Named targets: `src/omniforge/agents/streaming.py` (production), plus all test files that construct `Artifact(...)`. Update `content` → `inline_content`, `id=...` → `id=None` where appropriate, add `tenant_id`. Run full test suite.

---

## 7. Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Renaming `content` to `inline_content` breaks existing code | Medium -- any code constructing `Artifact` will fail | Step 6 explicitly greps and fixes all sites. Model tests catch serialization issues. |
| `tenant_id` required on `Artifact` but `Task.tenant_id` is `Optional[str]` | Low -- intentional fail-fast. Agents without a tenant context cannot produce artifacts | Document that artifact-producing agents must run within a tenant context. Pydantic raises `ValidationError` at construction — not a silent failure. |
| `MessagePart` union expansion breaks Pydantic discrimination | Low -- Pydantic uses `type` field value for discrimination | Each `*Part` has a unique frozen `type` value (`"text"`, `"file"`, `"data"`, `"artifact"`). Test confirms discrimination. |
| `InMemoryArtifactRepository` returns deep copies but existing `InMemoryTaskRepository` does not | Inconsistency -- but spec explicitly requires copies for artifacts | Document the difference. Consider aligning `InMemoryTaskRepository` in a separate PR. |
