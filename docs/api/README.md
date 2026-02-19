# OmniForge API Reference

Comprehensive API documentation for the OmniForge autonomous skill execution system.

## Documentation Structure

### [Skills API Reference](./skills.md)
Complete documentation for the autonomous skill execution engine:
- **AutonomousSkillExecutor** - Core ReAct loop execution engine
- **SkillOrchestrator** - High-level skill routing and mode selection
- **ContextLoader** - Progressive loading of supporting files
- **StringSubstitutor** - Variable substitution in skill content
- **Common Patterns** - Real-world usage examples

### [Configuration API Reference](./configuration.md)
Configuration classes and utilities:
- **AutonomousConfig** - Execution configuration parameters
- **ExecutionContext** - Sub-agent depth tracking
- **ExecutionState** - Runtime state tracking
- **ExecutionResult** - Final execution results
- **ExecutionMetrics** - Cost and performance metrics
- **PlatformAutonomousConfig** - Platform-wide configuration
- **Utility Functions** - Configuration helpers

## Quick Start

### Basic Execution

```python
from omniforge.skills.orchestrator import SkillOrchestrator
from omniforge.skills.loader import SkillLoader
from omniforge.tools.registry import ToolRegistry
from omniforge.tools.executor import ToolExecutor

# Setup
loader = SkillLoader(skills_dir="/path/to/skills")
registry = ToolRegistry()
registry.register_defaults()
tool_executor = ToolExecutor(registry)

orchestrator = SkillOrchestrator(
    skill_loader=loader,
    tool_registry=registry,
    tool_executor=tool_executor,
)

# Execute skill
async for event in orchestrator.execute(
    skill_name="data-processor",
    user_request="Process sales.csv",
    task_id="task-123",
):
    print(event)
```

### Custom Configuration

```python
from omniforge.skills.config import AutonomousConfig

config = AutonomousConfig(
    max_iterations=20,
    timeout_per_iteration_ms=60000,
    temperature=0.0,
    model="claude-sonnet-4",
)

orchestrator = SkillOrchestrator(
    skill_loader=loader,
    tool_registry=registry,
    tool_executor=tool_executor,
    default_config=config,
)
```

## Key Concepts

### ReAct Loop Pattern

The autonomous execution engine implements the ReAct (Reason-Act-Observe) pattern:

1. **Reason**: LLM analyzes current state and decides on action
2. **Act**: Execute the chosen tool with appropriate arguments
3. **Observe**: Capture tool output and add to conversation context
4. **Repeat**: Continue until task complete or max iterations reached

### Execution Modes

- **AUTONOMOUS**: Full ReAct loop with LLM reasoning and tool calls
- **SIMPLE**: Legacy mode for backward compatibility

### Progressive Context Loading

Supporting files are loaded on-demand to optimize token usage:
- Initial: SKILL.md content only
- On-demand: Supporting files via `read` tool during execution

### Variable Substitution

Standard variables available in skill content:
- `$ARGUMENTS` or `${ARGUMENTS}` - User's request
- `${CLAUDE_SESSION_ID}` or `${SESSION_ID}` - Session identifier
- `${SKILL_DIR}` - Absolute path to skill directory
- `${WORKSPACE}` - Current working directory
- `${USER}` - Current user name
- `${DATE}` - Current date (YYYY-MM-DD)

### Event Streaming

Real-time progress updates via TaskEvent stream:
- **TaskStatusEvent**: State changes (WORKING, COMPLETED, FAILED)
- **TaskMessageEvent**: Progress messages and results
- **TaskErrorEvent**: Error details with recovery suggestions
- **TaskDoneEvent**: Final state notification

## API Index

### Core Classes

- [AutonomousSkillExecutor](./skills.md#autonomousskillexecutor) - Primary execution engine
- [SkillOrchestrator](./skills.md#skillorchestrator) - Skill routing and orchestration
- [ContextLoader](./skills.md#contextloader) - Progressive file loading
- [StringSubstitutor](./skills.md#stringsubstitutor) - Variable substitution

### Configuration

- [AutonomousConfig](./configuration.md#autonomousconfig) - Execution parameters
- [ExecutionContext](./configuration.md#executioncontext) - Depth tracking
- [ExecutionState](./configuration.md#executionstate) - Runtime state
- [ExecutionResult](./configuration.md#executionresult) - Final results
- [ExecutionMetrics](./configuration.md#executionmetrics) - Performance metrics
- [PlatformAutonomousConfig](./configuration.md#platformautonomousconfig) - Platform config

### Data Models

- [FileReference](./skills.md#contextloader) - Supporting file metadata
- [LoadedContext](./skills.md#contextloader) - Loaded skill context
- [SubstitutionContext](./skills.md#stringsubstitutor) - Variable context
- [SubstitutedContent](./skills.md#stringsubstitutor) - Substitution results

### Enums

- [ExecutionMode](./skills.md#common-patterns-and-examples) - Execution mode selection
- [VisibilityLevel](../event-streaming-visibility.md) - Event visibility control
- [TaskState](../event-streaming-visibility.md) - Task state enumeration

### Utilities

- [parse_duration_ms()](./configuration.md#parse_duration_ms) - Parse duration strings
- [validate_skill_config()](./configuration.md#validate_skill_config) - Validate config
- [merge_configs()](./configuration.md#merge_configs) - Merge configurations

## Common Patterns

### Pattern 1: Streaming Execution
```python
async for event in orchestrator.execute(skill_name, user_request):
    if isinstance(event, TaskMessageEvent):
        print(f"Progress: {event.message_parts[0].text}")
```

### Pattern 2: Synchronous Execution
```python
result = await executor.execute_sync(user_request, task_id, session_id)
if result.success:
    print(f"Result: {result.result}")
```

### Pattern 3: Custom Configuration
```python
config = AutonomousConfig(max_iterations=30, model="claude-opus-4")
executor = AutonomousSkillExecutor(skill, registry, tool_executor, config)
```

### Pattern 4: Multi-Tenant Execution
```python
async for event in orchestrator.execute(
    skill_name, user_request, tenant_id=tenant_id
):
    # Handle tenant-specific execution
```

### Pattern 5: Error Handling
```python
result = await executor.execute_sync(...)
if not result.success and result.partial_results:
    print(f"Partial results: {result.partial_results}")
```

## Related Documentation

- [Migration Guide](../migration/autonomous-execution.md) - Migrating to autonomous execution
- [Event Streaming](../event-streaming-visibility.md) - Understanding TaskEvent types
- [Skill Development](../../examples/README.md) - Creating custom skills
- [Tools Reference](../tools/README.md) - Available tools for skills

## Version History

- **2026-01-30**: Initial API documentation for autonomous execution system
  - AutonomousSkillExecutor API
  - SkillOrchestrator API
  - Configuration classes
  - Preprocessing utilities
  - Common patterns and examples

---

**Last Updated:** 2026-01-30
