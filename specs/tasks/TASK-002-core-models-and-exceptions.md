# TASK-002: Core Models and Exceptions
**Complexity:** Medium | **Depends on:** TASK-001

## Pydantic Models (`src/omniforge/chat/models.py`)

Create all request/response models:

1. **ChatRequest**
   - `message: str` - Field with min_length=1, max_length=10000
   - `conversation_id: Optional[UUID]` - default None
   - Add `@field_validator("message")` to reject whitespace-only strings

2. **ChunkEvent** - `content: str`

3. **UsageInfo** - `tokens: int`

4. **DoneEvent** - `conversation_id: UUID`, `usage: UsageInfo`

5. **ErrorEvent** - `code: str`, `message: str`

## Custom Exceptions (`src/omniforge/chat/errors.py`)

Create exception hierarchy:

1. **ChatError(Exception)** - Base class with `code`, `message`, `status_code` attributes

2. **ValidationError(ChatError)** - status_code=400, code="validation_error"

3. **MessageTooLongError(ChatError)** - status_code=400, code="message_too_long"

4. **InternalError(ChatError)** - status_code=500, code="internal_error"

## Verification

```bash
mypy src/omniforge/chat/models.py src/omniforge/chat/errors.py
python -c "from omniforge.chat.models import ChatRequest; ChatRequest(message='test')"
```
