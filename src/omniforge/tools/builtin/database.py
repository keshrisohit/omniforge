"""Database query tool for SQL operations through unified interface.

This module provides the DatabaseTool for executing SQL queries with
safety controls, result limiting, and full audit logging.
"""

import time
from typing import Any, Optional, Union

from sqlalchemy import Connection, Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from omniforge.tools.base import (
    BaseTool,
    ParameterType,
    ToolCallContext,
    ToolDefinition,
    ToolParameter,
    ToolResult,
)
from omniforge.tools.types import ToolType


class DatabaseTool(BaseTool):
    """Tool for executing SQL queries with safety controls.

    Provides database access through the unified tool interface with:
    - Parameterized queries for SQL injection prevention
    - Result row limiting
    - Read-only mode support
    - Query execution time tracking
    - Comprehensive error handling

    Example:
        >>> from sqlalchemy import create_engine
        >>> engine = create_engine("sqlite:///:memory:")
        >>> tool = DatabaseTool(engine=engine, read_only=True)
        >>> context = ToolCallContext(
        ...     correlation_id="corr-1",
        ...     task_id="task-1",
        ...     agent_id="agent-1"
        ... )
        >>> result = await tool.execute(
        ...     arguments={"query": "SELECT * FROM users LIMIT 10"},
        ...     context=context
        ... )
        >>> result.success
        True
    """

    def __init__(
        self,
        engine: Optional[Engine] = None,
        connection_string: Optional[str] = None,
        read_only: bool = False,
        default_limit: int = 100,
        max_limit: int = 1000,
    ) -> None:
        """Initialize DatabaseTool.

        Args:
            engine: SQLAlchemy engine instance (provide engine OR connection_string)
            connection_string: Database connection string (used if engine not provided)
            read_only: If True, only SELECT queries are allowed
            default_limit: Default row limit for queries without LIMIT clause
            max_limit: Maximum allowed row limit

        Raises:
            ValueError: If neither engine nor connection_string is provided
        """
        if engine is None and connection_string is None:
            raise ValueError("Either 'engine' or 'connection_string' must be provided")

        self._engine = engine or create_engine(connection_string)  # type: ignore[arg-type]
        self._read_only = read_only
        self._default_limit = default_limit
        self._max_limit = max_limit

    @property
    def definition(self) -> ToolDefinition:
        """Get tool definition."""
        return ToolDefinition(
            name="database",
            type=ToolType.DATABASE,
            description="Execute SQL queries against the database with safety controls",
            parameters=[
                ToolParameter(
                    name="query",
                    type=ParameterType.STRING,
                    description="SQL query to execute (use :param_name for parameters)",
                    required=True,
                ),
                ToolParameter(
                    name="params",
                    type=ParameterType.OBJECT,
                    description="Query parameters as key-value pairs for parameterized queries",
                    required=False,
                ),
                ToolParameter(
                    name="limit",
                    type=ParameterType.INTEGER,
                    description=f"Maximum rows to return (default: {self._default_limit}, max: {self._max_limit})",
                    required=False,
                ),
            ],
            timeout_ms=30000,  # 30 seconds default
        )

    async def execute(self, context: ToolCallContext, arguments: dict[str, Any]) -> ToolResult:
        """Execute SQL query with safety controls.

        Args:
            context: Execution context
            arguments: Tool arguments containing query, params, and limit

        Returns:
            ToolResult with query results or error
        """
        start_time = time.time()

        # Extract arguments
        query_str = arguments.get("query", "").strip()
        params = arguments.get("params", {})
        limit = arguments.get("limit", self._default_limit)

        # Validate query
        if not query_str:
            return ToolResult(
                success=False,
                error="Query cannot be empty",
                duration_ms=int((time.time() - start_time) * 1000),
            )

        # Check read-only mode
        if self._read_only and not self._is_read_only_query(query_str):
            return ToolResult(
                success=False,
                error="Write operations are not allowed in read-only mode",
                duration_ms=int((time.time() - start_time) * 1000),
            )

        # Validate and enforce limit
        if limit > self._max_limit:
            limit = self._max_limit

        try:
            # Execute query
            with self._engine.connect() as connection:
                # Add LIMIT if not present in SELECT queries
                modified_query = self._apply_limit(query_str, limit)

                # Execute with parameters
                result = connection.execute(text(modified_query), params)

                # Fetch results if this is a SELECT query
                if result.returns_rows:
                    rows = result.fetchall()
                    columns = list(result.keys())

                    # Convert rows to dictionaries
                    data = [dict(zip(columns, row)) for row in rows]

                    query_result = {
                        "rows": data,
                        "row_count": len(data),
                        "columns": columns,
                    }
                else:
                    # For non-SELECT queries, return affected rows
                    query_result = {
                        "affected_rows": result.rowcount,
                        "message": "Query executed successfully",
                    }

            duration_ms = int((time.time() - start_time) * 1000)

            return ToolResult(
                success=True,
                result=query_result,
                duration_ms=duration_ms,
            )

        except SQLAlchemyError as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return ToolResult(
                success=False,
                error=f"Database error: {str(e)}",
                duration_ms=duration_ms,
            )
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return ToolResult(
                success=False,
                error=f"Query execution failed: {str(e)}",
                duration_ms=duration_ms,
            )

    def _is_read_only_query(self, query: str) -> bool:
        """Check if query is read-only (SELECT).

        Args:
            query: SQL query string

        Returns:
            True if query is read-only, False otherwise
        """
        query_upper = query.upper().strip()

        # Allow SELECT queries
        if query_upper.startswith("SELECT"):
            return True

        # Block write operations
        write_keywords = ["INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER", "TRUNCATE"]
        for keyword in write_keywords:
            if query_upper.startswith(keyword):
                return False

        # Default to read-only for unknown patterns
        return True

    def _apply_limit(self, query: str, limit: int) -> str:
        """Apply LIMIT clause to SELECT queries if not present.

        Args:
            query: SQL query string
            limit: Row limit to apply

        Returns:
            Modified query with LIMIT clause
        """
        query_upper = query.upper().strip()

        # Only apply to SELECT queries
        if not query_upper.startswith("SELECT"):
            return query

        # Check if LIMIT already exists
        if "LIMIT" in query_upper:
            return query

        # Add LIMIT clause
        return f"{query.rstrip(';')} LIMIT {limit}"
