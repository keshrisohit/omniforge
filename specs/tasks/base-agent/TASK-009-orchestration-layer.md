# TASK-009: Agent-to-Agent Orchestration

**Status**: Complete
**Complexity**: Complex
**Dependencies**: TASK-007, TASK-008
**Phase**: 3 - Agent-to-Agent Communication

## Objective

Enable agents to discover and delegate tasks to other agents.

## Requirements

1. Create `src/omniforge/orchestration/` module with `__init__.py`

2. Create `src/omniforge/orchestration/discovery.py`:
   - `AgentDiscoveryService` - finds agents by skill/capability
   - Uses AgentRegistry internally
   - Supports filtering by tenant context

3. Create `src/omniforge/orchestration/client.py`:
   - `A2AClient` - outbound HTTP client for agent communication
   - `send_task(agent_card: AgentCard, request: TaskCreateRequest) -> AsyncIterator[TaskEvent]`
   - Handles SSE response parsing

4. Create `src/omniforge/orchestration/router.py`:
   - `TaskRouter` - routes tasks between agents
   - Tracks parent/child task relationships
   - Aggregates results from delegated tasks

## Acceptance Criteria

- [x] Agent A can discover Agent B by skill
- [x] Agent A can create subtask on Agent B
- [x] Parent task tracks child task IDs
- [x] Child task results flow back to parent
- [x] Tests in `tests/orchestration/` covering discovery and delegation
