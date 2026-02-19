"""Chat API route handlers.

This module provides FastAPI route handlers for chat interactions,
including streaming responses via Server-Sent Events (SSE).
"""

from typing import AsyncIterator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from omniforge.chat.models import ChatRequest
from omniforge.chat.service import ChatService

# Create router with prefix and tags
router = APIRouter(prefix="/api/v1", tags=["chat"])

# Shared ChatService instance for all requests
_chat_service = ChatService()


async def _stream_response(request: ChatRequest, http_request: Request) -> AsyncIterator[str]:
    """Stream SSE events while checking for client disconnection.

    This helper function wraps the chat service processing with client
    disconnection detection to avoid unnecessary processing when the
    client has closed the connection.

    Args:
        request: The ChatRequest containing message and conversation details
        http_request: The FastAPI Request object for checking connection status

    Yields:
        SSE-formatted event strings from the chat service
    """
    async for event in _chat_service.process_chat(request):
        # Check if client has disconnected
        if await http_request.is_disconnected():
            break
        yield event


@router.post("/chat")
async def chat(request: Request, body: ChatRequest) -> StreamingResponse:
    """Handle chat requests with streaming SSE responses.

    This endpoint processes chat messages and streams responses back to the
    client using Server-Sent Events (SSE) protocol. The stream includes chunk
    events with partial content, followed by a done event with usage stats, or
    an error event if processing fails.

    Args:
        request: FastAPI Request object for connection monitoring
        body: ChatRequest containing the user's message and optional conversation_id

    Returns:
        StreamingResponse with text/event-stream media type and SSE headers

    Examples:
        >>> # Client request
        >>> POST /api/v1/chat
        >>> {
        >>>     "message": "Hello",
        >>>     "conversation_id": "123e4567-e89b-12d3-a456-426614174000"
        >>> }
        >>>
        >>> # Server response (SSE stream)
        >>> event: chunk
        >>> data: {"content": "Hello"}
        >>>
        >>> event: done
        >>> data: {"conversation_id": "...", "usage": {"tokens": 10}}
    """
    return StreamingResponse(
        _stream_response(body, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
