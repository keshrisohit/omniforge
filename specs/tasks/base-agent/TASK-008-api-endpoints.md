# TASK-008: Agent and Task API Endpoints

**Status**: Completed
**Complexity**: Complex
**Dependencies**: TASK-005, TASK-006, TASK-007
**Phase**: 2 - Task Persistence and Agent Registry

## Objective

Implement FastAPI routes for agent discovery and task management with SSE streaming.

## Requirements

1. Create `src/omniforge/api/routes/agents.py`:
   - `GET /.well-known/agent-card.json` - default agent card
   - `GET /api/v1/agents` - list registered agents
   - `GET /api/v1/agents/{agent_id}` - get agent card

2. Create `src/omniforge/api/routes/tasks.py`:
   - `POST /api/v1/agents/{agent_id}/tasks` - create task, return SSE stream
   - `GET /api/v1/agents/{agent_id}/tasks/{task_id}` - get task status
   - `POST /api/v1/agents/{agent_id}/tasks/{task_id}/send` - send message, return SSE stream
   - `POST /api/v1/agents/{agent_id}/tasks/{task_id}/cancel` - cancel task
   - `GET /api/v1/agents/{agent_id}/tasks` - list tasks

3. Update `src/omniforge/api/app.py` to include new routers

4. Update error handler middleware to handle AgentError

## Acceptance Criteria

- [x] Agent card endpoint returns valid A2A JSON
- [x] Task creation returns SSE stream with proper headers
- [x] Client disconnect is handled gracefully (check request.is_disconnected)
- [x] Integration tests in `tests/api/test_agent_routes.py` and `tests/api/test_task_routes.py`
- [x] SSE headers: Cache-Control, Connection, X-Accel-Buffering
