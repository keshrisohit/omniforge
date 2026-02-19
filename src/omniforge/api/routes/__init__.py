"""API route handlers for OmniForge platform.

This module exports all API routers for easy import and inclusion
in the main FastAPI application.
"""

from omniforge.api.routes.builder_agents import router as builder_agents_router
from omniforge.api.routes.chat import router as chat_router
from omniforge.api.routes.conversation import router as conversation_router
from omniforge.api.routes.oauth import router as oauth_router

__all__ = [
    "chat_router",
    "conversation_router",
    "builder_agents_router",
    "oauth_router",
]
