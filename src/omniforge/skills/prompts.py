"""System prompt templates and builders for autonomous skill execution.

This module provides utilities for building system prompts specifically for
autonomous skill execution with the ReAct (Reason-Act-Observe) pattern.
"""

from typing import Optional

from omniforge.prompts import get_default_registry
from omniforge.skills.context_loader import LoadedContext
from omniforge.skills.models import Skill
from omniforge.tools.base import ToolDefinition


class PromptBuilder:
    """Builds system prompts for autonomous skill execution.

    This class provides utilities for constructing comprehensive system prompts
    that include skill instructions, tool descriptions, available files, and
    ReAct format guidance.

    Example:
        >>> from omniforge.skills.models import Skill
        >>> from omniforge.tools.base import ToolDefinition
        >>> builder = PromptBuilder()
        >>> tools = [ToolDefinition(name="read", description="Read a file")]
        >>> tool_descriptions = builder.format_tool_descriptions(tools)
        >>> prompt = builder.build_system_prompt(
        ...     skill=skill,
        ...     tool_descriptions=tool_descriptions,
        ...     available_files_section="",
        ...     iteration=1,
        ...     max_iterations=15
        ... )
    """

    def __init__(self) -> None:
        """Initialize prompt builder with default registry."""
        self._registry = get_default_registry()

    def build_system_prompt(
        self,
        skill: Skill,
        tool_descriptions: str,
        available_files_section: str,
        iteration: int,
        max_iterations: int,
    ) -> str:
        """Build complete system prompt for autonomous skill execution.

        Creates a comprehensive prompt that includes the skill's instructions,
        available tools, supporting files, and execution format guidance.

        Args:
            skill: Skill instance with metadata and content
            tool_descriptions: Formatted string of available tool descriptions
            available_files_section: Formatted string listing available supporting files
            iteration: Current iteration number (1-indexed)
            max_iterations: Maximum number of iterations allowed

        Returns:
            Complete system prompt string ready for LLM consumption

        Example:
            >>> prompt = builder.build_system_prompt(
            ...     skill=my_skill,
            ...     tool_descriptions="- read: Read a file\\n- bash: Execute commands",
            ...     available_files_section="- reference.md: API documentation",
            ...     iteration=1,
            ...     max_iterations=15
            ... )
        """
        return self._registry.render(
            "skill_prompt_simple",
            skill_name=skill.metadata.name,
            skill_description=skill.metadata.description,
            skill_content=skill.content,
            available_files_section=available_files_section,
            tool_descriptions=tool_descriptions,
            iteration=iteration,
            max_iterations=max_iterations,
        )

    def format_tool_descriptions(
        self,
        tools: list[ToolDefinition],
        allowed_tools: Optional[list[str]] = None,
    ) -> str:
        """Format tool descriptions for inclusion in system prompt.

        Creates a formatted list of available tools with their descriptions
        and parameters. Optionally filters to only allowed tools.

        Args:
            tools: List of tool definitions to format
            allowed_tools: Optional list of allowed tool names (filters if provided)

        Returns:
            Formatted string with tool descriptions, one per line

        Example:
            >>> tools = [
            ...     ToolDefinition(name="read", description="Read a file"),
            ...     ToolDefinition(name="bash", description="Execute commands")
            ... ]
            >>> descriptions = builder.format_tool_descriptions(tools)
            >>> print(descriptions)
            - read: Read a file
              Parameters: {"file_path": "string (required)"}
            - bash: Execute commands
              Parameters: {"command": "string (required)"}
        """
        if not tools:
            return "No tools available."

        lines = []
        for tool in tools:
            # Skip if not in allowed list
            if allowed_tools and tool.name not in allowed_tools:
                continue

            # Add tool name and description
            lines.append(f"- {tool.name}: {tool.description}")

            # Add parameters if available
            if tool.parameters:
                param_parts = []
                for param in tool.parameters:
                    req_text = "required" if param.required else "optional"
                    param_str = f"{param.name} ({param.type.value}, {req_text})"
                    if param.description:
                        param_str += f": {param.description}"
                    param_parts.append(param_str)

                lines.append(f"  Parameters: {', '.join(param_parts)}")

        return "\n".join(lines)

    def build_available_files_section(self, context: LoadedContext) -> str:
        """Build the available files section for the system prompt.

        Creates a formatted section listing all supporting files that can be
        loaded on-demand during execution. Includes file descriptions and
        estimated line counts when available.

        Args:
            context: Loaded context containing available file references

        Returns:
            Formatted string with available files section, or empty string
            if no files are available

        Example:
            >>> context = LoadedContext(
            ...     skill_content="...",
            ...     available_files={
            ...         "reference.md": FileReference(
            ...             filename="reference.md",
            ...             path=Path("/skills/my-skill/reference.md"),
            ...             description="API documentation",
            ...             estimated_lines=1200
            ...         )
            ...     },
            ...     skill_dir=Path("/skills/my-skill")
            ... )
            >>> section = builder.build_available_files_section(context)
            >>> print(section)
            AVAILABLE SUPPORTING FILES (load on-demand with 'read' tool):
            - reference.md: API documentation (1,200 lines)

            Skill directory: /skills/my-skill
            Use the 'read' tool to load these files when you need their content.
        """
        if not context.available_files:
            return ""

        lines = [
            "AVAILABLE SUPPORTING FILES (load on-demand with 'read' tool):",
        ]

        # Add each file with description and line count
        for filename, ref in sorted(context.available_files.items()):
            line = f"- {filename}"
            if ref.description:
                line += f": {ref.description}"
            if ref.estimated_lines:
                line += f" ({ref.estimated_lines:,} lines)"
            lines.append(line)

        # Add skill directory and usage instruction
        lines.append("")
        lines.append(f"Skill directory: {context.skill_dir}")
        lines.append("Use the 'read' tool to load these files when you need their content.")

        return "\n".join(lines)

    def build_error_observation(self, tool_name: str, error: str, retry_count: int) -> str:
        """Build observation message for failed tool call.

        Creates a helpful error message that guides the LLM to try alternative
        approaches after a tool failure.

        Args:
            tool_name: Name of the tool that failed
            error: Error message from the tool
            retry_count: Number of times this has been retried (1-indexed)

        Returns:
            Formatted error observation message

        Example:
            >>> message = builder.build_error_observation(
            ...     tool_name="read",
            ...     error="File not found: /path/to/missing.txt",
            ...     retry_count=1
            ... )
            >>> print(message)
            Tool 'read' failed: File not found: /path/to/missing.txt
            Attempt 1. Please try again with different parameters or use an alternative approach.
        """
        return (
            f"Tool '{tool_name}' failed: {error}\n"
            f"Attempt {retry_count}. Please try again with different parameters "
            f"or use an alternative approach."
        )
