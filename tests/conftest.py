"""Pytest configuration and shared fixtures for the test suite."""

import os
import tempfile
from typing import AsyncGenerator, TYPE_CHECKING

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

if TYPE_CHECKING:
    from omniforge.storage.database import Base, Database, DatabaseConfig


# Configure pytest-asyncio to use auto mode
pytest_plugins = ["pytest_asyncio"]


@pytest.fixture
def anyio_backend():
    """Configure anyio to use asyncio backend."""
    return "asyncio"


@pytest.fixture
async def test_db() -> AsyncGenerator["Database", None]:
    """Create an in-memory SQLite database for testing.

    Yields:
        Database instance with in-memory SQLite connection
    """
    from omniforge.storage.database import Base, Database, DatabaseConfig
    from omniforge.storage.model_registry import register_all_models

    # Register all models before creating tables
    register_all_models()

    config = DatabaseConfig(url="sqlite+aiosqlite:///:memory:", echo=False)
    db = Database(config)

    # Create all tables
    async with db.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield db

    # Cleanup
    await db.engine.dispose()


@pytest.fixture
async def test_db_file() -> AsyncGenerator["Database", None]:
    """Create a file-based SQLite database for migration testing.

    Yields:
        Database instance with file-based SQLite connection
    """
    from omniforge.storage.database import Base, Database, DatabaseConfig
    from omniforge.storage.model_registry import register_all_models

    # Register all models before creating tables
    register_all_models()

    # Create temporary database file
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    try:
        config = DatabaseConfig(url=f"sqlite+aiosqlite:///{db_path}", echo=False)
        db = Database(config)

        # Create all tables
        async with db.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        yield db

        # Cleanup
        await db.engine.dispose()
    finally:
        # Remove temporary database file
        if os.path.exists(db_path):
            os.remove(db_path)


@pytest.fixture
async def db_session(test_db: "Database") -> AsyncGenerator[AsyncSession, None]:
    """Create a database session for testing.

    Args:
        test_db: Test database instance

    Yields:
        AsyncSession for database operations
    """
    async with test_db.session() as session:
        yield session


@pytest.fixture
def mock_encryption_key(monkeypatch: pytest.MonkeyPatch) -> str:
    """Provide a mock encryption key for testing.

    Args:
        monkeypatch: Pytest monkeypatch fixture

    Returns:
        Base64-encoded encryption key
    """
    from cryptography.fernet import Fernet

    key = Fernet.generate_key()
    monkeypatch.setenv("CREDENTIAL_ENCRYPTION_KEY", key.decode())
    return key.decode()


@pytest.fixture
def mock_oauth_config(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """Provide mock OAuth configuration for testing.

    Args:
        monkeypatch: Pytest monkeypatch fixture

    Returns:
        Dictionary with OAuth configuration
    """
    config = {
        "NOTION_CLIENT_ID": "test-notion-client-id",
        "NOTION_CLIENT_SECRET": "test-notion-client-secret",
        "NOTION_REDIRECT_URI": "http://localhost:8000/oauth/callback",
    }

    for key, value in config.items():
        monkeypatch.setenv(key, value)

    return config
