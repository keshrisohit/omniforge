# TASK-002: Implement Conversation Repositories (SQLite + InMemory)

## Description
Implement both the SQLAlchemy-backed SQLite repository and the in-memory repository for conversation storage. Both must enforce tenant isolation on all read operations.

## What to Build

### 1. `src/omniforge/conversation/orm.py`
- `ConversationModel` ORM model extending `storage.database.Base`
- `ConversationMessageModel` ORM model with foreign key to conversations
- Composite indexes: `(tenant_id, user_id)`, `(tenant_id, updated_at)`, `(conversation_id, created_at)`
- Use `conversation_metadata` / `message_metadata` column names (avoid SQLAlchemy reserved word)

### 2. `src/omniforge/conversation/sqlite_repository.py`
- `SQLiteConversationRepository` class using existing `Database` for session management
- All read methods filter by `tenant_id` (security requirement from Review ISSUE 2)
- `add_message` atomically updates `conversation.updated_at`
- `get_recent_messages` fetches DESC then reverses for chronological output

### 3. `src/omniforge/conversation/memory_repository.py`
- `InMemoryConversationRepository` with dict storage and `asyncio.Lock`
- Same tenant isolation logic as SQLite implementation
- Follow pattern from `storage/memory.py`

## Key Requirements
- Reuse `Database` and `Base` from `storage/database.py`
- `get_recent_messages(conversation_id, tenant_id, limit)` must validate tenant owns conversation
- `get_conversation(conversation_id, tenant_id)` returns None for wrong tenant (not an exception)
- ORM tables auto-created via `Base.metadata.create_all()`

## Dependencies
- TASK-001 (conversation models and repository Protocol)

## Success Criteria
- Both repositories implement the `ConversationRepository` Protocol
- Tenant isolation: get_conversation with wrong tenant_id returns None
- Messages stored and retrieved in chronological order
- `add_message` updates conversation.updated_at
- `list_conversations` returns results ordered by updated_at DESC
- Tests use in-memory SQLite (`sqlite+aiosqlite:///:memory:`)
- `tests/conversation/test_sqlite_repository.py` and `tests/conversation/test_memory_repository.py`

## Complexity
Medium
