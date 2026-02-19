"""Security module for OmniForge enterprise features.

This module provides:
- Multi-tenancy isolation through tenant context
- Role-Based Access Control (RBAC)
- Authentication and authorization
"""

from omniforge.security.auth import validate_api_key, validate_bearer_token
from omniforge.security.isolation import (
    enforce_agent_isolation,
    enforce_task_isolation,
    filter_by_tenant,
)
from omniforge.security.rbac import ROLE_PERMISSIONS, Permission, Role, check_permission
from omniforge.security.tenant import TenantContext, get_tenant_id

__all__ = [
    # Tenant management
    "TenantContext",
    "get_tenant_id",
    # RBAC
    "Permission",
    "Role",
    "ROLE_PERMISSIONS",
    "check_permission",
    # Authentication
    "validate_api_key",
    "validate_bearer_token",
    # Isolation
    "enforce_agent_isolation",
    "enforce_task_isolation",
    "filter_by_tenant",
]
