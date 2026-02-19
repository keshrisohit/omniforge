# TASK-303: Implement LLM Tool with LiteLLM Integration

## Description

Create the LLM tool that wraps LiteLLM to provide unified access to 100+ LLM providers. This is the core tool for agent reasoning, supporting streaming, cost tracking, and enterprise controls.

## Requirements

- Create `LLMTool` class extending StreamingTool:
  - Constructor accepting optional LLMConfig
  - `_setup_litellm()` method to configure LiteLLM:
    - Set API keys from config
    - Disable LiteLLM's internal retries (we handle in executor)
  - Implement `definition` property returning ToolDefinition:
    - name: "llm"
    - type: ToolType.LLM
    - Parameters: model, prompt, messages, temperature, max_tokens, system
    - timeout_ms: 60000
    - Retry config for LLM errors
  - Implement `execute()` method:
    - Resolve model (use default if not specified)
    - Check approved_models list (return error if not approved)
    - Build messages from prompt or use provided messages
    - Check cost budget before call (if context has budget)
    - Call litellm.acompletion()
    - Extract response content, usage, and cost
    - Return ToolResult with LLM-specific fields
  - Implement `execute_streaming()` method:
    - Same as execute but with stream=True
    - Yield token chunks from response
  - Implement `_estimate_cost()` and `_estimate_cost_from_tokens()`
  - Implement `_get_provider()` helper

## Acceptance Criteria

- [ ] LLM calls work through unified tool interface
- [ ] Model defaults work correctly
- [ ] Approved models enforced (returns error for unapproved)
- [ ] Cost estimated before call for budget checking
- [ ] Actual cost calculated from response
- [ ] Streaming yields tokens correctly
- [ ] Token counts included in ToolResult
- [ ] Integration test with mocked LiteLLM

## Dependencies

- TASK-102 (for StreamingTool, ToolDefinition)
- TASK-301 (for LLMConfig)
- TASK-302 (for cost utilities)
- External: litellm >= 1.50.0

## Files to Create/Modify

- `src/omniforge/tools/builtin/__init__.py` (new)
- `src/omniforge/tools/builtin/llm.py` (new)
- `tests/tools/builtin/__init__.py` (new)
- `tests/tools/builtin/test_llm.py` (new)

## Estimated Complexity

Complex (6-8 hours)

## Key Considerations

- Use litellm.acompletion for async calls
- Handle provider-specific response formats
- Cost tracking is critical for enterprise use
- Consider connection pooling for performance
