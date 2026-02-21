# OmniForge Artifact System (Artifact Store as First-Class Service)

**Created**: 2026-02-21
**Last Updated**: 2026-02-21
**Version**: 1.0
**Status**: Draft

## Overview

The Artifact System promotes artifacts from ephemeral, task-scoped blobs into first-class, persistent, addressable entities with a dedicated store. Today an artifact lives and dies with its parent Task -- Agent A cannot produce an artifact that Agent B later consumes unless they share the same task context. The Artifact Store removes that coupling: any agent can store an artifact, any agent can fetch it by ID, and artifacts carry enough metadata (type, MIME type, schema) to be self-describing. This enables multi-agent pipelines where each agent works independently and communicates through well-typed data artifacts rather than through shared task state.

## Alignment with Product Vision

This spec directly advances three pillars of the OmniForge vision:

1. **Agents build agents** -- Artifact sharing is the foundation for multi-agent pipelines. A research agent produces a dataset artifact; a code-gen agent consumes it to produce a code artifact; a review agent consumes that. No human wiring needed.
2. **Reliable orchestration at scale** -- Persistent, addressable artifacts mean pipelines can resume, retry, and audit. If an agent fails, its previously stored artifacts survive.
3. **Open Source SDK parity** -- SDK users get the same `ArtifactStore` protocol. They can use `InMemoryArtifactRepository` locally or plug in S3/GCS when deploying.

## User Personas

### Primary Users

- **SDK Developer (Agent Author)**: Writes Python agent classes. Needs a simple API to store outputs and fetch inputs. Does not want to manage storage plumbing -- just `store()` and `fetch()`.
- **Orchestration Developer**: Builds multi-agent pipelines. Needs to wire Agent A's output artifact as Agent B's input. Cares about artifact IDs being stable, addressable, and type-safe.

### Secondary Users

- **Platform Operator**: Manages deployed agents. Needs to understand artifact storage usage and eventually swap in durable backends (S3, GCS). Not the primary concern for V1 but the protocol must not block this.

## Problem Statement

**Today**: An artifact is a field on a Task object (`Task.artifacts: list[Artifact]`). It has no storage URL, no MIME type, no size tracking, and no way to reference it from another task. If Agent A produces a report and Agent B needs that report, the orchestrator must manually extract the artifact content from Agent A's completed task and embed it as a `DataPart` or `TextPart` in Agent B's task input. This is fragile, loses type information, and breaks down for large artifacts (images, datasets).

**After this change**: Agent A calls `artifact_store.store(artifact)` and gets back an ID. Agent B receives an `ArtifactPart(artifact_id="...")` in its task input, calls `artifact_store.fetch(artifact_id)`, and gets the full typed artifact. The orchestrator only passes IDs, not content. Large artifacts stay external (via `storage_url`); small ones can remain inline. Type information (`ArtifactType`, `mime_type`, `schema_url`) travels with the artifact.

## What Changes vs What Stays the Same

### Stays the Same (no modifications)
- **A2A SSE event types**: `status`, `message`, `artifact`, `done`, `error` -- same event type strings
- **TaskArtifactEvent**: Still delivers artifacts via SSE. The artifact it carries now has richer fields, but the event shape is unchanged
- **Task lifecycle and TaskState**: No new states, no transition changes
- **Task.artifacts field**: Still exists. Agents can still attach artifacts to tasks. The difference is those artifacts are now also persisted in the store
- **Existing MessagePart types**: `TextPart`, `FilePart`, `DataPart` are unchanged

### Changes

1. **`ArtifactType` enum** replaces the free-form `type: str` field on `Artifact`
2. **`Artifact` model** gains `tenant_id` (required), `storage_url`, `mime_type`, `size_bytes`, `schema_url`; `content` becomes `inline_content` and is optional
3. **`ArtifactPart`** added to `MessagePart` union -- a new way to reference stored artifacts in messages
4. **`ArtifactStore` protocol** and `InMemoryArtifactRepository` -- new storage layer
5. **`SkillOutputMode.ARTIFACT`** already exists in the codebase; no change needed there

## Key Concepts

### 1. ArtifactType Enum

A closed set of artifact categories. Agents declare what kind of thing they produced, consumers use it to decide how to handle it.

| Value | When to Use |
|---|---|
| `document` | Text documents, reports, markdown, HTML |
| `dataset` | Tabular data, JSON arrays, CSV-like structured data |
| `code` | Source code, scripts, configuration files |
| `image` | Images (PNG, JPEG, SVG, etc.) |
| `structured` | Arbitrary structured data (JSON objects, YAML) that does not fit the above |

### 2. Artifact Model Refactor

Current `Artifact` fields and their evolution:

| Field | Current | After |
|---|---|---|
| `id` | `str` (required) | Unchanged |
| `type` | `str` (free-form) | `ArtifactType` enum |
| `title` | `str` (required) | Unchanged |
| `content` | `Union[str, dict, list]` (required) | Renamed to `inline_content`, becomes `Optional`. Present for small artifacts. Absent when content is at `storage_url` |
| `metadata` | `Optional[dict]` | Unchanged |
| `storage_url` | -- | `Optional[str]`. URL/path where large content is stored. Mutually informative with `inline_content` (at least one should be present) |
| `mime_type` | -- | `Optional[str]`. IANA media type (e.g., `application/json`, `image/png`) |
| `size_bytes` | -- | `Optional[int]`. Content size. Useful for transfer decisions |
| `schema_url` | -- | `Optional[str]`. URL to JSON Schema describing the artifact's structure (for `dataset` and `structured` types) |
| `created_by_agent_id` | -- | `Optional[str]`. ID of the agent that produced this artifact |
| `created_at` | -- | `Optional[datetime]`. When the artifact was created |
| `tenant_id` | -- | `str` (required). Tenant that owns this artifact. Enforced by the store — cross-tenant fetches return `None` |

**Validation rule**: An artifact must have at least one of `inline_content` or `storage_url`. An artifact with neither is invalid.

### 3. ArtifactPart (New MessagePart Type)

A lightweight reference that lets agents pass artifacts as task inputs without embedding content.

```
ArtifactPart:
  type: "artifact"  (frozen, like other *Part types)
  artifact_id: str   (required -- references a stored artifact)
  title: Optional[str]  (human-readable hint, not authoritative)
```

**Usage**: When an orchestrator chains agents, it sends `ArtifactPart(artifact_id="abc-123")` as a message part in the downstream task's input. The downstream agent calls `artifact_store.fetch("abc-123")` to get the full artifact.

**MessagePart union becomes**: `Union[TextPart, FilePart, DataPart, ArtifactPart]`

This is a backward-compatible addition. Existing code that handles `TextPart | FilePart | DataPart` will not break; it simply will not handle `ArtifactPart` until updated. Agents that do not understand `ArtifactPart` can skip it (same as they would skip any unrecognized part type).

### 4. ArtifactStore Protocol

Follows the same `Protocol` pattern used by `TaskRepository` and `AgentRepository` in `storage/base.py`. Three operations — all tenant-scoped:

```
ArtifactStore (Protocol):
  async store(artifact: Artifact) -> str
    # Persists the artifact under artifact.tenant_id namespace, returns its ID
    # If artifact.id is already set, uses it (idempotent upsert within tenant)
    # If artifact.id is not set, generates a UUID

  async fetch(artifact_id: str, tenant_id: str) -> Optional[Artifact]
    # Returns the artifact only if it belongs to tenant_id
    # Returns None for not found OR cross-tenant access (no information leakage)

  async delete(artifact_id: str, tenant_id: str) -> None
    # Removes the artifact if it belongs to tenant_id
    # Raises ValueError if not found within that tenant
```

Tenant isolation is enforced at the store level, not at the caller level. An agent with a valid artifact ID but a different `tenant_id` gets `None` from `fetch()` — indistinguishable from "not found".

No `list` or `search` operations in V1. Keep it minimal.

### 5. InMemoryArtifactRepository

Dev/test implementation. Nested-dictionary-backed, asyncio-lock-protected.

- Stores artifacts in `dict[str, dict[str, Artifact]]` — outer key is `tenant_id`, inner key is `artifact_id`
- `store()` generates a UUID if `artifact.id` is empty; uses `artifact.tenant_id` as the namespace
- `fetch(artifact_id, tenant_id)` looks up only within the given tenant's namespace
- `delete(artifact_id, tenant_id)` raises `ValueError` if not found within that tenant
- `fetch()` returns a copy (not a reference) to prevent mutation
- Thread-safe via `asyncio.Lock`

## User Journeys

### Journey 1: Agent Producing an Artifact

A code-generation agent finishes generating a Python module and wants to make it available for other agents.

1. Agent completes its work, has the generated code as a string
2. Agent creates an `Artifact` with `artifact_type=ArtifactType.CODE`, `mime_type="text/x-python"`, `inline_content="def hello(): ..."`, `title="generated_module.py"`, `tenant_id=task.tenant_id`
3. Agent calls `self.artifact_store.store(artifact)` -- gets back the artifact ID
4. Agent yields `TaskArtifactEvent(artifact=artifact)` so the SSE stream delivers the artifact to the caller
5. Agent yields `TaskDoneEvent` with `COMPLETED` state
6. The artifact now lives in the store, addressable by ID, independent of the task's lifecycle

### Journey 2: Agent Consuming an Artifact

A code-review agent receives a task whose input includes an artifact reference.

1. Orchestrator creates a task for the review agent with `message_parts=[ArtifactPart(artifact_id="abc-123"), TextPart(text="Review this code for security issues")]`
2. Review agent's `process_task()` iterates over `task.messages[-1].parts`
3. Agent encounters an `ArtifactPart`, extracts the `artifact_id`
4. Agent calls `self.artifact_store.fetch("abc-123", tenant_id=task.tenant_id)` -- gets the full `Artifact` if it belongs to the same tenant
5. Agent reads `artifact.inline_content` (the Python code), performs its review
6. Agent yields its review as a `TaskMessageEvent` with `TextPart` containing the review text
7. Agent yields `TaskDoneEvent` with `COMPLETED` state

### Journey 3: Chaining Agents via Artifacts (Pipeline)

An orchestrator runs a three-agent pipeline: Research -> Draft -> Review.

1. Orchestrator creates a task for the Research agent: `"Find information about X"`
2. Research agent stores its findings as an artifact (`ArtifactType.DOCUMENT`, `mime_type="text/markdown"`), yields `TaskArtifactEvent`, completes
3. Orchestrator reads the `TaskArtifactEvent` from the SSE stream, extracts the artifact ID
4. Orchestrator creates a task for the Draft agent: `[ArtifactPart(artifact_id=research_artifact_id), TextPart(text="Write a report based on this research")]`
5. Draft agent fetches the research artifact, writes a report, stores it as a new artifact, yields `TaskArtifactEvent`, completes
6. Orchestrator creates a task for the Review agent: `[ArtifactPart(artifact_id=draft_artifact_id), TextPart(text="Review and improve this report")]`
7. Review agent fetches the draft, reviews it, produces a final artifact, completes
8. At every step, artifacts are independently stored. If the Review agent fails, the Research and Draft artifacts are still available for retry

## Success Criteria

### User Outcomes
- An artifact produced by any agent is fetchable by any other agent using only its ID -- no shared task context required
- Artifact type, MIME type, and schema URL provide enough metadata for a consuming agent to decide how to process the artifact without inspecting content
- Small artifacts (under a few KB) can stay inline for simplicity; the system does not force external storage
- Existing agents that do not use the artifact store continue to work unchanged

### Technical Outcomes
- `ArtifactStore` protocol is backend-agnostic -- swapping `InMemoryArtifactRepository` for an S3-backed implementation requires zero changes to agent code
- `ArtifactPart` added to `MessagePart` union without breaking existing `TextPart`/`FilePart`/`DataPart` handling
- All A2A SSE event types and task lifecycle states remain unchanged
- Tenant isolation is enforced at the store level — no agent can read another tenant's artifacts, even with a valid artifact ID

## Key Experiences

- **Store-and-forget for producers**: An agent calls `store()` and moves on. It does not need to know who will consume the artifact or when.
- **Fetch-by-ID for consumers**: An agent receives an artifact ID, calls `fetch()`, and gets a fully typed, self-describing object. No guessing about content format.
- **Seamless inline fallback**: For small artifacts, `inline_content` is populated and the agent never touches a URL. The artifact store is invisible for simple cases.

## Edge Cases and Considerations

- **Artifact not found**: `fetch()` returns `None`. Consuming agent must handle this gracefully (the producing agent's task may have been cleaned up, or the ID is invalid). Agent should yield a `TaskErrorEvent` with a clear message.
- **Both `inline_content` and `storage_url` present**: Valid. `inline_content` serves as a cache/preview; `storage_url` is the canonical source. Consumer should prefer `inline_content` if present and size is reasonable.
- **Neither `inline_content` nor `storage_url` present**: Invalid. Pydantic model validator should reject this at construction time.
- **Large inline content**: The `InMemoryArtifactRepository` has no size limit in V1. A future S3 backend would enforce a threshold (e.g., inline up to 256KB, external above that). For now, trust the agent author.
- **Duplicate artifact IDs**: `store()` with an existing ID performs an upsert (overwrites). This is intentional -- agents may update artifacts iteratively.
- **Concurrent access**: `InMemoryArtifactRepository` uses `asyncio.Lock` for safety, same as other in-memory repositories in the codebase.
- **Tenant isolation**: Enforced at the store level. `fetch()` and `delete()` take `tenant_id` as a required parameter. A valid artifact ID from a different tenant returns `None` (same as not found — no information leakage about artifact existence across tenants).

## Open Questions

- **Artifact TTL / cleanup**: Should artifacts expire? In V1, they persist until explicitly deleted. Automatic expiration is out of scope but should be considered for the durable backend.
- **Artifact versioning**: Should agents be able to update an artifact and keep history? Deferred. V1 is simple overwrite via upsert.
- **Intra-tenant access control**: Should agents need permission to fetch an artifact they did not create (within the same tenant)? Deferred to RBAC/security layer. V1: any agent in the same tenant can read any artifact in that tenant.
- **Size threshold for inline vs external**: When a durable backend is added, what is the cutoff for keeping content inline vs storing externally? This is a backend implementation decision, not a protocol decision.

## Out of Scope (For Now)

- **S3/GCS/durable storage backend** -- Only `InMemoryArtifactRepository` is needed now
- **New API endpoints for artifacts** -- Artifact storage is internal to agents, not exposed via REST yet
- **Artifact search/discovery** -- No `list()` or `search()` on the store in V1
- **Artifact versioning** -- No history, just latest state
- **Intra-tenant RBAC** -- Agent-level permissions within a tenant are deferred
- **Artifact streaming** -- Large artifact content is not streamed chunk-by-chunk; it is fetched whole

## Evolution Notes

### 2026-02-21
Initial specification. Based on analysis of existing codebase: `Artifact` model in `agents/models.py`, `MessagePart` union (`TextPart | FilePart | DataPart`), `TaskArtifactEvent` in `events.py`, Protocol-based repository pattern in `storage/base.py`, and `InMemory*` implementations in `storage/memory.py`. Notable: `SkillOutputMode.ARTIFACT` already exists, and `HandoffReturn.artifacts_created` already tracks artifact IDs by string -- both signs the codebase was designed with this extension in mind.
