# TASK-010: System Prompt Integration for Multi-LLM Support

**Phase**: 4 - Rename & Integration
**Complexity**: Medium
**Dependencies**: TASK-007, TASK-008
**Estimated Time**: 30-45 minutes

## Objective

Add skill navigation instructions to the agent system prompt for multi-LLM compatibility.

## What to Build

### 1. Update `src/omniforge/agents/cot/prompts.py`

Add new constants for skill navigation:

1. **SKILL_NAVIGATION_INSTRUCTIONS**
   - Path resolution rules with examples
   - base_path usage for relative paths
   - Absolute vs relative path handling

2. **SCRIPT_EXECUTION_INSTRUCTIONS**
   - Execute scripts via Bash, never Read
   - Context efficiency explanation
   - cd {base_path} && command pattern

3. **MULTI_LLM_PATH_RESOLUTION**
   - Concrete examples for all LLMs
   - Example 1: Loading reference documents
   - Example 2: Executing scripts
   - Example 3: Nested paths

4. **TOOL_CALLING_EXAMPLES**
   - JSON format examples for Read, Bash, Skill tools
   - Shows exact argument structure

### 2. Modify `build_react_system_prompt()` function

Add skill navigation section:
```python
def build_react_system_prompt(tools: list[ToolDefinition]) -> str:
    # ... existing code ...

    # Add skill navigation section
    prompt += "\n\n" + SKILL_NAVIGATION_INSTRUCTIONS
    prompt += "\n\n" + SCRIPT_EXECUTION_INSTRUCTIONS

    return prompt
```

### 3. Update tests

Add tests verifying:
- System prompt contains skill navigation
- Path resolution examples are present
- Script execution guidance included

## Key Requirements

- Instructions must work for Claude, GPT-4, and Gemini
- Explicit examples (not implicit understanding)
- Concrete path construction patterns
- Clear "execute, don't read" guidance for scripts

## Acceptance Criteria

- [ ] System prompt includes skill navigation section
- [ ] Path resolution examples cover all cases
- [ ] Script execution guidance is explicit
- [ ] Tests verify prompt content in `tests/agents/cot/test_prompts.py`
- [ ] Documentation updated with multi-LLM notes
