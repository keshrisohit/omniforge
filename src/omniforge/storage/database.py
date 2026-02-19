"""Database configuration and session management.

This module provides SQLAlchemy database configuration, session management,
and the declarative base for ORM models.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

from omniforge.storage.base_model import Base


class DatabaseConfig:
    """Database configuration.

    Attributes:
        url: Database connection URL (supports both sync and async URLs)
        echo: Whether to log SQL statements (default: False)
        pool_size: Connection pool size (default: 5)
        max_overflow: Maximum overflow connections (default: 10)
    """

    def __init__(
        self,
        url: str = "sqlite+aiosqlite:///:memory:",
        echo: bool = False,
        pool_size: int = 5,
        max_overflow: int = 10,
    ):
        self.url = url
        self.echo = echo
        self.pool_size = pool_size
        self.max_overflow = max_overflow


class Database:
    """Database connection and session manager.

    Manages SQLAlchemy engine and session lifecycle for both sync and async operations.

    Example:
        >>> config = DatabaseConfig(url="sqlite+aiosqlite:///./test.db")
        >>> db = Database(config)
        >>> async with db.session() as session:
        ...     result = await session.execute(select(CostRecordModel))
    """

    def __init__(self, config: DatabaseConfig):
        """Initialize database with configuration.

        Args:
            config: Database configuration
        """
        self.config = config

        # Prepare engine kwargs (exclude pool settings for SQLite)
        engine_kwargs = {"echo": config.echo}
        if "sqlite" not in config.url:
            # Only add pool settings for non-SQLite databases
            engine_kwargs["pool_size"] = config.pool_size
            engine_kwargs["max_overflow"] = config.max_overflow

        # Create async engine
        if "aiosqlite" in config.url or "asyncpg" in config.url:
            self.engine = create_async_engine(config.url, **engine_kwargs)
            self.session_factory = async_sessionmaker(
                self.engine, class_=AsyncSession, expire_on_commit=False
            )
            self.is_async = True
        else:
            # Fallback to sync engine
            self.engine = create_engine(config.url, **engine_kwargs)
            self.session_factory = sessionmaker(self.engine, expire_on_commit=False)
            self.is_async = False

    async def create_tables(self) -> None:
        """Create all tables defined in ORM models.

        Calls register_all_models() to ensure all ORM model modules are imported
        before creating tables, preventing incomplete schema creation.
        """
        from omniforge.storage.model_registry import register_all_models

        register_all_models()

        if self.is_async:
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
        else:
            Base.metadata.create_all(self.engine)

    async def drop_tables(self) -> None:
        """Drop all tables defined in ORM models.

        Calls register_all_models() to ensure all ORM model modules are imported
        before dropping tables, ensuring complete cleanup.
        """
        from omniforge.storage.model_registry import register_all_models

        register_all_models()

        if self.is_async:
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
        else:
            Base.metadata.drop_all(self.engine)

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Create a new database session.

        Yields:
            Database session (async or sync based on configuration)
        """
        if self.is_async:
            async with self.session_factory() as session:
                try:
                    yield session
                    await session.commit()
                except Exception:
                    await session.rollback()
                    raise
        else:
            session = self.session_factory()
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()

    async def close(self) -> None:
        """Close database engine and connections."""
        if self.is_async:
            await self.engine.dispose()
        else:
            self.engine.dispose()

    async def health_check(self) -> bool:
        """Check database connectivity.

        Returns:
            True if database is healthy

        Raises:
            Exception if database connection fails
        """
        if self.is_async:
            async with self.engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
        else:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        return True
