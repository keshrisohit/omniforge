# TASK-006: Unit Tests
**Complexity:** Medium | **Depends on:** TASK-003

## Model Tests (`tests/chat/test_models.py`)

Test ChatRequest validation:
- `test_valid_message` - accepts valid message
- `test_empty_message_rejected` - raises ValidationError for ""
- `test_whitespace_message_rejected` - raises for "   "
- `test_max_length_enforced` - raises for 10001+ chars
- `test_optional_conversation_id` - None by default
- `test_valid_conversation_id` - accepts valid UUID

## SSE Streaming Tests (`tests/chat/test_streaming.py`)

Test formatting functions:
- `test_format_sse_event` - correct format `event: {type}\ndata: {json}\n\n`
- `test_format_chunk_event` - contains "event: chunk" and content
- `test_format_done_event` - contains conversation_id and tokens
- `test_format_error_event` - contains code and message

## Response Generator Tests (`tests/chat/test_response_generator.py`)

- `test_generate_stream_yields_chunks` - verify async iteration produces strings
- `test_count_tokens_returns_positive_int` - verify token counting

## Verification

```bash
pytest tests/chat/ -v --no-cov
pytest tests/chat/ --cov=src/omniforge/chat --cov-report=term-missing
```
