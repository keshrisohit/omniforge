# TASK-105: Implement Tool Executor

## Description

Create the ToolExecutor class that provides unified execution for all tool calls. This handles argument validation, retry logic, timeout enforcement, chain integration, and event emission.

## Requirements

- Create `ToolExecutor` class with:
  - Constructor accepting registry, rate_limiter (optional), cost_tracker (optional)
  - `execute()` method that:
    - Retrieves tool from registry
    - Validates arguments via tool.validate_arguments()
    - Checks rate limits (if rate_limiter provided)
    - Creates tool_call step and adds to chain
    - Executes tool with retry logic
    - Tracks cost (if cost_tracker provided)
    - Creates tool_result step and adds to chain
    - Returns ToolResult
  - `_execute_with_retries()` internal method:
    - Implements exponential backoff
    - Respects timeout_ms configuration
    - Catches and categorizes errors
    - Returns ToolResult with retries_used count
  - `execute_with_events()` async generator method:
    - Same as execute() but yields ReasoningStep events
    - Useful for streaming to clients

## Acceptance Criteria

- [ ] Tools execute successfully through executor
- [ ] Retry logic works with exponential backoff
- [ ] Timeouts enforced via asyncio.wait_for
- [ ] Rate limiting checked before execution (when limiter provided)
- [ ] Cost tracking records after execution (when tracker provided)
- [ ] Steps added to chain with correct correlation IDs
- [ ] execute_with_events() yields steps for streaming
- [ ] Unit tests mock tools and verify retry/timeout behavior

## Dependencies

- TASK-101 (for ReasoningChain, ReasoningStep)
- TASK-102 (for BaseTool, ToolResult, ToolCallContext)
- TASK-103 (for ToolRegistry)
- TASK-104 (for error types)

## Files to Create/Modify

- `src/omniforge/tools/executor.py` (new)
- `tests/tools/test_executor.py` (new)

## Estimated Complexity

Complex (6-8 hours)

## Key Considerations

- Use asyncio.wait_for for timeout enforcement
- Calculate backoff: backoff_ms * (multiplier ** attempt)
- Handle both retryable and non-retryable errors
- Ensure chain steps have matching correlation_ids
