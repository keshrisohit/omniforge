# TASK-606: Extend RBAC for Tool and Chain Permissions

## Description

Extend the existing RBAC system with new permissions for tool execution, chain access, and enterprise controls. This enables fine-grained access control for the CoT system.

## Requirements

- Add new permissions to Permission enum:
  - TOOL_EXECUTE - can execute tools
  - TOOL_REGISTER - can register new tools
  - TOOL_CONFIGURE - can configure tool settings
  - CHAIN_READ - can read reasoning chains
  - CHAIN_READ_FULL - can read hidden steps in chains
  - CHAIN_EXPORT - can export chains for compliance
  - RATE_LIMIT_CONFIGURE - can configure rate limits
  - COST_VIEW - can view cost reports
  - COST_CONFIGURE - can configure cost budgets
- Create role templates with appropriate permissions:
  - DEVELOPER: full tool and chain access
  - END_USER: limited visibility
  - AUDITOR: read-all including hidden
  - ADMIN: full access
- Update permission checking in:
  - ToolExecutor (check TOOL_EXECUTE)
  - Chain endpoints (check CHAIN_READ, CHAIN_READ_FULL)
  - Enterprise endpoints (check respective permissions)

## Acceptance Criteria

- [ ] New permissions defined and documented
- [ ] Role templates include appropriate permissions
- [ ] Permission checks enforced in tool execution
- [ ] Permission checks enforced in chain access
- [ ] CHAIN_READ_FULL required for hidden steps
- [ ] Admin role has all permissions
- [ ] Unit tests verify permission enforcement

## Dependencies

- TASK-105 (for ToolExecutor)
- TASK-604 (for chain endpoints)
- Existing RBAC infrastructure

## Files to Create/Modify

- `src/omniforge/security/rbac.py` (extend)
- `tests/security/test_rbac_extensions.py` (new)

## Estimated Complexity

Simple (2-3 hours)

## Key Considerations

- Follow existing RBAC patterns
- Document permission requirements per endpoint
- Consider permission inheritance for roles
