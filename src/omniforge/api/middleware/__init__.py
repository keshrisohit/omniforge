"""API middleware components.

This module exports middleware functions for error handling,
authentication, and other cross-cutting concerns.
"""

from omniforge.api.middleware.error_handler import setup_error_handlers

__all__ = ["setup_error_handlers"]
