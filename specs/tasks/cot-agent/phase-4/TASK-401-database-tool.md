# TASK-401: Implement Database Query Tool

## Description

Create the database query tool that provides SQL query execution through the unified tool interface. This enables agents to query databases with full visibility and audit logging.

## Requirements

- Create `DatabaseTool` class extending BaseTool:
  - Constructor accepting SQLAlchemy engine or connection string
  - Implement `definition` property:
    - name: "database"
    - type: ToolType.DATABASE
    - Parameters: query (SQL string), params (optional list), limit (optional int, default 100)
    - Appropriate timeout (30s default)
  - Implement `execute()` method:
    - Execute query with parameters
    - Limit result rows
    - Return row count and data
    - Handle SQL errors gracefully
  - Implement `validate_arguments()`:
    - Check query is non-empty
    - Basic SQL injection prevention (warn on dangerous patterns)
- Support read-only mode option for safety
- Include query execution time in result

## Acceptance Criteria

- [ ] SQL queries execute successfully
- [ ] Parameterized queries work correctly
- [ ] Result limit enforced
- [ ] Row count included in result
- [ ] SQL errors return ToolResult with error, not exception
- [ ] Read-only mode prevents write operations
- [ ] Unit tests with in-memory SQLite database

## Dependencies

- TASK-102 (for BaseTool, ToolDefinition)
- External: SQLAlchemy (already in project)

## Files to Create/Modify

- `src/omniforge/tools/builtin/database.py` (new)
- `tests/tools/builtin/test_database.py` (new)

## Estimated Complexity

Medium (4-5 hours)

## Key Considerations

- Use SQLAlchemy text() for safe parameterized queries
- Consider connection pooling for performance
- Sensitive query logging should be configurable
