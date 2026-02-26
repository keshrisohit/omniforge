# Phase 2 — TaskGraph + Shared Context + Trace IDs

**Status:** Design / pre-implementation
**Depends on:** Phase 1 (done)
**Solves scenarios:** 1–4, 6, 8, 10–11, 13, 15, 17–18, 21–24, 26

---

## What Phase 2 Adds

Three independent but complementary pieces:

| Piece | What it enables |
|---|---|
| **Trace IDs** | Know which agent called which, at every hop, with timing |
| **Shared context store** | Agents share a key-value workspace without passing everything through messages |
| **TaskGraph executor** | Sequential + parallel multi-agent pipelines with error handling |

These three pieces are ordered that way intentionally — trace IDs and context store
are small changes to existing models; TaskGraph is the largest piece and uses both.

---

## Piece 1 — Trace IDs

### Problem
Today, `Task` has `parent_task_id` to link subtasks to their parent, but there is no
single ID that spans the whole chain (root → A → B → C). You can't answer:
"Show me every event from this user request across all agents."

### Solution
Add `trace_id: Optional[str]` to three places:
1. `Task` model
2. `ToolCallContext`
3. `BaseTaskEvent` (inherited by all event types)

The root task sets `trace_id = task.id` (or a new UUID). Every subtask and every
`ToolCallContext` inherits the same value. Every event emitted anywhere in the chain
carries it.

### Files to change

**`src/omniforge/tasks/models.py`**
- Add `trace_id: Optional[str] = None` to the `Task` class
- No validator changes needed — it's metadata only

**`src/omniforge/tools/base.py`**
- Add `trace_id: Optional[str] = None` to `ToolCallContext`

**`src/omniforge/agents/events.py`**
- Add `trace_id: Optional[str] = None` to `BaseTaskEvent`
  (all concrete events — `TaskStatusEvent`, `TaskMessageEvent`, etc. — inherit it for free)

**`src/omniforge/tools/builtin/subagent.py` — `SubAgentTool.execute()`**
- When building the subtask `Task`, copy `trace_id` from `context.trace_id`
  (fall back to `context.task_id` if none set — this is the root case)

**`src/omniforge/agents/master_agent.py` — `process_task()`**
- On the root task entry (when `task.trace_id is None`), set `task.trace_id = task.id`
- Pass it into `ToolCallContext` when building tool calls

### No breaking changes
All fields are `Optional` with `None` default. Existing tests pass unchanged.

---

## Piece 2 — Shared Agent Context Store

### Problem
Today, if AgentA produces structured output that AgentB needs to read, the only path
is to embed it in the task description string. This is lossy and token-expensive for
large payloads (e.g. a research document, parsed JSON).

### Solution
An in-memory key-value store scoped by `trace_id`. Agents can read and write named
slots. It's not a database — it's working memory for the duration of one request chain.

```
AgentA writes:  context_store.set(trace_id, "research_output", {...})
AgentB reads:   context_store.get(trace_id, "research_output")
```

Two new tools exposed to agents:
- `write_context` — store a JSON-serialisable value under a key
- `read_context` — retrieve a value by key

### New file: `src/omniforge/orchestration/context_store.py`

```python
class AgentContextStore:
    """In-memory context store scoped by trace_id."""

    def set(self, trace_id: str, key: str, value: Any) -> None: ...
    def get(self, trace_id: str, key: str) -> Optional[Any]: ...
    def list_keys(self, trace_id: str) -> list[str]: ...
    def clear(self, trace_id: str) -> None: ...  # called when chain completes
```

Singleton pattern (like `ToolRegistry` / `_default_registry`) — one instance per process.

### New file: `src/omniforge/tools/builtin/context.py`

Two tool classes:
- `WriteContextTool` — writes a key/value to the store for the current trace
- `ReadContextTool` — reads a key from the store for the current trace

Both receive `trace_id` from `ToolCallContext.trace_id`.

### Files to change

**`src/omniforge/tools/builtin/platform.py`** (or wherever tools are registered)
- Register `WriteContextTool` and `ReadContextTool` when setting up master agent tools

**`src/omniforge/agents/master_agent.py`**
- Pass the context store instance into agent init so it's shared across delegation hops
  (or use the global singleton pattern — simpler)

### Tradeoffs
- In-memory only in Phase 2 — not durable across restarts (Phase 3 adds persistence)
- Scoped by `trace_id` — two concurrent requests never bleed into each other
- Max entry size should be bounded (e.g. 1MB) to prevent memory abuse
- The store must be cleared when the root task completes to prevent leaks

---

## Piece 3 — TaskGraph Executor

### Problem
Today, multi-agent work is limited to one master calling one sub-agent at a time via
`SubAgentTool`. There is no:
- Sequential pipeline (step 1 must complete before step 2 starts)
- Parallel fan-out (steps 1, 2, 3 run concurrently, all must finish before step 4)
- Conditional branching (run step B only if step A's result meets a condition)
- Partial success handling (7 of 10 agents succeed — what do we do?)

### Solution
A `TaskGraph` data structure + `TaskGraphExecutor` that runs it. The LLM (master agent
ReAct loop) constructs the graph description and calls a new tool `run_pipeline`.

### New file: `src/omniforge/orchestration/task_graph.py`

Core data model:

```python
class StepMode(str, Enum):
    SEQUENTIAL = "sequential"   # steps run one after another
    PARALLEL = "parallel"       # steps run concurrently

class PipelineStep:
    agent_id: str
    task_description: str
    input_from: list[str]       # keys from context store to pass as input
    output_to: Optional[str]    # key to write result to in context store
    required: bool = True       # if False, failure doesn't stop the pipeline

class TaskGraph:
    steps: list[PipelineStep]
    mode: StepMode              # top-level mode; can nest groups later
    on_partial_success: Literal["fail", "continue", "best_effort"] = "fail"

class TaskGraphResult:
    succeeded: list[str]        # agent_ids that completed
    failed: list[str]           # agent_ids that failed
    outputs: dict[str, Any]     # context store values at completion
    trace_id: str
```

`TaskGraphExecutor` runs the graph:
- Sequential: runs steps in order, passes trace_id and shared context store through
- Parallel: uses `asyncio.gather` with `return_exceptions=True`, collects results
- Propagates trace_id and cancellation to all subtasks
- Handles partial failure per `on_partial_success` policy
- Calls `context_store.clear(trace_id)` on completion

### New file: `src/omniforge/tools/builtin/pipeline.py`

`RunPipelineTool` — wraps `TaskGraphExecutor` as a tool the ReAct loop can call.

LLM provides:
```json
{
  "mode": "sequential",
  "steps": [
    {"agent_id": "research-agent", "task_description": "...", "output_to": "research"},
    {"agent_id": "writer-agent",   "task_description": "...", "input_from": ["research"]}
  ]
}
```

Tool validates the input, builds a `TaskGraph`, runs the executor, returns results.

### How this fits in the ReAct loop

Master agent's ReAct prompt gets a new tool: `run_pipeline`.
The LLM decides when to use it vs. the existing `delegate_to_agent` (single agent, conversational)
or `SubAgentTool` (single agent, one-shot).

Decision guidance in master prompt:
- Single conversational handoff → `delegate_to_agent`
- Single one-shot task → `delegate_to_agent` or direct `SubAgentTool`
- Multi-step or parallel work → `run_pipeline`

### Files to change

**`src/omniforge/tools/builtin/platform.py`**
- Register `RunPipelineTool` alongside existing platform tools

**`src/omniforge/agents/master_agent.py` — `_SYSTEM_PROMPT`**
- Add `run_pipeline` to the capabilities list with description
- Add decision rule: when to use `run_pipeline` vs. `delegate_to_agent`

**`src/omniforge/agents/master_agent.py` — `__init__()`**
- Pass context store reference to tools that need it (if not using singleton)

---

## HITL Propagation Through Chains (Piece 3 concern)

When a step inside a `TaskGraph` emits `INPUT_REQUIRED`, the executor must:
1. Pause that step
2. Surface the question to the top-level caller (as `INPUT_REQUIRED`)
3. Resume the step with the user's answer when it arrives

This is **not in scope for the first iteration of Piece 3**. First iteration treats
`INPUT_REQUIRED` from a pipeline step as a step failure (conservative, safe). Full
HITL propagation through pipelines is a separate workstream.

---

## Cancellation Through Chains

When the root task is cancelled, `TaskGraphExecutor` must cancel all running subtasks.

Implementation: `asyncio.Task` handles for parallel steps are stored in the executor.
On cancellation, the executor calls `task.cancel()` on each handle and awaits cleanup.

Sequential steps: cancellation is checked between each step before starting the next.

---

## Streaming Through Chains

The `RunPipelineTool` collects events as they arrive and writes progress to the
context store. The master agent's `TaskMessageEvent` stream shows step-by-step progress.

For deep streaming (user sees AgentB's output in real time), the pipeline executor
yields `TaskMessageEvent` objects from subtasks upward — the same re-mapping pattern
already used in `MasterAgent.process_task()`.

---

## File Change Summary

| File | Change type | Why |
|---|---|---|
| `src/omniforge/tasks/models.py` | Modify | Add `trace_id` field to `Task` |
| `src/omniforge/tools/base.py` | Modify | Add `trace_id` to `ToolCallContext` |
| `src/omniforge/agents/events.py` | Modify | Add `trace_id` to `BaseTaskEvent` |
| `src/omniforge/tools/builtin/subagent.py` | Modify | Propagate `trace_id` to subtask |
| `src/omniforge/agents/master_agent.py` | Modify | Set root `trace_id`, add `run_pipeline` to prompt |
| `src/omniforge/orchestration/context_store.py` | **New** | In-memory shared context store |
| `src/omniforge/tools/builtin/context.py` | **New** | `ReadContextTool`, `WriteContextTool` |
| `src/omniforge/orchestration/task_graph.py` | **New** | `TaskGraph`, `PipelineStep`, `TaskGraphExecutor` |
| `src/omniforge/tools/builtin/pipeline.py` | **New** | `RunPipelineTool` wrapping the executor |
| `src/omniforge/tools/builtin/platform.py` | Modify | Register new tools |
| `tests/orchestration/test_context_store.py` | **New** | Unit tests for context store |
| `tests/orchestration/test_task_graph.py` | **New** | Unit tests for graph executor |
| `tests/tools/test_pipeline_tool.py` | **New** | Integration tests for run_pipeline tool |

**Total:** 5 files modified, 6 files new

---

## Implementation Order

1. **Trace IDs** — small, low-risk, unblocks everything else
2. **Context store** — independent of trace IDs but uses them for scoping
3. **TaskGraph executor** — depends on trace IDs and context store
4. **RunPipelineTool + prompt update** — wires executor into the ReAct loop

Each step is independently testable and deployable.

---

## What Phase 2 Does NOT Cover

- Durable state (if process restarts mid-pipeline, state is lost) → Phase 3
- Remote agents (HTTP adapter for A2A calls to external agents) → Phase 3
- Full HITL propagation through pipeline steps → separate workstream
- Per-agent cost quotas and rate limiting → Phase 3
- Audit trail / chain replay → Phase 3
