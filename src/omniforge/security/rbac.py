"""Role-Based Access Control (RBAC) for OmniForge.

This module defines permissions, roles, and permission checking logic
for enterprise access control.
"""

from enum import Enum
from typing import Optional


class Permission(str, Enum):
    """Permissions for agent operations.

    Each permission represents a specific action that can be performed
    on agents, tasks, skills, prompts, experiments, cache, tools, chains,
    and enterprise features within the system.
    """

    # Agent permissions
    AGENT_CREATE = "agent:create"
    AGENT_READ = "agent:read"
    AGENT_UPDATE = "agent:update"
    AGENT_DELETE = "agent:delete"

    # Task permissions
    TASK_CREATE = "task:create"
    TASK_READ = "task:read"
    TASK_CANCEL = "task:cancel"

    # Skill permissions
    SKILL_INVOKE = "skill:invoke"

    # Prompt permissions
    PROMPT_CREATE = "prompt:create"
    PROMPT_READ = "prompt:read"
    PROMPT_UPDATE = "prompt:update"
    PROMPT_DELETE = "prompt:delete"
    PROMPT_COMPOSE = "prompt:compose"

    # Experiment permissions
    EXPERIMENT_CREATE = "experiment:create"
    EXPERIMENT_READ = "experiment:read"
    EXPERIMENT_UPDATE = "experiment:update"
    EXPERIMENT_DELETE = "experiment:delete"

    # Cache permissions
    CACHE_CLEAR = "cache:clear"
    CACHE_STATS = "cache:stats"

    # Tool permissions (Phase 6)
    TOOL_EXECUTE = "tool:execute"
    TOOL_REGISTER = "tool:register"
    TOOL_CONFIGURE = "tool:configure"

    # Chain permissions (Phase 6)
    CHAIN_READ = "chain:read"
    CHAIN_READ_FULL = "chain:read_full"  # Can read hidden steps
    CHAIN_EXPORT = "chain:export"

    # Enterprise permissions (Phase 6)
    RATE_LIMIT_CONFIGURE = "rate_limit:configure"
    COST_VIEW = "cost:view"
    COST_CONFIGURE = "cost:configure"

    # Orchestration and handoff permissions
    ORCHESTRATION_DELEGATE = "orchestration:delegate"
    HANDOFF_INITIATE = "handoff:initiate"
    HANDOFF_CANCEL = "handoff:cancel"


class Role(str, Enum):
    """User roles with different permission levels.

    Roles are hierarchical, with higher roles inheriting permissions
    from lower roles:
    - End User: Basic task execution with limited visibility
    - Viewer: Read-only access
    - Operator: Can execute tasks and invoke skills
    - Developer: Can create and manage agents, full tool and chain access
    - Auditor: Read-all access including hidden chain steps for compliance
    - Admin: Full system access including configuration
    """

    END_USER = "end_user"
    VIEWER = "viewer"
    OPERATOR = "operator"
    DEVELOPER = "developer"
    AUDITOR = "auditor"
    ADMIN = "admin"


# Mapping of roles to their permitted actions
ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    # End User: Basic task execution with limited chain visibility
    Role.END_USER: {
        Permission.TASK_CREATE,
        Permission.TASK_READ,
        Permission.TOOL_EXECUTE,
        Permission.CHAIN_READ,  # Limited visibility (no hidden steps)
        Permission.HANDOFF_INITIATE,
    },
    # Viewer: Read-only access to agents, tasks, and chains
    Role.VIEWER: {
        Permission.AGENT_READ,
        Permission.TASK_READ,
        Permission.PROMPT_READ,
        Permission.EXPERIMENT_READ,
        Permission.CHAIN_READ,
    },
    # Operator: Can execute tasks, invoke tools and skills
    Role.OPERATOR: {
        Permission.AGENT_READ,
        Permission.TASK_CREATE,
        Permission.TASK_READ,
        Permission.TASK_CANCEL,
        Permission.SKILL_INVOKE,
        Permission.TOOL_EXECUTE,
        Permission.PROMPT_READ,
        Permission.PROMPT_COMPOSE,
        Permission.EXPERIMENT_READ,
        Permission.CHAIN_READ,
        Permission.ORCHESTRATION_DELEGATE,
        Permission.HANDOFF_INITIATE,
        Permission.HANDOFF_CANCEL,
    },
    # Developer: Full tool and chain access, can create agents
    Role.DEVELOPER: {
        Permission.AGENT_CREATE,
        Permission.AGENT_READ,
        Permission.AGENT_UPDATE,
        Permission.AGENT_DELETE,
        Permission.TASK_CREATE,
        Permission.TASK_READ,
        Permission.TASK_CANCEL,
        Permission.SKILL_INVOKE,
        Permission.TOOL_EXECUTE,
        Permission.TOOL_REGISTER,
        Permission.TOOL_CONFIGURE,
        Permission.CHAIN_READ,
        Permission.CHAIN_READ_FULL,  # Can read hidden steps
        Permission.CHAIN_EXPORT,
        Permission.PROMPT_CREATE,
        Permission.PROMPT_READ,
        Permission.PROMPT_UPDATE,
        Permission.PROMPT_COMPOSE,
        Permission.EXPERIMENT_CREATE,
        Permission.EXPERIMENT_READ,
        Permission.EXPERIMENT_UPDATE,
        Permission.COST_VIEW,
        Permission.ORCHESTRATION_DELEGATE,
        Permission.HANDOFF_INITIATE,
        Permission.HANDOFF_CANCEL,
    },
    # Auditor: Read-all access including hidden steps for compliance
    Role.AUDITOR: {
        Permission.AGENT_READ,
        Permission.TASK_READ,
        Permission.CHAIN_READ,
        Permission.CHAIN_READ_FULL,  # Can read hidden steps
        Permission.CHAIN_EXPORT,
        Permission.PROMPT_READ,
        Permission.EXPERIMENT_READ,
        Permission.COST_VIEW,
    },
    # Admin: Full system access including configuration
    Role.ADMIN: {
        Permission.AGENT_CREATE,
        Permission.AGENT_READ,
        Permission.AGENT_UPDATE,
        Permission.AGENT_DELETE,
        Permission.TASK_CREATE,
        Permission.TASK_READ,
        Permission.TASK_CANCEL,
        Permission.SKILL_INVOKE,
        Permission.TOOL_EXECUTE,
        Permission.TOOL_REGISTER,
        Permission.TOOL_CONFIGURE,
        Permission.CHAIN_READ,
        Permission.CHAIN_READ_FULL,
        Permission.CHAIN_EXPORT,
        Permission.PROMPT_CREATE,
        Permission.PROMPT_READ,
        Permission.PROMPT_UPDATE,
        Permission.PROMPT_DELETE,
        Permission.PROMPT_COMPOSE,
        Permission.EXPERIMENT_CREATE,
        Permission.EXPERIMENT_READ,
        Permission.EXPERIMENT_UPDATE,
        Permission.EXPERIMENT_DELETE,
        Permission.CACHE_CLEAR,
        Permission.CACHE_STATS,
        Permission.RATE_LIMIT_CONFIGURE,
        Permission.COST_VIEW,
        Permission.COST_CONFIGURE,
        Permission.ORCHESTRATION_DELEGATE,
        Permission.HANDOFF_INITIATE,
        Permission.HANDOFF_CANCEL,
    },
}


def check_permission(role: Optional[Role], permission: Permission) -> bool:
    """Check if a role has a specific permission.

    Args:
        role: The user's role (None for unauthenticated users)
        permission: The permission to check

    Returns:
        True if the role has the permission, False otherwise

    Examples:
        >>> check_permission(Role.VIEWER, Permission.AGENT_READ)
        True
        >>> check_permission(Role.VIEWER, Permission.AGENT_CREATE)
        False
        >>> check_permission(Role.ADMIN, Permission.AGENT_DELETE)
        True
        >>> check_permission(None, Permission.AGENT_READ)
        False
    """
    if role is None:
        return False

    return permission in ROLE_PERMISSIONS.get(role, set())
