"""Notion OAuth provider with workspace discovery.

This module provides Notion-specific OAuth integration with workspace
name discovery using the Notion API.
"""

from typing import Optional

import httpx

from omniforge.integrations.oauth.manager import OAuthConfig, OAuthManager, OAuthTokenError


class NotionOAuthProvider:
    """Notion-specific OAuth provider.

    Extends base OAuth manager with Notion workspace discovery.
    Automatically fetches workspace name after successful OAuth.

    Example:
        >>> config = OAuthConfig(
        ...     integration_id="notion",
        ...     client_id="...",
        ...     client_secret="...",
        ...     authorize_url="https://api.notion.com/v1/oauth/authorize",
        ...     token_url="https://api.notion.com/v1/oauth/token",
        ...     scopes=["read_content"],
        ...     redirect_uri="https://app.example.com/oauth/callback"
        ... )
        >>> provider = NotionOAuthProvider(manager, config)
        >>> credential_id = await provider.complete_flow_with_workspace(code, state)
    """

    NOTION_API_BASE = "https://api.notion.com/v1"
    NOTION_VERSION = "2022-06-28"

    def __init__(self, manager: OAuthManager, config: OAuthConfig) -> None:
        """Initialize Notion OAuth provider.

        Args:
            manager: OAuth manager instance
            config: Notion OAuth configuration
        """
        self._manager = manager
        self._config = config

    async def complete_flow_with_workspace(self, code: str, state: str) -> str:
        """Complete OAuth flow and discover workspace name.

        Exchanges code for tokens, fetches workspace info from Notion API,
        and stores credential with workspace name.

        Args:
            code: Authorization code from Notion
            state: State token for validation

        Returns:
            Credential ID

        Raises:
            OAuthTokenError: If token exchange or workspace discovery fails
        """
        # First validate state and get tokens
        _ = await self._manager._validate_state(state)
        tokens = await self._manager._exchange_code(self._config, code)

        # Discover workspace name
        workspace_name = await self._discover_workspace(tokens.access_token)

        # Now complete the full flow with workspace name
        credential_id = await self._manager.complete_flow(
            code=code,
            state=state,
            workspace_name=workspace_name,
        )

        return credential_id

    async def _discover_workspace(self, access_token: str) -> Optional[str]:
        """Discover Notion workspace name from API.

        Calls Notion's /users/me endpoint to get bot info and workspace name.

        Args:
            access_token: Notion access token

        Returns:
            Workspace name if available, None otherwise

        Raises:
            OAuthTokenError: If API call fails
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.NOTION_API_BASE}/users/me",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Notion-Version": self.NOTION_VERSION,
                    },
                )
                response.raise_for_status()
                data = response.json()

                # Extract workspace name from bot info
                bot_info = data.get("bot", {})
                workspace_name = bot_info.get("workspace_name")

                return workspace_name

            except httpx.HTTPError:
                # Don't fail the whole flow if workspace discovery fails
                # Just log and return None
                return None

    async def get_databases(self, credential_id: str, user_id: str, tenant_id: str) -> list[dict]:
        """List accessible Notion databases.

        Args:
            credential_id: OAuth credential ID
            user_id: User identifier
            tenant_id: Tenant identifier

        Returns:
            List of database objects from Notion API

        Raises:
            OAuthPermissionError: If credential access denied
            OAuthTokenError: If API call fails
        """
        access_token = await self._manager.get_access_token(credential_id, user_id, tenant_id)

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.NOTION_API_BASE}/search",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Notion-Version": self.NOTION_VERSION,
                        "Content-Type": "application/json",
                    },
                    json={
                        "filter": {"property": "object", "value": "database"},
                        "sort": {"direction": "descending", "timestamp": "last_edited_time"},
                    },
                )
                response.raise_for_status()
                data = response.json()

                return data.get("results", [])

            except httpx.HTTPError as e:
                raise OAuthTokenError(f"Failed to fetch Notion databases: {e}") from e

    async def get_pages(self, credential_id: str, user_id: str, tenant_id: str) -> list[dict]:
        """List accessible Notion pages.

        Args:
            credential_id: OAuth credential ID
            user_id: User identifier
            tenant_id: Tenant identifier

        Returns:
            List of page objects from Notion API

        Raises:
            OAuthPermissionError: If credential access denied
            OAuthTokenError: If API call fails
        """
        access_token = await self._manager.get_access_token(credential_id, user_id, tenant_id)

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.NOTION_API_BASE}/search",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Notion-Version": self.NOTION_VERSION,
                        "Content-Type": "application/json",
                    },
                    json={
                        "filter": {"property": "object", "value": "page"},
                        "sort": {"direction": "descending", "timestamp": "last_edited_time"},
                    },
                )
                response.raise_for_status()
                data = response.json()

                return data.get("results", [])

            except httpx.HTTPError as e:
                raise OAuthTokenError(f"Failed to fetch Notion pages: {e}") from e
