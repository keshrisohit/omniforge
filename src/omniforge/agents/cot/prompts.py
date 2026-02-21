"""System prompt templates and tool description formatters for ReAct pattern.

This module provides utilities for building LLM system prompts that teach
the ReAct (Reasoning + Acting) pattern and format tool descriptions.
"""

from omniforge.prompts import get_default_registry
from omniforge.tools.base import ToolDefinition


def format_single_tool(tool: ToolDefinition) -> str:
    """Format a single tool's definition for LLM consumption.

    Args:
        tool: Tool definition to format

    Returns:
        Formatted tool description with parameters and return information
    """
    # Tool name and description
    lines = [f"**{tool.name}**: {tool.description}"]

    # Parameters section
    if tool.parameters:
        lines.append("  Parameters:")
        for param in tool.parameters:
            # Build parameter line: name (type, required/optional, default=value): description
            parts = [f"    - {param.name} ({param.type.value}"]

            # Add required/optional status
            if param.required:
                parts.append(", required")
            else:
                parts.append(", optional")

            # Add default value if present
            if not param.required and param.default is not None:
                parts.append(f", default={param.default}")

            parts.append(f"): {param.description}")
            lines.append("".join(parts))

    # Returns section (if available)
    # Note: ToolDefinition doesn't have a returns field in the current schema,
    # so we'll handle this gracefully by checking for it
    if hasattr(tool, "returns") and tool.returns:
        lines.append(f"  Returns: {tool.returns}")

    return "\n".join(lines)


def format_tool_descriptions(tools: list[ToolDefinition]) -> str:
    """Format all tool descriptions for LLM consumption.

    Args:
        tools: List of tool definitions to format

    Returns:
        Formatted tool descriptions separated by blank lines
    """
    if not tools:
        return "No tools available."

    return "\n\n".join(format_single_tool(tool) for tool in tools)


def build_react_system_prompt(tools: list[ToolDefinition]) -> str:
    """Build complete ReAct system prompt with tool descriptions.

    This function composes a comprehensive ReAct prompt from templates
    stored in the prompt registry. It includes:
    - Core ReAct instructions with JSON format
    - Tool descriptions
    - Skill navigation guidance
    - Script execution instructions
    - Multi-LLM path resolution examples
    - Tool calling format examples

    Args:
        tools: List of available tools to include in the prompt

    Returns:
        Complete system prompt teaching ReAct pattern with formatted tools
    """
    # Get default registry with all templates
    registry = get_default_registry()

    # Format tool descriptions
    tool_descriptions = format_tool_descriptions(tools)

    # Get base ReAct prompt with tool descriptions
    react_base = registry.render("react_base", tool_descriptions=tool_descriptions)

    # Get additional guidance sections
    skill_navigation = registry.get("skill_navigation")
    script_execution = registry.get("script_execution")
    multi_llm_paths = registry.get("multi_llm_paths")
    tool_calling_examples = registry.get("tool_calling_examples")

    # Compose full prompt
    prompt = f"""{react_base}

{skill_navigation}

{script_execution}

{multi_llm_paths}

{tool_calling_examples}

##IMPORTANT REMINDER
Your response MUST be EXACTLY in one of these two formats - NO other formats are allowed:

**Tool Call Format:**
{{{{
  "thought": "your reasoning here",
  "action": "tool_name_from_above_list",
  "action_input": {{{{"param": "value"}}}},
  "is_final": false
}}}}

For the bash tool specifically, always use: `"action_input": {{{{"command": "your command here"}}}}`

**Final Answer Format:**
{{{{
  "thought": "your reasoning here",
  "final_answer": "your answer here",
  "is_final": true
}}}}

Now solve the user's task by responding with valid JSON only in the exact format above.
Remember: ALWAYS use tools first."""

    return prompt
