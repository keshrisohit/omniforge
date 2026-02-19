# TASK-503: Implement Cost Record Persistence and ORM Models

## Description

Create the database models and repository for persisting cost records. This enables billing, usage reporting, and historical cost analysis.

## Requirements

- Create SQLAlchemy ORM models:
  - `CostRecordModel`:
    - id (UUID PK)
    - tenant_id (indexed)
    - task_id (indexed)
    - chain_id, step_id (optional UUIDs)
    - tool_name, cost_usd, tokens, model
    - created_at
    - Composite indexes for tenant+date queries
  - `ModelUsageModel` for aggregated reporting:
    - id (UUID PK)
    - tenant_id, model, date (unique together)
    - call_count, input_tokens, output_tokens, total_cost_usd
- Create `CostRepository` class:
  - `save(cost_record)` async method
  - `get_by_task(task_id)` async method
  - `get_by_tenant_date_range(tenant_id, start, end)` async method
  - `get_tenant_totals(tenant_id, start, end)` async method
- Create `ModelUsageRepository` for usage aggregation

## Acceptance Criteria

- [ ] ORM models create correct database tables
- [ ] Cost records persist and retrieve correctly
- [ ] Date range queries work efficiently
- [ ] Tenant isolation enforced in queries
- [ ] Usage aggregation updates correctly
- [ ] Indexes optimize common query patterns
- [ ] Unit tests with in-memory SQLite

## Dependencies

- TASK-502 (for CostRecord model)
- Existing storage infrastructure (Base, session management)

## Files to Create/Modify

- `src/omniforge/storage/models.py` (extend with new models)
- `src/omniforge/storage/cost_repository.py` (new)
- `tests/storage/test_cost_repository.py` (new)

## Estimated Complexity

Medium (4-5 hours)

## Key Considerations

- Use batch inserts for high-volume cost tracking
- Consider partitioning for large-scale deployments
- Aggregation queries should use database-level aggregation
