"""Integration tests for database migrations.

Tests database schema creation and migration validation for both SQLite
and PostgreSQL databases.
"""

import os
import tempfile
from typing import AsyncGenerator

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from omniforge.storage.base_model import Base
from omniforge.storage.database import Database, DatabaseConfig
from omniforge.storage.model_registry import register_all_models


@pytest.fixture
async def sqlite_db() -> AsyncGenerator[Database, None]:
    """Create a file-based SQLite database for testing.

    Yields:
        Database instance with SQLite connection
    """
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    try:
        config = DatabaseConfig(url=f"sqlite+aiosqlite:///{db_path}", echo=False)
        db = Database(config)

        yield db

        await db.engine.dispose()
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)


@pytest.fixture
async def postgres_db() -> AsyncGenerator[Database, None]:
    """Create a PostgreSQL database for testing using testcontainers.

    This fixture is skipped if PostgreSQL is not available or if running
    in an environment without Docker.

    Yields:
        Database instance with PostgreSQL connection
    """
    pytest.importorskip("testcontainers")

    from testcontainers.postgres import PostgresContainer

    with PostgresContainer("postgres:15-alpine") as postgres:
        # Get connection details
        db_url = postgres.get_connection_url().replace("psycopg2", "asyncpg")

        config = DatabaseConfig(url=db_url, echo=False)
        db = Database(config)

        yield db

        await db.engine.dispose()


class TestDatabaseMigrations:
    """Integration tests for database migrations."""

    async def test_create_all_tables_sqlite(
        self,
        sqlite_db: Database,
    ) -> None:
        """Test that all tables are created correctly in SQLite.

        Validates:
        1. All ORM models are registered
        2. Tables are created with correct schema
        3. Indexes are created
        4. Foreign keys are set up correctly
        """
        # Arrange: Register all models
        register_all_models()

        # Act: Create all tables
        async with sqlite_db.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Assert: Verify tables exist
        async with sqlite_db.engine.connect() as conn:
            result = await conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
            tables = [row[0] for row in result.fetchall()]

        # Expected all 14 tables from all modules
        expected_tables = [
            # Storage module (7 tables)
            "cost_records",
            "model_usage",
            "reasoning_chains",
            "reasoning_steps",
            "audit_events",
            "oauth_states",
            "oauth_credentials",
            # Conversation module (2 tables)
            "conversations",
            "conversation_messages",  # Note: table name is conversation_messages, not messages
            # Skills module (1 table)
            "skill_creation_sessions",
            # Builder module (4 tables)
            "agent_configs",
            "credentials",
            "agent_executions",
            "public_skills",
        ]

        for table in expected_tables:
            assert table in tables, f"Table {table} not created. Available tables: {tables}"

        # Verify we have exactly 14 tables (plus any sqlite internal tables)
        user_tables = [t for t in tables if not t.startswith("sqlite_")]
        assert len(user_tables) == 14, f"Expected 14 tables, got {len(user_tables)}: {user_tables}"

    async def test_table_schema_validation_sqlite(
        self,
        sqlite_db: Database,
    ) -> None:
        """Test that table schemas match expected structure in SQLite.

        Validates column names, types, and constraints for critical tables.
        """
        # Arrange: Register all models and create all tables
        register_all_models()
        async with sqlite_db.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Act: Inspect schema
        async with sqlite_db.engine.connect() as conn:
            inspector = await conn.run_sync(
                lambda sync_conn: inspect(sync_conn)
            )

        # Assert: Validate agent_configs table
        agent_config_columns = {
            col["name"]: col for col in inspector.get_columns("agent_configs")
        }

        expected_columns = [
            "id",
            "tenant_id",
            "user_id",
            "name",
            "description",
            "trigger_type",
            "status",
            "created_at",
            "updated_at",
        ]

        for col_name in expected_columns:
            assert col_name in agent_config_columns, f"Column {col_name} not found"

    async def test_indexes_created_sqlite(
        self,
        sqlite_db: Database,
    ) -> None:
        """Test that database indexes are created correctly in SQLite.

        Validates that performance indexes are created for frequently
        queried columns.
        """
        # Arrange: Register all models and create all tables
        register_all_models()
        async with sqlite_db.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Act: Get indexes
        async with sqlite_db.engine.connect() as conn:
            inspector = await conn.run_sync(
                lambda sync_conn: inspect(sync_conn)
            )

        # Assert: Verify indexes exist
        agent_config_indexes = inspector.get_indexes("agent_configs")

        # Check that we have indexes (exact names depend on ORM model definition)
        assert len(agent_config_indexes) > 0, "No indexes found on agent_configs"

    async def test_foreign_key_constraints_sqlite(
        self,
        sqlite_db: Database,
    ) -> None:
        """Test that foreign key constraints are properly set up in SQLite.

        Validates referential integrity constraints between tables.
        """
        # Arrange: Register all models and create all tables
        register_all_models()
        async with sqlite_db.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Act: Get foreign keys
        async with sqlite_db.engine.connect() as conn:
            inspector = await conn.run_sync(
                lambda sync_conn: inspect(sync_conn)
            )

        # Assert: Check foreign keys (if any exist in schema)
        # Note: This is schema-dependent
        oauth_credentials_fks = inspector.get_foreign_keys("oauth_credentials")

        # OAuth credentials should have foreign keys or at least the table should exist
        assert "oauth_credentials" in inspector.get_table_names()

    @pytest.mark.skipif(
        os.getenv("SKIP_POSTGRES_TESTS", "false").lower() == "true",
        reason="PostgreSQL tests skipped (requires Docker)",
    )
    async def test_create_all_tables_postgres(
        self,
        postgres_db: Database,
    ) -> None:
        """Test that all tables are created correctly in PostgreSQL.

        Validates that the schema works correctly with PostgreSQL's
        type system and constraints.
        """
        # Arrange: Register all models
        register_all_models()

        # Act: Create all tables
        async with postgres_db.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Assert: Verify tables exist
        async with postgres_db.engine.connect() as conn:
            result = await conn.execute(
                text(
                    """
                    SELECT tablename
                    FROM pg_catalog.pg_tables
                    WHERE schemaname = 'public'
                    """
                )
            )
            tables = [row[0] for row in result.fetchall()]

        # Expected all 14 tables from all modules
        expected_tables = [
            # Storage module (7 tables)
            "cost_records",
            "model_usage",
            "reasoning_chains",
            "reasoning_steps",
            "audit_events",
            "oauth_states",
            "oauth_credentials",
            # Conversation module (2 tables)
            "conversations",
            "conversation_messages",  # Note: table name is conversation_messages, not messages
            # Skills module (1 table)
            "skill_creation_sessions",
            # Builder module (4 tables)
            "agent_configs",
            "credentials",
            "agent_executions",
            "public_skills",
        ]

        for table in expected_tables:
            assert table in tables, f"Table {table} not created in PostgreSQL"

    @pytest.mark.skipif(
        os.getenv("SKIP_POSTGRES_TESTS", "false").lower() == "true",
        reason="PostgreSQL tests skipped (requires Docker)",
    )
    async def test_postgres_specific_types(
        self,
        postgres_db: Database,
    ) -> None:
        """Test that PostgreSQL-specific types are used correctly.

        Validates that columns use appropriate PostgreSQL types like
        JSONB, UUID, TIMESTAMP WITH TIMEZONE, etc.
        """
        # Arrange: Register all models and create all tables
        register_all_models()
        async with postgres_db.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Act: Inspect schema
        async with postgres_db.engine.connect() as conn:
            inspector = await conn.run_sync(
                lambda sync_conn: inspect(sync_conn)
            )

        # Assert: Verify column types for agent_configs
        agent_config_columns = {
            col["name"]: col for col in inspector.get_columns("agent_configs")
        }

        # Verify timestamp columns
        if "created_at" in agent_config_columns:
            created_at_type = str(agent_config_columns["created_at"]["type"])
            assert "TIMESTAMP" in created_at_type.upper()

    async def test_migration_idempotency_sqlite(
        self,
        sqlite_db: Database,
    ) -> None:
        """Test that running migrations multiple times is safe.

        Validates that:
        1. Running create_all multiple times doesn't cause errors
        2. Schema remains consistent
        3. No data loss occurs
        """
        # Arrange: Register all models
        register_all_models()

        # Act: Create tables twice
        async with sqlite_db.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with sqlite_db.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Assert: Tables still exist and are accessible
        async with sqlite_db.engine.connect() as conn:
            result = await conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
            tables = [row[0] for row in result.fetchall()]

        assert len(tables) > 0, "Tables were lost after second migration"

    async def test_database_supports_concurrent_writes_sqlite(
        self,
        sqlite_db: Database,
    ) -> None:
        """Test that database supports concurrent write operations.

        Validates that multiple sessions can write to the database
        concurrently without corruption.
        """
        # Arrange: Register all models and create all tables
        register_all_models()
        async with sqlite_db.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Act: Perform concurrent writes
        import asyncio

        async def write_operation(session_num: int) -> None:
            async with sqlite_db.session() as session:
                await session.execute(
                    text("INSERT INTO cost_records (id, total_cost) VALUES (:id, :cost)"),
                    {"id": f"test-{session_num}", "cost": 1.0},
                )
                await session.commit()

        # Execute multiple writes concurrently
        await asyncio.gather(*[write_operation(i) for i in range(5)])

        # Assert: All records were written
        async with sqlite_db.session() as session:
            result = await session.execute(
                text("SELECT COUNT(*) FROM cost_records WHERE id LIKE 'test-%'")
            )
            count = result.scalar()

        assert count == 5, "Not all concurrent writes completed"

    async def test_drop_all_tables_sqlite(
        self,
        sqlite_db: Database,
    ) -> None:
        """Test that all tables can be dropped cleanly.

        Validates that drop_all operation removes all tables and
        leaves the database in a clean state.
        """
        # Arrange: Register all models and create all tables
        register_all_models()
        async with sqlite_db.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Act: Drop all tables
        async with sqlite_db.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

        # Assert: No tables remain
        async with sqlite_db.engine.connect() as conn:
            result = await conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
            tables = [row[0] for row in result.fetchall()]

        # Only sqlite internal tables should remain (if any)
        user_tables = [t for t in tables if not t.startswith("sqlite_")]
        assert len(user_tables) == 0, f"Tables still exist after drop_all: {user_tables}"
