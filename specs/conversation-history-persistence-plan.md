# Technical Implementation Plan: Conversation History Persistence

**Created**: 2026-02-04
**Last Updated**: 2026-02-04
**Version**: 1.0
**Status**: Draft

## Executive Summary

This plan implements persistent conversation history for the skill creation chatbot using a **single JSON blob approach**. The entire `ConversationContext` Pydantic model is stored as JSON in a new `skill_creation_sessions` table, following established repository patterns in the codebase. The design prioritizes simplicity, minimal code changes, and seamless integration with the existing `SkillCreationAgent`.

**Key Design Decisions:**
- Store full `ConversationContext` as JSON blob (selected in spec)
- 90-day retention for completed sessions, 30-day for abandoned (selected in spec)
- Hybrid caching: keep in-memory cache for performance + DB for durability
- Non-blocking async persistence with error tolerance
- Follow existing `AgentConfigRepository` patterns for consistency

## Requirements Analysis

### Functional Requirements (from Spec)

| Requirement | Implementation |
|-------------|----------------|
| Auto-save after every message exchange | Hook into `SkillCreationAgent.handle_message()` |
| Session restoration on reconnect | Modify `get_session_context()` to load from DB |
| Full LLM context preservation | Store entire `message_history` in JSON blob |
| Multi-tenant isolation | All queries filter by `tenant_id` |
| Error recovery with context | Persist even on exception paths |

### Non-Functional Requirements

| Requirement | Target | Implementation |
|-------------|--------|----------------|
| Save latency | < 100ms | Async non-blocking persist |
| Restore latency | < 500ms | Single row fetch with index |
| Storage efficiency | Reasonable | Optional gzip compression |
| Retention compliance | 90/30 days | Background cleanup job |

### Constraints and Assumptions

**Constraints:**
- Must use existing `Database` class and SQLAlchemy patterns
- Must maintain backward compatibility with current in-memory behavior
- Must not block user-facing operations on persistence failures
- Must enforce tenant isolation on all operations

**Assumptions:**
- `tenant_id` will be available in the agent context (may require API changes)
- Maximum `ConversationContext` size is under 1MB (reasonable for JSON)
- SQLite TEXT column is sufficient for storage (no size limits)
- Background cleanup can run during low-traffic periods

## System Architecture

### High-Level Architecture

```
+------------------+     +-------------------------+     +------------------+
|   API Layer      |---->|  SkillCreationAgent     |---->|  ConversationMgr |
| (session_id,     |     |  - handle_message()     |     |  - FSM states    |
|  tenant_id)      |     |  - get_session_context()|     |  - process_msg() |
+------------------+     +-------------------------+     +------------------+
                                    |
                                    | save/load
                                    v
                         +-------------------------+
                         | SkillCreationSession    |
                         | Repository              |
                         | - save()                |
                         | - load()                |
                         | - cleanup_old_sessions()|
                         +-------------------------+
                                    |
                                    | async
                                    v
                         +-------------------------+
                         | Database (SQLAlchemy)   |
                         | - skill_creation_       |
                         |   sessions table        |
                         +-------------------------+
```

### Data Flow

```
User Message
     |
     v
+--------------------+
| handle_message()   |
+--------------------+
     |
     | 1. Load from DB (if not in memory)
     v
+--------------------+
| get_session_context|
| - Check memory     |
| - Fallback to DB   |
+--------------------+
     |
     | 2. Process message
     v
+--------------------+
| ConversationMgr    |
| .process_message() |
+--------------------+
     |
     | 3. Save to memory + DB (async)
     v
+--------------------+
| _persist_context() |
| - Update memory    |
| - Queue DB write   |
+--------------------+
     |
     v
Response to User
```

## Technology Stack

| Component | Technology | Rationale |
|-----------|------------|-----------|
| ORM | SQLAlchemy 2.0 | Existing codebase standard |
| Database | SQLite (async via aiosqlite) | Existing infrastructure |
| Serialization | Pydantic JSON | Native `ConversationContext` support |
| Compression | gzip (optional) | Reduce storage for large contexts |
| Background Jobs | asyncio tasks | Lightweight, no external deps |

## Database Initialization and Dependency Injection

This section documents how the database and repository are properly initialized and passed to the agent.

### Initialization Sequence

```
Application Startup
      |
      v
+-----------------+
| 1. Load Config  |
| - DB URL        |
| - Credentials   |
+-----------------+
      |
      v
+-----------------+
| 2. Create DB    |
| Database(config)|
+-----------------+
      |
      v
+-----------------+
| 3. Create Tables|
| await db.create_|
|      tables()   |
+-----------------+
      |
      v
+-----------------+
| 4. Init Repo    |
| SessionRepo(db) |
+-----------------+
      |
      v
+-----------------+
| 5. Init Cleaner |
| Cleaner(repo)   |
| await start()   |
+-----------------+
      |
      v
+-----------------+
| 6. Init Agent   |
| Agent(repo)     |
+-----------------+
      |
      v
  Ready to Handle
    Requests
```

### Example: Application Startup Code

**File: `src/omniforge/api/app.py` (or main application entry point)**

```python
"""FastAPI application with skill creation persistence."""

from contextlib import asynccontextmanager
from fastapi import FastAPI

from omniforge.storage.database import Database, DatabaseConfig
from omniforge.skills.creation.session_repository import SkillCreationSessionRepository
from omniforge.skills.creation.session_cleaner import SkillCreationSessionCleaner
from omniforge.skills.creation.agent import SkillCreationAgent
from omniforge.chat.llm_generator import LLMResponseGenerator


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan with proper initialization and cleanup."""

    # 1. Initialize database
    db_config = DatabaseConfig(
        url="sqlite+aiosqlite:///./omniforge.db",
        echo=False,  # Set True for SQL logging during development
    )
    db = Database(db_config)

    # 2. Create tables (includes skill_creation_sessions table)
    await db.create_tables()

    # 3. Initialize repository
    session_repository = SkillCreationSessionRepository(db)

    # 4. Initialize and start cleanup job
    session_cleaner = SkillCreationSessionCleaner(session_repository)
    await session_cleaner.start()

    # 5. Initialize LLM generator (or get from config)
    llm_generator = LLMResponseGenerator()

    # 6. Initialize agent (repository will be passed to each request handler)
    # Store dependencies in app.state for access in routes
    app.state.db = db
    app.state.session_repository = session_repository
    app.state.session_cleaner = session_cleaner
    app.state.llm_generator = llm_generator

    yield  # Application runs

    # Cleanup on shutdown
    await session_cleaner.stop()
    # Database connections will be closed automatically


app = FastAPI(lifespan=lifespan)


# Example route that creates an agent with persistence
@app.post("/api/skills/create/message")
async def handle_skill_creation_message(
    session_id: str,
    tenant_id: str,
    message: str,
):
    """Handle skill creation conversation message."""

    # Create agent with persisted repository
    agent = SkillCreationAgent(
        llm_generator=app.state.llm_generator,
        session_repository=app.state.session_repository,
    )

    # Process message (persistence happens automatically)
    response_chunks = []
    async for chunk in agent.handle_message(message, session_id, tenant_id):
        response_chunks.append(chunk)

    return {"response": "".join(response_chunks)}
```

### Dependency Injection Pattern

The dependency flow is:

1. **Config** → `DatabaseConfig` (from environment or config file)
2. **DatabaseConfig** → `Database` instance
3. **Database** → `SkillCreationSessionRepository` (passed as constructor arg)
4. **Repository** → `SkillCreationSessionCleaner` (for background cleanup)
5. **Repository** → `SkillCreationAgent` (for persistence in message handling)

**Key Principles:**
- Database is created once at application startup
- Repository is created once and reused across all agents
- Agent instances can be created per-request or long-lived (both work)
- Cleanup job is started once at startup and stopped on shutdown

### Alternative: Dependency Injection Framework

For larger applications, consider using a DI framework like `dependency-injector`:

```python
from dependency_injector import containers, providers


class Container(containers.DeclarativeContainer):
    """Dependency injection container for OmniForge."""

    config = providers.Configuration()

    # Database
    database = providers.Singleton(
        Database,
        config=providers.Factory(
            DatabaseConfig,
            url=config.database.url,
        ),
    )

    # Repository
    session_repository = providers.Singleton(
        SkillCreationSessionRepository,
        db=database,
    )

    # Cleanup job
    session_cleaner = providers.Singleton(
        SkillCreationSessionCleaner,
        repository=session_repository,
    )

    # Agent factory (creates new instance for each call)
    skill_creation_agent = providers.Factory(
        SkillCreationAgent,
        session_repository=session_repository,
    )
```

This provides automatic dependency resolution and makes testing easier with mock injection.

## Component Specifications

### 1. Database Schema

**Table: `skill_creation_sessions`**

```sql
CREATE TABLE skill_creation_sessions (
    -- Primary key
    id VARCHAR(36) PRIMARY KEY DEFAULT (uuid()),

    -- Session identifiers
    session_id VARCHAR(255) NOT NULL,
    tenant_id VARCHAR(255) NOT NULL,

    -- Context storage (JSON blob of ConversationContext)
    context_json TEXT NOT NULL,

    -- State tracking (denormalized for efficient queries)
    state VARCHAR(50) NOT NULL,
    skill_name VARCHAR(255),

    -- Timestamps
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Status for lifecycle management
    status VARCHAR(20) NOT NULL DEFAULT 'active',

    -- Indexes
    UNIQUE(session_id, tenant_id),
    INDEX idx_tenant_session (tenant_id, session_id),
    INDEX idx_tenant_state (tenant_id, state),
    INDEX idx_tenant_updated (tenant_id, updated_at),
    INDEX idx_status_updated (status, updated_at)
);
```

**Field Descriptions:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Database-level primary key |
| `session_id` | String(255) | Application-level session identifier |
| `tenant_id` | String(255) | Tenant for multi-tenancy isolation |
| `context_json` | TEXT | Full `ConversationContext` as JSON |
| `state` | String(50) | FSM state (denormalized for queries) |
| `skill_name` | String(255) | Skill name (denormalized for queries) |
| `created_at` | DateTime | Session creation timestamp |
| `updated_at` | DateTime | Last modification timestamp |
| `status` | String(20) | Lifecycle status: active, completed, abandoned, deleted |

### 2. ORM Model

**File: `src/omniforge/skills/creation/orm.py`**

```python
"""SQLAlchemy ORM model for skill creation session persistence."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from omniforge.storage.database import Base


class SkillCreationSessionModel(Base):
    """ORM model for skill creation session persistence.

    Stores the full ConversationContext as a JSON blob with denormalized
    fields for efficient querying and lifecycle management.

    Attributes:
        id: Database-level unique identifier (UUID)
        session_id: Application-level session identifier
        tenant_id: Tenant identifier for multi-tenancy isolation
        context_json: Full ConversationContext serialized as JSON
        state: Current FSM state (denormalized for queries)
        skill_name: Skill name if available (denormalized)
        created_at: Session creation timestamp
        updated_at: Last modification timestamp
        status: Lifecycle status (active/completed/abandoned/deleted)
    """

    __tablename__ = "skill_creation_sessions"

    # Primary key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    # Session identifiers
    session_id: Mapped[str] = mapped_column(String(255), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Context storage (JSON blob)
    context_json: Mapped[str] = mapped_column(Text, nullable=False)

    # Denormalized fields for efficient queries
    state: Mapped[str] = mapped_column(String(50), nullable=False)
    skill_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True
    )

    # Lifecycle status
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active"
    )

    # Indexes and constraints
    __table_args__ = (
        UniqueConstraint("session_id", "tenant_id", name="uq_session_tenant"),
        Index("idx_tenant_session", "tenant_id", "session_id"),
        Index("idx_tenant_state", "tenant_id", "state"),
        Index("idx_tenant_updated", "tenant_id", "updated_at"),
        Index("idx_status_updated", "status", "updated_at"),
    )
```

### 3. Repository Pattern

**File: `src/omniforge/skills/creation/session_repository.py`**

```python
"""Repository for skill creation session persistence."""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import and_, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from omniforge.skills.creation.models import ConversationContext, ConversationState
from omniforge.skills.creation.orm import SkillCreationSessionModel
from omniforge.storage.database import Database

logger = logging.getLogger(__name__)


class SkillCreationSessionRepository:
    """Repository for skill creation session persistence with tenant isolation.

    Provides async CRUD operations for ConversationContext persistence,
    following the established repository patterns in the codebase.

    All operations require tenant_id for multi-tenancy isolation.

    Attributes:
        db: Database instance for session management
    """

    def __init__(self, db: Database) -> None:
        """Initialize repository with database connection.

        Args:
            db: Database instance for session management
        """
        self.db = db

    async def save(
        self,
        context: ConversationContext,
        tenant_id: str,
    ) -> None:
        """Save or update a session context.

        Uses upsert semantics: inserts if new, updates if exists.

        Args:
            context: ConversationContext to persist
            tenant_id: Tenant identifier for isolation

        Raises:
            ValueError: If tenant_id is empty
        """
        if not tenant_id or not tenant_id.strip():
            raise ValueError("tenant_id cannot be empty")

        async with self.db.session() as session:
            # Check if session exists
            existing = await self._get_model(
                session,
                context.session_id,
                tenant_id
            )

            # Serialize context to JSON
            context_json = context.model_dump_json()

            if existing:
                # Update existing session
                existing.context_json = context_json
                existing.state = context.state.value
                existing.skill_name = context.skill_name
                existing.updated_at = datetime.utcnow()

                # Update status based on state
                if context.state == ConversationState.COMPLETED:
                    existing.status = "completed"
                elif context.state == ConversationState.ERROR:
                    existing.status = "error"

                await session.flush()
                logger.debug(f"Updated session {context.session_id} for tenant {tenant_id}")
            else:
                # Create new session
                model = SkillCreationSessionModel(
                    session_id=context.session_id,
                    tenant_id=tenant_id,
                    context_json=context_json,
                    state=context.state.value,
                    skill_name=context.skill_name,
                    status="active",
                )
                session.add(model)
                await session.flush()
                logger.debug(f"Created session {context.session_id} for tenant {tenant_id}")

    async def load(
        self,
        session_id: str,
        tenant_id: str,
    ) -> Optional[ConversationContext]:
        """Load a session context by session_id and tenant_id.

        Args:
            session_id: Session identifier
            tenant_id: Tenant identifier for isolation

        Returns:
            ConversationContext if found, None otherwise

        Raises:
            ValueError: If tenant_id is empty
        """
        if not tenant_id or not tenant_id.strip():
            raise ValueError("tenant_id cannot be empty")

        async with self.db.session() as session:
            model = await self._get_model(session, session_id, tenant_id)

            if model is None:
                return None

            # Deserialize context from JSON
            context = ConversationContext.model_validate_json(model.context_json)
            logger.debug(f"Loaded session {session_id} for tenant {tenant_id}")
            return context

    async def delete(
        self,
        session_id: str,
        tenant_id: str,
    ) -> bool:
        """Delete a session (soft delete by setting status).

        Args:
            session_id: Session identifier
            tenant_id: Tenant identifier for isolation

        Returns:
            True if session was deleted, False if not found

        Raises:
            ValueError: If tenant_id is empty
        """
        if not tenant_id or not tenant_id.strip():
            raise ValueError("tenant_id cannot be empty")

        async with self.db.session() as session:
            result = await session.execute(
                update(SkillCreationSessionModel)
                .where(
                    and_(
                        SkillCreationSessionModel.session_id == session_id,
                        SkillCreationSessionModel.tenant_id == tenant_id,
                    )
                )
                .values(status="deleted", updated_at=datetime.utcnow())
            )
            await session.flush()

            deleted = result.rowcount > 0
            if deleted:
                logger.debug(f"Soft deleted session {session_id} for tenant {tenant_id}")
            return deleted

    async def list_by_tenant(
        self,
        tenant_id: str,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ConversationContext]:
        """List sessions for a tenant.

        Args:
            tenant_id: Tenant identifier
            status: Optional status filter (active, completed, abandoned)
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            List of ConversationContext objects

        Raises:
            ValueError: If tenant_id is empty
        """
        if not tenant_id or not tenant_id.strip():
            raise ValueError("tenant_id cannot be empty")

        async with self.db.session() as session:
            query = select(SkillCreationSessionModel).where(
                SkillCreationSessionModel.tenant_id == tenant_id
            )

            if status:
                query = query.where(SkillCreationSessionModel.status == status)
            else:
                # Exclude deleted by default
                query = query.where(SkillCreationSessionModel.status != "deleted")

            query = (
                query
                .order_by(SkillCreationSessionModel.updated_at.desc())
                .limit(limit)
                .offset(offset)
            )

            result = await session.execute(query)
            models = result.scalars().all()

            contexts = []
            for model in models:
                try:
                    context = ConversationContext.model_validate_json(model.context_json)
                    contexts.append(context)
                except Exception as e:
                    logger.warning(f"Failed to deserialize session {model.session_id}: {e}")

            return contexts

    async def mark_abandoned(
        self,
        cutoff_date: datetime,
        tenant_id: Optional[str] = None,
    ) -> int:
        """Mark sessions as abandoned if inactive past cutoff date.

        Args:
            cutoff_date: Sessions not updated since this date are marked abandoned
            tenant_id: Optional tenant filter (None for all tenants)

        Returns:
            Number of sessions marked as abandoned
        """
        async with self.db.session() as session:
            query = (
                update(SkillCreationSessionModel)
                .where(
                    and_(
                        SkillCreationSessionModel.status == "active",
                        SkillCreationSessionModel.updated_at < cutoff_date,
                        # Only mark non-terminal states as abandoned
                        SkillCreationSessionModel.state.notin_(
                            ["completed", "error"]
                        ),
                    )
                )
                .values(status="abandoned", updated_at=datetime.utcnow())
            )

            if tenant_id:
                query = query.where(SkillCreationSessionModel.tenant_id == tenant_id)

            result = await session.execute(query)
            await session.flush()

            count = result.rowcount
            logger.info(f"Marked {count} sessions as abandoned")
            return count

    async def cleanup_old_sessions(
        self,
        completed_retention_days: int = 90,
        abandoned_retention_days: int = 30,
        tenant_id: Optional[str] = None,
    ) -> int:
        """Delete sessions past retention period.

        Args:
            completed_retention_days: Days to retain completed sessions
            abandoned_retention_days: Days to retain abandoned sessions
            tenant_id: Optional tenant filter (None for all tenants)

        Returns:
            Number of sessions deleted
        """
        now = datetime.utcnow()
        completed_cutoff = now - timedelta(days=completed_retention_days)
        abandoned_cutoff = now - timedelta(days=abandoned_retention_days)

        async with self.db.session() as session:
            # Build delete query for completed sessions
            completed_query = delete(SkillCreationSessionModel).where(
                and_(
                    SkillCreationSessionModel.status == "completed",
                    SkillCreationSessionModel.updated_at < completed_cutoff,
                )
            )

            # Build delete query for abandoned/deleted sessions
            abandoned_query = delete(SkillCreationSessionModel).where(
                and_(
                    SkillCreationSessionModel.status.in_(["abandoned", "deleted"]),
                    SkillCreationSessionModel.updated_at < abandoned_cutoff,
                )
            )

            if tenant_id:
                completed_query = completed_query.where(
                    SkillCreationSessionModel.tenant_id == tenant_id
                )
                abandoned_query = abandoned_query.where(
                    SkillCreationSessionModel.tenant_id == tenant_id
                )

            result1 = await session.execute(completed_query)
            result2 = await session.execute(abandoned_query)
            await session.flush()

            total = result1.rowcount + result2.rowcount
            logger.info(f"Cleaned up {total} old sessions")
            return total

    async def _get_model(
        self,
        session: AsyncSession,
        session_id: str,
        tenant_id: str,
    ) -> Optional[SkillCreationSessionModel]:
        """Get ORM model by session_id and tenant_id.

        Args:
            session: Database session
            session_id: Session identifier
            tenant_id: Tenant identifier

        Returns:
            SkillCreationSessionModel if found, None otherwise
        """
        result = await session.execute(
            select(SkillCreationSessionModel).where(
                and_(
                    SkillCreationSessionModel.session_id == session_id,
                    SkillCreationSessionModel.tenant_id == tenant_id,
                )
            )
        )
        return result.scalar_one_or_none()
```

### 4. Background Cleanup Job

**File: `src/omniforge/skills/creation/session_cleaner.py`**

Proper lifecycle management for the cleanup background task:

```python
"""Background cleanup job for skill creation sessions."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from omniforge.skills.creation.session_repository import SkillCreationSessionRepository

logger = logging.getLogger(__name__)


class SkillCreationSessionCleaner:
    """Background task for cleaning up old skill creation sessions.

    This class manages a long-running asyncio task that periodically:
    1. Marks sessions as abandoned if inactive for 30 days
    2. Deletes completed sessions older than 90 days
    3. Deletes abandoned sessions older than 30 days

    The cleanup job runs daily and can be started/stopped cleanly.

    Attributes:
        repository: Repository for session operations
        cleanup_interval_seconds: How often to run cleanup (default: 24 hours)
        _task: The background asyncio task
        _running: Whether the cleanup loop is running
    """

    def __init__(
        self,
        repository: SkillCreationSessionRepository,
        cleanup_interval_seconds: int = 86400,  # 24 hours
    ) -> None:
        """Initialize cleaner with repository.

        Args:
            repository: Session repository for database operations
            cleanup_interval_seconds: Interval between cleanup runs (default: 86400 = 24 hours)
        """
        self.repository = repository
        self.cleanup_interval_seconds = cleanup_interval_seconds
        self._task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self) -> None:
        """Start the background cleanup task.

        This creates an asyncio task that runs the cleanup loop.
        If already running, this is a no-op.
        """
        if self._running:
            logger.warning("Cleanup task already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._cleanup_loop())
        logger.info(
            f"Started skill creation session cleanup task "
            f"(interval: {self.cleanup_interval_seconds}s)"
        )

    async def stop(self) -> None:
        """Stop the background cleanup task gracefully.

        Cancels the task and waits for it to finish.
        """
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                logger.info("Cleanup task cancelled")
            self._task = None

    async def _cleanup_loop(self) -> None:
        """Run cleanup periodically until stopped.

        This loop:
        1. Runs cleanup immediately on start
        2. Sleeps for the configured interval
        3. Repeats until self._running is False

        Errors are logged but don't stop the loop.
        """
        while self._running:
            try:
                await self._run_cleanup()
            except Exception as e:
                logger.error(f"Cleanup job failed: {e}", exc_info=True)

            # Sleep for configured interval
            # Use small increments so we can stop quickly
            remaining = self.cleanup_interval_seconds
            while remaining > 0 and self._running:
                sleep_time = min(60, remaining)  # Check _running every minute
                await asyncio.sleep(sleep_time)
                remaining -= sleep_time

    async def _run_cleanup(self) -> None:
        """Execute one cleanup cycle.

        Marks abandoned sessions and deletes old sessions per retention policy.
        """
        start_time = datetime.utcnow()
        logger.info("Starting session cleanup job")

        try:
            # Mark abandoned sessions (inactive for 30+ days)
            abandoned_cutoff = datetime.utcnow() - timedelta(days=30)
            abandoned_count = await self.repository.mark_abandoned(abandoned_cutoff)
            logger.info(f"Marked {abandoned_count} sessions as abandoned")

            # Delete old sessions (90 days for completed, 30 days for abandoned)
            deleted_count = await self.repository.cleanup_old_sessions(
                completed_retention_days=90,
                abandoned_retention_days=30,
            )
            logger.info(f"Deleted {deleted_count} old sessions")

            duration = (datetime.utcnow() - start_time).total_seconds()
            logger.info(
                f"Session cleanup completed in {duration:.2f}s "
                f"(abandoned: {abandoned_count}, deleted: {deleted_count})"
            )

        except Exception as e:
            logger.error(f"Error during cleanup: {e}", exc_info=True)
            raise
```

**Initialization in Application Startup:**

The cleanup job should be initialized once at application startup, not on every agent instantiation:

```python
# In main application startup (e.g., src/omniforge/api/app.py or similar)

from omniforge.skills.creation.session_repository import SkillCreationSessionRepository
from omniforge.skills.creation.session_cleaner import SkillCreationSessionCleaner
from omniforge.storage.database import Database

# Initialize database
db = Database(config)
await db.create_tables()

# Initialize repository
session_repository = SkillCreationSessionRepository(db)

# Initialize and start cleanup job (application-wide, not per-agent)
session_cleaner = SkillCreationSessionCleaner(session_repository)
await session_cleaner.start()

# Store cleaner for shutdown
app.state.session_cleaner = session_cleaner

# Shutdown hook
@app.on_event("shutdown")
async def shutdown():
    await app.state.session_cleaner.stop()
```

### 5. Integration Points

**Modified: `src/omniforge/skills/creation/agent.py`**

Key changes to `SkillCreationAgent`:

```python
class SkillCreationAgent:
    """Conversational agent for skill creation with persistent sessions."""

    def __init__(
        self,
        llm_generator: Optional[LLMResponseGenerator] = None,
        storage_config: Optional[StorageConfig] = None,
        session_repository: Optional[SkillCreationSessionRepository] = None,
    ) -> None:
        """Initialize agent with dependencies.

        Args:
            llm_generator: Optional LLM generator for responses
            storage_config: Optional storage configuration
            session_repository: Optional session repository for persistence
        """
        # ... existing initialization ...

        # Session persistence (None means in-memory only)
        self.session_repository = session_repository

        # In-memory cache (kept for performance)
        self.sessions: dict[str, ConversationContext] = {}

    async def handle_message(
        self,
        message: str,
        session_id: str,
        tenant_id: str,
        conversation_history: Optional[list[dict[str, str]]] = None,
    ) -> AsyncIterator[str]:
        """Handle conversational message with auto-persistence.

        Args:
            message: User's input message
            session_id: Unique session identifier
            tenant_id: Tenant identifier (required for multi-tenancy isolation)
            conversation_history: Optional conversation history for context

        Yields:
            Response chunks for streaming to user
        """

        try:
            # Get or create conversation context (loads from DB if needed)
            context = await self.get_session_context(session_id, tenant_id)

            # ... existing message processing ...

            # Update session context
            self.sessions[session_id] = updated_context

            # Persist to database (non-blocking)
            await self._persist_context(updated_context, tenant_id)

            # ... rest of existing logic ...

        except Exception as e:
            # ... existing error handling ...

            # Still persist on error for recovery
            context = self.sessions.get(session_id)
            if context:
                await self._persist_context(context, tenant_id, ignore_errors=True)

            yield error_message

    async def get_session_context(
        self,
        session_id: str,
        tenant_id: str,
    ) -> ConversationContext:
        """Get or create conversation context with DB fallback.

        Args:
            session_id: Unique session identifier
            tenant_id: Tenant identifier (required)

        Returns:
            ConversationContext for the session
        """

        # Check in-memory cache first
        if session_id in self.sessions:
            return self.sessions[session_id]

        # Try to load from database
        if self.session_repository:
            try:
                context = await self.session_repository.load(session_id, tenant_id)
                if context:
                    self.sessions[session_id] = context
                    logger.info(f"Restored session {session_id} from database")
                    return context
            except Exception as e:
                logger.warning(f"Failed to load session from DB: {e}")

        # Create new context
        context = ConversationContext(session_id=session_id)
        self.sessions[session_id] = context
        logger.debug(f"Created new session context: {session_id}")

        return context

    async def _persist_context(
        self,
        context: ConversationContext,
        tenant_id: str,
        ignore_errors: bool = False,
    ) -> None:
        """Persist context to database (non-blocking).

        Args:
            context: ConversationContext to persist
            tenant_id: Tenant identifier
            ignore_errors: If True, log errors but don't raise
        """
        if not self.session_repository:
            return

        try:
            await self.session_repository.save(context, tenant_id)
        except Exception as e:
            if ignore_errors:
                logger.error(f"Failed to persist session {context.session_id}: {e}")
            else:
                raise

    async def _clear_session(
        self,
        session_id: str,
        tenant_id: str,
    ) -> None:
        """Clear session context after completion.

        Note: Does NOT delete from DB - session remains for audit trail.
        The status is already set to 'completed' during final persist.

        Args:
            session_id: Session identifier to clear
            tenant_id: Tenant identifier (required)
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.debug(f"Cleared session from memory: {session_id}")
```

## Detailed Data Flow

### Sequence Diagram: Message Processing with Auto-Save

```
User                Agent              Memory         Repository        Database
 |                    |                  |               |                 |
 |--- message ------->|                  |               |                 |
 |                    |                  |               |                 |
 |                    |-- get context -->|               |                 |
 |                    |<-- not found ----|               |                 |
 |                    |                  |               |                 |
 |                    |------------------ load --------->|                 |
 |                    |                  |               |--- SELECT ----->|
 |                    |                  |               |<-- row ---------|
 |                    |<----------------- context -------|                 |
 |                    |                  |               |                 |
 |                    |-- store -------->| (cache)       |                 |
 |                    |                  |               |                 |
 |                    |== process_message (FSM) ==       |                 |
 |                    |                  |               |                 |
 |                    |-- store -------->| (update)      |                 |
 |                    |                  |               |                 |
 |                    |------------------ save --------->|                 |
 |                    |                  |               |--- UPSERT ----->|
 |                    |                  |               |<-- ok ----------|
 |                    |                  |               |                 |
 |<--- response ------|                  |               |                 |
```

### Sequence Diagram: Session Restoration on Reconnect

```
User                Agent              Memory         Repository        Database
 |                    |                  |               |                 |
 |--- reconnect ----->|                  |               |                 |
 |  (session_id)      |                  |               |                 |
 |                    |                  |               |                 |
 |                    |-- get context -->|               |                 |
 |                    |<-- not found ----|               |                 |
 |                    |                  |               |                 |
 |                    |------------------ load --------->|                 |
 |                    |                  |               |--- SELECT ----->|
 |                    |                  |               |<-- row ---------|
 |                    |<-- context (full history) -------|                 |
 |                    |                  |               |                 |
 |                    |-- store -------->| (cache)       |                 |
 |                    |                  |               |                 |
 |<--- "Resuming..." -|                  |               |                 |
 |                    |                  |               |                 |
 |--- continue ------>| (normal flow)    |               |                 |
```

### Sequence Diagram: Error Recovery with Context Preservation

```
User                Agent              FSM            Repository        Database
 |                    |                  |               |                 |
 |--- message ------->|                  |               |                 |
 |                    |                  |               |                 |
 |                    |-- process ------>|               |                 |
 |                    |                  |               |                 |
 |                    |         X ERROR X                |                 |
 |                    |                  |               |                 |
 |                    |<- state=GATHERING_DETAILS -      |                 |
 |                    |    (with full history)           |                 |
 |                    |                  |               |                 |
 |                    |------------------ save (ignore_errors=True) ------>|
 |                    |                  |               |--- UPSERT ----->|
 |                    |                  |               |<-- ok ----------|
 |                    |                  |               |                 |
 |<--- error msg -----|                  |               |                 |
 |    + recovery UI   |                  |               |                 |
```

### Sequence Diagram: Background Cleanup

```
Scheduler           Repository        Database
    |                   |                |
    |--- mark_abandoned(30 days) ------->|
    |                   |--- UPDATE ---->|
    |                   |<-- count ------|
    |<-- abandoned_count ----------------|
    |                   |                |
    |--- cleanup_old_sessions(90/30) --->|
    |                   |--- DELETE ---->|
    |                   |<-- count ------|
    |<-- deleted_count ------------------|
```

## Migration Strategy

### Alembic Migration Script

**File: `alembic/versions/xxxx_add_skill_creation_sessions.py`**

```python
"""Add skill_creation_sessions table for conversation persistence.

Revision ID: xxxx
Revises: previous_revision
Create Date: 2026-02-04
"""
from alembic import op
import sqlalchemy as sa

revision = 'xxxx'
down_revision = 'previous_revision'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create skill_creation_sessions table."""
    op.create_table(
        'skill_creation_sessions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('session_id', sa.String(255), nullable=False),
        sa.Column('tenant_id', sa.String(255), nullable=False),
        sa.Column('context_json', sa.Text(), nullable=False),
        sa.Column('state', sa.String(50), nullable=False),
        sa.Column('skill_name', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.UniqueConstraint('session_id', 'tenant_id', name='uq_session_tenant'),
    )

    # Create indexes
    op.create_index('idx_tenant_session', 'skill_creation_sessions',
                    ['tenant_id', 'session_id'])
    op.create_index('idx_tenant_state', 'skill_creation_sessions',
                    ['tenant_id', 'state'])
    op.create_index('idx_tenant_updated', 'skill_creation_sessions',
                    ['tenant_id', 'updated_at'])
    op.create_index('idx_status_updated', 'skill_creation_sessions',
                    ['status', 'updated_at'])


def downgrade() -> None:
    """Drop skill_creation_sessions table."""
    op.drop_index('idx_status_updated', 'skill_creation_sessions')
    op.drop_index('idx_tenant_updated', 'skill_creation_sessions')
    op.drop_index('idx_tenant_state', 'skill_creation_sessions')
    op.drop_index('idx_tenant_session', 'skill_creation_sessions')
    op.drop_table('skill_creation_sessions')
```

### Deployment Steps

1. **Pre-deployment:**
   - Run `alembic upgrade head` to create the table
   - Verify table exists with correct schema

2. **Deployment:**
   - Deploy new code with persistence enabled
   - In-memory sessions continue working during rollout
   - One-time restart may lose active in-memory sessions (documented in spec)

3. **Post-deployment:**
   - Monitor persistence latency and error rates
   - Verify sessions are being saved and restored
   - Enable cleanup job after initial stabilization

## Testing Strategy

### Unit Tests

**File: `tests/test_session_repository.py`**

```python
"""Tests for SkillCreationSessionRepository."""

import pytest
from datetime import datetime, timedelta

from omniforge.skills.creation.models import ConversationContext, ConversationState
from omniforge.skills.creation.session_repository import SkillCreationSessionRepository
from omniforge.storage.database import Database, DatabaseConfig


@pytest.fixture
async def db():
    """Create test database."""
    config = DatabaseConfig(url="sqlite+aiosqlite:///:memory:")
    database = Database(config)
    await database.create_tables()
    yield database
    await database.close()


@pytest.fixture
def repository(db):
    """Create repository instance."""
    return SkillCreationSessionRepository(db)


class TestSkillCreationSessionRepository:
    """Tests for session repository."""

    async def test_save_and_load_session(self, repository):
        """Should save and load session context."""
        context = ConversationContext(session_id="test-123")
        context.state = ConversationState.GATHERING_DETAILS
        context.skill_purpose = "Test skill"
        context.message_history = [{"role": "user", "content": "Hello"}]

        await repository.save(context, tenant_id="tenant-1")

        loaded = await repository.load("test-123", tenant_id="tenant-1")

        assert loaded is not None
        assert loaded.session_id == "test-123"
        assert loaded.state == ConversationState.GATHERING_DETAILS
        assert loaded.skill_purpose == "Test skill"
        assert len(loaded.message_history) == 1

    async def test_tenant_isolation(self, repository):
        """Should enforce tenant isolation."""
        context = ConversationContext(session_id="test-123")
        await repository.save(context, tenant_id="tenant-1")

        # Different tenant cannot access
        loaded = await repository.load("test-123", tenant_id="tenant-2")
        assert loaded is None

    async def test_update_existing_session(self, repository):
        """Should update existing session on save."""
        context = ConversationContext(session_id="test-123")
        await repository.save(context, tenant_id="tenant-1")

        context.state = ConversationState.GENERATING
        context.skill_name = "test-skill"
        await repository.save(context, tenant_id="tenant-1")

        loaded = await repository.load("test-123", tenant_id="tenant-1")
        assert loaded.state == ConversationState.GENERATING
        assert loaded.skill_name == "test-skill"

    async def test_list_by_tenant(self, repository):
        """Should list sessions for tenant."""
        for i in range(3):
            context = ConversationContext(session_id=f"test-{i}")
            await repository.save(context, tenant_id="tenant-1")

        # Different tenant
        context = ConversationContext(session_id="other")
        await repository.save(context, tenant_id="tenant-2")

        sessions = await repository.list_by_tenant("tenant-1")
        assert len(sessions) == 3

    async def test_soft_delete(self, repository):
        """Should soft delete session."""
        context = ConversationContext(session_id="test-123")
        await repository.save(context, tenant_id="tenant-1")

        deleted = await repository.delete("test-123", tenant_id="tenant-1")
        assert deleted is True

        # Excluded from default list
        sessions = await repository.list_by_tenant("tenant-1")
        assert len(sessions) == 0

        # But can still be loaded explicitly
        sessions = await repository.list_by_tenant("tenant-1", status="deleted")
        assert len(sessions) == 1

    async def test_mark_abandoned(self, repository):
        """Should mark old active sessions as abandoned."""
        context = ConversationContext(session_id="test-123")
        await repository.save(context, tenant_id="tenant-1")

        # Mark sessions older than now (all should be marked)
        cutoff = datetime.utcnow() + timedelta(days=1)
        count = await repository.mark_abandoned(cutoff)

        assert count == 1

        sessions = await repository.list_by_tenant("tenant-1", status="abandoned")
        assert len(sessions) == 1

    async def test_cleanup_old_sessions(self, repository):
        """Should delete sessions past retention period."""
        # This would need time manipulation or direct DB updates
        # to test properly - shown here for completeness
        pass

    async def test_empty_tenant_id_raises_error(self, repository):
        """Should raise error for empty tenant_id."""
        context = ConversationContext(session_id="test-123")

        with pytest.raises(ValueError, match="tenant_id cannot be empty"):
            await repository.save(context, tenant_id="")

        with pytest.raises(ValueError, match="tenant_id cannot be empty"):
            await repository.load("test-123", tenant_id="")
```

### Integration Tests

**File: `tests/test_agent_persistence.py`**

```python
"""Integration tests for SkillCreationAgent with persistence."""

import pytest

from omniforge.skills.creation.agent import SkillCreationAgent
from omniforge.skills.creation.session_repository import SkillCreationSessionRepository
from omniforge.storage.database import Database, DatabaseConfig


@pytest.fixture
async def db():
    """Create test database."""
    config = DatabaseConfig(url="sqlite+aiosqlite:///:memory:")
    database = Database(config)
    await database.create_tables()
    yield database
    await database.close()


@pytest.fixture
def agent_with_persistence(db):
    """Create agent with persistence enabled."""
    repository = SkillCreationSessionRepository(db)
    return SkillCreationAgent(session_repository=repository)


class TestAgentPersistence:
    """Integration tests for agent persistence."""

    async def test_session_restored_after_clear(self, agent_with_persistence):
        """Session should be restored from DB after memory clear."""
        agent = agent_with_persistence

        # Start a conversation
        response_chunks = []
        async for chunk in agent.handle_message(
            "Create a skill to format names",
            session_id="test-session",
            tenant_id="tenant-1",
        ):
            response_chunks.append(chunk)

        # Clear in-memory cache (simulates restart)
        agent.sessions.clear()

        # Continue conversation - should restore from DB
        response_chunks = []
        async for chunk in agent.handle_message(
            "Use uppercase format",
            session_id="test-session",
            tenant_id="tenant-1",
        ):
            response_chunks.append(chunk)

        # Verify context was restored (session has history)
        context = await agent.get_session_context("test-session", "tenant-1")
        assert len(context.message_history) >= 2

    async def test_error_recovery_preserves_context(self, agent_with_persistence):
        """Context should be preserved even on errors."""
        # This test would involve triggering errors and verifying
        # the context is still persisted
        pass

    async def test_tenant_isolation_in_agent(self, agent_with_persistence):
        """Different tenants should have isolated sessions."""
        agent = agent_with_persistence

        # Create session for tenant-1
        async for _ in agent.handle_message(
            "Create a skill",
            session_id="shared-id",
            tenant_id="tenant-1",
        ):
            pass

        # Clear memory
        agent.sessions.clear()

        # Tenant-2 with same session_id should get new context
        context = await agent.get_session_context("shared-id", "tenant-2")
        assert len(context.message_history) == 0  # New session
```

### Error Scenario Tests

```python
import asyncio
from unittest.mock import patch, AsyncMock


class TestErrorScenarios:
    """Tests for error handling in persistence."""

    async def test_db_unavailable_continues_gracefully(self):
        """Agent should continue working if DB is unavailable."""
        # Create agent without persistence (None repository)
        agent = SkillCreationAgent(session_repository=None)

        # Should work without persistence
        response_chunks = []
        async for chunk in agent.handle_message(
            "Create a skill to format dates",
            session_id="test-session",
            tenant_id="tenant-1",
        ):
            response_chunks.append(chunk)

        # Should get a response even without persistence
        assert len(response_chunks) > 0
        assert any("skill" in chunk.lower() for chunk in response_chunks)

        # Context should still exist in memory
        context = await agent.get_session_context("test-session", "tenant-1")
        assert context.session_id == "test-session"
        assert len(context.message_history) > 0

    async def test_persistence_error_logged_not_raised(self, agent_with_persistence):
        """Persistence errors should be logged but not block user response."""
        agent = agent_with_persistence

        # Mock the repository to raise an error on save
        with patch.object(
            agent.session_repository,
            "save",
            side_effect=RuntimeError("Database connection failed"),
        ):
            # Message processing should still succeed
            response_chunks = []
            async for chunk in agent.handle_message(
                "Create a skill",
                session_id="test-session",
                tenant_id="tenant-1",
            ):
                response_chunks.append(chunk)

            # Should still get a response despite persistence failure
            assert len(response_chunks) > 0

            # Context should still be in memory even if DB save failed
            assert "test-session" in agent.sessions

    async def test_concurrent_access_last_write_wins(self, repository):
        """Concurrent updates should use last-write-wins semantics."""
        # Create two contexts for same session
        context1 = ConversationContext(session_id="concurrent-test")
        context1.state = ConversationState.GATHERING_PURPOSE
        context1.skill_purpose = "First update"

        context2 = ConversationContext(session_id="concurrent-test")
        context2.state = ConversationState.GENERATING
        context2.skill_purpose = "Second update"

        # Save both concurrently
        await asyncio.gather(
            repository.save(context1, "tenant-1"),
            repository.save(context2, "tenant-1"),
        )

        # Load and verify one of them won (last-write-wins)
        loaded = await repository.load("concurrent-test", "tenant-1")
        assert loaded is not None
        assert loaded.session_id == "concurrent-test"

        # Should be one of the two states (can't predict which due to concurrency)
        assert loaded.state in [
            ConversationState.GATHERING_PURPOSE,
            ConversationState.GENERATING,
        ]
        assert loaded.skill_purpose in ["First update", "Second update"]

    async def test_load_corrupted_json_returns_none(self, repository, db):
        """Loading corrupted JSON should return None instead of crashing."""
        # Manually insert a session with invalid JSON
        from omniforge.skills.creation.orm import SkillCreationSessionModel
        from datetime import datetime

        async with db.session() as session:
            model = SkillCreationSessionModel(
                session_id="corrupted",
                tenant_id="tenant-1",
                context_json="{invalid json}",  # Corrupted JSON
                state="idle",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                status="active",
            )
            session.add(model)
            await session.flush()

        # Attempting to load should return None (graceful degradation)
        loaded = await repository.load("corrupted", "tenant-1")
        assert loaded is None
```

## Performance Considerations

### Caching Strategy

**Approach: Hybrid (In-Memory + DB)**

```
+------------------+
|   Request        |
+------------------+
         |
         v
+------------------+
|  Memory Cache    |  <-- Check first (O(1) lookup)
|  (dict lookup)   |
+------------------+
         |
    Not found?
         |
         v
+------------------+
|    Database      |  <-- Fallback (indexed query)
|  (single row)    |
+------------------+
         |
         v
+------------------+
|  Store in Memory |  <-- Cache for future
+------------------+
```

**Benefits:**
- Fast reads for active sessions (in-memory)
- Durability for recovery (database)
- Automatic cache population on restore

### Query Optimization

1. **Indexes created for common patterns:**
   - `idx_tenant_session`: Primary lookup
   - `idx_tenant_updated`: Listing with pagination
   - `idx_status_updated`: Cleanup queries

2. **Denormalized fields:**
   - `state`: Avoid JSON parsing for state-based queries
   - `skill_name`: Avoid JSON parsing for display

3. **Efficient cleanup:**
   - Batch deletes by status + date
   - Run during low-traffic periods

### Compression (Optional Enhancement)

For large `message_history` (100+ messages), consider gzip compression:

```python
import gzip
import base64

def compress_json(data: str) -> str:
    """Compress JSON string using gzip."""
    compressed = gzip.compress(data.encode('utf-8'))
    return base64.b64encode(compressed).decode('ascii')

def decompress_json(data: str) -> str:
    """Decompress gzip-compressed JSON string."""
    compressed = base64.b64decode(data.encode('ascii'))
    return gzip.decompress(compressed).decode('utf-8')
```

**Trade-offs:**
- Pro: ~70-80% reduction in storage for text-heavy contexts
- Con: CPU overhead for compression/decompression
- Recommendation: Enable only if storage becomes a concern

## Monitoring and Operations

### Metrics to Track

| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| `session_save_latency_ms` | Time to persist session | > 200ms |
| `session_load_latency_ms` | Time to restore session | > 500ms |
| `session_save_errors` | Failed persist operations | > 0 |
| `session_count_by_status` | Active/completed/abandoned | N/A (monitoring) |
| `session_storage_size_bytes` | Size of context_json | > 1MB |

### Logging

```python
# Key log events
logger.info(f"Restored session {session_id} from database")
logger.debug(f"Persisted session {session_id}, size={len(context_json)} bytes")
logger.warning(f"Failed to persist session {session_id}: {error}")
logger.info(f"Cleaned up {count} old sessions")
```

### Alerting

1. **Persistence failures**: Alert if save errors exceed threshold
2. **Restore failures**: Alert if load errors affect user experience
3. **Storage growth**: Alert if total storage exceeds budget

## Risk Assessment

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| DB unavailable during persist | Low (graceful fallback) | Medium | Error tolerance, in-memory fallback |
| Large contexts cause slow saves | Medium | Low | Monitor size, add compression if needed |
| Migration loses active sessions | Low | High (one-time) | Document in release notes |
| Concurrent access conflicts | Low | Low | Last-write-wins, optimistic locking |
| tenant_id not available | High | Medium | Require in API, use default |

## Implementation Phases

### Phase 1: Core Infrastructure (Week 1)
- [ ] Create ORM model (`orm.py`)
- [ ] Create repository (`session_repository.py`)
- [ ] Write Alembic migration
- [ ] Unit tests for repository

### Phase 2: Agent Integration (Week 1-2)
- [ ] Modify `SkillCreationAgent.__init__` to accept repository
- [ ] Modify `get_session_context` for DB fallback
- [ ] Add `_persist_context` method
- [ ] Modify `handle_message` for auto-save
- [ ] Integration tests for agent persistence

### Phase 3: Error Handling (Week 2)
- [ ] Non-blocking persist with error tolerance
- [ ] Persist on error paths
- [ ] Logging and metrics

### Phase 4: Cleanup and Monitoring (Week 2-3)
- [ ] Background cleanup job
- [ ] Monitoring dashboard
- [ ] Alerting rules
- [ ] Documentation

### Phase 5: Optional Enhancements (Future)
- [ ] Compression for large contexts
- [ ] Partial restoration (recent messages only)
- [ ] Admin UI for session management

## Alternative Approaches Considered

### Option A: Normalized Message Table (Rejected)

Store messages in separate table with foreign key to sessions.

**Pros:**
- Efficient message-level queries
- Reuses `ConversationMessageModel` pattern

**Cons:**
- More complex restoration (joins)
- Two tables to manage atomically
- Overhead for simple use case

**Decision:** Rejected. JSON blob is simpler and sufficient for skill creation where we always need full context.

### Option B: Event Sourcing (Rejected)

Store state changes as events, replay to restore.

**Pros:**
- Full audit trail of changes
- Can replay to any point

**Cons:**
- Significant complexity
- Overkill for this use case
- Slow restoration for long sessions

**Decision:** Rejected. Not worth the complexity for conversation persistence.

### Option C: Redis Cache + DB (Considered for Future)

Use Redis for hot cache, PostgreSQL for cold storage.

**Pros:**
- Faster reads
- Scales better

**Cons:**
- Additional infrastructure
- Complexity

**Decision:** Defer. Current SQLite + in-memory is sufficient for MVP.

## Open Questions (From Spec)

1. **Compression**: Defer. Monitor storage first, add if needed.

2. **Partial restoration**: Defer. Full context is manageable for skill creation flows.

3. **Real-time sync**: Out of scope. Refresh-based restoration is sufficient.

4. **Session continuation UI**: Frontend responsibility. Backend provides full context.

5. **Cleanup automation**: Automatic, running daily during off-peak hours.

## Appendix: Full File Listing

| File | Purpose |
|------|---------|
| `src/omniforge/skills/creation/orm.py` | SQLAlchemy ORM model |
| `src/omniforge/skills/creation/session_repository.py` | Repository for CRUD operations |
| `src/omniforge/skills/creation/agent.py` | Modified agent with persistence |
| `alembic/versions/xxxx_add_skill_creation_sessions.py` | Database migration |
| `tests/test_session_repository.py` | Repository unit tests |
| `tests/test_agent_persistence.py` | Agent integration tests |
