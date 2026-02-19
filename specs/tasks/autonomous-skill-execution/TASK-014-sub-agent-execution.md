# TASK-014: Integrate sub-agent execution with forked context

**Priority:** P1 (Should Have)
**Estimated Effort:** Medium (1-3 days)
**Dependencies:** TASK-011, TASK-012

---

## Description

Implement full sub-agent execution for skills with `context: fork` (FR-5). Skills can specify forked context to run in isolation with their own execution environment. The parent receives a summary of sub-agent results plus a link to the full trace for debugging.

## Files to Modify

- `src/omniforge/skills/orchestrator.py` - Complete _execute_forked implementation
- `src/omniforge/skills/autonomous_executor.py` - Support isolated execution

## Implementation Requirements

### SKILL.md Configuration for Forked Context

```yaml
---
name: deep-analysis
description: Analyze code quality in detail
context: fork
agent: Explore
max-iterations: 20
---

Perform deep analysis:
1. Find all Python files
2. Check for security vulnerabilities
3. Calculate complexity metrics
4. Generate detailed report
```

### Forked Execution Flow

1. Parent orchestrator receives skill execution request
2. Check if skill has `context: fork`
3. Verify depth limit not exceeded (TASK-011)
4. Create child execution context
5. Build sub-agent with isolated system prompt
6. Execute sub-agent to completion
7. Summarize results for parent
8. Return summary + full trace reference

### _execute_forked Implementation

```python
async def _execute_forked(
    self,
    skill: Skill,
    user_request: str,
    task_id: str,
    session_id: Optional[str],
    tenant_id: Optional[str],
    context: ExecutionContext,
) -> AsyncIterator[TaskEvent]:
    """Execute skill in forked (sub-agent) context."""

    # Step 1: Check depth limit
    if not context.can_spawn_sub_agent():
        yield TaskErrorEvent(
            task_id=task_id,
            error_code="MAX_DEPTH_EXCEEDED",
            error_message=f"Maximum sub-agent depth ({context.max_depth}) exceeded",
        )
        yield TaskDoneEvent(task_id=task_id, final_state=TaskState.FAILED)
        return

    # Step 2: Emit sub-agent start
    yield TaskStatusEvent(
        task_id=task_id,
        state=TaskState.RUNNING,
        message=f"Spawning sub-agent for skill: {skill.metadata.name}",
    )

    # Step 3: Create child context
    child_context = context.create_child_context(task_id)
    sub_task_id = f"{task_id}-subagent-{child_context.depth}"

    # Step 4: Build sub-agent configuration
    sub_config = self._build_sub_agent_config(skill, context)

    # Step 5: Create sub-agent executor
    executor = AutonomousSkillExecutor(
        skill=skill,
        tool_registry=self._tool_registry,
        tool_executor=self._tool_executor,
        config=sub_config,
        context=child_context,
    )

    # Step 6: Execute sub-agent (non-streaming to parent)
    try:
        result = await executor.execute_sync(
            user_request=user_request,
            task_id=sub_task_id,
            session_id=session_id,
            tenant_id=tenant_id,
        )

        # Step 7: Summarize for parent
        summary = self._summarize_sub_agent_result(result)

        yield TaskMessageEvent(
            task_id=task_id,
            message_parts=[
                TextPart(text=f"Sub-agent completed: {summary}"),
                TextPart(text=f"Full trace: {result.chain_id}"),
            ],
        )

        final_state = TaskState.COMPLETED if result.success else TaskState.FAILED
        yield TaskDoneEvent(task_id=task_id, final_state=final_state)

    except Exception as e:
        logger.exception("Sub-agent execution failed", skill=skill.metadata.name)
        yield TaskErrorEvent(
            task_id=task_id,
            error_code="SUBAGENT_ERROR",
            error_message=str(e),
        )
        yield TaskDoneEvent(task_id=task_id, final_state=TaskState.FAILED)
```

### Sub-Agent Configuration

```python
def _build_sub_agent_config(
    self,
    skill: Skill,
    parent_context: ExecutionContext,
) -> AutonomousConfig:
    """Build configuration for sub-agent execution."""

    # Sub-agents get reduced iteration budget
    budget_multiplier = 0.5 ** (parent_context.depth + 1)
    max_iterations = max(3, int(self._default_config.max_iterations * budget_multiplier))

    return AutonomousConfig(
        max_iterations=max_iterations,
        max_retries_per_tool=self._default_config.max_retries_per_tool,
        model=skill.metadata.model or self._default_config.model,
        enable_error_recovery=True,
    )
```

### Result Summarization

```python
def _summarize_sub_agent_result(self, result: ExecutionResult) -> str:
    """Create summary of sub-agent execution for parent."""
    if result.success:
        # Truncate to first 500 chars
        summary = result.result[:500]
        if len(result.result) > 500:
            summary += "... (truncated)"
        return summary
    else:
        return f"Failed: {result.error or 'Unknown error'}"
```

### Isolated System Prompt

Sub-agent's system prompt should NOT include parent conversation:
```python
def _build_isolated_system_prompt(self, skill: Skill) -> str:
    """Build system prompt for isolated sub-agent execution."""
    return f"""
You are a sub-agent executing the '{skill.metadata.name}' skill.

SKILL INSTRUCTIONS:
{skill.content}

AVAILABLE TOOLS:
{self._format_tools(skill.metadata.allowed_tools)}

Execute the task autonomously and report results when complete.
"""
```

## Acceptance Criteria

- [ ] Skills with `context: fork` create sub-agent
- [ ] Sub-agent runs in isolation (no parent context)
- [ ] Depth limit respected (error if exceeded)
- [ ] Iteration budget reduced for sub-agents
- [ ] Parent receives summary (not full output)
- [ ] Full trace available via chain_id reference
- [ ] Sub-agent uses skill's allowed_tools
- [ ] Error handling for sub-agent failures
- [ ] Logging for sub-agent spawn/completion

## Testing

```python
async def test_forked_context_spawns_sub_agent():
    """Skills with context: fork should spawn sub-agent."""
    skill = create_skill_with_fork_context()
    events = [e async for e in orchestrator.execute("fork-skill", "analyze code")]

    # Should have sub-agent spawn message
    assert any("sub-agent" in str(e) for e in events)

async def test_sub_agent_isolation():
    """Sub-agent should not have access to parent context."""
    # Verify sub-agent system prompt doesn't include parent conversation

async def test_sub_agent_reduced_budget():
    """Sub-agents should have reduced iteration budget."""
    config = orchestrator._build_sub_agent_config(skill, context)
    assert config.max_iterations < orchestrator._default_config.max_iterations

async def test_sub_agent_result_summarized():
    """Parent should receive summarized result."""
    events = [e async for e in orchestrator.execute("fork-skill", "analyze")]
    # Verify result is summarized, not full output
```

## Technical Notes

- Sub-agents use `execute_sync` to collect result (not streaming to parent)
- Parent can optionally stream sub-agent events if needed
- Consider adding `include_sub_agent_events: bool` option
- Sub-agent trace should be queryable via chain_id
- Log sub-agent metrics separately for cost tracking
