"""Autonomous CoT agent with ReAct pattern.

This module provides the AutonomousCoTAgent that implements fully autonomous
reasoning using the ReAct (Reasoning + Acting) pattern. Users provide a task
description, and the agent autonomously decides actions, generates prompts,
and determines when to stop.
"""

from typing import Any

from omniforge.agents.cot.agent import CoTAgent
from omniforge.agents.cot.engine import ReasoningEngine
from omniforge.agents.cot.parser import ReActParser
from omniforge.agents.cot.prompts import build_react_system_prompt
from omniforge.agents.models import (
    AgentCapabilities,
    AgentIdentity,
    AgentSkill,
    SkillInputMode,
    SkillOutputMode,
)
from omniforge.tasks.models import Task


class MaxIterationsError(Exception):
    """Raised when autonomous agent reaches maximum reasoning iterations.

    This prevents infinite loops in the ReAct reasoning process by enforcing
    a maximum number of thought/action cycles.

    Attributes:
        max_iterations: The maximum allowed iterations
        final_conversation: The conversation history up to this point
    """

    def __init__(self, max_iterations: int, final_conversation: list[dict[str, str]]) -> None:
        """Initialize error with iteration limit and conversation history.

        Args:
            max_iterations: The maximum allowed iterations
            final_conversation: The conversation messages before termination
        """
        super().__init__(
            f"Agent reached maximum iterations ({max_iterations}) without "
            f"producing a final answer"
        )
        self.max_iterations = max_iterations
        self.final_conversation = final_conversation


class AutonomousCoTAgent(CoTAgent):
    """Fully autonomous agent using the ReAct reasoning pattern.

    This agent implements the ReAct (Reasoning + Acting) pattern for autonomous
    task solving. Given a task description, it autonomously:
    1. Reasons about what to do next (Thought)
    2. Takes an action by calling a tool (Action + Action Input)
    3. Observes the result (Observation)
    4. Repeats until it has enough information to provide a final answer

    The agent uses zero-temperature LLM calls for deterministic reasoning and
    maintains a conversation history across iterations for context.

    Class Attributes:
        identity: Agent identity information for A2A protocol
        capabilities: Agent capabilities (streaming enabled)
        skills: List of skills (empty - tool-based, not skill-based)

    Instance Attributes:
        _max_iterations: Maximum reasoning iterations before failure
        _reasoning_model: LLM model to use for reasoning
        _temperature: Temperature for LLM calls (0.0 for deterministic)
        _parser: ReAct response parser

    Example:
        >>> agent = AutonomousCoTAgent(
        ...     max_iterations=10,
        ...     reasoning_model="claude-sonnet-4",
        ...     temperature=0.0
        ... )
        >>> async for event in agent.process_task(task):
        ...     print(event)  # Stream reasoning steps and completion
    """

    identity = AgentIdentity(
        id="autonomous-cot-agent",
        name="Autonomous CoT Agent",
        description="Fully autonomous agent using ReAct pattern for task solving",
        version="1.0.0",
    )
    capabilities = AgentCapabilities(streaming=True)
    skills = [
        AgentSkill(
            id="autonomous-task-solving",
            name="Autonomous Task Solving",
            description="Solve tasks autonomously using ReAct pattern with available tools",
            input_modes=[SkillInputMode.TEXT],
            output_modes=[SkillOutputMode.TEXT],
        )
    ]

    def __init__(
        self,
        max_iterations: int = 10,
        reasoning_model: str = "claude-sonnet-4",
        temperature: float = 0.0,
        **kwargs: Any,
    ) -> None:
        """Initialize autonomous agent with ReAct configuration.

        Args:
            max_iterations: Maximum reasoning iterations before failure (default: 10)
            reasoning_model: LLM model for reasoning (default: "claude-sonnet-4")
            temperature: LLM temperature for determinism (default: 0.0)
            **kwargs: Additional arguments passed to CoTAgent (agent_id, tenant_id, etc.)
        """
        super().__init__(**kwargs)
        self._max_iterations = max_iterations
        self._reasoning_model = reasoning_model
        self._temperature = temperature
        self._parser = ReActParser()

    async def reason(self, task: Task, engine: ReasoningEngine) -> str:
        """Perform autonomous reasoning using the ReAct pattern.

        This method implements the core ReAct loop:
        1. Build system prompt with available tools
        2. Initialize conversation with user's task
        3. For each iteration:
           - Call LLM to get Thought/Action or Final Answer
           - Parse response to extract action or answer
           - If final answer: return
           - Execute tool action and observe result
           - Add observation to conversation
        4. Raise MaxIterationsError if no answer after max iterations

        Args:
            task: The task to solve
            engine: The reasoning engine for tool calls and chain tracking

        Returns:
            The final answer string

        Raises:
            MaxIterationsError: If max iterations reached without final answer
            ValueError: If LLM produces invalid response (no action or final answer)
        """
        # Build system prompt with available tools
        system_prompt = self._build_system_prompt(engine)

        # Initialize conversation with system and user message
        conversation: list[dict[str, str]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": self._extract_user_message(task)},
        ]

        # Execute ReAct loop
        for iteration in range(self._max_iterations):
            # Add thinking step for iteration tracking
            engine.add_thinking(
                f"ReAct iteration {iteration + 1}/{self._max_iterations}",
                confidence=None,
            )

            # Call LLM with conversation history
            llm_result = await engine.call_llm(
                messages=conversation,
                model=self._reasoning_model,
                temperature=self._temperature,
            )

            # Get the LLM response text
            llm_response = llm_result.result.result.get("content", "") if llm_result.result.result else ""

            # Parse the response
            parsed = self._parser.parse(llm_response)

            # Add thought to chain if present
            if parsed.thought:
                engine.add_thinking(f"Thought: {parsed.thought}", confidence=None)

            # Check for final answer
            if parsed.is_final:
                engine.add_synthesis(
                    conclusion="Agent reached final answer",
                    sources=[llm_result.step_id],
                )
                # Use final_answer if provided, otherwise use a default message
                return parsed.final_answer or "Task completed."

            # Extract action
            if not parsed.action:
                raise ValueError(
                    f"LLM response contained neither action nor final answer: {llm_response}"
                )

            # Execute tool action
            try:
                tool_result = await engine.call_tool(
                    tool_name=parsed.action,
                    arguments=parsed.action_input or {},
                )

                # Format observation
                observation = f"Observation: {tool_result.result.result if tool_result.result.result else 'No result'}"

            except Exception as e:
                # Handle tool execution errors gracefully
                observation = f"Observation: Tool execution failed with error: {str(e)}"
                engine.add_thinking(f"Tool execution error: {str(e)}", confidence=0.0)

            # Append assistant response and observation to conversation
            conversation.append({"role": "assistant", "content": llm_response})
            conversation.append({"role": "user", "content": observation})

        # Max iterations reached without final answer
        raise MaxIterationsError(self._max_iterations, conversation)

    def _build_system_prompt(self, engine: ReasoningEngine) -> str:
        """Build ReAct system prompt with available tools.

        Args:
            engine: The reasoning engine to get tool definitions from

        Returns:
            Complete ReAct system prompt with tool descriptions
        """
        tools = engine.get_available_tools()
        return build_react_system_prompt(tools)

    def _extract_user_message(self, task: Task) -> str:
        """Extract user message content from task.

        Args:
            task: The task containing user messages

        Returns:
            The text content from the first user message
        """
        if not task.messages:
            return "Please help me with this task."

        # Get first message parts
        first_message = task.messages[0]
        if not first_message.parts:
            return "Please help me with this task."

        # Extract text from first part
        first_part = first_message.parts[0]
        if hasattr(first_part, "text"):
            return first_part.text

        return "Please help me with this task."
