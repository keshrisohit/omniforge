# TASK-201: Implement ReasoningEngine

## Description

Create the ReasoningEngine class that provides a high-level API for agents to interact with tools and build reasoning chains. This is the primary interface agents use for calling LLMs, executing tools, and managing chain state.

## Requirements

- Create `ToolCallResult` class wrapping ToolResult with step references:
  - result: ToolResult
  - call_step: ReasoningStep
  - result_step: ReasoningStep
  - Properties: step_id, success, value, error
- Create `ReasoningEngine` class with:
  - Constructor accepting chain, executor, task, default_llm_model
  - Properties: chain, task
  - `add_thinking()` method for adding thinking steps
  - `add_synthesis()` method for combining results
  - `call_llm()` convenience method for LLM calls:
    - Parameters: prompt, model, system, temperature, max_tokens, visibility
    - Returns ToolCallResult
  - `call_tool()` method for any registered tool:
    - Parameters: tool_name, arguments, visibility
    - Returns ToolCallResult
  - `get_available_tools()` returning list of ToolDefinitions
  - `execute_reasoning()` async generator for yielding steps as events

## Acceptance Criteria

- [ ] add_thinking() creates THINKING step and adds to chain
- [ ] add_synthesis() creates SYNTHESIS step with source references
- [ ] call_llm() wraps LLM tool with convenience parameters
- [ ] call_tool() executes any tool and returns ToolCallResult
- [ ] ToolCallResult provides easy access to step IDs for synthesis
- [ ] execute_reasoning() yields steps as they are created
- [ ] Chain state is correctly maintained throughout reasoning
- [ ] Unit tests cover all methods with mocked executor

## Dependencies

- TASK-101 (for ReasoningChain, ReasoningStep)
- TASK-102 (for ToolCallContext, ToolResult)
- TASK-105 (for ToolExecutor)

## Files to Create/Modify

- `src/omniforge/agents/cot/engine.py` (new)
- `tests/agents/cot/test_engine.py` (new)

## Estimated Complexity

Complex (6-8 hours)

## Key Considerations

- execute_reasoning() needs to poll for new steps during async execution
- Consider using asyncio.Queue for step delivery
- ToolCallResult should make step referencing ergonomic
