"""OmniForge API module.

This module provides the FastAPI application and route handlers
for the OmniForge platform.
"""

from omniforge.api.app import app, create_app

__all__ = ["app", "create_app"]
