# TASK-013: Implement streaming events with visibility filtering

**Priority:** P1 (Should Have)
**Estimated Effort:** Medium (1-3 days)
**Dependencies:** TASK-005, TASK-012

---

## Description

Implement streaming events (FR-7) with visibility filtering (FR-4) for autonomous skill execution. Events are emitted in real-time and filtered based on user role (END_USER, DEVELOPER, ADMIN) and tool type. Integrate with existing `VisibilityController` and `TaskEvent` system.

## Files to Modify

- `src/omniforge/skills/autonomous_executor.py` - Add detailed event emission
- `src/omniforge/skills/orchestrator.py` - Add visibility filtering

## Implementation Requirements

### Visibility Levels

```python
class VisibilityLevel(str, Enum):
    FULL = "full"       # Every thought, tool call, result
    SUMMARY = "summary" # High-level progress milestones
    HIDDEN = "hidden"   # Completely hidden
```

### Event Types and When to Emit

| Event | Visibility | When Emitted |
|-------|------------|--------------|
| TaskStatusEvent | SUMMARY | Start, state changes |
| Iteration start | FULL | Beginning of each iteration |
| Thought/Reasoning | FULL | LLM reasoning text |
| Tool call | SUMMARY/FULL | Before tool execution |
| Tool result | FULL | After tool execution |
| Progress update | SUMMARY | Meaningful milestones |
| Error | SUMMARY | Errors encountered |
| TaskDoneEvent | SUMMARY | Completion |

### Event Emission in ReAct Loop

```python
async def execute(self, ...):
    for iteration in range(max_iterations):
        # Emit iteration start (FULL)
        yield TaskMessageEvent(
            task_id=task_id,
            message_parts=[TextPart(text=f"Iteration {iteration + 1}/{max_iterations}")],
            visibility=VisibilityLevel.FULL,
        )

        # Think phase - emit reasoning (FULL)
        yield TaskMessageEvent(
            message_parts=[TextPart(text=f"Thought: {parsed.thought}")],
            visibility=VisibilityLevel.FULL,
        )

        # Act phase - emit tool call (SUMMARY for name, FULL for details)
        if parsed.action:
            yield TaskMessageEvent(
                message_parts=[TextPart(text=f"Using tool: {parsed.action}")],
                visibility=VisibilityLevel.SUMMARY,
            )
            yield TaskMessageEvent(
                message_parts=[TextPart(text=f"Arguments: {parsed.action_input}")],
                visibility=VisibilityLevel.FULL,
            )

            # Execute tool
            result = await self._tool_executor.execute_tool(...)

            # Observe phase - emit result (FULL)
            yield TaskMessageEvent(
                message_parts=[TextPart(text=f"Result: {result.output[:500]}")],
                visibility=VisibilityLevel.FULL,
            )
```

### Visibility Filtering in Orchestrator

```python
async def execute(self, ..., user_role: Optional[str] = None):
    """Execute with visibility filtering based on role."""
    visibility_config = self._get_visibility_config(user_role)

    async for event in executor.execute(...):
        if self._should_emit_event(event, visibility_config):
            yield self._filter_sensitive_data(event)

def _should_emit_event(
    self,
    event: TaskEvent,
    config: VisibilityConfig,
) -> bool:
    """Check if event should be emitted based on visibility rules."""
    if not hasattr(event, 'visibility'):
        return True  # Always emit events without visibility

    event_visibility = event.visibility
    user_level = config.level

    if event_visibility == VisibilityLevel.FULL:
        return user_level == VisibilityLevel.FULL
    elif event_visibility == VisibilityLevel.SUMMARY:
        return user_level in [VisibilityLevel.FULL, VisibilityLevel.SUMMARY]
    else:
        return False  # HIDDEN events never emitted
```

### Sensitive Data Filtering

```python
SENSITIVE_PATTERNS = ["password", "api_key", "token", "secret", "credential"]

def _filter_sensitive_data(self, event: TaskEvent) -> TaskEvent:
    """Redact sensitive data from event content."""
    if isinstance(event, TaskMessageEvent):
        filtered_parts = []
        for part in event.message_parts:
            if isinstance(part, TextPart):
                filtered_text = self._redact_sensitive(part.text)
                filtered_parts.append(TextPart(text=filtered_text))
            else:
                filtered_parts.append(part)
        return TaskMessageEvent(..., message_parts=filtered_parts)
    return event

def _redact_sensitive(self, text: str) -> str:
    """Redact sensitive values from text."""
    for pattern in SENSITIVE_PATTERNS:
        # Match pattern: "api_key": "value" or api_key=value
        text = re.sub(
            rf'({pattern}\s*[=:]\s*)["\']?[^"\'\s,}}]+["\']?',
            r'\1[REDACTED]',
            text,
            flags=re.IGNORECASE
        )
    return text
```

### Role-Based Visibility Config

```python
DEFAULT_VISIBILITY_BY_ROLE = {
    "END_USER": VisibilityLevel.SUMMARY,
    "DEVELOPER": VisibilityLevel.FULL,
    "ADMIN": VisibilityLevel.FULL,
}

def _get_visibility_config(self, user_role: Optional[str]) -> VisibilityConfig:
    """Get visibility configuration for user role."""
    level = DEFAULT_VISIBILITY_BY_ROLE.get(user_role, VisibilityLevel.SUMMARY)
    return VisibilityConfig(level=level)
```

## Acceptance Criteria

- [ ] Events emitted at appropriate points in ReAct loop
- [ ] Events include visibility level
- [ ] Role-based filtering works (END_USER sees SUMMARY, DEVELOPER sees FULL)
- [ ] Sensitive data automatically redacted
- [ ] Progress percentage calculated and included
- [ ] Events stream in real-time (not buffered)
- [ ] Integration with existing VisibilityController
- [ ] Unit tests for filtering logic

## Testing

```python
async def test_events_have_visibility_levels():
    """All events should have visibility level."""
    events = [e async for e in executor.execute("test")]
    for event in events:
        if isinstance(event, TaskMessageEvent):
            assert hasattr(event, 'visibility')

async def test_end_user_sees_summary_only():
    """END_USER role should only see SUMMARY events."""
    events = [e async for e in orchestrator.execute(..., user_role="END_USER")]
    for event in events:
        if hasattr(event, 'visibility'):
            assert event.visibility != VisibilityLevel.FULL

async def test_developer_sees_all_events():
    """DEVELOPER role should see FULL events."""
    events = [e async for e in orchestrator.execute(..., user_role="DEVELOPER")]
    # Should include detailed tool arguments, results, etc.

def test_sensitive_data_redacted():
    """Sensitive patterns should be redacted."""
    text = 'api_key="sk-12345" password: secret123'
    filtered = orchestrator._redact_sensitive(text)
    assert "sk-12345" not in filtered
    assert "secret123" not in filtered
    assert "[REDACTED]" in filtered
```

## Technical Notes

- Use existing TaskEvent types from `omniforge.agents.events`
- Consider using existing VisibilityController if available
- Event buffering should be minimal for real-time streaming
- Progress percentage: `(iteration / max_iterations) * 100`
- Consider tool-type-based visibility (e.g., DATABASE queries always HIDDEN)
