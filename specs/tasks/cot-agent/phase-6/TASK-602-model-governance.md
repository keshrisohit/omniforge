# TASK-602: Implement Model Governance for Enterprise Compliance

## Description

Create the model governance system that enforces which LLM models can be used in production environments. This supports enterprise compliance requirements and cost control.

## Requirements

- Create `ModelPolicy` model:
  - approved_models: list[str]
  - blocked_models: list[str]
  - require_approval: bool
  - max_cost_per_call_usd: Optional[float]
- Create `ModelGovernance` class:
  - Constructor accepting default_policy
  - `configure_tenant(tenant_id, policy)` method
  - `is_model_allowed(tenant_id, model)` method
  - `get_approved_models(tenant_id)` method
  - `validate_model_call(tenant_id, model, estimated_cost)` method
- Create `ModelNotApprovedError` exception (if not already in TASK-104)
- Integrate with LLM tool to check before execution

## Acceptance Criteria

- [ ] Approved models list enforced
- [ ] Blocked models rejected even if in approved list
- [ ] Per-tenant policies supported
- [ ] Default policy used for unconfigured tenants
- [ ] Cost limits per call enforced
- [ ] ModelNotApprovedError raised for violations
- [ ] Unit tests cover all governance scenarios

## Dependencies

- TASK-104 (for error types)
- TASK-303 (for LLM tool integration)

## Files to Create/Modify

- `src/omniforge/enterprise/model_governance.py` (new)
- `tests/enterprise/test_model_governance.py` (new)

## Estimated Complexity

Simple (2-3 hours)

## Key Considerations

- Allow wildcard patterns (e.g., "claude-*")
- Consider model aliases (gpt-4 -> gpt-4-turbo-preview)
- Log all model policy violations
