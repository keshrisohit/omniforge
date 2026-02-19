# TASK-012: Create SkillOrchestrator for routing

**Priority:** P0 (Must Have)
**Estimated Effort:** Medium (1-3 days)
**Dependencies:** TASK-005, TASK-006

---

## Description

Create `SkillOrchestrator` class to route skill execution to the appropriate executor based on execution mode and manage skill lifecycle. Routes to `AutonomousSkillExecutor` for autonomous mode or `ExecutableSkill` for simple/legacy mode. Also handles sub-agent spawning for skills with `context: fork`.

## Files to Create

- `src/omniforge/skills/orchestrator.py` - SkillOrchestrator implementation

## Implementation Requirements

### ExecutionMode Enum

```python
class ExecutionMode(str, Enum):
    AUTONOMOUS = "autonomous"
    SIMPLE = "simple"
```

### SkillOrchestrator Class

**Constructor:**
```python
def __init__(
    self,
    skill_loader: SkillLoader,
    tool_registry: ToolRegistry,
    tool_executor: ToolExecutor,
    default_config: Optional[AutonomousConfig] = None,
) -> None
```

**Main Method:**
```python
async def execute(
    self,
    skill_name: str,
    user_request: str,
    task_id: str = "default",
    session_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    execution_mode_override: Optional[ExecutionMode] = None,
    context: Optional[ExecutionContext] = None,
) -> AsyncIterator[TaskEvent]:
    """Execute a skill by name.

    1. Load skill via SkillLoader
    2. Determine execution mode
    3. Handle forked context (sub-agent)
    4. Route to appropriate executor
    """
```

### Routing Logic

```python
def _determine_execution_mode(
    self,
    skill: Skill,
    override: Optional[ExecutionMode],
) -> ExecutionMode:
    """Determine execution mode for a skill.

    Priority:
    1. Override parameter (if provided)
    2. Skill metadata execution_mode
    3. Default: AUTONOMOUS
    """
    if override:
        return override

    mode = skill.metadata.execution_mode or "autonomous"
    return ExecutionMode(mode.lower())
```

### Execution Paths

**Autonomous Path:**
```python
async def _execute_autonomous(
    self,
    skill: Skill,
    user_request: str,
    task_id: str,
    session_id: Optional[str],
    tenant_id: Optional[str],
    context: ExecutionContext,
) -> AsyncIterator[TaskEvent]:
    """Execute skill using AutonomousSkillExecutor."""
    config = self._build_config(skill)
    executor = AutonomousSkillExecutor(
        skill=skill,
        tool_registry=self._tool_registry,
        tool_executor=self._tool_executor,
        config=config,
        context=context,
    )

    # Activate skill context in tool executor
    self._tool_executor.activate_skill(skill)

    try:
        async for event in executor.execute(...):
            yield event
    finally:
        self._tool_executor.deactivate_skill(skill.metadata.name)
```

**Simple/Legacy Path:**
```python
async def _execute_simple(
    self,
    skill: Skill,
    user_request: str,
    task_id: str,
) -> AsyncIterator[TaskEvent]:
    """Execute skill using ExecutableSkill (legacy)."""
    executor = ExecutableSkill(skill=skill, tool_registry=self._tool_registry)

    yield TaskStatusEvent(task_id=task_id, state=TaskState.RUNNING)

    result = await executor.execute(user_request, task_id)

    yield TaskMessageEvent(task_id=task_id, message_parts=[TextPart(text=result)])
    yield TaskDoneEvent(task_id=task_id, final_state=TaskState.COMPLETED)
```

**Forked Context Path:**
```python
async def _execute_forked(
    self,
    skill: Skill,
    user_request: str,
    task_id: str,
    context: ExecutionContext,
    ...
) -> AsyncIterator[TaskEvent]:
    """Execute skill in forked (sub-agent) context.

    1. Check depth limit
    2. Create child context
    3. Build sub-agent with reduced budget
    4. Execute and summarize results
    """
```

### Configuration Merging

```python
def _build_config(self, skill: Skill) -> AutonomousConfig:
    """Build config from skill metadata and platform defaults."""
    config = AutonomousConfig(
        max_iterations=skill.metadata.max_iterations or self._default_config.max_iterations,
        max_retries_per_tool=skill.metadata.max_retries_per_tool or self._default_config.max_retries_per_tool,
        model=skill.metadata.model or self._default_config.model,
        # ... other fields
    )
    return config
```

## Acceptance Criteria

- [ ] Routes autonomous mode to AutonomousSkillExecutor
- [ ] Routes simple mode to ExecutableSkill (legacy)
- [ ] Handles forked context for sub-agents
- [ ] Execution mode override parameter works
- [ ] Configuration merges skill + platform defaults
- [ ] Skill context activated/deactivated properly
- [ ] Streaming events from both execution paths
- [ ] Tenant ID propagated for multi-tenancy
- [ ] Unit tests for routing logic

## Testing

```python
async def test_routes_to_autonomous_executor():
    """Autonomous mode should use AutonomousSkillExecutor."""
    skill = create_skill(execution_mode="autonomous")
    orchestrator = SkillOrchestrator(...)

    events = [e async for e in orchestrator.execute("test-skill", "request")]
    # Verify autonomous-specific events

async def test_routes_to_simple_executor():
    """Simple mode should use ExecutableSkill."""
    skill = create_skill(execution_mode="simple")
    events = [e async for e in orchestrator.execute("test-skill", "request")]
    # Verify simple execution

async def test_execution_mode_override():
    """Override should take precedence."""
    skill = create_skill(execution_mode="autonomous")
    events = [e async for e in orchestrator.execute(
        "test-skill", "request",
        execution_mode_override=ExecutionMode.SIMPLE
    )]
    # Should use simple executor

async def test_forked_context_spawns_sub_agent():
    """Skills with context: fork should spawn sub-agent."""
    skill = create_skill(context="fork")
    events = [e async for e in orchestrator.execute("fork-skill", "request")]
    # Verify sub-agent execution
```

## Technical Notes

- Use existing SkillLoader for loading skills
- Use existing ToolExecutor.activate_skill/deactivate_skill
- Default context: ExecutionContext(depth=0)
- Consider adding skill execution metrics/telemetry
- Log execution path at INFO level
