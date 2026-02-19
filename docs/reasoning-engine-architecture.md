# ReasoningEngine Architecture

A comprehensive guide to understanding how the ReasoningEngine works in OmniForge.

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Core Components](#core-components)
4. [Step-by-Step Execution Flow](#step-by-step-execution-flow)
5. [ReasoningChain Structure](#reasoningchain-structure)
6. [Tool Execution Flow](#tool-execution-flow)
7. [Examples](#examples)

---

## Overview

The **ReasoningEngine** is the heart of OmniForge's agent reasoning system. It provides a high-level API for agents to:
- 🧠 Record reasoning steps (thinking, tool calls, synthesis)
- 🔧 Execute tools through a unified interface
- 📊 Build chains of thought that can be inspected and audited
- 💰 Track costs and token usage
- 🔄 Stream reasoning steps in real-time

Think of it as a **"reasoning notebook"** where an agent writes down its thoughts, actions, and observations in a structured format.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                         Agent                                 │
│  (AutonomousCoTAgent, SimpleAgent, etc.)                     │
└────────────────────┬─────────────────────────────────────────┘
                     │ uses
                     ▼
┌──────────────────────────────────────────────────────────────┐
│                    ReasoningEngine                            │
│  ┌────────────────────────────────────────────────────┐     │
│  │  • add_thinking()     - Record thoughts            │     │
│  │  • add_synthesis()    - Record conclusions         │     │
│  │  • call_llm()         - Call LLM (convenience)     │     │
│  │  • call_tool()        - Execute any tool           │     │
│  │  • get_available_tools() - List tools              │     │
│  └────────────────────────────────────────────────────┘     │
│                                                               │
│  Manages:                                                     │
│  • ReasoningChain (sequence of steps)                        │
│  • ToolExecutor (for tool execution)                         │
│  • Task context (IDs, budgets, etc.)                         │
└────────────────────┬─────────────────────────────────────────┘
                     │
         ┌───────────┴────────────┐
         ▼                        ▼
┌─────────────────┐      ┌──────────────────┐
│ ReasoningChain  │      │  ToolExecutor    │
│                 │      │                  │
│ • steps: []     │      │ • Registry       │
│ • metrics       │      │ • Retry logic    │
│ • status        │      │ • Rate limiting  │
└─────────────────┘      └──────────────────┘
```

---

## Core Components

### 1. **ReasoningEngine**
**Location**: `src/omniforge/agents/cot/engine.py`

The main API that agents interact with.

```python
class ReasoningEngine:
    def __init__(
        self,
        chain: ReasoningChain,      # Where to record steps
        executor: ToolExecutor,      # How to execute tools
        task: dict[str, Any],        # Task context
        default_llm_model: str       # Default LLM to use
    ):
        self._chain = chain
        self._executor = executor
        self._task = task
        self._default_llm_model = default_llm_model
```

**Key Properties**:
- `chain`: The reasoning chain being built
- `task`: Task context (IDs, budgets, tenant info)

### 2. **ReasoningChain**
**Location**: `src/omniforge/agents/cot/chain.py`

A sequential record of all reasoning steps.

```python
class ReasoningChain(BaseModel):
    id: UUID                        # Chain identifier
    task_id: str                    # Associated task
    agent_id: str                   # Agent executing
    status: ChainStatus             # RUNNING | COMPLETED | FAILED
    steps: list[ReasoningStep]      # Sequential steps
    metrics: ChainMetrics           # Aggregated stats

    def add_step(self, step: ReasoningStep) -> None:
        # Auto-assigns step number
        # Updates metrics automatically
        ...
```

**Metrics Tracked**:
- Total steps
- LLM calls count
- Tool calls count
- Total tokens consumed
- Total cost (USD)

### 3. **ReasoningStep**
**Location**: `src/omniforge/agents/cot/chain.py`

A single step in the reasoning process.

```python
class ReasoningStep(BaseModel):
    id: UUID                        # Unique step ID
    step_number: int                # Sequential number
    type: StepType                  # THINKING | TOOL_CALL | TOOL_RESULT | SYNTHESIS
    timestamp: datetime             # When created
    visibility: VisibilityConfig    # Who can see this

    # Type-specific fields (only one populated based on type)
    thinking: Optional[ThinkingInfo]
    tool_call: Optional[ToolCallInfo]
    tool_result: Optional[ToolResultInfo]
    synthesis: Optional[SynthesisInfo]

    # Cost tracking
    tokens_used: int
    cost: float
```

**Step Types**:

| Type | Purpose | Example |
|------|---------|---------|
| `THINKING` | Agent's internal reasoning | "I need to search for the user's email" |
| `TOOL_CALL` | Invoking a tool | `call_tool("database", {"query": "SELECT..."})` |
| `TOOL_RESULT` | Result from tool | Success/failure, data returned |
| `SYNTHESIS` | Combining multiple results | "Based on steps 3 and 5, the answer is X" |

### 4. **ToolExecutor**
**Location**: `src/omniforge/tools/executor.py`

Handles the actual execution of tools with enterprise features.

```python
class ToolExecutor:
    def __init__(
        self,
        registry: ToolRegistry,          # Where tools are registered
        rate_limiter: Optional[...],     # Rate limiting
        cost_tracker: Optional[...]      # Cost tracking
    ):
        ...

    async def execute(
        self,
        tool_name: str,
        arguments: dict,
        context: ToolCallContext,
        chain: ReasoningChain           # Records steps here
    ) -> ToolResult:
        # 1. Retrieve tool from registry
        # 2. Validate arguments
        # 3. Check rate limits
        # 4. Add TOOL_CALL step to chain
        # 5. Execute with retries
        # 6. Track costs
        # 7. Add TOOL_RESULT step to chain
        # 8. Return result
```

---

## Step-by-Step Execution Flow

### Example: Agent Solving "What's 2+2?"

#### 1. **Agent Initialization**

```python
# Agent creates a reasoning chain
chain = ReasoningChain(
    task_id="task-123",
    agent_id="agent-456",
    status=ChainStatus.RUNNING
)

# Agent gets tool executor
executor = ToolExecutor(registry=tool_registry)

# Agent creates reasoning engine
engine = ReasoningEngine(
    chain=chain,
    executor=executor,
    task={"id": "task-123", "agent_id": "agent-456"},
    default_llm_model="claude-sonnet-4"
)
```

#### 2. **Agent Records Initial Thinking**

```python
# Agent adds a thinking step
engine.add_thinking("User asked 'What's 2+2?'. I need to use LLM to answer.")
```

**What happens**:
```python
# ReasoningEngine creates a step
step = ReasoningStep(
    step_number=0,
    type=StepType.THINKING,
    thinking=ThinkingInfo(
        content="User asked 'What's 2+2?'. I need to use LLM to answer.",
        confidence=None
    )
)

# Adds it to the chain
chain.add_step(step)  # Auto-assigns step_number=0
```

**Chain State**:
```
Chain steps = [
    Step 0: THINKING - "User asked 'What's 2+2?'. I need to use LLM to answer."
]
```

#### 3. **Agent Calls LLM**

```python
# Agent calls LLM through reasoning engine
result = await engine.call_llm(
    prompt="What is 2+2?",
    model="llama-3.1-8b-instant"
)
```

**What happens inside `call_llm()`**:

```python
# 1. Build arguments for LLM tool
arguments = {
    "model": "llama-3.1-8b-instant",
    "messages": [{"role": "user", "content": "What is 2+2?"}],
    "temperature": 0.7
}

# 2. Delegate to call_tool()
return await self.call_tool("llm", arguments)
```

**What happens inside `call_tool()`**:

```python
# 1. Build context
context = ToolCallContext(
    correlation_id="corr-abc-123",
    task_id="task-123",
    agent_id="agent-456"
)

# 2. Execute through executor
result = await executor.execute(
    tool_name="llm",
    arguments=arguments,
    context=context,
    chain=chain  # Chain is passed here!
)
```

**What happens inside `executor.execute()`**:

```python
# 1. Get LLM tool from registry
tool = registry.get("llm")  # Returns LLMTool instance

# 2. Validate arguments
tool.validate_arguments(arguments)  # Checks required params

# 3. Add TOOL_CALL step to chain
tool_call_step = ReasoningStep(
    step_number=0,  # Will become 1
    type=StepType.TOOL_CALL,
    tool_call=ToolCallInfo(
        tool_name="llm",
        tool_type=ToolType.LLM,
        parameters={"model": "llama-3.1-8b-instant", ...},
        correlation_id="corr-abc-123"
    )
)
chain.add_step(tool_call_step)  # Step number auto-assigned to 1

# 4. Execute tool
result = await tool.execute(context, arguments)
# (This calls LiteLLM, which calls Groq, gets response)

# 5. Add TOOL_RESULT step to chain
tool_result_step = ReasoningStep(
    step_number=0,  # Will become 2
    type=StepType.TOOL_RESULT,
    tool_result=ToolResultInfo(
        correlation_id="corr-abc-123",  # Links to step 1
        success=True,
        result={"content": "2+2 equals 4", ...}
    ),
    tokens_used=50,
    cost=0.000001
)
chain.add_step(tool_result_step)  # Step number auto-assigned to 2

# 6. Return result
return result
```

**Chain State After LLM Call**:
```
Chain steps = [
    Step 0: THINKING    - "User asked 'What's 2+2?'. I need to use LLM to answer."
    Step 1: TOOL_CALL   - llm(model="llama-3.1-8b-instant", ...)
                          correlation_id="corr-abc-123"
    Step 2: TOOL_RESULT - correlation_id="corr-abc-123"
                          result={"content": "2+2 equals 4"}
                          tokens=50, cost=0.000001
]

Chain metrics:
    total_steps: 3
    llm_calls: 1
    tool_calls: 1
    total_tokens: 50
    total_cost: 0.000001
```

#### 4. **Agent Wraps Result**

```python
# call_tool() wraps the result
return ToolCallResult(
    result=result,
    call_step=chain.steps[-2],    # Step 1 (TOOL_CALL)
    result_step=chain.steps[-1]   # Step 2 (TOOL_RESULT)
)
```

Now the agent has:
```python
result.success        # True
result.value          # {"content": "2+2 equals 4", ...}
result.step_id        # UUID of step 2 (for referencing)
result.call_step      # Reference to step 1
result.result_step    # Reference to step 2
```

#### 5. **Agent Synthesizes Answer**

```python
# Agent creates final synthesis
engine.add_synthesis(
    conclusion="The answer is: 2+2 equals 4",
    sources=[result.step_id]  # References step 2
)
```

**Final Chain State**:
```
Chain steps = [
    Step 0: THINKING    - "User asked 'What's 2+2?'. I need to use LLM to answer."
    Step 1: TOOL_CALL   - llm(...)
    Step 2: TOOL_RESULT - result={"content": "2+2 equals 4"}
    Step 3: SYNTHESIS   - "The answer is: 2+2 equals 4"
                          sources=[step-2-uuid]
]

Chain metrics:
    total_steps: 4
    llm_calls: 2  # Synthesis counts as LLM call
    tool_calls: 1
    total_tokens: 50
    total_cost: 0.000001
```

---

## ReasoningChain Structure

### Chain Lifecycle

```
1. CREATED
   ↓
2. RUNNING     ← Agent adds steps
   ↓
3. COMPLETED   ← Agent finishes
   or
   FAILED      ← Error occurred
```

### Chain Metrics Auto-Update

Every time a step is added:

```python
def add_step(self, step: ReasoningStep) -> None:
    # Auto-assign step number
    step.step_number = len(self.steps)

    # Add to steps
    self.steps.append(step)

    # Update metrics
    self.metrics.total_steps += 1
    self.metrics.total_tokens += step.tokens_used
    self.metrics.total_cost += step.cost

    # Type-specific metrics
    if step.type == StepType.TOOL_CALL:
        self.metrics.tool_calls += 1
    elif step.type in (StepType.THINKING, StepType.SYNTHESIS):
        self.metrics.llm_calls += 1
```

### Step Correlation

Tool calls and results are linked via `correlation_id`:

```
Step 5: TOOL_CALL
    correlation_id: "corr-xyz-789"
    tool: "database"

Step 6: TOOL_RESULT
    correlation_id: "corr-xyz-789"  ← Same ID!
    success: True
```

This allows:
- Matching results to calls
- Error tracking
- Distributed tracing
- Audit logging

---

## Tool Execution Flow

### Detailed Tool Execution

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Agent: engine.call_tool("database", {...})              │
└───────────────────┬─────────────────────────────────────────┘
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. ReasoningEngine: Build context, call executor           │
└───────────────────┬─────────────────────────────────────────┘
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. ToolExecutor: Add TOOL_CALL step to chain               │
│    Step N: TOOL_CALL                                        │
│        tool_name: "database"                                │
│        correlation_id: "corr-123"                           │
└───────────────────┬─────────────────────────────────────────┘
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. ToolExecutor: Execute with retries                      │
│    • Attempt 1... (may retry on failure)                   │
│    • Apply rate limiting                                    │
│    • Enforce timeout                                        │
└───────────────────┬─────────────────────────────────────────┘
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Tool.execute(): Actual tool logic                       │
│    • DatabaseTool runs SQL query                            │
│    • LLMTool calls LiteLLM                                  │
│    • Returns ToolResult                                     │
└───────────────────┬─────────────────────────────────────────┘
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. ToolExecutor: Track cost                                │
│    cost_tracker.track_cost(task_id, cost, tokens)          │
└───────────────────┬─────────────────────────────────────────┘
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ 7. ToolExecutor: Add TOOL_RESULT step to chain             │
│    Step N+1: TOOL_RESULT                                    │
│        correlation_id: "corr-123"                           │
│        success: True                                        │
│        result: {...}                                        │
│        tokens_used: 100                                     │
│        cost: 0.00002                                        │
└───────────────────┬─────────────────────────────────────────┘
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ 8. ReasoningEngine: Wrap result                            │
│    return ToolCallResult(result, call_step, result_step)   │
└───────────────────┬─────────────────────────────────────────┘
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ 9. Agent: Use result                                        │
│    if result.success:                                       │
│        data = result.value                                  │
└─────────────────────────────────────────────────────────────┘
```

---

## Examples

### Example 1: Simple Autonomous Agent

**Location**: `src/omniforge/agents/cot/autonomous.py`

```python
async def reason(self, task: Task, engine: ReasoningEngine) -> str:
    # Build system prompt with available tools
    tools = engine.get_available_tools()
    system_prompt = build_react_system_prompt(tools)

    # Initialize conversation
    conversation = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": task.description}
    ]

    # ReAct loop
    for iteration in range(max_iterations):
        # 1. Record thinking
        engine.add_thinking(f"ReAct iteration {iteration + 1}")

        # 2. Call LLM to decide next action
        llm_result = await engine.call_llm(
            messages=conversation,
            model="claude-sonnet-4"
        )

        # 3. Parse response (thought, action, final answer?)
        parsed = parser.parse(llm_result.value["content"])

        # 4. Add thought to chain
        if parsed.thought:
            engine.add_thinking(f"Thought: {parsed.thought}")

        # 5. Check if final answer
        if parsed.is_final:
            engine.add_synthesis(
                "Agent reached final answer",
                sources=[llm_result.step_id]
            )
            return parsed.final_answer

        # 6. Execute tool action
        tool_result = await engine.call_tool(
            tool_name=parsed.action,
            arguments=parsed.action_input
        )

        # 7. Add observation to conversation
        observation = f"Observation: {tool_result.value}"
        conversation.append({"role": "assistant", "content": llm_result.value})
        conversation.append({"role": "user", "content": observation})

    raise MaxIterationsError("No final answer produced")
```

**Chain produced**:
```
Step 0:  THINKING      - "ReAct iteration 1"
Step 1:  TOOL_CALL     - llm(messages=[...])
Step 2:  TOOL_RESULT   - {"content": "Thought: I need to search..."}
Step 3:  THINKING      - "Thought: I need to search..."
Step 4:  TOOL_CALL     - database(query="SELECT...")
Step 5:  TOOL_RESULT   - {"rows": [...]}
Step 6:  THINKING      - "ReAct iteration 2"
Step 7:  TOOL_CALL     - llm(messages=[...])
Step 8:  TOOL_RESULT   - {"content": "Final Answer: ..."}
Step 9:  SYNTHESIS     - "Agent reached final answer"
                         sources=[step-8-uuid]
```

### Example 2: Custom Tool Execution

```python
# Create engine
engine = ReasoningEngine(chain, executor, task)

# Add initial thinking
engine.add_thinking("Starting data analysis")

# Execute custom tool
result = await engine.call_tool(
    tool_name="data_analyzer",
    arguments={
        "dataset": "sales_2024.csv",
        "operation": "aggregate",
        "group_by": "region"
    }
)

# Check result
if result.success:
    data = result.value
    engine.add_thinking(f"Analysis completed: {data['summary']}")

    # Synthesize findings
    engine.add_synthesis(
        conclusion=f"Total sales: ${data['total']}",
        sources=[result.step_id]
    )
else:
    engine.add_thinking(f"Analysis failed: {result.error}")
```

### Example 3: Streaming Reasoning

```python
async def my_reasoning(engine: ReasoningEngine):
    """Custom reasoning function that yields steps."""
    engine.add_thinking("Starting analysis...")

    result = await engine.call_llm(prompt="Analyze this data")

    engine.add_synthesis("Conclusion", [result.step_id])

# Stream steps as they're created
async for step in engine.execute_reasoning(my_reasoning):
    print(f"Step {step.step_number}: {step.type}")
    if step.type == StepType.THINKING:
        print(f"  Thought: {step.thinking.content}")
    elif step.type == StepType.TOOL_RESULT:
        print(f"  Result: {step.tool_result.success}")
```

---

## Key Design Principles

### 1. **Separation of Concerns**
- **ReasoningEngine**: High-level agent API
- **ReasoningChain**: Data structure for steps
- **ToolExecutor**: Tool execution logic
- **Tools**: Individual tool implementations

### 2. **Automatic Bookkeeping**
- Step numbers auto-assigned
- Metrics auto-updated
- Correlation IDs auto-generated
- Timestamps auto-recorded

### 3. **Transparency**
- Every action recorded
- Full audit trail
- Cost tracking built-in
- Visibility controls

### 4. **Flexibility**
- Any tool can be called
- Custom step types supported
- Extensible for new features

### 5. **Enterprise-Ready**
- Rate limiting
- Cost tracking
- Multi-tenancy
- RBAC integration

---

## Summary

The **ReasoningEngine** is OmniForge's solution for **structured, auditable, cost-tracked agent reasoning**:

1. **Agents** use `ReasoningEngine` as their primary interface
2. **Engine** records steps in a `ReasoningChain`
3. **Chain** maintains sequential reasoning history
4. **Executor** handles tool execution with enterprise features
5. **Steps** capture thoughts, actions, results, and synthesis

This architecture enables:
- ✅ Complete reasoning transparency
- ✅ Cost and token tracking
- ✅ Real-time streaming
- ✅ Enterprise governance
- ✅ Audit trails
- ✅ Debugging and analysis

Every LLM call, tool execution, and thought is recorded, making agent behavior fully observable and debuggable.
