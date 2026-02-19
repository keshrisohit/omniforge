# Smart Master Agent: Technical Implementation Plan

**Created**: 2026-01-30
**Spec**: [Smart Master Agent Spec](smart-master-agent-spec.md)
**Status**: Draft
**Version**: 1.0

---

## Executive Summary

This plan transforms the master agent from a stateless keyword matcher into a context-aware, LLM-powered orchestrator. The work is organized into three sequential phases:

1. **Conversation Storage** -- Persistent Conversation and Message models backed by SQLite via SQLAlchemy, using an abstract repository so the backend can be swapped later.
2. **Context Passing** -- A context assembler that retrieves recent messages, applies a token budget, and threads history from `ChatService` through `MasterResponseGenerator` into `MasterAgent`.
3. **LLM Intent Analysis** -- A new `LLMIntentAnalyzer` module that calls a fast/cheap LLM via litellm for structured intent classification, with automatic fallback to the existing keyword classifier.

All three phases share a critical constraint: backward compatibility. Every existing public method signature gains optional parameters; no existing caller breaks. Multi-tenancy is enforced at the repository layer. Every new component has a clean interface that can be tested in isolation.

---

## Requirements Analysis

### Functional Requirements

| ID   | Requirement | Source |
|------|-------------|--------|
| FR-1 | Replace keyword intent detection with LLM-powered classification | Spec Capability 1 |
| FR-2 | Return structured intent output (action_type, confidence, entities, reasoning, is_ambiguous, alternative_action, clarifying_question) | Spec Capability 1 |
| FR-3 | Fall back to keyword classifier on LLM failure | Spec Edge Cases |
| FR-4 | Persist all user and assistant messages to a database | Spec Capability 2 |
| FR-5 | Scope conversations by tenant_id and user_id | Spec Capability 2 |
| FR-6 | Retrieve and pass recent conversation history to the master agent | Spec Capability 3 |
| FR-7 | Token-budgeted context window (default 2000 tokens, last 10 exchanges max) | Spec Capability 3 |
| FR-8 | Include conversation history in LLM intent prompt | Spec Capability 3 |
| FR-9 | Support listing conversations per user/tenant | Spec Capability 2 |

### Non-Functional Requirements

| ID    | Requirement | Target |
|-------|-------------|--------|
| NFR-1 | Intent classification latency | < 1 second p95 |
| NFR-2 | Cost per intent request | < $0.005 |
| NFR-3 | Conversation storage reliability | Zero data loss under normal ops |
| NFR-4 | Context window efficiency | Fit within token budget without losing critical context |
| NFR-5 | Backward compatibility | All existing callers work without modification |
| NFR-6 | Testability | Every component testable in isolation with no LLM calls |
| NFR-7 | Python 3.9+ compatibility | No use of Python 3.10+ syntax |

---

## Constraints and Assumptions

### Constraints

1. **Python 3.9+** -- Use `Optional[X]` not `X | None`, use `list[T]` (available since 3.9 via `__future__` or `typing`).
2. **Line length 100** -- Enforced by black.
3. **Type annotations required** -- Enforced by mypy.
4. **SOLID principles** -- Single responsibility per module, clean interfaces.
5. **No circular dependencies** -- Conversation storage must not import from chat or agents.
6. **Existing SQLAlchemy setup** -- Reuse `Base` from `storage/database.py`, `Database` class, and existing ORM patterns from `storage/models.py`.
7. **Existing litellm integration** -- Reuse the `LLMResponseGenerator` pattern and `load_config_from_env()`.
8. **Multi-tenancy** -- All queries MUST filter by `tenant_id`. Never expose cross-tenant data.

### Assumptions

1. SQLite (via aiosqlite) is sufficient for current development volume.
2. A fast LLM model (GPT-4o-mini / Claude Haiku / Groq) can produce reliable structured classification output.
3. 2000 tokens of history is a reasonable starting budget (tunable via configuration).
4. tiktoken is available (already a dependency via `llm_generator.py`).
5. The existing `ChatRequest.conversation_id` (UUID, optional) in `chat/models.py` will continue to be the primary conversation handle.

---

## System Architecture

### High-Level Component Diagram

```
                          +---------------------+
                          |   API Layer (FastAPI)|
                          |  routes/chat.py     |
                          +----------+----------+
                                     |
                                     | ChatRequest (message, conversation_id)
                                     v
                          +----------+----------+
                          |     ChatService     |
                          |   (chat/service.py) |
                          +----------+----------+
                                     |
                    +----------------+----------------+
                    |                                 |
                    v                                 v
         +---------+---------+            +----------+-----------+
         | ConversationRepo  |            | MasterResponseGen    |
         | (storage layer)   |            | (chat/master_resp)   |
         | - save message    |            +----------+-----------+
         | - get history     |                       |
         +---------+---------+                       v
                   |                      +----------+-----------+
                   |                      |     MasterAgent      |
                   |                      |  (agents/master)     |
                   |                      +----------+-----------+
                   |                                 |
                   |                    +------------+------------+
                   |                    |                         |
                   |                    v                         v
                   |         +----------+----------+  +----------+---------+
                   |         | LLMIntentAnalyzer   |  | KeywordAnalyzer    |
                   |         | (primary)           |  | (fallback)         |
                   |         +----------+----------+  +--------------------+
                   |                    |
                   |                    v
                   |         +----------+----------+
                   |         |  litellm (existing) |
                   |         +---------------------+
                   |
                   v
         +---------+---------+
         |    SQLAlchemy      |
         |  (SQLite/Postgres) |
         +--------------------+
```

### Data Flow (Happy Path)

```
1. User sends: ChatRequest(message="Run the first one", conversation_id=UUID)

2. ChatService.process_chat(request):
   a. Resolve conversation_id (create new if absent)
   b. Store user message -> ConversationRepository.add_message()
   c. Retrieve history -> ConversationRepository.get_recent_messages()
   d. Build context  -> ContextAssembler.assemble(history, token_budget=2000)
   e. Call response_generator.generate_stream(message, context)

3. MasterResponseGenerator.generate_stream(message, context):
   a. Create Task with conversation history in messages list
   b. Delegate to MasterAgent.process_task(task)

4. MasterAgent.process_task(task):
   a. Extract user message + conversation history from task
   b. _analyze_intent(message, conversation_history):
      i.  Try LLMIntentAnalyzer.analyze(message, history, available_actions)
      ii. If LLM fails -> fall back to keyword_analyze_intent(message)
   c. Route based on RoutingDecision
   d. Yield TaskEvents

5. ChatService (continued):
   a. Stream response chunks to client
   b. Store assistant message -> ConversationRepository.add_message()
   c. Yield done event
```

### Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Storage pattern | Abstract Protocol + SQLite impl | Swap to Postgres later without touching business logic |
| LLM for intent only | Yes (not response generation) | Predictable responses via templates; lower cost/latency |
| Keyword as fallback | Keep existing code | Zero-downtime degradation on LLM outage |
| Context budget | Token-based (not message-count) | Handles both short and verbose conversations |
| Structured output | JSON mode via litellm | Reliable parsing; fallback on malformed output |
| Model selection | Configurable via env var `OMNIFORGE_INTENT_MODEL` | Operator chooses cost/quality tradeoff |

---

## Technology Stack

| Layer | Technology | Justification |
|-------|-----------|---------------|
| ORM | SQLAlchemy 2.0+ (already in pyproject.toml) | Existing investment, async support, migration path |
| Async SQLite | aiosqlite (already used in Database class) | Non-blocking DB ops in async context |
| LLM client | litellm (already in LLMResponseGenerator) | Multi-provider, streaming, JSON mode |
| Token counting | tiktoken (already in LLMResponseGenerator) | Accurate token budget enforcement |
| Data models | Pydantic v2 (already used throughout) | Validation, serialization, type safety |
| Testing | pytest + pytest-asyncio (already configured) | Existing test infrastructure |

No new dependencies are required.

---

## Component Specifications

### Component 1: Conversation Domain Models

**Location**: `src/omniforge/conversation/models.py` (new module)

**Purpose**: Pure data models for Conversation and Message entities, decoupled from ORM.

```python
# src/omniforge/conversation/models.py

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    """Role of message sender."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Conversation(BaseModel):
    """A conversation between a user and the platform."""
    id: str = Field(..., min_length=1, max_length=255)
    tenant_id: str = Field(..., min_length=1, max_length=255)
    user_id: str = Field(..., min_length=1, max_length=255)
    title: Optional[str] = Field(None, max_length=500)
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class Message(BaseModel):
    """A single message within a conversation."""
    id: str = Field(..., min_length=1, max_length=255)
    conversation_id: str = Field(..., min_length=1, max_length=255)
    role: MessageRole
    content: str
    created_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
```

**Design notes**:
- Pure Pydantic models with no ORM dependency.
- `metadata` on Message stores routing decisions, intent results, etc.
- `metadata` on Conversation stores future expansion (tags, status, etc.).

---

### Component 2: Conversation Repository (Abstract Interface)

**Location**: `src/omniforge/conversation/repository.py`

**Purpose**: Define the storage contract. All consumers depend on this Protocol, never on a concrete implementation.

```python
# src/omniforge/conversation/repository.py

from typing import Optional, Protocol
from omniforge.conversation.models import Conversation, Message


class ConversationRepository(Protocol):
    """Protocol for conversation persistence operations.

    All implementations MUST scope queries by tenant_id.
    """

    async def create_conversation(
        self, tenant_id: str, user_id: str, title: Optional[str] = None
    ) -> Conversation:
        """Create a new conversation."""
        ...

    async def get_conversation(
        self, conversation_id: str, tenant_id: str
    ) -> Optional[Conversation]:
        """Get conversation by ID. Returns None if not found or wrong tenant."""
        ...

    async def list_conversations(
        self, tenant_id: str, user_id: str, limit: int = 50, offset: int = 0
    ) -> list[Conversation]:
        """List conversations for a user, ordered by updated_at desc."""
        ...

    async def update_conversation(
        self, conversation: Conversation
    ) -> Conversation:
        """Update conversation metadata/title."""
        ...

    async def add_message(
        self, conversation_id: str, role: str, content: str,
        metadata: Optional[dict] = None
    ) -> Message:
        """Add a message to a conversation. Updates conversation.updated_at."""
        ...

    async def get_messages(
        self, conversation_id: str, limit: int = 50, before_id: Optional[str] = None
    ) -> list[Message]:
        """Get messages in chronological order, with optional cursor pagination."""
        ...

    async def get_recent_messages(
        self, conversation_id: str, limit: int = 20
    ) -> list[Message]:
        """Get most recent N messages in chronological order."""
        ...
```

**Design notes**:
- Uses Python `Protocol` (structural typing) -- same pattern as `prompts/storage/repository.py`.
- `tenant_id` is required on `get_conversation` to prevent cross-tenant access.
- `get_recent_messages` is the primary method for context assembly.
- Methods are async to match the existing async architecture.

---

### Component 3: SQLite Conversation Repository

**Location**: `src/omniforge/conversation/sqlite_repository.py`

**Purpose**: SQLAlchemy-backed implementation of `ConversationRepository`.

**ORM Models** (in `src/omniforge/conversation/orm.py`):

```python
# src/omniforge/conversation/orm.py

import uuid
from datetime import datetime
from sqlalchemy import DateTime, Index, JSON, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from omniforge.storage.database import Base


class ConversationModel(Base):
    """ORM model for conversations."""
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    conversation_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # Relationship to messages
    messages: Mapped[list["ConversationMessageModel"]] = relationship(
        "ConversationMessageModel",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ConversationMessageModel.created_at",
    )

    __table_args__ = (
        Index("idx_conv_tenant_user", "tenant_id", "user_id"),
        Index("idx_conv_tenant_updated", "tenant_id", "updated_at"),
    )


class ConversationMessageModel(Base):
    """ORM model for conversation messages."""
    __tablename__ = "conversation_messages"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    conversation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, index=True
    )
    message_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # Relationship back to conversation
    conversation: Mapped["ConversationModel"] = relationship(
        "ConversationModel", back_populates="messages"
    )

    __table_args__ = (
        Index("idx_msg_conversation_created", "conversation_id", "created_at"),
    )
```

**Repository implementation** (`sqlite_repository.py`):

```python
class SQLiteConversationRepository:
    """SQLAlchemy-backed conversation repository.

    Uses the existing Database class for session management.
    """

    def __init__(self, database: Database) -> None:
        self._db = database

    async def create_conversation(
        self, tenant_id: str, user_id: str, title: Optional[str] = None
    ) -> Conversation:
        async with self._db.session() as session:
            model = ConversationModel(
                tenant_id=tenant_id,
                user_id=user_id,
                title=title,
            )
            session.add(model)
            await session.flush()
            return self._to_domain(model)

    async def get_conversation(
        self, conversation_id: str, tenant_id: str
    ) -> Optional[Conversation]:
        async with self._db.session() as session:
            result = await session.execute(
                select(ConversationModel).where(
                    ConversationModel.id == conversation_id,
                    ConversationModel.tenant_id == tenant_id,
                )
            )
            model = result.scalar_one_or_none()
            return self._to_domain(model) if model else None

    async def add_message(
        self, conversation_id: str, role: str, content: str,
        metadata: Optional[dict] = None
    ) -> Message:
        async with self._db.session() as session:
            msg = ConversationMessageModel(
                conversation_id=conversation_id,
                role=role,
                content=content,
                message_metadata=metadata or {},
            )
            session.add(msg)
            # Update conversation.updated_at
            await session.execute(
                update(ConversationModel)
                .where(ConversationModel.id == conversation_id)
                .values(updated_at=datetime.utcnow())
            )
            await session.flush()
            return self._message_to_domain(msg)

    async def get_recent_messages(
        self, conversation_id: str, limit: int = 20
    ) -> list[Message]:
        async with self._db.session() as session:
            result = await session.execute(
                select(ConversationMessageModel)
                .where(ConversationMessageModel.conversation_id == conversation_id)
                .order_by(ConversationMessageModel.created_at.desc())
                .limit(limit)
            )
            rows = list(result.scalars().all())
            rows.reverse()  # Return in chronological order
            return [self._message_to_domain(r) for r in rows]

    # ... list_conversations, get_messages, update_conversation follow same pattern
```

**Design notes**:
- Reuses `Database` and `Base` from `storage/database.py` -- no new database infrastructure.
- ORM column named `conversation_metadata` / `message_metadata` to avoid SQLAlchemy reserved word `metadata`.
- `add_message` atomically updates `conversation.updated_at` in the same transaction.
- `get_recent_messages` fetches in DESC order then reverses for chronological output (efficient for LIMIT queries).

---

### Component 4: In-Memory Conversation Repository

**Location**: `src/omniforge/conversation/memory_repository.py`

**Purpose**: Thread-safe in-memory implementation for testing and development without a database.

```python
class InMemoryConversationRepository:
    """In-memory conversation storage for testing."""

    def __init__(self) -> None:
        self._conversations: dict[str, Conversation] = {}
        self._messages: dict[str, list[Message]] = {}  # conversation_id -> messages
        self._lock = asyncio.Lock()

    # Implements same interface as ConversationRepository Protocol
    # Uses dicts + asyncio.Lock for thread safety
    # Same pattern as storage/memory.py InMemoryTaskRepository
```

This follows the existing pattern in `storage/memory.py`.

---

### Component 5: Context Assembler

**Location**: `src/omniforge/conversation/context.py`

**Purpose**: Pure function module that assembles conversation context from message history, respecting a token budget.

```python
# src/omniforge/conversation/context.py

from typing import Optional
from omniforge.conversation.models import Message


# Default configuration
DEFAULT_TOKEN_BUDGET = 2000
DEFAULT_MAX_MESSAGES = 20  # 10 exchanges = 20 messages
MIN_RECENT_MESSAGES = 6    # Always include last 3 exchanges


def estimate_tokens(text: str) -> int:
    """Estimate token count for a text string.

    Uses tiktoken if available, falls back to char/4 approximation.
    """
    try:
        import tiktoken
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    except Exception:
        return max(1, len(text) // 4)


def assemble_context(
    messages: list[Message],
    token_budget: int = DEFAULT_TOKEN_BUDGET,
    max_messages: int = DEFAULT_MAX_MESSAGES,
    min_recent: int = MIN_RECENT_MESSAGES,
) -> list[Message]:
    """Assemble conversation context within token budget.

    Strategy:
    1. Always include the most recent `min_recent` messages (3 exchanges).
    2. Add older messages until token budget or max_messages is reached.
    3. Return messages in chronological order.

    Args:
        messages: Full message list in chronological order (newest last).
        token_budget: Maximum total tokens for context.
        max_messages: Maximum number of messages to include.
        min_recent: Minimum recent messages to always include.

    Returns:
        Subset of messages that fit within the budget, chronological order.
    """
    if not messages:
        return []

    # Cap to max_messages from the end
    candidates = messages[-max_messages:]

    # Always include the most recent min_recent messages
    guaranteed = candidates[-min_recent:] if len(candidates) >= min_recent else candidates
    remaining = candidates[:-len(guaranteed)] if len(guaranteed) < len(candidates) else []

    # Count tokens for guaranteed messages
    used_tokens = sum(estimate_tokens(_format_message(m)) for m in guaranteed)

    # Add older messages (from most recent to oldest) if budget allows
    additional: list[Message] = []
    for msg in reversed(remaining):
        msg_tokens = estimate_tokens(_format_message(msg))
        if used_tokens + msg_tokens > token_budget:
            break
        additional.append(msg)
        used_tokens += msg_tokens

    # Combine: additional (reversed to chronological) + guaranteed
    additional.reverse()
    return additional + guaranteed


def format_context_for_llm(messages: list[Message]) -> list[dict[str, str]]:
    """Format messages into LLM chat format.

    Args:
        messages: Messages to format.

    Returns:
        List of {"role": "user"|"assistant", "content": "..."} dicts.
    """
    return [
        {"role": msg.role.value if hasattr(msg.role, 'value') else msg.role,
         "content": msg.content}
        for msg in messages
    ]


def _format_message(msg: Message) -> str:
    """Format a single message for token counting."""
    role = msg.role.value if hasattr(msg.role, 'value') else msg.role
    return f"{role}: {msg.content}"
```

**Design notes**:
- Pure functions -- no side effects, fully testable with synthetic data.
- `assemble_context` guarantees the last 3 exchanges are always present.
- Older messages are added greedily until the token budget is exhausted.
- `format_context_for_llm` produces the standard OpenAI/Anthropic message format.

---

### Component 6: LLM Intent Analyzer

**Location**: `src/omniforge/conversation/intent_analyzer.py`

**Purpose**: LLM-powered intent classification with structured output.

```python
# src/omniforge/conversation/intent_analyzer.py

import json
import logging
from typing import Any, Optional

import litellm

from omniforge.agents.master_agent import ActionType, RoutingDecision
from omniforge.conversation.models import Message
from omniforge.conversation.context import format_context_for_llm
from omniforge.llm.config import load_config_from_env

logger = logging.getLogger(__name__)


# Structured output schema for intent classification
INTENT_RESULT_SCHEMA = {
    "type": "object",
    "properties": {
        "action_type": {
            "type": "string",
            "enum": [at.value for at in ActionType],
        },
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "entities": {"type": "object"},
        "reasoning": {"type": "string"},
        "is_ambiguous": {"type": "boolean"},
        "alternative_action": {
            "type": "string",
            "enum": [at.value for at in ActionType] + [None],
        },
        "clarifying_question": {"type": "string"},
    },
    "required": ["action_type", "confidence", "reasoning", "is_ambiguous"],
}


class LLMIntentAnalyzer:
    """Analyzes user intent using an LLM for structured classification.

    Uses a fast, inexpensive model for intent classification. Configurable
    via environment variable OMNIFORGE_INTENT_MODEL (default: gpt-4o-mini).
    """

    def __init__(
        self,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 500,
    ) -> None:
        self._config = load_config_from_env()
        self._model = model or os.getenv(
            "OMNIFORGE_INTENT_MODEL", "gpt-4o-mini"
        )
        self._temperature = temperature
        self._max_tokens = max_tokens

    async def analyze(
        self,
        message: str,
        conversation_history: Optional[list[Message]] = None,
        available_agents: Optional[list[str]] = None,
    ) -> RoutingDecision:
        """Analyze user intent using LLM.

        Args:
            message: Current user message.
            conversation_history: Recent conversation context.
            available_agents: Names/descriptions of available agents.

        Returns:
            RoutingDecision with LLM-determined action type and metadata.

        Raises:
            IntentAnalysisError: If LLM call fails and cannot produce a result.
        """
        system_prompt = self._build_system_prompt(available_agents)
        messages = self._build_messages(system_prompt, message, conversation_history)

        try:
            response = await litellm.acompletion(
                model=self._model,
                messages=messages,
                temperature=self._temperature,
                max_tokens=self._max_tokens,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            return self._parse_response(content)

        except Exception as e:
            logger.warning(f"LLM intent analysis failed: {e}")
            raise IntentAnalysisError(str(e)) from e

    def _build_system_prompt(
        self, available_agents: Optional[list[str]] = None
    ) -> str:
        """Build the system prompt for intent classification."""
        agents_section = ""
        if available_agents:
            agents_list = "\n".join(f"- {a}" for a in available_agents)
            agents_section = f"\n\nAvailable agents:\n{agents_list}"

        return f"""You are an intent classifier for the OmniForge AI agent platform.

Analyze the user's message and classify their intent into one of these action types:

- create_agent: User wants to create a new automation agent
- create_skill: User wants to create a new skill/capability
- execute_task: User wants to run/execute something using existing agents
- update_agent: User wants to modify an existing agent
- query_info: User is asking for information, help, or listing things
- manage_platform: User wants to configure platform settings
- unknown: Cannot determine intent
{agents_section}

Respond with a JSON object containing:
- action_type: one of the action types above
- confidence: 0.0 to 1.0 (how confident you are)
- entities: key-value pairs extracted (agent_name, data_source, frequency, etc.)
- reasoning: brief explanation of why you chose this intent
- is_ambiguous: true if the request could map to multiple intents
- alternative_action: second-best action type if ambiguous (null otherwise)
- clarifying_question: a question to ask if confidence < 0.7 (null otherwise)

Consider the conversation history to resolve references like "yes", "the first one",
"do that again", or "change it to weekly". Context is critical for follow-ups."""

    def _build_messages(
        self,
        system_prompt: str,
        current_message: str,
        history: Optional[list[Message]] = None,
    ) -> list[dict[str, str]]:
        """Build the full message list for the LLM call."""
        messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history
        if history:
            formatted = format_context_for_llm(history)
            messages.extend(formatted)

        # Add current message
        messages.append({"role": "user", "content": current_message})
        return messages

    def _parse_response(self, content: str) -> RoutingDecision:
        """Parse LLM JSON response into RoutingDecision."""
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise IntentAnalysisError(f"Invalid JSON from LLM: {e}") from e

        # Validate action_type
        action_str = data.get("action_type", "unknown")
        try:
            action_type = ActionType(action_str)
        except ValueError:
            action_type = ActionType.UNKNOWN

        confidence = max(0.0, min(1.0, float(data.get("confidence", 0.5))))

        return RoutingDecision(
            action_type=action_type,
            confidence=confidence,
            reasoning=data.get("reasoning", ""),
            entities=data.get("entities", {}),
        )


class IntentAnalysisError(Exception):
    """Raised when LLM intent analysis fails."""
    pass
```

**Design notes**:
- Uses `response_format={"type": "json_object"}` for structured output (supported by most modern LLMs via litellm).
- Low temperature (0.1) for deterministic classification.
- Low `max_tokens` (500) since the response is structured JSON, not prose.
- `_parse_response` validates and normalizes all fields defensively.
- `IntentAnalysisError` is a clean exception type that callers can catch for fallback.
- The model is configurable via `OMNIFORGE_INTENT_MODEL` env var.

---

### Component 7: Updated ChatService

**Location**: `src/omniforge/chat/service.py` (existing file, modified)

**Changes**: Add conversation storage and context retrieval.

```python
# Updated ChatService.process_chat method (pseudocode showing changes)

class ChatService:
    def __init__(
        self,
        response_generator: Optional[ResponseGenerator] = None,
        user_id: Optional[str] = None,
        conversation_repo: Optional[ConversationRepository] = None,  # NEW
        tenant_id: Optional[str] = None,  # NEW
    ) -> None:
        self._response_generator = response_generator or MasterResponseGenerator(
            user_id=user_id
        )
        self._conversation_repo = conversation_repo  # NEW
        self._tenant_id = tenant_id or "default-tenant"  # NEW
        self._user_id = user_id or "default-user"  # NEW

    async def process_chat(self, request: ChatRequest) -> AsyncIterator[str]:
        conversation_id = str(request.conversation_id) if request.conversation_id else str(uuid4())

        # --- NEW: Conversation storage ---
        conversation_history: list[Message] = []
        if self._conversation_repo:
            # Ensure conversation exists
            conv = await self._conversation_repo.get_conversation(
                conversation_id, self._tenant_id
            )
            if conv is None:
                conv = await self._conversation_repo.create_conversation(
                    tenant_id=self._tenant_id,
                    user_id=self._user_id,
                )
                conversation_id = conv.id

            # Store user message
            await self._conversation_repo.add_message(
                conversation_id=conversation_id,
                role="user",
                content=request.message,
            )

            # Retrieve context
            conversation_history = await self._conversation_repo.get_recent_messages(
                conversation_id=conversation_id,
                limit=20,
            )
        # --- END NEW ---

        accumulated_content = ""
        try:
            # Pass history to response generator (NEW parameter)
            async for chunk in self._response_generator.generate_stream(
                request.message,
                conversation_history=conversation_history,  # NEW
            ):
                accumulated_content += chunk
                yield format_chunk_event(chunk)

            # --- NEW: Store assistant response ---
            if self._conversation_repo and accumulated_content:
                await self._conversation_repo.add_message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=accumulated_content,
                )
            # --- END NEW ---

            # ... rest unchanged (token counting, done event)
```

**Backward compatibility**: `conversation_repo` defaults to `None`. When `None`, the service behaves exactly as before (no storage, no context). Existing callers (API routes, tests) are unaffected.

---

### Component 8: Updated MasterResponseGenerator

**Location**: `src/omniforge/chat/master_response_generator.py` (existing file, modified)

**Changes**: Accept and forward conversation history.

```python
class MasterResponseGenerator:
    async def generate_stream(
        self,
        message: str,
        conversation_history: Optional[list[Message]] = None,  # NEW
    ) -> AsyncIterator[str]:
        # Build context window
        context_messages: list[Message] = []
        if conversation_history:
            context_messages = assemble_context(
                conversation_history,
                token_budget=2000,
            )

        # Create task with history
        task = self._create_task_from_message(message, context_messages)

        async for event in self._master_agent.process_task(task):
            if hasattr(event, "message_parts"):
                for part in event.message_parts:
                    if hasattr(part, "text"):
                        yield part.text
```

The `_create_task_from_message` method is updated to include context messages in the `task.messages` list, prepended before the current user message.

**Backward compatibility**: `conversation_history` defaults to `None`. When absent, behavior is identical to current implementation.

---

### Component 9: Updated MasterAgent._analyze_intent

**Location**: `src/omniforge/agents/master_agent.py` (existing file, modified)

**Changes**: Use `LLMIntentAnalyzer` as primary classifier, keep keyword matching as fallback.

```python
class MasterAgent(BaseAgent):
    def __init__(
        self,
        agent_id: Optional[UUID] = None,
        tenant_id: Optional[str] = None,
        agent_registry: Optional[AgentRegistry] = None,
        intent_analyzer: Optional[LLMIntentAnalyzer] = None,  # NEW
        **kwargs,
    ) -> None:
        super().__init__(agent_id=agent_id, tenant_id=tenant_id, **kwargs)
        self._agent_registry = agent_registry
        self._conversation_context: dict[str, Any] = {}
        self._intent_analyzer = intent_analyzer  # NEW

    async def _analyze_intent(
        self,
        message: str,
        conversation_history: Optional[list[Message]] = None,  # NEW
    ) -> RoutingDecision:
        """Analyze intent using LLM (primary) with keyword fallback."""

        # Try LLM-based analysis if analyzer is available
        if self._intent_analyzer is not None:
            try:
                return await self._intent_analyzer.analyze(
                    message=message,
                    conversation_history=conversation_history,
                )
            except IntentAnalysisError:
                logger.warning(
                    "LLM intent analysis failed, falling back to keywords"
                )

        # Fallback: existing keyword matching (unchanged)
        return self._keyword_analyze_intent(message)

    def _keyword_analyze_intent(self, message: str) -> RoutingDecision:
        """Original keyword-based intent analysis (now a fallback).

        This is the existing code from lines 190-321, extracted to a
        named method for clarity.
        """
        # ... existing keyword matching code moved here verbatim ...
```

**Design notes**:
- `intent_analyzer` is injected via constructor (dependency injection).
- When `intent_analyzer` is `None`, the agent uses keyword matching only (full backward compat).
- The existing keyword logic is extracted into `_keyword_analyze_intent` (a pure rename, no logic changes).
- `conversation_history` is extracted from the task messages in `process_task`.

---

### Component 10: Updated ResponseGenerator (Adapter)

**Location**: `src/omniforge/chat/response_generator.py` (existing file, modified)

**Changes**: Forward the `conversation_history` parameter through to whichever backend generator is active.

```python
class ResponseGenerator:
    async def generate_stream(
        self,
        message: str,
        conversation_history: Optional[list] = None,  # NEW
    ) -> AsyncIterator[str]:
        if self._master_generator:
            async for chunk in self._master_generator.generate_stream(
                message, conversation_history=conversation_history
            ):
                yield chunk
        elif self._generator:
            # LLM generator does not use history (unchanged)
            async for chunk in self._generator.generate_stream(message):
                yield chunk
        else:
            # Placeholder fallback (unchanged)
            yield "Thank you for your message! "
            yield f'You said: "{message}" '
            yield "This is a placeholder response. "
```

---

## Database Schema

### Table: conversations

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | VARCHAR(36) | PK | UUID |
| tenant_id | VARCHAR(255) | NOT NULL, INDEX | Multi-tenancy |
| user_id | VARCHAR(255) | NOT NULL, INDEX | User scoping |
| title | VARCHAR(500) | NULLABLE | Auto-generated or user-set |
| created_at | DATETIME | NOT NULL | Immutable |
| updated_at | DATETIME | NOT NULL | Updated on new message |
| conversation_metadata | JSON | NOT NULL, DEFAULT {} | Extensible |

**Indexes**:
- `idx_conv_tenant_user (tenant_id, user_id)` -- list conversations
- `idx_conv_tenant_updated (tenant_id, updated_at)` -- recent conversations

### Table: conversation_messages

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | VARCHAR(36) | PK | UUID |
| conversation_id | VARCHAR(36) | FK conversations.id, CASCADE | Parent ref |
| role | VARCHAR(20) | NOT NULL | "user", "assistant", "system" |
| content | TEXT | NOT NULL | Message body |
| created_at | DATETIME | NOT NULL, INDEX | Chronological ordering |
| message_metadata | JSON | NOT NULL, DEFAULT {} | Intent results, routing |

**Indexes**:
- `idx_msg_conversation_created (conversation_id, created_at)` -- message retrieval

**Table creation**: Use `Database.create_tables()` which calls `Base.metadata.create_all()`. Since the new ORM models extend `Base`, they are auto-discovered.

---

## LLM Integration Architecture

### Intent Classification Prompt

The system prompt (detailed in Component 6) instructs the LLM to:

1. Classify into one of 7 action types.
2. Assign a confidence score (0.0 - 1.0).
3. Extract entities (agent_name, data_source, frequency, etc.).
4. Provide reasoning.
5. Flag ambiguity and suggest alternatives.
6. Generate a clarifying question when confidence < 0.7.

### Model Selection Strategy

```
Priority:
1. OMNIFORGE_INTENT_MODEL env var (explicit override)
2. "gpt-4o-mini" (default -- fast, cheap, good at structured output)

Fallback chain:
  LLM intent -> keyword intent (on any LLM error)
```

### Cost Analysis

| Model | Input cost/1M | Output cost/1M | Est. tokens/request | Est. cost/request |
|-------|---------------|----------------|---------------------|-------------------|
| gpt-4o-mini | $0.15 | $0.60 | ~800 in + ~200 out | ~$0.00024 |
| claude-3-haiku | $0.25 | $1.25 | ~800 in + ~200 out | ~$0.00045 |
| groq/llama-3.3-70b | $0.59 | $0.79 | ~800 in + ~200 out | ~$0.00063 |

All well under the $0.005 target per request.

### Error Handling

```
LLMIntentAnalyzer.analyze()
  |
  |-- litellm.acompletion() raises Exception
  |   -> Log warning, raise IntentAnalysisError
  |
  |-- JSON parse fails
  |   -> Log warning, raise IntentAnalysisError
  |
  |-- Invalid action_type in response
  |   -> Default to ActionType.UNKNOWN (graceful)
  |
  |-- Confidence out of range
      -> Clamp to [0.0, 1.0] (graceful)

MasterAgent._analyze_intent()
  |
  |-- Catches IntentAnalysisError
  |   -> Falls back to _keyword_analyze_intent()
  |
  |-- intent_analyzer is None
      -> Uses _keyword_analyze_intent() directly
```

---

## Context Window Management

### Token Budget Algorithm

```
Given: messages[] (chronological), budget=2000, min_recent=6

1. Take last 20 messages (max_messages cap)
2. Reserve last 6 messages (3 exchanges) -- "guaranteed"
3. Count tokens for guaranteed set -> used_tokens
4. Walk backward through remaining messages:
   - If used_tokens + msg_tokens <= budget: include, add tokens
   - Else: stop
5. Return [additional (chronological)] + [guaranteed]
```

### Token Estimation

- Primary: `tiktoken.get_encoding("cl100k_base")` for accurate GPT-family counting.
- Fallback: `max(1, len(text) // 4)` if tiktoken fails.
- Per-message overhead: `"{role}: "` prefix (~3 tokens).

### Configuration

| Parameter | Default | Env var | Notes |
|-----------|---------|---------|-------|
| Token budget | 2000 | `OMNIFORGE_CONTEXT_TOKEN_BUDGET` | Start conservative |
| Max messages | 20 | `OMNIFORGE_CONTEXT_MAX_MESSAGES` | 10 exchanges |
| Min recent | 6 | N/A | Always 3 exchanges |

---

## Security Architecture

### Multi-Tenancy Enforcement

Every repository method that reads data requires `tenant_id`:
- `get_conversation(conversation_id, tenant_id)` -- enforces tenant scoping.
- `list_conversations(tenant_id, user_id)` -- scoped by design.
- Messages are accessed through conversation_id, which is tenant-verified.

### Data Isolation

- Conversations are scoped by `(tenant_id, user_id)`.
- No API endpoint allows cross-tenant conversation access.
- The `conversation_id` in a `ChatRequest` is validated against the authenticated tenant/user before use.

### Sensitive Data

- Conversation content is stored as-is in v1 (plaintext in SQLite).
- Future enhancement: application-level encryption for message content.
- Intent metadata stored in `message_metadata` does NOT include raw API keys or secrets detected in user messages.
- LLM API keys are managed via environment variables, never stored in conversation data.

---

## Performance and Scalability

### Latency Budget

| Step | Target | Notes |
|------|--------|-------|
| DB: get recent messages | < 10ms | Indexed query, small result set |
| Context assembly | < 5ms | In-memory, pure function |
| LLM intent classification | < 800ms | Fast model, structured output |
| Response generation (existing) | varies | Template-based, fast |
| DB: store messages (async) | < 10ms | Simple insert |
| **Total overhead** | **< 850ms** | Added to existing response time |

### Scaling Considerations

- **SQLite to PostgreSQL**: Swap `SQLiteConversationRepository` for a PostgreSQL implementation. The `ConversationRepository` Protocol ensures zero business logic changes.
- **Read-heavy workload**: Message retrieval is indexed. For very active conversations (1000+ messages), the `LIMIT` clause and DESC ordering ensure fast queries.
- **Connection pooling**: Already supported by `Database` class (`pool_size`, `max_overflow`).

---

## Monitoring and Operations

### Logging

| Event | Level | Module | Content |
|-------|-------|--------|---------|
| LLM intent call | INFO | intent_analyzer | model, latency_ms, action_type, confidence |
| LLM intent failure | WARNING | intent_analyzer | error type, message |
| Keyword fallback used | WARNING | master_agent | reason (LLM failed / analyzer not configured) |
| Conversation created | DEBUG | sqlite_repository | conversation_id, tenant_id |
| Message stored | DEBUG | sqlite_repository | conversation_id, role |
| Context assembled | DEBUG | context | message_count, total_tokens, budget |

### Metrics (Future)

- `intent_classification_latency_ms` -- histogram
- `intent_classification_method` -- counter (llm vs keyword)
- `intent_confidence` -- histogram
- `context_messages_included` -- histogram
- `context_tokens_used` -- histogram
- `conversation_message_count` -- gauge per conversation

---

## Testing Strategy

### Unit Tests

**Component: Conversation Models** (`tests/conversation/test_models.py`)
- Valid Conversation and Message creation
- Validation of required fields (id, tenant_id, user_id)
- MessageRole enum values
- Metadata defaults

**Component: Context Assembler** (`tests/conversation/test_context.py`)
- Empty message list returns empty
- Messages within budget included fully
- Messages exceeding budget are truncated from oldest
- Guaranteed recent messages always included (even if they exceed budget alone)
- Token estimation accuracy (vs tiktoken)
- `format_context_for_llm` output structure
- Edge case: single message
- Edge case: all messages very long (each exceeds budget)

**Component: LLMIntentAnalyzer** (`tests/conversation/test_intent_analyzer.py`)
- Mock litellm.acompletion to return known JSON
- Valid structured output parsed correctly
- Invalid JSON raises IntentAnalysisError
- Unknown action_type defaults to UNKNOWN
- Confidence clamped to [0.0, 1.0]
- System prompt includes available agents when provided
- Conversation history formatted in messages
- API error raises IntentAnalysisError

**Component: Keyword Analyzer** (`tests/agents/test_keyword_intent.py`)
- All existing keyword tests remain passing (extracted method)
- Each ActionType has at least 2 test phrases
- Unknown intent for nonsense input

**Component: SQLite Repository** (`tests/conversation/test_sqlite_repository.py`)
- Create and retrieve conversation
- Tenant isolation (get_conversation with wrong tenant returns None)
- Add and retrieve messages in chronological order
- get_recent_messages respects limit
- list_conversations ordered by updated_at
- Message addition updates conversation.updated_at
- Concurrent operations with asyncio (no data corruption)

**Component: InMemory Repository** (`tests/conversation/test_memory_repository.py`)
- Mirror all SQLite tests for functional parity

### Integration Tests

**Full flow** (`tests/integration/test_smart_master_agent.py`):
1. Create ChatService with SQLite repository and LLM analyzer (mocked).
2. Send first message -> verify conversation created, user message stored.
3. Verify LLM analyzer called with empty history (first message).
4. Verify response generated and assistant message stored.
5. Send follow-up -> verify history includes both prior messages.
6. Verify LLM analyzer called with conversation context.
7. Simulate LLM failure -> verify keyword fallback used.
8. Verify full round-trip with conversation_id continuity.

**Backward compatibility** (`tests/integration/test_backward_compat.py`):
1. Create ChatService with NO repository (repo=None).
2. Verify identical behavior to current implementation.
3. No storage calls, no context, keyword-only intent.

### Performance Tests

**Context assembly benchmark** (`tests/performance/test_context_performance.py`):
- Assemble context for 10, 50, 100, 500 messages.
- Verify < 50ms for 500 messages.
- Verify token counting accuracy within 10% of tiktoken.

### Test Configuration

All tests use `InMemoryConversationRepository` by default. SQLite tests use an in-memory SQLite database (`sqlite+aiosqlite:///:memory:`). LLM calls are always mocked in unit and integration tests.

---

## Development Workflow

### Module Structure (New Files)

```
src/omniforge/conversation/          # NEW package
    __init__.py
    models.py                        # Conversation, Message, MessageRole
    repository.py                    # ConversationRepository Protocol
    sqlite_repository.py             # SQLAlchemy implementation
    memory_repository.py             # In-memory implementation (testing)
    orm.py                           # SQLAlchemy ORM models
    context.py                       # Context assembly (pure functions)
    intent_analyzer.py               # LLMIntentAnalyzer

tests/conversation/                  # NEW test package
    __init__.py
    test_models.py
    test_context.py
    test_intent_analyzer.py
    test_sqlite_repository.py
    test_memory_repository.py

tests/integration/
    test_smart_master_agent.py       # NEW integration test
    test_backward_compat.py          # NEW backward compat test
```

### Modified Files

```
src/omniforge/chat/service.py               # Add repo + context params
src/omniforge/chat/response_generator.py     # Forward history param
src/omniforge/chat/master_response_generator.py  # Accept + assemble context
src/omniforge/agents/master_agent.py         # Add analyzer + extract keyword method
```

### Dependency Graph (No Cycles)

```
conversation/models.py      <- Pure, depends on nothing internal
conversation/repository.py  <- Depends on conversation/models
conversation/orm.py         <- Depends on storage/database.Base
conversation/context.py     <- Depends on conversation/models
conversation/intent_analyzer.py <- Depends on conversation/models, agents/master_agent.ActionType
conversation/sqlite_repository.py <- Depends on conversation/orm, conversation/models, storage/database

chat/service.py             <- Depends on conversation/repository (optional)
chat/master_response_generator.py <- Depends on conversation/context
agents/master_agent.py      <- Depends on conversation/intent_analyzer (optional)
```

No circular dependencies. The `conversation` package depends only on `storage/database.Base` (for ORM) and `agents/master_agent.ActionType` (for the enum). To eliminate the dependency on `ActionType`, we could duplicate the enum in the conversation package, but since `ActionType` is a simple `str, Enum` with no imports, the coupling is minimal and acceptable.

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| LLM accuracy below 90% for OmniForge-specific intents | Medium | Medium | Extensive prompt iteration; build eval test set of 50+ user messages before launch |
| LLM latency spikes (> 2s) degrading user experience | Low | Medium | Keyword fallback automatic; consider "thinking" indicator in UI |
| SQLite performance under concurrent writes | Low | Low | Single-process dev stage; PostgreSQL swap path ready |
| Token budget too small (2000) for complex conversations | Medium | Low | Configurable; monitor and adjust based on clarification rates |
| Breaking existing tests with signature changes | Low | High | All new params have defaults; backward compat integration test |
| Conversation storage adds data privacy burden | Medium | Medium | Start with plaintext; add encryption in follow-up phase |

---

## Implementation Phases

### Phase 1: Conversation Storage (Foundation)

**Duration**: 2-3 days
**Dependencies**: None

**Tasks**:
1. Create `src/omniforge/conversation/` package with `__init__.py`
2. Implement `models.py` (Conversation, Message, MessageRole)
3. Implement `repository.py` (ConversationRepository Protocol)
4. Implement `orm.py` (SQLAlchemy ORM models)
5. Implement `sqlite_repository.py`
6. Implement `memory_repository.py`
7. Write unit tests for models, both repositories
8. Verify ORM tables create correctly via `Database.create_tables()`

**Done when**: All unit tests pass. Messages can be stored and retrieved with tenant isolation.

### Phase 2: Context Passing (Plumbing)

**Duration**: 2-3 days
**Dependencies**: Phase 1

**Tasks**:
1. Implement `context.py` (assemble_context, format_context_for_llm, estimate_tokens)
2. Write unit tests for context assembly (budget enforcement, edge cases)
3. Update `ChatService.__init__` to accept optional `ConversationRepository`
4. Update `ChatService.process_chat` to store messages and retrieve history
5. Update `ResponseGenerator.generate_stream` to accept and forward `conversation_history`
6. Update `MasterResponseGenerator.generate_stream` to accept history and call `assemble_context`
7. Update `MasterResponseGenerator._create_task_from_message` to include history in task
8. Write backward compatibility test (service with repo=None)
9. Write integration test (service with in-memory repo)
10. Run all existing tests to confirm no regressions

**Done when**: Conversation history flows from ChatService through to MasterAgent. All existing tests pass. New integration tests pass.

### Phase 3: LLM Intent Analysis (Intelligence)

**Duration**: 3-4 days
**Dependencies**: Phase 2

**Tasks**:
1. Implement `intent_analyzer.py` (LLMIntentAnalyzer, IntentAnalysisError)
2. Write unit tests with mocked litellm (all parse/error paths)
3. Extract `_keyword_analyze_intent` from `MasterAgent._analyze_intent`
4. Update `MasterAgent.__init__` to accept optional `LLMIntentAnalyzer`
5. Update `MasterAgent._analyze_intent` to try LLM then fall back to keywords
6. Update `MasterAgent.process_task` to extract history from task and pass to `_analyze_intent`
7. Write integration test: full flow with mocked LLM
8. Write integration test: LLM failure triggers keyword fallback
9. Build eval test set (20+ user messages with expected intents) for prompt tuning
10. Run full test suite, lint, type check
11. Manual testing with real LLM API key (optional, not automated)

**Done when**: LLM-powered intent classification works end-to-end with fallback. All tests pass. Eval accuracy meets initial threshold.

---

## Alternative Approaches Considered

### Alternative 1: Message-Count Context Window (Rejected)

Instead of token budgeting, always include the last N messages regardless of length.

**Pros**: Simpler implementation, no token counting needed.
**Cons**: Long messages could blow the LLM context window or waste budget on a single verbose message. Short conversations would include too few tokens of useful context.
**Decision**: Token-based budgeting is slightly more complex but handles real-world variance much better.

### Alternative 2: Separate Intent Microservice (Rejected)

Run intent classification as a separate HTTP service.

**Pros**: Independent scaling, separate deployment, language flexibility.
**Cons**: Massive overkill for current single-process architecture. Adds network latency, deployment complexity, and operational burden. The abstract interface pattern (`LLMIntentAnalyzer` class) provides the same replaceability without the infrastructure cost.
**Decision**: In-process module with clean interface. Can extract to service later if needed.

### Alternative 3: Fine-tuned Classification Model (Deferred)

Train a custom classifier on OmniForge-specific intents.

**Pros**: Potentially higher accuracy, lower latency, lower cost.
**Cons**: Requires labeled training data (we do not have enough yet). Maintenance burden for retraining. Premature optimization.
**Decision**: Start with prompt-engineered general model. The conversation storage enables collecting labeled data for future fine-tuning.

### Sync vs Async Tradeoff

All new code is async (repository methods, LLM calls). This matches the existing codebase (`async def process_task`, `async def generate_stream`). The token counting and context assembly are synchronous pure functions called within async methods -- no blocking IO.

### Push vs Pull for Context

**Pull** (chosen): ChatService retrieves history on each request. Simple, stateless between requests, no memory management needed.
**Push** (rejected): Maintain an in-memory context buffer that grows with each message. Requires lifecycle management, memory bounds, and loses state on process restart.

---

## References

- [Product Spec](smart-master-agent-spec.md)
- [Product Vision](product-vision.md)
- [Coding Guidelines](/Users/sohitkumar/code/omniforge/coding-guidelines.md)
- [Existing Master Agent](/Users/sohitkumar/code/omniforge/src/omniforge/agents/master_agent.py)
- [Existing Chat Service](/Users/sohitkumar/code/omniforge/src/omniforge/chat/service.py)
- [Existing Database Setup](/Users/sohitkumar/code/omniforge/src/omniforge/storage/database.py)
- [Existing ORM Models](/Users/sohitkumar/code/omniforge/src/omniforge/storage/models.py)
- [LLM Config](/Users/sohitkumar/code/omniforge/src/omniforge/llm/config.py)

---

## Evolution Notes

### 2026-01-30 v1.0 (Initial Plan)

**Key decisions**:
- New `conversation/` package to avoid polluting existing `chat/` or `storage/` modules with conversation-specific logic.
- Protocol-based repository for backend swappability.
- Optional dependency injection on all modified constructors for backward compatibility.
- Token-based context window over message-count.
- Keyword fallback preserved as safety net.

**Open items**:
- Exact prompt wording for intent classification requires iteration against a test set.
- Token budget (2000) may need tuning based on real-world follow-up resolution accuracy.
- Conversation title auto-generation (from first message) is a UI concern but could be handled in the repository.
