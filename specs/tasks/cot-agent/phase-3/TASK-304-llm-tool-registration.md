# TASK-304: Register LLM Tool and Create Default Registry Setup

## Description

Create the default tool registry setup that includes the LLM tool and provides a convenient way to initialize the tool system with built-in tools.

## Requirements

- Create `setup_default_tools(registry: ToolRegistry, config: LLMConfig)` function:
  - Creates and registers LLMTool with provided config
  - Returns the configured registry
- Create `get_default_tool_registry()` function:
  - Returns singleton registry with default tools registered
  - Uses lazy initialization
- Update tools/__init__.py exports:
  - Export BaseTool, ToolRegistry, ToolExecutor
  - Export setup_default_tools, get_default_tool_registry
  - Export LLMTool from builtin
- Ensure LLM tool is discoverable via registry.list_tools()

## Acceptance Criteria

- [ ] LLM tool registered in default registry
- [ ] get_default_tool_registry() returns consistent instance
- [ ] setup_default_tools() configurable for custom registries
- [ ] All public APIs exported from tools module
- [ ] Integration test verifies LLM tool execution through registry

## Dependencies

- TASK-103 (for ToolRegistry)
- TASK-303 (for LLMTool)
- TASK-301 (for LLMConfig)

## Files to Create/Modify

- `src/omniforge/tools/__init__.py` (update)
- `src/omniforge/tools/builtin/__init__.py` (update)
- `tests/tools/test_default_setup.py` (new)

## Estimated Complexity

Simple (1-2 hours)

## Key Considerations

- Default registry should be thread-safe singleton
- Consider allowing custom tools in default setup
- Exports should be documented in module docstring
