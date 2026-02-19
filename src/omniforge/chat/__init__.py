"""Chat module for OmniForge platform.

This module provides chat request processing, response streaming, and
SSE event formatting capabilities.
"""

from omniforge.chat.errors import ChatError, InternalError, MessageTooLongError, ValidationError
from omniforge.chat.models import ChatRequest, ChunkEvent, DoneEvent, ErrorEvent, UsageInfo
from omniforge.chat.response_generator import ResponseGenerator
from omniforge.chat.service import ChatService
from omniforge.chat.streaming import (
    format_chunk_event,
    format_done_event,
    format_error_event,
    format_sse_event,
    stream_with_error_handling,
)

__all__ = [
    # Service
    "ChatService",
    # Models
    "ChatRequest",
    "ChunkEvent",
    "DoneEvent",
    "ErrorEvent",
    "UsageInfo",
    # Errors
    "ChatError",
    "ValidationError",
    "MessageTooLongError",
    "InternalError",
    # Response Generator
    "ResponseGenerator",
    # Streaming utilities
    "format_sse_event",
    "format_chunk_event",
    "format_done_event",
    "format_error_event",
    "stream_with_error_handling",
]
