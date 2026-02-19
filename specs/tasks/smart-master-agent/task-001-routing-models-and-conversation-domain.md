# TASK-001: Extract Routing Models and Create Conversation Domain Models

## Description
Extract `ActionType` and `RoutingDecision` into a shared `routing/models.py` module to prevent circular dependencies (Review ISSUE 1). Create the conversation domain models (`Conversation`, `Message`, `MessageRole`) and the repository Protocol interface.

## What to Build

### 1. `src/omniforge/routing/__init__.py` and `src/omniforge/routing/models.py`
- Move `ActionType` enum and `RoutingDecision` dataclass from `agents/master_agent.py` to `routing/models.py`
- Update `agents/master_agent.py` to import from `routing.models` instead

### 2. `src/omniforge/conversation/__init__.py` and `src/omniforge/conversation/models.py`
- `MessageRole` enum (user, assistant, system)
- `Conversation` Pydantic model (id, tenant_id, user_id, title, created_at, updated_at, metadata)
- `Message` Pydantic model (id, conversation_id, role, content, created_at, metadata)

### 3. `src/omniforge/conversation/repository.py`
- `ConversationRepository` Protocol with async methods
- All read methods MUST require `tenant_id` parameter (Review ISSUE 2): `get_conversation`, `get_recent_messages`, `get_messages`, `list_conversations`
- Methods: `create_conversation`, `get_conversation`, `list_conversations`, `update_conversation`, `add_message`, `get_messages`, `get_recent_messages`

## Key Requirements
- Python 3.9+ compatible (`Optional[X]` not `X | None`)
- All fields validated via Pydantic
- `tenant_id` required on ALL read operations (security critical per review)
- No imports from `chat/` or `agents/` packages in conversation models
- `routing/models.py` must be pure (no internal imports beyond stdlib)

## Dependencies
- None (first task)

## Success Criteria
- `ActionType` and `RoutingDecision` live in `routing/models.py`
- `master_agent.py` imports from `routing.models` and all existing tests still pass
- Conversation models validate required fields (id, tenant_id, user_id)
- Repository Protocol defines all methods with tenant_id on read operations
- Unit tests: model creation, validation, enum values, field constraints
- `tests/routing/test_models.py` and `tests/conversation/test_models.py`

## Complexity
Medium
