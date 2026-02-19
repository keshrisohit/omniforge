"""Reasoning engine for chain of thought agents.

This module provides the ReasoningEngine class that agents use to interact with tools,
build reasoning chains, and manage chain state during task execution.
"""

import asyncio
from typing import TYPE_CHECKING, Any, AsyncIterator, Callable, Optional
from uuid import uuid4

from omniforge.agents.cot.chain import (
    ReasoningChain,
    ReasoningStep,
    StepType,
    SynthesisInfo,
    ThinkingInfo,
    VisibilityConfig,
    VisibilityLevel,
)
from omniforge.tools.base import ToolCallContext, ToolDefinition, ToolResult

if TYPE_CHECKING:
    from omniforge.tools.executor import ToolExecutor


class ToolCallResult:
    """Wraps a ToolResult with step references for easy synthesis.

    This class provides convenient access to both the tool call and result steps,
    making it easy to reference steps when building synthesis steps.
    """

    def __init__(
        self, result: ToolResult, call_step: ReasoningStep, result_step: ReasoningStep
    ) -> None:
        """Initialize a ToolCallResult.

        Args:
            result: The underlying ToolResult from execution
            call_step: The TOOL_CALL step that initiated the execution
            result_step: The TOOL_RESULT step containing the outcome
        """
        self.result = result
        self.call_step = call_step
        self.result_step = result_step

    @property
    def step_id(self) -> str:
        """Get the result step ID (commonly used for synthesis references).

        Returns:
            The UUID of the result step as a string
        """
        return str(self.result_step.id)

    @property
    def success(self) -> bool:
        """Check if the tool execution succeeded.

        Returns:
            True if execution succeeded, False otherwise
        """
        return self.result.success

    @property
    def value(self) -> Optional[dict[str, Any]]:
        """Get the result value if successful.

        Returns:
            Result data dictionary, or None if failed
        """
        return self.result.result

    @property
    def error(self) -> Optional[str]:
        """Get the error message if failed.

        Returns:
            Error message string, or None if successful
        """
        return self.result.error


class ReasoningEngine:
    """High-level API for agents to interact with tools and build reasoning chains.

    The ReasoningEngine provides convenience methods for:
    - Adding thinking and synthesis steps
    - Calling LLMs with simplified interface
    - Executing arbitrary tools
    - Managing chain state
    - Yielding steps as events during reasoning
    """

    def __init__(
        self,
        chain: ReasoningChain,
        executor: "ToolExecutor",
        task: dict[str, Any],
        default_llm_model: str = "claude-sonnet-4",
    ) -> None:
        """Initialize the reasoning engine.

        Args:
            chain: Reasoning chain to record steps in
            executor: Tool executor for executing tools and LLM calls
            task: Task information dictionary (must contain 'id' and 'agent_id')
            default_llm_model: Default LLM model to use for call_llm()
        """
        self._chain = chain
        self._executor = executor
        self._task = task
        self._default_llm_model = default_llm_model

    @property
    def chain(self) -> ReasoningChain:
        """Get the reasoning chain.

        Returns:
            The ReasoningChain being built
        """
        return self._chain

    @property
    def task(self) -> dict[str, Any]:
        """Get the task information.

        Returns:
            Task dictionary with id, agent_id, and other metadata
        """
        return self._task

    def add_thinking(self, thought: str, confidence: Optional[float] = None) -> ReasoningStep:
        """Add a thinking step to the chain.

        Args:
            thought: The reasoning or thought content
            confidence: Optional confidence level (0.0-1.0)

        Returns:
            The created ReasoningStep
        """
        step = ReasoningStep(
            step_number=0,  # Will be updated by chain.add_step
            type=StepType.THINKING,
            thinking=ThinkingInfo(content=thought, confidence=confidence),
        )
        self._chain.add_step(step)
        return step

    def add_synthesis(self, conclusion: str, sources: list[str]) -> ReasoningStep:
        """Add a synthesis step that combines results from previous steps.

        Args:
            conclusion: The synthesized conclusion or answer
            sources: List of step IDs used as sources (as strings)

        Returns:
            The created ReasoningStep
        """
        from uuid import UUID

        # Convert string step IDs to UUIDs
        source_uuids = [UUID(source_id) for source_id in sources]

        step = ReasoningStep(
            step_number=0,  # Will be updated by chain.add_step
            type=StepType.SYNTHESIS,
            synthesis=SynthesisInfo(content=conclusion, sources=source_uuids),
        )
        self._chain.add_step(step)
        return step

    async def call_llm(
        self,
        prompt: Optional[str] = None,
        messages: Optional[list[dict[str, str]]] = None,
        model: Optional[str] = None,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        visibility: Optional[VisibilityLevel] = None,
    ) -> ToolCallResult:
        """Call an LLM with simplified interface.

        Convenience wrapper around call_tool() for LLM calls. Either prompt
        or messages must be provided.

        Args:
            prompt: Simple prompt string (converted to user message)
            messages: List of message dicts with 'role' and 'content'
            model: LLM model to use (defaults to default_llm_model)
            system: System prompt for the LLM
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            visibility: Visibility level for the call (defaults to FULL)

        Returns:
            ToolCallResult wrapping the LLM response

        Raises:
            ValueError: If neither prompt nor messages is provided
        """
        if prompt is None and messages is None:
            raise ValueError("Either 'prompt' or 'messages' must be provided")

        # Build arguments for LLM tool
        arguments: dict[str, Any] = {
            "model": model or self._default_llm_model,
            "temperature": temperature,
            "response_format": {"type": "json_object"},  # Force JSON mode for ReAct pattern
        }

        # Handle prompt vs messages
        if prompt is not None:
            arguments["messages"] = [{"role": "user", "content": prompt}]
        else:
            arguments["messages"] = messages

        # Add optional parameters
        if system is not None:
            arguments["system"] = system
        if max_tokens is not None:
            arguments["max_tokens"] = max_tokens

        # Use call_tool to execute LLM
        return await self.call_tool("llm", arguments, visibility=visibility)

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        visibility: Optional[VisibilityLevel] = None,
    ) -> ToolCallResult:
        """Execute any registered tool and return wrapped result.

        Args:
            tool_name: Name of the tool to execute
            arguments: Arguments to pass to the tool
            visibility: Optional visibility level for the tool call

        Returns:
            ToolCallResult wrapping the tool execution result
        """
        # Build tool call context
        context = ToolCallContext(
            correlation_id=str(uuid4()),
            task_id=self._task.get("id", "unknown"),
            agent_id=self._task.get("agent_id", "unknown"),
            tenant_id=self._task.get("tenant_id"),
            chain_id=self._task.get("chain_id"),
            max_tokens=self._task.get("max_tokens"),
            max_cost_usd=self._task.get("max_cost_usd"),
        )

        # Execute tool through executor (adds steps to chain)
        result = await self._executor.execute(
            tool_name=tool_name, arguments=arguments, context=context, chain=self._chain
        )

        # Find the tool call and result steps added by executor
        # The executor adds exactly 2 steps: TOOL_CALL and TOOL_RESULT
        call_step = self._chain.steps[-2]
        result_step = self._chain.steps[-1]

        # Override visibility if specified
        if visibility is not None:
            call_step.visibility = VisibilityConfig(level=visibility)
            result_step.visibility = VisibilityConfig(level=visibility)

        return ToolCallResult(result=result, call_step=call_step, result_step=result_step)

    def get_available_tools(self) -> list[ToolDefinition]:
        """Get list of all available tool definitions from the registry.

        Returns:
            List of ToolDefinition objects for all registered tools
        """
        # Access the registry through the executor
        registry = self._executor._registry
        tool_names = registry.list_tools()

        # Get definitions for all tools
        definitions = []
        for name in tool_names:
            try:
                definition = registry.get_definition(name)
                definitions.append(definition)
            except Exception:
                # Skip tools that can't be retrieved
                continue

        return definitions

    async def execute_reasoning(
        self, reasoning_func: Callable[["ReasoningEngine"], AsyncIterator[ReasoningStep]]
    ) -> AsyncIterator[ReasoningStep]:
        """Execute a reasoning function and yield steps as they're created.

        This async generator wraps a reasoning function and yields steps as they
        are added to the chain. Useful for streaming reasoning to clients.

        Args:
            reasoning_func: Async generator function that takes this engine
                          and yields reasoning steps

        Yields:
            ReasoningStep objects as they are created during reasoning

        Example:
            async def my_reasoning(engine: ReasoningEngine):
                engine.add_thinking("Starting analysis...")
                result = await engine.call_llm(prompt="Analyze this...")
                engine.add_synthesis("Conclusion", [result.step_id])

            async for step in engine.execute_reasoning(my_reasoning):
                print(f"New step: {step.type}")
        """
        # Track initial step count
        initial_step_count = len(self._chain.steps)
        steps_yielded = 0

        # Create a queue for new steps
        step_queue: asyncio.Queue[Optional[ReasoningStep]] = asyncio.Queue()
        execution_complete = False

        # Create a polling task that watches for new steps
        async def poll_for_steps() -> None:
            """Poll the chain for new steps and add them to the queue."""
            nonlocal steps_yielded
            while not execution_complete:
                current_count = len(self._chain.steps)
                expected_count = initial_step_count + steps_yielded
                if current_count > expected_count:
                    # New steps were added
                    for i in range(expected_count, current_count):
                        await step_queue.put(self._chain.steps[i])
                        steps_yielded += 1
                await asyncio.sleep(0.001)  # Small delay to avoid busy waiting

        # Create a task to execute the reasoning function
        async def execute_and_signal() -> None:
            """Execute the reasoning function and signal completion."""
            nonlocal execution_complete
            async for step in reasoning_func(self):
                # The function already adds steps to chain, just continue
                pass
            # Give polling loop a chance to catch final steps
            await asyncio.sleep(0.01)
            execution_complete = True
            # Signal completion
            await step_queue.put(None)

        # Start both tasks
        polling_task = asyncio.create_task(poll_for_steps())
        execution_task = asyncio.create_task(execute_and_signal())

        try:
            # Yield steps as they arrive in the queue
            while True:
                step = await step_queue.get()
                if step is None:
                    # Completion signal received
                    break
                yield step

            # Wait for execution to complete
            await execution_task
        finally:
            # Clean up polling task
            polling_task.cancel()
            try:
                await polling_task
            except asyncio.CancelledError:
                pass
