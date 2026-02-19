# TASK-004: Chat Service
**Complexity:** Medium | **Depends on:** TASK-003

## ChatService (`src/omniforge/chat/service.py`)

Orchestrates chat request processing:

1. **__init__(self, response_generator: ResponseGenerator | None = None)**
   - Accept optional ResponseGenerator for dependency injection (testing)
   - Default to creating new ResponseGenerator

2. **async def process_chat(self, request: ChatRequest) -> AsyncIterator[str]**
   - Generate or use provided `conversation_id`
   - Stream response chunks via `_response_generator.generate_stream()`
   - Accumulate total content for token counting
   - Yield formatted SSE chunk events
   - On completion: yield done event with conversation_id and usage
   - On exception: yield error event with code "processing_error"

## Key Implementation Details

- Use `uuid4()` if no conversation_id provided
- Import and use all formatting functions from streaming.py
- Ensure proper async iteration with `async for`

## Verification

```bash
mypy src/omniforge/chat/service.py
python -c "from omniforge.chat.service import ChatService; print(ChatService)"
```
