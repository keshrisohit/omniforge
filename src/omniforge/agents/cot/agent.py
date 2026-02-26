"""CoT agent base class with visible reasoning.

This module provides the CoTAgent abstract base class that extends BaseAgent
with chain of thought capabilities. All reasoning steps are tracked in a
ReasoningChain and streamed as events for real-time visibility.
"""

import asyncio
from abc import abstractmethod
from datetime import datetime
from typing import TYPE_CHECKING, Any, AsyncIterator, Optional
from uuid import UUID

from omniforge.agents.base import BaseAgent
from omniforge.agents.cot.chain import ChainStatus, ReasoningChain
from omniforge.agents.cot.engine import ReasoningEngine
from omniforge.agents.cot.events import (
    ChainCompletedEvent,
    ChainFailedEvent,
    ChainStartedEvent,
)
from omniforge.agents.events import TaskDoneEvent, TaskEvent, TaskStatusEvent
from omniforge.agents.models import AgentCapabilities, AgentIdentity, AgentSkill
from omniforge.tasks.models import Task, TaskState
from omniforge.tools.registry import ToolRegistry
from omniforge.tools.setup import get_default_tool_registry

if TYPE_CHECKING:
    pass


class CoTAgent(BaseAgent):
    """Abstract base class for agents with chain of thought capabilities.

    This class extends BaseAgent to provide visible reasoning through
    ReasoningChain tracking. All tool calls, thoughts, and synthesis steps
    are captured in the chain and streamed as events.

    Subclasses must:
    - Define class-level identity, capabilities, and skills
    - Implement the abstract reason() method

    The process_task() method orchestrates the reasoning lifecycle:
    1. Create reasoning chain
    2. Emit chain started event
    3. Call reason() to perform agent-specific reasoning
    4. Yield reasoning step events as they occur
    5. Persist chain and emit completion/failure events

    Class Attributes:
        identity: Agent identity information
        capabilities: Agent capabilities configuration
        skills: List of skills the agent provides

    Instance Attributes:
        _tool_registry: Registry of available tools
        _executor: Tool executor for running tools
        _chain_repository: Optional repository for persisting chains
        _rate_limiter: Optional rate limiter for quota enforcement
        _cost_tracker: Optional cost tracker for budget enforcement

    Example:
        >>> class MyCoTAgent(CoTAgent):
        ...     identity = AgentIdentity(
        ...         id="my-cot-agent",
        ...         name="My CoT Agent",
        ...         description="Reasons with visible steps",
        ...         version="1.0.0"
        ...     )
        ...     capabilities = AgentCapabilities(streaming=True)
        ...     skills = []
        ...
        ...     async def reason(
        ...         self, task: Task, engine: ReasoningEngine
        ...     ) -> str:
        ...         engine.add_thinking("Analyzing task...")
        ...         result = await engine.call_llm(prompt="Solve this task")
        ...         return result.result.value
    """

    # Class-level attributes (subclasses must define)
    identity: AgentIdentity
    capabilities: AgentCapabilities
    skills: list[AgentSkill]

    def __init__(
        self,
        agent_id: Optional[UUID] = None,
        tenant_id: Optional[str] = None,
        tool_registry: Optional[ToolRegistry] = None,
        chain_repository: Optional[Any] = None,  # type: ignore[assignment]
        rate_limiter: Optional[Any] = None,  # type: ignore[assignment]
        cost_tracker: Optional[Any] = None,  # type: ignore[assignment]
        backend: Optional[Any] = None,
    ) -> None:
        """Initialize CoT agent with reasoning infrastructure.

        Args:
            agent_id: Optional explicit UUID for the agent instance
            tenant_id: Optional tenant identifier for multi-tenancy
            tool_registry: Registry of available tools (uses default if not provided)
            chain_repository: Optional repository for persisting chains (Phase 6)
            rate_limiter: Optional rate limiter for quota enforcement (Phase 5)
            cost_tracker: Optional cost tracker for budget enforcement (Phase 5)
            backend: Execution backend (defaults to InProcessBackend)
        """
        from omniforge.tools.executor import ToolExecutor

        super().__init__(agent_id=agent_id, tenant_id=tenant_id)
        self._tool_registry = tool_registry or get_default_tool_registry()
        self._executor = ToolExecutor(
            registry=self._tool_registry,
            rate_limiter=rate_limiter,
            cost_tracker=cost_tracker,
            backend=backend,
        )
        self._chain_repository = chain_repository
        self._rate_limiter = rate_limiter
        self._cost_tracker = cost_tracker

    async def process_task(self, task: Task) -> AsyncIterator[TaskEvent]:
        """Process a task with visible chain of thought reasoning.

        This method orchestrates the complete reasoning lifecycle:
        1. Creates a new ReasoningChain
        2. Emits ChainStartedEvent and TaskStatusEvent(WORKING)
        3. Creates ReasoningEngine with an event queue
        4. Runs reason() as a background asyncio task
        5. Drains events from queue in real-time, yielding them as they arrive
        6. On success: persists chain, emits ChainCompletedEvent, TaskDoneEvent(COMPLETED)
        7. On failure: persists chain, emits ChainFailedEvent, TaskDoneEvent(FAILED)

        Args:
            task: The task to process

        Yields:
            TaskEvent objects representing reasoning progress and completion
        """
        # Create reasoning chain
        chain = ReasoningChain(
            task_id=task.id,
            agent_id=str(self._id),
            status=ChainStatus.RUNNING,
        )

        # Emit chain started event
        yield ChainStartedEvent(
            task_id=task.id,
            timestamp=datetime.utcnow(),
            chain_id=str(chain.id),
        )

        # Emit working status
        yield TaskStatusEvent(
            task_id=task.id,
            timestamp=datetime.utcnow(),
            state=TaskState.WORKING,
        )

        # CoTAgent owns the queue — it creates it and passes it to the engine.
        # The engine and anything it calls (tools, sub-agents) publish to this queue;
        # CoTAgent is the sole consumer draining it.
        event_queue: asyncio.Queue = asyncio.Queue()

        # Create reasoning engine, injecting the caller-owned queue
        engine = ReasoningEngine(
            chain=chain,
            executor=self._executor,
            task=task.model_dump(),
            event_queue=event_queue,
        )

        # Sentinel object signals reason() completion
        _done = object()

        async def _run_reason() -> str:
            try:
                return await self.reason(task, engine)
            finally:
                # Always signal completion, even on exception
                event_queue.put_nowait(_done)

        # Run reason() as background task so we can drain the queue concurrently
        reason_task = asyncio.create_task(_run_reason())

        # Stream events as they arrive from the engine queue
        while True:
            item = await event_queue.get()
            if item is _done:
                break
            yield item  # ReasoningStepEvent or forwarded TaskMessageEvent from sub-agents

        try:
            # Get result (or re-raise any exception from reason())
            final_answer = await reason_task

            # Emit message event with final answer
            if final_answer:
                from omniforge.agents.events import TaskMessageEvent
                from omniforge.agents.models import TextPart

                yield TaskMessageEvent(
                    task_id=task.id,
                    timestamp=datetime.utcnow(),
                    message_parts=[TextPart(text=final_answer)],
                    is_partial=False,
                )

            # Update chain status to completed
            chain.status = ChainStatus.COMPLETED
            chain.completed_at = datetime.utcnow()

            # Persist chain if repository available
            if self._chain_repository:
                await self._chain_repository.save(chain)

            # Emit chain completed event
            yield ChainCompletedEvent(
                task_id=task.id,
                timestamp=datetime.utcnow(),
                chain_id=str(chain.id),
                metrics=chain.metrics,
            )

            # Emit task done event
            yield TaskDoneEvent(
                task_id=task.id,
                timestamp=datetime.utcnow(),
                final_state=TaskState.COMPLETED,
            )

        except Exception as e:
            # Update chain status to failed
            chain.status = ChainStatus.FAILED
            chain.completed_at = datetime.utcnow()

            # Persist chain if repository available
            if self._chain_repository:
                await self._chain_repository.save(chain)

            # Emit chain failed event
            yield ChainFailedEvent(
                task_id=task.id,
                timestamp=datetime.utcnow(),
                chain_id=str(chain.id),
                error_code="REASONING_FAILED",
                error_message=str(e),
            )

            # Emit task done event with failed state
            yield TaskDoneEvent(
                task_id=task.id,
                timestamp=datetime.utcnow(),
                final_state=TaskState.FAILED,
            )

    @abstractmethod
    async def reason(self, task: Task, engine: ReasoningEngine) -> str:
        """Perform agent-specific reasoning to solve the task.

        This is the core method that subclasses must implement. It receives
        a task and a reasoning engine, and uses the engine to perform
        visible reasoning steps.

        The engine provides:
        - add_thinking(): Add a thinking step
        - call_llm(): Call an LLM as a tool
        - call_tool(): Call any registered tool
        - get_available_tools(): Get list of available tools

        Args:
            task: The task to solve
            engine: The reasoning engine for adding steps and calling tools

        Returns:
            The final answer/result as a string

        Raises:
            Exception: Any error during reasoning

        Example:
            >>> async def reason(self, task: Task, engine: ReasoningEngine) -> str:
            ...     # Add thinking step
            ...     engine.add_thinking("I need to analyze the user's request")
            ...
            ...     # Call LLM
            ...     result = await engine.call_llm(
            ...         prompt=task.messages[0].parts[0].text
            ...     )
            ...
            ...     # Synthesize result
            ...     engine.add_synthesis(
            ...         summary="Completed analysis",
            ...         source_step_ids=[result.step_id]
            ...     )
            ...
            ...     return result.result.value
        """
        pass
