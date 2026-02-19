# TASK-008: Implement error recovery and retry logic

**Priority:** P0 (Must Have)
**Estimated Effort:** Medium (1-3 days)
**Dependencies:** TASK-005

---

## Description

Enhance `AutonomousSkillExecutor` with sophisticated error recovery and retry logic. When tools fail, the executor should retry with different parameters or suggest alternative approaches. Track failed approaches to avoid infinite loops. Target: 80%+ recovery rate for common errors.

## Files to Modify

- `src/omniforge/skills/autonomous_executor.py` - Add error recovery methods

## Implementation Requirements

### Error Recovery Strategy

1. **Retry with Same Tool** (up to max_retries_per_tool)
   - Exponential backoff between retries
   - Different parameters count as different attempts

2. **Suggest Alternative Approach**
   - After max retries exceeded, prompt LLM to try different tool
   - Provide error context to inform next decision

3. **Track Failed Approaches**
   - Hash of (tool_name, error_type) to track failures
   - Prevent infinite loops on same approach

4. **Partial Result Synthesis**
   - Collect successful intermediate results
   - Return partial results when complete solution impossible

### _handle_tool_error Method

```python
async def _handle_tool_error(
    self,
    tool_name: str,
    error: str,
    state: ExecutionState,
    tool_args: dict,
) -> str:
    """Handle tool execution error with recovery strategy.

    Returns observation message for conversation.
    """
    # Create approach key for tracking
    approach_key = f"{tool_name}:{hash(str(error)[:100])}"

    # Check retry count
    retry_count = state.failed_approaches.get(approach_key, 0)

    if retry_count < self._config.max_retries_per_tool:
        # Increment retry counter
        state.failed_approaches[approach_key] = retry_count + 1
        state.error_count += 1

        return (
            f"Tool '{tool_name}' failed: {error}\n"
            f"Retry attempt {retry_count + 1}/{self._config.max_retries_per_tool}. "
            f"Please retry with different parameters or try an alternative approach."
        )

    # Max retries exceeded - must try different approach
    return (
        f"Tool '{tool_name}' failed after {retry_count} attempts: {error}\n"
        f"This approach is not working. Please try a completely different "
        f"tool or method to accomplish this task."
    )
```

### Partial Result Synthesis

```python
def _synthesize_partial_results(self, state: ExecutionState) -> str:
    """Synthesize partial results when complete solution not possible."""
    if not state.partial_results:
        return "Unable to complete task. No partial results available."

    return (
        f"Completed {len(state.partial_results)} of intended objectives:\n"
        + "\n".join(f"- {r}" for r in state.partial_results)
        + f"\n\nEncountered {state.error_count} errors during execution."
    )
```

### Recording Partial Results

During successful tool calls, record meaningful results:
```python
if result.success and self._is_meaningful_result(result):
    state.partial_results.append(
        f"{tool_name}: {self._summarize_result(result)}"
    )
```

### Error Categories

| Error Type | Recovery Strategy |
|------------|-------------------|
| Network timeout | Retry with backoff |
| File not found | Try different path/encoding |
| Permission denied | Try alternative tool |
| Rate limit | Wait and retry |
| Invalid arguments | Fix arguments and retry |
| Tool not available | Suggest alternative |

## Acceptance Criteria

- [ ] Retries up to max_retries_per_tool times
- [ ] Different parameters count as different attempts
- [ ] Failed approaches tracked to prevent loops
- [ ] Partial results accumulated
- [ ] Partial results returned when max_iterations reached
- [ ] Error messages inform LLM of failure context
- [ ] Recovery rate measured in metrics
- [ ] Unit tests for each recovery scenario
- [ ] Integration test for end-to-end recovery

## Testing

```python
async def test_error_recovery_retries_tool():
    """Failed tool should be retried."""
    # Mock tool to fail twice then succeed
    tool_executor.execute_tool = AsyncMock(side_effect=[
        ToolResult(success=False, error="Timeout"),
        ToolResult(success=False, error="Timeout"),
        ToolResult(success=True, output="Success"),
    ])

    result = await executor.execute_sync("test")
    assert result.success
    assert tool_executor.execute_tool.call_count == 3

async def test_error_recovery_suggests_alternative():
    """After max retries, should suggest alternative."""
    # Mock tool to always fail
    config = AutonomousConfig(max_retries_per_tool=2)
    # Verify observation message suggests alternative

async def test_partial_results_returned():
    """Partial results should be returned on max_iterations."""
    # Execute with tool that partially succeeds
    result = await executor.execute_sync("complex task")
    assert "partial" in result.result.lower() or result.partial_results
```

## Technical Notes

- Use hash of error message (first 100 chars) to group similar errors
- Track approach key format: `{tool_name}:{error_hash}`
- Log recovery attempts at INFO level
- Add recovery_count to ExecutionMetrics
- Consider exponential backoff: `wait = base * (2 ** retry_count)`
