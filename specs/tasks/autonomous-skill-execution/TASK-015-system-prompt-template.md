# TASK-015: Build system prompt template and ReAct format

**Priority:** P1 (Should Have)
**Estimated Effort:** Small (<1 day)
**Dependencies:** TASK-003, TASK-005

---

## Description

Create the system prompt template for autonomous skill execution. The prompt instructs the LLM to follow the ReAct (Reason-Act-Observe) pattern with a specific JSON response format. Includes skill instructions, available tools, supporting files list, and execution rules.

## Files to Create/Modify

- `src/omniforge/skills/prompts.py` - System prompt template and builder

## Implementation Requirements

### System Prompt Template

```python
AUTONOMOUS_SKILL_SYSTEM_PROMPT = """
You are executing the '{skill_name}' skill autonomously.

SKILL INSTRUCTIONS:
{skill_content}

{available_files_section}

AVAILABLE TOOLS:
{tool_descriptions}

EXECUTION FORMAT:
You must respond in JSON format with one of these structures:

1. When you need to call a tool:
{{
    "thought": "Your reasoning about what to do next",
    "action": "tool_name",
    "action_input": {{"arg1": "value1", "arg2": "value2"}},
    "is_final": false
}}

2. When you have completed the task:
{{
    "thought": "Your final reasoning",
    "final_answer": "Your complete response to the user",
    "is_final": true
}}

RULES:
- Think step by step about how to accomplish the task
- Use tools to gather information and perform actions
- If a tool fails, try an alternative approach
- Continue until the task is complete or you cannot make progress
- Provide clear, actionable final answers
- Always respond with valid JSON in the format above

Current iteration: {iteration}/{max_iterations}
"""
```

### PromptBuilder Class

```python
class PromptBuilder:
    """Builds system prompts for autonomous skill execution."""

    def build_system_prompt(
        self,
        skill: Skill,
        tool_descriptions: str,
        available_files_section: str,
        iteration: int,
        max_iterations: int,
    ) -> str:
        """Build complete system prompt."""
        return AUTONOMOUS_SKILL_SYSTEM_PROMPT.format(
            skill_name=skill.metadata.name,
            skill_content=skill.content,
            available_files_section=available_files_section,
            tool_descriptions=tool_descriptions,
            iteration=iteration,
            max_iterations=max_iterations,
        )

    def format_tool_descriptions(
        self,
        tools: list[BaseTool],
        allowed_tools: Optional[list[str]] = None,
    ) -> str:
        """Format tool descriptions for prompt."""
        lines = []
        for tool in tools:
            if allowed_tools and tool.name not in allowed_tools:
                continue
            lines.append(f"- {tool.name}: {tool.description}")
            if tool.parameters:
                lines.append(f"  Parameters: {tool.parameters}")
        return "\n".join(lines)
```

### Available Files Section Format

```python
def build_available_files_section(self, context: LoadedContext) -> str:
    """Build the available files section."""
    if not context.available_files:
        return ""

    lines = [
        "AVAILABLE SUPPORTING FILES (load on-demand with 'read' tool):",
    ]
    for filename, ref in sorted(context.available_files.items()):
        line = f"- {filename}"
        if ref.description:
            line += f": {ref.description}"
        if ref.estimated_lines:
            line += f" ({ref.estimated_lines:,} lines)"
        lines.append(line)

    lines.append("")
    lines.append(f"Skill directory: {context.skill_dir}")
    lines.append("Use the 'read' tool to load these files when you need their content.")

    return "\n".join(lines)
```

### Response Format Documentation

The LLM response format:

**Action Response:**
```json
{
    "thought": "I need to read the file to understand its contents",
    "action": "read",
    "action_input": {"file_path": "/path/to/file.txt"},
    "is_final": false
}
```

**Final Answer Response:**
```json
{
    "thought": "I have completed the analysis and found 5 issues",
    "final_answer": "Analysis complete. Found 5 issues:\n1. ...\n2. ...",
    "is_final": true
}
```

### Error Recovery Prompt Addition

When tool fails, append to conversation:
```python
def build_error_observation(self, tool_name: str, error: str, retry_count: int) -> str:
    """Build observation message for failed tool call."""
    return (
        f"Tool '{tool_name}' failed: {error}\n"
        f"Attempt {retry_count}. Please try again with different parameters "
        f"or use an alternative approach."
    )
```

## Acceptance Criteria

- [ ] System prompt template follows ReAct pattern
- [ ] JSON response format clearly documented
- [ ] Skill instructions included
- [ ] Available tools listed with descriptions
- [ ] Available files section included when applicable
- [ ] Current iteration number shown
- [ ] Response format enforced (JSON with required fields)
- [ ] Error recovery prompt guides alternative approaches
- [ ] Unit tests for prompt building

## Testing

```python
def test_build_system_prompt():
    """System prompt should include all required sections."""
    builder = PromptBuilder()
    prompt = builder.build_system_prompt(
        skill=mock_skill,
        tool_descriptions="- read: Read a file",
        available_files_section="- reference.md: API docs",
        iteration=1,
        max_iterations=15,
    )

    assert mock_skill.metadata.name in prompt
    assert mock_skill.content in prompt
    assert "- read: Read a file" in prompt
    assert "reference.md" in prompt
    assert "1/15" in prompt
    assert "JSON format" in prompt

def test_format_tool_descriptions():
    """Tool descriptions should be properly formatted."""
    builder = PromptBuilder()
    tools = [MockTool(name="read", description="Read a file")]
    result = builder.format_tool_descriptions(tools)
    assert "- read: Read a file" in result

def test_available_files_section_empty():
    """Empty available files should return empty string."""
    context = LoadedContext(available_files={}, ...)
    section = builder.build_available_files_section(context)
    assert section == ""
```

## Technical Notes

- Use f-strings with double braces `{{` `}}` for literal braces in JSON example
- Iteration number helps LLM understand progress/urgency
- Consider adding token limit guidance in prompt
- Available files section is optional (empty if no supporting files)
- Tool descriptions from existing ToolRegistry format
