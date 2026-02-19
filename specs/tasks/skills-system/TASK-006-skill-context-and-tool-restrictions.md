# TASK-006: Skill Context and Tool Restrictions

**Phase**: 3 - Tool Integration
**Complexity**: Medium
**Dependencies**: TASK-001
**Estimated Time**: 30-45 minutes

## Objective

Implement SkillContext for managing tool restrictions during skill execution.

## What to Build

### Create `src/omniforge/skills/context.py`

Implement `SkillContext` class:

1. **__init__(skill: Skill, executor: ToolExecutor)**
   - Store skill reference and executor
   - Initialize internal state (_allowed_tools)

2. **__enter__() / __exit__()**
   - Context manager for backward compatibility
   - Sets up allowed_tools set on enter
   - Clears on exit

3. **check_tool_allowed(tool_name: str)**
   - Validate tool is in allowed-tools list
   - Case-insensitive comparison
   - Raise SkillToolNotAllowedError if blocked
   - No-op if allowed_tools is None (all tools allowed)

4. **check_tool_arguments(tool_name: str, arguments: dict)**
   - Validate tool arguments against skill rules
   - Block Read tool on script files:
     - Check if file_path argument matches any script_path in skill
     - Raise SkillScriptReadError with helpful message

5. **is_restricted property**
   - Return True if tool restrictions are active

6. **allowed_tool_names property**
   - Return set of allowed tools or None if unrestricted

## Key Requirements

- Case-insensitive tool name matching
- Script read blocking is critical for context efficiency
- Error messages must guide agent to correct behavior
- Works standalone or integrated with ToolExecutor

## Acceptance Criteria

- [ ] Tool restrictions enforce correctly (block disallowed tools)
- [ ] Script file read attempts blocked with helpful error
- [ ] Case-insensitive matching works ("Bash" == "bash")
- [ ] No restrictions when allowed_tools is None
- [ ] Unit tests in `tests/skills/test_context.py` with >80% coverage
- [ ] Tests cover script read blocking scenarios
