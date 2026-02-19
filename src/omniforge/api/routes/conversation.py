"""Conversation API route handlers.

This module provides FastAPI route handlers for conversational agent building,
including session management, message streaming, and OAuth flow integration.
"""

import json
import uuid
from typing import AsyncIterator, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from omniforge.api.dependencies import get_current_tenant
from omniforge.api.schemas.conversation import (
    ConversationMessageRequest,
    ConversationMessageResponse,
    ConversationOAuthCompleteRequest,
    ConversationOAuthCompleteResponse,
    ConversationStartResponse,
)
from omniforge.builder.conversation import ConversationManager

# Create router with prefix and tags
router = APIRouter(prefix="/api/v1/conversation", tags=["conversation"])

# Shared conversation manager instance
_conversation_manager = ConversationManager()


@router.post("/start", response_model=ConversationStartResponse)
async def start_conversation(
    request: Request,
    tenant_id: Optional[str] = Depends(get_current_tenant),
) -> ConversationStartResponse:
    """Start a new agent-building conversation session.

    Creates a new conversation context and returns a session ID for subsequent
    message exchanges. The conversation guides users through creating an agent
    via natural language interaction.

    Args:
        request: FastAPI request object
        tenant_id: Current tenant ID from middleware

    Returns:
        ConversationStartResponse with session_id, initial message, and phase

    Raises:
        HTTPException: If tenant_id is not available

    Examples:
        >>> POST /api/v1/conversation/start
        >>> {}
        >>>
        >>> {
        >>>   "session_id": "550e8400-e29b-41d4-a716-446655440000",
        >>>   "message": "Hi! I'll help you create an agent...",
        >>>   "phase": "discovery"
        >>> }
    """
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Tenant ID required")

    # Generate session ID
    session_id = str(uuid.uuid4())

    # Extract user_id from request state (set by auth middleware)
    user_id = getattr(request.state, "user_id", "anonymous")

    # Start conversation
    context = _conversation_manager.start_conversation(
        conversation_id=session_id,
        tenant_id=tenant_id,
        user_id=user_id,
    )

    initial_message = (
        "Hi! I'll help you create an AI agent through conversation. "
        "What would you like your agent to automate? "
        "(e.g., 'Create weekly reports from Notion')"
    )

    return ConversationStartResponse(
        session_id=session_id,
        message=initial_message,
        phase=context.state.value,
    )


async def _stream_conversation_response(
    session_id: str, user_message: str, http_request: Request
) -> AsyncIterator[str]:
    """Stream conversation response as Server-Sent Events.

    Args:
        session_id: Conversation session ID
        user_message: User's message
        http_request: FastAPI request for disconnect detection

    Yields:
        SSE-formatted event strings with conversation responses
    """
    try:
        # Process user input
        context, response = _conversation_manager.process_user_input(
            conversation_id=session_id,
            user_input=user_message,
        )

        # Check for disconnection
        if await http_request.is_disconnected():
            return

        # Build response data
        response_data = ConversationMessageResponse(
            text=response,
            phase=context.state.value,
            actions=[],
            oauth_url=None,
        )

        # For integration setup phase, include OAuth URL
        if context.state.value == "integration_setup" and context.integration_type:
            # Generate OAuth URL (placeholder - actual implementation in OAuth manager)
            oauth_url = f"/oauth/authorize/{context.integration_type}?session={session_id}"
            response_data.oauth_url = oauth_url

        # Stream response as SSE event
        event_data = json.dumps(response_data.model_dump())
        yield f"event: message\ndata: {event_data}\n\n"

        # Send done event
        done_data = json.dumps({"session_id": session_id, "phase": context.state.value})
        yield f"event: done\ndata: {done_data}\n\n"

    except ValueError as e:
        # Conversation not found or invalid state
        error_data = json.dumps({"code": "invalid_session", "message": str(e)})
        yield f"event: error\ndata: {error_data}\n\n"
    except Exception:
        # Unexpected error
        error_data = json.dumps(
            {"code": "processing_error", "message": "Failed to process message"}
        )
        yield f"event: error\ndata: {error_data}\n\n"


@router.post("/{session_id}/message")
async def send_message(
    session_id: str,
    body: ConversationMessageRequest,
    request: Request,
    tenant_id: Optional[str] = Depends(get_current_tenant),
) -> StreamingResponse:
    """Send a message in an ongoing conversation.

    Processes the user's message and streams the assistant's response via
    Server-Sent Events (SSE). The response includes the assistant's text,
    current conversation phase, and any required actions (e.g., OAuth).

    Args:
        session_id: Conversation session ID from start endpoint
        body: ConversationMessageRequest with user message
        request: FastAPI request object
        tenant_id: Current tenant ID from middleware

    Returns:
        StreamingResponse with SSE events containing conversation responses

    Raises:
        HTTPException: If tenant_id is not available

    Examples:
        >>> POST /api/v1/conversation/{session_id}/message
        >>> {
        >>>   "message": "I want to create weekly Notion reports"
        >>> }
        >>>
        >>> # SSE stream:
        >>> event: message
        >>> data: {"text": "Great! Which integration...", "phase": "...", ...}
        >>>
        >>> event: done
        >>> data: {"session_id": "...", "phase": "..."}
    """
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Tenant ID required")

    return StreamingResponse(
        _stream_conversation_response(session_id, body.message, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/{session_id}/oauth-complete", response_model=ConversationOAuthCompleteResponse)
async def complete_oauth(
    session_id: str,
    body: ConversationOAuthCompleteRequest,
    tenant_id: Optional[str] = Depends(get_current_tenant),
) -> ConversationOAuthCompleteResponse:
    """Complete OAuth flow and resume conversation.

    Called after user completes OAuth authorization with an integration provider
    (e.g., Notion). Exchanges the authorization code for access tokens, stores
    credentials securely, and resumes the agent-building conversation.

    Args:
        session_id: Conversation session ID
        body: ConversationOAuthCompleteRequest with integration, code, and state
        tenant_id: Current tenant ID from middleware

    Returns:
        ConversationOAuthCompleteResponse with success status and next message

    Raises:
        HTTPException: If tenant_id missing, session invalid, or OAuth fails

    Examples:
        >>> POST /api/v1/conversation/{session_id}/oauth-complete
        >>> {
        >>>   "integration": "notion",
        >>>   "code": "abc123...",
        >>>   "state": "xyz789..."
        >>> }
        >>>
        >>> {
        >>>   "success": true,
        >>>   "workspace_name": "My Workspace",
        >>>   "message": "Connected successfully! Now let's configure..."
        >>> }
    """
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Tenant ID required")

    # Get conversation context
    context = _conversation_manager.get_context(session_id)
    if not context:
        raise HTTPException(status_code=404, detail="Conversation session not found")

    # Validate state matches
    # TODO: Implement state validation for CSRF protection

    # TODO: Exchange OAuth code for tokens via OAuth manager
    # For now, simulate successful OAuth
    integration_id = f"integration-{body.integration}-{uuid.uuid4().hex[:8]}"
    workspace_name = f"My {body.integration.capitalize()} Workspace"

    # Update conversation context
    context.integration_id = integration_id
    context.integration_type = body.integration

    # Generate next message
    next_message = (
        f"{body.integration.capitalize()} connected successfully!\n\n"
        "Now, tell me more about what this agent should do:\n"
        "- What information should it gather?\n"
        "- What format should the output be?\n"
        "- When should it run?"
    )

    return ConversationOAuthCompleteResponse(
        success=True,
        workspace_name=workspace_name,
        message=next_message,
    )
