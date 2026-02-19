# Understanding the ReasoningEngine

**Complete guide to OmniForge's ReasoningEngine**

## What is the ReasoningEngine?

The **ReasoningEngine** is the core component that enables structured, auditable, and cost-tracked agent reasoning in OmniForge. Think of it as a **"reasoning notebook"** where agents:

- 📝 **Record their thoughts** (thinking steps)
- 🔧 **Execute tools** (LLMs, databases, APIs)
- 📊 **Synthesize conclusions** (combining multiple results)
- 💰 **Track costs** (tokens and USD)
- 🔍 **Build audit trails** (complete reasoning history)

## Quick Start

```python
from omniforge.agents.cot.chain import ReasoningChain
from omniforge.agents.cot.engine import ReasoningEngine
from omniforge.tools.executor import ToolExecutor
from omniforge.tools.setup import get_default_tool_registry

# 1. Create chain
chain = ReasoningChain(task_id="task-123", agent_id="agent-456")

# 2. Get executor with tools
executor = ToolExecutor(registry=get_default_tool_registry())

# 3. Create engine
engine = ReasoningEngine(
    chain=chain,
    executor=executor,
    task={"id": "task-123", "agent_id": "agent-456"}
)

# 4. Use it!
engine.add_thinking("Let me analyze this...")
result = await engine.call_llm(prompt="What is 2+2?")
engine.add_synthesis("The answer is 4", sources=[result.step_id])
```

## Core Concepts

### 1. **ReasoningChain** - The Notebook

A sequential record of all reasoning steps:

```python
chain = ReasoningChain(
    task_id="task-123",
    agent_id="agent-456",
    status=ChainStatus.RUNNING,
    steps=[],        # Auto-populated
    metrics={}       # Auto-updated
)
```

**Automatically tracks**:
- Total steps
- LLM calls count
- Tool calls count
- Total tokens used
- Total cost in USD

### 2. **ReasoningStep** - The Entry

A single entry in the notebook:

```python
Step 0: THINKING    - "User wants weather info"
Step 1: TOOL_CALL   - weather_api(city="NYC")
Step 2: TOOL_RESULT - {temp: 72, condition: "sunny"}
Step 3: SYNTHESIS   - "Weather in NYC is 72°F and sunny"
```

**Four step types**:
- `THINKING`: Agent's internal reasoning
- `TOOL_CALL`: Invoking a tool (auto-added)
- `TOOL_RESULT`: Tool's response (auto-added)
- `SYNTHESIS`: Combining results into conclusions

### 3. **ReasoningEngine** - The API

The interface agents use to interact with the chain:

| Method | Purpose | Example |
|--------|---------|---------|
| `add_thinking()` | Record thoughts | `engine.add_thinking("I need to search")` |
| `call_llm()` | Call LLM | `await engine.call_llm(prompt="Hello")` |
| `call_tool()` | Execute any tool | `await engine.call_tool("database", {...})` |
| `add_synthesis()` | Combine results | `engine.add_synthesis("Answer: 42", [s1, s2])` |

### 4. **ToolExecutor** - The Execution Engine

Handles actual tool execution with enterprise features:
- ✅ Retry logic with exponential backoff
- ✅ Timeout enforcement
- ✅ Rate limiting
- ✅ Cost tracking
- ✅ Audit logging
- ✅ Automatic step recording

## How It Works

### Simple Example

```python
# 1. Agent records thought
engine.add_thinking("User asked about weather")
```
**Chain**: `[Step 0: THINKING]`

```python
# 2. Agent calls tool
result = await engine.call_tool("weather", {"city": "NYC"})
```
**Chain**:
```
[Step 0: THINKING]
[Step 1: TOOL_CALL - weather(city="NYC")]
[Step 2: TOOL_RESULT - {temp: 72}]
```

```python
# 3. Agent synthesizes
engine.add_synthesis(
    "Weather is 72°F",
    sources=[result.step_id]
)
```
**Chain**:
```
[Step 0: THINKING]
[Step 1: TOOL_CALL]
[Step 2: TOOL_RESULT]
[Step 3: SYNTHESIS - "Weather is 72°F"]
```

### What Happens Behind the Scenes

When you call `engine.call_tool()`:

1. **ReasoningEngine** creates a `ToolCallContext` with IDs
2. **ToolExecutor** retrieves the tool from registry
3. **ToolExecutor** validates arguments
4. **ToolExecutor** adds `TOOL_CALL` step to chain
5. **Tool** executes (with retries if needed)
6. **ToolExecutor** tracks cost
7. **ToolExecutor** adds `TOOL_RESULT` step to chain
8. **ReasoningEngine** wraps result and returns to agent

All **automatically**! The agent just calls one method.

## Key Features

### 🔗 Automatic Correlation

Tool calls and results are linked via `correlation_id`:

```
Step 5: TOOL_CALL
    correlation_id: "corr-xyz"
    tool: "database"

Step 6: TOOL_RESULT
    correlation_id: "corr-xyz"  ← Same ID!
    success: True
```

### 💰 Built-in Cost Tracking

Every LLM call automatically tracked:

```python
result = await engine.call_llm(prompt="Hello")

# Cost automatically calculated
print(f"Cost: ${result.result_step.cost}")
print(f"Tokens: {result.result_step.tokens_used}")

# Chain metrics auto-updated
print(f"Total cost: ${engine.chain.metrics.total_cost}")
```

### 📊 Real-time Metrics

Metrics update automatically:

```python
metrics = engine.chain.metrics

print(f"Steps: {metrics.total_steps}")
print(f"LLM calls: {metrics.llm_calls}")
print(f"Tool calls: {metrics.tool_calls}")
print(f"Tokens: {metrics.total_tokens}")
print(f"Cost: ${metrics.total_cost}")
```

### 🔍 Complete Audit Trail

Every action recorded:

```python
for step in engine.chain.steps:
    print(f"{step.step_number}: {step.type}")
    print(f"  Time: {step.timestamp}")
    print(f"  Tokens: {step.tokens_used}")
    print(f"  Cost: ${step.cost}")
```

### 🎯 Step References

Link steps together:

```python
# Execute tools
search = await engine.call_tool("search", {...})
analyze = await engine.call_llm(prompt=f"Analyze: {search.value}")

# Reference both in synthesis
engine.add_synthesis(
    "Based on search and analysis...",
    sources=[search.step_id, analyze.step_id]
)
```

## Common Patterns

### Pattern 1: Simple Reasoning

```python
# Think
engine.add_thinking("User wants X")

# Act
result = await engine.call_llm(prompt="Do X")

# Conclude
engine.add_synthesis("Answer is Y", [result.step_id])
```

### Pattern 2: ReAct Loop

```python
for i in range(max_iterations):
    # Think
    engine.add_thinking(f"Iteration {i}")

    # Reason
    response = await engine.call_llm(messages=conversation)

    # Check if done
    if is_final_answer(response):
        return response.value

    # Act
    tool_result = await engine.call_tool(
        tool_name=parse_action(response),
        arguments=parse_input(response)
    )

    # Observe
    conversation.append({
        "role": "user",
        "content": f"Observation: {tool_result.value}"
    })
```

### Pattern 3: Multi-Tool Workflow

```python
# Step 1
engine.add_thinking("Fetching data")
data = await engine.call_tool("database", {...})

# Step 2
engine.add_thinking("Analyzing data")
analysis = await engine.call_llm(prompt=f"Analyze: {data.value}")

# Step 3
engine.add_thinking("Saving results")
save = await engine.call_tool("storage", {"data": analysis.value})

# Synthesize
engine.add_synthesis(
    "Analysis complete",
    sources=[data.step_id, analysis.step_id, save.step_id]
)
```

## File Structure

```
src/omniforge/
├── agents/cot/
│   ├── chain.py          # ReasoningChain, ReasoningStep
│   ├── engine.py         # ReasoningEngine
│   ├── agent.py          # CoTAgent base class
│   └── autonomous.py     # AutonomousCoTAgent
├── tools/
│   ├── executor.py       # ToolExecutor
│   ├── registry.py       # ToolRegistry
│   ├── setup.py          # Default tools setup
│   └── builtin/
│       └── llm.py        # LLMTool
└── llm/
    ├── config.py         # LLM configuration
    └── cost.py           # Cost calculation
```

## Documentation

| Document | Description |
|----------|-------------|
| [reasoning-engine-architecture.md](./reasoning-engine-architecture.md) | Detailed architecture and design |
| [reasoning-engine-quick-reference.md](./reasoning-engine-quick-reference.md) | Quick reference cheat sheet |
| [reasoning-engine-visual-guide.md](./reasoning-engine-visual-guide.md) | Visual diagrams and flows |
| [llm-architecture.md](./llm-architecture.md) | How LLMs are called |
| [groq-provider-setup.md](./groq-provider-setup.md) | Groq integration guide |

## Examples

| Example | Description |
|---------|-------------|
| `examples/reasoning_engine_example.py` | Complete working examples |
| `examples/autonomous_agent_examples.py` | Autonomous agent patterns |
| `examples/groq_example.py` | Using Groq models |

## Key Benefits

### For Agents
- 🚀 **Simple API**: Just call methods, everything else automatic
- 🎯 **High-level abstractions**: `call_llm()` instead of complex setup
- 📊 **Built-in tracking**: Costs, tokens, metrics - all automatic

### For Developers
- 🔍 **Complete visibility**: See exactly what agents are doing
- 🐛 **Easy debugging**: Full history of every step
- 💰 **Cost monitoring**: Track spending in real-time
- 🔒 **Enterprise ready**: Rate limiting, RBAC, multi-tenancy

### For Users
- 📖 **Transparency**: Understand how AI reached conclusions
- ✅ **Auditability**: Complete reasoning trail
- 🎛️ **Control**: Visibility settings, budget limits

## Integration Points

### With Tool System
```python
# ReasoningEngine uses ToolExecutor
executor = ToolExecutor(registry=tool_registry)
engine = ReasoningEngine(chain, executor, task)

# Tools automatically registered
await engine.call_tool("any_tool", {...})
```

### With LLM System
```python
# LLM configuration loaded automatically
from omniforge.llm.config import load_config_from_env
config = load_config_from_env()  # Loads Groq, OpenAI, etc.

# ReasoningEngine uses configured LLMs
await engine.call_llm(model="llama-3.1-8b-instant")
```

### With Cost Tracking
```python
# Cost tracking happens automatically
from omniforge.llm.cost import estimate_cost_before_call

# Before call
estimated = estimate_cost_before_call(model, messages, max_tokens)

# After call (in ToolResult)
actual = result.cost_usd
```

## Best Practices

### ✅ DO

- Use `add_thinking()` to document reasoning
- Check `result.success` before using `result.value`
- Use `add_synthesis()` to combine multiple results
- Track step IDs for referencing later
- Set budget limits in task context

### ❌ DON'T

- Modify `chain.steps` directly (use engine methods)
- Forget to `await` async calls
- Ignore error handling
- Access `result.result` (use `result.value`)
- Create steps manually (let engine/executor do it)

## Summary

The **ReasoningEngine** provides:

1. **Simple API** for agents to record reasoning
2. **Automatic bookkeeping** (step numbers, metrics, costs)
3. **Tool execution** with enterprise features
4. **Complete audit trail** for transparency
5. **Cost tracking** for monitoring
6. **Streaming support** for real-time updates

**Everything is automatic** - agents just call high-level methods, and the engine handles:
- Step creation and numbering
- Correlation ID management
- Metrics calculation
- Cost tracking
- Error handling
- Retry logic
- Audit logging

This architecture makes agent development **simple** while providing **enterprise-grade** features out of the box.

---

## Next Steps

1. **Read the docs**:
   - [Architecture Guide](./reasoning-engine-architecture.md) - Deep dive
   - [Quick Reference](./reasoning-engine-quick-reference.md) - Cheat sheet
   - [Visual Guide](./reasoning-engine-visual-guide.md) - Diagrams

2. **Try the examples**:
   ```bash
   python examples/reasoning_engine_example.py
   ```

3. **Build your own agent**:
   - Extend `CoTAgent` base class
   - Implement `reason()` method using `ReasoningEngine`
   - Add custom tools to registry

4. **Explore integrations**:
   - [LLM Architecture](./llm-architecture.md)
   - [Groq Provider](./groq-provider-setup.md)
   - Tool system documentation

**Happy building! 🚀**
