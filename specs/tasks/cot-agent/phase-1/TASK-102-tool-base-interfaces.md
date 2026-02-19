# TASK-102: Implement Tool Base Interfaces and Models

## Description

Create the unified tool interface that all tools must implement. This includes the BaseTool abstract class, ToolDefinition for registration, and supporting models for tool configuration, execution context, and results.

## Requirements

- Create `ToolParameter` model for parameter specifications
- Create `ToolRetryConfig` with max_retries, backoff_ms, backoff_multiplier, retryable_errors
- Create `ToolVisibilityConfig` with default_level, summary_template, sensitive_fields
- Create `ToolPermissions` with required_roles, audit_level
- Create `ToolDefinition` model containing:
  - name, type, description, version
  - List of parameters with types
  - timeout_ms, retry_config, cache_ttl_seconds
  - visibility and permissions configuration
- Create `ToolCallContext` with correlation_id, task_id, agent_id, tenant_id, chain_id, budget constraints
- Create `ToolResult` with success, result, error, duration_ms, LLM-specific fields
- Create `BaseTool` abstract class with:
  - Abstract `definition` property
  - Abstract `execute()` method
  - Default `validate_arguments()` method
  - Default `generate_summary()` method
- Create `StreamingTool` subclass with `execute_streaming()` method

## Acceptance Criteria

- [ ] ToolDefinition validates all required fields
- [ ] BaseTool enforces interface contract
- [ ] ToolResult captures all execution metadata
- [ ] validate_arguments() checks required parameters
- [ ] generate_summary() uses template when available
- [ ] Type hints pass mypy strict mode
- [ ] Unit tests cover interface contracts

## Dependencies

- TASK-101 (for ToolType, VisibilityLevel enums)

## Files to Create/Modify

- `src/omniforge/tools/__init__.py` (new)
- `src/omniforge/tools/base.py` (new)
- `src/omniforge/tools/models.py` (new - if separating models)
- `tests/tools/__init__.py` (new)
- `tests/tools/test_base.py` (new)

## Estimated Complexity

Medium (4-6 hours)

## Key Considerations

- BaseTool should be generic for type safety
- Consider async context manager pattern for resources
- Retry configuration should be sensible defaults
