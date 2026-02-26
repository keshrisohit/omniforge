"""Built-in tools for OmniForge agents.

This module provides core built-in tools including LLM, file system,
database access, and other essential agent capabilities.
"""

from omniforge.tools.builtin.bash import BashTool
from omniforge.tools.builtin.database import DatabaseTool
from omniforge.tools.builtin.email import EmailTool
from omniforge.tools.builtin.external import ExternalAPITool, WeatherAPITool
from omniforge.tools.builtin.filesystem import FileSystemTool

# New function-based tools (preferred)
from omniforge.tools.builtin.function import (
    FunctionDefinition,
    FunctionRegistry,
    FunctionTool,
    function,
)
from omniforge.tools.builtin.glob import GlobTool
from omniforge.tools.builtin.grep import GrepTool
from omniforge.tools.builtin.llm import LLMTool
from omniforge.tools.builtin.read import ReadTool

# Deprecated skill-based tools (backward compatibility)
from omniforge.tools.builtin.skill import (
    SkillDefinition,
    SkillRegistry,
    SkillTool,
    skill,
)
from omniforge.tools.builtin.subagent import SubAgentTool
from omniforge.tools.builtin.platform import (
    AddSkillToAgentTool,
    CreateAgentTool,
    ListAgentsTool,
    ListSkillsTool,
    list_all_skills,
    make_agent_id,
    read_skill_meta,
    register_platform_tools,
)
from omniforge.tools.builtin.artifact import (
    FetchArtifactTool,
    StoreArtifactTool,
    register_artifact_tools,
)
from omniforge.tools.builtin.write import WriteTool

__all__ = [
    "LLMTool",
    "DatabaseTool",
    "EmailTool",
    "FileSystemTool",
    "SubAgentTool",
    "ExternalAPITool",
    "WeatherAPITool",
    # Command execution and file operations
    "BashTool",
    "ReadTool",
    "WriteTool",
    "GrepTool",
    "GlobTool",
    # New function-based tools
    "FunctionDefinition",
    "FunctionRegistry",
    "FunctionTool",
    "function",
    # Deprecated skill-based tools (for backward compatibility)
    "SkillDefinition",
    "SkillRegistry",
    "SkillTool",
    "skill",
    # Platform management tools
    "ListAgentsTool",
    "ListSkillsTool",
    "CreateAgentTool",
    "AddSkillToAgentTool",
    "register_platform_tools",
    "list_all_skills",
    "read_skill_meta",
    "make_agent_id",
    # Artifact storage tools
    "StoreArtifactTool",
    "FetchArtifactTool",
    "register_artifact_tools",
]
