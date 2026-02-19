# TASK-011: Skills System Integration Tests

**Phase**: 4 - Rename & Integration
**Complexity**: Medium
**Dependencies**: TASK-008, TASK-009, TASK-010
**Estimated Time**: 45-60 minutes

## Objective

Create comprehensive integration tests for the complete Skills System.

## What to Build

### Create `tests/skills/test_integration.py`

1. **test_skill_discovery_flow()**
   - Create temp skill directory structure
   - Build index
   - Verify skills appear in SkillTool description
   - Verify priority resolution works

2. **test_skill_activation_flow()**
   - Load skill via SkillTool.execute()
   - Verify base_path and content returned
   - Verify allowed_tools extracted

3. **test_tool_restriction_enforcement()**
   - Activate skill with allowed-tools
   - Attempt disallowed tool - verify blocked
   - Attempt allowed tool - verify works

4. **test_script_read_blocking()**
   - Create skill with scripts/ directory
   - Activate skill
   - Attempt Read on script file - verify SkillScriptReadError
   - Attempt Bash execution - verify works

5. **test_skill_stack_security()**
   - Activate skill
   - Trigger exception
   - Verify restrictions still active after exception
   - Verify cannot deactivate out of order

6. **test_auto_deactivation_on_task_complete()**
   - Activate skill during task
   - Complete task
   - Verify skill auto-deactivated

7. **test_storage_priority_resolution()**
   - Create same skill at enterprise and project levels
   - Verify enterprise version wins

### Create `tests/skills/conftest.py`

Shared fixtures:
- `skill_directory(tmp_path)` - temp skill structure
- `storage_config(skill_directory)` - configured StorageConfig
- `skill_loader(storage_config)` - initialized SkillLoader
- `skill_tool(skill_loader)` - configured SkillTool
- `executor_with_skills()` - ToolExecutor with skill support

## Key Requirements

- Use pytest fixtures for isolation
- Test realistic scenarios
- Cover security-critical paths
- Verify all CRITICAL issues from review are addressed

## Acceptance Criteria

- [ ] All integration tests pass
- [ ] Tool restriction enforcement verified
- [ ] Script read blocking verified
- [ ] Stack security verified
- [ ] Priority resolution verified
- [ ] Coverage report shows >80% for skills module
