"""Demo script showcasing the PromptBuilder utility for autonomous skill execution.

This script demonstrates how to use the PromptBuilder to generate complete
system prompts for autonomous skill execution with the ReAct pattern.
"""

from pathlib import Path

from omniforge.skills.context_loader import FileReference, LoadedContext
from omniforge.skills.models import Skill, SkillMetadata
from omniforge.skills.prompts import PromptBuilder
from omniforge.tools.base import ParameterType, ToolDefinition, ToolParameter
from omniforge.tools.types import ToolType


def main() -> None:
    """Demonstrate prompt building for autonomous skill execution."""
    print("=" * 80)
    print("System Prompt Template Builder Demo")
    print("=" * 80)
    print()

    # Create a sample skill
    skill_metadata = SkillMetadata(
        name="data-analyzer",
        description="Analyze data files and generate insights",
    )
    skill = Skill(
        metadata=skill_metadata,
        content="""# Data Analyzer Skill

This skill helps you analyze CSV and JSON data files.

## Instructions

1. Read the data file using the read tool
2. Analyze the structure and content
3. Generate summary statistics
4. Identify any patterns or anomalies
5. Provide actionable insights

## Output Format

Provide a clear summary with:
- Data overview (rows, columns, types)
- Key statistics
- Notable patterns
- Recommended actions
""",
        path=Path("/skills/data-analyzer/SKILL.md"),
        base_path=Path("/skills/data-analyzer"),
        storage_layer="global",
    )

    # Define available tools
    tools = [
        ToolDefinition(
            name="read",
            type=ToolType.FILE_READ,
            description="Read content from a file",
            parameters=[
                ToolParameter(
                    name="file_path",
                    type=ParameterType.STRING,
                    description="Absolute path to the file",
                    required=True,
                )
            ],
        ),
        ToolDefinition(
            name="bash",
            type=ToolType.BASH,
            description="Execute bash commands",
            parameters=[
                ToolParameter(
                    name="command",
                    type=ParameterType.STRING,
                    description="Command to execute",
                    required=True,
                )
            ],
        ),
    ]

    # Create context with available supporting files
    context = LoadedContext(
        skill_content=skill.content,
        available_files={
            "examples.csv": FileReference(
                filename="examples.csv",
                path=Path("/skills/data-analyzer/examples.csv"),
                description="Sample data for reference",
                estimated_lines=500,
            ),
            "analysis_template.md": FileReference(
                filename="analysis_template.md",
                path=Path("/skills/data-analyzer/analysis_template.md"),
                description="Template for formatting analysis output",
                estimated_lines=100,
            ),
        },
        skill_dir=Path("/skills/data-analyzer"),
        line_count=25,
    )

    # Build the prompt
    print("Building system prompt...")
    print()
    builder = PromptBuilder()

    # Format tools
    tool_descriptions = builder.format_tool_descriptions(tools)
    print("1. Tool Descriptions:")
    print("-" * 40)
    print(tool_descriptions)
    print()

    # Format available files
    files_section = builder.build_available_files_section(context)
    print("2. Available Files Section:")
    print("-" * 40)
    print(files_section)
    print()

    # Build complete prompt
    prompt = builder.build_system_prompt(
        skill=skill,
        tool_descriptions=tool_descriptions,
        available_files_section=files_section,
        iteration=3,
        max_iterations=15,
    )

    print("3. Complete System Prompt:")
    print("=" * 80)
    print(prompt)
    print("=" * 80)
    print()

    # Demonstrate error observation builder
    print("4. Error Recovery Message:")
    print("-" * 40)
    error_msg = builder.build_error_observation(
        tool_name="read",
        error="File not found: /data/missing.csv",
        retry_count=2,
    )
    print(error_msg)
    print()

    print("Demo completed successfully!")


if __name__ == "__main__":
    main()
