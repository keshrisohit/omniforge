"""Task management API route handlers.

This module provides FastAPI route handlers for task operations,
including task creation, status retrieval, message sending, cancellation,
and listing. Task creation and message sending return Server-Sent Events (SSE).
"""

import os
from datetime import datetime
from typing import AsyncIterator, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from omniforge.agents.base import BaseAgent
from omniforge.agents.errors import TaskNotFoundError, TaskStateError
from omniforge.agents.models import TextPart
from omniforge.agents.registry import AgentRegistry
from omniforge.api.dependencies import get_current_tenant
from omniforge.api.routes.agents import _agent_repository
from omniforge.security.isolation import enforce_agent_isolation, enforce_task_isolation
from omniforge.storage.base import TaskRepository
from omniforge.storage.database import Database, DatabaseConfig
from omniforge.storage.memory import InMemoryTaskRepository
from omniforge.tasks.models import (
    ChatRequest,
    ChatResponse,
    Task,
    TaskCreateRequest,
    TaskMessage,
    TaskSendRequest,
    TaskState,
)

# Create router with tags
router = APIRouter(tags=["tasks"])

# Shared in-memory task repository instance
# TODO: Replace with persistent storage in production
_task_repository: TaskRepository = InMemoryTaskRepository()

# Shared database instance for SQL-backed task repository
_database: Optional[Database] = None


def get_agent_registry() -> AgentRegistry:
    """Dependency for getting the agent registry instance.

    Returns:
        AgentRegistry instance configured with the repository
    """
    return AgentRegistry(repository=_agent_repository)


def get_task_repository() -> TaskRepository:
    """Dependency for getting the task repository instance.

    Returns:
        TaskRepository instance
    """
    return _task_repository


def get_database() -> Database:
    """Get or create shared database instance.

    Returns:
        Database instance
    """
    global _database
    if _database is None:
        config = DatabaseConfig(
            url=os.getenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
        )
        _database = Database(config)
    return _database


async def get_sql_task_repository():
    """Dependency for getting the SQL-backed task repository.

    Yields:
        SQLTaskRepository instance backed by a database session
    """
    from omniforge.storage.task_repository import SQLTaskRepository

    db = get_database()
    async with db.session() as session:
        yield SQLTaskRepository(session)


async def _stream_task_events(
    task: Task, agent: BaseAgent, http_request: Request, task_repo: TaskRepository
) -> AsyncIterator[str]:
    """Stream SSE events from task processing while persisting state changes.

    This helper function processes a task through an agent and yields
    SSE-formatted events, while monitoring for client disconnection and
    persisting every event's effects to the task repository.

    Args:
        task: The task to process
        agent: The agent to process the task
        http_request: The FastAPI Request object for checking connection status
        task_repo: Repository for persisting task state changes

    Yields:
        SSE-formatted event strings
    """
    from omniforge.tasks.manager import TaskManager

    current_task = task
    try:
        async for event in agent.process_task(task):  # type: ignore[attr-defined]
            # Check if client has disconnected
            if await http_request.is_disconnected():
                break

            # Persist event effects to repository
            updated = TaskManager.apply_event(current_task, event)
            if updated is not current_task:
                await task_repo.update(updated)
                current_task = updated

            # Format as SSE event
            event_json = event.model_dump_json()
            yield f"event: {event.type}\ndata: {event_json}\n\n"

    except Exception as e:
        from omniforge.agents.events import TaskErrorEvent

        error_event = TaskErrorEvent(
            task_id=task.id,
            timestamp=datetime.utcnow(),
            error_code="processing_error",
            error_message=str(e),
        )
        # Persist the failure
        failed = TaskManager.apply_event(current_task, error_event)
        if failed is not current_task:
            await task_repo.update(failed)

        yield f"event: error\ndata: {error_event.model_dump_json()}\n\n"


@router.post("/api/v1/agents/{agent_id}/tasks")
async def create_task(
    agent_id: str,
    request: Request,
    body: TaskCreateRequest,
    registry: AgentRegistry = Depends(get_agent_registry),
    task_repo: TaskRepository = Depends(get_task_repository),
) -> StreamingResponse:
    """Create a new task and stream processing events via SSE.

    This endpoint creates a task for the specified agent and immediately
    begins processing it, streaming events back to the client using
    Server-Sent Events (SSE) protocol.

    Args:
        agent_id: ID of the agent to process the task
        request: FastAPI Request object for connection monitoring
        body: TaskCreateRequest with message_parts and metadata
        registry: Injected AgentRegistry dependency
        task_repo: Injected TaskRepository dependency

    Returns:
        StreamingResponse with text/event-stream media type and SSE headers

    Raises:
        AgentNotFoundError: If the agent does not exist (handled by middleware)

    Example:
        >>> POST /api/v1/agents/my-agent/tasks
        >>> {
        >>>     "message_parts": [{"type": "text", "text": "Hello"}],
        >>>     "tenant_id": "tenant-1",
        >>>     "user_id": "user-1"
        >>> }
        >>>
        >>> # Server response (SSE stream)
        >>> event: status
        >>> data: {"type": "status", "task_id": "...", "state": "working", ...}
        >>>
        >>> event: message
        >>> data: {"type": "message", "task_id": "...", "message_parts": [...], ...}
        >>>
        >>> event: done
        >>> data: {"type": "done", "task_id": "...", "final_state": "completed", ...}
    """
    # Get agent from registry (raises AgentNotFoundError if not found)
    agent: BaseAgent = await registry.get(agent_id)

    # Enforce tenant isolation for agent access
    enforce_agent_isolation(agent)

    # Create task
    task_id = str(uuid4())
    now = datetime.utcnow()

    # Create initial user message
    user_message = TaskMessage(
        id=str(uuid4()),
        role="user",
        parts=body.message_parts,
        created_at=now,
    )

    task = Task(
        id=task_id,
        agent_id=agent_id,
        state=TaskState.SUBMITTED,
        messages=[user_message],
        created_at=now,
        updated_at=now,
        tenant_id=body.tenant_id,
        user_id=body.user_id,
        parent_task_id=body.parent_task_id,
        skill_name=body.skill_name,
    )

    # Save task to repository
    await task_repo.save(task)

    # Stream task processing events
    return StreamingResponse(
        _stream_task_events(task, agent, request, task_repo),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/api/v1/agents/{agent_id}/chat", response_model=None)
async def chat(
    agent_id: str,
    request: Request,
    body: ChatRequest,
    registry: AgentRegistry = Depends(get_agent_registry),
    task_repo: TaskRepository = Depends(get_task_repository),
):
    """Simplified chat endpoint for quick agent interactions.

    This endpoint provides a simpler alternative to the task creation endpoint,
    accepting a plain text message instead of structured message parts.
    Supports both streaming (SSE) and non-streaming responses.

    Args:
        agent_id: ID of the agent to chat with
        request: FastAPI Request object for connection monitoring
        body: ChatRequest with message and optional parameters
        registry: Injected AgentRegistry dependency
        task_repo: Injected TaskRepository dependency

    Returns:
        StreamingResponse (if stream=True) or ChatResponse (if stream=False)

    Raises:
        AgentNotFoundError: If the agent does not exist (handled by middleware)

    Example (streaming):
        >>> POST /api/v1/agents/my-agent/chat
        >>> {
        >>>     "message": "Hello!",
        >>>     "stream": true
        >>> }
        >>>
        >>> # Server response (SSE stream)
        >>> event: status
        >>> data: {"type": "status", "task_id": "...", ...}
        >>> ...

    Example (non-streaming):
        >>> POST /api/v1/agents/my-agent/chat
        >>> {
        >>>     "message": "Hello!",
        >>>     "stream": false
        >>> }
        >>>
        >>> # Server response (JSON)
        >>> {
        >>>     "task_id": "...",
        >>>     "response": "Hello! How can I help?",
        >>>     "state": "completed"
        >>> }
    """
    # Get agent from registry (raises AgentNotFoundError if not found)
    agent: BaseAgent = await registry.get(agent_id)

    # Enforce tenant isolation for agent access
    enforce_agent_isolation(agent)

    # Create task from simple message
    task_id = str(uuid4())
    now = datetime.utcnow()

    # Create initial user message from text
    user_message = TaskMessage(
        id=str(uuid4()),
        role="user",
        parts=[TextPart(text=body.message)],
        created_at=now,
    )

    task = Task(
        id=task_id,
        agent_id=agent_id,
        state=TaskState.SUBMITTED,
        messages=[user_message],
        created_at=now,
        updated_at=now,
        tenant_id=body.tenant_id,
        user_id=body.user_id,
        parent_task_id=None,
    )

    # Save task to repository
    await task_repo.save(task)

    # Return streaming or non-streaming response based on request
    if body.stream:
        # Stream task processing events via SSE
        return StreamingResponse(
            _stream_task_events(task, agent, request, task_repo),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    else:
        # Collect response and return as JSON, persisting state for each event
        from omniforge.agents.events import TaskDoneEvent, TaskMessageEvent
        from omniforge.tasks.manager import TaskManager

        response_text = ""
        final_state = TaskState.COMPLETED
        current_task = task

        async for event in agent.process_task(task):  # type: ignore[attr-defined]
            updated = TaskManager.apply_event(current_task, event)
            if updated is not current_task:
                await task_repo.update(updated)
                current_task = updated

            if isinstance(event, TaskMessageEvent):
                for part in event.message_parts:
                    if isinstance(part, TextPart):
                        response_text += part.text

            if isinstance(event, TaskDoneEvent):
                final_state = event.final_state

        return ChatResponse(
            task_id=task.id, response=response_text.strip(), state=final_state.value
        )


@router.get("/api/v1/agents/{agent_id}/tasks/{task_id}")
async def get_task_status(
    agent_id: str,
    task_id: str,
    task_repo: TaskRepository = Depends(get_task_repository),
) -> dict:
    """Get the current status of a task.

    This endpoint retrieves the current state and details of a task.

    Args:
        agent_id: ID of the agent handling the task
        task_id: ID of the task to retrieve
        task_repo: Injected TaskRepository dependency

    Returns:
        Dictionary with task status information

    Raises:
        TaskNotFoundError: If the task does not exist (handled by middleware)

    Example:
        >>> GET /api/v1/agents/my-agent/tasks/task-123
        >>> {
        >>>     "id": "task-123",
        >>>     "agent_id": "my-agent",
        >>>     "state": "completed",
        >>>     "created_at": "2024-01-01T00:00:00Z",
        >>>     "updated_at": "2024-01-01T00:01:00Z"
        >>> }
    """
    # Get task from repository
    task = await task_repo.get(task_id)

    if task is None or task.agent_id != agent_id:
        raise TaskNotFoundError(task_id)

    # Enforce tenant isolation for task access
    enforce_task_isolation(task)

    # Return task summary
    return {
        "id": task.id,
        "agent_id": task.agent_id,
        "state": task.state.value,
        "skill_name": task.skill_name,
        "input_summary": task.input_summary,
        "trace_id": task.trace_id,
        "created_at": task.created_at.isoformat(),
        "updated_at": task.updated_at.isoformat(),
        "message_count": len(task.messages),
        "artifact_count": len(task.artifacts),
    }


@router.post("/api/v1/agents/{agent_id}/tasks/{task_id}/send")
async def send_message(
    agent_id: str,
    task_id: str,
    request: Request,
    body: TaskSendRequest,
    registry: AgentRegistry = Depends(get_agent_registry),
    task_repo: TaskRepository = Depends(get_task_repository),
) -> StreamingResponse:
    """Send a message to an existing task and stream response events via SSE.

    This endpoint sends a message to a task and streams the agent's
    response events back to the client using Server-Sent Events (SSE).

    Args:
        agent_id: ID of the agent handling the task
        task_id: ID of the task to send message to
        request: FastAPI Request object for connection monitoring
        body: TaskSendRequest with message_parts
        registry: Injected AgentRegistry dependency
        task_repo: Injected TaskRepository dependency

    Returns:
        StreamingResponse with text/event-stream media type and SSE headers

    Raises:
        AgentNotFoundError: If the agent does not exist (handled by middleware)
        TaskNotFoundError: If the task does not exist (handled by middleware)
        TaskStateError: If task is in a terminal state (handled by middleware)

    Example:
        >>> POST /api/v1/agents/my-agent/tasks/task-123/send
        >>> {
        >>>     "message_parts": [{"type": "text", "text": "Continue"}]
        >>> }
        >>>
        >>> # Server response (SSE stream)
        >>> event: status
        >>> data: {"type": "status", "task_id": "task-123", "state": "working", ...}
        >>> ...
    """
    # Get agent from registry (raises AgentNotFoundError if not found)
    agent: BaseAgent = await registry.get(agent_id)

    # Enforce tenant isolation for agent access
    enforce_agent_isolation(agent)

    # Get task from repository
    task = await task_repo.get(task_id)

    if task is None or task.agent_id != agent_id:
        raise TaskNotFoundError(task_id)

    # Enforce tenant isolation for task access
    enforce_task_isolation(task)

    # Check if task is in a terminal state
    if task.state.is_terminal():
        raise TaskStateError(task_id, task.state.value, "send_message")

    # Add user message to task
    now = datetime.utcnow()
    user_message = TaskMessage(
        id=str(uuid4()),
        role="user",
        parts=body.message_parts,
        created_at=now,
    )
    task.messages.append(user_message)
    task.updated_at = now

    # Update task in repository
    await task_repo.update(task)

    # Handle message in agent (for multi-turn support)
    # Extract text from message parts for simplicity
    message_text = " ".join(part.text for part in body.message_parts if isinstance(part, TextPart))
    agent.handle_message(task_id, message_text)

    # Stream task processing events
    return StreamingResponse(
        _stream_task_events(task, agent, request, task_repo),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/api/v1/agents/{agent_id}/tasks/{task_id}/cancel")
async def cancel_task(
    agent_id: str,
    task_id: str,
    registry: AgentRegistry = Depends(get_agent_registry),
    task_repo: TaskRepository = Depends(get_task_repository),
) -> dict:
    """Cancel a running task.

    This endpoint cancels a task that is currently in progress.

    Args:
        agent_id: ID of the agent handling the task
        task_id: ID of the task to cancel
        registry: Injected AgentRegistry dependency
        task_repo: Injected TaskRepository dependency

    Returns:
        Dictionary confirming cancellation

    Raises:
        AgentNotFoundError: If the agent does not exist (handled by middleware)
        TaskNotFoundError: If the task does not exist (handled by middleware)
        TaskStateError: If task is already in a terminal state (handled by middleware)

    Example:
        >>> POST /api/v1/agents/my-agent/tasks/task-123/cancel
        >>> {
        >>>     "id": "task-123",
        >>>     "state": "cancelled"
        >>> }
    """
    # Get agent from registry (raises AgentNotFoundError if not found)
    agent: BaseAgent = await registry.get(agent_id)

    # Enforce tenant isolation for agent access
    enforce_agent_isolation(agent)

    # Get task from repository
    task = await task_repo.get(task_id)

    if task is None or task.agent_id != agent_id:
        raise TaskNotFoundError(task_id)

    # Enforce tenant isolation for task access
    enforce_task_isolation(task)

    # Check if task is in a terminal state
    if task.state.is_terminal():
        raise TaskStateError(task_id, task.state.value, "cancel")

    # Cancel task in agent
    agent.cancel_task(task_id)

    # Update task state to cancelled
    task.state = TaskState.CANCELLED
    task.updated_at = datetime.utcnow()
    await task_repo.update(task)

    return {
        "id": task.id,
        "state": task.state.value,
    }


@router.get("/api/v1/agents/{agent_id}/tasks")
async def list_tasks(
    agent_id: str,
    registry: AgentRegistry = Depends(get_agent_registry),
    task_repo: TaskRepository = Depends(get_task_repository),
) -> list[dict]:
    """List all tasks for a specific agent.

    This endpoint returns a list of all tasks associated with the
    specified agent.

    Args:
        agent_id: ID of the agent
        registry: Injected AgentRegistry dependency
        task_repo: Injected TaskRepository dependency

    Returns:
        List of task summary objects

    Raises:
        AgentNotFoundError: If the agent does not exist (handled by middleware)

    Example:
        >>> GET /api/v1/agents/my-agent/tasks
        >>> [
        >>>     {
        >>>         "id": "task-123",
        >>>         "state": "completed",
        >>>         "created_at": "2024-01-01T00:00:00Z",
        >>>         "updated_at": "2024-01-01T00:01:00Z"
        >>>     }
        >>> ]
    """
    # Verify agent exists (raises AgentNotFoundError if not found)
    agent: BaseAgent = await registry.get(agent_id)

    # Enforce tenant isolation for agent access
    enforce_agent_isolation(agent)

    # Get tasks for this agent
    tasks = await task_repo.list_by_agent(agent_id)

    # Return task summaries
    return [
        {
            "id": task.id,
            "agent_id": task.agent_id,
            "state": task.state.value,
            "skill_name": task.skill_name,
            "input_summary": task.input_summary,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat(),
            "message_count": len(task.messages),
            "artifact_count": len(task.artifacts),
        }
        for task in tasks
    ]


@router.get("/api/v1/tasks")
async def list_tenant_tasks(
    skill_name: Optional[str] = Query(None, max_length=255),
    state: Optional[str] = Query(None, max_length=50),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    task_repo: TaskRepository = Depends(get_task_repository),
    tenant_id: Optional[str] = Depends(get_current_tenant),
) -> list[dict]:
    """List tasks for the current tenant with optional filtering.

    Tenant is read from request state set by TenantMiddleware.

    Args:
        skill_name: Optional skill name filter
        state: Optional state filter
        limit: Maximum number of tasks to return (default: 100)
        offset: Number of tasks to skip (default: 0)
        task_repo: Injected TaskRepository dependency
        tenant_id: Current tenant ID from middleware

    Returns:
        List of task summary objects for the tenant
    """
    if not tenant_id:
        return []

    if skill_name:
        tasks = await task_repo.list_by_skill(tenant_id, skill_name, limit=limit)
    else:
        tasks = await task_repo.list_by_tenant(tenant_id, limit=limit, offset=offset)

    # Apply optional state filter
    if state:
        tasks = [t for t in tasks if t.state.value == state]

    return [
        {
            "id": task.id,
            "agent_id": task.agent_id,
            "skill_name": task.skill_name,
            "input_summary": task.input_summary,
            "state": task.state.value,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat(),
            "artifact_count": len(task.artifacts),
            "message_count": len(task.messages),
        }
        for task in tasks
    ]
