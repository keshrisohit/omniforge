"""Pydantic models for Skills System.

This module defines the data models for skills, including metadata, configuration,
scope, and hooks following the Skills System specification.
"""

import re
import warnings
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ContextMode(str, Enum):
    """Context mode for skill execution.

    Defines how the skill's context should be handled when activated.
    """

    INHERIT = "inherit"
    FORK = "fork"


class HookDefinition(BaseModel):
    """Individual hook definition.

    Attributes:
        type: Type of hook (currently only 'command' is supported)
        command: Command to execute
        once: If True, run only once per session (default: False)
    """

    type: str = "command"
    command: str
    once: bool = False


class HookMatcher(BaseModel):
    """Hook with optional tool matcher.

    Attributes:
        matcher: Optional tool name pattern (e.g., "Bash", "Read")
        hooks: List of hooks to run for this matcher
    """

    matcher: Optional[str] = None
    hooks: list[HookDefinition]


class SkillHooks(BaseModel):
    """Skill lifecycle hooks configuration.

    Supports both Claude Code format (PreToolUse/PostToolUse/Stop) and
    legacy OmniForge format (pre/post) for backward compatibility.

    Claude Code Format (Recommended):
        PreToolUse: Hooks to run before tool usage
        PostToolUse: Hooks to run after tool usage
        Stop: Hooks to run when skill stops

    Legacy Format (Deprecated):
        pre: Path to pre-activation script
        post: Path to post-execution script

    Attributes:
        PreToolUse: Optional list of hooks with tool matchers for pre-tool execution
        PostToolUse: Optional list of hooks with tool matchers for post-tool execution
        Stop: Optional list of hooks for skill termination
        pre: DEPRECATED - Path to pre-activation script (use PreToolUse instead)
        post: DEPRECATED - Path to post-execution script (use PostToolUse instead)
    """

    # New Claude Code format
    PreToolUse: Optional[list[HookMatcher]] = None
    PostToolUse: Optional[list[HookMatcher]] = None
    Stop: Optional[list[HookMatcher]] = None

    # Legacy format (deprecated)
    pre: Optional[str] = None
    post: Optional[str] = None

    @model_validator(mode="after")
    def migrate_legacy_format(self) -> "SkillHooks":
        """Migrate legacy pre/post format to new event-based format.

        If legacy 'pre' or 'post' fields are used, they are automatically
        converted to the new PreToolUse/PostToolUse format.

        Returns:
            Self with migrated hooks
        """
        # Warn about deprecated format
        if self.pre is not None or self.post is not None:
            warnings.warn(
                "The 'pre' and 'post' hook fields are deprecated. "
                "Use 'PreToolUse', 'PostToolUse', and 'Stop' instead. "
                "See Claude Code skills documentation for details.",
                DeprecationWarning,
                stacklevel=2,
            )

        # Migrate 'pre' to PreToolUse if not already set
        if self.pre and not self.PreToolUse:
            self.PreToolUse = [HookMatcher(hooks=[HookDefinition(command=self.pre)])]

        # Migrate 'post' to PostToolUse if not already set
        if self.post and not self.PostToolUse:
            self.PostToolUse = [HookMatcher(hooks=[HookDefinition(command=self.post)])]

        return self


class SkillScope(BaseModel):
    """Skill scope and visibility configuration.

    Defines where and for whom the skill is available.

    Attributes:
        agents: Optional list of agent IDs that can use this skill
        tenants: Optional list of tenant IDs that can access this skill
        environments: Optional list of environments where skill is available
    """

    agents: Optional[list[str]] = None
    tenants: Optional[list[str]] = None
    environments: Optional[list[str]] = None


class SkillMetadata(BaseModel):
    """Skill metadata from YAML frontmatter.

    This model represents all metadata fields that can be defined in the
    skill file's YAML frontmatter section, following Claude Code specifications.

    Attributes:
        name: Skill identifier in kebab-case (1-64 characters, per Claude Code spec)
        description: Brief description of skill's purpose (max 1024 characters)
        allowed_tools: Optional list of tool names that skill can use
        model: Optional LLM model override for skill execution
        context: Context mode for skill execution (default: inherit)
        agent: Optional specific agent configuration
        hooks: Optional lifecycle hooks configuration
        user_invocable: Whether skill appears in user-facing menus (default: True)
        disable_model_invocation: Prevent model from invoking programmatically (default: False)
        priority: Optional priority level for skill ordering (default: 0)
        tags: Optional list of tags for categorization
        scope: Optional scope restrictions for skill availability
        execution_mode: Execution mode for autonomous skills (default: "autonomous")
        max_iterations: Max ReAct iterations for autonomous execution (default: None)
        max_retries_per_tool: Max retries per tool for autonomous execution (default: None)
        timeout_per_iteration: Timeout per iteration for autonomous execution (default: None)
        early_termination: Allow early termination on confidence (default: None)
    """

    # Core fields (Claude Code standard)
    name: str = Field(..., min_length=1, max_length=64)
    description: str = Field(..., min_length=1, max_length=1024)
    allowed_tools: Optional[list[str]] = Field(None, alias="allowed-tools")
    model: Optional[str] = None
    context: ContextMode = ContextMode.INHERIT
    agent: Optional[str] = None
    hooks: Optional[SkillHooks] = None

    # Visibility control (Claude Code standard)
    user_invocable: bool = Field(True, alias="user-invocable")
    disable_model_invocation: bool = Field(False, alias="disable-model-invocation")

    # OmniForge extensions
    priority: int = 0
    tags: Optional[list[str]] = None
    scope: Optional[SkillScope] = None
    legacy_large_file: bool = Field(
        False,
        alias="legacy-large-file",
        description="Bypass 500-line limit for legacy skills (deprecated)",
    )

    # Autonomous execution configuration
    execution_mode: str = Field(
        default="autonomous",
        alias="execution-mode",
        description="Execution mode: 'autonomous' or 'simple'",
    )
    max_iterations: Optional[int] = Field(
        None,
        alias="max-iterations",
        ge=1,
        le=100,
        description="Max ReAct iterations (default: 15)",
    )
    max_retries_per_tool: Optional[int] = Field(
        None,
        alias="max-retries-per-tool",
        ge=0,
        le=10,
        description="Max retries per tool (default: 3)",
    )
    timeout_per_iteration: Optional[str] = Field(
        None,
        alias="timeout-per-iteration",
        description="Timeout per iteration (e.g., '30s')",
    )
    early_termination: Optional[bool] = Field(
        None,
        alias="early-termination",
        description="Allow early termination on confidence",
    )

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("name")
    @classmethod
    def validate_kebab_case(cls, value: str) -> str:
        """Validate that skill name follows kebab-case format.

        Args:
            value: The skill name to validate

        Returns:
            The validated skill name

        Raises:
            ValueError: If name format is invalid
        """
        if not re.match(r"^[a-z][a-z0-9-]*$", value):
            raise ValueError(
                "Skill name must be kebab-case: start with lowercase letter, "
                "contain only lowercase letters, numbers, and hyphens"
            )
        return value


class Skill(BaseModel):
    """Complete skill definition with metadata and content.

    Represents a full skill loaded from a skill file, including both
    metadata and instruction content.

    Attributes:
        metadata: Skill metadata from YAML frontmatter
        content: Skill instruction content (markdown)
        path: Absolute path to skill file
        base_path: Base directory path for resolving relative paths
        storage_layer: Storage layer identifier (e.g., "global", "tenant-123")
        script_paths: Optional resolved absolute paths to hook scripts
    """

    metadata: SkillMetadata
    content: str
    path: Path
    base_path: Path
    storage_layer: str
    script_paths: Optional[dict[str, Path]] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def is_script_file(self, file_path: Path) -> bool:
        """Check if a file path is one of this skill's hook scripts.

        Args:
            file_path: The file path to check

        Returns:
            True if the file is a hook script for this skill, False otherwise
        """
        if not self.script_paths:
            return False

        # Resolve the input path to absolute
        resolved_path = file_path.resolve()

        # Check against all script paths
        for script_path in self.script_paths.values():
            if script_path.resolve() == resolved_path:
                return True

        return False


class SkillIndexEntry(BaseModel):
    """Lightweight skill entry for discovery and listing.

    This model contains minimal information for skill discovery without
    loading full skill content.

    Attributes:
        name: Skill identifier in kebab-case (max 64 characters)
        description: Brief description of skill's purpose (max 1024 characters)
        path: Absolute path to skill file
        storage_layer: Storage layer identifier
        tags: Optional list of tags for categorization
        priority: Priority level for skill ordering (default: 0)
    """

    name: str = Field(..., min_length=1, max_length=64)
    description: str = Field(..., min_length=1, max_length=1024)
    path: Path
    storage_layer: str
    tags: Optional[list[str]] = None
    priority: int = 0

    model_config = ConfigDict(arbitrary_types_allowed=True)
