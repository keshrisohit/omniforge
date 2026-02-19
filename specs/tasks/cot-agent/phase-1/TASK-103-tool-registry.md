# TASK-103: Implement Tool Registry

## Description

Create the ToolRegistry class that provides centralized tool registration, discovery, and retrieval. This is the central repository where all tools are registered and looked up during execution.

## Requirements

- Create `ToolRegistry` class with:
  - Internal dictionaries for tools and definitions
  - `register(tool, replace=False)` method
  - `unregister(name)` method
  - `get(name)` method returning BaseTool
  - `get_definition(name)` method returning ToolDefinition
  - `list_tools(tool_type=None)` method with optional filtering
  - `has_tool(name)` method for existence check
  - `clear()` method for cleanup
- Create module-level functions:
  - `get_default_registry()` for global singleton access
  - `register_tool(tool, replace=False)` convenience function
- Implement proper error handling with custom exceptions

## Acceptance Criteria

- [ ] Tools can be registered and retrieved by name
- [ ] Duplicate registration raises ToolAlreadyRegisteredError (unless replace=True)
- [ ] Missing tool lookup raises ToolNotFoundError
- [ ] list_tools() correctly filters by tool_type
- [ ] Default registry is singleton per process
- [ ] Thread safety for concurrent access (if needed)
- [ ] Unit tests cover all registry operations

## Dependencies

- TASK-102 (for BaseTool, ToolDefinition)
- TASK-104 (for error types - can be developed in parallel)

## Files to Create/Modify

- `src/omniforge/tools/registry.py` (new)
- `tests/tools/test_registry.py` (new)

## Estimated Complexity

Simple (2-4 hours)

## Key Considerations

- Consider thread safety if registry is modified at runtime
- Registry should be lightweight and fast for lookups
- Consider lazy initialization of default registry
