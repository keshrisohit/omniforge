"""Sub-agent delegation tool for hierarchical agent orchestration.

This module provides the SubAgentTool for delegating tasks to child agents,
enabling hierarchical agent orchestration with full reasoning chain visibility.
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from omniforge.agents.errors import AgentNotFoundError
from omniforge.agents.events import (
    TaskArtifactEvent,
    TaskDoneEvent,
    TaskErrorEvent,
    TaskMessageEvent,
)
from omniforge.agents.models import TextPart
from omniforge.agents.registry import AgentRegistry
from omniforge.tasks.models import Task, TaskMessage, TaskState
from omniforge.tools.base import (
    BaseTool,
    ParameterType,
    ToolCallContext,
    ToolDefinition,
    ToolParameter,
    ToolResult,
)
from omniforge.tools.types import ToolType


class SubAgentTool(BaseTool):
    """Tool for delegating tasks to sub-agents.

    Provides hierarchical agent orchestration through the unified tool interface with:
    - Agent lookup via registry
    - Task creation and execution
    - Sub-agent reasoning chain capture
    - Cycle detection to prevent infinite loops
    - Timeout enforcement
    - Full error handling

    Example:
        >>> registry = AgentRegistry(repository=repo)
        >>> tool = SubAgentTool(agent_registry=registry, timeout_ms=300000)
        >>> context = ToolCallContext(
        ...     correlation_id="corr-1",
        ...     task_id="task-1",
        ...     agent_id="agent-1"
        ... )
        >>> result = await tool.execute(
        ...     arguments={
        ...         "agent_id": "data-analyzer",
        ...         "task_description": "Analyze this dataset",
        ...         "context": {"dataset_id": "ds-123"}
        ...     },
        ...     context=context
        ... )
        >>> result.success
        True
    """

    def __init__(
        self,
        agent_registry: AgentRegistry,
        timeout_ms: int = 300000,  # 5 minutes default
    ) -> None:
        """Initialize SubAgentTool.

        Args:
            agent_registry: Registry for looking up available agents
            timeout_ms: Maximum execution time for sub-agent tasks in milliseconds
        """
        self._agent_registry = agent_registry
        self._timeout_ms = timeout_ms

    @property
    def definition(self) -> ToolDefinition:
        """Get tool definition."""
        return ToolDefinition(
            name="sub_agent",
            type=ToolType.SUB_AGENT,
            description="Delegate a task to a sub-agent for processing",
            parameters=[
                ToolParameter(
                    name="agent_id",
                    type=ParameterType.STRING,
                    description="ID of the agent to delegate to",
                    required=True,
                ),
                ToolParameter(
                    name="task_description",
                    type=ParameterType.STRING,
                    description="Description of the task for the sub-agent",
                    required=True,
                ),
                ToolParameter(
                    name="context",
                    type=ParameterType.OBJECT,
                    description="Optional context data to pass to the sub-agent",
                    required=False,
                ),
            ],
            timeout_ms=self._timeout_ms,
        )

    async def execute(self, context: ToolCallContext, arguments: dict[str, Any]) -> ToolResult:
        """Execute sub-agent delegation.

        Args:
            context: Execution context with correlation_id, task_id, agent_id
            arguments: Tool arguments containing agent_id, task_description, and context

        Returns:
            ToolResult with sub-agent results or error
        """
        start_time = time.time()

        # Extract arguments
        agent_id = arguments.get("agent_id", "").strip()
        task_description = arguments.get("task_description", "").strip()
        task_context = arguments.get("context", {})

        # Validate arguments
        if not agent_id:
            return ToolResult(
                success=False,
                error="agent_id cannot be empty",
                duration_ms=int((time.time() - start_time) * 1000),
            )

        if not task_description:
            return ToolResult(
                success=False,
                error="task_description cannot be empty",
                duration_ms=int((time.time() - start_time) * 1000),
            )

        # Check for cycles by tracking agent chain
        agent_chain = task_context.get("_agent_chain", [])
        if agent_id in agent_chain:
            return ToolResult(
                success=False,
                error=f"Cycle detected: Agent '{agent_id}' is already in the delegation chain {agent_chain}",
                duration_ms=int((time.time() - start_time) * 1000),
            )

        # Add current agent to chain for cycle detection
        new_agent_chain = agent_chain + [context.agent_id]
        updated_context = {**task_context, "_agent_chain": new_agent_chain}

        try:
            # Look up agent in registry
            agent = await self._agent_registry.get(agent_id)

            # Create task for sub-agent
            task_id = f"subtask-{uuid4()}"
            task = Task(
                id=task_id,
                agent_id=agent_id,
                state=TaskState.SUBMITTED,
                messages=[
                    TaskMessage(
                        id=f"msg-{uuid4()}",
                        role="user",
                        parts=[TextPart(text=task_description)],
                        created_at=datetime.now(timezone.utc),
                    )
                ],
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                tenant_id=context.tenant_id,
                user_id=context.user_id or "system",
                parent_task_id=context.task_id,
                conversation_id=context.conversation_id,
                # Propagate trace_id; fall back to parent task_id if not yet set (root case)
                trace_id=context.trace_id or context.task_id,
            )

            # Process task with timeout
            timeout_seconds = self._timeout_ms / 1000
            result = await asyncio.wait_for(
                self._process_sub_agent_task(
                    agent, task, updated_context, event_queue=context.event_queue
                ),
                timeout=timeout_seconds,
            )

            duration_ms = int((time.time() - start_time) * 1000)

            return ToolResult(
                success=True,
                result=result,
                duration_ms=duration_ms,
            )

        except AgentNotFoundError:
            duration_ms = int((time.time() - start_time) * 1000)
            return ToolResult(
                success=False,
                error=f"Agent '{agent_id}' not found. Use list_agents to see available agents.",
                duration_ms=duration_ms,
            )

        except asyncio.TimeoutError:
            timeout_secs = self._timeout_ms // 1000
            duration_ms = int((time.time() - start_time) * 1000)
            return ToolResult(
                success=False,
                error=(
                    f"Agent '{agent_id}' timed out after {timeout_secs}s. "
                    "The task may still be running in the background."
                ),
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return ToolResult(
                success=False,
                error=f"Agent '{agent_id}' failed: {str(e)}",
                duration_ms=duration_ms,
            )

    async def _process_sub_agent_task(
        self, agent: Any, task: Task, context: dict[str, Any], event_queue: Any = None
    ) -> dict[str, Any]:
        """Process task with sub-agent and collect results.

        Args:
            agent: The sub-agent to process the task
            task: The task to process
            context: Context data passed to sub-agent
            event_queue: Optional asyncio.Queue to forward TaskMessageEvents upstream

        Returns:
            Dictionary with sub-agent results

        Raises:
            Exception: If sub-agent processing fails
        """
        messages = []
        artifacts = []
        final_state = None
        error_info = None
        sub_chain_id = task.id  # Use task ID as sub-chain identifier

        # Process task events from agent
        async for event in agent.process_task(task):
            # Forward all non-terminal events upstream so the parent's consumer
            # (e.g. SSE endpoint) gets real-time visibility into the sub-agent.
            # Terminal events (Done/Error) are internal coordination signals and
            # must not be forwarded — they would confuse the parent's event loop.
            if event_queue is not None and not isinstance(event, (TaskDoneEvent, TaskErrorEvent)):
                event_queue.put_nowait(event)

            if isinstance(event, TaskMessageEvent):
                # Collect all message parts — text, data, and file references
                for part in event.message_parts:
                    if hasattr(part, "text") and part.text:  # type: ignore[union-attr]
                        messages.append(part.text)  # type: ignore[union-attr]
                    elif hasattr(part, "data") and part.data is not None:  # type: ignore[union-attr]
                        import json as _json

                        try:
                            messages.append(f"[Data: {_json.dumps(part.data)}]")  # type: ignore[union-attr]
                        except Exception:
                            messages.append(f"[Data: {str(part.data)}]")  # type: ignore[union-attr]
                    elif hasattr(part, "file_id"):  # type: ignore[union-attr]
                        messages.append(f"[File: {part.file_id}]")  # type: ignore[union-attr]

            elif isinstance(event, TaskArtifactEvent):
                # Collect artifacts produced by sub-agent (files, data outputs)
                artifacts.append(event.artifact.model_dump())

            elif isinstance(event, TaskDoneEvent):
                final_state = event.final_state
                break

            elif isinstance(event, TaskErrorEvent):
                error_info = {
                    "code": event.error_code,
                    "message": event.error_message,
                    "details": event.details,
                }
                # Continue consuming events until done event arrives

        # Guard: sub-agent never sent a terminal event
        if final_state is None:
            raise Exception(
                f"Agent '{task.agent_id}' ended without sending a completion signal."
            )

        # Build result
        result = {
            "sub_chain_id": sub_chain_id,
            "agent_id": task.agent_id,
            "final_state": final_state.value,
            "messages": messages,
            "context": context,
        }

        if error_info:
            result["error"] = error_info

        if artifacts:
            result["artifacts"] = artifacts

        # Raise on failure so the ReAct loop treats it as an error observation
        if final_state == TaskState.FAILED:
            if error_info:
                raise Exception(f"[{error_info['code']}] {error_info['message']}")
            else:
                raise Exception("sub-agent failed with no error details")

        return result
