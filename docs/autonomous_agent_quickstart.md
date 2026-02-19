# SimpleAutonomousAgent Quick Start

Create agents that autonomously decide which tools to use at runtime based on your prompts.

## TL;DR - Simplest Usage

```python
from omniforge.agents import run_autonomous_agent

# One line - that's it!
result = await run_autonomous_agent(
    "Count how many Python files are in the src/ directory"
)
print(result)
```

## Basic Usage

```python
from omniforge.agents import SimpleAutonomousAgent

# Create agent
agent = SimpleAutonomousAgent()

# Run with prompt - agent decides which tools to use
result = await agent.run("Find all TODO comments in Python files")
print(result)
```

## How It Works

The agent uses the **ReAct pattern** (Reasoning + Acting):

1. **Thinks** - Analyzes what needs to be done
2. **Acts** - Chooses and executes a tool (bash, read, write, grep, glob, llm)
3. **Observes** - Reviews the tool result
4. **Repeats** - Continues until task is complete

You don't write any tool-calling logic - the agent figures it out!

## Custom System Prompt

Guide agent behavior with a system prompt:

```python
agent = SimpleAutonomousAgent(
    system_prompt="""You are a senior code reviewer.

When reviewing code:
- Focus on security, performance, and maintainability
- Be specific with line numbers
- Suggest concrete improvements
- Be concise but thorough"""
)

result = await agent.run("Review src/omniforge/agents/base.py")
print(result)
```

## Configuration Options

```python
agent = SimpleAutonomousAgent(
    system_prompt="You are a DevOps expert.",
    max_iterations=20,             # More iterations for complex tasks
    model="claude-sonnet-4",       # LLM model to use
    temperature=0.0,               # 0.0 = deterministic, 0.7+ = creative
)
```

## Real Examples

### File Operations
```python
agent = SimpleAutonomousAgent()

# Agent automatically uses read, write, bash tools
result = await agent.run("""
1. Create a file called test.txt
2. Write 'Hello World' to it
3. Read it back
4. Delete it
""")
```

### Code Analysis
```python
agent = SimpleAutonomousAgent(
    system_prompt="You are a code structure analyst."
)

result = await agent.run(
    "Analyze the agents module and describe its architecture"
)
```

### Search and Find
```python
agent = SimpleAutonomousAgent()

# Agent uses grep/glob automatically
result = await agent.run(
    "Find all files importing 'asyncio' and count them"
)
```

### Data Processing
```python
agent = SimpleAutonomousAgent(
    system_prompt="You are a data analyst. Present findings with numbers."
)

result = await agent.run("""
Analyze Python files in src/:
- Count total files
- Find average file size
- List the 5 largest files
""")
```

## Watching the Agent Think (Advanced)

See reasoning steps in real-time:

```python
from omniforge.agents import SimpleAutonomousAgent
from omniforge.agents.helpers import create_simple_task

agent = SimpleAutonomousAgent()

task = create_simple_task(
    message="Find and count TypeScript files",
    agent_id=agent.identity.id,
)

async for event in agent.process_task(task):
    if hasattr(event, "step"):
        step = event.step
        if step.type == "thinking":
            print(f"💭 {step.thinking.content}")
        elif step.type == "tool_call":
            print(f"🔧 Tool: {step.tool_call.tool_name}")
        elif step.type == "tool_result":
            print(f"✅ Success" if step.tool_result.success else f"❌ Error")
    elif hasattr(event, "message_parts"):
        print(f"\n📝 Final Answer: {event.message_parts[0].text}")
```

## Available Built-in Tools

The agent can use these tools automatically:

- **bash** - Execute shell commands
- **read** - Read files
- **write** - Write files
- **grep** - Search patterns
- **glob** - Find files
- **llm** - Call LLMs for analysis

## Error Handling

```python
agent = SimpleAutonomousAgent(max_iterations=5)

try:
    result = await agent.run("Complex task that may timeout")
    print(result)
except RuntimeError as e:
    print(f"Agent failed: {e}")
    # Tip: Increase max_iterations for complex tasks
```

## Batch Processing

```python
agent = SimpleAutonomousAgent()

prompts = [
    "Count Python files in src/",
    "Find files with TODO comments",
    "Show me the largest file",
]

results = await asyncio.gather(*[agent.run(p) for p in prompts])

for prompt, result in zip(prompts, results):
    print(f"Q: {prompt}")
    print(f"A: {result}\n")
```

## Different Models

```python
# Claude Sonnet (default)
agent_sonnet = SimpleAutonomousAgent(model="claude-sonnet-4")

# GPT-4
agent_gpt = SimpleAutonomousAgent(model="gpt-4")

# Claude Opus (most capable)
agent_opus = SimpleAutonomousAgent(model="claude-opus-4")
```

## Comparison with Other Agents

| Agent Type | When to Use |
|------------|-------------|
| **SimpleAutonomousAgent** | Autonomous tool selection, just pass prompt |
| **SimpleAgent** | Basic agents without tool calling |
| **CoTAgent** | Manual control over tool selection |
| **AutonomousCoTAgent** | Full CoT with custom ReAct parser |

## Quick Reference

```python
# One-liner
result = await run_autonomous_agent("Your prompt here")

# Basic agent
agent = SimpleAutonomousAgent()
result = await agent.run("Your prompt here")

# Customized
agent = SimpleAutonomousAgent(
    system_prompt="Custom instructions",
    max_iterations=20,
    model="claude-sonnet-4",
    temperature=0.0,
)
result = await agent.run("Your prompt here")

# Streaming
async for event in agent.process_task(task):
    # Handle events...
```

## Tips for Best Results

1. **Be specific** - Clear prompts get better results
   - ❌ "Analyze code"
   - ✅ "Count Python files in src/ and calculate average file size"

2. **Break complex tasks into steps** - Agent follows structured instructions well
   ```python
   result = await agent.run("""
   1. Find all Python files
   2. Check which have tests
   3. Calculate coverage percentage
   4. List files without tests
   """)
   ```

3. **Adjust max_iterations** - Complex tasks need more iterations
   ```python
   agent = SimpleAutonomousAgent(max_iterations=25)
   ```

4. **Use system prompts** - Guide agent personality and behavior
   ```python
   agent = SimpleAutonomousAgent(
       system_prompt="You are a security expert. Focus on vulnerabilities."
   )
   ```

5. **Choose the right temperature**
   - `0.0` - Deterministic, reproducible results
   - `0.3-0.5` - Balanced
   - `0.7-1.0` - Creative, varied responses

## Full Example

```python
import asyncio
from omniforge.agents import SimpleAutonomousAgent

async def main():
    # Create agent with custom behavior
    agent = SimpleAutonomousAgent(
        system_prompt="""You are a helpful code assistant.

        When analyzing code:
        - Be concise but thorough
        - Provide specific examples
        - Suggest improvements""",
        max_iterations=15,
        model="claude-sonnet-4",
        temperature=0.0,  # Deterministic
    )

    # Complex multi-step task
    result = await agent.run("""
    Perform a code quality check:
    1. Find all Python files in src/omniforge/agents/
    2. Count total lines of code
    3. Find files larger than 200 lines
    4. Check which files have docstrings
    5. Provide a summary report
    """)

    print(result)

if __name__ == "__main__":
    asyncio.run(main())
```

## Next Steps

- See `examples/autonomous_agent_examples.py` for 15 complete examples
- Check `tests/agents/test_autonomous_simple.py` for usage patterns
- Read the source in `src/omniforge/agents/autonomous_simple.py`

## Questions?

- **"Agent takes too long"** → Reduce `max_iterations` or simplify the task
- **"Agent gives wrong answer"** → Adjust `system_prompt` to guide behavior
- **"Need more control"** → Use `CoTAgent` for manual tool selection
- **"Want to add custom tools"** → Pass custom `tool_registry` to agent

Happy autonomous agent building! 🤖
