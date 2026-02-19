# TASK-011: Implement sub-agent depth tracking

**Priority:** P1 (Should Have)
**Estimated Effort:** Small (<1 day)
**Dependencies:** TASK-005

---

## Description

Add explicit depth tracking for sub-agent execution to prevent infinite recursion and resource exhaustion. Skills with `context: fork` spawn sub-agents, which could theoretically spawn their own sub-agents. This task implements a maximum depth limit (default: 2 levels) and proper depth propagation.

## Files to Modify

- `src/omniforge/skills/config.py` - Add ExecutionContext with depth tracking
- `src/omniforge/skills/autonomous_executor.py` - Pass and check depth
- `src/omniforge/skills/orchestrator.py` - Propagate depth to sub-agents

## Implementation Requirements

### ExecutionContext Dataclass

```python
@dataclass
class ExecutionContext:
    """Context passed through execution for tracking and limits."""
    depth: int = 0
    max_depth: int = 2
    parent_task_id: Optional[str] = None
    root_task_id: Optional[str] = None

    def create_child_context(self, task_id: str) -> "ExecutionContext":
        """Create child context for sub-agent."""
        return ExecutionContext(
            depth=self.depth + 1,
            max_depth=self.max_depth,
            parent_task_id=task_id,
            root_task_id=self.root_task_id or task_id,
        )

    def can_spawn_sub_agent(self) -> bool:
        """Check if another sub-agent level is allowed."""
        return self.depth < self.max_depth
```

### Depth Check in Orchestrator

```python
async def _execute_forked(
    self,
    skill: Skill,
    user_request: str,
    task_id: str,
    context: ExecutionContext,
    ...
) -> AsyncIterator[TaskEvent]:
    """Execute skill in forked (sub-agent) context."""

    # Check depth limit
    if not context.can_spawn_sub_agent():
        yield TaskErrorEvent(
            task_id=task_id,
            error_code="MAX_DEPTH_EXCEEDED",
            error_message=(
                f"Maximum sub-agent depth ({context.max_depth}) exceeded. "
                f"Cannot spawn sub-agent at depth {context.depth}."
            ),
        )
        yield TaskDoneEvent(task_id=task_id, final_state=TaskState.FAILED)
        return

    # Create child context
    child_context = context.create_child_context(task_id)

    # Execute sub-agent with child context
    sub_config = AutonomousConfig(
        max_iterations=self._config.max_iterations // 2,  # 50% budget
        ...
    )

    executor = AutonomousSkillExecutor(
        skill=skill,
        config=sub_config,
        context=child_context,  # Pass child context
        ...
    )
```

### Iteration Budget Reduction

Sub-agents get reduced iteration budget based on depth:
- Level 0 (root): 100% of max_iterations
- Level 1 (sub-agent): 50% of max_iterations
- Level 2 (sub-sub-agent): 25% of max_iterations

```python
def _get_iteration_budget_for_depth(self, depth: int) -> int:
    """Calculate iteration budget based on depth."""
    base = self._default_config.max_iterations
    return max(3, base // (2 ** depth))  # Minimum 3 iterations
```

### Logging and Metrics

Log sub-agent spawning:
```python
logger.info(
    "Spawning sub-agent",
    skill=skill.metadata.name,
    depth=child_context.depth,
    parent_task_id=context.parent_task_id,
    iteration_budget=sub_config.max_iterations,
)
```

Track in metrics:
```python
metrics["sub_agent_depth"] = context.depth
metrics["parent_task_id"] = context.parent_task_id
```

## Acceptance Criteria

- [ ] ExecutionContext tracks depth and limits
- [ ] Sub-agents cannot exceed max_depth (default: 2)
- [ ] Clear error when depth exceeded
- [ ] Child context inherits and increments depth
- [ ] Iteration budget reduced for deeper levels
- [ ] Root task ID propagated for tracing
- [ ] Depth logged for debugging
- [ ] Unit tests for depth logic

## Testing

```python
def test_execution_context_depth_tracking():
    """Context should track depth correctly."""
    root = ExecutionContext()
    assert root.depth == 0
    assert root.can_spawn_sub_agent()

    child = root.create_child_context("task-1")
    assert child.depth == 1
    assert child.parent_task_id == "task-1"
    assert child.can_spawn_sub_agent()

    grandchild = child.create_child_context("task-2")
    assert grandchild.depth == 2
    assert not grandchild.can_spawn_sub_agent()  # At max depth

def test_max_depth_exceeded_error():
    """Should error when max depth exceeded."""
    context = ExecutionContext(depth=2, max_depth=2)
    # Attempt to spawn sub-agent should yield error event

def test_iteration_budget_reduction():
    """Sub-agents get reduced iteration budget."""
    orchestrator = SkillOrchestrator(...)
    assert orchestrator._get_iteration_budget_for_depth(0) == 15
    assert orchestrator._get_iteration_budget_for_depth(1) == 7
    assert orchestrator._get_iteration_budget_for_depth(2) == 3
```

## Technical Notes

- Default max_depth=2 is conservative (root + 2 sub-agent levels)
- Consider making max_depth configurable per skill
- Track total iterations across all sub-agents for cost management
- Sub-agent task IDs should include parent reference for tracing
