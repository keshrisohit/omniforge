# TASK-023: Update API documentation

**Priority:** P1 (Should Have)
**Estimated Effort:** Small (<1 day)
**Dependencies:** TASK-019

---

## Description

Update the API documentation to cover all new autonomous skill execution classes, methods, and configuration options. Generate docstrings for all public APIs and create reference documentation.

## Files to Modify

- `docs/api/skills.md` - Skills API reference
- `docs/api/configuration.md` - Configuration reference
- Source files - Ensure docstrings are complete

## Documentation Requirements

### API Reference Structure

```markdown
# Skills API Reference

## AutonomousSkillExecutor

The primary execution engine for autonomous skill execution using the ReAct pattern.

### Constructor

```python
AutonomousSkillExecutor(
    skill: Skill,
    tool_registry: ToolRegistry,
    tool_executor: ToolExecutor,
    config: Optional[AutonomousConfig] = None,
    context_loader: Optional[ContextLoader] = None,
    dynamic_injector: Optional[DynamicInjector] = None,
    string_substitutor: Optional[StringSubstitutor] = None,
) -> None
```

**Parameters:**
- `skill` - The Skill object to execute
- `tool_registry` - Registry of available tools
- `tool_executor` - Executor for tool calls
- `config` - Optional execution configuration
- `context_loader` - Optional custom context loader
- `dynamic_injector` - Optional custom dynamic injector
- `string_substitutor` - Optional custom string substitutor

### Methods

#### execute()

```python
async def execute(
    user_request: str,
    task_id: str = "default",
    session_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
) -> AsyncIterator[TaskEvent]
```

Execute the skill autonomously and stream events.

**Parameters:**
- `user_request` - User's request/task description
- `task_id` - Task identifier for tracking
- `session_id` - Optional session ID for variable substitution
- `tenant_id` - Optional tenant ID for multi-tenancy

**Yields:**
- `TaskEvent` instances for streaming progress

**Example:**
```python
executor = AutonomousSkillExecutor(skill, registry, tool_executor)
async for event in executor.execute("Process data.csv"):
    if isinstance(event, TaskMessageEvent):
        print(event.message_parts)
    elif isinstance(event, TaskDoneEvent):
        print(f"Completed: {event.final_state}")
```

#### execute_sync()

```python
async def execute_sync(
    user_request: str,
    task_id: str = "default",
    session_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
) -> ExecutionResult
```

Execute synchronously and return result (non-streaming).

**Returns:**
- `ExecutionResult` with final outcome

---

## SkillOrchestrator

Orchestrates skill execution with mode-based routing.

### Methods

#### execute()

```python
async def execute(
    skill_name: str,
    user_request: str,
    task_id: str = "default",
    session_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    execution_mode_override: Optional[ExecutionMode] = None,
) -> AsyncIterator[TaskEvent]
```

Execute a skill by name with automatic mode routing.

---

## ContextLoader

Loads and manages skill context with progressive loading.

### Methods

#### load_initial_context()

```python
def load_initial_context() -> LoadedContext
```

Load initial context from SKILL.md only.

**Returns:**
- `LoadedContext` with skill content and available file references

---

## DynamicInjector

Injects command output into skill content before execution.

### Methods

#### process()

```python
async def process(
    content: str,
    task_id: str = "injection",
    working_dir: Optional[str] = None,
) -> InjectedContent
```

Process content and replace !`command` placeholders.

---

## StringSubstitutor

Substitutes variables in skill content.

### Methods

#### substitute()

```python
def substitute(
    content: str,
    context: SubstitutionContext,
    auto_append_arguments: bool = True,
) -> SubstitutedContent
```

Substitute variables in content.

---

## Configuration Classes

### AutonomousConfig

```python
@dataclass
class AutonomousConfig:
    max_iterations: int = 15
    max_retries_per_tool: int = 3
    timeout_per_iteration_ms: int = 30000
    early_termination: bool = True
    model: Optional[str] = None
    temperature: float = 0.0
    enable_error_recovery: bool = True
```

### ExecutionState

```python
@dataclass
class ExecutionState:
    iteration: int = 0
    observations: list[dict]
    failed_approaches: dict[str, int]
    loaded_files: set[str]
    partial_results: list[str]
    error_count: int = 0
    start_time: datetime
```

### ExecutionResult

```python
@dataclass
class ExecutionResult:
    success: bool
    result: str
    iterations_used: int
    chain_id: str
    metrics: dict
    partial_results: list[str]
    error: Optional[str] = None
```

---

## Enums

### ExecutionMode

```python
class ExecutionMode(str, Enum):
    AUTONOMOUS = "autonomous"
    SIMPLE = "simple"
```

### VisibilityLevel

```python
class VisibilityLevel(str, Enum):
    FULL = "full"
    SUMMARY = "summary"
    HIDDEN = "hidden"
```
```

### Docstring Requirements

All public classes and methods should have docstrings:

```python
class AutonomousSkillExecutor:
    """Executes skills autonomously using ReAct pattern.

    The executor:
    1. Preprocesses skill content (context injection, variable substitution)
    2. Builds system prompt with available tools and files
    3. Runs ReAct loop: Think -> Act -> Observe -> repeat
    4. Handles errors with automatic recovery and alternative approaches
    5. Emits streaming events for real-time progress updates

    Example:
        >>> executor = AutonomousSkillExecutor(
        ...     skill=skill,
        ...     tool_registry=registry,
        ...     tool_executor=tool_executor,
        ... )
        >>> async for event in executor.execute("Process data.csv"):
        ...     print(event)

    Attributes:
        skill: The skill being executed
        config: Execution configuration

    See Also:
        SkillOrchestrator: For high-level skill routing
        ExecutionResult: For execution results
    """
```

## Acceptance Criteria

- [ ] All public classes documented
- [ ] All public methods documented with parameters/returns
- [ ] Code examples for major APIs
- [ ] Configuration reference complete
- [ ] Docstrings in source code complete
- [ ] API docs can be generated with sphinx/mkdocs
- [ ] Links between related classes

## Technical Notes

- Use Google-style docstrings
- Include type hints in signatures
- Provide realistic code examples
- Cross-reference related classes
- Document exceptions raised
- Consider auto-generating from docstrings with sphinx
