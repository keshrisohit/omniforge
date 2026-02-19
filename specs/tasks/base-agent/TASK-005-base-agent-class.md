# TASK-005: BaseAgent Abstract Class

**Status**: Pending
**Complexity**: Medium
**Dependencies**: TASK-001, TASK-002, TASK-003, TASK-004
**Phase**: 1 - Core Agent Interface

## Objective

Implement the BaseAgent abstract class that all OmniForge agents extend.

## Requirements

1. Create `src/omniforge/agents/base.py` with:
   - `BaseAgent` abstract class with:
     - Class-level: `identity: AgentIdentity`, `capabilities: AgentCapabilities`, `skills: list[AgentSkill]`
     - Instance `_id: UUID` (generated or explicit)
     - `get_agent_card(service_endpoint: str) -> AgentCard` method
     - Abstract `process_task(task: Task) -> AsyncIterator[TaskEvent]` method
     - Default `handle_message(task_id, message)` implementation
     - Default `cancel_task(task_id)` stub

2. Agent must be instantiable with optional explicit ID

3. AgentCard generation should populate all fields from class attributes

## Acceptance Criteria

- [ ] BaseAgent cannot be instantiated directly (abstract)
- [ ] Subclass with minimal implementation works (name, process_task)
- [ ] `get_agent_card()` returns valid A2A AgentCard
- [ ] Tests include concrete test agent subclass
- [ ] Tests in `tests/agents/test_base.py` covering:
  - Unique ID generation
  - Explicit ID assignment
  - Agent card generation
  - Abstract method enforcement
