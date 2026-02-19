# TASK-007: Integration Tests
**Complexity:** Medium | **Depends on:** TASK-005

## Test Fixtures (`tests/conftest.py`)

1. **@pytest.fixture def app()** - returns `create_app()`

2. **@pytest.fixture def client(app)** - returns `TestClient(app)`

3. **@pytest.fixture async def async_client(app)** - yields `AsyncClient(app=app, base_url="http://test")`

## Chat Endpoint Tests (`tests/api/test_chat_endpoint.py`)

Test POST /api/v1/chat:
- `test_valid_message_returns_stream` - 200, content-type is event-stream
- `test_empty_message_returns_422` - validation error
- `test_whitespace_message_returns_422` - validation error
- `test_message_too_long_returns_422` - 10001+ chars rejected
- `test_stream_contains_chunk_events` - response has "event: chunk"
- `test_stream_ends_with_done_event` - response has "event: done"
- `test_done_event_contains_conversation_id` - conversation_id in response
- `test_conversation_id_preserved` - provided UUID returned in done event

## Service Tests (`tests/chat/test_service.py`)

- `test_process_chat_yields_chunks` - verify chunk events yielded
- `test_process_chat_ends_with_done` - verify done event at end
- `test_process_chat_generates_conversation_id` - UUID generated if not provided
- `test_process_chat_preserves_conversation_id` - provided UUID used

## Health Endpoint Test (`tests/api/test_health.py`)

- `test_health_returns_healthy` - GET /health returns `{"status": "healthy"}`

## Verification

```bash
pytest tests/ -v
pytest tests/ --cov=src/omniforge --cov-report=term-missing
```
