# Event Streaming with Visibility Filtering

**Implementation of TASK-013**

This document describes the event streaming system with progressive visibility disclosure for autonomous skill execution in OmniForge.

## Overview

The event streaming system allows real-time monitoring of autonomous skill execution with role-based visibility control. Different user roles see different levels of detail, from high-level progress summaries to detailed execution traces.

## Visibility Levels

Events can have three visibility levels:

- **FULL**: Detailed execution information (iterations, thoughts, tool arguments, observations)
- **SUMMARY**: High-level progress updates (tool calls, status changes, final answers)
- **HIDDEN**: Completely hidden from all users

## Role-Based Filtering

User roles determine which events are visible:

| Role | Visibility Level | Events Seen |
|------|-----------------|-------------|
| END_USER | SUMMARY | High-level progress only |
| DEVELOPER | FULL | All detailed execution events |
| ADMIN | FULL | All detailed execution events |

## Event Types with Visibility

### TaskStatusEvent (Default: SUMMARY)
Task state transitions (starting, working, completed).

```python
TaskStatusEvent(
    task_id="task-123",
    timestamp=datetime.utcnow(),
    state=TaskState.WORKING,
    message="Starting autonomous skill execution",
    visibility=VisibilityLevel.SUMMARY,
)
```

### TaskMessageEvent (Configurable)
Progress messages during execution.

```python
# SUMMARY visibility - High-level action
TaskMessageEvent(
    task_id="task-123",
    timestamp=datetime.utcnow(),
    message_parts=[TextPart(text="Action: read_file")],
    visibility=VisibilityLevel.SUMMARY,
)

# FULL visibility - Detailed iteration info
TaskMessageEvent(
    task_id="task-123",
    timestamp=datetime.utcnow(),
    message_parts=[TextPart(text="Iteration 1/15: Analyzing next step")],
    visibility=VisibilityLevel.FULL,
)
```

### TaskErrorEvent (Default: SUMMARY)
Error notifications.

```python
TaskErrorEvent(
    task_id="task-123",
    timestamp=datetime.utcnow(),
    error_code="TOOL_EXECUTION_ERROR",
    error_message="Failed to read file: not found",
    visibility=VisibilityLevel.SUMMARY,
)
```

## Usage

### Basic Event Streaming

```python
from omniforge.skills.autonomous_executor import AutonomousSkillExecutor

executor = AutonomousSkillExecutor(skill, tool_registry, tool_executor)

# Stream events with visibility levels
async for event in executor.execute("Process data.csv", "task-1", "session-1"):
    # All events now include visibility attribute
    print(f"Event: {event.type}, Visibility: {event.visibility}")
```

### Filtering Events by Role

```python
from omniforge.skills.event_filter import filter_event_stream

# Filter for END_USER (SUMMARY events only)
async for event in filter_event_stream(
    executor.execute("Process data.csv", "task-1", "session-1"),
    user_role="END_USER"
):
    # Only high-level progress events
    print(event)

# Filter for DEVELOPER (all events)
async for event in filter_event_stream(
    executor.execute("Process data.csv", "task-1", "session-1"),
    user_role="DEVELOPER"
):
    # Detailed execution trace
    print(event)
```

### Sensitive Data Redaction

The event filter automatically redacts sensitive data:

```python
# Sensitive patterns: password, api_key, token, secret, credential

# Original event:
TaskMessageEvent(
    message_parts=[TextPart(text='Using api_key="sk-12345" for authentication')]
)

# After filtering:
TaskMessageEvent(
    message_parts=[TextPart(text='Using api_key="[REDACTED]" for authentication')]
)
```

## Implementation Details

### Event Visibility Assignment in AutonomousSkillExecutor

Events are assigned visibility levels based on their content:

```python
# FULL visibility - Internal execution details
- Iteration progress: "Iteration 1/15: Analyzing next step"
- Reasoning thoughts: "Thought: Need to read the file first"
- Tool observations: "Observation: File contains 1000 rows"

# SUMMARY visibility - User-facing progress
- Tool actions: "Action: read_file"
- Final answers: "Final answer: Processed 1000 rows successfully"
- Status changes: "Starting autonomous skill execution"
- Errors: "Tool execution failed: file not found"
```

### EventFilter Class

The `EventFilter` class handles:
1. Role-based visibility filtering
2. Sensitive data redaction
3. Event metadata preservation

```python
from omniforge.skills.event_filter import EventFilter

filter = EventFilter(user_role="END_USER")

# Check if event should be emitted
if filter.should_emit_event(event):
    # Redact sensitive data
    filtered_event = filter.filter_sensitive_data(event)
    yield filtered_event
```

### Filtering Logic

```
Event Visibility Level | User Role | Emitted?
--------------------- | --------- | --------
HIDDEN               | Any       | No
SUMMARY              | END_USER  | Yes
SUMMARY              | DEVELOPER | Yes
SUMMARY              | ADMIN     | Yes
FULL                 | END_USER  | No
FULL                 | DEVELOPER | Yes
FULL                 | ADMIN     | Yes
```

## Testing

Comprehensive tests cover:
- Event visibility level assignment
- Role-based filtering
- Sensitive data redaction
- Integration with AutonomousSkillExecutor

```bash
# Run event filtering tests
pytest tests/skills/test_event_filter.py -v

# Run integration tests
pytest tests/skills/test_event_streaming_integration.py -v
```

## Architecture

```
┌─────────────────────────────┐
│  AutonomousSkillExecutor    │
│  - Emits events with        │
│    visibility levels        │
└──────────┬──────────────────┘
           │ TaskEvent stream
           ▼
┌─────────────────────────────┐
│  filter_event_stream()      │
│  - Role-based filtering     │
│  - Sensitive data redaction │
└──────────┬──────────────────┘
           │ Filtered events
           ▼
┌─────────────────────────────┐
│  Client (UI/API)            │
│  - Receives appropriate     │
│    events for user role     │
└─────────────────────────────┘
```

## Future Enhancements

Potential improvements:
1. Tool-type-based visibility (e.g., DATABASE queries always HIDDEN)
2. Custom visibility rules per skill
3. Real-time visibility level adjustment
4. Event aggregation for SUMMARY views
5. Progress percentage calculation

## References

- Implementation: `src/omniforge/skills/event_filter.py`
- Events: `src/omniforge/agents/events.py`
- Executor: `src/omniforge/skills/autonomous_executor.py`
- Tests: `tests/skills/test_event_filter.py`
- Integration Tests: `tests/skills/test_event_streaming_integration.py`
- Task Specification: `specs/tasks/autonomous-skill-execution/TASK-013-streaming-events.md`
