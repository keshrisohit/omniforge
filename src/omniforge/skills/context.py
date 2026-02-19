"""Skill execution context for managing tool restrictions.

This module provides the SkillContext class that enforces tool access restrictions
and validates tool arguments during skill execution.
"""

from pathlib import Path
from typing import Any, Optional

from omniforge.skills.errors import SkillScriptReadError, SkillToolNotAllowedError
from omniforge.skills.models import Skill


class SkillContext:
    """Context manager for skill execution with tool restrictions.

    Manages tool access control during skill execution, enforcing allowed_tools
    restrictions and preventing access to skill hook scripts.

    Attributes:
        skill: The skill being executed
        executor: Optional tool executor reference for future integration
    """

    def __init__(self, skill: Skill, executor: Optional[Any] = None) -> None:
        """Initialize skill context.

        Args:
            skill: The skill to execute with restrictions
            executor: Optional tool executor for future integration
        """
        self.skill = skill
        self.executor = executor
        self._allowed_tools: Optional[set[str]] = None

    def __enter__(self) -> "SkillContext":
        """Enter context manager and set up allowed tools.

        Returns:
            Self for context manager protocol
        """
        # Convert allowed_tools list to case-insensitive set
        if self.skill.metadata.allowed_tools is not None:
            self._allowed_tools = {tool.lower() for tool in self.skill.metadata.allowed_tools}
        else:
            self._allowed_tools = None
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context manager and clear state.

        Args:
            exc_type: Exception type if raised
            exc_val: Exception value if raised
            exc_tb: Exception traceback if raised
        """
        self._allowed_tools = None

    def check_tool_allowed(self, tool_name: str) -> None:
        """Validate that a tool is allowed for this skill.

        Args:
            tool_name: Name of the tool to check

        Raises:
            SkillToolNotAllowedError: If tool is not in allowed_tools list
        """
        # No restrictions if allowed_tools is None
        if self._allowed_tools is None:
            return

        # Case-insensitive comparison
        if tool_name.lower() not in self._allowed_tools:
            raise SkillToolNotAllowedError(
                skill_name=self.skill.metadata.name,
                tool_name=tool_name,
                allowed_tools=self.skill.metadata.allowed_tools,
            )

    def check_tool_arguments(self, tool_name: str, arguments: dict[str, Any]) -> None:
        """Validate tool arguments against skill restrictions.

        Specifically blocks Read tool attempts to access skill hook scripts,
        which is critical for context efficiency.

        Args:
            tool_name: Name of the tool being called
            arguments: Tool arguments to validate

        Raises:
            SkillScriptReadError: If attempting to read a skill hook script
        """
        # Only validate Read tool for script access
        if tool_name.lower() != "read":
            return

        # Check if file_path argument targets a script file
        file_path_arg = arguments.get("file_path")
        if not file_path_arg:
            return

        # Convert to Path for comparison
        file_path = Path(file_path_arg)

        # Check if this file is one of the skill's scripts
        if self.skill.is_script_file(file_path):
            raise SkillScriptReadError(
                skill_name=self.skill.metadata.name,
                script_type="hook",
                script_path=str(file_path),
                reason=(
                    "Skills cannot read their own hook scripts. "
                    "This restriction improves context efficiency. "
                    "Hook scripts are executed automatically by the system."
                ),
            )

    @property
    def is_restricted(self) -> bool:
        """Check if tool restrictions are active.

        Returns:
            True if tool restrictions are enforced, False if all tools allowed
        """
        return self._allowed_tools is not None

    @property
    def allowed_tool_names(self) -> Optional[set[str]]:
        """Get set of allowed tool names.

        Returns:
            Set of allowed tool names (original case), or None if unrestricted
        """
        if self._allowed_tools is None:
            return None
        # Return original case from metadata (empty list returns empty set)
        if self.skill.metadata.allowed_tools is not None:
            return set(self.skill.metadata.allowed_tools)
        return None
