"""Skills System for OmniForge.

This module provides the Skills System that allows loading and activating
reusable instruction sets (skills) for AI agents.
"""

from omniforge.skills.config import (
    AutonomousConfig,
    ExecutionMetrics,
    ExecutionResult,
    ExecutionState,
    PlatformAutonomousConfig,
    is_valid_duration,
    merge_configs,
    parse_duration_ms,
    validate_skill_config,
)
from omniforge.skills.context_loader import ContextLoader, FileReference, LoadedContext
from omniforge.skills.errors import (
    SkillActivationError,
    SkillError,
    SkillNotFoundError,
    SkillParseError,
    SkillScriptReadError,
    SkillToolNotAllowedError,
)
from omniforge.skills.loader import SkillLoader
from omniforge.skills.models import (
    ContextMode,
    Skill,
    SkillHooks,
    SkillIndexEntry,
    SkillMetadata,
    SkillScope,
)
from omniforge.skills.parser import SkillParser
from omniforge.skills.prompts import PromptBuilder
from omniforge.skills.script_executor import (
    SandboxMode,
    ScriptExecutionConfig,
    ScriptExecutor,
    ScriptResult,
    SecurityError,
)
from omniforge.skills.storage import SkillStorageManager, StorageConfig
from omniforge.skills.string_substitutor import (
    StringSubstitutor,
    SubstitutedContent,
    SubstitutionContext,
)
from omniforge.skills.tool import SkillTool

__all__ = [
    # Models
    "ContextMode",
    "Skill",
    "SkillHooks",
    "SkillIndexEntry",
    "SkillMetadata",
    "SkillScope",
    # Context Loader
    "ContextLoader",
    "FileReference",
    "LoadedContext",
    # Autonomous Execution Config
    "AutonomousConfig",
    "ExecutionMetrics",
    "ExecutionResult",
    "ExecutionState",
    "PlatformAutonomousConfig",
    "parse_duration_ms",
    "is_valid_duration",
    "validate_skill_config",
    "merge_configs",
    # Storage
    "SkillStorageManager",
    "StorageConfig",
    # Parser
    "SkillParser",
    # Loader
    "SkillLoader",
    # Prompts
    "PromptBuilder",
    # Script Executor
    "SandboxMode",
    "ScriptExecutionConfig",
    "ScriptExecutor",
    "ScriptResult",
    "SecurityError",
    # String Substitution
    "StringSubstitutor",
    "SubstitutedContent",
    "SubstitutionContext",
    # Tool
    "SkillTool",
    # Errors
    "SkillActivationError",
    "SkillError",
    "SkillNotFoundError",
    "SkillParseError",
    "SkillScriptReadError",
    "SkillToolNotAllowedError",
]
