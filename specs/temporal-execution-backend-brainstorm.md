# Temporal Execution Backend - Brainstorm

**Date**: 2026-02-26
**Status**: Brainstorm / Not Started

---

## The Core Idea

Back agent execution on Temporal so the ReAct loop is durable and restartable.
Tool execution and LLM calls become Temporal Activities. HITL becomes a Signal.

## The Temporal Mapping

| OmniForge Concept | Temporal Concept |
|---|---|
| Agent ReAct loop | Workflow |
| LLM inference call | Activity |
| Tool execution | Activity |
| Sub-agent delegation | Child Workflow |
| HITL pause | Signal (workflow blocks waiting) |
| Task ID | Workflow Run ID |
| Task state | Workflow state (durable) |

## What Changes vs What Stays

**Changes:**
- `CoTAgent.process_task()` → Temporal workflow definition
- `ToolExecutor.execute()` → Temporal activity
- Task lifecycle managed by Temporal (not InMemoryTaskRepository)
- Worker processes replace current async task runners

**Stays the same:**
- ToolRegistry, BaseAgent, prompt system
- Skills system
- REST API surface (just calls Temporal client instead of running agent directly)

## The ReAct Loop as Workflow (sketch)

```python
@workflow.defn
class AgentWorkflow:
    @workflow.run
    async def run(self, task: TaskInput) -> str:
        messages = [{"role": "user", "content": task.content}]

        for _ in range(max_iterations):
            response = await workflow.execute_activity(
                llm_inference, messages,
                start_to_close_timeout=timedelta(seconds=60),
                retry_policy=RetryPolicy(max_attempts=3)
            )
            tool_calls = parse_tool_calls(response)  # deterministic, stays in workflow

            if not tool_calls:
                return response

            results = await asyncio.gather(*[
                workflow.execute_activity(execute_tool, tc, ...)
                for tc in tool_calls
            ])
            messages = build_next_messages(messages, response, results)
```

## HITL via Signal

```python
@workflow.signal
def provide_human_input(self, response: str):
    self._human_response = response

# Workflow blocks durably (survives crashes)
await workflow.wait_condition(lambda: self._human_response is not None)
```

## Sub-agent = Child Workflow

```python
child_result = await workflow.execute_child_workflow(
    AgentWorkflow.run, task_input,
    id=f"{workflow.info().workflow_id}-subagent-{uuid}",
    parent_close_policy=ParentClosePolicy.REQUEST_CANCEL
)
```

## SSE Streaming Bridge

Temporal doesn't natively push events. Options:
- **Preferred**: Events published to pub/sub (Redis) by activities. SSE endpoint subscribes.
- **Simple**: SSE polls via Temporal Queries (not real-time but works)

## Long Loop Problem

Temporal caps workflow history at ~50MB. Long ReAct loops need `continue_as_new`:

```python
if workflow.info().get_current_history_length() > 1000:
    workflow.continue_as_new(AgentWorkflowInput(messages=messages, iteration=i))
```

## Making Temporal Optional

See `temporal-optional-backend-design.md` for the abstraction layer design.

## Phased Approach

1. Define `ExecutionBackend` abstraction (no Temporal yet)
2. Implement `InProcessBackend` — current behavior, zero new deps
3. Implement `TemporalBackend` as optional extra (`pip install omniforge[temporal]`)
4. Wrap tool execution first (lowest risk)
5. Wrap full ReAct loop
6. Replace task repository with Temporal as source of truth
7. HITL via signals

## Key Tradeoffs

| | Temporal | Current (In-process) |
|---|---|---|
| Crash recovery | Durable, restartable | Lost |
| HITL | First-class signals | Event-based |
| Visibility | Temporal UI, full history | Manual tracing |
| Complexity | New infra dependency | Simple in-process |
| Local dev | Needs Temporal server | Just run Python |
| Determinism | Workflow code must be pure | No constraint |
| Parallel agents | Native child workflows | asyncio gather |
