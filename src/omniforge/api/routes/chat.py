"""Chat API route handlers.

This module provides FastAPI route handlers for chat interactions,
including streaming responses via Server-Sent Events (SSE).
"""

from datetime import datetime
from typing import AsyncIterator
from uuid import uuid4

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from omniforge.agents.master_agent import MasterAgent
from omniforge.agents.models import TextPart
from omniforge.agents.registry import AgentRegistry
from omniforge.chat.models import ChatRequest
from omniforge.storage.memory import InMemoryAgentRepository
from omniforge.tasks.models import Task, TaskMessage, TaskState

# Create router with prefix and tags
router = APIRouter(prefix="/api/v1", tags=["chat"])

# Shared agent registry — same one used across all chat sessions
_agent_registry = AgentRegistry(repository=InMemoryAgentRepository())

# Per-session MasterAgent instances so delegation state doesn't bleed between users.
# Key: conversation_id (str). Value: MasterAgent.
_session_agents: dict[str, MasterAgent] = {}


def _get_session_agent(session_id: str) -> MasterAgent:
    """Return the MasterAgent for this session, creating one if needed."""
    if session_id not in _session_agents:
        _session_agents[session_id] = MasterAgent(agent_registry=_agent_registry)
    return _session_agents[session_id]


async def _stream_agent_events(
    request: ChatRequest, http_request: Request
) -> AsyncIterator[str]:
    """Stream all SSE events from agent.process_task() while watching for disconnection.

    Emits the full event stream — reasoning steps, chain lifecycle events, tool
    calls/results, and messages — in the same format as the tasks endpoint.

    Args:
        request: ChatRequest containing message and optional conversation_id
        http_request: FastAPI Request for disconnect detection

    Yields:
        SSE-formatted event strings: ``event: <type>\\ndata: <json>\\n\\n``
    """
    # Use conversation_id as session key so each conversation gets an isolated
    # MasterAgent. If no conversation_id, generate a fresh session.
    session_id = str(request.conversation_id) if request.conversation_id else str(uuid4())
    agent = _get_session_agent(session_id)

    task_id = str(uuid4())
    now = datetime.utcnow()

    task = Task(
        id=task_id,
        agent_id="master-agent",
        state=TaskState.SUBMITTED,
        messages=[
            TaskMessage(
                id=str(uuid4()),
                role="user",
                parts=[TextPart(text=request.message)],
                created_at=now,
            )
        ],
        created_at=now,
        updated_at=now,
        user_id="anonymous",
        conversation_id=session_id,
    )

    try:
        async for event in agent.process_task(task):
            if await http_request.is_disconnected():
                break
            yield f"event: {event.type}\ndata: {event.model_dump_json()}\n\n"

    except Exception as e:
        from omniforge.agents.events import TaskErrorEvent

        error_event = TaskErrorEvent(
            task_id=task_id,
            timestamp=datetime.utcnow(),
            error_code="processing_error",
            error_message=str(e),
        )
        yield f"event: error\ndata: {error_event.model_dump_json()}\n\n"


@router.post("/chat")
async def chat(request: Request, body: ChatRequest) -> StreamingResponse:
    """Handle chat requests with streaming SSE responses.

    Streams all agent events — reasoning steps, tool calls, messages, and
    chain lifecycle — back to the client as Server-Sent Events.

    Args:
        request: FastAPI Request for connection monitoring
        body: ChatRequest with user message and optional conversation_id

    Returns:
        StreamingResponse with text/event-stream media type

    Example stream::

        event: chain_started
        data: {"type": "chain_started", "task_id": "...", "chain_id": "..."}

        event: reasoning_step
        data: {"type": "reasoning_step", "step": {"type": "thinking", ...}}

        event: reasoning_step
        data: {"type": "reasoning_step", "step": {"type": "tool_call", ...}}

        event: message
        data: {"type": "message", "message_parts": [{"text": "..."}], ...}

        event: done
        data: {"type": "done", "final_state": "completed", ...}
    """
    return StreamingResponse(
        _stream_agent_events(body, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
