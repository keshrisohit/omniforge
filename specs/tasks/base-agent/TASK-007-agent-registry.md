# TASK-007: Agent Registry and Discovery

**Status**: Complete
**Complexity**: Simple
**Dependencies**: TASK-005, TASK-006
**Phase**: 2 - Task Persistence and Agent Registry

## Objective

Create an agent registry for discovering and managing registered agents.

## Requirements

1. Create `src/omniforge/agents/registry.py` with:
   - `AgentRegistry` class:
     - `register(agent: BaseAgent) -> None`
     - `unregister(agent_id: UUID) -> None`
     - `get(agent_id: UUID) -> BaseAgent`
     - `list_all() -> list[BaseAgent]`
     - `find_by_skill(skill_id: str) -> list[BaseAgent]`
     - `find_by_tag(tag: str) -> list[BaseAgent]`
   - Singleton or dependency-injectable pattern

2. Registry should work with AgentRepository for persistence

3. Support tenant isolation when tenant_id is provided

## Acceptance Criteria

- [x] Agents can be registered and retrieved by ID
- [x] Skill-based discovery returns matching agents
- [x] Tag-based discovery returns matching agents
- [x] AgentNotFoundError raised for missing agents
- [x] Tests in `tests/agents/test_registry.py`

## Implementation Notes

- Agent IDs use the `identity.id` (agent type ID) rather than instance UUIDs
- Registry uses dependency injection pattern with `AgentRepository`
- Tenant isolation implemented through optional `tenant_id` parameter
- 100% test coverage with 20 comprehensive tests
- All acceptance criteria met and validated
