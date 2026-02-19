# TASK-003: OrchestrationManager (All Strategies + Synthesis)

**Phase**: 2 - Orchestrator
**Complexity**: Medium
**Dependencies**: TASK-001
**Files to create/modify**:
- Create `src/omniforge/orchestration/manager.py`
- Create `tests/orchestration/test_manager.py`

## Description

Implement the `OrchestrationManager` that coordinates sub-agent queries using the existing `A2AClient`. This is the core of the Orchestrator Pattern -- delegates tasks to sub-agents, collects responses, and synthesizes them.

### Models (in manager.py)

- `DelegationStrategy(str, Enum)` - PARALLEL, SEQUENTIAL, FIRST_SUCCESS
- `SubAgentResult` dataclass - agent_id, success (bool), response (Optional[str]), error (Optional[str]), latency_ms (int)

### OrchestrationManager class

**Constructor**: Takes `A2AClient` (existing from `src/omniforge/orchestration/client.py`) and `conversation_repo` (`SQLiteConversationRepository`).

**Core method:**
`delegate_to_agents(thread_id, tenant_id, user_id, message, target_agent_cards: list[AgentCard], strategy: DelegationStrategy, timeout_ms: int) -> list[SubAgentResult]`

**Strategy implementations:**
- `_delegate_parallel` - Use `asyncio.gather` to send tasks to all agents concurrently via `A2AClient.send_task()`. Each agent call collects text from `TaskMessageEvent.message_parts` where part type is "text". Returns `SubAgentResult` per agent.
- `_delegate_sequential` - Iterate agents one at a time, calling each via `A2AClient.send_task()`.
- `_delegate_first_success` - Like parallel, but return once one agent succeeds.

**Synthesis method:**
`synthesize_responses(sub_results: list[SubAgentResult]) -> str`
- No results: return "No responses received from sub-agents."
- All failed: return "All sub-agents failed to provide responses."
- Single success: return that response directly
- Multiple successes: concatenate with attribution: `"From {agent_id}:\n{response}"` joined by `"\n\n"`

### Key behaviors

- Use existing `A2AClient.send_task()` for HTTP communication
- Create `TaskCreateRequest` with `TextPart(text=message)` for each sub-agent
- Track latency per agent using `time.time()`
- Catch all exceptions per-agent; never let one agent failure crash the batch
- Individual agent failures produce `SubAgentResult(success=False, error=str(e))`

## Acceptance Criteria

- Parallel delegation sends to all agents concurrently (verify with mock timing)
- Sequential delegation sends one at a time in order
- First-success returns first successful result
- Individual agent failures do not crash the batch
- `synthesize_responses` produces correct output for 0, 1, and N results
- Tests mock `A2AClient.send_task()` to return controlled `TaskEvent` sequences
- Latency tracking produces reasonable millisecond values
