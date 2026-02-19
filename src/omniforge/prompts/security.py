"""Layer-based access control for prompt management.

This module implements access control policies for prompt layers,
ensuring users can only modify prompts at appropriate hierarchical levels
based on their roles.
"""

from typing import Optional

from omniforge.prompts.enums import PromptLayer
from omniforge.prompts.models import Prompt
from omniforge.security.rbac import Permission, Role, check_permission

# Mapping of roles to the prompt layers they can modify
LAYER_ACCESS: dict[Role, set[PromptLayer]] = {
    Role.VIEWER: set(),
    Role.OPERATOR: set(),
    Role.DEVELOPER: {PromptLayer.FEATURE, PromptLayer.AGENT},
    Role.ADMIN: {
        PromptLayer.SYSTEM,
        PromptLayer.TENANT,
        PromptLayer.FEATURE,
        PromptLayer.AGENT,
        PromptLayer.USER,
    },
}


def can_modify_layer(role: Role, layer: PromptLayer) -> bool:
    """Check if a role has permission to modify prompts at a specific layer.

    Args:
        role: The user's role
        layer: The prompt layer to check

    Returns:
        True if the role can modify the layer, False otherwise

    Examples:
        >>> can_modify_layer(Role.ADMIN, PromptLayer.SYSTEM)
        True
        >>> can_modify_layer(Role.DEVELOPER, PromptLayer.SYSTEM)
        False
        >>> can_modify_layer(Role.DEVELOPER, PromptLayer.FEATURE)
        True
        >>> can_modify_layer(Role.VIEWER, PromptLayer.FEATURE)
        False
    """
    return layer in LAYER_ACCESS.get(role, set())


def check_prompt_access(user_role: Role, prompt: Prompt, operation: str) -> bool:
    """Verify user has permission for an operation on a specific prompt.

    This function combines two access checks:
    1. RBAC permission check - Does the role have the operation permission?
    2. Layer access check - Can the role modify prompts at this layer?

    Args:
        user_role: The user's role
        prompt: The prompt being accessed
        operation: The operation being performed (create, read, update, delete, compose)

    Returns:
        True if access is granted, False otherwise

    Raises:
        ValueError: If operation is not a valid prompt operation

    Examples:
        >>> prompt = Prompt(
        ...     id="p1",
        ...     layer=PromptLayer.FEATURE,
        ...     scope_id="feature1",
        ...     name="Test",
        ...     content="Test prompt"
        ... )
        >>> check_prompt_access(Role.DEVELOPER, prompt, "update")
        True
        >>> check_prompt_access(Role.VIEWER, prompt, "update")
        False
        >>> system_prompt = Prompt(
        ...     id="p2",
        ...     layer=PromptLayer.SYSTEM,
        ...     scope_id="system",
        ...     name="System",
        ...     content="System prompt"
        ... )
        >>> check_prompt_access(Role.DEVELOPER, system_prompt, "update")
        False
    """
    # Map operation strings to Permission enum values
    operation_to_permission = {
        "create": Permission.PROMPT_CREATE,
        "read": Permission.PROMPT_READ,
        "update": Permission.PROMPT_UPDATE,
        "delete": Permission.PROMPT_DELETE,
        "compose": Permission.PROMPT_COMPOSE,
    }

    if operation not in operation_to_permission:
        raise ValueError(
            f"Invalid operation '{operation}'. Must be one of: "
            f"{', '.join(operation_to_permission.keys())}"
        )

    permission = operation_to_permission[operation]

    # Check RBAC permission first
    if not check_permission(user_role, permission):
        return False

    # For read and compose operations, grant access regardless of layer
    # (users can read/compose any prompt they have permission for)
    if operation in ("read", "compose"):
        return True

    # For create, update, delete operations, check layer access
    return can_modify_layer(user_role, prompt.layer)


def can_access_tenant_prompts(
    user_tenant_id: Optional[str], prompt_tenant_id: Optional[str]
) -> bool:
    """Check if a user can access prompts from a specific tenant.

    Tenant isolation rules:
    - SYSTEM layer prompts (tenant_id=None) are visible to all tenants
    - Tenant-scoped prompts are only visible to users from that tenant
    - Users without a tenant_id can only access SYSTEM prompts

    Args:
        user_tenant_id: The user's tenant ID (None for system users)
        prompt_tenant_id: The prompt's tenant ID (None for system prompts)

    Returns:
        True if the user can access the prompt, False otherwise

    Examples:
        >>> can_access_tenant_prompts("tenant-1", "tenant-1")
        True
        >>> can_access_tenant_prompts("tenant-1", "tenant-2")
        False
        >>> can_access_tenant_prompts("tenant-1", None)
        True
        >>> can_access_tenant_prompts(None, "tenant-1")
        False
        >>> can_access_tenant_prompts(None, None)
        True
    """
    # SYSTEM prompts (no tenant_id) are visible to everyone
    if prompt_tenant_id is None:
        return True

    # Tenant-scoped prompts require matching tenant_id
    return user_tenant_id == prompt_tenant_id
