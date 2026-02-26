# InProcessBackend Technical Plan

**Date**: 2026-02-26
**Status**: Ready to implement
**Goal**: Introduce an `ExecutionBackend` abstraction that defaults to in-process execution,
making Temporal an optional future drop-in. Zero behavioral change today.

---

## The Abstraction Layer

```
Agent code (CoTAgent / MasterAgent)
        │
        ▼
ExecutionBackend (abstract protocol)        ← new
        │
  ┌─────┴──────┐
  │            │
InProcessBackend    TemporalBackend  (future, optional)
(default, zero deps)   (pip install omniforge[temporal])
```

The key insight: **agents already go through two narrow chokepoints**.
Wrap those two points, everything else is untouched.

**Chokepoint 1**: `ToolExecutor.execute()` — every tool call flows here
**Chokepoint 2**: `ToolExecutor._execute_with_retries()` — actual I/O happens here

---

## New Files

### `src/omniforge/execution/__init__.py`
```python
from .backend import ExecutionBackend
from .inprocess import InProcessBackend

__all__ = ["ExecutionBackend", "InProcessBackend"]
```

### `src/omniforge/execution/backend.py`
```python
from abc import ABC, abstractmethod
from typing import Any, Callable, Awaitable

class ExecutionBackend(ABC):
    """Abstract execution backend. Swap for Temporal without touching agent code."""

    @abstractmethod
    async def run_activity(
        self,
        fn: Callable[..., Awaitable[Any]],
        *args: Any,
        activity_name: str = "",
        timeout_ms: int = 30_000,
        max_retries: int = 3,
        **kwargs: Any,
    ) -> Any:
        """Run a single unit of work (tool call, LLM call).

        InProcessBackend: just calls fn(*args, **kwargs).
        TemporalBackend: wraps as workflow.execute_activity().
        """
        ...

    @abstractmethod
    async def run_child_agent(
        self,
        agent_fn: Callable[..., Awaitable[str]],
        *args: Any,
        child_id: str = "",
    ) -> str:
        """Run a sub-agent as a child execution unit.

        InProcessBackend: just calls agent_fn(*args).
        TemporalBackend: wraps as workflow.execute_child_workflow().
        """
        ...
```

### `src/omniforge/execution/inprocess.py`
```python
from typing import Any, Callable, Awaitable
from .backend import ExecutionBackend

class InProcessBackend(ExecutionBackend):
    """Default backend: runs everything in-process with asyncio.

    Zero new dependencies. Identical behavior to today.
    """

    async def run_activity(self, fn, *args, activity_name="", timeout_ms=30_000,
                           max_retries=3, **kwargs) -> Any:
        return await fn(*args, **kwargs)

    async def run_child_agent(self, agent_fn, *args, child_id="") -> str:
        return await agent_fn(*args)
```

---

## Changes Required

### 1. `ToolExecutor` — inject backend, route `_execute_with_retries` through it

**File**: `src/omniforge/tools/executor.py`

Current:
```python
def __init__(self, registry, rate_limiter=None, cost_tracker=None):
    ...
```

After:
```python
def __init__(self, registry, rate_limiter=None, cost_tracker=None, backend=None):
    from omniforge.execution import InProcessBackend
    self._backend = backend or InProcessBackend()
    ...
```

The `_execute_with_retries` method routes through the backend:
```python
async def _execute_with_retries(self, tool, arguments, context):
    async def _do_execute():
        # existing retry logic stays here, exactly as-is
        ...

    return await self._backend.run_activity(
        _do_execute,
        activity_name=tool.definition.name,
        timeout_ms=tool.definition.timeout_ms,
        max_retries=tool.definition.retry_config.max_retries,
    )
```

**Important**: The retry logic stays inside `_do_execute` for InProcessBackend.
For TemporalBackend, Temporal owns the retry — so the inner retry loop becomes a no-op.

### 2. `CoTAgent` — accept and thread backend through to executor

**File**: `src/omniforge/agents/cot/agent.py`

```python
def __init__(self, ..., backend=None):
    from omniforge.execution import InProcessBackend
    self._backend = backend or InProcessBackend()
    self._executor = ToolExecutor(
        registry=self._tool_registry,
        rate_limiter=rate_limiter,
        cost_tracker=cost_tracker,
        backend=self._backend,        # ← thread through
    )
```

### 3. No other agent files need to change

`ReasoningEngine` calls `self._executor.execute()` — unchanged.
`MasterAgent` inherits from `CoTAgent` — unchanged.
`SubAgentTool` creates its own agent instance — unchanged for now.

---

## What Could Break

### High Risk

| Risk | Why | Mitigation |
|---|---|---|
| `_execute_with_retries` refactor | It's a tight loop with timing, backoff math, and error detection. Extracting `_do_execute` closure must not change execution order | Keep all retry logic inside closure; only outermost call goes through backend |
| Closure captures mutable state | The closure captures `arguments` (mutated on rate limit retry) and `retries_used` | Use `nonlocal` properly; test mutable capture explicitly |
| `execute_with_events` not updated | There's a second execution path (`execute_with_events`) that duplicates most of `execute`. Must be updated too or will diverge | Update both in same PR |
| `ToolExecutor._skill_stack` is stateful | If backend ever serializes/deserializes the executor, skill stack is lost | Document: backend must not serialize executor; skill state stays in-process always |

### Medium Risk

| Risk | Why | Mitigation |
|---|---|---|
| Default `InProcessBackend` instantiated per-executor | If `ToolExecutor` is created frequently, creates many backend instances | Singleton pattern or pass via DI — use DI |
| `CoTAgent` tests that mock `ToolExecutor` directly | Tests that patch `executor._execute_with_retries` will break if the call path changes | Search for all such mocks and update |
| `ReasoningEngine` accesses `executor._registry` directly | `engine.get_available_tools()` reaches into `self._executor._registry` — not routed through backend, which is correct | Leave as-is; tool listing is read-only, not an activity |

### Low Risk

| Risk | Why |
|---|---|
| `InProcessBackend.run_activity` adds one async call level | Adds a single await hop. No performance impact in practice |
| Import cycle risk | `execution/` imports nothing from `agents/` or `tools/` — safe |

---

## What Needs to Be Tested

### Unit Tests (new file: `tests/execution/test_inprocess_backend.py`)

- [ ] `run_activity` calls `fn` with correct args and returns result
- [ ] `run_activity` propagates exceptions from `fn` (does NOT swallow)
- [ ] `run_child_agent` calls `agent_fn` with correct args and returns result
- [ ] `run_child_agent` propagates exceptions

### Integration Tests (update existing)

- [ ] `ToolExecutor.execute()` still records TOOL_CALL and TOOL_RESULT steps to chain
- [ ] `ToolExecutor.execute()` still respects retry config (max_retries, backoff)
- [ ] `ToolExecutor.execute()` still enforces timeout (ToolTimeoutError)
- [ ] `ToolExecutor.execute()` still enforces skill restrictions
- [ ] `ToolExecutor.execute()` still tracks cost
- [ ] `ToolExecutor.execute_with_events()` still yields steps in correct order
- [ ] `CoTAgent` still processes task end-to-end with default backend (smoke test)
- [ ] `CoTAgent` accepts custom backend injected via constructor
- [ ] Custom backend's `run_activity` is called (mock backend, verify call)

### Regression: All Existing Tests Must Still Pass

Run `pytest` — the 166 passing tests must remain green. Key suites:
- `tests/agents/` — all agent event and delegation tests
- `tests/tools/` — tool executor, registry, builtin tools
- `tests/orchestration/` — router tests
- `tests/agents/cot/` — ReAct loop, prompt tests

### Contract Test (new): Backend Compliance

```python
# tests/execution/test_backend_contract.py
# Any backend must pass this suite — ensures Temporal backend
# will work when implemented later

class BackendContractTest:
    backend: ExecutionBackend  # subclasses set this

    async def test_run_activity_returns_result(self): ...
    async def test_run_activity_propagates_error(self): ...
    async def test_run_child_agent_returns_string(self): ...


class TestInProcessBackendContract(BackendContractTest):
    backend = InProcessBackend()
```

---

## Implementation Order

1. Create `src/omniforge/execution/` package (backend.py, inprocess.py, __init__.py)
2. Add `backend` param to `ToolExecutor.__init__` (default=None → InProcessBackend)
3. Refactor `_execute_with_retries` to route outermost call through backend
4. Update `execute_with_events` the same way
5. Add `backend` param to `CoTAgent.__init__`, thread to ToolExecutor
6. Write new tests in `tests/execution/`
7. Run full test suite — must be green

**No changes to**: ToolRegistry, BaseAgent, MasterAgent, Skills system, API routes, prompts.

---

## Future: Adding TemporalBackend

Once this is in place, adding Temporal is just:

```python
# src/omniforge/execution/temporal.py
# Only importable if `pip install omniforge[temporal]`
from temporalio import workflow
from .backend import ExecutionBackend

class TemporalBackend(ExecutionBackend):
    async def run_activity(self, fn, *args, activity_name="",
                           timeout_ms=30_000, max_retries=3, **kwargs):
        return await workflow.execute_activity(
            fn, args,
            start_to_close_timeout=timedelta(milliseconds=timeout_ms),
            retry_policy=RetryPolicy(maximum_attempts=max_retries),
        )
    ...
```

Agents switch backends at construction time — zero code change in agent logic.
