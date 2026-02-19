"""Simple autonomous agent with minimal API.

This module provides SimpleAutonomousAgent - a batteries-included autonomous agent
that requires minimal configuration. Just provide a system prompt and user message,
and the agent handles tool selection, execution, and iteration automatically.
"""

from typing import Any, Optional

from omniforge.agents.cot.agent import CoTAgent
from omniforge.agents.cot.engine import ReasoningEngine
from omniforge.agents.cot.parser import ReActParser
from omniforge.agents.cot.prompts import build_react_system_prompt
from omniforge.agents.helpers import create_simple_task, get_latest_user_message
from omniforge.agents.models import (
    AgentCapabilities,
    AgentIdentity,
    AgentSkill,
    SkillInputMode,
    SkillOutputMode,
)
from omniforge.tasks.models import Task
from omniforge.tools.registry import ToolRegistry
from omniforge.tools.setup import get_default_tool_registry


class SimpleAutonomousAgent(CoTAgent):
    """Dead-simple autonomous agent with ReAct pattern.

    This agent provides the simplest possible interface for autonomous tool-using agents:
    1. Create agent with optional system prompt
    2. Call run() with user message
    3. Get final answer back

    The agent autonomously:
    - Decides which tools to use
    - Executes tools with correct arguments
    - Iterates until task is solved
    - Returns final answer

    Features:
    - Zero boilerplate - just create and run
    - Configurable system prompt for custom behavior
    - Built-in ReAct reasoning loop
    - Automatic tool selection from registry
    - Streaming support for real-time visibility

    Example:
        >>> # Basic usage
        >>> agent = SimpleAutonomousAgent()
        >>> result = await agent.run("Find all Python files in src/")
        >>> print(result)

        >>> # Custom system prompt
        >>> agent = SimpleAutonomousAgent(
        ...     system_prompt="You are a file organization expert. Be concise."
        ... )
        >>> result = await agent.run("Organize the files by type")

        >>> # Custom configuration
        >>> agent = SimpleAutonomousAgent(
        ...     max_iterations=20,
        ...     model="gpt-4",
        ...     temperature=0.0,
        ... )
        >>> result = await agent.run("Complex task here...")
    """

    identity = AgentIdentity(
        id="simple-autonomous-agent",
        name="Simple Autonomous Agent",
        description="Zero-config autonomous agent with ReAct pattern",
        version="1.0.0",
    )

    capabilities = AgentCapabilities(
        streaming=True,
        multi_turn=False,
        push_notifications=False,
        hitl_support=False,
    )

    skills = [
        AgentSkill(
            id="autonomous-execution",
            name="Autonomous Execution",
            description="Autonomously solve tasks using available tools",
            input_modes=[SkillInputMode.TEXT],
            output_modes=[SkillOutputMode.TEXT],
        )
    ]

    def __init__(
        self,
        system_prompt: Optional[str] = None,
        max_iterations: int = 15,
        model: str = "claude-sonnet-4",
        temperature: float = 0.0,
        tool_registry: Optional[ToolRegistry] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize simple autonomous agent.

        Args:
            system_prompt: Optional custom system prompt to guide agent behavior.
                         If not provided, uses default ReAct prompt.
            max_iterations: Maximum reasoning iterations before stopping (default: 15)
            model: LLM model to use for reasoning (default: "claude-sonnet-4")
            temperature: Temperature for LLM calls (default: 0.0 for deterministic)
            tool_registry: Optional custom tool registry (uses default if not provided)
            **kwargs: Additional arguments passed to CoTAgent

        Example:
            >>> agent = SimpleAutonomousAgent(
            ...     system_prompt="You are a helpful coding assistant.",
            ...     max_iterations=20,
            ...     model="gpt-4",
            ... )
        """
        super().__init__(tool_registry=tool_registry or get_default_tool_registry(), **kwargs)

        self._custom_system_prompt = system_prompt
        self._max_iterations = max_iterations
        self._model = model
        self._temperature = temperature
        self._parser = ReActParser()

    async def reason(self, task: Task, engine: ReasoningEngine) -> str:
        """Execute autonomous ReAct reasoning loop.

        This method implements the complete ReAct pattern:
        1. Build system prompt with tools (or use custom prompt)
        2. Initialize conversation with user message
        3. Iterate: Think → Act → Observe
        4. Return final answer when agent decides task is complete

        Args:
            task: The task to solve
            engine: Reasoning engine for tool calls

        Returns:
            Final answer as string

        Raises:
            RuntimeError: If max iterations reached without answer
            ValueError: If LLM produces invalid response
        """
        # Build system prompt
        system_prompt = self._build_system_prompt(engine)

        # Extract current user message (latest user message in task)
        user_message = self._extract_user_message(task)

        # Initialize conversation with history context from prior task messages
        conversation: list[dict[str, str]] = [
            {
                "role": "user",
                "content": self._build_user_content_with_history(task, user_message),
            },
        ]

        # Execute ReAct loop
        for iteration in range(self._max_iterations):
            # Track iteration
            engine.add_thinking(
                f"Iteration {iteration + 1}/{self._max_iterations}: Analyzing next step",
                confidence=None,
            )

            # Get LLM decision (pass system separately, not in messages)
            llm_result = await engine.call_llm(
                messages=conversation,
                system=system_prompt,
                model=self._model,
                temperature=self._temperature,
            )

            # Check if LLM call succeeded
            if not llm_result.success or not llm_result.value:
                raise RuntimeError(f"LLM call failed: {llm_result.error}")

            llm_response = llm_result.value.get("content", "")

            # Parse response for action or final answer
            parsed = self._parser.parse(llm_response)

            # Log thought if present
            if parsed.thought:
                engine.add_thinking(f"Thought: {parsed.thought}", confidence=None)

            # Check for final answer
            if parsed.is_final:
                # Use final_answer if provided, otherwise use a default message
                final_message = parsed.final_answer or "Task completed."
                engine.add_synthesis(
                    conclusion=f"Task completed: {final_message}",
                    sources=[llm_result.step_id],
                )
                return final_message

            # Must have an action if not final
            if not parsed.action:
                raise ValueError(
                    f"LLM response has no action or final answer: {llm_response[:200]}"
                )

            # Execute tool action
            engine.add_thinking(f"Action: {parsed.action}", confidence=None)

            try:
                tool_result = await engine.call_tool(
                    tool_name=parsed.action,
                    arguments=parsed.action_input or {},
                )

                # Format observation
                if tool_result.success:
                    result_value = tool_result.value
                    # Truncate large results for context efficiency
                    result_str = str(result_value)
                    if len(result_str) > 2000:
                        result_str = result_str[:2000] + "...(truncated)"
                    observation = f"Observation: {result_str}"
                else:
                    observation = f"Observation: Error - {tool_result.error}"

            except Exception as e:
                observation = f"Observation: Tool execution failed - {str(e)}"

                engine.add_thinking(f"Tool error: {str(e)}", confidence=0.0)
                raise e


            # Add to conversation
            conversation.append({"role": "assistant", "content": llm_response})
            conversation.append({"role": "user", "content": observation})

        # Max iterations reached
        raise RuntimeError(
            f"Agent reached maximum iterations ({self._max_iterations}) "
            f"without producing final answer. Last conversation:\n"
            f"{conversation[-2:]}"
        )

    async def run(self, prompt: str, user_id: str = "default-user") -> str:
        """Simple API to run agent with a user prompt.

        This is the main entry point - just pass a prompt and get an answer.

        Args:
            prompt: The user's message/task description
            user_id: Optional user identifier

        Returns:
            The agent's final answer as a string

        Example:
            >>> agent = SimpleAutonomousAgent()
            >>> result = await agent.run("Count Python files in src/")
            >>> print(result)  # "Found 42 Python files in src/ directory"

        Raises:
            RuntimeError: If agent fails to complete task
        """
        # Create task
        task = create_simple_task(
            message=prompt,
            agent_id=self.identity.id,
            user_id=user_id,
            tenant_id=self.tenant_id,
        )

        # Process task and extract final answer
        final_answer = ""

        async for event in self.process_task(task):
            # Look for message events containing the final answer
            if hasattr(event, "message_parts"):
                for part in event.message_parts:
                    if hasattr(part, "text"):
                        final_answer += part.text

        return final_answer

    def _build_system_prompt(self, engine: ReasoningEngine) -> str:
        """Build system prompt with tool descriptions.

        Args:
            engine: Reasoning engine to get tools from

        Returns:
            Complete system prompt with tool descriptions
        """
        if self._custom_system_prompt:
            # Use custom prompt but append tool descriptions
            tools = engine.get_available_tools()
            base_prompt = build_react_system_prompt(tools)

            # Combine custom prompt with tool format
            return f"""{self._custom_system_prompt}

{base_prompt}"""
        else:
            # Use default ReAct prompt
            tools = engine.get_available_tools()
            return build_react_system_prompt(tools)

    def _extract_user_message(self, task: Task) -> str:
        """Extract the current (latest) user message from task.

        Args:
            task: Task containing messages

        Returns:
            Text of the latest user message, or a default prompt if none found
        """
        return get_latest_user_message(task) or "Please help me with this task."

    def _build_user_content_with_history(self, task: Task, current_message: str) -> str:
        """Build the initial LLM user content, prepending prior conversation history.

        Prior task messages (all except the last user message) are formatted as a
        readable context block so the LLM can reference what was previously discussed.
        The JSON mode reminder is always appended.

        Args:
            task: Task containing conversation history in task.messages
            current_message: The current user message text

        Returns:
            Full content string for the first conversation turn
        """
        json_reminder = (
            "\n\nIMPORTANT: Respond with valid JSON only as specified in the system prompt."
        )

        # Prior messages = everything except the last (current user message)
        history_messages = task.messages[:-1] if len(task.messages) > 1 else []
        if not history_messages:
            return f"{current_message}{json_reminder}"

        history_lines = []
        for msg in history_messages:
            role_str = msg.role if isinstance(msg.role, str) else str(msg.role)
            role_label = "User" if role_str == "user" else "Assistant"
            text_parts = [p.text for p in msg.parts if hasattr(p, "text")]
            text = " ".join(text_parts).strip()
            if text:
                history_lines.append(f"{role_label}: {text}")

        if not history_lines:
            return f"{current_message}{json_reminder}"

        context = "## Conversation History\n" + "\n".join(history_lines) + "\n\n"
        return f"{context}{current_message}{json_reminder}"


# Convenience function for one-shot usage
async def run_autonomous_agent(
    prompt: str,
    system_prompt: Optional[str] = None,
    max_iterations: int = 15,
    model: str = "groq/llama-3.1-8b-instant",
    temperature: float = 0.0,
    tool_registry: Optional[ToolRegistry] = None,
) -> str:
    """One-shot function to run autonomous agent with a prompt.

    This is the absolute simplest way to use an autonomous agent:
    just call this function with a prompt and get a result.

    Args:
        prompt: User prompt/task description
        system_prompt: Optional custom system instructions
        max_iterations: Max reasoning iterations
        model: LLM model to use
        temperature: LLM temperature
        tool_registry: Optional custom tool registry

    Returns:
        Final answer as string

    Example:
        >>> result = await run_autonomous_agent(
        ...     "Find all TODO comments in Python files"
        ... )
        >>> print(result)

        >>> # With custom system prompt
        >>> result = await run_autonomous_agent(
        ...     "Analyze the codebase",
        ...     system_prompt="You are a senior code reviewer. Be critical."
        ... )
    """
    agent = SimpleAutonomousAgent(
        system_prompt=system_prompt,
        max_iterations=max_iterations,
        model=model,
        temperature=temperature,
        tool_registry=tool_registry,
    )

    return await agent.run(prompt)
