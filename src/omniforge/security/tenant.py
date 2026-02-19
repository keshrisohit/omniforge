"""Tenant context and middleware for multi-tenancy support.

This module provides tenant isolation functionality through context variables
and middleware that extracts tenant information from HTTP headers.
"""

from contextvars import ContextVar
from typing import Optional

# Context variable to store the current tenant ID
_tenant_context: ContextVar[Optional[str]] = ContextVar("tenant_id", default=None)


class TenantContext:
    """Manages tenant context for multi-tenancy isolation.

    This class provides methods to get and set the current tenant ID
    using context variables for thread-safe and async-safe storage.
    """

    @staticmethod
    def get() -> Optional[str]:
        """Get the current tenant ID from context.

        Returns:
            The current tenant ID, or None if not set

        Examples:
            >>> TenantContext.set("tenant-123")
            >>> TenantContext.get()
            'tenant-123'
        """
        return _tenant_context.get()

    @staticmethod
    def set(tenant_id: Optional[str]) -> None:
        """Set the current tenant ID in context.

        Args:
            tenant_id: The tenant ID to set, or None to clear

        Examples:
            >>> TenantContext.set("tenant-123")
            >>> TenantContext.get()
            'tenant-123'
        """
        _tenant_context.set(tenant_id)

    @staticmethod
    def clear() -> None:
        """Clear the current tenant ID from context.

        Examples:
            >>> TenantContext.set("tenant-123")
            >>> TenantContext.clear()
            >>> TenantContext.get()
            None
        """
        _tenant_context.set(None)


def get_tenant_id() -> Optional[str]:
    """Helper function to get the current tenant ID.

    This is a convenience wrapper around TenantContext.get() for
    easier importing and usage in other modules.

    Returns:
        The current tenant ID, or None if not set

    Examples:
        >>> from omniforge.security.tenant import get_tenant_id
        >>> tenant_id = get_tenant_id()
    """
    return TenantContext.get()
