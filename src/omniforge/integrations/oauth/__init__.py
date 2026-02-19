"""OAuth integration and provider management.

This module provides OAuth 2.0 authentication flows, token management,
and integration providers for external services.
"""

from omniforge.integrations.oauth.manager import OAuthConfig, OAuthManager

__all__ = ["OAuthConfig", "OAuthManager"]
