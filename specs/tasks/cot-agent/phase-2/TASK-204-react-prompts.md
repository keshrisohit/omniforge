# TASK-204: Implement ReAct System Prompt Templates

## Description

Create the system prompt templates and tool description formatters for the ReAct pattern. These prompts teach the LLM how to use the ReAct format and provide tool information.

## Requirements

- Create prompt building utilities:
  - `build_react_system_prompt(tools: list[ToolDefinition])` function
  - `format_tool_descriptions(tools: list[ToolDefinition])` function
  - `format_single_tool(tool: ToolDefinition)` function
- System prompt template should include:
  - Agent role description
  - Available tools section (dynamically generated)
  - ReAct format specification with examples
  - Important rules (10 rules from spec)
  - "Begin!" instruction
- Tool description format:
  - Tool name in bold: **tool_name**: description
  - Parameters section with name, type, required/optional, default, description
  - Returns section with description
- Consider prompt variants:
  - Default ReAct prompt
  - Prompt with few-shot examples (optional)

## Acceptance Criteria

- [ ] build_react_system_prompt() generates complete ReAct prompt
- [ ] Tools are correctly formatted with parameters
- [ ] Required/optional distinction is clear
- [ ] Default values shown for optional parameters
- [ ] Prompt includes all 10 important rules
- [ ] Output is markdown-formatted for LLM consumption
- [ ] Unit tests verify prompt structure and content

## Dependencies

- TASK-102 (for ToolDefinition, ToolParameter)

## Files to Create/Modify

- `src/omniforge/agents/cot/prompts.py` (new)
- `tests/agents/cot/test_prompts.py` (new)

## Estimated Complexity

Simple (2-3 hours)

## Key Considerations

- Prompts should be readable and well-formatted
- Consider token efficiency in prompt design
- Tool descriptions should be clear for LLM understanding
