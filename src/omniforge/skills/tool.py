"""SkillTool for loading and activating agent skills from SKILL.md files.

This module provides the SkillTool class that implements progressive disclosure
for skills, exposing available skills in the tool description and loading full
skill content only when activated.
"""

import time
from difflib import SequenceMatcher
from typing import Any, Optional

from omniforge.skills.errors import SkillNotFoundError
from omniforge.skills.loader import SkillLoader
from omniforge.tools.base import (
    BaseTool,
    ParameterType,
    ToolCallContext,
    ToolDefinition,
    ToolParameter,
    ToolResult,
)
from omniforge.tools.types import ToolType


class SkillTool(BaseTool):
    """Tool for loading agent skills from SKILL.md files.

    Implements progressive disclosure pattern:
    - Stage 1: Tool description includes list of available skills (metadata only)
    - Stage 2: On activation, loads full skill content with base_path for resolution

    The tool description is dynamically generated to include current available
    skills, supporting hot reload without system prompt changes.

    Example:
        >>> from omniforge.skills.storage import StorageConfig
        >>> config = StorageConfig(global_path="/skills")
        >>> loader = SkillLoader(config)
        >>> loader.build_index()
        >>> tool = SkillTool(loader)
        >>> context = ToolCallContext(
        ...     correlation_id="corr-1",
        ...     task_id="task-1",
        ...     agent_id="agent-1"
        ... )
        >>> result = await tool.execute(
        ...     arguments={"skill_name": "debug-agent"},
        ...     context=context
        ... )
        >>> result.success
        True
        >>> result.result["skill_name"]
        'debug-agent'
    """

    def __init__(self, skill_loader: SkillLoader, timeout_ms: int = 30000) -> None:
        """Initialize SkillTool with skill loader.

        Args:
            skill_loader: SkillLoader instance for skill discovery and loading
            timeout_ms: Timeout for skill loading in milliseconds (default: 30000)
        """
        self._skill_loader = skill_loader
        self._timeout_ms = timeout_ms

    @property
    def definition(self) -> ToolDefinition:
        """Get dynamically generated tool definition with available skills.

        The definition is regenerated on each access to support hot reload
        of skill changes without requiring system prompt updates.

        Returns:
            ToolDefinition with current list of available skills in description
        """
        return ToolDefinition(
            name="skill",
            type=ToolType.SKILL,
            description=self._build_description(),
            parameters=[
                ToolParameter(
                    name="skill_name",
                    type=ParameterType.STRING,
                    description="Name of the skill to activate",
                    required=True,
                ),
                ToolParameter(
                    name="args",
                    type=ParameterType.STRING,
                    description="Optional arguments to pass to the skill",
                    required=False,
                ),
            ],
            timeout_ms=self._timeout_ms,
        )

    async def execute(self, context: ToolCallContext, arguments: dict[str, Any]) -> ToolResult:
        """Execute skill loading and activation.

        Loads the complete skill content and returns it with base_path for
        path resolution by multi-LLM agents.

        Args:
            context: Execution context containing task/agent/tenant information
            arguments: Tool arguments with skill_name (required) and args (optional)

        Returns:
            ToolResult containing:
                - skill_name: Name of the activated skill
                - base_path: Absolute path to skill directory for path resolution
                - content: Full SKILL.md content (markdown with frontmatter stripped)
                - allowed_tools: List of allowed tools (if any)
                - args: Arguments passed through from input

        Raises:
            Does not raise - errors are returned in ToolResult.error
        """
        start_time = time.time()

        # Extract and validate skill_name
        skill_name = arguments.get("skill_name", "").strip()
        if not skill_name:
            return ToolResult(
                success=False,
                error="skill_name is required",
                duration_ms=int((time.time() - start_time) * 1000),
            )

        # Extract optional args
        args = arguments.get("args")

        try:
            # Load full skill (Stage 2)
            skill = self._skill_loader.load_skill(skill_name)

            duration_ms = int((time.time() - start_time) * 1000)

            # Build result with skill content and metadata
            result_data: dict[str, Any] = {
                "skill_name": skill.metadata.name,
                "base_path": str(skill.base_path),
                "content": skill.content,
            }

            # Include allowed_tools if specified
            if skill.metadata.allowed_tools is not None:
                result_data["allowed_tools"] = skill.metadata.allowed_tools

            # Pass through args if provided
            if args is not None:
                result_data["args"] = args

            return ToolResult(
                success=True,
                result=result_data,
                duration_ms=duration_ms,
            )

        except SkillNotFoundError as e:
            duration_ms = int((time.time() - start_time) * 1000)

            # Try to find similar skills for helpful error message
            available_skills = [entry.name for entry in self._skill_loader.list_skills()]
            similar = self._find_similar(skill_name, available_skills)

            error_msg = str(e)
            if similar:
                error_msg += f". Did you mean '{similar}'?"

            return ToolResult(
                success=False,
                error=error_msg,
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return ToolResult(
                success=False,
                error=f"Failed to load skill '{skill_name}': {str(e)}",
                duration_ms=duration_ms,
            )

    def _build_description(self) -> str:
        """Build dynamic tool description with available skills.

        Generates description that includes:
        - Usage instructions
        - Available skills list with names and descriptions
        - Progressive disclosure explanation
        - Multi-LLM path resolution guidance

        Returns:
            Complete tool description string
        """
        # Get available skills from loader
        skills = self._skill_loader.list_skills()

        # Build skills list section
        if not skills:
            skills_section = "No skills currently available."
        else:
            skill_items = []
            for skill in skills:
                # Format: "skill-name: Description of what the skill does"
                skill_items.append(f"  - {skill.name}: {skill.description}")
            skills_section = "\n".join(skill_items)

        # Build complete description
        description = f"""Load and activate an agent skill from a SKILL.md file.

PROGRESSIVE DISCLOSURE:
This tool uses a two-stage loading pattern:
1. Stage 1 (Tool Description): Lists available skills by name and description
2. Stage 2 (Activation): Loads full skill content when you invoke the tool

AVAILABLE SKILLS:
{skills_section}

USAGE:
Invoke this tool with a skill_name to load the skill's instructions. The tool
returns the skill content and base_path for resolving relative file paths.

PATH RESOLUTION (Multi-LLM Compatibility):
When a skill is activated, you receive a base_path (absolute path to skill
directory). Use this to resolve any relative paths in the skill instructions.
For example, if base_path is "/skills/debug" and skill mentions "script.py",
the full path is "/skills/debug/script.py".

This tool provides discovery (Stage 1) and activation (Stage 2) of skills.
Tool restrictions (if specified in skill metadata) are enforced automatically
by the execution environment.
"""
        return description

    def _find_similar(
        self, name: str, available: list[str], threshold: float = 0.6
    ) -> Optional[str]:
        """Find similar skill name for typo suggestions.

        Uses simple string similarity matching to find the best match
        among available skills.

        Args:
            name: The requested skill name (possibly with typo)
            available: List of available skill names
            threshold: Minimum similarity ratio (0.0 to 1.0) to return match

        Returns:
            Most similar skill name if found above threshold, None otherwise

        Example:
            >>> tool._find_similar("debag", ["debug-agent", "test-agent"])
            'debug-agent'
        """
        if not available:
            return None

        best_match = None
        best_ratio = 0.0

        for candidate in available:
            # Calculate similarity ratio (0.0 to 1.0)
            ratio = SequenceMatcher(None, name.lower(), candidate.lower()).ratio()

            if ratio > best_ratio and ratio >= threshold:
                best_ratio = ratio
                best_match = candidate

        return best_match
