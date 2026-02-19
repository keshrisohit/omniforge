# Technical Implementation Plan: Orchestrator and Handoff Patterns

**Created**: 2026-02-05
**Last Updated**: 2026-02-06
**Version**: 2.0 (HTTP-Only Simplified)
**Status**: Ready for Implementation
**Related Spec**: [orchestrator-handoff-patterns-spec.md](orchestrator-handoff-patterns-spec.md)

---

## Executive Summary

This technical plan details the implementation of two multi-agent interaction patterns for OmniForge: the **Orchestrator Pattern** (for Q&A and coordinated sub-agent queries) and the **Handoff Pattern** (for skill creation and deep specialized workflows). The implementation uses the existing HTTP/SSE infrastructure, extends the conversation persistence layer, and provides real-time streaming for both patterns.

**Key Architecture Decisions:**
1. **Thread-based conversation anchoring** - All agent interactions share a caller-provided `thread_id` for context continuity
2. **Dual streaming modes** - Orchestrator buffers/synthesizes; handoff passes through directly
3. **Extend existing ORM** - Leverage `ConversationModel.state_metadata` for orchestration state
4. **HTTP/SSE only** - Use existing `A2AClient` for all inter-agent communication
5. **No backward compatibility** - Clean implementation without legacy constraints

**Technology Stack:**
- Python 3.9+ with asyncio
- FastAPI for API endpoints
- HTTP/SSE (existing `A2AClient`) for all agent communication
- SQLAlchemy async (existing)
- Pydantic v2 for data models
- Python stdlib logging (no external observability dependencies)

**What Changed from v1.0:**
- ❌ Removed all gRPC implementation
- ❌ Removed Protocol Buffer definitions
- ❌ Removed backward compatibility constraints
- ✅ Simplified to use existing HTTP/SSE infrastructure
- ✅ Cleaner component boundaries
- ✅ Faster implementation path

---

## Requirements Analysis

### Functional Requirements (from Spec)

| ID | Requirement | Pattern |
|----|-------------|---------|
| FR-1 | Main Agent coordinates sub-agent queries | Orchestrator |
| FR-2 | Sub-agent responses synthesized before delivery | Orchestrator |
| FR-3 | Control transfers to specialized agent | Handoff |
| FR-4 | Direct streaming from specialized agent to user | Handoff |
| FR-5 | thread_id preserved across all agent interactions | Both |
| FR-6 | Conversation history accessible to any participating agent | Both |
| FR-7 | Graceful return from handoff to main agent | Handoff |
| FR-8 | State persistence for interrupted handoffs | Handoff |

### Non-Functional Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-1 | First token latency (orchestrator) | < 3 seconds P95 |
| NFR-2 | Handoff transition time | < 1 second |
| NFR-3 | Context preservation | 100% |
| NFR-4 | Streaming reliability | 99.5% |
| NFR-5 | Cross-tenant isolation | 0 violations |
| NFR-6 | A2A protocol compliance | HTTP/SSE v0.3 |

---

## Constraints and Assumptions

### Hard Constraints

1. **Use Existing Infrastructure** - Must use existing `A2AClient` (HTTP/SSE) from `src/omniforge/orchestration/client.py`
2. **Multi-tenancy** - All operations must validate `tenant_id` at repository layer
3. **Thread Immutability** - `thread_id` is caller-provided and immutable throughout conversation

### Assumptions

1. **No Nested Handoffs** - Agent A cannot hand off to B who hands off to C (out of scope)
2. **Single Active Handoff** - User can only be in one handoff session per thread
3. **Local Agent Registry** - All agents are registered locally (no external marketplace yet)
4. **HTTP/SSE Sufficient** - Acceptable latency for initial implementation

### Design Decisions

| Question | Decision | Rationale |
|----------|----------|-----------|
| Inter-agent protocol | **HTTP/SSE** | Existing infrastructure, simpler, sufficient performance |
| Handoff state storage | **state_metadata JSON column** | No new tables, flexible schema |
| State retention | **30 days** | Configurable via settings |
| Response synthesis | **Text concatenation** | Simple Phase 1, LLM synthesis in Phase 2 |

---

## System Architecture

### High-Level Architecture

```
+------------------------------------------------------------------+
|                        CLIENT LAYER                               |
|  [Web UI]  [SDK]  [API Gateway]                                  |
|     |        |         |                                         |
|     +--------+---------+                                         |
|              |                                                   |
|     [WebSocket/SSE Connection Manager]                           |
+------------------------------------------------------------------+
              |
              v
+------------------------------------------------------------------+
|                     API LAYER (FastAPI)                          |
|  /api/v1/threads/{thread_id}/messages                           |
|  /api/v1/threads/{thread_id}/handoff                            |
+------------------------------------------------------------------+
              |
              v
+------------------------------------------------------------------+
|                  ORCHESTRATION LAYER                             |
|                                                                  |
|  +------------------+    +-----------------+                     |
|  | OrchestrationMgr |    | HandoffManager  |                     |
|  +------------------+    +-----------------+                     |
|         |                       |                                |
|         v                       v                                |
|  +------------------------------------------+                    |
|  |            StreamRouter                  |                    |
|  |  (Routes based on handoff state)         |                    |
|  +------------------------------------------+                    |
|              |                                                   |
|              v                                                   |
|  +------------------------------------------+                    |
|  |         Existing A2AClient               |                    |
|  |         (HTTP/SSE)                       |                    |
|  +------------------------------------------+                    |
+------------------------------------------------------------------+
              |
              v
+------------------------------------------------------------------+
|                    AGENT LAYER                                   |
|                                                                  |
|  +-------------+  +---------------+  +------------------+        |
|  | Main Agent  |  | Knowledge Bot |  | Skill Creation   |        |
|  | (Chatbot)   |  | Sub-Agent     |  | Agent (Handoff)  |        |
|  +-------------+  +---------------+  +------------------+        |
|                                                                  |
+------------------------------------------------------------------+
              |
              v
+------------------------------------------------------------------+
|                   PERSISTENCE LAYER                              |
|                                                                  |
|  +-------------------+  +-------------------+                    |
|  | ConversationRepo  |  | AgentRegistry     |                    |
|  | (SQLite/Postgres) |  | (Agent Cards)     |                    |
|  +-------------------+  +-------------------+                    |
|                                                                  |
+------------------------------------------------------------------+
```

### Data Flow: Orchestrator Pattern

```
User Message (thread_id: abc-123)
         |
         v
    Main Agent
         |
         +---> Analyze intent
         |
         +---> Decide sub-agents needed: [knowledge-agent, research-agent]
         |
         +---> Create A2A tasks (parallel)
         |          |
         |    +-----+-----+
         |    |           |
         v    v           v
    Knowledge Agent    Research Agent
         |                 |
         | (HTTP/SSE)      | (HTTP/SSE)
         |                 |
         v                 v
    [Aggregation Buffer in Main Agent]
         |
         +---> Synthesize response (text concatenation)
         |
         +---> Store in conversation history
         |
         v
    User (SSE/WebSocket stream)
```

### Data Flow: Handoff Pattern

```
User Message: "Create a skill for Slack alerts"
         |
         v
    Main Agent
         |
         +---> Detect handoff trigger ("create skill")
         |
         +---> Send HandoffRequest to Skill Creation Agent
         |
         +---> Store handoff metadata in conversation
         |
         v
    [Connection Routed to Skill Creation Agent]
         |
         v
    Skill Creation Agent <---> User (direct HTTP/SSE stream)
         |
         +---> FSM state progression
         |
         +---> Store messages in shared conversation (thread_id)
         |
         v
    [On completion or exit]
         |
         +---> Send HandoffReturn to Main Agent
         |
         v
    Main Agent resumes
```

---

## Technology Stack

### Core Technologies

| Component | Technology | Version | Rationale |
|-----------|------------|---------|-----------|
| Language | Python | 3.9+ | Existing codebase requirement |
| Web Framework | FastAPI | 0.104+ | Async-native, streaming support |
| ORM | SQLAlchemy | 2.0+ | Async support, existing in codebase |
| Database | SQLite/PostgreSQL | - | Configurable (existing pattern) |
| HTTP Client | httpx | 0.24+ | Already in use by existing A2AClient |
| Validation | Pydantic | 2.5+ | Existing pattern, fast validation |
| Streaming | SSE/WebSocket | - | Client-facing and inter-agent streaming |

### No New External Dependencies

The implementation uses only existing dependencies already in the project. No new packages required.

---

## Component Specifications

### 1. A2A Protocol Models

**Location**: `src/omniforge/orchestration/a2a_models.py`

```python
"""A2A protocol models for orchestration and handoff."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


class HandoffRequest(BaseModel):
    """Request to hand off conversation control to another agent."""

    thread_id: str = Field(..., min_length=1, max_length=255)
    tenant_id: str = Field(..., min_length=1, max_length=255)
    user_id: str = Field(..., min_length=1, max_length=255)
    source_agent_id: str = Field(..., min_length=1, max_length=255)
    target_agent_id: str = Field(..., min_length=1, max_length=255)
    context_summary: str = Field(..., min_length=1, max_length=2000)
    recent_message_count: int = Field(default=5, ge=1, le=20)
    handoff_reason: str = Field(..., min_length=1, max_length=500)
    preserve_state: bool = True
    return_expected: bool = True
    handoff_metadata: Optional[dict] = None


class HandoffAccept(BaseModel):
    """Acknowledgment of handoff acceptance."""

    thread_id: str
    source_agent_id: str
    target_agent_id: str
    accepted: bool
    rejection_reason: Optional[str] = None
    estimated_duration_seconds: Optional[int] = None


class HandoffReturn(BaseModel):
    """Signal to return control from specialized agent."""

    thread_id: str
    tenant_id: str
    source_agent_id: str  # The agent returning control
    target_agent_id: str  # The agent receiving control (usually main)
    completion_status: str  # completed, cancelled, error
    result_summary: Optional[str] = None
    artifacts_created: list[str] = Field(default_factory=list)


class OrchestrationError(Exception):
    """Base exception for orchestration errors."""
    pass


class HandoffError(OrchestrationError):
    """Error during handoff operations."""
    pass


class DelegationError(OrchestrationError):
    """Error during task delegation."""
    pass
```

### 2. Orchestration Manager

**Location**: `src/omniforge/orchestration/manager.py`

```python
"""Orchestration manager for coordinating multi-agent interactions."""

from typing import AsyncIterator, Optional
from dataclasses import dataclass
from enum import Enum

from omniforge.orchestration.client import A2AClient  # Existing
from omniforge.orchestration.a2a_models import DelegationError
from omniforge.agents.events import TaskEvent
from omniforge.agents.models import AgentCard, TextPart
from omniforge.tasks.models import TaskCreateRequest


class DelegationStrategy(str, Enum):
    """Strategy for delegating to sub-agents."""
    PARALLEL = "parallel"      # Query all sub-agents simultaneously
    SEQUENTIAL = "sequential"  # Query one at a time
    FIRST_SUCCESS = "first_success"  # Return first successful response


@dataclass
class SubAgentResult:
    """Result from a sub-agent delegation."""
    agent_id: str
    success: bool
    response: Optional[str] = None
    error: Optional[str] = None
    latency_ms: int = 0


class OrchestrationManager:
    """Manages orchestrator pattern for multi-agent coordination.

    Coordinates sub-agent queries via existing A2AClient (HTTP/SSE),
    aggregates responses, and synthesizes final output.
    """

    def __init__(
        self,
        a2a_client: A2AClient,
        conversation_repo,
    ) -> None:
        self._client = a2a_client
        self._conversation_repo = conversation_repo

    async def delegate_to_agents(
        self,
        thread_id: str,
        tenant_id: str,
        user_id: str,
        message: str,
        target_agent_cards: list[AgentCard],
        strategy: DelegationStrategy = DelegationStrategy.PARALLEL,
        timeout_ms: int = 30000,
    ) -> list[SubAgentResult]:
        """Delegate task to one or more sub-agents.

        Returns:
            List of SubAgentResult from each agent
        """
        if strategy == DelegationStrategy.PARALLEL:
            return await self._delegate_parallel(
                thread_id, tenant_id, user_id, message,
                target_agent_cards, timeout_ms
            )
        elif strategy == DelegationStrategy.SEQUENTIAL:
            return await self._delegate_sequential(
                thread_id, tenant_id, user_id, message,
                target_agent_cards, timeout_ms
            )
        else:  # FIRST_SUCCESS
            return await self._delegate_first_success(
                thread_id, tenant_id, user_id, message,
                target_agent_cards, timeout_ms
            )

    async def _delegate_parallel(
        self,
        thread_id: str,
        tenant_id: str,
        user_id: str,
        message: str,
        agent_cards: list[AgentCard],
        timeout_ms: int,
    ) -> list[SubAgentResult]:
        """Execute parallel delegation to multiple agents."""
        import asyncio
        from time import time

        async def delegate_one(agent_card: AgentCard) -> SubAgentResult:
            start_time = time()
            try:
                request = TaskCreateRequest(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    message_parts=[TextPart(text=message)],
                    parent_task_id=None,
                )

                response_chunks = []
                async for event in self._client.send_task(agent_card, request):
                    if event.type == "message":
                        for part in event.message_parts:
                            if part.type == "text":
                                response_chunks.append(part.text)
                    elif event.type == "done":
                        break

                latency_ms = int((time() - start_time) * 1000)
                return SubAgentResult(
                    agent_id=agent_card.identity.id,
                    success=True,
                    response="".join(response_chunks),
                    latency_ms=latency_ms,
                )
            except Exception as e:
                latency_ms = int((time() - start_time) * 1000)
                return SubAgentResult(
                    agent_id=agent_card.identity.id,
                    success=False,
                    error=str(e),
                    latency_ms=latency_ms,
                )

        # Execute all delegations in parallel
        tasks = [delegate_one(card) for card in agent_cards]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return [r for r in results if isinstance(r, SubAgentResult)]

    def synthesize_responses(
        self,
        sub_results: list[SubAgentResult],
    ) -> str:
        """Synthesize sub-agent responses into coherent output.

        Phase 1: Simple text concatenation with attribution.
        Phase 2: Can add LLM-based synthesis.
        """
        if not sub_results:
            return "No responses received from sub-agents."

        successful_results = [r for r in sub_results if r.success and r.response]

        if not successful_results:
            return "All sub-agents failed to provide responses."

        if len(successful_results) == 1:
            # Single result, return directly
            return successful_results[0].response

        # Multiple results, concatenate with attribution
        synthesis_parts = []
        for result in successful_results:
            synthesis_parts.append(
                f"From {result.agent_id}:\n{result.response}"
            )

        return "\n\n".join(synthesis_parts)
```

### 3. Handoff Manager

**Location**: `src/omniforge/orchestration/handoff.py`

```python
"""Handoff manager for control transfer between agents."""

from typing import AsyncIterator, Optional
from enum import Enum
from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from omniforge.orchestration.client import A2AClient  # Existing
from omniforge.orchestration.a2a_models import (
    HandoffRequest, HandoffAccept, HandoffReturn, HandoffError
)
from omniforge.conversation.sqlite_repository import SQLiteConversationRepository


class HandoffState(str, Enum):
    """State of a handoff session."""
    PENDING = "pending"
    ACTIVE = "active"
    RETURNING = "returning"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ERROR = "error"


class HandoffSession(BaseModel):
    """Tracks an active handoff session."""

    handoff_id: str
    thread_id: str
    tenant_id: str
    user_id: str
    source_agent_id: str
    target_agent_id: str
    state: HandoffState = HandoffState.PENDING
    context_summary: str
    handoff_reason: str
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    result_summary: Optional[str] = None
    artifacts_created: list[str] = Field(default_factory=list)
    workflow_state: Optional[str] = None
    workflow_metadata: dict = Field(default_factory=dict)


class HandoffManager:
    """Manages handoff pattern for control transfer between agents."""

    def __init__(
        self,
        a2a_client: A2AClient,
        conversation_repo: SQLiteConversationRepository,
    ) -> None:
        self._client = a2a_client
        self._conversation_repo = conversation_repo
        self._active_handoffs: dict[str, HandoffSession] = {}  # thread_id -> session

    async def initiate_handoff(
        self,
        thread_id: str,
        tenant_id: str,
        user_id: str,
        source_agent_id: str,
        target_agent_card: "AgentCard",
        context_summary: str,
        handoff_reason: str,
    ) -> HandoffAccept:
        """Initiate a handoff to a specialized agent."""
        # 1. Validate no existing active handoff
        existing = await self.get_active_handoff(thread_id, tenant_id)
        if existing:
            raise HandoffError(f"Active handoff already exists for thread {thread_id}")

        # 2. Create handoff session
        handoff_id = str(uuid4())
        session = HandoffSession(
            handoff_id=handoff_id,
            thread_id=thread_id,
            tenant_id=tenant_id,
            user_id=user_id,
            source_agent_id=source_agent_id,
            target_agent_id=target_agent_card.identity.id,
            context_summary=context_summary,
            handoff_reason=handoff_reason,
        )

        # 3. Send handoff request via HTTP (existing A2AClient could be extended)
        # For now, assume acceptance (Phase 1 simplification)
        acceptance = HandoffAccept(
            thread_id=thread_id,
            source_agent_id=source_agent_id,
            target_agent_id=target_agent_card.identity.id,
            accepted=True,
        )

        # 4. Update session state and persist
        session.state = HandoffState.ACTIVE
        await self._persist_handoff_session(session)
        self._active_handoffs[thread_id] = session

        return acceptance

    async def get_active_handoff(
        self,
        thread_id: str,
        tenant_id: str,
    ) -> Optional[HandoffSession]:
        """Get active handoff session for a thread."""
        # Check cache first
        if thread_id in self._active_handoffs:
            return self._active_handoffs[thread_id]

        # Load from database
        conversation = await self._conversation_repo.get_conversation(
            UUID(thread_id), tenant_id
        )
        if conversation and conversation.state_metadata:
            handoff_data = conversation.state_metadata.get("handoff_session")
            if handoff_data:
                session = HandoffSession(**handoff_data)
                if session.state == HandoffState.ACTIVE:
                    self._active_handoffs[thread_id] = session
                    return session

        return None

    async def _persist_handoff_session(self, session: HandoffSession) -> None:
        """Persist handoff session to conversation state_metadata."""
        conversation = await self._conversation_repo.get_conversation(
            UUID(session.thread_id), session.tenant_id
        )
        if not conversation:
            raise HandoffError(f"Conversation not found: {session.thread_id}")

        # Update state_metadata with handoff session
        if not conversation.state_metadata:
            conversation.state_metadata = {}
        conversation.state_metadata["handoff_session"] = session.model_dump()

        await self._conversation_repo.update_state(
            UUID(session.thread_id),
            session.tenant_id,
            state_metadata=conversation.state_metadata,
        )
```

### 4. Thread Manager

**Location**: `src/omniforge/orchestration/thread.py`

```python
"""Thread lifecycle and context management."""

from typing import Optional
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, Field

from omniforge.conversation.models import Message, MessageRole
from omniforge.conversation.sqlite_repository import SQLiteConversationRepository


class ThreadContext(BaseModel):
    """Context information for a conversation thread."""

    thread_id: str
    tenant_id: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    current_active_agent: str
    is_handoff_active: bool = False
    handoff_target_agent: Optional[str] = None
    total_messages: int = 0


class ThreadManager:
    """Manages thread lifecycle and context."""

    def __init__(
        self,
        conversation_repo: SQLiteConversationRepository,
    ) -> None:
        self._conversation_repo = conversation_repo

    async def validate_thread(
        self,
        thread_id: str,
        tenant_id: str,
        user_id: Optional[str] = None,
    ) -> bool:
        """Validate thread_id belongs to tenant.

        Security critical: Prevents cross-tenant thread access.
        """
        try:
            conversation = await self._conversation_repo.get_conversation(
                UUID(thread_id), tenant_id
            )
            if conversation is None:
                return False
            if user_id and conversation.user_id != user_id:
                return False
            return True
        except Exception:
            return False

    async def get_recent_messages(
        self,
        thread_id: str,
        tenant_id: str,
        count: int = 10,
        include_system: bool = False,
    ) -> list[Message]:
        """Get recent messages from thread for context."""
        # Leverage existing conversation repository
        messages = await self._conversation_repo.get_messages(
            UUID(thread_id), tenant_id
        )

        if not include_system:
            messages = [m for m in messages if m.role != MessageRole.SYSTEM]

        return messages[-count:] if messages else []
```

### 5. Stream Router

**Location**: `src/omniforge/orchestration/stream_router.py`

```python
"""Routes streaming requests based on handoff state."""

from typing import AsyncIterator

from omniforge.orchestration.handoff import HandoffManager, HandoffState
from omniforge.orchestration.manager import OrchestrationManager


class StreamRouter:
    """Routes streams based on conversation state."""

    def __init__(
        self,
        handoff_manager: HandoffManager,
        orchestration_manager: OrchestrationManager,
    ):
        self._handoff_manager = handoff_manager
        self._orchestration_manager = orchestration_manager

    async def route_message(
        self,
        thread_id: str,
        tenant_id: str,
        user_id: str,
        message: str,
    ) -> AsyncIterator[str]:
        """Route message to appropriate handler based on thread state.

        Checks for active handoff first. If found, routes directly to
        specialized agent. Otherwise, uses orchestration flow.
        """
        # Check for active handoff
        handoff = await self._handoff_manager.get_active_handoff(
            thread_id, tenant_id
        )

        if handoff and handoff.state == HandoffState.ACTIVE:
            # Direct routing to specialized agent (Phase 1: simplified)
            # In full implementation, this would forward via A2AClient
            yield f"[HANDOFF MODE: {handoff.target_agent_id}] {message}"
        else:
            # Normal orchestration flow
            # Simplified: just yield message (full implementation does delegation)
            yield message
```

### 6. Agent Card Extensions

**Location**: `src/omniforge/agents/models.py` (extend existing)

```python
# Add to existing models.py

class HandoffCapability(BaseModel):
    """Handoff-specific capability configuration."""

    supports_handoff: bool = False
    handoff_triggers: list[str] = Field(default_factory=list)
    workflow_states: list[str] = Field(default_factory=list)
    requires_exclusive_control: bool = True
    max_session_duration_seconds: int = 3600


class OrchestrationCapability(BaseModel):
    """Orchestration-specific capability configuration."""

    can_orchestrate: bool = False
    can_be_orchestrated: bool = True
    supported_delegation_strategies: list[str] = Field(
        default_factory=lambda: ["parallel", "sequential"]
    )
    max_concurrent_delegations: int = 5


# Extend existing AgentCapabilities
class AgentCapabilities(BaseModel):
    # Existing fields...
    streaming: bool = False
    push_notifications: bool = False
    multi_turn: bool = False
    hitl_support: bool = False

    # New orchestration capabilities
    handoff: HandoffCapability = Field(default_factory=HandoffCapability)
    orchestration: OrchestrationCapability = Field(
        default_factory=OrchestrationCapability
    )
```

---

## Streaming Architecture

### Orchestrator Pattern Streaming

```
              Client (WebSocket/SSE)
                      |
                      v
        +-------------+--------------+
        |     OrchestrationManager   |
        +-------------+--------------+
                      |
           +----------+----------+
           |                     |
           v                     v
    +------+------+       +------+------+
    | Sub-Agent A |       | Sub-Agent B |
    | (HTTP/SSE)  |       | (HTTP/SSE)  |
    +------+------+       +------+------+
           |                     |
           |    Existing         |
           |    A2AClient        |
           v                     v
        +-------------+--------------+
        |   Aggregation Buffer       |
        +-------------+--------------+
                      |
                      v
        +-------------+--------------+
        |   Synthesis               |
        |   (Text Concatenation)    |
        +-------------+--------------+
                      |
                      v
              User Response Stream
```

**Simplified Approach:**
- Use existing `A2AClient.send_task()` for delegation
- Collect responses in simple buffer
- Concatenate with attribution (no LLM synthesis Phase 1)

### Handoff Pattern Streaming

```
              Client (WebSocket/SSE)
                      |
                      v
        +-------------+--------------+
        |        StreamRouter         |
        +-------------+--------------+
                      |
         Check: is_handoff_active?
                      |
           +---------YES---------+
           |                     |
           v                     |
    +------+------+              |
    | HandoffMgr  |              |
    +------+------+              |
           |                     |
           v                     |
    +------+------+              |
    | Specialized |              |
    | Agent       |              |
    | (HTTP/SSE)  |              |
    +------+------+              |
           |                     |
           | Direct Stream       |
           v                     v
              User Response Stream
```

---

## Security Architecture

### Tenant Isolation

```python
# All operations include tenant validation

async def validate_operation(thread_id: str, tenant_id: str):
    """Every orchestration operation validates tenant."""
    conversation = await repo.get_conversation(UUID(thread_id), tenant_id)
    if not conversation:
        raise SecurityError("Thread not found for tenant")
```

### RBAC Integration

```python
# Extend existing Permission enum

class Permission(str, Enum):
    # Existing permissions...

    # Orchestration permissions
    ORCHESTRATION_DELEGATE = "orchestration:delegate"
    HANDOFF_INITIATE = "handoff:initiate"
    HANDOFF_CANCEL = "handoff:cancel"


# Check permissions before operations
async def initiate_handoff(...):
    if not await rbac.has_permission(user_id, tenant_id, Permission.HANDOFF_INITIATE):
        raise PermissionError("User cannot initiate handoffs")
```

### Context Sanitization

```python
"""Sanitize context when passing between agents."""

import re

class ContextSanitizer:
    SENSITIVE_PATTERNS = [
        (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL]"),
        (r"\b\d{16}\b", "[CARD]"),
        (r"(?i)(password|secret|token)\s*[:=]\s*\S+", "[REDACTED]"),
    ]

    def sanitize(self, text: str) -> str:
        result = text
        for pattern, replacement in self.SENSITIVE_PATTERNS:
            result = re.sub(pattern, replacement, result)
        return result
```

---

## Observability

### Simple Logging

```python
"""Use Python stdlib logging."""

import logging

logger = logging.getLogger("omniforge.orchestration")

# Delegation log
logger.info(
    "Delegation started",
    extra={
        "thread_id": "abc-123",
        "source_agent": "main-chatbot",
        "target_agent": "knowledge-agent",
        "tenant_id": "tenant-456",
    }
)

# Handoff log
logger.info(
    "Handoff initiated",
    extra={
        "thread_id": "abc-123",
        "target_agent": "skill-creation-agent",
        "handoff_reason": "skill_creation",
    }
)
```

---

## Implementation Phases

### Phase 1: Foundation (Week 1)

**Scope:**
- A2A Protocol models (Pydantic)
- ThreadManager implementation
- Basic OrchestrationManager (sequential delegation only)
- Unit tests

**Deliverables:**
- `src/omniforge/orchestration/a2a_models.py`
- `src/omniforge/orchestration/thread.py`
- `src/omniforge/orchestration/manager.py` (basic)
- Tests

**Dependencies:** None

### Phase 2: Orchestrator Pattern (Week 2)

**Scope:**
- Parallel delegation support
- Aggregation buffer
- Simple response synthesis (concatenation)
- Integration tests

**Deliverables:**
- `src/omniforge/orchestration/manager.py` (complete)
- `src/omniforge/orchestration/buffer.py`
- Integration tests

**Dependencies:** Phase 1

### Phase 3: Handoff Pattern (Week 3)

**Scope:**
- HandoffManager implementation
- StreamRouter implementation
- Handoff state persistence
- Resumption mechanism

**Deliverables:**
- `src/omniforge/orchestration/handoff.py`
- `src/omniforge/orchestration/stream_router.py`
- Integration tests

**Dependencies:** Phase 1, Phase 2

### Phase 4: Security & Testing (Week 4)

**Scope:**
- RBAC integration
- Context sanitization
- End-to-end integration tests
- Documentation

**Deliverables:**
- Security components
- Complete test suite
- Documentation

**Dependencies:** All previous phases

---

## Testing Strategy

**Unit Tests:**
- All Pydantic models
- Buffer aggregation logic
- Context sanitization
- Thread validation

**Integration Tests:**
- Full orchestration flow with mocked A2AClient
- Full handoff flow with mocked specialized agent
- Database persistence with test SQLite
- Error scenarios (timeout, agent unavailable)

**End-to-End Tests:**
- Complete Q&A orchestration scenario
- Complete skill creation handoff scenario
- Concurrent handoff prevention
- Tenant isolation validation

---

## Performance Targets

| Operation | Target | Measurement Point |
|-----------|--------|-------------------|
| First token (orchestrator) | < 3s P95 | User message to first stream chunk |
| First token (handoff) | < 1s P95 | User message to first stream chunk |
| Handoff transition | < 1s | Handoff initiation to first response |
| Sub-agent delegation | < 500ms | Request to first event |

---

## References

- [Orchestrator and Handoff Patterns Spec](orchestrator-handoff-patterns-spec.md)
- [OmniForge Product Vision](product-vision.md)
- [Existing Conversation ORM](../src/omniforge/conversation/orm.py)
- [Existing A2A Client](../src/omniforge/orchestration/client.py)
- [Google A2A Protocol Specification](https://a2a-protocol.org/latest/specification/)
