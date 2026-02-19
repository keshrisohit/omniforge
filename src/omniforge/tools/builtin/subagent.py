"""Sub-agent delegation tool for hierarchical agent orchestration.

This module provides the SubAgentTool for delegating tasks to child agents,
enabling hierarchical agent orchestration with full reasoning chain visibility.
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from omniforge.agents.errors import AgentNotFoundError
from omniforge.agents.events import (
    TaskDoneEvent,
    TaskErrorEvent,
    TaskEvent,
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
                user_id=context.correlation_id,  # Use correlation_id as user
                parent_task_id=context.task_id,
            )

            # Process task with timeout
            timeout_seconds = self._timeout_ms / 1000
            result = await asyncio.wait_for(
                self._process_sub_agent_task(agent, task, updated_context),
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
                error=f"Agent not found: {agent_id}",
                duration_ms=duration_ms,
            )

        except asyncio.TimeoutError:
            duration_ms = int((time.time() - start_time) * 1000)
            return ToolResult(
                success=False,
                error=f"Sub-agent execution timed out after {self._timeout_ms}ms",
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return ToolResult(
                success=False,
                error=f"Sub-agent execution failed: {str(e)}",
                duration_ms=duration_ms,
            )

    async def _process_sub_agent_task(
        self, agent: Any, task: Task, context: dict[str, Any]
    ) -> dict[str, Any]:
        """Process task with sub-agent and collect results.

        Args:
            agent: The sub-agent to process the task
            task: The task to process
            context: Context data passed to sub-agent

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
            if isinstance(event, TaskMessageEvent):
                # Collect message parts
                for part in event.message_parts:
                    if hasattr(part, "text"):
                        messages.append(part.text)

            elif isinstance(event, TaskDoneEvent):
                final_state = event.final_state
                break

            elif isinstance(event, TaskErrorEvent):
                error_info = {
                    "code": event.error_code,
                    "message": event.error_message,
                    "details": event.details,
                }
                # Continue to wait for done event

        # Build result
        result = {
            "sub_chain_id": sub_chain_id,
            "agent_id": task.agent_id,
            "final_state": final_state.value if final_state else "unknown",
            "messages": messages,
            "context": context,
        }

        if error_info:
            result["error"] = error_info

        if artifacts:
            result["artifacts"] = artifacts

        # If task failed, include error in the result
        if final_state == TaskState.FAILED and error_info:
            raise Exception(f"Sub-agent failed: {error_info['message']}")

        return result
