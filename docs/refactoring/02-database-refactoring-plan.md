# Refactoring Plan: Database (OCP Violation)

## Current State Analysis

### File: `src/omniforge/storage/database.py`

### Problem Summary
`Database` class violates Open/Closed Principle by:

1. **Hardcoded sync/async branching** (lines 83-120)
2. **Cannot extend without modification** - New session patterns require changing code
3. **Mixed responsibilities** - Handles engine creation, session management, and runtime mode detection

### Current Architecture

```python
class Database:
    """Database connection and session management."""

    def __init__(self, url: str, echo: bool = False):
        self._url = url
        self._echo = echo
        self._engine: Optional[Engine] = None
        self._async_engine: Optional[AsyncEngine] = None

    def _initialize_engines(self) -> None:
        """Initialize BOTH sync and async engines."""
        # Creates both engines regardless of which is needed
        # Lines 59-79

    @asynccontextmanager
    async def session(self):
        """Get database session - sync or async depending on context.

        Lines 104-121: Complex runtime detection
        """
        if self._is_async_context():
            # Async path
            async with AsyncSession(...) as session:
                yield session
        else:
            # Sync path (ERROR: Can't use sync in async context)
            with Session(...) as session:
                yield session

    def _is_async_context(self) -> bool:
        """Runtime detection of async context.

        Lines 83-99: Fragile detection logic
        """
        try:
            asyncio.current_task()
            return True
        except RuntimeError:
            return False
```

### Impact Metrics
- **Cyclomatic Complexity**: 12+ (session method)
- **Runtime Overhead**: Context detection on every session creation
- **Extensibility**: Zero (new patterns require code changes)
- **Type Safety**: Low (Union[Session, AsyncSession] loses type information)

---

## Refactoring Strategy

### Phase 1: Separate Sync/Async Implementations (2-3 hours)

#### Step 1.1: Create Database Interface

**New File**: `src/omniforge/storage/database_protocol.py`

```python
"""Database protocol for dependency injection."""

from contextlib import asynccontextmanager, contextmanager
from typing import AsyncIterator, Iterator, Protocol

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session


class DatabaseProtocol(Protocol):
    """Protocol for database implementations.

    Allows dependency injection and testing with different implementations.
    """

    @property
    def url(self) -> str:
        """Get database URL."""
        ...

    async def initialize(self) -> None:
        """Initialize database connection."""
        ...

    async def close(self) -> None:
        """Close database connection."""
        ...


class SyncDatabaseProtocol(DatabaseProtocol, Protocol):
    """Protocol for synchronous database operations."""

    @contextmanager
    def session(self) -> Iterator[Session]:
        """Get synchronous database session.

        Yields:
            SQLAlchemy Session for database operations
        """
        ...


class AsyncDatabaseProtocol(DatabaseProtocol, Protocol):
    """Protocol for asynchronous database operations."""

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """Get asynchronous database session.

        Yields:
            SQLAlchemy AsyncSession for database operations
        """
        ...
```

#### Step 1.2: Create AsyncDatabase Implementation

**New File**: `src/omniforge/storage/async_database.py`

```python
"""Async database implementation."""

from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from omniforge.storage.database_protocol import AsyncDatabaseProtocol
from omniforge.storage.models import Base


class AsyncDatabase(AsyncDatabaseProtocol):
    """Asynchronous database connection manager.

    Responsibilities:
    - Manage async SQLAlchemy engine lifecycle
    - Provide async session factory
    - Handle async table creation/dropping
    - Single responsibility: ASYNC operations only
    """

    def __init__(
        self,
        url: str,
        echo: bool = False,
        pool_size: int = 5,
        max_overflow: int = 10,
    ) -> None:
        """Initialize async database.

        Args:
            url: Database URL (must use async driver: postgresql+asyncpg, sqlite+aiosqlite)
            echo: Echo SQL statements for debugging
            pool_size: Connection pool size
            max_overflow: Max overflow connections
        """
        if not self._is_async_url(url):
            raise ValueError(
                f"AsyncDatabase requires async driver. "
                f"Got: {url}. Use postgresql+asyncpg:// or sqlite+aiosqlite://"
            )

        self._url = url
        self._echo = echo
        self._pool_size = pool_size
        self._max_overflow = max_overflow
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[sessionmaker] = None

    @property
    def url(self) -> str:
        """Get database URL."""
        return self._url

    @property
    def engine(self) -> AsyncEngine:
        """Get async engine (creates if needed)."""
        if self._engine is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._engine

    async def initialize(self) -> None:
        """Initialize async database engine and session factory."""
        if self._engine is not None:
            return  # Already initialized

        self._engine = create_async_engine(
            self._url,
            echo=self._echo,
            pool_size=self._pool_size,
            max_overflow=self._max_overflow,
            future=True,  # Use SQLAlchemy 2.0 style
        )

        self._session_factory = sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def close(self) -> None:
        """Close database engine and cleanup resources."""
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """Get async database session.

        Yields:
            AsyncSession for database operations

        Example:
            async with db.session() as session:
                result = await session.execute(select(User))
                users = result.scalars().all()
        """
        if self._session_factory is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def create_tables(self) -> None:
        """Create all database tables defined in models."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_tables(self) -> None:
        """Drop all database tables (use with caution!)."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    @staticmethod
    def _is_async_url(url: str) -> bool:
        """Check if URL uses async driver."""
        async_drivers = [
            "postgresql+asyncpg",
            "mysql+aiomysql",
            "sqlite+aiosqlite",
        ]
        return any(url.startswith(f"{driver}://") for driver in async_drivers)
```

#### Step 1.3: Create SyncDatabase Implementation

**New File**: `src/omniforge/storage/sync_database.py`

```python
"""Synchronous database implementation."""

from contextlib import contextmanager
from typing import Iterator, Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from omniforge.storage.database_protocol import SyncDatabaseProtocol
from omniforge.storage.models import Base


class SyncDatabase(SyncDatabaseProtocol):
    """Synchronous database connection manager.

    Responsibilities:
    - Manage sync SQLAlchemy engine lifecycle
    - Provide sync session factory
    - Handle sync table creation/dropping
    - Single responsibility: SYNC operations only
    """

    def __init__(
        self,
        url: str,
        echo: bool = False,
        pool_size: int = 5,
        max_overflow: int = 10,
    ) -> None:
        """Initialize sync database.

        Args:
            url: Database URL (uses sync driver: postgresql://, sqlite://)
            echo: Echo SQL statements for debugging
            pool_size: Connection pool size
            max_overflow: Max overflow connections
        """
        if self._is_async_url(url):
            raise ValueError(
                f"SyncDatabase requires sync driver. "
                f"Got: {url}. Use postgresql:// or sqlite://"
            )

        self._url = url
        self._echo = echo
        self._pool_size = pool_size
        self._max_overflow = max_overflow
        self._engine: Optional[Engine] = None
        self._session_factory: Optional[sessionmaker] = None

    @property
    def url(self) -> str:
        """Get database URL."""
        return self._url

    @property
    def engine(self) -> Engine:
        """Get sync engine (creates if needed)."""
        if self._engine is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._engine

    async def initialize(self) -> None:
        """Initialize sync database engine and session factory.

        Note: Async method signature for protocol compatibility.
        Actual initialization is synchronous.
        """
        if self._engine is not None:
            return  # Already initialized

        self._engine = create_engine(
            self._url,
            echo=self._echo,
            pool_size=self._pool_size,
            max_overflow=self._max_overflow,
            future=True,  # Use SQLAlchemy 2.0 style
        )

        self._session_factory = sessionmaker(
            bind=self._engine,
            class_=Session,
            expire_on_commit=False,
        )

    async def close(self) -> None:
        """Close database engine and cleanup resources.

        Note: Async method signature for protocol compatibility.
        Actual cleanup is synchronous.
        """
        if self._engine is not None:
            self._engine.dispose()
            self._engine = None
            self._session_factory = None

    @contextmanager
    def session(self) -> Iterator[Session]:
        """Get sync database session.

        Yields:
            Session for database operations

        Example:
            with db.session() as session:
                result = session.execute(select(User))
                users = result.scalars().all()
        """
        if self._session_factory is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        with self._session_factory() as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise

    def create_tables(self) -> None:
        """Create all database tables defined in models."""
        Base.metadata.create_all(self.engine)

    def drop_tables(self) -> None:
        """Drop all database tables (use with caution!)."""
        Base.metadata.drop_all(self.engine)

    @staticmethod
    def _is_async_url(url: str) -> bool:
        """Check if URL uses async driver."""
        async_drivers = [
            "postgresql+asyncpg",
            "mysql+aiomysql",
            "sqlite+aiosqlite",
        ]
        return any(url.startswith(f"{driver}://") for driver in async_drivers)
```

---

### Phase 2: Create Database Factory (1-2 hours)

#### Step 2.1: Implement Factory Pattern

**New File**: `src/omniforge/storage/database_factory.py`

```python
"""Factory for creating appropriate database implementation."""

from typing import Union

from omniforge.storage.async_database import AsyncDatabase
from omniforge.storage.database_protocol import AsyncDatabaseProtocol, SyncDatabaseProtocol
from omniforge.storage.sync_database import SyncDatabase


class DatabaseFactory:
    """Factory for creating database implementations.

    Open/Closed Principle:
    - Open for extension: Can add new database types
    - Closed for modification: Existing code doesn't change

    Example:
        # Auto-detect based on URL
        db = DatabaseFactory.create("postgresql+asyncpg://...")  # AsyncDatabase
        db = DatabaseFactory.create("postgresql://...")          # SyncDatabase

        # Explicit creation
        db = DatabaseFactory.create_async("postgresql+asyncpg://...")
        db = DatabaseFactory.create_sync("postgresql://...")
    """

    @staticmethod
    def create(
        url: str,
        echo: bool = False,
        **kwargs,
    ) -> Union[AsyncDatabaseProtocol, SyncDatabaseProtocol]:
        """Create appropriate database implementation based on URL.

        Args:
            url: Database URL (driver determines async vs sync)
            echo: Echo SQL statements
            **kwargs: Additional arguments passed to database constructor

        Returns:
            AsyncDatabase if URL uses async driver, SyncDatabase otherwise

        Raises:
            ValueError: If URL format is invalid
        """
        if DatabaseFactory._is_async_url(url):
            return AsyncDatabase(url=url, echo=echo, **kwargs)
        else:
            return SyncDatabase(url=url, echo=echo, **kwargs)

    @staticmethod
    def create_async(
        url: str,
        echo: bool = False,
        **kwargs,
    ) -> AsyncDatabaseProtocol:
        """Create async database implementation.

        Args:
            url: Database URL (must use async driver)
            echo: Echo SQL statements
            **kwargs: Additional arguments passed to constructor

        Returns:
            AsyncDatabase instance

        Raises:
            ValueError: If URL doesn't use async driver
        """
        return AsyncDatabase(url=url, echo=echo, **kwargs)

    @staticmethod
    def create_sync(
        url: str,
        echo: bool = False,
        **kwargs,
    ) -> SyncDatabaseProtocol:
        """Create sync database implementation.

        Args:
            url: Database URL (must use sync driver)
            echo: Echo SQL statements
            **kwargs: Additional arguments passed to constructor

        Returns:
            SyncDatabase instance

        Raises:
            ValueError: If URL uses async driver
        """
        return SyncDatabase(url=url, echo=echo, **kwargs)

    @staticmethod
    def _is_async_url(url: str) -> bool:
        """Check if URL uses async driver."""
        async_drivers = [
            "postgresql+asyncpg",
            "mysql+aiomysql",
            "sqlite+aiosqlite",
        ]
        return any(url.startswith(f"{driver}://") for driver in async_drivers)


# Convenience functions
def create_database(url: str, **kwargs) -> Union[AsyncDatabaseProtocol, SyncDatabaseProtocol]:
    """Convenience function to create database."""
    return DatabaseFactory.create(url, **kwargs)


def create_async_database(url: str, **kwargs) -> AsyncDatabaseProtocol:
    """Convenience function to create async database."""
    return DatabaseFactory.create_async(url, **kwargs)


def create_sync_database(url: str, **kwargs) -> SyncDatabaseProtocol:
    """Convenience function to create sync database."""
    return DatabaseFactory.create_sync(url, **kwargs)
```

---

### Phase 3: Extend with Transaction Support (Optional - 2 hours)

#### Step 3.1: Add Transaction Decorators

**New File**: `src/omniforge/storage/transactions.py`

```python
"""Transaction management extensions.

Demonstrates Open/Closed Principle:
- Extends database functionality WITHOUT modifying core classes
- New transaction patterns added through composition
"""

from contextlib import asynccontextmanager, contextmanager
from typing import AsyncIterator, Callable, Iterator, Optional, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from omniforge.storage.database_protocol import AsyncDatabaseProtocol, SyncDatabaseProtocol


T = TypeVar("T")


class TransactionManager:
    """Manages database transactions with nested transaction support.

    Extension without modification:
    - Wraps existing database implementations
    - Adds transaction semantics
    - Original database classes unchanged
    """

    def __init__(
        self,
        database: Union[AsyncDatabaseProtocol, SyncDatabaseProtocol],
    ) -> None:
        """Initialize transaction manager.

        Args:
            database: Database implementation to wrap
        """
        self._database = database
        self._is_async = hasattr(database.session, "__aenter__")

    @asynccontextmanager
    async def transaction(
        self,
        isolation_level: Optional[str] = None,
    ) -> AsyncIterator[AsyncSession]:
        """Start a transaction with optional isolation level.

        Args:
            isolation_level: Optional SQL isolation level
                ("READ COMMITTED", "REPEATABLE READ", "SERIALIZABLE")

        Yields:
            Database session within transaction

        Example:
            async with transaction_manager.transaction() as session:
                # Operations here are atomic
                user = User(name="test")
                session.add(user)
                # Commits on successful exit, rolls back on exception
        """
        if not self._is_async:
            raise RuntimeError("Use sync_transaction() for sync databases")

        async with self._database.session() as session:
            if isolation_level:
                await session.execute(
                    f"SET TRANSACTION ISOLATION LEVEL {isolation_level}"
                )

            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    @contextmanager
    def sync_transaction(
        self,
        isolation_level: Optional[str] = None,
    ) -> Iterator[Session]:
        """Start a sync transaction with optional isolation level."""
        if self._is_async:
            raise RuntimeError("Use transaction() for async databases")

        with self._database.session() as session:
            if isolation_level:
                session.execute(
                    f"SET TRANSACTION ISOLATION LEVEL {isolation_level}"
                )

            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise


class ReadOnlySessionManager:
    """Provides read-only database sessions.

    Another extension without modification:
    - Adds read-only semantics
    - Prevents accidental writes
    - Original database unchanged
    """

    def __init__(
        self,
        database: Union[AsyncDatabaseProtocol, SyncDatabaseProtocol],
    ) -> None:
        """Initialize read-only session manager."""
        self._database = database
        self._is_async = hasattr(database.session, "__aenter__")

    @asynccontextmanager
    async def readonly_session(self) -> AsyncIterator[AsyncSession]:
        """Get read-only database session.

        Yields:
            Database session that rolls back on exit (no commits)
        """
        if not self._is_async:
            raise RuntimeError("Use sync_readonly_session() for sync databases")

        async with self._database.session() as session:
            try:
                yield session
            finally:
                # Always rollback - read-only!
                await session.rollback()

    @contextmanager
    def sync_readonly_session(self) -> Iterator[Session]:
        """Get read-only sync database session."""
        if self._is_async:
            raise RuntimeError("Use readonly_session() for async databases")

        with self._database.session() as session:
            try:
                yield session
            finally:
                # Always rollback - read-only!
                session.rollback()
```

---

### Phase 4: Update Existing Code (2-3 hours)

#### Step 4.1: Deprecate Old Database Class

**Modified File**: `src/omniforge/storage/database.py`

```python
"""Legacy database class - DEPRECATED.

Use AsyncDatabase or SyncDatabase instead:
    from omniforge.storage import create_database

    db = create_database("postgresql+asyncpg://...")
    await db.initialize()

    async with db.session() as session:
        # Use session
"""

import warnings
from typing import Union

from omniforge.storage.async_database import AsyncDatabase
from omniforge.storage.database_factory import DatabaseFactory
from omniforge.storage.sync_database import SyncDatabase


class Database:
    """DEPRECATED: Use AsyncDatabase or SyncDatabase instead.

    This class will be removed in version 2.0.
    """

    def __init__(self, url: str, echo: bool = False):
        warnings.warn(
            "Database class is deprecated. "
            "Use create_database() or DatabaseFactory instead.",
            DeprecationWarning,
            stacklevel=2,
        )

        # Delegate to factory
        self._impl = DatabaseFactory.create(url, echo=echo)

    def __getattr__(self, name: str):
        """Delegate all calls to implementation."""
        return getattr(self._impl, name)
```

#### Step 4.2: Update Storage Module

**Modified File**: `src/omniforge/storage/__init__.py`

```python
"""Storage layer for OmniForge."""

# New recommended API
from omniforge.storage.async_database import AsyncDatabase
from omniforge.storage.database_factory import (
    DatabaseFactory,
    create_async_database,
    create_database,
    create_sync_database,
)
from omniforge.storage.database_protocol import (
    AsyncDatabaseProtocol,
    DatabaseProtocol,
    SyncDatabaseProtocol,
)
from omniforge.storage.sync_database import SyncDatabase

# Legacy (deprecated)
from omniforge.storage.database import Database

# Repositories
from omniforge.storage.chain_repository import ChainRepository
from omniforge.storage.memory import (
    InMemoryAgentRepository,
    InMemoryChainRepository,
    InMemoryTaskRepository,
)

__all__ = [
    # Recommended API
    "AsyncDatabase",
    "SyncDatabase",
    "DatabaseFactory",
    "create_database",
    "create_async_database",
    "create_sync_database",
    # Protocols
    "DatabaseProtocol",
    "AsyncDatabaseProtocol",
    "SyncDatabaseProtocol",
    # Legacy (deprecated)
    "Database",
    # Repositories
    "ChainRepository",
    "InMemoryAgentRepository",
    "InMemoryChainRepository",
    "InMemoryTaskRepository",
]
```

---

## Migration Path

### For Existing Code (Gradual Migration)

#### Option 1: Keep Using Database (Works, but deprecated)
```python
# OLD CODE - Still works with deprecation warning
from omniforge.storage import Database

db = Database("postgresql+asyncpg://...")
await db.initialize()
```

#### Option 2: Use Factory (Recommended)
```python
# NEW CODE - Recommended
from omniforge.storage import create_database

db = create_database("postgresql+asyncpg://...")
await db.initialize()
```

#### Option 3: Use Specific Implementation
```python
# NEW CODE - Most explicit
from omniforge.storage import AsyncDatabase

db = AsyncDatabase("postgresql+asyncpg://...")
await db.initialize()
```

### For New Code

Always use the new API:

```python
from omniforge.storage import create_database

# Factory chooses implementation based on URL
db = create_database(
    url="postgresql+asyncpg://localhost/mydb",
    echo=True,
    pool_size=10,
)
await db.initialize()

async with db.session() as session:
    # Use session
    pass
```

---

## Testing Strategy

### Unit Tests Per Implementation

**Test File**: `tests/storage/test_async_database.py`

```python
"""Tests for AsyncDatabase."""

import pytest

from omniforge.storage import AsyncDatabase


@pytest.mark.asyncio
class TestAsyncDatabase:
    async def test_initialize_creates_engine(self):
        """Should create async engine on initialize."""
        db = AsyncDatabase("sqlite+aiosqlite:///:memory:")

        await db.initialize()

        assert db.engine is not None
        assert db._session_factory is not None

    async def test_session_yields_async_session(self):
        """Should yield AsyncSession."""
        db = AsyncDatabase("sqlite+aiosqlite:///:memory:")
        await db.initialize()

        async with db.session() as session:
            # Verify it's AsyncSession
            assert session.__class__.__name__ == "AsyncSession"

    async def test_session_commits_on_success(self):
        """Should commit transaction on successful exit."""
        # Test implementation...

    async def test_session_rolls_back_on_error(self):
        """Should rollback transaction on exception."""
        # Test implementation...

    async def test_close_disposes_engine(self):
        """Should dispose engine on close."""
        db = AsyncDatabase("sqlite+aiosqlite:///:memory:")
        await db.initialize()

        await db.close()

        with pytest.raises(RuntimeError, match="not initialized"):
            _ = db.engine

    async def test_rejects_sync_url(self):
        """Should reject non-async URL."""
        with pytest.raises(ValueError, match="requires async driver"):
            AsyncDatabase("postgresql://localhost/db")
```

**Test File**: `tests/storage/test_sync_database.py`

```python
"""Tests for SyncDatabase."""

import pytest

from omniforge.storage import SyncDatabase


class TestSyncDatabase:
    async def test_initialize_creates_engine(self):
        """Should create sync engine on initialize."""
        db = SyncDatabase("sqlite:///:memory:")

        await db.initialize()

        assert db.engine is not None
        assert db._session_factory is not None

    def test_session_yields_sync_session(self):
        """Should yield Session."""
        db = SyncDatabase("sqlite:///:memory:")

        # Initialize first
        import asyncio
        asyncio.run(db.initialize())

        with db.session() as session:
            # Verify it's Session (not AsyncSession)
            assert session.__class__.__name__ == "Session"

    def test_rejects_async_url(self):
        """Should reject async URL."""
        with pytest.raises(ValueError, match="requires sync driver"):
            SyncDatabase("postgresql+asyncpg://localhost/db")
```

### Integration Tests

```python
"""Integration tests for database implementations."""

import pytest

from omniforge.storage import create_database
from omniforge.storage.models import Base, User  # Example model


@pytest.mark.asyncio
async def test_async_database_full_workflow():
    """Test complete workflow with AsyncDatabase."""
    db = create_database("sqlite+aiosqlite:///:memory:")
    await db.initialize()

    # Create tables
    await db.create_tables()

    # Insert data
    async with db.session() as session:
        user = User(name="test", email="test@example.com")
        session.add(user)

    # Query data
    async with db.session() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()
        assert len(users) == 1
        assert users[0].name == "test"

    await db.close()
```

---

## Benefits After Refactoring

### Open/Closed Principle ✅
```python
# Add new session pattern WITHOUT modifying existing classes
class PooledSessionManager:
    """New session strategy - no changes to core classes needed!"""

    def __init__(self, database: DatabaseProtocol):
        self._database = database
        self._pool = []  # Custom pooling logic

    @asynccontextmanager
    async def pooled_session(self):
        # Get from pool or create new
        session = self._get_from_pool()
        try:
            yield session
        finally:
            self._return_to_pool(session)
```

### Single Responsibility ✅
- **AsyncDatabase**: Only async operations
- **SyncDatabase**: Only sync operations
- **DatabaseFactory**: Only creation logic
- **TransactionManager**: Only transaction semantics

### Type Safety ✅
```python
# Before: Union type loses information
db: Database
session = db.session()  # Is this Session or AsyncSession? ¯\_(ツ)_/¯

# After: Clear types
async_db: AsyncDatabaseProtocol = create_async_database(...)
async with async_db.session() as session:
    # session is clearly AsyncSession - type checker knows!
```

### Testability ✅
```python
# Easy to mock specific implementation
class MockAsyncDatabase(AsyncDatabaseProtocol):
    async def session(self):
        # Return mock session
        pass

# Use in tests
async def test_repository(mock_db: MockAsyncDatabase):
    repo = ChainRepository(mock_db)
    # Test repository without real database
```

### Extensibility ✅
- Add transaction support without modifying core
- Add connection pooling strategies
- Add session interceptors
- Add retry logic
- All through composition!

---

## Timeline

- **Phase 1** (Async/Sync implementations): 2-3 hours
- **Phase 2** (Factory pattern): 1-2 hours
- **Phase 3** (Extensions - optional): 2 hours
- **Phase 4** (Migration): 2-3 hours

**Total: 7-10 hours** (approximately 1-2 work days)

---

## Success Metrics

### Code Quality
- ✅ No runtime context detection
- ✅ Clear separation of sync/async
- ✅ Type-safe session management
- ✅ No cyclomatic complexity > 8

### Extensibility
- ✅ New session patterns added without modification
- ✅ Transaction support through composition
- ✅ Easy to add connection pooling
- ✅ Custom session managers composable

### Performance
- ✅ Remove runtime detection overhead
- ✅ No unnecessary engine initialization
- ✅ Connection pooling configurable
- ✅ Same or better performance than before

---

## Risk Assessment

### Low Risk
- Existing Database class remains functional (deprecated)
- Backward compatible migration path
- New code uses new API gradually

### Medium Risk
- Repositories using Database need update
- Type annotations need update
- Tests need migration

### Mitigation
- Deprecation warnings guide migration
- Comprehensive test coverage
- Factory auto-detects correct implementation
- Phase migration over multiple releases

This refactoring makes Database:
- ✅ Open for extension (new patterns via composition)
- ✅ Closed for modification (core classes stable)
- ✅ Type-safe (AsyncSession vs Session)
- ✅ Testable (protocols enable mocking)
- ✅ Maintainable (single responsibility per class)
