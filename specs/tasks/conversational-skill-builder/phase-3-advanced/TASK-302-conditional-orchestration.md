# TASK-302: Conditional Skill Orchestration

**Phase**: 3A (Advanced Orchestration)
**Estimated Effort**: 14 hours
**Dependencies**: TASK-301 (Parallel Orchestration)
**Priority**: P1

## Objective

Add conditional skill execution based on runtime conditions. Skills can be skipped or executed based on previous skill outputs or predefined conditions.

## Requirements

- Create `SkillCondition` model with condition expression and evaluation
- Extend SkillReference with optional `condition` field
- Implement condition evaluator for simple expressions
- Support conditions based on previous skill outputs
- Create conversation flow for condition definition
- Add condition validation before agent activation

## Implementation Notes

- Reference product spec "Conditional Orchestration" example
- Simple expression language: field comparisons, boolean logic
- Example: `insurance_provider == 'UnitedHealthcare'`
- Conditions evaluated at runtime against execution context
- Invalid conditions caught during agent creation, not execution

## Acceptance Criteria

- [ ] SkillCondition model supports simple comparison expressions
- [ ] Condition evaluator handles ==, !=, <, >, in operators
- [ ] Skills with false conditions are skipped in execution
- [ ] Conditions can reference previous skill output fields
- [ ] Execution events include condition evaluation results
- [ ] Invalid conditions rejected during agent creation
- [ ] Conversation guides users through condition definition
- [ ] 85%+ test coverage for condition evaluation

## Files to Create/Modify

- `src/omniforge/execution/orchestration/conditions.py` - SkillCondition, evaluator
- `src/omniforge/execution/orchestration/engine.py` - Add condition evaluation
- `src/omniforge/builder/models/agent_config.py` - Add condition to SkillReference
- `src/omniforge/builder/conversation/conditions.py` - Condition definition flow
- `tests/execution/orchestration/test_conditions.py` - Condition evaluation tests
- `tests/builder/conversation/test_condition_flow.py` - Conversation tests
