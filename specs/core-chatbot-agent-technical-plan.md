# Core Chatbot Agent - Technical Implementation Plan

**Created**: 2026-01-03
**Version**: 1.0
**Status**: Draft
**Related Spec**: [core-chatbot-agent.md](./core-chatbot-agent.md)

---

## Executive Summary

This document provides the technical implementation plan for the Core Chatbot Agent, which serves as the primary conversational interface for the OmniForge platform. The implementation uses **FastAPI** for its native async/SSE support, type safety, and automatic OpenAPI documentation. The initial version (v1) delivers a stateless, streaming chat endpoint with placeholder response generation, designed for easy integration of real LLM providers in future iterations.

**Key Technical Decisions:**
- FastAPI as the web framework (async-native, SSE support, Pydantic validation)
- Server-Sent Events (SSE) for real-time streaming
- Stateless design with optional conversation_id for future context support
- Modular architecture separating API, streaming, and response generation layers
- Comprehensive error handling with typed error responses

---

## Requirements Analysis

### Functional Requirements (from spec)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-1 | Accept POST requests with JSON message payload | Must Have |
| FR-2 | Stream responses via SSE with `chunk`, `done`, and `error` events | Must Have |
| FR-3 | Support optional `conversation_id` in request | Must Have |
| FR-4 | Return `conversation_id` and usage metadata in `done` event | Must Have |
| FR-5 | Validate request payload (non-empty message, length limits) | Must Have |
| FR-6 | Handle client disconnections gracefully | Must Have |

### Non-Functional Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-1 | Time to first token | < 500ms |
| NFR-2 | Stream completion rate | 99%+ (excluding client disconnects) |
| NFR-3 | Request validation response time | < 50ms |
| NFR-4 | Maximum message length | 10,000 characters |
| NFR-5 | Full UTF-8 support | Required |
| NFR-6 | Type annotations | 100% coverage (mypy strict) |

---

## Constraints and Assumptions

### Technical Constraints (from CLAUDE.md and user requirements)

- **Python 3.9+**: All code must be compatible with Python 3.9
- **Type Annotations**: mypy with `disallow_untyped_defs = true`
- **Line Length**: 100 characters (black/ruff)
- **Source Location**: Backend code in `src/omniforge/`
- **Test Location**: Tests in `tests/`
- **Coverage**: pytest with coverage reporting

### Assumptions

1. **No LLM Integration in v1**: Response generation uses placeholder/echo logic
2. **No Authentication in v1**: Endpoints are unauthenticated
3. **No Persistence in v1**: No database, stateless design
4. **Single Instance**: No distributed deployment considerations in v1
5. **No Rate Limiting in v1**: Deferred to future iteration

---

## System Architecture

### High-Level Architecture

```
+------------------+     HTTP POST      +-------------------+
|                  | ----------------> |                   |
|     Client       |                   |   FastAPI App     |
|                  | <---------------- |                   |
+------------------+    SSE Stream     +-------------------+
                                              |
                                              v
                                    +-------------------+
                                    |  Request Handler  |
                                    |  (Validation)     |
                                    +-------------------+
                                              |
                                              v
                                    +-------------------+
                                    |  Chat Service     |
                                    |  (Business Logic) |
                                    +-------------------+
                                              |
                                              v
                                    +-------------------+
                                    |  Response Gen     |
                                    |  (Placeholder)    |
                                    +-------------------+
                                              |
                                              v
                                    +-------------------+
                                    |  SSE Formatter    |
                                    |  (Streaming)      |
                                    +-------------------+
```

### Component Responsibilities

| Component | Responsibility |
|-----------|----------------|
| FastAPI App | HTTP server, routing, middleware |
| Request Handler | Pydantic validation, error formatting |
| Chat Service | Orchestrates request processing |
| Response Generator | Produces response content (placeholder in v1) |
| SSE Formatter | Formats and yields SSE events |

---

## Technology Stack

### Core Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| fastapi | >=0.100.0 | Web framework with async support |
| uvicorn | >=0.23.0 | ASGI server |
| pydantic | >=2.0.0 | Request/response validation |
| sse-starlette | >=1.6.0 | SSE response helper (or native impl) |

### Development Dependencies (extend existing)

| Dependency | Version | Purpose |
|------------|---------|---------|
| httpx | >=0.24.0 | Async HTTP client for testing |
| pytest-asyncio | >=0.21.0 | Async test support |

### Rationale

**FastAPI** was chosen over alternatives because:
- **Native async support**: Essential for SSE streaming without blocking
- **Pydantic integration**: Type-safe request/response validation aligns with mypy requirements
- **Automatic OpenAPI**: Reduces documentation burden
- **SSE support**: Works with Starlette's streaming responses
- **Industry standard**: Well-maintained, extensive documentation, large ecosystem

**sse-starlette vs native**: While Starlette supports streaming responses natively, `sse-starlette` provides cleaner SSE formatting. However, for simplicity and fewer dependencies, we will implement SSE formatting manually using Starlette's `StreamingResponse`.

---

## Detailed Component Design

### File Structure

```
src/omniforge/
    __init__.py                  # Package init (exists)
    api/
        __init__.py
        app.py                   # FastAPI application factory
        routes/
            __init__.py
            chat.py              # Chat endpoint
        middleware/
            __init__.py
            error_handler.py     # Global error handling
    chat/
        __init__.py
        service.py               # Chat business logic
        models.py                # Pydantic models (request/response)
        streaming.py             # SSE formatting and streaming
        response_generator.py    # Response generation (placeholder)
        errors.py                # Custom exceptions

tests/
    __init__.py                  # Package init (exists)
    conftest.py                  # Pytest fixtures
    api/
        __init__.py
        test_chat_endpoint.py    # API integration tests
    chat/
        __init__.py
        test_service.py          # Service unit tests
        test_streaming.py        # SSE formatting tests
        test_models.py           # Model validation tests
```

### 1. Pydantic Models (`src/omniforge/chat/models.py`)

```python
"""Chat request and response models."""

from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    """Incoming chat message request."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="The user's message to the chatbot",
    )
    conversation_id: Optional[UUID] = Field(
        default=None,
        description="Optional conversation ID for context (future use)",
    )

    @field_validator("message")
    @classmethod
    def message_not_whitespace(cls, v: str) -> str:
        """Ensure message is not just whitespace."""
        if not v.strip():
            raise ValueError("Message cannot be empty or whitespace only")
        return v


class ChunkEvent(BaseModel):
    """SSE chunk event data."""

    content: str


class UsageInfo(BaseModel):
    """Token usage information."""

    tokens: int


class DoneEvent(BaseModel):
    """SSE done event data."""

    conversation_id: UUID
    usage: UsageInfo


class ErrorEvent(BaseModel):
    """SSE error event data."""

    code: str
    message: str
```

### 2. Custom Exceptions (`src/omniforge/chat/errors.py`)

```python
"""Custom exceptions for chat functionality."""

from typing import Optional


class ChatError(Exception):
    """Base exception for chat-related errors."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 500,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class ValidationError(ChatError):
    """Request validation failed."""

    def __init__(self, message: str) -> None:
        super().__init__(
            code="validation_error",
            message=message,
            status_code=400,
        )


class MessageTooLongError(ChatError):
    """Message exceeds maximum length."""

    def __init__(self, max_length: int = 10000) -> None:
        super().__init__(
            code="message_too_long",
            message=f"Message exceeds maximum length of {max_length} characters",
            status_code=400,
        )


class InternalError(ChatError):
    """Internal server error."""

    def __init__(self, message: str = "An internal error occurred") -> None:
        super().__init__(
            code="internal_error",
            message=message,
            status_code=500,
        )
```

### 3. Response Generator (`src/omniforge/chat/response_generator.py`)

```python
"""Response generation for chat messages.

This module provides placeholder response generation for v1.
In future versions, this will integrate with LLM providers.
"""

from typing import AsyncIterator


class ResponseGenerator:
    """Generates chat responses.

    In v1, this provides placeholder responses. Future versions
    will integrate with LLM providers (OpenAI, Anthropic, etc.).
    """

    async def generate_stream(self, message: str) -> AsyncIterator[str]:
        """Generate a streaming response for the given message.

        Args:
            message: The user's input message.

        Yields:
            Response chunks as strings.
        """
        # Placeholder implementation - echoes message with prefix
        response_parts = [
            "Thank you for your message. ",
            "You said: ",
            f'"{message[:100]}{"..." if len(message) > 100 else ""}". ',
            "This is a placeholder response. ",
            "LLM integration coming soon!",
        ]

        for part in response_parts:
            yield part

    def count_tokens(self, text: str) -> int:
        """Count tokens in text.

        Args:
            text: Text to count tokens for.

        Returns:
            Approximate token count (simplified for v1).
        """
        # Simple approximation: ~4 characters per token
        return max(1, len(text) // 4)
```

### 4. SSE Streaming (`src/omniforge/chat/streaming.py`)

```python
"""Server-Sent Events streaming utilities."""

import json
from typing import Any, AsyncIterator

from omniforge.chat.models import ChunkEvent, DoneEvent, ErrorEvent


def format_sse_event(event_type: str, data: Any) -> str:
    """Format data as an SSE event.

    Args:
        event_type: The event type (chunk, done, error).
        data: The event data (will be JSON serialized if not a string).

    Returns:
        Formatted SSE event string.
    """
    if isinstance(data, str):
        json_data = data
    else:
        json_data = json.dumps(data)

    return f"event: {event_type}\ndata: {json_data}\n\n"


def format_chunk_event(content: str) -> str:
    """Format a chunk event.

    Args:
        content: The chunk content.

    Returns:
        Formatted SSE chunk event.
    """
    event = ChunkEvent(content=content)
    return format_sse_event("chunk", event.model_dump())


def format_done_event(done_event: DoneEvent) -> str:
    """Format a done event.

    Args:
        done_event: The done event data.

    Returns:
        Formatted SSE done event.
    """
    return format_sse_event("done", done_event.model_dump(mode="json"))


def format_error_event(error_event: ErrorEvent) -> str:
    """Format an error event.

    Args:
        error_event: The error event data.

    Returns:
        Formatted SSE error event.
    """
    return format_sse_event("error", error_event.model_dump())


async def stream_with_error_handling(
    stream: AsyncIterator[str],
) -> AsyncIterator[str]:
    """Wrap a stream with error handling.

    Catches exceptions and yields error events instead of raising.

    Args:
        stream: The source stream.

    Yields:
        SSE formatted events.
    """
    try:
        async for item in stream:
            yield item
    except Exception as e:
        error_event = ErrorEvent(
            code="stream_error",
            message=str(e),
        )
        yield format_error_event(error_event)
```

### 5. Chat Service (`src/omniforge/chat/service.py`)

```python
"""Chat service orchestrating request processing."""

from typing import AsyncIterator
from uuid import UUID, uuid4

from omniforge.chat.models import ChatRequest, DoneEvent, ErrorEvent, UsageInfo
from omniforge.chat.response_generator import ResponseGenerator
from omniforge.chat.streaming import (
    format_chunk_event,
    format_done_event,
    format_error_event,
)


class ChatService:
    """Orchestrates chat request processing."""

    def __init__(self, response_generator: ResponseGenerator | None = None) -> None:
        """Initialize the chat service.

        Args:
            response_generator: Optional response generator (for testing).
        """
        self._response_generator = response_generator or ResponseGenerator()

    async def process_chat(self, request: ChatRequest) -> AsyncIterator[str]:
        """Process a chat request and stream the response.

        Args:
            request: The validated chat request.

        Yields:
            SSE formatted events (chunk, done, or error).
        """
        conversation_id = request.conversation_id or uuid4()
        total_content = ""

        try:
            # Stream response chunks
            async for chunk in self._response_generator.generate_stream(
                request.message
            ):
                total_content += chunk
                yield format_chunk_event(chunk)

            # Send done event with metadata
            token_count = self._response_generator.count_tokens(total_content)
            done_event = DoneEvent(
                conversation_id=conversation_id,
                usage=UsageInfo(tokens=token_count),
            )
            yield format_done_event(done_event)

        except Exception as e:
            # Stream error event
            error_event = ErrorEvent(
                code="processing_error",
                message=f"Error generating response: {str(e)}",
            )
            yield format_error_event(error_event)
```

### 6. Chat Endpoint (`src/omniforge/api/routes/chat.py`)

```python
"""Chat API endpoint."""

import asyncio
from typing import AsyncIterator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import ValidationError as PydanticValidationError

from omniforge.chat.errors import ChatError, ValidationError
from omniforge.chat.models import ChatRequest, ErrorEvent
from omniforge.chat.service import ChatService
from omniforge.chat.streaming import format_error_event

router = APIRouter(prefix="/api/v1", tags=["chat"])

# Service instance (could be injected via dependency injection in future)
_chat_service = ChatService()


async def _stream_response(
    request: ChatRequest,
    http_request: Request,
) -> AsyncIterator[str]:
    """Stream the chat response, handling client disconnection.

    Args:
        request: The validated chat request.
        http_request: The HTTP request for disconnect detection.

    Yields:
        SSE formatted events.
    """
    async for event in _chat_service.process_chat(request):
        # Check if client disconnected
        if await http_request.is_disconnected():
            break
        yield event


@router.post(
    "/chat",
    response_class=StreamingResponse,
    summary="Chat with the agent",
    description="Send a message and receive a streaming SSE response.",
    responses={
        200: {
            "description": "SSE stream of chat response",
            "content": {"text/event-stream": {}},
        },
        400: {"description": "Invalid request"},
        422: {"description": "Validation error"},
    },
)
async def chat(
    request: Request,
    body: ChatRequest,
) -> StreamingResponse:
    """Chat endpoint that streams responses via SSE.

    Args:
        request: The HTTP request.
        body: The validated chat request body.

    Returns:
        StreamingResponse with SSE content.
    """
    return StreamingResponse(
        _stream_response(body, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
```

### 7. Error Handler Middleware (`src/omniforge/api/middleware/error_handler.py`)

```python
"""Global error handling middleware."""

import logging
from typing import Callable

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError

from omniforge.chat.errors import ChatError

logger = logging.getLogger(__name__)


def setup_error_handlers(app: FastAPI) -> None:
    """Configure global error handlers for the application.

    Args:
        app: The FastAPI application.
    """

    @app.exception_handler(ChatError)
    async def chat_error_handler(
        request: Request,
        exc: ChatError,
    ) -> JSONResponse:
        """Handle ChatError exceptions."""
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.code, "message": exc.message},
        )

    @app.exception_handler(PydanticValidationError)
    async def validation_error_handler(
        request: Request,
        exc: PydanticValidationError,
    ) -> JSONResponse:
        """Handle Pydantic validation errors."""
        errors = exc.errors()
        message = "; ".join(
            f"{err['loc'][-1]}: {err['msg']}" for err in errors
        )
        return JSONResponse(
            status_code=400,
            content={"code": "validation_error", "message": message},
        )

    @app.exception_handler(Exception)
    async def generic_error_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        """Handle unexpected exceptions."""
        logger.exception("Unexpected error occurred")
        return JSONResponse(
            status_code=500,
            content={
                "code": "internal_error",
                "message": "An unexpected error occurred",
            },
        )
```

### 8. FastAPI Application Factory (`src/omniforge/api/app.py`)

```python
"""FastAPI application factory."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from omniforge.api.middleware.error_handler import setup_error_handlers
from omniforge.api.routes import chat


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance.
    """
    app = FastAPI(
        title="OmniForge Chat API",
        description="Core chatbot agent for the OmniForge platform",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Configure CORS (permissive for development)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Restrict in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Setup error handlers
    setup_error_handlers(app)

    # Include routers
    app.include_router(chat.router)

    # Health check endpoint
    @app.get("/health", tags=["health"])
    async def health_check() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "healthy"}

    return app


# Application instance for uvicorn
app = create_app()
```

---

## API Specification

### Endpoint: POST /api/v1/chat

**Request:**
```json
{
  "message": "Hello, help me create an agent",
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| message | string | Yes | 1-10,000 characters, non-whitespace |
| conversation_id | UUID | No | Valid UUID v4 format |

**Response (SSE Stream):**
```
Content-Type: text/event-stream

event: chunk
data: {"content": "Thank you for your message. "}

event: chunk
data: {"content": "You said: \"Hello, help me create an agent\". "}

event: chunk
data: {"content": "This is a placeholder response. "}

event: chunk
data: {"content": "LLM integration coming soon!"}

event: done
data: {"conversation_id": "550e8400-e29b-41d4-a716-446655440000", "usage": {"tokens": 42}}
```

**Error Response (SSE):**
```
event: error
data: {"code": "processing_error", "message": "Error generating response: ..."}
```

**Error Response (HTTP 400/422):**
```json
{
  "code": "validation_error",
  "message": "message: String should have at least 1 character"
}
```

---

## Error Handling Strategy

### Error Categories

| Category | HTTP Code | SSE Event | When |
|----------|-----------|-----------|------|
| Validation Error | 400 | N/A (before stream) | Invalid request body |
| Processing Error | N/A | `error` | Error during response generation |
| Internal Error | 500 | N/A or `error` | Unexpected server error |

### Error Response Format

All errors follow a consistent format:
```json
{
  "code": "error_code",
  "message": "Human-readable error message"
}
```

### Error Codes

| Code | Description |
|------|-------------|
| `validation_error` | Request failed validation |
| `message_too_long` | Message exceeds 10,000 characters |
| `processing_error` | Error during response generation |
| `stream_error` | Error during SSE streaming |
| `internal_error` | Unexpected server error |

---

## Testing Strategy

### Test Categories

| Category | Coverage Target | Description |
|----------|-----------------|-------------|
| Unit Tests | 100% | Isolated component testing |
| Integration Tests | Key paths | API endpoint testing |
| SSE Stream Tests | All event types | Stream format verification |

### Test Files

**`tests/conftest.py`** - Shared fixtures:
```python
"""Pytest fixtures for chat tests."""

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

from omniforge.api.app import create_app


@pytest.fixture
def app():
    """Create a test application."""
    return create_app()


@pytest.fixture
def client(app):
    """Create a synchronous test client."""
    return TestClient(app)


@pytest.fixture
async def async_client(app):
    """Create an async test client for SSE testing."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
```

**`tests/api/test_chat_endpoint.py`** - API tests:
```python
"""Tests for chat API endpoint."""

import pytest
from fastapi.testclient import TestClient


class TestChatEndpoint:
    """Test cases for POST /api/v1/chat."""

    def test_valid_message_returns_stream(self, client: TestClient) -> None:
        """Test that valid message returns SSE stream."""
        response = client.post(
            "/api/v1/chat",
            json={"message": "Hello"},
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

    def test_empty_message_returns_400(self, client: TestClient) -> None:
        """Test that empty message returns validation error."""
        response = client.post(
            "/api/v1/chat",
            json={"message": ""},
        )
        assert response.status_code == 422

    def test_whitespace_message_returns_400(self, client: TestClient) -> None:
        """Test that whitespace-only message returns error."""
        response = client.post(
            "/api/v1/chat",
            json={"message": "   "},
        )
        assert response.status_code == 422

    def test_message_too_long_returns_400(self, client: TestClient) -> None:
        """Test that overly long message returns error."""
        response = client.post(
            "/api/v1/chat",
            json={"message": "x" * 10001},
        )
        assert response.status_code == 422

    def test_stream_contains_chunk_events(self, client: TestClient) -> None:
        """Test that stream contains chunk events."""
        response = client.post(
            "/api/v1/chat",
            json={"message": "Hello"},
        )
        content = response.text
        assert "event: chunk" in content

    def test_stream_ends_with_done_event(self, client: TestClient) -> None:
        """Test that stream ends with done event."""
        response = client.post(
            "/api/v1/chat",
            json={"message": "Hello"},
        )
        content = response.text
        assert "event: done" in content

    def test_done_event_contains_conversation_id(self, client: TestClient) -> None:
        """Test that done event includes conversation_id."""
        response = client.post(
            "/api/v1/chat",
            json={"message": "Hello"},
        )
        content = response.text
        assert "conversation_id" in content

    def test_conversation_id_preserved(self, client: TestClient) -> None:
        """Test that provided conversation_id is returned."""
        conv_id = "550e8400-e29b-41d4-a716-446655440000"
        response = client.post(
            "/api/v1/chat",
            json={"message": "Hello", "conversation_id": conv_id},
        )
        content = response.text
        assert conv_id in content
```

**`tests/chat/test_models.py`** - Model validation tests:
```python
"""Tests for chat models."""

import pytest
from pydantic import ValidationError

from omniforge.chat.models import ChatRequest


class TestChatRequest:
    """Test cases for ChatRequest model."""

    def test_valid_message(self) -> None:
        """Test valid message is accepted."""
        request = ChatRequest(message="Hello")
        assert request.message == "Hello"

    def test_empty_message_rejected(self) -> None:
        """Test empty message raises validation error."""
        with pytest.raises(ValidationError):
            ChatRequest(message="")

    def test_whitespace_message_rejected(self) -> None:
        """Test whitespace-only message raises error."""
        with pytest.raises(ValidationError):
            ChatRequest(message="   ")

    def test_max_length_enforced(self) -> None:
        """Test message exceeding max length raises error."""
        with pytest.raises(ValidationError):
            ChatRequest(message="x" * 10001)

    def test_optional_conversation_id(self) -> None:
        """Test conversation_id is optional."""
        request = ChatRequest(message="Hello")
        assert request.conversation_id is None

    def test_valid_conversation_id(self) -> None:
        """Test valid UUID conversation_id is accepted."""
        from uuid import uuid4
        conv_id = uuid4()
        request = ChatRequest(message="Hello", conversation_id=conv_id)
        assert request.conversation_id == conv_id
```

**`tests/chat/test_streaming.py`** - SSE formatting tests:
```python
"""Tests for SSE streaming utilities."""

from uuid import uuid4

from omniforge.chat.models import DoneEvent, ErrorEvent, UsageInfo
from omniforge.chat.streaming import (
    format_chunk_event,
    format_done_event,
    format_error_event,
    format_sse_event,
)


class TestSSEFormatting:
    """Test cases for SSE event formatting."""

    def test_format_sse_event(self) -> None:
        """Test basic SSE event formatting."""
        result = format_sse_event("test", {"key": "value"})
        assert result == 'event: test\ndata: {"key": "value"}\n\n'

    def test_format_chunk_event(self) -> None:
        """Test chunk event formatting."""
        result = format_chunk_event("Hello")
        assert "event: chunk" in result
        assert '"content": "Hello"' in result

    def test_format_done_event(self) -> None:
        """Test done event formatting."""
        conv_id = uuid4()
        done = DoneEvent(
            conversation_id=conv_id,
            usage=UsageInfo(tokens=42),
        )
        result = format_done_event(done)
        assert "event: done" in result
        assert str(conv_id) in result
        assert '"tokens": 42' in result

    def test_format_error_event(self) -> None:
        """Test error event formatting."""
        error = ErrorEvent(code="test_error", message="Test message")
        result = format_error_event(error)
        assert "event: error" in result
        assert "test_error" in result
        assert "Test message" in result
```

### Running Tests

```bash
# Run all tests with coverage
pytest

# Run specific test file
pytest tests/api/test_chat_endpoint.py

# Run with verbose output
pytest -v

# Run without coverage
pytest --no-cov
```

---

## Infrastructure and Deployment

### Local Development

```bash
# Install dependencies
pip install -e ".[dev]"
pip install fastapi uvicorn pydantic httpx

# Run development server
uvicorn omniforge.api.app:app --reload --port 8000
```

### Docker (Future)

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY . .
RUN pip install -e ".[dev]" && \
    pip install fastapi uvicorn pydantic

EXPOSE 8000
CMD ["uvicorn", "omniforge.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Variables (Future)

| Variable | Description | Default |
|----------|-------------|---------|
| `PORT` | Server port | 8000 |
| `LOG_LEVEL` | Logging level | INFO |
| `CORS_ORIGINS` | Allowed CORS origins | * |

---

## Monitoring and Operations

### Logging

- Use Python's standard `logging` module
- Log all requests with conversation_id for tracing
- Log errors with full stack traces at ERROR level
- Structured JSON logging recommended for production

### Health Check

- `GET /health` endpoint returns `{"status": "healthy"}`
- Use for Kubernetes liveness/readiness probes

### Metrics (Future)

Consider adding:
- Request count by endpoint
- Response latency histograms
- Error rate by error code
- Active SSE connections

---

## Development Workflow

### Repository Structure

All new files follow the structure in "File Structure" section above.

### Branching Strategy

1. Create feature branch: `feature/core-chatbot-agent`
2. Implement components incrementally
3. Ensure all tests pass with coverage
4. Run linting and type checking
5. Create pull request for review

### Quality Gates

Before merging:
- [ ] `pytest` - All tests pass
- [ ] `pytest --cov` - Coverage > 80%
- [ ] `black .` - Code formatted
- [ ] `ruff check .` - No linting errors
- [ ] `mypy src/` - No type errors

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| SSE connection issues in production | Medium | High | Implement connection timeouts, heartbeat mechanism in future |
| Client disconnect not detected | Low | Medium | Use `request.is_disconnected()` check |
| Memory leak from unclosed streams | Low | High | Proper async generator cleanup, testing |
| Slow response generation blocks event loop | Medium | Medium | Use async generators, consider background tasks |
| Pydantic v2 breaking changes | Low | Medium | Pin dependency versions |

---

## Implementation Phases

### Phase 1: Core Infrastructure (Day 1)

1. Add FastAPI dependencies to `pyproject.toml`
2. Create directory structure
3. Implement Pydantic models (`models.py`)
4. Implement custom exceptions (`errors.py`)

### Phase 2: Streaming Layer (Day 1-2)

1. Implement SSE formatting (`streaming.py`)
2. Implement placeholder response generator (`response_generator.py`)
3. Write unit tests for streaming and models

### Phase 3: API Layer (Day 2)

1. Implement chat service (`service.py`)
2. Implement chat endpoint (`routes/chat.py`)
3. Implement error handling middleware
4. Create FastAPI app factory

### Phase 4: Testing and Polish (Day 2-3)

1. Write integration tests
2. Add test fixtures
3. Run full test suite with coverage
4. Run linting and type checking
5. Fix any issues

### Phase 5: Documentation (Day 3)

1. Add docstrings to all public functions
2. Verify OpenAPI documentation
3. Update README if needed

---

## Alternative Approaches Considered

### 1. WebSockets Instead of SSE

**Pros:**
- Bidirectional communication
- Lower overhead for frequent messages
- Better connection state management

**Cons:**
- More complex implementation
- Not as HTTP-native (proxy issues)
- Overkill for unidirectional streaming

**Decision:** SSE chosen for simplicity and HTTP compatibility, per spec requirement.

### 2. Async Framework: Starlette vs FastAPI

**Pros of Starlette:**
- Lighter weight
- More control

**Cons of Starlette:**
- No built-in validation
- More boilerplate
- Less documentation

**Decision:** FastAPI chosen for Pydantic integration and automatic OpenAPI docs.

### 3. Response Generator: Async Generator vs Callback

**Async Generator:**
- Clean iteration with `async for`
- Natural fit for streaming
- Easy to compose

**Callback:**
- More complex coordination
- Harder to test
- Less Pythonic

**Decision:** Async generators chosen for clarity and testability.

---

## Future Considerations

### LLM Integration (v2)

The `ResponseGenerator` class is designed for easy extension:
```python
class OpenAIResponseGenerator(ResponseGenerator):
    async def generate_stream(self, message: str) -> AsyncIterator[str]:
        # Integrate with OpenAI streaming API
        pass
```

### Authentication (v2)

Add middleware for API key or JWT validation:
```python
@router.post("/chat")
async def chat(
    request: Request,
    body: ChatRequest,
    api_key: str = Depends(verify_api_key),  # Add dependency
) -> StreamingResponse:
    ...
```

### Conversation Context (v2)

Store and retrieve conversation history:
- Redis for session storage
- Database for persistent history
- Context window management

---

## Appendix: Dependency Updates

Add to `pyproject.toml`:

```toml
[project]
dependencies = [
    "fastapi>=0.100.0",
    "uvicorn>=0.23.0",
    "pydantic>=2.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "pytest-asyncio>=0.21.0",
    "httpx>=0.24.0",
    "black>=23.0.0",
    "ruff>=0.1.0",
    "mypy>=1.0.0",
]
```

---

## Summary

This technical plan provides a comprehensive blueprint for implementing the Core Chatbot Agent. The design prioritizes:

1. **Simplicity**: Minimal dependencies, clear separation of concerns
2. **Type Safety**: Full mypy compatibility with strict type annotations
3. **Testability**: Modular design enabling comprehensive unit and integration testing
4. **Extensibility**: Clean abstractions for future LLM integration
5. **Reliability**: Proper error handling at all layers

The implementation can be completed in approximately 3 days and establishes the foundation for OmniForge's conversational interface.
