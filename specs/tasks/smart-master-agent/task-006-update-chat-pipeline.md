# TASK-006: Update Chat Pipeline (ChatService + ResponseGenerator + MasterResponseGenerator)

## Description
Wire conversation storage and context passing through the chat pipeline. Add error handling for storage failures (Review ISSUE 5) and proper conversation_id validation (Review ISSUE 3).

## What to Build

### 1. Modify `src/omniforge/chat/service.py` (ChatService)
- Add constructor params: `conversation_repo: Optional[ConversationRepository] = None`, `tenant_id: Optional[str] = None`
- In `process_chat`:
  - If `conversation_repo` is set and `request.conversation_id` is provided, validate conversation exists and belongs to tenant. Raise error if not found (Review ISSUE 3).
  - If no `conversation_id`, create new conversation
  - Store user message (wrapped in try/except -- continue on failure, Review ISSUE 5)
  - Retrieve recent messages (wrapped in try/except -- fall back to empty list on failure)
  - Pass `conversation_history` to `generate_stream`
  - After response, store assistant message (wrapped in try/except)

### 2. Modify `src/omniforge/chat/response_generator.py`
- Add `conversation_history: Optional[list] = None` param to `generate_stream`
- Forward to master generator if present

### 3. Modify `src/omniforge/chat/master_response_generator.py`
- Accept `conversation_history` in `generate_stream`
- Call `assemble_context` on history before passing to task
- Include context messages in task creation

## Key Requirements
- **Backward compatible**: All new params default to None. No repo = no storage, no context (existing behavior)
- Storage failures MUST NOT break the response (try/except with logging, Review ISSUE 5)
- When `conversation_id` is provided but not found, raise ValueError (Review ISSUE 3)
- When `conversation_id` is None, auto-create conversation
- `tenant_id` defaults to "default-tenant"

## Dependencies
- TASK-001 (conversation models, repository Protocol)
- TASK-002 (repository implementations -- needed for tests)
- TASK-003 (context assembler)

## Success Criteria
- ChatService with `repo=None` behaves identically to current (backward compat test)
- ChatService with in-memory repo stores and retrieves messages
- Invalid conversation_id raises error
- Storage failure logs warning but response still delivered
- History flows from ChatService -> ResponseGenerator -> MasterResponseGenerator -> Task
- `tests/chat/test_chat_service_conversation.py`

## Complexity
Medium
