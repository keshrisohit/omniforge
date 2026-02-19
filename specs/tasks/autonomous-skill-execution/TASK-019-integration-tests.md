# TASK-019: Integration tests for end-to-end execution

**Priority:** P0 (Must Have)
**Estimated Effort:** Medium (1-3 days)
**Dependencies:** TASK-012, TASK-013

---

## Description

Create integration tests that validate the complete autonomous skill execution flow from skill loading through result generation. Tests should use realistic skill definitions and exercise the full preprocessing pipeline, ReAct loop, and event streaming.

## Files to Create

- `tests/skills/test_autonomous_execution_integration.py`
- `tests/skills/fixtures/test_skills/` - Test skill directories

## Test Requirements

### End-to-End Execution Tests

```python
class TestAutonomousExecutionIntegration:
    """Integration tests for complete execution flow."""

    async def test_end_to_end_simple_skill(self, skill_directory, orchestrator):
        """Simple skill should execute successfully."""
        events = []
        async for event in orchestrator.execute("simple-skill", "Process data"):
            events.append(event)

        # Verify complete event sequence
        assert any(isinstance(e, TaskStatusEvent) for e in events)
        assert any(isinstance(e, TaskDoneEvent) for e in events)
        assert events[-1].final_state == TaskState.COMPLETED

    async def test_end_to_end_with_tool_calls(self, skill_with_tools, orchestrator):
        """Skill with tool calls should execute tools."""
        events = []
        async for event in orchestrator.execute("tool-skill", "Read file.txt"):
            events.append(event)

        # Verify tool was called
        tool_events = [e for e in events if "read" in str(e).lower()]
        assert len(tool_events) > 0

    async def test_end_to_end_with_error_recovery(self, flaky_tool_skill, orchestrator):
        """Skill should recover from tool failures."""
        # Setup tool to fail initially then succeed
        events = []
        async for event in orchestrator.execute("flaky-skill", "Process"):
            events.append(event)

        # Should eventually succeed despite initial failures
        assert events[-1].final_state == TaskState.COMPLETED

    async def test_end_to_end_max_iterations(self, complex_skill, orchestrator):
        """Skill should stop at max_iterations if not complete."""
        events = []
        async for event in orchestrator.execute("complex-skill", "Infinite task"):
            events.append(event)

        # Should have max_iterations worth of iteration events
        # Should end with FAILED or partial result
```

### Preprocessing Pipeline Tests

```python
class TestPreprocessingIntegration:
    """Integration tests for preprocessing pipeline."""

    async def test_variable_substitution_integration(self, skill_with_variables, orchestrator):
        """Variables should be substituted in skill content."""
        # Skill content contains $ARGUMENTS and ${SKILL_DIR}
        # Verify they are replaced before LLM sees them

    async def test_dynamic_injection_integration(self, skill_with_injections, orchestrator):
        """Dynamic injections should be processed before execution."""
        # Skill content contains !`date` injection
        # Verify date is injected into content

    async def test_context_loading_integration(self, skill_with_supporting_files, orchestrator):
        """Supporting files should be available for loading."""
        # Skill has reference.md mentioned in SKILL.md
        # Verify file can be loaded via read tool
```

### Routing Tests

```python
class TestRoutingIntegration:
    """Integration tests for execution mode routing."""

    async def test_autonomous_mode_routing(self, autonomous_skill, orchestrator):
        """Autonomous mode should use AutonomousSkillExecutor."""
        events = []
        async for event in orchestrator.execute("auto-skill", "Task"):
            events.append(event)

        # Verify autonomous execution pattern (iterations, etc.)

    async def test_simple_mode_routing(self, simple_skill, orchestrator):
        """Simple mode should use legacy executor."""
        events = []
        async for event in orchestrator.execute("simple-skill", "Task"):
            events.append(event)

        # Verify simple execution pattern (single pass)

    async def test_forked_context_routing(self, forked_skill, orchestrator):
        """Forked context should spawn sub-agent."""
        events = []
        async for event in orchestrator.execute("fork-skill", "Analyze"):
            events.append(event)

        # Verify sub-agent spawning events
```

### Event Streaming Tests

```python
class TestEventStreamingIntegration:
    """Integration tests for event streaming."""

    async def test_events_stream_in_order(self, orchestrator):
        """Events should be emitted in correct order."""
        events = []
        async for event in orchestrator.execute("test-skill", "Task"):
            events.append(event)

        # First event should be status (RUNNING)
        assert isinstance(events[0], TaskStatusEvent)
        # Last event should be done
        assert isinstance(events[-1], TaskDoneEvent)

    async def test_events_have_timestamps(self, orchestrator):
        """All events should have timestamps."""
        async for event in orchestrator.execute("test-skill", "Task"):
            assert hasattr(event, 'timestamp')
            assert event.timestamp is not None

    async def test_visibility_filtering_end_user(self, orchestrator):
        """END_USER should only see SUMMARY events."""
        events = []
        async for event in orchestrator.execute(
            "test-skill", "Task", user_role="END_USER"
        ):
            events.append(event)

        # Should not include FULL visibility events

    async def test_visibility_filtering_developer(self, orchestrator):
        """DEVELOPER should see all events."""
        events = []
        async for event in orchestrator.execute(
            "test-skill", "Task", user_role="DEVELOPER"
        ):
            events.append(event)

        # Should include detailed tool arguments, thoughts, etc.
```

## Test Fixtures

### Test Skill Directories

Create test skills in `tests/skills/fixtures/test_skills/`:

```
tests/skills/fixtures/test_skills/
├── simple-skill/
│   └── SKILL.md
├── tool-skill/
│   └── SKILL.md
├── flaky-skill/
│   └── SKILL.md
├── complex-skill/
│   └── SKILL.md
├── skill-with-variables/
│   └── SKILL.md
├── skill-with-injections/
│   └── SKILL.md
├── skill-with-supporting-files/
│   ├── SKILL.md
│   └── reference.md
├── autonomous-skill/
│   └── SKILL.md
├── simple-mode-skill/
│   └── SKILL.md
└── forked-skill/
    └── SKILL.md
```

### Fixture Examples

```python
@pytest.fixture
def skill_directory(tmp_path):
    """Create temporary skill directory with test skill."""
    skill_dir = tmp_path / "test-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("""---
name: test-skill
description: Test skill for integration testing
allowed-tools:
  - read
  - write
---

# Test Skill

Process files and generate output.
""")
    return skill_dir

@pytest.fixture
def orchestrator(skill_directory):
    """Create SkillOrchestrator with test setup."""
    config = StorageConfig(project_path=str(skill_directory.parent))
    loader = SkillLoader(config)
    loader.build_index(force=True)

    registry = get_default_tool_registry()
    tool_executor = ToolExecutor(registry)

    return SkillOrchestrator(
        skill_loader=loader,
        tool_registry=registry,
        tool_executor=tool_executor,
    )
```

## Acceptance Criteria

- [ ] All listed tests implemented
- [ ] Tests use realistic skill definitions
- [ ] Full preprocessing pipeline exercised
- [ ] Event streaming validated
- [ ] Routing logic tested
- [ ] Error recovery paths tested
- [ ] Tests run in under 2 minutes
- [ ] Tests are reproducible (no flakiness)

## Technical Notes

- Use `pytest-asyncio` for async test support
- Consider using `pytest-timeout` for long-running tests
- Mock LLM at the boundary to avoid API calls
- Use real file system for skill loading tests
- Test fixtures should be reusable across test classes
