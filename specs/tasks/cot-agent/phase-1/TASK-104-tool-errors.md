# TASK-104: Implement Tool Exception Hierarchy

## Description

Create a comprehensive exception hierarchy for tool-related errors. These exceptions provide clear error categorization for debugging, error handling, and user feedback.

## Requirements

- Create base `ToolError` exception class
- Create specific exceptions:
  - `ToolNotFoundError` - tool not in registry
  - `ToolAlreadyRegisteredError` - duplicate registration
  - `ToolValidationError` - argument validation failed
  - `ToolExecutionError` - execution failure
  - `ToolTimeoutError` - execution exceeded timeout
  - `RateLimitExceededError` - tenant quota exceeded
  - `CostBudgetExceededError` - task budget exceeded
  - `ModelNotApprovedError` - LLM model not in approved list
- Each exception should include:
  - Descriptive message
  - Relevant context (tool_name, tenant_id, etc.)
  - Error code for programmatic handling

## Acceptance Criteria

- [ ] All exceptions inherit from ToolError
- [ ] Each exception has descriptive __str__ output
- [ ] Error codes are unique and documented
- [ ] Exceptions are importable from tools module
- [ ] Unit tests verify exception messages and codes

## Dependencies

- None (can be developed in parallel with TASK-102/103)

## Files to Create/Modify

- `src/omniforge/tools/errors.py` (new)
- `tests/tools/test_errors.py` (new)

## Estimated Complexity

Simple (1-2 hours)

## Key Considerations

- Follow Python exception best practices
- Include error codes for API responses
- Consider i18n for error messages in future
