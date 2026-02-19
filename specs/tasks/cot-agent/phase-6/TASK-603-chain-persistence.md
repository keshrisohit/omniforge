# TASK-603: Implement Reasoning Chain Persistence

## Description

Create the database models and repository for persisting reasoning chains and steps. This enables audit trails, debugging, and chain replay functionality.

## Requirements

- Create SQLAlchemy ORM models:
  - `ReasoningChainModel`:
    - id (UUID PK)
    - task_id, agent_id (indexed)
    - status, started_at, completed_at
    - metrics (JSON)
    - child_chain_ids (JSON array)
    - tenant_id (indexed)
    - Composite indexes for tenant queries
  - `ReasoningStepModel`:
    - id (UUID PK)
    - chain_id (FK to chains, cascade delete)
    - step_number, type, timestamp
    - thinking, tool_call, tool_result, synthesis (JSON)
    - visibility (JSON)
    - parent_step_id (optional UUID)
    - Indexes for chain+step_number queries
- Create `ChainRepository` class:
  - `save(chain)` async method
  - `get_by_id(chain_id)` async method
  - `get_by_task(task_id)` async method
  - `list_by_tenant(tenant_id, limit, offset)` async method
  - `delete(chain_id)` async method (soft delete optional)

## Acceptance Criteria

- [ ] Chains persist with all steps
- [ ] Chain retrieval reconstructs full object
- [ ] Steps ordered by step_number
- [ ] Tenant isolation enforced
- [ ] Cascade delete removes steps with chain
- [ ] Pagination works for list queries
- [ ] Unit tests with in-memory SQLite

## Dependencies

- TASK-101 (for ReasoningChain, ReasoningStep models)
- Existing storage infrastructure

## Files to Create/Modify

- `src/omniforge/storage/models.py` (extend)
- `src/omniforge/storage/chain_repository.py` (new)
- `tests/storage/test_chain_repository.py` (new)

## Estimated Complexity

Medium (4-5 hours)

## Key Considerations

- Steps can be large - consider chunked loading
- JSON fields for flexibility with step data
- Consider retention policy/cleanup job
