"""OAuth providers for specific integrations.

This module provides integration-specific OAuth providers with
workspace discovery and specialized handling.
"""

from omniforge.integrations.oauth.providers.notion import NotionOAuthProvider

__all__ = ["NotionOAuthProvider"]
