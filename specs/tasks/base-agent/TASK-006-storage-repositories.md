# TASK-006: Storage Layer and Repositories

**Status**: Pending
**Complexity**: Medium
**Dependencies**: TASK-001, TASK-002
**Phase**: 2 - Task Persistence and Agent Registry

## Objective

Implement repository pattern with in-memory storage for tasks and agents.

## Requirements

1. Create `src/omniforge/storage/` module with `__init__.py`

2. Create `src/omniforge/storage/base.py` with abstract interfaces:
   - `TaskRepository` protocol: get, save, update, delete, list_by_agent
   - `AgentRepository` protocol: get, save, delete, list_all, list_by_tenant

3. Create `src/omniforge/storage/memory.py` with in-memory implementations:
   - `InMemoryTaskRepository` - dict-based storage
   - `InMemoryAgentRepository` - dict-based storage
   - Thread-safe with asyncio locks

4. Create `src/omniforge/tasks/manager.py`:
   - `TaskManager` class that uses TaskRepository
   - `create_task(agent_id, request) -> Task`
   - `get_task(task_id) -> Task`
   - `update_task_state(task_id, state) -> Task`
   - `process_task(task) -> AsyncIterator[TaskEvent]` - delegates to agent

## Acceptance Criteria

- [ ] Repository interfaces use Protocol (structural typing)
- [ ] In-memory implementation passes all repository tests
- [ ] TaskManager handles task lifecycle correctly
- [ ] Tests in `tests/storage/` and `tests/tasks/test_manager.py`
- [ ] Storage can be swapped without changing TaskManager
