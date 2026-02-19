"""Custom exceptions for Skills System.

This module defines the exception hierarchy for skill-related errors,
providing structured error handling with error codes and context.
"""

from typing import Any, Optional


class SkillError(Exception):
    """Base exception for all skill-related errors.

    Attributes:
        message: Human-readable error message
        error_code: Machine-readable error code
        context: Additional context information about the error
    """

    def __init__(
        self, message: str, error_code: str, context: Optional[dict[str, Any]] = None
    ) -> None:
        """Initialize skill error.

        Args:
            message: Human-readable error description
            error_code: Machine-readable error code
            context: Optional additional context information
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.context = context or {}


class SkillNotFoundError(SkillError):
    """Raised when a skill cannot be found.

    This error indicates that the requested skill does not exist in the
    specified storage layer or scope.
    """

    def __init__(self, skill_name: str, storage_layer: Optional[str] = None) -> None:
        """Initialize skill not found error.

        Args:
            skill_name: The name of the skill that was not found
            storage_layer: Optional storage layer that was searched
        """
        if storage_layer:
            message = f"Skill '{skill_name}' not found in storage layer '{storage_layer}'"
        else:
            message = f"Skill '{skill_name}' not found"

        context = {"skill_name": skill_name}
        if storage_layer:
            context["storage_layer"] = storage_layer

        super().__init__(
            message=message,
            error_code="skill_not_found",
            context=context,
        )
        self.skill_name = skill_name
        self.storage_layer = storage_layer


class SkillParseError(SkillError):
    """Raised when a skill file cannot be parsed.

    This error indicates that the skill file has invalid format, malformed
    YAML frontmatter, or other parsing issues.
    """

    def __init__(self, skill_path: str, reason: str, line_number: Optional[int] = None) -> None:
        """Initialize skill parse error.

        Args:
            skill_path: Path to the skill file that failed to parse
            reason: Description of why parsing failed
            line_number: Optional line number where error occurred
        """
        if line_number:
            message = f"Failed to parse skill file '{skill_path}' at line {line_number}: {reason}"
        else:
            message = f"Failed to parse skill file '{skill_path}': {reason}"

        context: dict[str, Any] = {"skill_path": skill_path, "reason": reason}
        if line_number:
            context["line_number"] = line_number

        super().__init__(
            message=message,
            error_code="skill_parse_error",
            context=context,
        )
        self.skill_path = skill_path
        self.reason = reason
        self.line_number = line_number


class SkillToolNotAllowedError(SkillError):
    """Raised when a skill attempts to use a disallowed tool.

    This error indicates that a skill tried to invoke a tool that is not
    in its allowed_tools list.
    """

    def __init__(
        self, skill_name: str, tool_name: str, allowed_tools: Optional[list[str]] = None
    ) -> None:
        """Initialize skill tool not allowed error.

        Args:
            skill_name: Name of the skill attempting to use the tool
            tool_name: Name of the tool that is not allowed
            allowed_tools: Optional list of tools that are allowed
        """
        if allowed_tools:
            message = (
                f"Skill '{skill_name}' cannot use tool '{tool_name}'. "
                f"Allowed tools: {', '.join(allowed_tools)}"
            )
        else:
            message = (
                f"Skill '{skill_name}' cannot use tool '{tool_name}'. "
                f"No tools are allowed for this skill"
            )

        context: dict[str, Any] = {"skill_name": skill_name, "tool_name": tool_name}
        if allowed_tools:
            context["allowed_tools"] = allowed_tools

        super().__init__(
            message=message,
            error_code="skill_tool_not_allowed",
            context=context,
        )
        self.skill_name = skill_name
        self.tool_name = tool_name
        self.allowed_tools = allowed_tools


class SkillActivationError(SkillError):
    """Raised when a skill cannot be activated.

    This error indicates that skill activation failed due to scope restrictions,
    missing dependencies, or other activation constraints.
    """

    def __init__(self, skill_name: str, reason: str) -> None:
        """Initialize skill activation error.

        Args:
            skill_name: Name of the skill that failed to activate
            reason: Description of why activation failed
        """
        message = f"Failed to activate skill '{skill_name}': {reason}"

        super().__init__(
            message=message,
            error_code="skill_activation_error",
            context={"skill_name": skill_name, "reason": reason},
        )
        self.skill_name = skill_name
        self.reason = reason


class SkillScriptReadError(SkillError):
    """Raised when a skill hook script cannot be read.

    This error indicates that a pre or post hook script file exists but
    cannot be read due to permissions, encoding issues, or other problems.
    """

    def __init__(self, skill_name: str, script_type: str, script_path: str, reason: str) -> None:
        """Initialize skill script read error.

        Args:
            skill_name: Name of the skill owning the script
            script_type: Type of script ("pre" or "post")
            script_path: Path to the script that failed to read
            reason: Description of why reading failed
        """
        message = (
            f"Failed to read {script_type} hook script for skill '{skill_name}' "
            f"at '{script_path}': {reason}"
        )

        super().__init__(
            message=message,
            error_code="skill_script_read_error",
            context={
                "skill_name": skill_name,
                "script_type": script_type,
                "script_path": script_path,
                "reason": reason,
            },
        )
        self.skill_name = skill_name
        self.script_type = script_type
        self.script_path = script_path
        self.reason = reason


class SkillValidationError(SkillError):
    """Raised when a skill fails validation checks.

    This error indicates that a skill does not meet required validation
    criteria such as file size limits or content requirements.
    """

    def __init__(
        self, skill_name: str, reason: str, details: Optional[dict[str, Any]] = None
    ) -> None:
        """Initialize skill validation error.

        Args:
            skill_name: Name of the skill that failed validation
            reason: Description of why validation failed
            details: Optional additional validation details
        """
        message = f"Skill '{skill_name}' failed validation: {reason}"

        context: dict[str, Any] = {"skill_name": skill_name, "reason": reason}
        if details:
            context.update(details)

        super().__init__(
            message=message,
            error_code="skill_validation_error",
            context=context,
        )
        self.skill_name = skill_name
        self.reason = reason
        self.details = details
