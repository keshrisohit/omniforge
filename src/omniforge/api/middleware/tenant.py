"""FastAPI middleware for tenant context management.

This module provides middleware that extracts tenant information from
HTTP headers and sets the tenant context for request processing.
"""

from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from omniforge.security.auth import validate_api_key
from omniforge.security.tenant import TenantContext


class TenantMiddleware(BaseHTTPMiddleware):
    """Middleware to extract and set tenant context from HTTP headers.

    This middleware extracts the tenant ID from the X-Tenant-ID header
    or from API key authentication and sets it in the tenant context
    for the duration of the request.

    The tenant context is automatically cleared after each request.

    Headers supported:
    - X-Tenant-ID: Direct tenant ID
    - X-API-Key: API key in format "tenant_id:role:secret"
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and set tenant context.

        Args:
            request: The incoming HTTP request
            call_next: The next middleware/handler in the chain

        Returns:
            The HTTP response from downstream handlers
        """
        try:
            # Try to get tenant ID from X-Tenant-ID header first
            tenant_id = request.headers.get("X-Tenant-ID")

            # If not found, try to extract from API key
            if not tenant_id:
                api_key = request.headers.get("X-API-Key")
                if api_key:
                    is_valid, extracted_tenant_id, role = validate_api_key(api_key)
                    if is_valid and extracted_tenant_id:
                        tenant_id = extracted_tenant_id
                        # Store role in request state for later use
                        request.state.user_role = role

            # Set tenant context if we have a tenant ID
            if tenant_id:
                TenantContext.set(tenant_id)
                # Store tenant_id in request state for dependency access
                request.state.tenant_id = tenant_id

            # Process the request
            response: Response = await call_next(request)

            return response

        finally:
            # Always clear tenant context after request
            TenantContext.clear()
