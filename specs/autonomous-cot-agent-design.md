# Autonomous Chain of Thought Agent Design

**Created**: 2026-01-11
**Status**: Design Document
**Related**: cot-agent-with-unified-tools-spec.md, cot-agent-with-unified-tools-plan.md

---

## Overview

The **AutonomousCoTAgent** is a concrete implementation of the CoTAgent that uses the **ReAct (Reasoning + Acting)** pattern to autonomously solve tasks. Users simply provide a high-level task description, and the agent:

1. Decides which tools to call
2. Generates its own prompts
3. Determines when the task is complete
4. Handles errors and retries autonomously

This is in contrast to the manual `reason()` implementation where developers write explicit reasoning logic.

---

## ReAct Pattern

The agent follows the **ReAct loop**:

```
Thought: <reasoning about what to do next>
Action: <tool name to call>
Action Input: <arguments for the tool>
Observation: <result from tool execution>
... (repeat until done)
Thought: <final reasoning>
Final Answer: <response to user>
```

**Example Execution:**

```
User: "What's the weather in San Francisco and Paris? Compare them."

Thought: I need to get weather data for both cities. Let me start with San Francisco.
Action: weather_api
Action Input: {"location": "San Francisco", "units": "celsius"}
Observation: {"temperature": 18, "conditions": "partly cloudy"}

Thought: Now I need Paris weather data.
Action: weather_api
Action Input: {"location": "Paris", "units": "celsius"}
Observation: {"temperature": 12, "conditions": "rainy"}

Thought: I have both weather reports. Now I can compare them.
Final Answer: San Francisco is currently warmer at 18°C with partly cloudy conditions, while Paris is cooler at 12°C with rainy conditions. San Francisco is 6 degrees warmer.
```

---

## System Prompt Design

The agent uses a carefully crafted system prompt that:
- Teaches the ReAct format
- Lists available tools with descriptions
- Provides examples of correct usage
- Specifies termination conditions

**Template:**

```
You are an autonomous AI agent that can reason and act to solve user tasks.

You have access to the following tools:

{tool_descriptions}

Use the following format for your responses:

Thought: <your reasoning about what to do next>
Action: <the tool name from the list above>
Action Input: <valid JSON arguments for the tool>
Observation: <tool result will appear here>
... (repeat Thought/Action/Action Input/Observation as many times as needed)
Thought: <final reasoning>
Final Answer: <your response to the user>

IMPORTANT RULES:
1. Always start with "Thought:" to explain your reasoning
2. After Thought, use "Action:" to specify which tool to call
3. After Action, use "Action Input:" with valid JSON arguments
4. Wait for the "Observation:" which shows the tool result
5. Continue the Thought/Action/Observation cycle until you can answer
6. When you have enough information, output "Final Answer:" with your response
7. NEVER make up tool results - always wait for real observations
8. NEVER call the same tool with same arguments twice unless needed
9. If a tool fails, try a different approach
10. Action Input MUST be valid JSON

Begin!
```

---

## Tool Description Format

Tools are automatically described to the agent:

```json
{
  "name": "database",
  "description": "Query the database for data. Use SQL queries.",
  "parameters": {
    "query": {
      "type": "string",
      "description": "SQL query to execute",
      "required": true
    },
    "limit": {
      "type": "integer",
      "description": "Maximum rows to return",
      "required": false,
      "default": 100
    }
  },
  "returns": {
    "type": "object",
    "description": "Query results with rows and metadata"
  }
}
```

Rendered as:

```
database: Query the database for data. Use SQL queries.
  Parameters:
    - query (string, required): SQL query to execute
    - limit (integer, optional, default=100): Maximum rows to return
  Returns: Query results with rows and metadata
```

---

## Response Parsing

The agent parses LLM responses to extract structured actions:

```python
class ReActParser:
    """Parse ReAct format from LLM responses."""

    THOUGHT_PATTERN = r"Thought:\s*(.+?)(?=\n(?:Action|Final Answer):|$)"
    ACTION_PATTERN = r"Action:\s*(\w+)"
    ACTION_INPUT_PATTERN = r"Action Input:\s*({.+?}|\[.+?\])"
    FINAL_ANSWER_PATTERN = r"Final Answer:\s*(.+?)$"

    def parse(self, response: str) -> ParsedResponse:
        """Parse LLM response into structured format."""
        # Extract thought
        thought_match = re.search(self.THOUGHT_PATTERN, response, re.DOTALL)
        thought = thought_match.group(1).strip() if thought_match else None

        # Check for final answer
        final_match = re.search(self.FINAL_ANSWER_PATTERN, response, re.DOTALL | re.MULTILINE)
        if final_match:
            return ParsedResponse(
                thought=thought,
                is_final=True,
                final_answer=final_match.group(1).strip()
            )

        # Extract action
        action_match = re.search(self.ACTION_PATTERN, response)
        action = action_match.group(1).strip() if action_match else None

        # Extract action input
        input_match = re.search(self.ACTION_INPUT_PATTERN, response, re.DOTALL)
        if input_match:
            try:
                action_input = json.loads(input_match.group(1))
            except json.JSONDecodeError:
                action_input = None
        else:
            action_input = None

        return ParsedResponse(
            thought=thought,
            is_final=False,
            action=action,
            action_input=action_input
        )
```

---

## Autonomous Reasoning Loop

```python
async def autonomous_reasoning_loop(
    task: Task,
    engine: ReasoningEngine,
    max_iterations: int = 10
) -> str:
    """Execute autonomous ReAct loop."""

    # Build system prompt with tool descriptions
    system_prompt = build_system_prompt(engine.get_available_tools())

    # Initialize conversation history
    conversation = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": task.messages[-1].parts[0].text}
    ]

    parser = ReActParser()

    for iteration in range(max_iterations):
        # Call LLM to decide next action
        engine.add_thinking(f"Iteration {iteration + 1}/{max_iterations}")

        llm_response = await engine.call_llm(
            messages=conversation,
            model="claude-sonnet-4",
            temperature=0.0  # Deterministic for reasoning
        )

        # Parse response
        parsed = parser.parse(llm_response.value)

        # Add LLM's thought to chain
        if parsed.thought:
            engine.add_thinking(parsed.thought)

        # Check if done
        if parsed.is_final:
            engine.add_synthesis(
                conclusion=parsed.final_answer,
                sources=[step.id for step in engine.chain.steps]
            )
            return parsed.final_answer

        # Execute action
        if not parsed.action:
            raise ValueError(f"LLM did not provide valid action: {llm_response.value}")

        try:
            # Call the tool
            tool_result = await engine.call_tool(
                parsed.action,
                parsed.action_input or {}
            )

            observation = tool_result.value

        except Exception as e:
            observation = f"Error: {str(e)}"

        # Add observation to conversation
        conversation.append({
            "role": "assistant",
            "content": llm_response.value
        })
        conversation.append({
            "role": "user",
            "content": f"Observation: {observation}"
        })

    # Max iterations reached
    raise MaxIterationsError(
        f"Agent did not complete task in {max_iterations} iterations"
    )
```

---

## Complete Implementation

**Location**: `src/omniforge/agents/cot/autonomous.py`

```python
"""Autonomous Chain of Thought Agent with ReAct pattern.

This agent autonomously solves tasks using the ReAct (Reasoning + Acting)
pattern, where the LLM decides all actions and tool calls.
"""

import json
import re
from typing import Any, Optional

from omniforge.agents.cot.agent import CoTAgent
from omniforge.agents.cot.engine import ReasoningEngine
from omniforge.agents.models import AgentIdentity
from omniforge.tasks.models import Task
from omniforge.tools.base import ToolDefinition


class ReActParser:
    """Parser for ReAct format responses."""

    THOUGHT_PATTERN = r"Thought:\s*(.+?)(?=\n(?:Action|Final Answer):|$)"
    ACTION_PATTERN = r"Action:\s*(\w+)"
    ACTION_INPUT_PATTERN = r"Action Input:\s*({.+?}|\[.+?\])"
    FINAL_ANSWER_PATTERN = r"Final Answer:\s*(.+?)$"

    def parse(self, response: str) -> "ParsedResponse":
        """Parse LLM response into structured ReAct format."""
        thought_match = re.search(
            self.THOUGHT_PATTERN, response, re.DOTALL
        )
        thought = thought_match.group(1).strip() if thought_match else None

        # Check for final answer
        final_match = re.search(
            self.FINAL_ANSWER_PATTERN, response, re.DOTALL | re.MULTILINE
        )
        if final_match:
            return ParsedResponse(
                thought=thought,
                is_final=True,
                final_answer=final_match.group(1).strip(),
            )

        # Extract action
        action_match = re.search(self.ACTION_PATTERN, response)
        action = action_match.group(1).strip() if action_match else None

        # Extract action input
        input_match = re.search(
            self.ACTION_INPUT_PATTERN, response, re.DOTALL
        )
        if input_match:
            try:
                action_input = json.loads(input_match.group(1))
            except json.JSONDecodeError:
                action_input = None
        else:
            action_input = None

        return ParsedResponse(
            thought=thought,
            is_final=False,
            action=action,
            action_input=action_input,
        )


class ParsedResponse:
    """Parsed ReAct response."""

    def __init__(
        self,
        thought: Optional[str] = None,
        is_final: bool = False,
        final_answer: Optional[str] = None,
        action: Optional[str] = None,
        action_input: Optional[dict[str, Any]] = None,
    ):
        self.thought = thought
        self.is_final = is_final
        self.final_answer = final_answer
        self.action = action
        self.action_input = action_input


class MaxIterationsError(Exception):
    """Raised when agent exceeds maximum iterations."""
    pass


class AutonomousCoTAgent(CoTAgent):
    """Autonomous CoT Agent using ReAct pattern.

    This agent autonomously solves tasks by:
    1. Reasoning about what to do (Thought)
    2. Deciding which tool to call (Action)
    3. Observing the result (Observation)
    4. Repeating until task is complete (Final Answer)

    Users simply provide a task description, and the agent handles everything.

    Example:
        >>> agent = AutonomousCoTAgent()
        >>> task = Task(messages=[Message(parts=[TextPart(text="Analyze Q4 sales")])])
        >>> async for event in agent.process_task(task):
        ...     print(event)
    """

    identity = AgentIdentity(
        id="autonomous-cot-agent",
        name="Autonomous CoT Agent",
        description="Autonomous agent using ReAct pattern for reasoning",
        version="1.0.0",
    )

    def __init__(
        self,
        max_iterations: int = 10,
        reasoning_model: str = "claude-sonnet-4",
        temperature: float = 0.0,
        **kwargs: Any,
    ):
        """Initialize autonomous agent.

        Args:
            max_iterations: Maximum reasoning iterations before stopping
            reasoning_model: LLM model to use for reasoning
            temperature: Temperature for LLM calls (0.0 = deterministic)
            **kwargs: Additional arguments passed to CoTAgent
        """
        super().__init__(**kwargs)
        self.max_iterations = max_iterations
        self.reasoning_model = reasoning_model
        self.temperature = temperature
        self._parser = ReActParser()

    async def reason(self, task: Task, engine: ReasoningEngine) -> None:
        """Execute autonomous ReAct reasoning loop.

        This method is called by CoTAgent.process_task() and implements
        the autonomous reasoning logic.

        Args:
            task: The task to solve
            engine: Reasoning engine providing tool access
        """
        # Build system prompt with available tools
        system_prompt = self._build_system_prompt(engine)

        # Get user's task
        user_message = task.messages[-1].parts[0].text

        # Initialize conversation
        conversation = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        # ReAct loop
        for iteration in range(self.max_iterations):
            engine.add_thinking(f"Starting iteration {iteration + 1}/{self.max_iterations}")

            # Call LLM to decide next action
            llm_result = await engine.call_llm(
                messages=conversation,
                model=self.reasoning_model,
                temperature=self.temperature,
            )

            llm_response = llm_result.value

            # Parse response
            parsed = self._parser.parse(llm_response)

            # Add thought to chain
            if parsed.thought:
                engine.add_thinking(parsed.thought)

            # Check if task is complete
            if parsed.is_final:
                engine.add_synthesis(
                    conclusion=parsed.final_answer,
                    sources=[step.id for step in engine.chain.steps],
                )
                return  # Done!

            # Validate action
            if not parsed.action:
                error_msg = f"LLM did not provide valid action. Response: {llm_response}"
                engine.add_thinking(f"ERROR: {error_msg}")
                raise ValueError(error_msg)

            # Execute action
            try:
                tool_result = await engine.call_tool(
                    parsed.action, parsed.action_input or {}
                )
                observation = tool_result.value

            except Exception as e:
                observation = f"Error executing {parsed.action}: {str(e)}"
                engine.add_thinking(f"Tool execution failed: {observation}")

            # Add to conversation for next iteration
            conversation.append(
                {"role": "assistant", "content": llm_response}
            )
            conversation.append(
                {"role": "user", "content": f"Observation: {observation}"}
            )

        # Max iterations reached without completion
        raise MaxIterationsError(
            f"Agent did not complete task in {self.max_iterations} iterations"
        )

    def _build_system_prompt(self, engine: ReasoningEngine) -> str:
        """Build ReAct system prompt with tool descriptions."""
        # Get available tools
        tools = engine.get_available_tools()

        # Format tool descriptions
        tool_descriptions = self._format_tool_descriptions(tools)

        return f"""You are an autonomous AI agent that can reason and act to solve user tasks.

You have access to the following tools:

{tool_descriptions}

Use the following format for your responses:

Thought: <your reasoning about what to do next>
Action: <the tool name from the list above>
Action Input: <valid JSON arguments for the tool>
Observation: <tool result will appear here>
... (repeat Thought/Action/Action Input/Observation as many times as needed)
Thought: <final reasoning>
Final Answer: <your response to the user>

IMPORTANT RULES:
1. Always start with "Thought:" to explain your reasoning
2. After Thought, use "Action:" to specify which tool to call
3. After Action, use "Action Input:" with valid JSON arguments
4. Wait for the "Observation:" which shows the tool result
5. Continue the Thought/Action/Observation cycle until you can answer
6. When you have enough information, output "Final Answer:" with your response
7. NEVER make up tool results - always wait for real observations
8. NEVER call the same tool with same arguments twice unless needed
9. If a tool fails, try a different approach
10. Action Input MUST be valid JSON

Begin!"""

    def _format_tool_descriptions(
        self, tools: list[ToolDefinition]
    ) -> str:
        """Format tool definitions for system prompt."""
        descriptions = []

        for tool in tools:
            # Tool name and description
            desc = f"**{tool.name}**: {tool.description}\n"

            # Parameters
            if tool.parameters:
                desc += "  Parameters:\n"
                for param_name, param_info in tool.parameters.items():
                    required = "required" if param_info.get("required") else "optional"
                    param_type = param_info.get("type", "any")
                    param_desc = param_info.get("description", "")
                    default = param_info.get("default")

                    param_line = f"    - {param_name} ({param_type}, {required}"
                    if default is not None:
                        param_line += f", default={default}"
                    param_line += f"): {param_desc}\n"

                    desc += param_line

            # Returns
            if tool.returns:
                return_desc = tool.returns.get("description", "")
                desc += f"  Returns: {return_desc}\n"

            descriptions.append(desc)

        return "\n".join(descriptions)
```

---

## Usage Examples

### Example 1: Simple Task

```python
from omniforge.agents.cot.autonomous import AutonomousCoTAgent
from omniforge.tasks.models import Task, Message, TextPart

# Create agent
agent = AutonomousCoTAgent(
    max_iterations=10,
    reasoning_model="claude-sonnet-4"
)

# Create task
task = Task(
    id="task-123",
    messages=[
        Message(parts=[
            TextPart(text="What's the weather in San Francisco?")
        ])
    ]
)

# Process task - agent decides everything
async for event in agent.process_task(task):
    print(event)
```

**Agent's Autonomous Execution:**

```
Thought: I need to get weather data for San Francisco.
Action: weather_api
Action Input: {"location": "San Francisco", "units": "celsius"}
Observation: {"temperature": 18, "conditions": "partly cloudy"}

Thought: I have the weather information for San Francisco.
Final Answer: The current weather in San Francisco is 18°C with partly cloudy conditions.
```

### Example 2: Complex Multi-Step Task

```python
task = Task(
    id="task-456",
    messages=[
        Message(parts=[
            TextPart(text="Analyze Q4 sales data and identify top 3 products by revenue")
        ])
    ]
)

async for event in agent.process_task(task):
    print(event)
```

**Agent's Autonomous Execution:**

```
Thought: I need to query the database for Q4 sales data.
Action: database
Action Input: {"query": "SELECT product_id, product_name, SUM(revenue) as total_revenue FROM sales WHERE quarter='Q4' GROUP BY product_id, product_name ORDER BY total_revenue DESC LIMIT 10"}
Observation: {"rows": 10, "data": [{"product_id": 101, "product_name": "Widget Pro", "total_revenue": 45000}, ...]}

Thought: I have the sales data. Now I need to analyze it to identify the top 3 products.
Action: llm
Action Input: {"prompt": "Analyze this sales data and identify the top 3 products by revenue: [data]", "model": "gpt-3.5-turbo"}
Observation: "The top 3 products are: 1) Widget Pro ($45,000), 2) Gadget Plus ($38,000), 3) Tool Master ($32,000)"

Thought: I have completed the analysis.
Final Answer: Based on Q4 sales data, the top 3 products by revenue are:
1. Widget Pro - $45,000
2. Gadget Plus - $38,000
3. Tool Master - $32,000
```

### Example 3: Error Handling

```python
task = Task(
    id="task-789",
    messages=[
        Message(parts=[
            TextPart(text="Get data from nonexistent_api")
        ])
    ]
)

async for event in agent.process_task(task):
    print(event)
```

**Agent's Autonomous Execution:**

```
Thought: I need to call the nonexistent_api.
Action: nonexistent_api
Action Input: {}
Observation: Error executing nonexistent_api: Tool 'nonexistent_api' not found in registry

Thought: That tool doesn't exist. Let me check what tools are available and try a different approach.
Action: llm
Action Input: {"prompt": "What should I do if a requested API doesn't exist?", "model": "claude-sonnet-4"}
Observation: "If an API doesn't exist, you should inform the user and suggest alternatives..."

Thought: I understand the situation now.
Final Answer: I apologize, but the 'nonexistent_api' tool is not available. Could you please clarify what data you're looking for? I have access to database, file system, and other tools that might help.
```

---

## Configuration

The AutonomousCoTAgent can be configured:

```python
agent = AutonomousCoTAgent(
    # Reasoning configuration
    max_iterations=15,  # Allow more steps for complex tasks
    reasoning_model="claude-opus-4",  # Use more powerful model
    temperature=0.1,  # Slight randomness for creativity

    # Tool configuration
    tool_registry=custom_registry,  # Custom tools

    # Enterprise configuration
    rate_limiter=rate_limiter,
    cost_tracker=cost_tracker,

    # Storage
    chain_repository=postgres_repository,
)
```

---

## Benefits

1. **Zero Code Required**: Users just provide task description
2. **Fully Autonomous**: Agent decides all actions
3. **Transparent**: Every decision visible in reasoning chain
4. **Cost Tracked**: All LLM calls attributed with costs
5. **Error Recovery**: Agent handles failures gracefully
6. **Extensible**: Add new tools, agent uses them automatically

---

## Limitations

1. **LLM Dependent**: Quality depends on LLM reasoning ability
2. **Token Costs**: More iterations = higher costs
3. **Latency**: Each iteration requires LLM round-trip
4. **Not Guaranteed**: May not solve all tasks in max iterations
5. **Prompt Sensitivity**: Performance depends on system prompt quality

---

## Next Steps

1. Implement `AutonomousCoTAgent` in `src/omniforge/agents/cot/autonomous.py`
2. Add comprehensive tests with mocked tools
3. Create example agents for common use cases
4. Add prompt optimization and few-shot examples
5. Implement streaming token-by-token for real-time UX
6. Add HITL (Human-in-the-Loop) breakpoints for sensitive operations
