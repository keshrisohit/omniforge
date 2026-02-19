# TASK-005: Implement AutonomousSkillExecutor core ReAct loop

**Priority:** P0 (Must Have)
**Estimated Effort:** Large (3-5 days)
**Dependencies:** TASK-001, TASK-004

---

## Description

Create the `AutonomousSkillExecutor` class - the primary execution engine for autonomous skill execution. Implements the ReAct (Reason-Act-Observe) pattern with iterative refinement, allowing skills to think, call tools, observe results, and repeat until task completion.

This is the core component of the autonomous execution system. It orchestrates the preprocessing pipeline, builds system prompts, runs the ReAct loop, and emits streaming events.

## Files to Create

- `src/omniforge/skills/autonomous_executor.py` - Main executor implementation

## Implementation Requirements

### AutonomousSkillExecutor Class

**Constructor:**
```python
def __init__(
    self,
    skill: Skill,
    tool_registry: ToolRegistry,
    tool_executor: ToolExecutor,
    config: Optional[AutonomousConfig] = None,
    context_loader: Optional[ContextLoader] = None,
    dynamic_injector: Optional[DynamicInjector] = None,
    string_substitutor: Optional[StringSubstitutor] = None,
) -> None
```

**Primary Methods:**
- `async execute(user_request, task_id, session_id, tenant_id) -> AsyncIterator[TaskEvent]` - Main streaming execution
- `async execute_sync(...) -> ExecutionResult` - Non-streaming wrapper

**ReAct Loop Flow:**
1. Preprocess content (context loading, injection, substitution)
2. Build system prompt with skill instructions, tools, available files
3. Initialize conversation with user request
4. Loop until completion or max_iterations:
   - Call LLM with conversation and system prompt
   - Parse response for action or final answer
   - If final answer: break and return
   - If action: execute tool, observe result, add to conversation
   - Emit streaming events

### Key Components

**System Prompt Building:**
- Skill instructions from SKILL.md
- Available tools from registry
- Available supporting files from ContextLoader
- ReAct format instructions
- Current iteration number

**Response Parsing:**
Expected LLM response format:
```json
{
    "thought": "Reasoning about next step",
    "action": "tool_name",
    "action_input": {"arg1": "value"},
    "is_final": false
}
```
Or for final answer:
```json
{
    "thought": "Final reasoning",
    "final_answer": "Complete response",
    "is_final": true
}
```

**Conversation Management:**
- Maintain list of messages for LLM context
- Add assistant response after each LLM call
- Add user message with observation after each tool call

### Event Emission

Emit `TaskEvent` instances at key points:
- `TaskStatusEvent` - Start, state changes
- `TaskMessageEvent` - Iteration progress, tool calls
- `TaskErrorEvent` - Errors encountered
- `TaskDoneEvent` - Completion (success/failure)

## Acceptance Criteria

- [ ] ReAct loop executes up to max_iterations
- [ ] LLM calls use ReasoningEngine.call_llm()
- [ ] Tool calls use ToolExecutor
- [ ] Conversation history maintained across iterations
- [ ] Final answer terminates loop early
- [ ] Streaming events emitted throughout
- [ ] Handles LLM call failures gracefully
- [ ] Handles tool call failures (basic - TASK-008 does full recovery)
- [ ] execute_sync() collects all events and returns ExecutionResult
- [ ] Type hints pass mypy
- [ ] Integration with preprocessing pipeline (can use mocks initially)

## Testing

```python
async def test_execute_returns_events():
    """Execute should yield TaskEvent instances."""
    executor = AutonomousSkillExecutor(mock_skill, registry, tool_executor)
    events = [e async for e in executor.execute("test request")]
    assert len(events) > 0
    assert isinstance(events[0], TaskStatusEvent)

async def test_execute_respects_max_iterations():
    """Execute should stop at max_iterations."""
    config = AutonomousConfig(max_iterations=3)
    executor = AutonomousSkillExecutor(mock_skill, registry, tool_executor, config)
    # Mock LLM to never return final answer
    events = [e async for e in executor.execute("test")]
    # Should have exactly 3 iteration attempts

async def test_execute_stops_on_final_answer():
    """Execute should stop when LLM returns final answer."""
    # Mock LLM to return final answer on iteration 2
    events = [e async for e in executor.execute("test")]
    # Verify loop terminated early

async def test_execute_sync_returns_result():
    """execute_sync should return ExecutionResult."""
    result = await executor.execute_sync("test")
    assert isinstance(result, ExecutionResult)
    assert result.success in [True, False]
```

## Technical Notes

- Use existing `ReasoningEngine` for LLM calls
- Use existing `ToolExecutor` for tool execution
- Use existing `ReActParser` for parsing LLM responses
- System prompt template should be configurable
- Consider token limits when building conversation
- Use `asyncio.timeout` for iteration timeout enforcement
