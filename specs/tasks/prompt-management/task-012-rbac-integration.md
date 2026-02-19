# TASK-012: Implement RBAC and Agent Integration

## Objective

Extend the security module with prompt permissions and integrate prompt configuration with the agent system.

## Requirements

### RBAC Extensions (`src/omniforge/security/rbac.py` modification)

**New Permissions**:
Add to Permission enum:
- `PROMPT_CREATE`, `PROMPT_READ`, `PROMPT_UPDATE`, `PROMPT_DELETE`, `PROMPT_COMPOSE`
- `EXPERIMENT_CREATE`, `EXPERIMENT_READ`, `EXPERIMENT_UPDATE`, `EXPERIMENT_DELETE`
- `CACHE_CLEAR`, `CACHE_STATS`

**Role Permission Mapping**:
- VIEWER: PROMPT_READ, EXPERIMENT_READ
- OPERATOR: PROMPT_READ, PROMPT_COMPOSE, EXPERIMENT_READ
- DEVELOPER: PROMPT_CREATE/READ/UPDATE, PROMPT_COMPOSE, EXPERIMENT_CREATE/READ/UPDATE
- ADMIN: All prompt and experiment permissions including DELETE, CACHE_*

### Layer-Based Access Control (`src/omniforge/prompts/security.py`)

**LAYER_ACCESS mapping**:
```python
LAYER_ACCESS = {
    Role.VIEWER: set(),
    Role.OPERATOR: set(),
    Role.DEVELOPER: {PromptLayer.FEATURE, PromptLayer.AGENT},
    Role.ADMIN: {PromptLayer.SYSTEM, PromptLayer.TENANT, PromptLayer.FEATURE, PromptLayer.AGENT},
}
```

`can_modify_layer(role: Role, layer: PromptLayer) -> bool`:
- Check if role can modify prompts at the specified layer

`check_prompt_access(user_role: Role, prompt: Prompt, operation: str) -> bool`:
- Verify user has permission for operation on this prompt
- Consider both RBAC permission and layer access

### Agent Integration (`src/omniforge/agents/base.py` modification)

Add to BaseAgent (or AgentConfig):
- `prompt_config: Optional[PromptConfig] = None` attribute
- Method to get composed prompt: `get_composed_prompt(variables: dict) -> str`

### Tenant Isolation
- All prompt repository operations include tenant_id filtering
- System prompts visible to all tenants
- Tenant/Feature/Agent prompts isolated to owning tenant

## Acceptance Criteria
- [ ] New permissions added to RBAC system
- [ ] Role permissions correctly mapped
- [ ] Layer-based access control works
- [ ] Only ADMIN can modify SYSTEM/TENANT prompts
- [ ] Developers can modify FEATURE/AGENT prompts
- [ ] Agent base class supports prompt_config
- [ ] Tenant isolation enforced on all queries
- [ ] Unit tests for permission checks
- [ ] Integration test for cross-tenant isolation

## Dependencies
- TASK-001 (enums)
- TASK-010 (SDK for PromptConfig)

## Estimated Complexity
Medium
