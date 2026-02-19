"""Tests for database query tool."""

import pytest
from sqlalchemy import create_engine, text

from omniforge.tools.base import ToolCallContext
from omniforge.tools.builtin.database import DatabaseTool


@pytest.fixture
def in_memory_db():
    """Create in-memory SQLite database with test data."""
    engine = create_engine("sqlite:///:memory:")

    # Create test table and insert data
    with engine.connect() as conn:
        conn.execute(
            text(
                """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                age INTEGER
            )
        """
            )
        )

        # Insert test data
        for i in range(1, 11):
            conn.execute(
                text(
                    "INSERT INTO users (id, name, email, age) VALUES (:id, :name, :email, :age)"
                ),
                {"id": i, "name": f"User {i}", "email": f"user{i}@example.com", "age": 20 + i},
            )
        conn.commit()

    return engine


@pytest.fixture
def tool_context() -> ToolCallContext:
    """Create test tool call context."""
    return ToolCallContext(
        correlation_id="corr-123",
        task_id="task-123",
        agent_id="agent-456",
    )


def test_database_tool_initialization_with_engine(in_memory_db) -> None:
    """Test DatabaseTool initializes with engine."""
    tool = DatabaseTool(engine=in_memory_db)

    assert tool._engine is in_memory_db
    assert tool._read_only is False
    assert tool._default_limit == 100


def test_database_tool_initialization_with_connection_string() -> None:
    """Test DatabaseTool initializes with connection string."""
    tool = DatabaseTool(connection_string="sqlite:///:memory:")

    assert tool._engine is not None
    assert tool._read_only is False


def test_database_tool_initialization_requires_engine_or_string() -> None:
    """Test DatabaseTool requires engine or connection_string."""
    with pytest.raises(ValueError, match="Either 'engine' or 'connection_string' must be provided"):
        DatabaseTool()


def test_database_tool_definition(in_memory_db) -> None:
    """Test DatabaseTool definition."""
    tool = DatabaseTool(engine=in_memory_db)
    definition = tool.definition

    assert definition.name == "database"
    assert definition.type.value == "database"

    # Check parameters
    param_names = [p.name for p in definition.parameters]
    assert "query" in param_names
    assert "params" in param_names
    assert "limit" in param_names

    assert definition.timeout_ms == 30000


@pytest.mark.asyncio
async def test_database_tool_execute_select(
    in_memory_db, tool_context: ToolCallContext
) -> None:
    """Test executing SELECT query."""
    tool = DatabaseTool(engine=in_memory_db)

    result = await tool.execute(
        arguments={"query": "SELECT * FROM users WHERE age > 25"},
        context=tool_context,
    )

    assert result.success is True
    assert "rows" in result.result
    assert "row_count" in result.result
    assert "columns" in result.result
    assert result.result["row_count"] == 5
    assert "id" in result.result["columns"]
    assert "name" in result.result["columns"]
    assert result.duration_ms >= 0


@pytest.mark.asyncio
async def test_database_tool_execute_with_parameters(
    in_memory_db, tool_context: ToolCallContext
) -> None:
    """Test executing parameterized query."""
    tool = DatabaseTool(engine=in_memory_db)

    result = await tool.execute(
        arguments={
            "query": "SELECT * FROM users WHERE age > :min_age AND age < :max_age",
            "params": {"min_age": 23, "max_age": 27},
        },
        context=tool_context,
    )

    assert result.success is True
    assert result.result["row_count"] == 3
    # Should return users 4, 5, 6 (ages 24, 25, 26)


@pytest.mark.asyncio
async def test_database_tool_result_limit_enforced(
    in_memory_db, tool_context: ToolCallContext
) -> None:
    """Test result limit is enforced."""
    tool = DatabaseTool(engine=in_memory_db, default_limit=5)

    result = await tool.execute(
        arguments={"query": "SELECT * FROM users"},
        context=tool_context,
    )

    assert result.success is True
    assert result.result["row_count"] == 5  # Limited to 5


@pytest.mark.asyncio
async def test_database_tool_custom_limit(in_memory_db, tool_context: ToolCallContext) -> None:
    """Test custom limit parameter."""
    tool = DatabaseTool(engine=in_memory_db)

    result = await tool.execute(
        arguments={"query": "SELECT * FROM users", "limit": 3},
        context=tool_context,
    )

    assert result.success is True
    assert result.result["row_count"] == 3


@pytest.mark.asyncio
async def test_database_tool_max_limit_enforced(
    in_memory_db, tool_context: ToolCallContext
) -> None:
    """Test max limit is enforced."""
    tool = DatabaseTool(engine=in_memory_db, max_limit=7)

    result = await tool.execute(
        arguments={"query": "SELECT * FROM users", "limit": 1000},  # Request 1000
        context=tool_context,
    )

    assert result.success is True
    assert result.result["row_count"] == 7  # Limited to max_limit


@pytest.mark.asyncio
async def test_database_tool_empty_query(in_memory_db, tool_context: ToolCallContext) -> None:
    """Test empty query returns error."""
    tool = DatabaseTool(engine=in_memory_db)

    result = await tool.execute(
        arguments={"query": ""},
        context=tool_context,
    )

    assert result.success is False
    assert "cannot be empty" in result.error.lower()


@pytest.mark.asyncio
async def test_database_tool_sql_error(in_memory_db, tool_context: ToolCallContext) -> None:
    """Test SQL errors return ToolResult with error."""
    tool = DatabaseTool(engine=in_memory_db)

    result = await tool.execute(
        arguments={"query": "SELECT * FROM nonexistent_table"},
        context=tool_context,
    )

    assert result.success is False
    assert "error" in result.error.lower()
    assert result.duration_ms >= 0


@pytest.mark.asyncio
async def test_database_tool_read_only_mode_allows_select(
    in_memory_db, tool_context: ToolCallContext
) -> None:
    """Test read-only mode allows SELECT queries."""
    tool = DatabaseTool(engine=in_memory_db, read_only=True)

    result = await tool.execute(
        arguments={"query": "SELECT * FROM users"},
        context=tool_context,
    )

    assert result.success is True
    assert result.result["row_count"] > 0


@pytest.mark.asyncio
async def test_database_tool_read_only_mode_prevents_insert(
    in_memory_db, tool_context: ToolCallContext
) -> None:
    """Test read-only mode prevents INSERT."""
    tool = DatabaseTool(engine=in_memory_db, read_only=True)

    result = await tool.execute(
        arguments={"query": "INSERT INTO users (id, name, email, age) VALUES (99, 'Test', 'test@example.com', 30)"},
        context=tool_context,
    )

    assert result.success is False
    assert "not allowed in read-only mode" in result.error


@pytest.mark.asyncio
async def test_database_tool_read_only_mode_prevents_update(
    in_memory_db, tool_context: ToolCallContext
) -> None:
    """Test read-only mode prevents UPDATE."""
    tool = DatabaseTool(engine=in_memory_db, read_only=True)

    result = await tool.execute(
        arguments={"query": "UPDATE users SET age = 100 WHERE id = 1"},
        context=tool_context,
    )

    assert result.success is False
    assert "not allowed in read-only mode" in result.error


@pytest.mark.asyncio
async def test_database_tool_read_only_mode_prevents_delete(
    in_memory_db, tool_context: ToolCallContext
) -> None:
    """Test read-only mode prevents DELETE."""
    tool = DatabaseTool(engine=in_memory_db, read_only=True)

    result = await tool.execute(
        arguments={"query": "DELETE FROM users WHERE id = 1"},
        context=tool_context,
    )

    assert result.success is False
    assert "not allowed in read-only mode" in result.error


@pytest.mark.asyncio
async def test_database_tool_read_only_mode_prevents_drop(
    in_memory_db, tool_context: ToolCallContext
) -> None:
    """Test read-only mode prevents DROP."""
    tool = DatabaseTool(engine=in_memory_db, read_only=True)

    result = await tool.execute(
        arguments={"query": "DROP TABLE users"},
        context=tool_context,
    )

    assert result.success is False
    assert "not allowed in read-only mode" in result.error


@pytest.mark.asyncio
async def test_database_tool_insert_returns_affected_rows(
    in_memory_db, tool_context: ToolCallContext
) -> None:
    """Test INSERT returns affected rows count."""
    tool = DatabaseTool(engine=in_memory_db, read_only=False)

    result = await tool.execute(
        arguments={
            "query": "INSERT INTO users (id, name, email, age) VALUES (:id, :name, :email, :age)",
            "params": {"id": 99, "name": "New User", "email": "new@example.com", "age": 35},
        },
        context=tool_context,
    )

    assert result.success is True
    assert "affected_rows" in result.result
    assert result.result["affected_rows"] == 1


@pytest.mark.asyncio
async def test_database_tool_update_returns_affected_rows(
    in_memory_db, tool_context: ToolCallContext
) -> None:
    """Test UPDATE returns affected rows count."""
    tool = DatabaseTool(engine=in_memory_db, read_only=False)

    result = await tool.execute(
        arguments={"query": "UPDATE users SET age = 100 WHERE id <= 3"},
        context=tool_context,
    )

    assert result.success is True
    assert "affected_rows" in result.result
    assert result.result["affected_rows"] == 3


@pytest.mark.asyncio
async def test_database_tool_limit_not_applied_to_non_select(
    in_memory_db, tool_context: ToolCallContext
) -> None:
    """Test LIMIT not applied to non-SELECT queries."""
    tool = DatabaseTool(engine=in_memory_db, read_only=False)

    result = await tool.execute(
        arguments={"query": "UPDATE users SET age = age + 1"},
        context=tool_context,
    )

    assert result.success is True
    assert result.result["affected_rows"] == 10  # All rows updated


@pytest.mark.asyncio
async def test_database_tool_existing_limit_not_modified(
    in_memory_db, tool_context: ToolCallContext
) -> None:
    """Test existing LIMIT clause is not modified."""
    tool = DatabaseTool(engine=in_memory_db, default_limit=100)

    result = await tool.execute(
        arguments={"query": "SELECT * FROM users LIMIT 2"},
        context=tool_context,
    )

    assert result.success is True
    assert result.result["row_count"] == 2  # Original LIMIT respected
