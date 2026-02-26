"""Reasoning engine for chain of thought agents.

This module provides the ReasoningEngine class that agents use to interact with tools,
build reasoning chains, and manage chain state during task execution.
"""

import asyncio
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional
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
from omniforge.agents.cot.events import ReasoningStepEvent
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
        event_queue: Optional[asyncio.Queue] = None,
    ) -> None:
        """Initialize the reasoning engine.

        Args:
            chain: Reasoning chain to record steps in
            executor: Tool executor for executing tools and LLM calls
            task: Task information dictionary (must contain 'id' and 'agent_id')
            default_llm_model: Default LLM model to use for call_llm()
            event_queue: Queue owned by the caller for real-time event streaming.
                         If not provided, a local queue is created (events are
                         still emitted but no external consumer will drain them).
        """
        self._chain = chain
        self._executor = executor
        self._task = task
        self._default_llm_model = default_llm_model
        self._event_queue: asyncio.Queue = event_queue if event_queue is not None else asyncio.Queue()

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
        self._event_queue.put_nowait(
            ReasoningStepEvent(
                task_id=self._task.get("id", "unknown"),
                timestamp=datetime.utcnow(),
                chain_id=str(self._chain.id),
                step=step,
            )
        )
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
        self._event_queue.put_nowait(
            ReasoningStepEvent(
                task_id=self._task.get("id", "unknown"),
                timestamp=datetime.utcnow(),
                chain_id=str(self._chain.id),
                step=step,
            )
        )
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
            user_id=self._task.get("user_id"),
            conversation_id=self._task.get("conversation_id"),
            trace_id=self._task.get("trace_id"),
            max_tokens=self._task.get("max_tokens"),
            max_cost_usd=self._task.get("max_cost_usd"),
            event_queue=self._event_queue,
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

        # Publish tool call and result steps to the event queue for real-time streaming
        self._event_queue.put_nowait(
            ReasoningStepEvent(
                task_id=self._task.get("id", "unknown"),
                timestamp=datetime.utcnow(),
                chain_id=str(self._chain.id),
                step=call_step,
            )
        )
        self._event_queue.put_nowait(
            ReasoningStepEvent(
                task_id=self._task.get("id", "unknown"),
                timestamp=datetime.utcnow(),
                chain_id=str(self._chain.id),
                step=result_step,
            )
        )

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

