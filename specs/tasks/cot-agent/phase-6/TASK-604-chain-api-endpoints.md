# TASK-604: Implement Chain Management API Endpoints

## Description

Create the REST API endpoints for accessing reasoning chains. These enable clients to retrieve chains for debugging, audit, and visualization.

## Requirements

- Create chain routes in FastAPI:
  - `GET /api/v1/chains/{chain_id}`:
    - Returns full chain with steps
    - Respects visibility based on user role
  - `GET /api/v1/tasks/{task_id}/chain`:
    - Returns chain for a specific task
    - 404 if no chain exists
  - `GET /api/v1/chains/{chain_id}/steps`:
    - Paginated list of steps
    - Parameters: limit, offset, type filter
  - `GET /api/v1/tenants/{tenant_id}/chains`:
    - List chains for tenant
    - Parameters: limit, offset, status filter, date range
- Response models:
  - ChainResponse (full chain)
  - ChainListResponse (list with pagination metadata)
  - StepListResponse (paginated steps)
- Apply visibility filtering based on authenticated user's role
- Require authentication for all endpoints

## Acceptance Criteria

- [ ] All endpoints return correct data
- [ ] Visibility filtering applied per user role
- [ ] Pagination works correctly
- [ ] 404 returned for non-existent chains
- [ ] 403 returned for unauthorized access
- [ ] Filters (status, date range) work
- [ ] API tests cover all endpoints

## Dependencies

- TASK-603 (for ChainRepository)
- TASK-601 (for VisibilityController)
- Existing API infrastructure (FastAPI app, auth)

## Files to Create/Modify

- `src/omniforge/api/routes/chains.py` (new)
- `src/omniforge/api/app.py` (register routes)
- `tests/api/test_chains.py` (new)

## Estimated Complexity

Medium (4-5 hours)

## Key Considerations

- Use Pydantic response models for validation
- Apply tenant context from auth middleware
- Consider caching for frequently accessed chains
