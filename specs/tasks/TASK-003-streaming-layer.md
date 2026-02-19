# TASK-003: Streaming Layer
**Complexity:** Medium | **Depends on:** TASK-002

## SSE Formatting (`src/omniforge/chat/streaming.py`)

Implement SSE event formatting utilities:

1. **format_sse_event(event_type: str, data: Any) -> str**
   - Format: `event: {type}\ndata: {json}\n\n`
   - JSON-serialize data if not already a string

2. **format_chunk_event(content: str) -> str**
   - Uses ChunkEvent model
   - Returns formatted SSE with event type "chunk"

3. **format_done_event(done_event: DoneEvent) -> str**
   - Use `model_dump(mode="json")` for UUID serialization
   - Event type "done"

4. **format_error_event(error_event: ErrorEvent) -> str**
   - Event type "error"

5. **stream_with_error_handling(stream: AsyncIterator[str]) -> AsyncIterator[str]**
   - Wraps stream, catches exceptions
   - Yields error event on exception instead of raising

## Response Generator (`src/omniforge/chat/response_generator.py`)

Placeholder implementation for v1:

1. **ResponseGenerator class**
   - `async def generate_stream(self, message: str) -> AsyncIterator[str]`
     - Yields placeholder response parts: "Thank you...", "You said: ...", etc.
   - `def count_tokens(self, text: str) -> int`
     - Simple approximation: `max(1, len(text) // 4)`

## Verification

```bash
mypy src/omniforge/chat/streaming.py src/omniforge/chat/response_generator.py
python -c "from omniforge.chat.streaming import format_chunk_event; print(format_chunk_event('test'))"
```
