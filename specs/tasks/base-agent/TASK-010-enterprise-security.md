# TASK-010: Enterprise Security Features

**Status**: Pending
**Complexity**: Complex
**Dependencies**: TASK-008
**Phase**: 4 - Enterprise Features

## Objective

Implement multi-tenancy isolation and RBAC for agent operations.

## Requirements

1. Create `src/omniforge/security/` module with `__init__.py`

2. Create `src/omniforge/security/tenant.py`:
   - `TenantContext` with ContextVar for current tenant
   - `tenant_middleware` - extracts tenant from X-Tenant-ID header
   - `get_tenant_id()` helper function

3. Create `src/omniforge/security/rbac.py`:
   - `Permission` enum (agent:create/read/update/delete, task:create/read/cancel, skill:invoke)
   - `Role` enum (viewer, operator, developer, admin)
   - `ROLE_PERMISSIONS` mapping
   - `check_permission(user, permission) -> bool`

4. Create `src/omniforge/security/auth.py`:
   - API key validation logic
   - Bearer token validation stub (for future OAuth)

5. Create `src/omniforge/api/middleware/tenant.py`:
   - FastAPI middleware for tenant context

6. Update API routes to enforce tenant isolation

## Acceptance Criteria

- [ ] Tenant A cannot access Tenant B's agents or tasks
- [ ] RBAC permissions are checked on protected endpoints
- [ ] Unauthorized access returns 403
- [ ] Tests in `tests/security/` covering isolation and permissions
- [ ] Middleware properly sets/clears context
