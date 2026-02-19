# Base Agent Interface - Technical Implementation Plan

**Created**: 2026-01-03
**Last Updated**: 2026-01-03
**Version**: 1.0
**Status**: Draft

---

## Executive Summary

This technical plan defines the implementation architecture for OmniForge's Base Agent Interface, following Google's A2A (Agent2Agent) protocol. The design prioritizes **integration with existing infrastructure**, specifically reusing the SSE streaming utilities in `chat/streaming.py` and extending the Pydantic models in `chat/models.py`.

**Key Architectural Decisions:**

1. **Abstract Base Class Pattern**: `BaseAgent` serves as the foundation all agents extend, with a clean interface for task processing
2. **Shared Streaming Infrastructure**: Extend existing `chat/streaming.py` to support A2A protocol events without duplication
3. **Event-Driven Task Lifecycle**: Tasks emit typed events that flow through a unified streaming pipeline
4. **Repository Pattern for Persistence**: Pluggable storage backends with in-memory default for local SDK use
5. **Enterprise Extensions as Mixins**: Multi-tenancy and RBAC as composable mixins, not baked into the core interface

**Implementation Scope:**
- Phase 1: Core agent interface and streaming (2-3 weeks)
- Phase 2: Task persistence and agent registry (1-2 weeks)
- Phase 3: Agent-to-agent communication (1-2 weeks)
- Phase 4: Enterprise features (2-3 weeks)

---

## Requirements Analysis

### Functional Requirements (from Product Spec)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR1 | BaseAgent abstract class with identity, capabilities, skills | Must Have |
| FR2 | Agent Card generation and serving (/.well-known/agent-card.json) | Must Have |
| FR3 | Task lifecycle management (submitted, working, input_required, completed, failed) | Must Have |
| FR4 | SSE streaming for real-time task updates | Must Have |
| FR5 | Message parts (TextPart, FilePart, DataPart) | Must Have |
| FR6 | Artifact generation and delivery | Must Have |
| FR7 | SDK-based agent creation (Python class extension) | Must Have |
| FR8 | API-based agent creation (POST /api/v1/agents) | Should Have |
| FR9 | Chat-based agent creation (via chatbot interface) | Should Have |
| FR10 | Agent-to-agent discovery and communication | Should Have |
| FR11 | Push notification support (webhooks) | Nice to Have |
| FR12 | Polling fallback for non-streaming clients | Nice to Have |

### Non-Functional Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR1 | Initial task acknowledgment latency | < 100ms |
| NFR2 | Streaming connection success rate | > 99% |
| NFR3 | Type annotation coverage | 100% |
| NFR4 | Test coverage | >= 80% |
| NFR5 | A2A protocol version | 0.3 |
| NFR6 | Python version compatibility | >= 3.9 |

### Integration Requirements

| ID | Requirement | Approach |
|----|-------------|----------|
| IR1 | Reuse `chat/streaming.py` SSE utilities | Extend with new event formatters |
| IR2 | Extend `chat/models.py` Pydantic models | Add A2A-specific models alongside |
| IR3 | Integrate with existing FastAPI app | Add new router at /api/v1/agents |
| IR4 | Support existing error handling patterns | Extend `ChatError` hierarchy |

---

## Constraints and Assumptions

### Constraints

1. **Python 3.9+ Compatibility**: All code must work with Python 3.9 features only
2. **Existing Infrastructure**: Must integrate with current FastAPI app structure
3. **Line Length**: 100 characters (Black/Ruff configuration)
4. **Type Safety**: mypy strict mode with `disallow_untyped_defs = true`
5. **SSE Reuse**: Agent streaming MUST use `chat/streaming.py` utilities

### Assumptions

1. **Database**: No database exists yet; plan assumes adding SQLAlchemy/SQLite for persistence
2. **Security Module**: Does not exist; will be created as part of Phase 4
3. **Orchestration Module**: Does not exist; will be created as part of Phase 3
4. **A2A Version**: Targeting version 0.3 (latest stable draft)
5. **Local-First**: SDK works standalone without platform connection

---

## System Architecture

### High-Level Architecture

```
+-------------------------------------------------------------------+
|                        OmniForge Platform                          |
+-------------------------------------------------------------------+
|                                                                    |
|  +------------------+    +------------------+    +---------------+ |
|  |   API Layer      |    |  Agent Registry  |    |   Security    | |
|  |  (FastAPI)       |    |  (Discovery)     |    |  (RBAC/Auth)  | |
|  +--------+---------+    +--------+---------+    +-------+-------+ |
|           |                       |                      |         |
|           v                       v                      v         |
|  +-----------------------------------------------------------+    |
|  |                    Agent Execution Layer                   |    |
|  |  +-------------+  +--------------+  +------------------+   |    |
|  |  | BaseAgent   |  | TaskManager  |  | StreamingBridge  |   |    |
|  |  | (Abstract)  |  | (Lifecycle)  |  | (SSE Events)     |   |    |
|  |  +-------------+  +--------------+  +------------------+   |    |
|  +-----------------------------------------------------------+    |
|           |                       |                               |
|           v                       v                               |
|  +------------------+    +------------------+                     |
|  |  Task Repository |    | Agent Repository |                     |
|  |  (Persistence)   |    | (Persistence)    |                     |
|  +------------------+    +------------------+                     |
|           |                       |                               |
|           v                       v                               |
|  +-----------------------------------------------------------+    |
|  |                    Storage Backend                         |    |
|  |  (In-Memory / SQLite / PostgreSQL)                        |    |
|  +-----------------------------------------------------------+    |
+-------------------------------------------------------------------+
```

### Streaming Integration Architecture

```
                     Existing Chat Flow                    New Agent Flow
                     ================                      ==============

+----------------+   +------------------+   +----------------+   +------------------+
|  ChatRequest   |   |  ResponseGen     |   |  AgentTask     |   |  BaseAgent       |
|  (models.py)   |-->|  generate_stream |   |  (models.py)   |-->|  process_task    |
+----------------+   +--------+---------+   +----------------+   +--------+---------+
                              |                                           |
                              v                                           v
                     +------------------+                        +------------------+
                     |  ChunkEvent      |                        |  TaskEvent       |
                     |  DoneEvent       |                        |  (Status/Message |
                     |  ErrorEvent      |                        |   /Artifact)     |
                     +--------+---------+                        +--------+---------+
                              |                                           |
                              +-------------------+-------------------+
                                                  |
                                                  v
                                         +------------------+
                                         | streaming.py     |
                                         | format_sse_event |
                                         +--------+---------+
                                                  |
                                                  v
                                         +------------------+
                                         | StreamingResponse|
                                         | (FastAPI)        |
                                         +------------------+
```

### Component Interaction Diagram

```
Client                    API                     Agent                    Storage
  |                        |                        |                         |
  |-- POST /tasks -------->|                        |                         |
  |                        |-- create_task -------->|                         |
  |                        |                        |-- save(task) ---------->|
  |                        |<--- task_id -----------|                         |
  |<-- SSE Stream ---------|                        |                         |
  |                        |                        |                         |
  |                        |-- process_task ------->|                         |
  |                        |                        |-- update_status ------->|
  |<-- event: status ------|<-- TaskStatusEvent ----|                         |
  |                        |                        |                         |
  |                        |                        |-- yield message ------->|
  |<-- event: message -----|<-- TaskMessageEvent ---|                         |
  |                        |                        |                         |
  |                        |                        |-- yield artifact ------>|
  |<-- event: artifact ----|<-- TaskArtifactEvent --|                         |
  |                        |                        |                         |
  |<-- event: done --------|<-- TaskDoneEvent ------|-- mark_complete ------->|
  |                        |                        |                         |
```

---

## Technology Stack

### Core Dependencies (Existing)

| Dependency | Version | Purpose |
|------------|---------|---------|
| fastapi | >=0.100.0 | Web framework, SSE streaming |
| pydantic | >=2.0.0 | Data validation, models |
| uvicorn | >=0.23.0 | ASGI server |

### New Dependencies (Required)

| Dependency | Version | Purpose | Justification |
|------------|---------|---------|---------------|
| sqlalchemy | >=2.0.0 | ORM for task/agent persistence | Industry standard, async support |
| aiosqlite | >=0.19.0 | Async SQLite driver | Local development, SDK standalone |

### Development Dependencies (Existing)

All existing dev dependencies remain unchanged.

---

## Module Structure

### Directory Layout

```
src/omniforge/
|-- __init__.py
|-- agents/                          # NEW: Base agent implementation
|   |-- __init__.py
|   |-- base.py                      # BaseAgent abstract class
|   |-- models.py                    # A2A protocol models (AgentCard, Task, etc.)
|   |-- events.py                    # Task event types
|   |-- streaming.py                 # Agent streaming bridge (extends chat/streaming.py)
|   |-- errors.py                    # Agent-specific exceptions
|   |-- skills.py                    # Skill decorator and registry
|   |-- repository.py                # Agent persistence interface
|   |-- registry.py                  # Agent discovery/registry
|
|-- tasks/                           # NEW: Task lifecycle management
|   |-- __init__.py
|   |-- manager.py                   # TaskManager for lifecycle operations
|   |-- models.py                    # Task state models
|   |-- repository.py                # Task persistence interface
|   |-- events.py                    # Task events (extends agent events)
|
|-- orchestration/                   # NEW: Agent-to-agent communication
|   |-- __init__.py
|   |-- router.py                    # Message routing between agents
|   |-- discovery.py                 # Agent discovery service
|   |-- client.py                    # A2A client for outbound communication
|
|-- security/                        # NEW: Enterprise security features
|   |-- __init__.py
|   |-- auth.py                      # Authentication schemes
|   |-- rbac.py                      # Role-based access control
|   |-- tenant.py                    # Multi-tenancy isolation
|
|-- storage/                         # NEW: Persistence layer
|   |-- __init__.py
|   |-- base.py                      # Abstract repository interface
|   |-- memory.py                    # In-memory implementation
|   |-- database.py                  # SQLAlchemy implementation
|   |-- models.py                    # SQLAlchemy ORM models
|
|-- chat/                            # EXISTING: Chat implementation
|   |-- __init__.py
|   |-- streaming.py                 # EXTEND: Add agent event formatters
|   |-- models.py                    # EXTEND: Add shared base classes
|   |-- service.py                   # Unchanged
|   |-- response_generator.py        # Unchanged
|   |-- errors.py                    # EXTEND: Add AgentError hierarchy
|
|-- api/
|   |-- __init__.py
|   |-- app.py                       # MODIFY: Add agent router
|   |-- routes/
|   |   |-- __init__.py
|   |   |-- chat.py                  # Unchanged
|   |   |-- agents.py                # NEW: Agent discovery endpoints
|   |   |-- tasks.py                 # NEW: Task management endpoints
|   |-- middleware/
|   |   |-- __init__.py
|   |   |-- error_handler.py         # EXTEND: Handle AgentError
|   |   |-- tenant.py                # NEW: Tenant context middleware
```

### Module Dependencies

```
                                  +----------------+
                                  |    api/        |
                                  | routes, app    |
                                  +-------+--------+
                                          |
                    +---------------------+---------------------+
                    |                     |                     |
                    v                     v                     v
            +---------------+     +---------------+     +---------------+
            |   agents/     |     |   tasks/      |     |   chat/       |
            | base, models  |     | manager       |     | (existing)    |
            +-------+-------+     +-------+-------+     +---------------+
                    |                     |
                    +----------+----------+
                               |
                               v
                      +----------------+
                      |   storage/     |
                      | repositories   |
                      +----------------+
                               |
                               v
                      +----------------+
                      | orchestration/ |
                      | (agent-agent)  |
                      +----------------+
```

---

## Component Specifications

### 1. BaseAgent Abstract Class

**Location**: `src/omniforge/agents/base.py`

**Purpose**: Abstract base class defining the contract all agents must implement.

```python
from abc import ABC, abstractmethod
from typing import AsyncIterator
from uuid import UUID

from omniforge.agents.models import AgentCard, AgentIdentity, AgentCapabilities, AgentSkill
from omniforge.agents.events import TaskEvent
from omniforge.tasks.models import Task, TaskMessage


class BaseAgent(ABC):
    """Abstract base class for all OmniForge agents.

    Implements the A2A protocol for agent identity, capability discovery,
    and task processing. Subclasses must implement the process_task method
    to define agent-specific behavior.

    Attributes:
        identity: Agent identity information (id, name, description, version)
        capabilities: Feature flags (streaming, push, multi-turn, hitl)
        skills: List of skills this agent provides

    Example:
        class MyAgent(BaseAgent):
            identity = AgentIdentity(
                name="My Agent",
                description="Does something useful"
            )
            skills = [
                AgentSkill(id="greet", name="Greet", description="Says hello")
            ]

            async def process_task(self, task: Task) -> AsyncIterator[TaskEvent]:
                yield TaskMessageEvent(content=TextPart(text="Hello!"))
                yield TaskDoneEvent()
    """

    # Class-level configuration (overridden by subclasses)
    identity: AgentIdentity
    capabilities: AgentCapabilities = AgentCapabilities()
    skills: list[AgentSkill] = []

    def __init__(self, agent_id: UUID | None = None) -> None:
        """Initialize agent with optional explicit ID.

        Args:
            agent_id: Optional UUID. If not provided, generates a new one.
        """
        self._id = agent_id or uuid4()

    @property
    def id(self) -> UUID:
        """Unique identifier for this agent instance."""
        return self._id

    def get_agent_card(self) -> AgentCard:
        """Generate A2A-compliant Agent Card for this agent.

        Returns:
            AgentCard with identity, capabilities, skills, and endpoint info.
        """
        ...

    @abstractmethod
    async def process_task(self, task: Task) -> AsyncIterator[TaskEvent]:
        """Process a task and yield events representing progress.

        This is the main extension point for agent behavior. Implementations
        should yield TaskEvent objects as processing progresses.

        Args:
            task: The task to process, containing messages and context.

        Yields:
            TaskEvent objects (status updates, messages, artifacts, done/error).

        Raises:
            TaskError: If task processing fails unrecoverably.
        """
        ...

    async def handle_message(
        self, task_id: UUID, message: TaskMessage
    ) -> AsyncIterator[TaskEvent]:
        """Handle an additional message on an existing task.

        Default implementation retrieves task and calls process_task.
        Override for custom multi-turn handling.

        Args:
            task_id: ID of the existing task.
            message: New message to process.

        Yields:
            TaskEvent objects representing the response.
        """
        ...

    async def cancel_task(self, task_id: UUID) -> Task:
        """Cancel an in-progress task.

        Args:
            task_id: ID of the task to cancel.

        Returns:
            Updated task with cancelled status.

        Raises:
            TaskNotFoundError: If task does not exist.
            TaskStateError: If task is not cancellable.
        """
        ...
```

### 2. A2A Protocol Models

**Location**: `src/omniforge/agents/models.py`

**Purpose**: Pydantic models for A2A protocol entities.

```python
from datetime import datetime
from enum import Enum
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


# ============================================================
# Agent Identity and Discovery
# ============================================================

class AgentIdentity(BaseModel):
    """Agent identity information."""
    id: UUID = Field(default_factory=uuid4)
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(default="")
    version: str = Field(default="1.0.0")


class AgentCapabilities(BaseModel):
    """Feature flags indicating agent capabilities."""
    streaming: bool = True
    push_notifications: bool = False
    multi_turn: bool = True
    hitl_support: bool = True


class SkillInputMode(str, Enum):
    """Supported input content types for a skill."""
    TEXT = "text"
    FILE = "file"
    DATA = "data"


class SkillOutputMode(str, Enum):
    """Supported output content types for a skill."""
    TEXT = "text"
    FILE = "file"
    DATA = "data"


class AgentSkill(BaseModel):
    """A discrete capability offered by an agent."""
    id: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(default="")
    tags: list[str] = Field(default_factory=list)
    examples: list[str] = Field(default_factory=list)
    input_modes: list[SkillInputMode] = Field(
        default_factory=lambda: [SkillInputMode.TEXT]
    )
    output_modes: list[SkillOutputMode] = Field(
        default_factory=lambda: [SkillOutputMode.TEXT]
    )


class AuthScheme(str, Enum):
    """Supported authentication schemes."""
    NONE = "none"
    API_KEY = "api_key"
    BEARER = "bearer"
    OAUTH2 = "oauth2"


class SecurityConfig(BaseModel):
    """Security configuration for an agent."""
    auth_schemes: list[AuthScheme] = Field(
        default_factory=lambda: [AuthScheme.NONE]
    )
    tenant_isolation: bool = False


class AgentCard(BaseModel):
    """A2A-compliant Agent Card for capability discovery.

    This is the primary discovery mechanism for agents. Clients fetch
    the Agent Card to understand what an agent can do and how to
    communicate with it.
    """
    # Identity
    id: UUID
    name: str
    description: str
    version: str

    # Protocol
    protocol_version: str = Field(default="0.3", alias="protocolVersion")

    # Connection
    service_endpoint: str = Field(..., alias="serviceEndpoint")

    # Capabilities
    capabilities: AgentCapabilities

    # Skills
    skills: list[AgentSkill]

    # Security
    security: SecurityConfig = Field(default_factory=SecurityConfig)

    class Config:
        populate_by_name = True


# ============================================================
# Message Parts (A2A Protocol)
# ============================================================

class TextPart(BaseModel):
    """Plain text or markdown content."""
    type: Literal["text"] = "text"
    text: str
    mime_type: str = Field(default="text/plain", alias="mimeType")


class FilePart(BaseModel):
    """File reference (inline or URI-based)."""
    type: Literal["file"] = "file"
    name: str
    mime_type: str = Field(..., alias="mimeType")
    uri: str | None = None
    data: str | None = None  # Base64 encoded inline content


class DataPart(BaseModel):
    """Structured JSON data."""
    type: Literal["data"] = "data"
    data: dict
    schema_uri: str | None = Field(default=None, alias="schemaUri")


# Union type for message parts
MessagePart = TextPart | FilePart | DataPart


# ============================================================
# Artifacts
# ============================================================

class Artifact(BaseModel):
    """Output generated by an agent during task processing."""
    id: UUID = Field(default_factory=uuid4)
    name: str = Field(default="")
    description: str = Field(default="")
    parts: list[MessagePart] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

### 3. Task Models

**Location**: `src/omniforge/tasks/models.py`

**Purpose**: Task state management and lifecycle models.

```python
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from omniforge.agents.models import MessagePart, Artifact


class TaskState(str, Enum):
    """A2A task lifecycle states."""
    SUBMITTED = "submitted"
    WORKING = "working"
    INPUT_REQUIRED = "input_required"
    AUTH_REQUIRED = "auth_required"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class TaskMessage(BaseModel):
    """A message in a task conversation."""
    id: UUID = Field(default_factory=uuid4)
    role: str = Field(..., pattern="^(user|agent)$")
    parts: list[MessagePart]
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TaskError(BaseModel):
    """Error information for failed tasks."""
    code: str
    message: str
    details: dict | None = None


class Task(BaseModel):
    """A unit of work being processed by an agent.

    Tasks represent requests from clients and track progress through
    the A2A task lifecycle.
    """
    id: UUID = Field(default_factory=uuid4)
    agent_id: UUID

    # State
    state: TaskState = TaskState.SUBMITTED

    # Context
    messages: list[TaskMessage] = Field(default_factory=list)
    artifacts: list[Artifact] = Field(default_factory=list)

    # Error (populated on failure)
    error: TaskError | None = None

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Multi-tenancy (optional, populated by platform)
    tenant_id: Optional[str] = None
    user_id: Optional[str] = None

    # Parent task (for agent-to-agent delegation)
    parent_task_id: Optional[UUID] = None


class TaskCreateRequest(BaseModel):
    """Request to create a new task."""
    message: str = Field(..., min_length=1, max_length=100000)
    skill_id: Optional[str] = None
    context: dict = Field(default_factory=dict)


class TaskSendRequest(BaseModel):
    """Request to send a message to an existing task."""
    message: str = Field(..., min_length=1, max_length=100000)
```

### 4. Task Events (Streaming)

**Location**: `src/omniforge/agents/events.py`

**Purpose**: Typed events for task progress streaming.

```python
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from omniforge.agents.models import Artifact, MessagePart
from omniforge.tasks.models import TaskState


class BaseTaskEvent(BaseModel):
    """Base class for all task events."""
    task_id: UUID
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class TaskStatusEvent(BaseTaskEvent):
    """Task state transition event."""
    type: Literal["task_status"] = "task_status"
    state: TaskState
    message: str | None = None


class TaskMessageEvent(BaseTaskEvent):
    """Agent message event (partial or complete)."""
    type: Literal["message"] = "message"
    role: Literal["agent"] = "agent"
    parts: list[MessagePart]
    is_partial: bool = False


class TaskArtifactEvent(BaseTaskEvent):
    """Artifact generation event."""
    type: Literal["artifact"] = "artifact"
    artifact: Artifact


class TaskDoneEvent(BaseTaskEvent):
    """Task completion event."""
    type: Literal["done"] = "done"
    state: TaskState = TaskState.COMPLETED


class TaskErrorEvent(BaseTaskEvent):
    """Task error event."""
    type: Literal["error"] = "error"
    code: str
    message: str
    details: dict | None = None


# Union type for all task events
TaskEvent = (
    TaskStatusEvent |
    TaskMessageEvent |
    TaskArtifactEvent |
    TaskDoneEvent |
    TaskErrorEvent
)
```

### 5. Extended Streaming Module

**Location**: `src/omniforge/agents/streaming.py`

**Purpose**: Bridge between agent events and SSE formatting, **reusing existing `chat/streaming.py`**.

```python
"""Agent streaming utilities extending chat/streaming.py.

This module bridges agent task events to SSE formatting by reusing the
existing SSE utilities from the chat module.
"""

from typing import AsyncIterator

from omniforge.agents.events import (
    TaskEvent,
    TaskStatusEvent,
    TaskMessageEvent,
    TaskArtifactEvent,
    TaskDoneEvent,
    TaskErrorEvent,
)
from omniforge.chat.streaming import format_sse_event


def format_task_event(event: TaskEvent) -> str:
    """Format a TaskEvent as an SSE event string.

    Reuses format_sse_event from chat/streaming.py to ensure consistent
    SSE formatting across the entire platform.

    Args:
        event: The TaskEvent to format.

    Returns:
        SSE-formatted string.
    """
    return format_sse_event(event.type, event.model_dump(mode="json"))


def format_task_status_event(event: TaskStatusEvent) -> str:
    """Format a task status event for SSE."""
    return format_sse_event("task_status", event.model_dump(mode="json"))


def format_task_message_event(event: TaskMessageEvent) -> str:
    """Format a task message event for SSE."""
    return format_sse_event("message", event.model_dump(mode="json"))


def format_task_artifact_event(event: TaskArtifactEvent) -> str:
    """Format a task artifact event for SSE."""
    return format_sse_event("artifact", event.model_dump(mode="json"))


def format_task_done_event(event: TaskDoneEvent) -> str:
    """Format a task done event for SSE."""
    return format_sse_event("done", event.model_dump(mode="json"))


def format_task_error_event(event: TaskErrorEvent) -> str:
    """Format a task error event for SSE."""
    return format_sse_event("error", event.model_dump(mode="json"))


async def stream_task_events(
    events: AsyncIterator[TaskEvent],
) -> AsyncIterator[str]:
    """Convert task event stream to SSE string stream.

    This is the main bridge between agent task processing and SSE delivery.
    It handles all event types and applies consistent formatting.

    Args:
        events: Async iterator of TaskEvent objects.

    Yields:
        SSE-formatted strings for each event.
    """
    async for event in events:
        yield format_task_event(event)


async def stream_task_with_error_handling(
    events: AsyncIterator[TaskEvent],
    task_id: UUID,
) -> AsyncIterator[str]:
    """Wrap task event stream with error handling.

    Similar to chat/streaming.py's stream_with_error_handling, but
    specific to task events.

    Args:
        events: The async iterator of task events.
        task_id: The task ID for error event context.

    Yields:
        SSE-formatted strings, with error events for exceptions.
    """
    try:
        async for event in events:
            yield format_task_event(event)
    except Exception as e:
        error_event = TaskErrorEvent(
            task_id=task_id,
            code="internal_error",
            message=str(e),
        )
        yield format_task_error_event(error_event)
```

### 6. Agent Errors

**Location**: `src/omniforge/agents/errors.py`

**Purpose**: Agent-specific exception hierarchy extending `chat/errors.py` pattern.

```python
"""Agent-specific exceptions.

Extends the error pattern from chat/errors.py for agent operations.
"""


class AgentError(Exception):
    """Base exception for all agent-related errors.

    Mirrors ChatError pattern for consistency across the platform.
    """

    def __init__(self, message: str, code: str, status_code: int) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class AgentNotFoundError(AgentError):
    """Raised when an agent cannot be found."""

    def __init__(self, agent_id: str) -> None:
        super().__init__(
            message=f"Agent {agent_id} not found",
            code="agent_not_found",
            status_code=404,
        )


class TaskNotFoundError(AgentError):
    """Raised when a task cannot be found."""

    def __init__(self, task_id: str) -> None:
        super().__init__(
            message=f"Task {task_id} not found",
            code="task_not_found",
            status_code=404,
        )


class TaskStateError(AgentError):
    """Raised when a task operation is invalid for current state."""

    def __init__(self, message: str) -> None:
        super().__init__(
            message=message,
            code="task_state_error",
            status_code=409,
        )


class SkillNotFoundError(AgentError):
    """Raised when a requested skill is not found."""

    def __init__(self, skill_id: str) -> None:
        super().__init__(
            message=f"Skill {skill_id} not found",
            code="skill_not_found",
            status_code=404,
        )


class AgentProcessingError(AgentError):
    """Raised when agent task processing fails."""

    def __init__(self, message: str) -> None:
        super().__init__(
            message=message,
            code="agent_processing_error",
            status_code=500,
        )
```

---

## API Endpoints Design

### Agent Discovery Endpoints

**Location**: `src/omniforge/api/routes/agents.py`

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/.well-known/agent-card.json` | Public Agent Card (platform default agent) | None |
| GET | `/api/v1/agents` | List registered agents | Optional |
| GET | `/api/v1/agents/{agent_id}` | Get specific agent card | Optional |
| POST | `/api/v1/agents` | Register new agent (API creation) | Required |

### Task Management Endpoints

**Location**: `src/omniforge/api/routes/tasks.py`

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/api/v1/agents/{agent_id}/tasks` | Create new task | Optional |
| GET | `/api/v1/agents/{agent_id}/tasks/{task_id}` | Get task status | Optional |
| POST | `/api/v1/agents/{agent_id}/tasks/{task_id}/send` | Send message (SSE stream) | Optional |
| POST | `/api/v1/agents/{agent_id}/tasks/{task_id}/cancel` | Cancel task | Optional |
| GET | `/api/v1/agents/{agent_id}/tasks` | List tasks (with filters) | Optional |

### Endpoint Implementation Example

```python
"""Task management API routes."""

from typing import AsyncIterator
from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from omniforge.agents.streaming import stream_task_with_error_handling
from omniforge.tasks.manager import TaskManager
from omniforge.tasks.models import TaskCreateRequest, TaskSendRequest

router = APIRouter(prefix="/api/v1/agents/{agent_id}/tasks", tags=["tasks"])


@router.post("")
async def create_task(
    request: Request,
    agent_id: UUID,
    body: TaskCreateRequest,
) -> StreamingResponse:
    """Create a new task and stream results.

    Creates a task for the specified agent and immediately begins
    processing. Returns an SSE stream with task events.
    """
    task_manager = TaskManager.get_instance()

    async def stream_response() -> AsyncIterator[str]:
        task = await task_manager.create_task(agent_id, body)
        events = task_manager.process_task(task)
        async for sse_event in stream_task_with_error_handling(events, task.id):
            if await request.is_disconnected():
                break
            yield sse_event

    return StreamingResponse(
        stream_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/{task_id}/send")
async def send_message(
    request: Request,
    agent_id: UUID,
    task_id: UUID,
    body: TaskSendRequest,
) -> StreamingResponse:
    """Send a message to an existing task and stream response.

    Continues an existing multi-turn conversation with the agent.
    """
    task_manager = TaskManager.get_instance()

    async def stream_response() -> AsyncIterator[str]:
        events = await task_manager.send_message(task_id, body)
        async for sse_event in stream_task_with_error_handling(events, task_id):
            if await request.is_disconnected():
                break
            yield sse_event

    return StreamingResponse(
        stream_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
```

---

## Database Schema

### Entity-Relationship Diagram

```
+------------------+       +------------------+       +------------------+
|     agents       |       |      tasks       |       |    artifacts     |
+------------------+       +------------------+       +------------------+
| id (PK)          |<---+  | id (PK)          |<---+  | id (PK)          |
| name             |    |  | agent_id (FK)    |    |  | task_id (FK)     |
| description      |    |  | state            |    |  | name             |
| version          |    |  | messages (JSON)  |    |  | description      |
| capabilities     |    |  | error (JSON)     |    |  | parts (JSON)     |
| skills (JSON)    |    |  | tenant_id        |    |  | created_at       |
| security (JSON)  |    |  | user_id          |    |  +------------------+
| tenant_id        |    |  | parent_task_id   |
| created_at       |    |  | created_at       |
| updated_at       |    +--| updated_at       |
+------------------+       +------------------+
```

### SQLAlchemy Models

**Location**: `src/omniforge/storage/models.py`

```python
"""SQLAlchemy ORM models for persistence."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, String, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


class AgentModel(Base):
    """Persistent agent registration."""

    __tablename__ = "agents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    version = Column(String(50), nullable=False, default="1.0.0")
    capabilities = Column(JSON, nullable=False, default=dict)
    skills = Column(JSON, nullable=False, default=list)
    security = Column(JSON, nullable=False, default=dict)

    # Multi-tenancy
    tenant_id = Column(String(100), nullable=True, index=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tasks = relationship("TaskModel", back_populates="agent")


class TaskModel(Base):
    """Persistent task storage."""

    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)
    state = Column(String(50), nullable=False, default="submitted")
    messages = Column(JSON, nullable=False, default=list)
    error = Column(JSON, nullable=True)

    # Multi-tenancy
    tenant_id = Column(String(100), nullable=True, index=True)
    user_id = Column(String(100), nullable=True, index=True)

    # Parent task (agent-to-agent)
    parent_task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    agent = relationship("AgentModel", back_populates="tasks")
    artifacts = relationship("ArtifactModel", back_populates="task")
    parent = relationship("TaskModel", remote_side=[id])


class ArtifactModel(Base):
    """Persistent artifact storage."""

    __tablename__ = "artifacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False)
    name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    parts = Column(JSON, nullable=False, default=list)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    task = relationship("TaskModel", back_populates="artifacts")
```

---

## Streaming Event Flow

### Complete Event Flow Diagram

```
+------------+    +-------------+    +---------------+    +-------------+
|   Client   |    |  API Layer  |    |  TaskManager  |    |  BaseAgent  |
+------------+    +-------------+    +---------------+    +-------------+
      |                 |                   |                    |
      | POST /tasks     |                   |                    |
      |---------------->|                   |                    |
      |                 | create_task()     |                    |
      |                 |------------------>|                    |
      |                 |                   | new Task           |
      |                 |                   |<-------------------|
      |                 | SSE: task_status  |                    |
      |<----------------|  (submitted)      |                    |
      |                 |                   | process_task()     |
      |                 |                   |------------------->|
      |                 |                   |                    |
      |                 | SSE: task_status  | TaskStatusEvent    |
      |<----------------|  (working)        |<-------------------|
      |                 |                   |                    |
      |                 | SSE: message      | TaskMessageEvent   |
      |<----------------|  (partial: true)  |<-------------------|
      |                 |                   |                    |
      |                 | SSE: message      | TaskMessageEvent   |
      |<----------------|  (partial: true)  |<-------------------|
      |                 |                   |                    |
      |                 | SSE: artifact     | TaskArtifactEvent  |
      |<----------------|                   |<-------------------|
      |                 |                   |                    |
      |                 | SSE: done         | TaskDoneEvent      |
      |<----------------|                   |<-------------------|
      |                 |                   |                    |
```

### Event Type to SSE Mapping

| TaskEvent Type | SSE Event Name | Payload |
|----------------|----------------|---------|
| TaskStatusEvent | `task_status` | `{task_id, state, message?}` |
| TaskMessageEvent | `message` | `{task_id, role, parts, is_partial}` |
| TaskArtifactEvent | `artifact` | `{task_id, artifact: {id, name, parts}}` |
| TaskDoneEvent | `done` | `{task_id, state}` |
| TaskErrorEvent | `error` | `{task_id, code, message, details?}` |

### Example SSE Stream

```
event: task_status
data: {"task_id": "abc-123", "state": "submitted", "timestamp": "..."}

event: task_status
data: {"task_id": "abc-123", "state": "working", "timestamp": "..."}

event: message
data: {"task_id": "abc-123", "role": "agent", "parts": [{"type": "text", "text": "Processing your request..."}], "is_partial": true, "timestamp": "..."}

event: message
data: {"task_id": "abc-123", "role": "agent", "parts": [{"type": "text", "text": "Here is the analysis you requested."}], "is_partial": false, "timestamp": "..."}

event: artifact
data: {"task_id": "abc-123", "artifact": {"id": "xyz-789", "name": "Report", "parts": [{"type": "file", "name": "report.pdf", "mimeType": "application/pdf", "uri": "/artifacts/xyz-789"}]}, "timestamp": "..."}

event: done
data: {"task_id": "abc-123", "state": "completed", "timestamp": "..."}
```

---

## Security Architecture

### Authentication Flow

```
+--------+    +----------+    +-----------+    +---------+
| Client |    |   API    |    |   Auth    |    |  Agent  |
+--------+    +----------+    +-----------+    +---------+
     |             |               |               |
     | Request     |               |               |
     | + API Key   |               |               |
     |------------>|               |               |
     |             | validate()    |               |
     |             |-------------->|               |
     |             |               | lookup key    |
     |             |               |-------------->|
     |             |<--------------|               |
     |             | user context  |               |
     |             |               |               |
     |             | check_access()|               |
     |             |-------------->|               |
     |             |<--------------|               |
     |             | authorized    |               |
     |             |               |               |
     |             | process       |               |
     |             |------------------------------>|
     |<-------------------------------------------|
     | Response    |               |               |
```

### RBAC Model

```python
"""Role-based access control for agents."""

from enum import Enum


class Permission(str, Enum):
    """Agent-related permissions."""
    AGENT_CREATE = "agent:create"
    AGENT_READ = "agent:read"
    AGENT_UPDATE = "agent:update"
    AGENT_DELETE = "agent:delete"
    TASK_CREATE = "task:create"
    TASK_READ = "task:read"
    TASK_CANCEL = "task:cancel"
    SKILL_INVOKE = "skill:invoke"


class Role(str, Enum):
    """Built-in roles."""
    VIEWER = "viewer"
    OPERATOR = "operator"
    DEVELOPER = "developer"
    ADMIN = "admin"


# Role to permission mapping
ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.VIEWER: {
        Permission.AGENT_READ,
        Permission.TASK_READ,
    },
    Role.OPERATOR: {
        Permission.AGENT_READ,
        Permission.TASK_CREATE,
        Permission.TASK_READ,
        Permission.TASK_CANCEL,
        Permission.SKILL_INVOKE,
    },
    Role.DEVELOPER: {
        Permission.AGENT_CREATE,
        Permission.AGENT_READ,
        Permission.AGENT_UPDATE,
        Permission.TASK_CREATE,
        Permission.TASK_READ,
        Permission.TASK_CANCEL,
        Permission.SKILL_INVOKE,
    },
    Role.ADMIN: set(Permission),  # All permissions
}
```

### Multi-Tenancy Isolation

```python
"""Tenant context middleware."""

from contextvars import ContextVar
from typing import Optional

from fastapi import Request

# Context variable for current tenant
current_tenant: ContextVar[Optional[str]] = ContextVar("current_tenant", default=None)


async def tenant_middleware(request: Request, call_next):
    """Extract and set tenant context from request headers."""
    tenant_id = request.headers.get("X-Tenant-ID")
    token = current_tenant.set(tenant_id)
    try:
        response = await call_next(request)
        return response
    finally:
        current_tenant.reset(token)


def get_tenant_id() -> Optional[str]:
    """Get current tenant ID from context."""
    return current_tenant.get()
```

---

## Performance and Scalability

### Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| Task acknowledgment latency | < 100ms | Time from request to first SSE event |
| Task processing overhead | < 50ms | Framework overhead per task |
| Streaming throughput | > 1000 events/sec | Events per second per agent |
| Concurrent tasks | > 100 per agent | Simultaneous tasks in progress |

### Scalability Strategies

1. **Horizontal Scaling**: Agents are stateless; scale by adding instances
2. **Connection Pooling**: SQLAlchemy connection pool for database access
3. **Async Everything**: All I/O operations use async/await
4. **Backpressure Handling**: Stream buffering with configurable limits

### Caching Strategy

```
+----------+     +----------+     +----------+
|  Client  |     |   Cache  |     | Database |
+----------+     +----------+     +----------+
     |               |                  |
     | GET /agent-card                  |
     |-------------->|                  |
     |               | cache hit?       |
     |<--------------|                  |
     |               |                  |
     |               | cache miss       |
     |               |----------------->|
     |               |<-----------------|
     |               | store (TTL: 5m)  |
     |<--------------|                  |
```

---

## Monitoring and Operations

### Observability Stack

| Component | Tool | Purpose |
|-----------|------|---------|
| Logging | Python logging | Structured logs with context |
| Metrics | (Future) Prometheus | Request counts, latencies |
| Tracing | (Future) OpenTelemetry | Distributed tracing |

### Key Metrics to Track

- `agent_task_created_total` - Counter of tasks created
- `agent_task_completed_total` - Counter of completed tasks
- `agent_task_failed_total` - Counter of failed tasks
- `agent_task_duration_seconds` - Histogram of task processing time
- `agent_streaming_events_total` - Counter of SSE events sent
- `agent_streaming_connections_active` - Gauge of active SSE connections

### Logging Format

```python
import logging
import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
)

# Usage
logger = structlog.get_logger()
logger.info("task_created", task_id=str(task.id), agent_id=str(agent.id))
```

---

## Development Workflow

### Repository Structure

```
omniforge/
|-- src/omniforge/
|   |-- agents/          # Phase 1
|   |-- tasks/           # Phase 1
|   |-- storage/         # Phase 2
|   |-- orchestration/   # Phase 3
|   |-- security/        # Phase 4
|   |-- chat/            # Existing
|   |-- api/             # Existing + Extensions
|
|-- tests/
|   |-- agents/          # Agent tests
|   |-- tasks/           # Task tests
|   |-- integration/     # Integration tests
|   |-- conftest.py      # Shared fixtures
|
|-- specs/               # Documentation
```

### Testing Strategy

**Unit Tests** (80% coverage target):
- Model validation
- Event formatting
- State transitions
- Error handling

**Integration Tests**:
- API endpoint flows
- SSE streaming
- Database operations

**Example Test Structure**:

```python
# tests/agents/test_base.py

import pytest
from uuid import uuid4

from omniforge.agents.base import BaseAgent
from omniforge.agents.models import AgentIdentity, AgentSkill
from omniforge.agents.events import TaskMessageEvent, TaskDoneEvent
from omniforge.tasks.models import Task


class TestAgent(BaseAgent):
    """Concrete test implementation of BaseAgent."""

    identity = AgentIdentity(name="Test Agent", description="For testing")
    skills = [AgentSkill(id="test", name="Test", description="Test skill")]

    async def process_task(self, task: Task):
        yield TaskMessageEvent(
            task_id=task.id,
            parts=[{"type": "text", "text": "Hello"}]
        )
        yield TaskDoneEvent(task_id=task.id)


class TestBaseAgent:
    """Tests for BaseAgent abstract class."""

    def test_agent_has_unique_id(self) -> None:
        """Each agent instance should have a unique ID."""
        agent1 = TestAgent()
        agent2 = TestAgent()
        assert agent1.id != agent2.id

    def test_agent_can_use_explicit_id(self) -> None:
        """Agent should accept explicit ID in constructor."""
        explicit_id = uuid4()
        agent = TestAgent(agent_id=explicit_id)
        assert agent.id == explicit_id

    def test_get_agent_card_returns_valid_card(self) -> None:
        """Agent card should contain identity and skills."""
        agent = TestAgent()
        card = agent.get_agent_card()

        assert card.name == "Test Agent"
        assert len(card.skills) == 1
        assert card.skills[0].id == "test"

    @pytest.mark.asyncio
    async def test_process_task_yields_events(self) -> None:
        """process_task should yield message and done events."""
        agent = TestAgent()
        task = Task(agent_id=agent.id)

        events = []
        async for event in agent.process_task(task):
            events.append(event)

        assert len(events) == 2
        assert isinstance(events[0], TaskMessageEvent)
        assert isinstance(events[1], TaskDoneEvent)
```

---

## Risk Assessment

### Technical Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| A2A protocol changes | Medium | Medium | Pin to version 0.3; abstract protocol layer |
| SSE connection timeouts | High | Medium | Implement heartbeat events; reconnection logic |
| Database bottleneck | High | Low | Connection pooling; async queries; caching |
| Complex state management | Medium | Medium | State machine pattern; comprehensive tests |
| Streaming backpressure | Medium | Low | Buffer limits; slow client detection |

### Dependency Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| SQLAlchemy major update | Low | Pin to ^2.0.0; integration tests |
| FastAPI breaking changes | Medium | Pin to ^0.100.0; use stable APIs only |
| Pydantic v2 issues | Low | Already on v2; extensive model tests |

---

## Implementation Phases

### Phase 1: Core Agent Interface (Week 1-2)

**Goal**: Functional BaseAgent with streaming, compatible with existing chat infrastructure.

**Deliverables**:
1. `agents/base.py` - BaseAgent abstract class
2. `agents/models.py` - A2A protocol models
3. `agents/events.py` - Task event types
4. `agents/streaming.py` - Streaming bridge (reusing chat/streaming.py)
5. `agents/errors.py` - Exception hierarchy
6. `tasks/models.py` - Task state models
7. Unit tests for all components

**Success Criteria**:
- [x] BaseAgent can be subclassed with minimal code
- [x] Task events flow through SSE using existing formatters
- [x] 80%+ test coverage

### Phase 2: Task Persistence and Registry (Week 3-4)

**Goal**: Durable task storage and agent discovery.

**Deliverables**:
1. `storage/base.py` - Repository interface
2. `storage/memory.py` - In-memory implementation
3. `storage/database.py` - SQLAlchemy implementation
4. `storage/models.py` - ORM models
5. `tasks/manager.py` - TaskManager service
6. `agents/registry.py` - Agent registry
7. `api/routes/agents.py` - Agent discovery endpoints
8. `api/routes/tasks.py` - Task management endpoints

**Success Criteria**:
- [x] Tasks survive agent restart (with database backend)
- [x] Agents discoverable via Agent Card endpoint
- [x] API endpoints pass integration tests

### Phase 3: Agent-to-Agent Communication (Week 5-6)

**Goal**: Enable agents to delegate tasks to other agents.

**Deliverables**:
1. `orchestration/discovery.py` - Agent discovery service
2. `orchestration/client.py` - A2A client for outbound calls
3. `orchestration/router.py` - Message routing
4. Integration with TaskManager for parent/child relationships

**Success Criteria**:
- [x] Agent A can discover Agent B
- [x] Agent A can delegate subtask to Agent B
- [x] Parent task tracks child task progress

### Phase 4: Enterprise Features (Week 7-9)

**Goal**: Production-ready multi-tenancy and RBAC.

**Deliverables**:
1. `security/auth.py` - Authentication handlers (API key, Bearer)
2. `security/rbac.py` - Permission checking
3. `security/tenant.py` - Tenant isolation middleware
4. `api/middleware/tenant.py` - Tenant context middleware
5. Database migrations for tenant_id columns
6. Audit logging

**Success Criteria**:
- [x] Tenant A cannot access Tenant B resources
- [x] RBAC enforced on all endpoints
- [x] Audit trail for security-relevant operations

---

## Alternative Approaches

### Alternative 1: Event Sourcing for Tasks

**Description**: Store all task events as an append-only log instead of mutable task records.

**Pros**:
- Complete audit trail
- Easy replay/debugging
- Natural fit for streaming architecture

**Cons**:
- Higher storage requirements
- More complex querying
- Eventual consistency challenges

**Recommendation**: Consider for Phase 5 if audit requirements demand it.

### Alternative 2: Separate Streaming Service

**Description**: Extract SSE handling into a dedicated microservice.

**Pros**:
- Independent scaling of streaming tier
- Cleaner separation of concerns

**Cons**:
- Added operational complexity
- Latency from service-to-service calls
- Premature for current scale

**Recommendation**: Keep integrated for MVP; revisit at scale.

### Alternative 3: WebSocket Instead of SSE

**Description**: Use WebSocket for bidirectional communication instead of SSE.

**Pros**:
- Bidirectional communication
- Lower latency for client messages
- Better for high-frequency updates

**Cons**:
- More complex connection management
- Not compatible with existing chat SSE infrastructure
- Overkill for server-push-only use case

**Recommendation**: Keep SSE for A2A compliance and infrastructure reuse.

---

## Appendix A: Extended Streaming.py

The following functions should be added to `src/omniforge/chat/streaming.py` to support agent events while maintaining backward compatibility:

```python
# Additional exports for agent events
# These reuse format_sse_event for consistent formatting

from omniforge.agents.events import (
    TaskEvent,
    TaskStatusEvent,
    TaskMessageEvent,
    TaskArtifactEvent,
    TaskDoneEvent,
    TaskErrorEvent,
)

__all__ = [
    # Existing exports
    "format_sse_event",
    "format_chunk_event",
    "format_done_event",
    "format_error_event",
    "stream_with_error_handling",
    # New agent event exports
    "format_task_event",
]


def format_task_event(event: TaskEvent) -> str:
    """Format any TaskEvent as an SSE event string.

    This is a convenience function that dispatches to the appropriate
    formatter based on event type.

    Args:
        event: The TaskEvent to format.

    Returns:
        SSE-formatted string.
    """
    return format_sse_event(event.type, event.model_dump(mode="json"))
```

---

## Appendix B: Skill Decorator Pattern

For developer ergonomics, skills can be defined using decorators:

```python
from omniforge.agents import BaseAgent, skill


class MyAgent(BaseAgent):
    identity = AgentIdentity(name="My Agent", description="...")

    @skill(
        id="analyze",
        name="Analyze Data",
        description="Analyzes structured data",
        tags=["analysis", "data"],
        examples=["Analyze this CSV data"]
    )
    async def analyze_data(self, task: Task) -> AsyncIterator[TaskEvent]:
        """Skill implementation."""
        yield TaskMessageEvent(...)
        yield TaskDoneEvent()
```

---

## References

- [A2A Protocol Specification v0.3](https://a2a-protocol.org/latest/specification/)
- [Product Specification](/Users/sohitkumar/code/omniforge/specs/base-agent-interface-spec.md)
- [Existing Chat Streaming](/Users/sohitkumar/code/omniforge/src/omniforge/chat/streaming.py)
- [Existing Chat Models](/Users/sohitkumar/code/omniforge/src/omniforge/chat/models.py)
- [Coding Guidelines](/Users/sohitkumar/code/omniforge/coding-guidelines.md)
