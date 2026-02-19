# TASK-007: SkillTool Implementation for SKILL.md Loading

**Phase**: 3 - Tool Integration
**Complexity**: Medium
**Dependencies**: TASK-004, TASK-006
**Estimated Time**: 45-60 minutes

## Objective

Implement the new SkillTool for loading agent skills from SKILL.md files.

## What to Build

### Create `src/omniforge/skills/tool.py`

Implement `SkillTool(BaseTool)` class:

1. **__init__(skill_loader, timeout_ms=30000)**
   - Store SkillLoader reference
   - Configure timeout

2. **definition property -> ToolDefinition**
   - Return dynamically generated definition
   - Name: "skill" (will conflict with existing - addressed in Phase 4)
   - Type: ToolType.SKILL
   - Parameters: skill_name (required), args (optional)
   - Description built dynamically with available_skills

3. **_build_description() -> str**
   - Generate tool description with:
     - Usage instructions
     - `<available_skills>` section from loader.list_skills()
     - Progressive disclosure explanation
     - Path resolution guidance for multi-LLM support

4. **execute(arguments, context) -> ToolResult**
   - Extract skill_name and args from arguments
   - Validate skill_name is provided
   - Load full skill via loader.load_skill()
   - Return ToolResult with:
     - skill_name
     - base_path (absolute path to skill directory)
     - content (full SKILL.md body)
     - allowed_tools (if any)
     - args (passed through)

5. **_find_similar(name, available, threshold=0.6) -> Optional[str]**
   - Simple string matching for suggestions
   - Help with typos in skill names

## Key Requirements

- Dynamic description regenerated on each access (supports hot reload)
- Performance target: < 50ms activation latency
- Return absolute base_path for path resolution
- Include multi-LLM compatible instructions in description

## Acceptance Criteria

- [ ] Tool definition generated with available skills list
- [ ] Skill loading returns complete content with base_path
- [ ] SkillNotFoundError includes similar skill suggestions
- [ ] Description contains multi-LLM path resolution guidance
- [ ] Unit tests in `tests/skills/test_tool.py` with >80% coverage
- [ ] Activation completes in < 50ms
