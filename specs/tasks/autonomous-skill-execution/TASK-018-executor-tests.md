# TASK-018: Unit tests for AutonomousSkillExecutor

**Priority:** P0 (Must Have)
**Estimated Effort:** Medium (1-3 days)
**Dependencies:** TASK-005, TASK-008

---

## Description

Create comprehensive unit tests for `AutonomousSkillExecutor` including the ReAct loop, error recovery, and result handling. Target 90% code coverage. Tests should mock LLM calls and tool execution to test control flow and edge cases.

## Files to Create

- `tests/skills/test_autonomous_executor.py`

## Test Requirements

### ReAct Loop Tests

```python
class TestAutonomousSkillExecutorReActLoop:
    """Tests for ReAct loop execution."""

    async def test_execute_returns_events(self, executor):
        """Execute should yield TaskEvent instances."""

    async def test_execute_emits_start_event(self, executor):
        """Execute should emit TaskStatusEvent at start."""

    async def test_execute_emits_done_event(self, executor):
        """Execute should emit TaskDoneEvent on completion."""

    async def test_execute_respects_max_iterations(self, executor, mock_llm):
        """Execute should stop at max_iterations."""
        # Mock LLM to never return final answer
        # Verify exactly max_iterations LLM calls

    async def test_execute_stops_on_final_answer(self, executor, mock_llm):
        """Execute should stop when LLM returns final answer."""
        # Mock LLM to return final answer on iteration 2
        # Verify loop terminated early

    async def test_execute_calls_llm_with_system_prompt(self, executor, mock_llm):
        """LLM should be called with skill-specific system prompt."""

    async def test_execute_maintains_conversation_history(self, executor, mock_llm):
        """Conversation should accumulate across iterations."""

    async def test_execute_handles_no_action_response(self, executor, mock_llm):
        """Response without action should prompt for continuation."""
```

### Tool Execution Tests

```python
class TestAutonomousSkillExecutorToolCalls:
    """Tests for tool execution within ReAct loop."""

    async def test_execute_tool_on_action(self, executor, mock_tool_executor):
        """Tools should be executed when LLM requests action."""

    async def test_tool_result_added_to_conversation(self, executor, mock_tool_executor):
        """Tool results should be added as observations."""

    async def test_tool_failure_triggers_observation(self, executor, mock_tool_executor):
        """Tool failures should be reported back to LLM."""

    async def test_multiple_tool_calls_in_sequence(self, executor, mock_llm, mock_tool_executor):
        """Multiple tools can be called across iterations."""
```

### Error Recovery Tests

```python
class TestAutonomousSkillExecutorErrorRecovery:
    """Tests for error recovery behavior."""

    async def test_error_recovery_retries_tool(self, executor, mock_tool_executor):
        """Failed tool should be retried up to max_retries."""
        # Mock tool to fail twice then succeed
        # Verify retries and eventual success

    async def test_error_recovery_tracks_failed_approaches(self, executor):
        """Failed approaches should be tracked to prevent loops."""

    async def test_error_recovery_suggests_alternative(self, executor, mock_tool_executor):
        """After max retries, LLM should be prompted for alternative."""

    async def test_partial_results_collected(self, executor):
        """Successful intermediate results should be collected."""

    async def test_partial_results_returned_on_max_iterations(self, executor):
        """Partial results should be included in final output."""

    async def test_handle_llm_error(self, executor, mock_llm):
        """LLM call failures should be handled gracefully."""

    async def test_error_count_tracked(self, executor):
        """Error count should be incremented on failures."""
```

### Configuration Tests

```python
class TestAutonomousSkillExecutorConfig:
    """Tests for configuration handling."""

    def test_default_config_applied(self, executor):
        """Default configuration should be used when not specified."""

    def test_custom_config_applied(self):
        """Custom configuration should override defaults."""

    def test_config_from_skill_metadata(self, skill_with_metadata):
        """Configuration should be built from skill metadata."""

    def test_early_termination_config(self, executor):
        """Early termination setting should be respected."""
```

### Sync Execution Tests

```python
class TestAutonomousSkillExecutorSync:
    """Tests for execute_sync method."""

    async def test_execute_sync_returns_result(self, executor):
        """execute_sync should return ExecutionResult."""

    async def test_execute_sync_success_result(self, executor, mock_llm):
        """Successful execution should return success=True."""

    async def test_execute_sync_failure_result(self, executor, mock_llm):
        """Failed execution should return success=False with error."""

    async def test_execute_sync_includes_iterations(self, executor):
        """Result should include iterations_used count."""
```

### Preprocessing Integration Tests

```python
class TestAutonomousSkillExecutorPreprocessing:
    """Tests for preprocessing pipeline integration."""

    async def test_preprocess_content_called(self, executor):
        """Preprocessing should be called before execution."""

    async def test_context_loader_used(self, executor, mock_context_loader):
        """ContextLoader should be used for progressive loading."""

    async def test_dynamic_injector_used(self, executor, mock_dynamic_injector):
        """DynamicInjector should be used for command injection."""

    async def test_string_substitutor_used(self, executor, mock_string_substitutor):
        """StringSubstitutor should be used for variable replacement."""
```

## Test Fixtures

```python
@pytest.fixture
def mock_skill():
    """Create mock skill for testing."""
    skill = MagicMock()
    skill.metadata.name = "test-skill"
    skill.metadata.description = "Test skill"
    skill.metadata.allowed_tools = ["read", "write"]
    skill.metadata.model = None
    skill.metadata.max_iterations = None
    skill.content = "Test skill instructions"
    skill.base_path = Path("/tmp/skills/test")
    return skill

@pytest.fixture
def mock_tool_registry():
    """Create mock tool registry."""
    return MagicMock()

@pytest.fixture
def mock_tool_executor():
    """Create mock tool executor."""
    executor = AsyncMock()
    executor.execute_tool.return_value = ToolResult(success=True, output="Success")
    return executor

@pytest.fixture
def mock_llm():
    """Create mock LLM that returns final answer."""
    # Return final answer response format

@pytest.fixture
def executor(mock_skill, mock_tool_registry, mock_tool_executor):
    """Create executor with mocked dependencies."""
    return AutonomousSkillExecutor(
        skill=mock_skill,
        tool_registry=mock_tool_registry,
        tool_executor=mock_tool_executor,
    )
```

## Coverage Targets

| Component | Target Coverage |
|-----------|-----------------|
| AutonomousSkillExecutor | 90% |
| Error recovery paths | 85% |
| Edge cases | 80% |

## Acceptance Criteria

- [ ] All listed tests implemented
- [ ] Tests pass reliably
- [ ] Coverage targets met
- [ ] Error recovery thoroughly tested
- [ ] Async patterns correctly handled
- [ ] Tests run in under 60 seconds
- [ ] No flaky tests

## Technical Notes

- Use `pytest-asyncio` for async test support
- Mock LLM responses to control test flow
- Use `AsyncMock` from `unittest.mock` for async methods
- Consider using parametrized tests for iteration counts
- Test both streaming (execute) and non-streaming (execute_sync) paths
