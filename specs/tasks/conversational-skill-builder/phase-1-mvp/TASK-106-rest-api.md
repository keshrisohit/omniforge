# TASK-106: REST API Endpoints

**Phase**: 1 (MVP)
**Estimated Effort**: 10 hours
**Dependencies**: TASK-103, TASK-104, TASK-105
**Priority**: P0

## Objective

Create the FastAPI REST endpoints for conversation, agent CRUD, OAuth callbacks, and agent execution. These endpoints enable the frontend to interact with the builder service.

## Requirements

- Create conversation endpoints: start session, send message, complete OAuth
- Create agent CRUD endpoints: list, get, update, delete, run
- Create OAuth callback endpoints for Notion
- Implement request/response models with Pydantic
- Add tenant middleware for multi-tenancy
- Support streaming responses for conversation messages
- Add OpenAPI documentation for all endpoints

## Implementation Notes

- Reference technical plan Section 14 for API specifications
- Follow existing patterns in `src/omniforge/api/routes/`
- Use `src/omniforge/api/dependencies.py` for auth dependencies
- Streaming via `StreamingResponse` for conversation
- All endpoints require authentication via existing auth middleware
- Tenant ID extracted from JWT or header per existing tenant middleware

## Acceptance Criteria

- [ ] `POST /api/v1/conversation/start` creates new session and returns session_id
- [ ] `POST /api/v1/conversation/{session_id}/message` streams response with phases
- [ ] `POST /api/v1/conversation/{session_id}/oauth-complete` resumes conversation
- [ ] `GET /api/v1/builder/agents` lists user's agents
- [ ] `GET /api/v1/builder/agents/{agent_id}` returns agent details
- [ ] `POST /api/v1/builder/agents/{agent_id}/run` triggers execution
- [ ] `GET /oauth/callback/notion` handles OAuth callback
- [ ] All endpoints have OpenAPI documentation
- [ ] Integration tests verify full request/response cycle

## Files to Create/Modify

- `src/omniforge/api/routes/conversation.py` - Conversation endpoints
- `src/omniforge/api/routes/builder_agents.py` - Agent CRUD endpoints
- `src/omniforge/api/routes/oauth.py` - OAuth callback endpoints
- `src/omniforge/api/routes/__init__.py` - Register new routes
- `src/omniforge/api/app.py` - Include new routers (extend existing)
- `src/omniforge/api/schemas/conversation.py` - Request/response schemas
- `src/omniforge/api/schemas/builder.py` - Builder request/response schemas
- `tests/api/routes/test_conversation.py` - Conversation endpoint tests
- `tests/api/routes/test_builder_agents.py` - Agent endpoint tests
- `tests/api/routes/test_oauth.py` - OAuth callback tests
