# TASK-302: Implement LLM Cost Calculation Utilities

## Description

Create utilities for estimating and calculating LLM costs. This supports pre-call cost estimation for budget checks and post-call cost calculation for tracking.

## Requirements

- Create cost per token lookup tables:
  - COST_PER_M_INPUT: dict mapping model to $/1M input tokens
  - COST_PER_M_OUTPUT: dict mapping model to $/1M output tokens
  - Include major models: claude-sonnet-4, claude-opus-4, gpt-4, gpt-4-turbo, gpt-3.5-turbo, etc.
- Create `estimate_prompt_tokens(text: str)` function:
  - Simple approximation: len(text) // 4
  - Optional: use tiktoken for accurate counting
- Create `estimate_cost(model, input_tokens, output_tokens)` function
- Create `estimate_cost_before_call(model, messages, max_tokens)` function:
  - Estimate input tokens from messages
  - Estimate output as max_tokens // 2 (conservative)
- Create `calculate_cost_from_response(response)` function:
  - Use LiteLLM's completion_cost when available
  - Fallback to estimate_cost with actual token counts
- Create `get_provider_from_model(model: str)` function:
  - Parse model name to determine provider
  - Handle prefixed models (e.g., "azure/gpt-4")

## Acceptance Criteria

- [ ] Cost tables include all major models
- [ ] Token estimation reasonably accurate
- [ ] Pre-call estimation conservative (overestimates)
- [ ] Post-call calculation uses actual tokens
- [ ] Provider detection works for common patterns
- [ ] Unit tests verify calculations

## Dependencies

- None (utility module)

## Files to Create/Modify

- `src/omniforge/llm/cost.py` (new)
- `tests/llm/test_cost.py` (new)

## Estimated Complexity

Simple (2-3 hours)

## Key Considerations

- LLM pricing changes frequently - consider external config
- LiteLLM provides completion_cost() but may fail on unknown models
- Consider adding tiktoken as optional dependency
