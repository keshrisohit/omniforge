"""FastAPI dependencies for authentication and authorization.

This module provides dependency injection functions for extracting
and validating authentication credentials and permissions in API routes.
"""

from typing import Callable, Optional

from fastapi import Header, Request

from omniforge.agents.errors import ForbiddenError, UnauthorizedError
from omniforge.security.auth import validate_api_key
from omniforge.security.rbac import Permission, Role, check_permission


def get_user_role(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
) -> Optional[Role]:
    """Extract and validate user role from API key header.

    Args:
        x_api_key: API key from X-API-Key header

    Returns:
        User role if authenticated, None if no authentication provided

    Raises:
        UnauthorizedError: If API key is provided but invalid
    """
    if not x_api_key:
        return None

    is_valid, tenant_id, role = validate_api_key(x_api_key)
    if not is_valid:
        raise UnauthorizedError("Invalid API key")

    return role


def require_permission(permission: Permission) -> Callable[..., None]:
    """Create a dependency that requires a specific permission.

    Args:
        permission: The permission required for the endpoint

    Returns:
        FastAPI dependency function that validates the permission

    Example:
        >>> @router.post("/api/v1/agents")
        >>> async def create_agent(
        ...     _: None = Depends(require_permission(Permission.AGENT_CREATE))
        ... ):
        ...     # Only users with AGENT_CREATE permission can access
        ...     pass
    """

    def permission_dependency(
        x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    ) -> None:
        """Check if user has required permission.

        Args:
            x_api_key: API key from X-API-Key header

        Raises:
            UnauthorizedError: If no authentication provided
            ForbiddenError: If user lacks required permission
        """
        if not x_api_key:
            raise UnauthorizedError("Authentication required")

        is_valid, tenant_id, role = validate_api_key(x_api_key)
        if not is_valid:
            raise UnauthorizedError("Invalid API key")

        if not check_permission(role, permission):
            raise ForbiddenError(f"Insufficient permissions: requires {permission.value}")

    return permission_dependency


def get_current_tenant(request: Request) -> Optional[str]:
    """Get the current tenant ID from request state.

    The tenant ID is set by TenantMiddleware from headers.

    Args:
        request: FastAPI request object

    Returns:
        Tenant ID if present in request state, None otherwise
    """
    return getattr(request.state, "tenant_id", None)


def get_current_user(request: Request) -> Optional[str]:
    """Get the current user ID from request state.

    The user ID is extracted from authentication (API key or JWT).

    Args:
        request: FastAPI request object

    Returns:
        User ID if authenticated, None otherwise
    """
    return getattr(request.state, "user_id", None)
