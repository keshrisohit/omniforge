# Skills API Reference

This document provides comprehensive API documentation for the OmniForge autonomous skill execution system.

## Table of Contents

1. [Overview](#overview)
2. [AutonomousSkillExecutor](#autonomousskillexecutor)
3. [SkillOrchestrator](#skillorchestrator)
4. [ContextLoader](#contextloader)
5. [StringSubstitutor](#stringsubstitutor)
6. [Configuration Classes](#configuration-classes)
7. [Common Patterns and Examples](#common-patterns-and-examples)

---

## Overview

The autonomous skill execution system implements the ReAct (Reason-Act-Observe) pattern for executing skills. The system consists of several key components:

- **AutonomousSkillExecutor**: Core execution engine implementing the ReAct loop
- **SkillOrchestrator**: High-level router for managing skill execution modes
- **ContextLoader**: Progressive loading of supporting files
- **StringSubstitutor**: Variable substitution in skill content
- **Configuration Classes**: Models for execution configuration and state

### Architecture

```
User Request
     ↓
SkillOrchestrator (routing)
     ↓
AutonomousSkillExecutor (ReAct loop)
     ↓
  Preprocessing:
  - ContextLoader (load supporting files)
  - StringSubstitutor (replace variables)
     ↓
  ReAct Loop:
  1. Reason (LLM analyzes state)
  2. Act (execute tool)
  3. Observe (capture result)
  4. Repeat until complete
     ↓
TaskEvent Stream (real-time progress)
```

---

## AutonomousSkillExecutor

The primary execution engine for autonomous skill execution using the ReAct pattern.

### Class Definition

```python
class AutonomousSkillExecutor:
    """Autonomous skill executor implementing the ReAct loop pattern.

    This class orchestrates the preprocessing pipeline, builds system prompts,
    runs the ReAct loop, and emits streaming events for real-time progress visibility.

    The ReAct loop follows this pattern:
    1. Reason: LLM analyzes current state and decides on action
    2. Act: Execute the chosen tool with appropriate arguments
    3. Observe: Capture tool output and add to conversation context
    4. Repeat until task complete or max iterations reached
    """
```

### Constructor

```python
def __init__(
    self,
    skill: Skill,
    tool_registry: ToolRegistry,
    tool_executor: ToolExecutor,
    config: Optional[AutonomousConfig] = None,
    context: Optional[ExecutionContext] = None,
    context_loader: Optional[ContextLoader] = None,
    string_substitutor: Optional[StringSubstitutor] = None,
) -> None
```

**Parameters:**
- `skill` (Skill): The skill definition with instructions and metadata
- `tool_registry` (ToolRegistry): Registry of available tools
- `tool_executor` (ToolExecutor): Executor for running tools
- `config` (Optional[AutonomousConfig]): Execution configuration parameters (uses defaults if not provided)
- `context` (Optional[ExecutionContext]): Execution context for depth tracking (uses defaults if not provided)
- `context_loader` (Optional[ContextLoader]): Optional loader for supporting files
- `string_substitutor` (Optional[StringSubstitutor]): Optional substitutor for variable replacement

**Example:**
```python
from omniforge.skills.autonomous_executor import AutonomousSkillExecutor
from omniforge.skills.config import AutonomousConfig
from omniforge.skills.loader import SkillLoader
from omniforge.tools.registry import ToolRegistry
from omniforge.tools.executor import ToolExecutor

# Load skill
loader = SkillLoader(skills_dir="/path/to/skills")
skill = loader.load_skill("data-processor")

# Create registry and executor
registry = ToolRegistry()
registry.register_defaults()
tool_executor = ToolExecutor(registry)

# Create executor with custom config
config = AutonomousConfig(
    max_iterations=20,
    max_retries_per_tool=3,
    temperature=0.0,
)

executor = AutonomousSkillExecutor(
    skill=skill,
    tool_registry=registry,
    tool_executor=tool_executor,
    config=config,
)
```

### Methods

#### execute()

Execute skill autonomously with streaming events.

```python
async def execute(
    self,
    user_request: str,
    task_id: str,
    session_id: str,
    tenant_id: Optional[str] = None,
) -> AsyncIterator[TaskEvent]
```

**Parameters:**
- `user_request` (str): User's request/task description
- `task_id` (str): Unique task identifier
- `session_id` (str): Session identifier for this execution
- `tenant_id` (Optional[str]): Optional tenant identifier for multi-tenancy

**Yields:**
- `TaskEvent`: Instances (status, message, error, done) throughout execution

**Example:**
```python
# Execute skill with streaming
async for event in executor.execute(
    user_request="Process data.csv and generate summary",
    task_id="task-123",
    session_id="session-1",
):
    if isinstance(event, TaskMessageEvent):
        # Display progress messages
        for part in event.message_parts:
            if isinstance(part, TextPart):
                print(f"Progress: {part.text}")

    elif isinstance(event, TaskStatusEvent):
        print(f"Status: {event.state} - {event.message}")

    elif isinstance(event, TaskErrorEvent):
        print(f"Error: {event.error_message}")

    elif isinstance(event, TaskDoneEvent):
        print(f"Completed with state: {event.final_state}")
```

#### execute_sync()

Execute skill and return final result (non-streaming).

```python
async def execute_sync(
    self,
    user_request: str,
    task_id: str,
    session_id: str,
    tenant_id: Optional[str] = None,
) -> ExecutionResult
```

**Parameters:**
- `user_request` (str): User's request/task description
- `task_id` (str): Unique task identifier
- `session_id` (str): Session identifier for this execution
- `tenant_id` (Optional[str]): Optional tenant identifier for multi-tenancy

**Returns:**
- `ExecutionResult`: Final execution result with success status, result text, and metrics

**Example:**
```python
# Execute synchronously and get final result
result = await executor.execute_sync(
    user_request="Process data.csv",
    task_id="task-123",
    session_id="session-1",
)

if result.success:
    print(f"Result: {result.result}")
    print(f"Iterations: {result.iterations_used}")
    print(f"Duration: {result.metrics.duration_seconds}s")
    print(f"Cost: ${result.metrics.total_cost}")
else:
    print(f"Error: {result.error}")
    if result.partial_results:
        print(f"Partial results: {result.partial_results}")
```

---

## SkillOrchestrator

Orchestrator for routing skill execution to appropriate executors based on execution mode.

### Class Definition

```python
class SkillOrchestrator:
    """Orchestrator for routing skill execution to appropriate executors.

    This class is the main entry point for skill execution. It:
    1. Loads skills via SkillLoader
    2. Determines execution mode (autonomous vs simple)
    3. Handles forked context (sub-agent spawning)
    4. Routes to appropriate executor
    5. Manages skill context activation/deactivation
    """
```

### Constructor

```python
def __init__(
    self,
    skill_loader: SkillLoader,
    tool_registry: ToolRegistry,
    tool_executor: ToolExecutor,
    default_config: Optional[AutonomousConfig] = None,
) -> None
```

**Parameters:**
- `skill_loader` (SkillLoader): Loader for discovering and loading skills
- `tool_registry` (ToolRegistry): Registry of available tools
- `tool_executor` (ToolExecutor): Executor for running tools
- `default_config` (Optional[AutonomousConfig]): Default configuration for autonomous execution

**Example:**
```python
from omniforge.skills.orchestrator import SkillOrchestrator
from omniforge.skills.loader import SkillLoader
from omniforge.skills.config import AutonomousConfig
from omniforge.tools.registry import ToolRegistry
from omniforge.tools.executor import ToolExecutor

# Create components
loader = SkillLoader(skills_dir="/path/to/skills")
registry = ToolRegistry()
registry.register_defaults()
tool_executor = ToolExecutor(registry)

# Create orchestrator with default config
default_config = AutonomousConfig(
    max_iterations=15,
    temperature=0.0,
)

orchestrator = SkillOrchestrator(
    skill_loader=loader,
    tool_registry=registry,
    tool_executor=tool_executor,
    default_config=default_config,
)
```

### Methods

#### execute()

Execute a skill by name with automatic mode routing.

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
) -> AsyncIterator[TaskEvent]
```

**Parameters:**
- `skill_name` (str): Name of the skill to execute
- `user_request` (str): User's request/task description
- `task_id` (str): Unique task identifier (default: "default")
- `session_id` (Optional[str]): Session identifier for this execution
- `tenant_id` (Optional[str]): Tenant identifier for multi-tenancy
- `execution_mode_override` (Optional[ExecutionMode]): Override for execution mode
- `context` (Optional[ExecutionContext]): Execution context for depth tracking

**Yields:**
- `TaskEvent`: Instances for progress updates

**Raises:**
- `SkillNotFoundError`: If skill is not found in the skill loader

**Example:**
```python
# Execute skill by name
async for event in orchestrator.execute(
    skill_name="data-processor",
    user_request="Process sales.csv and generate report",
    task_id="task-456",
):
    if isinstance(event, TaskMessageEvent):
        print(f"Progress: {event.message_parts[0].text}")

# Override execution mode
from omniforge.skills.orchestrator import ExecutionMode

async for event in orchestrator.execute(
    skill_name="simple-calculator",
    user_request="Calculate 2 + 2",
    execution_mode_override=ExecutionMode.SIMPLE,
):
    if isinstance(event, TaskDoneEvent):
        print(f"Completed: {event.final_state}")
```

---

## ContextLoader

Progressive context loader for skill supporting files.

### Class Definition

```python
class ContextLoader:
    """Loader for progressive context loading of skill supporting files.

    Parses SKILL.md for references to supporting files and manages on-demand loading.
    Only SKILL.md content is loaded initially; supporting files are loaded on-demand
    via the `read` tool during execution.

    Supported file reference patterns:
    1. "See reference.md for API documentation (1,200 lines)"
    2. "- reference.md: Description"
    3. "**reference.md**: Description (300 lines)"
    4. "Read examples.md for usage patterns"
    5. "Check templates/report.md"
    """
```

### Constructor

```python
def __init__(self, skill: Skill) -> None
```

**Parameters:**
- `skill` (Skill): The skill to load context for

### Methods

#### load_initial_context()

Load initial context with SKILL.md content and available file references.

```python
def load_initial_context(self) -> LoadedContext
```

**Returns:**
- `LoadedContext`: Object with skill content and available file references

**Example:**
```python
from omniforge.skills.context_loader import ContextLoader

# Create loader for a skill
loader = ContextLoader(skill)

# Load initial context
context = loader.load_initial_context()

print(f"Skill content lines: {context.line_count}")
print(f"Available files: {list(context.available_files.keys())}")

# Access file references
for filename, file_ref in context.available_files.items():
    print(f"  {filename}: {file_ref.description}")
    if file_ref.estimated_lines:
        print(f"    Estimated lines: {file_ref.estimated_lines}")
```

#### build_available_files_prompt()

Build formatted prompt section for available supporting files.

```python
def build_available_files_prompt(self, context: LoadedContext) -> str
```

**Parameters:**
- `context` (LoadedContext): The loaded context with available files

**Returns:**
- `str`: Formatted string for system prompt

**Example:**
```python
context = loader.load_initial_context()
files_section = loader.build_available_files_prompt(context)

# Use in system prompt
system_prompt = f"""
{skill_instructions}

{files_section}

Use the `read` tool to load files on-demand when needed.
"""
```

---

## StringSubstitutor

Substitutes variables in skill content before execution.

### Class Definition

```python
class StringSubstitutor:
    """Substitutes variables in skill content before execution.

    Replaces standard variables ($ARGUMENTS, ${CLAUDE_SESSION_ID}, etc.) and custom
    variables in skill content. Auto-appends arguments if not present in content.
    """
```

### Methods

#### substitute()

Substitute variables in content with values from context.

```python
def substitute(
    self,
    content: str,
    context: SubstitutionContext,
    auto_append_arguments: bool = True,
) -> SubstitutedContent
```

**Parameters:**
- `content` (str): Skill content with variables to replace
- `context` (SubstitutionContext): Context containing variable values
- `auto_append_arguments` (bool): If True and $ARGUMENTS not in content, append arguments

**Returns:**
- `SubstitutedContent`: Result with replaced content and metadata

**Example:**
```python
from omniforge.skills.string_substitutor import StringSubstitutor, SubstitutionContext

# Create substitutor
substitutor = StringSubstitutor()

# Build context
context = SubstitutionContext(
    arguments="data.csv",
    session_id="session-123",
    skill_dir="/path/to/skill",
    workspace="/path/to/workspace",
    user="john",
    date="2026-01-30",
)

# Substitute variables
skill_content = """
Process the file: $ARGUMENTS
Skill directory: ${SKILL_DIR}
Session: ${CLAUDE_SESSION_ID}
"""

result = substitutor.substitute(skill_content, context)

print(result.content)
# Output:
# Process the file: data.csv
# Skill directory: /path/to/skill
# Session: session-123

print(f"Substitutions made: {result.substitutions_made}")
print(f"Undefined variables: {result.undefined_vars}")
```

#### build_context()

Build substitution context with defaults for unspecified values.

```python
def build_context(
    self,
    arguments: str = "",
    session_id: Optional[str] = None,
    skill_dir: str = "",
    workspace: Optional[str] = None,
    user: Optional[str] = None,
    date: Optional[str] = None,
    custom_vars: Optional[dict[str, str]] = None,
) -> SubstitutionContext
```

**Parameters:**
- `arguments` (str): User-provided arguments (default: "")
- `session_id` (Optional[str]): Unique session ID (auto-generated if None)
- `skill_dir` (str): Absolute path to skill directory (default: "")
- `workspace` (Optional[str]): Working directory (default: current directory)
- `user` (Optional[str]): Current user name (default: from USER env var)
- `date` (Optional[str]): Current date (default: today in YYYY-MM-DD format)
- `custom_vars` (Optional[dict[str, str]]): Additional custom variables

**Returns:**
- `SubstitutionContext`: Context with all values populated

**Example:**
```python
# Build context with defaults
context = substitutor.build_context(
    arguments="process data",
    skill_dir="/path/to/skill",
    custom_vars={"PROJECT": "sales-analysis"},
)

# Use context for substitution
result = substitutor.substitute(content, context)
```

---

## Configuration Classes

### AutonomousConfig

Configuration for autonomous skill execution.

```python
@dataclass
class AutonomousConfig:
    """Configuration for autonomous skill execution.

    Attributes:
        max_iterations: Maximum ReAct loop iterations (1-100, default: 15)
        max_retries_per_tool: Max retries per tool/approach (1-10, default: 3)
        timeout_per_iteration_ms: Timeout per iteration in milliseconds (1000-300000, default: 30000)
        early_termination: Allow early termination when goal is reached (default: True)
        model: Optional LLM model override for skill execution
        temperature: LLM temperature for generation (0.0-2.0, default: 0.0)
        enable_error_recovery: Enable automatic error recovery mechanisms (default: True)
    """
    max_iterations: int = 15
    max_retries_per_tool: int = 3
    timeout_per_iteration_ms: int = 30000
    early_termination: bool = True
    model: Optional[str] = None
    temperature: float = 0.0
    enable_error_recovery: bool = True
```

**Example:**
```python
from omniforge.skills.config import AutonomousConfig

# Create custom config
config = AutonomousConfig(
    max_iterations=20,
    max_retries_per_tool=5,
    timeout_per_iteration_ms=60000,  # 60 seconds
    temperature=0.2,
    model="claude-sonnet-4",
)
```

### ExecutionContext

Context for tracking sub-agent execution depth and hierarchy.

```python
@dataclass
class ExecutionContext:
    """Context for tracking sub-agent execution depth and hierarchy.

    Attributes:
        depth: Current execution depth (0 = root, 1 = first sub-agent, etc.)
        max_depth: Maximum allowed depth for sub-agent spawning (default: 2)
        parent_task_id: Task ID of the parent that spawned this context
        root_task_id: Task ID of the root execution (top-level)
        skill_chain: List of skill names in the execution chain (for debugging)
    """
    depth: int = 0
    max_depth: int = 2
    parent_task_id: Optional[str] = None
    root_task_id: Optional[str] = None
    skill_chain: list[str] = field(default_factory=list)
```

**Example:**
```python
from omniforge.skills.config import ExecutionContext

# Create root context
root_context = ExecutionContext(max_depth=2)

# Create child context for sub-agent
child_context = root_context.create_child_context(
    task_id="child-task-123",
    skill_name="sub-skill",
)

# Check if can spawn another sub-agent
if child_context.can_spawn_sub_agent():
    print("Can spawn another level of sub-agents")

# Get iteration budget for child
budget = child_context.get_iteration_budget_for_child(base_iterations=15)
print(f"Child iteration budget: {budget}")
```

### ExecutionState

Runtime state tracking for autonomous skill execution.

```python
@dataclass
class ExecutionState:
    """Runtime state tracking for autonomous skill execution.

    Attributes:
        iteration: Current iteration number (0-indexed)
        observations: List of tool call observations/results
        failed_approaches: Mapping of failed approaches to retry counts
        loaded_files: Set of supporting files loaded on-demand
        partial_results: Accumulated partial results from iterations
        error_count: Total number of errors encountered
        start_time: Execution start timestamp
    """
    iteration: int = 0
    observations: list[dict] = field(default_factory=list)
    failed_approaches: dict[str, int] = field(default_factory=dict)
    loaded_files: set[str] = field(default_factory=set)
    partial_results: list[str] = field(default_factory=list)
    error_count: int = 0
    start_time: datetime = field(default_factory=datetime.utcnow)
```

### ExecutionResult

Final result wrapper for autonomous skill execution.

```python
@dataclass
class ExecutionResult:
    """Final result wrapper for autonomous skill execution.

    Attributes:
        success: Whether execution completed successfully
        result: Final result text/output
        iterations_used: Number of iterations executed
        chain_id: Reasoning chain ID for debugging and tracing
        metrics: Detailed execution metrics
        partial_results: Partial results if execution incomplete
        error: Error message if execution failed
    """
    success: bool
    result: str
    iterations_used: int
    chain_id: str
    metrics: ExecutionMetrics
    partial_results: list[str] = field(default_factory=list)
    error: Optional[str] = None
```

### ExecutionMetrics

Detailed metrics for autonomous skill execution.

```python
@dataclass
class ExecutionMetrics:
    """Detailed metrics for autonomous skill execution.

    Attributes:
        total_tokens: Total tokens consumed across all LLM calls
        prompt_tokens: Tokens used in prompts
        completion_tokens: Tokens used in completions
        total_cost: Total cost in USD
        duration_seconds: Total execution duration in seconds
        tool_calls_successful: Number of successful tool calls
        tool_calls_failed: Number of failed tool calls
        error_recoveries: Number of successful error recoveries
        model_used: LLM model used for execution
        estimated_cost_per_call: Estimated cost per LLM call based on model
    """
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_cost: float = 0.0
    duration_seconds: float = 0.0
    tool_calls_successful: int = 0
    tool_calls_failed: int = 0
    error_recoveries: int = 0
    model_used: Optional[str] = None
    estimated_cost_per_call: float = 0.0
```

### ExecutionMode

Execution mode enumeration for skill routing.

```python
class ExecutionMode(str, Enum):
    """Execution mode for skill routing.

    Attributes:
        AUTONOMOUS: Use AutonomousSkillExecutor with ReAct loop
        SIMPLE: Use ExecutableSkill (legacy mode)
    """
    AUTONOMOUS = "autonomous"
    SIMPLE = "simple"
```

---

## Common Patterns and Examples

### Pattern 1: Basic Autonomous Execution

Execute a skill autonomously with streaming progress updates:

```python
from omniforge.skills.orchestrator import SkillOrchestrator
from omniforge.skills.loader import SkillLoader
from omniforge.tools.registry import ToolRegistry
from omniforge.tools.executor import ToolExecutor
from omniforge.agents.events import TaskMessageEvent, TaskDoneEvent

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

# Execute with streaming
async for event in orchestrator.execute(
    skill_name="data-processor",
    user_request="Process sales.csv and generate summary report",
    task_id="task-001",
):
    if isinstance(event, TaskMessageEvent):
        print(f"[PROGRESS] {event.message_parts[0].text}")
    elif isinstance(event, TaskDoneEvent):
        print(f"[DONE] Final state: {event.final_state}")
```

### Pattern 2: Custom Configuration

Execute with custom configuration for resource-intensive tasks:

```python
from omniforge.skills.config import AutonomousConfig

# Custom config for long-running task
config = AutonomousConfig(
    max_iterations=30,
    max_retries_per_tool=5,
    timeout_per_iteration_ms=120000,  # 2 minutes per iteration
    temperature=0.1,
    model="claude-opus-4",  # Use more powerful model
    enable_error_recovery=True,
)

orchestrator = SkillOrchestrator(
    skill_loader=loader,
    tool_registry=registry,
    tool_executor=tool_executor,
    default_config=config,
)
```

### Pattern 3: Multi-Tenant Execution

Execute skills with tenant isolation:

```python
# Execute for specific tenant
async for event in orchestrator.execute(
    skill_name="report-generator",
    user_request="Generate Q4 sales report",
    task_id=f"task-{tenant_id}-001",
    session_id=f"session-{user_id}",
    tenant_id=tenant_id,
):
    # Handle events with tenant context
    if isinstance(event, TaskMessageEvent):
        logger.info(f"[Tenant: {tenant_id}] {event.message_parts[0].text}")
```

### Pattern 4: Sub-Agent Execution

Execute skills with sub-agent spawning and depth tracking:

```python
from omniforge.skills.config import ExecutionContext

# Create root context
root_context = ExecutionContext(
    max_depth=2,  # Allow up to 2 levels of sub-agents
)

# Execute parent skill that may spawn sub-agents
async for event in orchestrator.execute(
    skill_name="complex-workflow",
    user_request="Analyze data and generate insights",
    task_id="root-task",
    context=root_context,
):
    # Parent skill can spawn sub-agents for subtasks
    # Depth tracking prevents infinite recursion
    pass
```

### Pattern 5: Error Handling and Recovery

Handle errors and partial results:

```python
from omniforge.agents.events import TaskErrorEvent

result = await executor.execute_sync(
    user_request="Process corrupted_data.csv",
    task_id="task-002",
    session_id="session-002",
)

if not result.success:
    print(f"Execution failed: {result.error}")

    # Check for partial results
    if result.partial_results:
        print(f"Partial results completed:")
        for partial in result.partial_results:
            print(f"  - {partial}")

    # Check metrics for debugging
    print(f"Iterations used: {result.iterations_used}")
    print(f"Errors encountered: {result.metrics.error_recoveries}")
else:
    print(f"Success: {result.result}")
```

### Pattern 6: Variable Substitution

Use variable substitution in skill content:

```python
from omniforge.skills.string_substitutor import StringSubstitutor, SubstitutionContext

substitutor = StringSubstitutor()

# Build context with custom variables
context = substitutor.build_context(
    arguments="Q4-2025-sales.csv",
    skill_dir="/skills/data-processor",
    custom_vars={
        "OUTPUT_DIR": "/output/reports",
        "FORMAT": "pdf",
    },
)

# Skill content can use variables:
# Process $ARGUMENTS and save to ${OUTPUT_DIR} in ${FORMAT} format

result = substitutor.substitute(skill_content, context)
print(result.content)
```

### Pattern 7: Progressive Context Loading

Load supporting files on-demand:

```python
from omniforge.skills.context_loader import ContextLoader

# Create loader
loader = ContextLoader(skill)

# Load initial context (SKILL.md only)
context = loader.load_initial_context()

# System prompt includes available files
print(f"Available supporting files: {list(context.available_files.keys())}")

# During execution, agent can use 'read' tool to load:
# - reference.md (API documentation)
# - examples.md (usage examples)
# - templates/report.md (report template)
```

### Pattern 8: Cost Tracking

Track execution costs and resource usage:

```python
result = await executor.execute_sync(
    user_request="Generate comprehensive analysis",
    task_id="task-003",
    session_id="session-003",
)

# Access detailed metrics
metrics = result.metrics
print(f"Model used: {metrics.model_used}")
print(f"Duration: {metrics.duration_seconds:.2f}s")
print(f"Total tokens: {metrics.total_tokens}")
print(f"Estimated cost: ${metrics.total_cost:.4f}")
print(f"Tool calls successful: {metrics.tool_calls_successful}")
print(f"Tool calls failed: {metrics.tool_calls_failed}")
print(f"Error recoveries: {metrics.error_recoveries}")
```

---

## See Also

- [Migration Guide](../migration/autonomous-execution.md) - Migrating from simple to autonomous execution
- [Event Streaming and Visibility](../event-streaming-visibility.md) - Understanding TaskEvent types
- [Tools API Reference](../tools/README.md) - Available tools for skill execution
- [Skill Development Guide](../../examples/README.md) - Creating custom skills

---

**Last Updated:** 2026-01-30
