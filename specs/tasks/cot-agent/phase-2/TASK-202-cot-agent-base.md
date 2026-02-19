# TASK-202: Implement CoTAgent Base Class

## Description

Create the CoTAgent abstract base class that extends BaseAgent with chain of thought capabilities. This class provides the orchestration framework for visible reasoning, while subclasses implement specific reasoning logic.

## Requirements

- Create `CoTAgent` class extending BaseAgent:
  - Class attributes: identity, capabilities, skills
  - Constructor accepting:
    - agent_id, tenant_id (inherited)
    - tool_registry: ToolRegistry
    - chain_repository: ChainRepository (optional)
    - rate_limiter: RateLimiter (optional)
    - cost_tracker: CostTracker (optional)
  - Create ToolExecutor in constructor
  - Implement `process_task()` that:
    - Creates ReasoningChain for the task
    - Emits ChainStartedEvent
    - Emits TaskStatusEvent (WORKING)
    - Creates ReasoningEngine
    - Calls abstract `reason()` method via wrapper
    - Yields ReasoningStepEvent for each step
    - On completion: update chain status, persist, emit ChainCompletedEvent
    - On error: update chain status, persist, emit ChainFailedEvent
    - Emit TaskDoneEvent at end
  - Implement `_reason_with_events()` wrapper for step yielding
  - Declare abstract `reason(task, engine)` method

## Acceptance Criteria

- [ ] CoTAgent extends BaseAgent correctly
- [ ] process_task() yields correct event sequence
- [ ] Reasoning chain created and persisted
- [ ] Chain status transitions: initializing -> thinking -> completed/failed
- [ ] Subclasses can implement reason() to define behavior
- [ ] Error handling wraps failures in ChainFailedEvent
- [ ] Integration test with mock reason() implementation

## Dependencies

- TASK-101 (for ReasoningChain, ChainStatus)
- TASK-106 (for ChainStartedEvent, ReasoningStepEvent, etc.)
- TASK-201 (for ReasoningEngine)
- TASK-105 (for ToolExecutor)
- Existing BaseAgent interface

## Files to Create/Modify

- `src/omniforge/agents/cot/agent.py` (new)
- `tests/agents/cot/test_agent.py` (new)

## Estimated Complexity

Complex (6-8 hours)

## Key Considerations

- process_task is async generator yielding TaskEvent
- Chain repository may be None for in-memory only
- Consider datetime.utcnow for timestamps (or use timezone-aware)
