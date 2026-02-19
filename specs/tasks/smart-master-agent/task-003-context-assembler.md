# TASK-003: Implement Context Assembler

## Description
Implement pure functions for assembling conversation context from message history. Simplified for v1 per review feedback (ISSUE 4) -- use message count with optional token budgeting.

## What to Build

### `src/omniforge/conversation/context.py`
- `estimate_tokens(text: str) -> int`: Token estimation using tiktoken with char/4 fallback. Log warning on fallback (Review ISSUE 9).
- `assemble_context(messages, max_messages=20) -> list[Message]`: Return most recent N messages in chronological order. Simple message-count approach for v1.
- `format_context_for_llm(messages) -> list[dict[str, str]]`: Convert Message objects to `{"role": "...", "content": "..."}` dicts for LLM API calls.
- `_format_message(msg) -> str`: Format single message for token counting.

## Key Requirements
- All functions are pure (no side effects, no state)
- `estimate_tokens` tries tiktoken first, logs warning and falls back to `len(text) // 3` (more conservative per review)
- `assemble_context` is simple for v1: just `messages[-max_messages:]`
- `format_context_for_llm` handles both `MessageRole` enum and raw string roles
- Python 3.9+ compatible

## Dependencies
- TASK-001 (conversation models -- `Message`, `MessageRole`)

## Success Criteria
- Empty message list returns empty list
- Messages within limit included fully
- Messages exceeding limit are truncated from oldest
- Token estimation works with and without tiktoken
- `format_context_for_llm` produces correct `{"role": "...", "content": "..."}` format
- Edge cases: single message, empty content, very long messages
- `tests/conversation/test_context.py`

## Complexity
Simple
