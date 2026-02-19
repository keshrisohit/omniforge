# TASK-004: Implement LLM Intent Analyzer

## Description
Create the LLM-powered intent classification module that uses litellm for structured JSON output. Includes timeout configuration (Review ISSUE 6) and proper error handling.

## What to Build

### `src/omniforge/conversation/intent_analyzer.py`
- `IntentAnalysisError` exception class
- `LLMIntentAnalyzer` class with:
  - Constructor: `model` (default from env `OMNIFORGE_INTENT_MODEL` or "gpt-4o-mini"), `temperature` (0.1), `max_tokens` (500), `timeout` (from env `OMNIFORGE_INTENT_TIMEOUT_SEC` or 5.0)
  - `async analyze(message, conversation_history, available_agents) -> RoutingDecision`
  - `_build_system_prompt(available_agents)` -- intent classification prompt with all 7 action types
  - `_build_messages(system_prompt, current_message, history)` -- builds LLM message list
  - `_parse_response(content: str) -> RoutingDecision` -- defensive JSON parsing

## Key Requirements
- Uses `asyncio.wait_for()` with configurable timeout (Review ISSUE 6)
- `response_format={"type": "json_object"}` for structured output via litellm
- Defensive parsing: unknown action_type defaults to UNKNOWN, confidence clamped to [0.0, 1.0]
- Invalid JSON raises `IntentAnalysisError`
- LLM call failure raises `IntentAnalysisError` (caller handles fallback)
- Imports `ActionType` and `RoutingDecision` from `routing.models` (no circular dependency)
- Uses `format_context_for_llm` from `conversation.context`
- Model configurable via `OMNIFORGE_INTENT_MODEL` env var

## Dependencies
- TASK-001 (routing models, conversation models)
- TASK-003 (format_context_for_llm)

## Success Criteria
- Mock litellm.acompletion to return known JSON -- parsed correctly
- Invalid JSON raises IntentAnalysisError
- Unknown action_type defaults to ActionType.UNKNOWN
- Confidence values clamped to [0.0, 1.0]
- Timeout triggers IntentAnalysisError
- System prompt includes available agents when provided
- Conversation history formatted correctly in messages
- API error raises IntentAnalysisError
- `tests/conversation/test_intent_analyzer.py`

## Complexity
Medium
