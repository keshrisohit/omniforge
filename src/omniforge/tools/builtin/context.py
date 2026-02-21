"""Context read/write tools for sharing data across agents in a pipeline.

These tools give agents access to the working-memory store (AgentContextStore)
scoped by the current trace_id. They are the primary mechanism for agents in
a TaskGraph pipeline to exchange structured data without embedding everything
in task description strings.
"""

import time
from typing import Any

from omniforge.memory.working import get_context_store
from omniforge.tools.base import (
    BaseTool,
    ParameterType,
    ToolCallContext,
    ToolDefinition,
    ToolParameter,
    ToolResult,
)
from omniforge.tools.types import ToolType


class WriteContextTool(BaseTool):
    """Write a JSON-serialisable value into the shared context store.

    The value is scoped to the current trace_id so concurrent request
    chains never interfere with each other.
    """

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="write_context",
            type=ToolType.FUNCTION,
            description=(
                "Write a value into the shared working-memory store for this request chain. "
                "Other agents in the same pipeline can read it with read_context. "
                "Values are scoped to this trace and cleared when the chain completes."
            ),
            parameters=[
                ToolParameter(
                    name="key",
                    type=ParameterType.STRING,
                    description="Slot name to write to (e.g. 'research_output', 'parsed_data')",
                    required=True,
                ),
                ToolParameter(
                    name="value",
                    type=ParameterType.OBJECT,
                    description="JSON-serialisable value to store (max 1 MB)",
                    required=True,
                ),
            ],
            timeout_ms=5000,
        )

    async def execute(self, context: ToolCallContext, arguments: dict[str, Any]) -> ToolResult:
        start = time.time()
        key = (arguments.get("key") or "").strip()
        value = arguments.get("value")

        if not key:
            return ToolResult(
                success=False,
                error="key is required",
                duration_ms=int((time.time() - start) * 1000),
            )
        if value is None:
            return ToolResult(
                success=False,
                error="value is required",
                duration_ms=int((time.time() - start) * 1000),
            )

        trace_id = context.trace_id or context.task_id
        try:
            get_context_store().set(trace_id, key, value)
        except ValueError as exc:
            return ToolResult(
                success=False,
                error=str(exc),
                duration_ms=int((time.time() - start) * 1000),
            )

        return ToolResult(
            success=True,
            result={"key": key, "trace_id": trace_id},
            duration_ms=int((time.time() - start) * 1000),
        )


class ReadContextTool(BaseTool):
    """Read a value from the shared context store.

    Returns None (as a null JSON value) if the key does not exist.
    """

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="read_context",
            type=ToolType.FUNCTION,
            description=(
                "Read a value from the shared working-memory store for this request chain. "
                "Use after another agent has written data with write_context. "
                "Returns null if the key has not been written yet."
            ),
            parameters=[
                ToolParameter(
                    name="key",
                    type=ParameterType.STRING,
                    description="Slot name to read (e.g. 'research_output')",
                    required=True,
                ),
            ],
            timeout_ms=5000,
        )

    async def execute(self, context: ToolCallContext, arguments: dict[str, Any]) -> ToolResult:
        start = time.time()
        key = (arguments.get("key") or "").strip()

        if not key:
            return ToolResult(
                success=False,
                error="key is required",
                duration_ms=int((time.time() - start) * 1000),
            )

        trace_id = context.trace_id or context.task_id
        value = get_context_store().get(trace_id, key)

        return ToolResult(
            success=True,
            result={"key": key, "value": value, "trace_id": trace_id, "found": value is not None},
            duration_ms=int((time.time() - start) * 1000),
        )
