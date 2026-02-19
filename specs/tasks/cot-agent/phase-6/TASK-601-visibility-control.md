# TASK-601: Implement Visibility Control System

## Description

Create the visibility control system that manages what reasoning chain information is visible to different users based on roles, tool types, and configuration. This enables simplified views for end-users while maintaining full detail for developers.

## Requirements

- Create `VisibilityRule` model:
  - role: Optional[str]
  - tool_type: Optional[ToolType]
  - level: VisibilityLevel
  - summary_template: Optional[str]
- Create `VisibilityConfig` (expanded):
  - default_level: VisibilityLevel
  - rules_by_tool_type: dict[ToolType, VisibilityLevel]
  - rules_by_role: dict[str, VisibilityLevel]
  - child_chain_visibility: VisibilityLevel
- Create `VisibilityController` class:
  - Constructor accepting VisibilityConfig
  - `apply_visibility(step, user_role, tool_type)` method
  - `filter_chain(chain, user_role)` method returning filtered chain
  - `get_effective_level(step, user_role)` method
  - Resolution order: security > role > tool > step > default
- Create visibility utilities:
  - `redact_sensitive_fields(step, sensitive_fields)` function
  - `generate_summary(step, template)` function

## Acceptance Criteria

- [ ] Visibility levels applied correctly per role
- [ ] Tool type visibility rules work
- [ ] Resolution order followed (most specific wins)
- [ ] Sensitive fields redacted in non-full views
- [ ] Summary templates generate readable summaries
- [ ] filter_chain returns only visible steps
- [ ] Unit tests cover all visibility scenarios

## Dependencies

- TASK-101 (for ReasoningStep, VisibilityLevel)

## Files to Create/Modify

- `src/omniforge/agents/cot/visibility.py` (new)
- `tests/agents/cot/test_visibility.py` (new)

## Estimated Complexity

Medium (4-5 hours)

## Key Considerations

- Security requirements always take precedence
- Hidden steps should still exist in chain (for audit)
- Summary generation should be fail-safe
