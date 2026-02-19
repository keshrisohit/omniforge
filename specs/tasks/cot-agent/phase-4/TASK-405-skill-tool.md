# TASK-405: Implement Internal Skill Invocation Tool

## Description

Create the skill tool that enables agents to invoke registered internal skills (Python functions) through the unified tool interface. Skills are internal capabilities like document processing, data transformation, or custom business logic.

## Requirements

- Create `SkillRegistry` class:
  - `register(name, func, description, parameters)` method
  - `get(name)` method returning skill function
  - `list_skills()` method returning skill definitions
  - Support both sync and async skill functions
- Create `SkillTool` class extending BaseTool:
  - Constructor accepting SkillRegistry
  - Implement `definition` property:
    - name: "skill"
    - type: ToolType.SKILL
    - Parameters: skill_name, arguments (dict)
  - Implement `execute()` method:
    - Look up skill by name
    - Validate arguments against skill parameters
    - Execute skill function (handle sync/async)
    - Return skill result
- Create decorator for easy skill registration:
  - `@skill(name, description)` decorator
  - Auto-extracts parameters from function signature

## Acceptance Criteria

- [ ] Skills can be registered and invoked
- [ ] Both sync and async skills supported
- [ ] Skill arguments validated before execution
- [ ] Skill errors returned as ToolResult errors
- [ ] Decorator simplifies skill registration
- [ ] list_skills() returns all registered skills
- [ ] Unit tests cover registration and execution

## Dependencies

- TASK-102 (for BaseTool, ToolDefinition)

## Files to Create/Modify

- `src/omniforge/tools/builtin/skill.py` (new)
- `tests/tools/builtin/test_skill.py` (new)

## Estimated Complexity

Medium (4-5 hours)

## Key Considerations

- Use inspect module for signature extraction
- Handle both sync and async functions (asyncio.iscoroutinefunction)
- Consider execution timeout for long-running skills
