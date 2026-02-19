# TASK-008: ToolExecutor Skill Stack Integration

**Phase**: 3 - Tool Integration
**Complexity**: Complex
**Dependencies**: TASK-006, TASK-007
**Estimated Time**: 45-60 minutes

## Objective

Integrate skill context with ToolExecutor using stack-based tracking for security.

## What to Build

### Modify `src/omniforge/tools/executor.py`

Add skill-aware execution to ToolExecutor:

1. **New instance variables in __init__**:
   - `_skill_stack: list[Skill]` - Stack of active skills
   - `_skill_contexts: dict[str, SkillContext]` - name -> context mapping

2. **active_skill property -> Optional[Skill]**
   - Return top of skill stack or None

3. **activate_skill(skill: Skill)**
   - Create SkillContext for skill
   - Push to stack and register in contexts dict
   - Raise SkillError if skill already active
   - Log activation for audit

4. **deactivate_skill(skill_name: str)**
   - Enforce stack discipline (can only deactivate top)
   - Pop from stack, remove from contexts
   - Raise SkillError if not at top or not active
   - Log deactivation for audit

5. **Modify execute() method**:
   - Before execution, check if active_skill exists
   - Call context.check_tool_allowed(tool_name)
   - Call context.check_tool_arguments(tool_name, arguments)
   - Return error ToolResult if blocked (don't execute)
   - Log tool execution in skill context for audit

## Key Requirements

- Stack-based tracking survives exceptions (addresses CRITICAL-3)
- Enforce LIFO deactivation order
- Audit logging for all skill activations/deactivations
- Exception-safe: restrictions persist even on errors

## Acceptance Criteria

- [ ] Skill activation adds to stack correctly
- [ ] Tool restrictions enforced during skill context
- [ ] Script read attempts blocked with helpful error
- [ ] Cannot deactivate out of order (stack discipline)
- [ ] Restrictions survive exceptions
- [ ] Unit tests in `tests/tools/test_executor_skills.py`
- [ ] Integration tests verify security model
