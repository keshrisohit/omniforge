# ReasoningEngine Quick Reference

A concise cheat sheet for working with the ReasoningEngine.

## Basic Setup

```python
from omniforge.agents.cot.chain import ReasoningChain, ChainStatus
from omniforge.agents.cot.engine import ReasoningEngine
from omniforge.tools.executor import ToolExecutor
from omniforge.tools.setup import get_default_tool_registry

# 1. Create chain
chain = ReasoningChain(
    task_id="task-123",
    agent_id="agent-456",
    status=ChainStatus.RUNNING
)

# 2. Get tool executor
registry = get_default_tool_registry()
executor = ToolExecutor(registry=registry)

# 3. Create reasoning engine
engine = ReasoningEngine(
    chain=chain,
    executor=executor,
    task={"id": "task-123", "agent_id": "agent-456"},
    default_llm_model="claude-sonnet-4"
)
```

## Core Operations

### Add Thinking Step

```python
# Simple thought
engine.add_thinking("I need to analyze this data")

# With confidence
engine.add_thinking("This looks correct", confidence=0.9)
```

### Call LLM

```python
# Simple prompt
result = await engine.call_llm(
    prompt="What is 2+2?"
)

# With messages array
result = await engine.call_llm(
    messages=[
        {"role": "system", "content": "You are helpful"},
        {"role": "user", "content": "Hello"}
    ],
    model="llama-3.1-8b-instant",
    temperature=0.7
)

# Access result
content = result.value["content"]  # LLM response text
step_id = result.step_id           # For referencing later
success = result.success           # True/False
```

### Call Any Tool

```python
# Execute tool
result = await engine.call_tool(
    tool_name="database",
    arguments={
        "query": "SELECT * FROM users",
        "limit": 10
    }
)

# Check result
if result.success:
    data = result.value
    print(f"Got {len(data['rows'])} rows")
else:
    print(f"Error: {result.error}")
```

### Add Synthesis

```python
# Combine multiple steps into conclusion
engine.add_synthesis(
    conclusion="Based on the data, the average is 42",
    sources=[step1_id, step2_id, step3_id]
)
```

## Accessing Chain Data

### Get All Steps

```python
# Access all steps
for step in engine.chain.steps:
    print(f"Step {step.step_number}: {step.type}")
```

### Get Metrics

```python
metrics = engine.chain.metrics
print(f"Total steps: {metrics.total_steps}")
print(f"LLM calls: {metrics.llm_calls}")
print(f"Tool calls: {metrics.tool_calls}")
print(f"Total tokens: {metrics.total_tokens}")
print(f"Total cost: ${metrics.total_cost:.6f}")
```

### Find Specific Steps

```python
# Get thinking steps
thinking_steps = [
    step for step in engine.chain.steps
    if step.type == StepType.THINKING
]

# Get tool results
tool_results = [
    step for step in engine.chain.steps
    if step.type == StepType.TOOL_RESULT
]

# Find by correlation ID
step = engine.chain.get_step_by_correlation_id("corr-123")
```

## Step Types Reference

| Type | When to Use | Example |
|------|-------------|---------|
| `THINKING` | Record agent's reasoning | `engine.add_thinking("I should search first")` |
| `TOOL_CALL` | Automatically added when calling tools | Created by `call_tool()` or `call_llm()` |
| `TOOL_RESULT` | Automatically added after tool execution | Created by tool executor |
| `SYNTHESIS` | Combine results into conclusion | `engine.add_synthesis("Answer: 42", [step1, step2])` |

## Common Patterns

### Pattern 1: Think → Act → Synthesize

```python
# 1. Record thinking
engine.add_thinking("User wants to know their balance")

# 2. Execute action
result = await engine.call_tool(
    tool_name="database",
    arguments={"query": "SELECT balance FROM accounts WHERE user_id=?"}
)

# 3. Synthesize answer
if result.success:
    balance = result.value["rows"][0]["balance"]
    engine.add_synthesis(
        f"User's balance is ${balance}",
        sources=[result.step_id]
    )
```

### Pattern 2: ReAct Loop (Reasoning + Acting)

```python
for iteration in range(max_iterations):
    # Think
    engine.add_thinking(f"Iteration {iteration + 1}")

    # Decide action
    llm_result = await engine.call_llm(
        messages=conversation,
        model="claude-sonnet-4"
    )

    # Parse and execute
    parsed = parse_response(llm_result.value)

    if parsed.is_final:
        return parsed.answer

    # Act
    tool_result = await engine.call_tool(
        tool_name=parsed.action,
        arguments=parsed.action_input
    )

    # Update conversation
    conversation.append({
        "role": "assistant",
        "content": llm_result.value["content"]
    })
    conversation.append({
        "role": "user",
        "content": f"Observation: {tool_result.value}"
    })
```

### Pattern 3: Multi-Tool Workflow

```python
# Step 1: Search
engine.add_thinking("Searching for user data")
search_result = await engine.call_tool("search", {"query": "user:123"})

# Step 2: Analyze
engine.add_thinking("Analyzing results")
analysis = await engine.call_llm(
    prompt=f"Analyze this data: {search_result.value}"
)

# Step 3: Save
engine.add_thinking("Saving analysis")
save_result = await engine.call_tool(
    "database",
    {"action": "insert", "data": analysis.value}
)

# Synthesize
engine.add_synthesis(
    "Analysis completed and saved",
    sources=[search_result.step_id, analysis.step_id, save_result.step_id]
)
```

### Pattern 4: Error Handling

```python
engine.add_thinking("Attempting database query")

result = await engine.call_tool("database", {"query": "..."})

if result.success:
    engine.add_thinking(f"Query succeeded: {result.value}")
else:
    engine.add_thinking(
        f"Query failed: {result.error}. Trying alternative approach",
        confidence=0.5
    )
    # Try alternative
    alt_result = await engine.call_tool("cache", {"key": "fallback"})
```

## ToolCallResult Properties

When you call `call_llm()` or `call_tool()`, you get a `ToolCallResult`:

```python
result = await engine.call_llm(prompt="Hello")

# Properties
result.success        # bool: Did it succeed?
result.value          # dict: The actual result data
result.error          # str: Error message if failed
result.step_id        # str: UUID of result step (for referencing)
result.call_step      # ReasoningStep: The TOOL_CALL step
result.result_step    # ReasoningStep: The TOOL_RESULT step
```

## Streaming Reasoning

Stream steps as they're created:

```python
async def my_reasoning(engine: ReasoningEngine):
    engine.add_thinking("Starting...")
    result = await engine.call_llm(prompt="Analyze")
    engine.add_synthesis("Done", [result.step_id])

# Stream it
async for step in engine.execute_reasoning(my_reasoning):
    if step.type == StepType.THINKING:
        print(f"💭 {step.thinking.content}")
    elif step.type == StepType.TOOL_RESULT:
        print(f"✅ Tool completed: {step.tool_result.success}")
```

## Available Tools

```python
# Get list of all available tools
tools = engine.get_available_tools()

for tool in tools:
    print(f"Tool: {tool.name}")
    print(f"  Type: {tool.type}")
    print(f"  Description: {tool.description}")
    print(f"  Parameters: {tool.parameters}")
```

## Cost Tracking

Costs are automatically tracked:

```python
# Check total cost
total_cost = engine.chain.metrics.total_cost
print(f"Total: ${total_cost:.6f}")

# Check per-step cost
for step in engine.chain.steps:
    if step.cost > 0:
        print(f"Step {step.step_number}: ${step.cost:.6f}")
```

## Chain Serialization

Chains can be serialized to JSON:

```python
# Convert to dict
chain_dict = engine.chain.model_dump()

# Convert to JSON
import json
chain_json = json.dumps(chain_dict, indent=2, default=str)

# Save to file
with open("reasoning_chain.json", "w") as f:
    f.write(chain_json)
```

## Visibility Control

Control who can see steps:

```python
from omniforge.tools.types import VisibilityLevel

# Hide sensitive tool call
result = await engine.call_tool(
    tool_name="database",
    arguments={"query": "SELECT * FROM sensitive_data"},
    visibility=VisibilityLevel.INTERNAL  # Only internal systems
)

# Public result
result = await engine.call_llm(
    prompt="Public info",
    visibility=VisibilityLevel.FULL  # Everyone can see
)
```

## Common Mistakes to Avoid

### ❌ DON'T: Forget to await

```python
# Wrong
result = engine.call_llm(prompt="Hello")  # Missing await!

# Right
result = await engine.call_llm(prompt="Hello")
```

### ❌ DON'T: Access wrong result field

```python
result = await engine.call_llm(prompt="Hello")

# Wrong
content = result.result["content"]  # result.result is ToolResult object

# Right
content = result.value["content"]  # Use .value
```

### ❌ DON'T: Ignore errors

```python
result = await engine.call_tool("database", {...})
data = result.value  # May be None if failed!

# Right
if result.success:
    data = result.value
else:
    handle_error(result.error)
```

### ❌ DON'T: Modify chain directly

```python
# Wrong
engine.chain.steps.append(my_step)  # May break metrics

# Right
engine.add_thinking(...)  # Use engine methods
```

## Debugging Tips

### Print Chain Steps

```python
def print_chain(chain: ReasoningChain):
    print(f"\nChain: {chain.id}")
    print(f"Status: {chain.status}")
    print(f"Steps: {len(chain.steps)}\n")

    for step in chain.steps:
        print(f"Step {step.step_number}: {step.type}")
        if step.type == StepType.THINKING:
            print(f"  💭 {step.thinking.content[:50]}...")
        elif step.type == StepType.TOOL_CALL:
            print(f"  🔧 {step.tool_call.tool_name}(...)")
        elif step.type == StepType.TOOL_RESULT:
            print(f"  {'✅' if step.tool_result.success else '❌'} {step.tool_result.correlation_id}")
        elif step.type == StepType.SYNTHESIS:
            print(f"  📊 {step.synthesis.content[:50]}...")
        print(f"     Tokens: {step.tokens_used}, Cost: ${step.cost:.6f}")
```

### Export Chain for Analysis

```python
# Export to pandas DataFrame
import pandas as pd

steps_data = []
for step in engine.chain.steps:
    steps_data.append({
        "step_number": step.step_number,
        "type": step.type,
        "tokens": step.tokens_used,
        "cost": step.cost,
        "timestamp": step.timestamp
    })

df = pd.DataFrame(steps_data)
print(df.describe())
```

## File Locations

| Component | File Path |
|-----------|-----------|
| ReasoningEngine | `src/omniforge/agents/cot/engine.py` |
| ReasoningChain | `src/omniforge/agents/cot/chain.py` |
| ToolExecutor | `src/omniforge/tools/executor.py` |
| Tool Registry | `src/omniforge/tools/registry.py` |
| LLMTool | `src/omniforge/tools/builtin/llm.py` |

## Next Steps

- Read [ReasoningEngine Architecture](./reasoning-engine-architecture.md) for detailed explanations
- Check [LLM Architecture](./llm-architecture.md) to understand LLM integration
- See [Groq Provider Setup](./groq-provider-setup.md) for using Groq models
- Explore `examples/` directory for complete agent examples
