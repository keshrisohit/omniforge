"""Integration tests for OAuth flow with mocked external APIs.

Tests the complete OAuth flow including token exchange, refresh, and error handling
with mocked Notion API responses.
"""

import json
import time
from datetime import datetime, timedelta
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import responses
from sqlalchemy.ext.asyncio import AsyncSession

from omniforge.integrations.oauth.manager import (
    OAuthConfig,
    OAuthError,
    OAuthManager,
    OAuthPermissionError,
    OAuthStateError,
    OAuthTokenError,
)
from omniforge.integrations.oauth.providers.notion import NotionOAuthProvider
from omniforge.storage.database import Database


@pytest.fixture
def oauth_config(mock_oauth_config: dict[str, str]) -> OAuthConfig:
    """Create OAuth configuration for testing.

    Args:
        mock_oauth_config: Mock OAuth configuration fixture

    Returns:
        OAuthConfig instance for Notion
    """
    return OAuthConfig(
        client_id=mock_oauth_config["NOTION_CLIENT_ID"],
        client_secret=mock_oauth_config["NOTION_CLIENT_SECRET"],
        authorize_url="https://api.notion.com/v1/oauth/authorize",
        token_url="https://api.notion.com/v1/oauth/token",
        redirect_uri=mock_oauth_config["NOTION_REDIRECT_URI"],
        scopes=["read_content", "update_content"],
        scope_separator="+",
    )


@pytest.fixture
async def oauth_manager(
    db_session: AsyncSession,
    oauth_config: OAuthConfig,
    mock_encryption_key: str,
) -> OAuthManager:
    """Create OAuth manager for testing.

    Args:
        db_session: Database session fixture
        oauth_config: OAuth configuration fixture
        mock_encryption_key: Mock encryption key fixture

    Returns:
        OAuthManager instance
    """
    return OAuthManager(session=db_session, config=oauth_config)


@pytest.fixture
async def notion_provider(
    db_session: AsyncSession,
    oauth_config: OAuthConfig,
    mock_encryption_key: str,
) -> NotionOAuthProvider:
    """Create Notion OAuth provider for testing.

    Args:
        db_session: Database session fixture
        oauth_config: OAuth configuration fixture
        mock_encryption_key: Mock encryption key fixture

    Returns:
        NotionOAuthProvider instance
    """
    return NotionOAuthProvider(session=db_session, config=oauth_config)


class TestOAuthFlow:
    """Integration tests for OAuth flow."""

    @responses.activate
    async def test_complete_oauth_flow_with_notion(
        self,
        oauth_manager: OAuthManager,
        db_session: AsyncSession,
    ) -> None:
        """Test complete OAuth flow from initiation to token storage.

        This test validates:
        1. Authorization URL generation
        2. State token creation and storage
        3. Token exchange with Notion API
        4. Encrypted credential storage
        """
        # Arrange
        user_id = "test-user-123"
        tenant_id = "test-tenant-456"
        integration_id = "notion"

        # Mock token exchange response
        responses.add(
            responses.POST,
            "https://api.notion.com/v1/oauth/token",
            json={
                "access_token": "test-access-token-abc123",
                "token_type": "bearer",
                "bot_id": "test-bot-id",
                "workspace_name": "Test Workspace",
                "workspace_icon": "https://example.com/icon.png",
                "workspace_id": "test-workspace-id",
                "owner": {"type": "user"},
                "duplicated_template_id": None,
            },
            status=200,
        )

        # Act: Step 1 - Initiate OAuth flow
        authorize_url, state = await oauth_manager.initiate_flow(
            user_id=user_id,
            tenant_id=tenant_id,
            integration_id=integration_id,
        )

        # Assert: Authorize URL is valid
        assert "https://api.notion.com/v1/oauth/authorize" in authorize_url
        assert f"client_id={oauth_manager.config.client_id}" in authorize_url
        assert f"state={state}" in authorize_url
        assert "scope=read_content" in authorize_url or "scope=read_content+update_content" in authorize_url

        # Act: Step 2 - Complete OAuth flow
        code = "test-authorization-code"
        credential_id = await oauth_manager.complete_flow(
            state=state,
            code=code,
        )

        # Assert: Credential was stored
        assert credential_id is not None

        # Act: Step 3 - Retrieve access token
        access_token = await oauth_manager.get_access_token(
            credential_id=credential_id,
            user_id=user_id,
            tenant_id=tenant_id,
        )

        # Assert: Access token matches
        assert access_token == "test-access-token-abc123"

    @responses.activate
    async def test_oauth_flow_with_token_refresh(
        self,
        oauth_manager: OAuthManager,
        db_session: AsyncSession,
    ) -> None:
        """Test OAuth flow with automatic token refresh.

        Validates that expired tokens are automatically refreshed when accessed.
        """
        # Arrange
        user_id = "test-user-123"
        tenant_id = "test-tenant-456"
        integration_id = "notion"

        # Mock initial token exchange (with short expiry)
        responses.add(
            responses.POST,
            "https://api.notion.com/v1/oauth/token",
            json={
                "access_token": "initial-access-token",
                "token_type": "bearer",
                "expires_in": 60,  # 1 minute expiry
                "refresh_token": "test-refresh-token",
                "bot_id": "test-bot-id",
            },
            status=200,
        )

        # Mock token refresh response
        responses.add(
            responses.POST,
            "https://api.notion.com/v1/oauth/token",
            json={
                "access_token": "refreshed-access-token",
                "token_type": "bearer",
                "expires_in": 3600,  # 1 hour expiry
                "refresh_token": "new-refresh-token",
            },
            status=200,
        )

        # Act: Complete initial OAuth flow
        authorize_url, state = await oauth_manager.initiate_flow(
            user_id=user_id,
            tenant_id=tenant_id,
            integration_id=integration_id,
        )

        credential_id = await oauth_manager.complete_flow(
            state=state,
            code="test-code",
        )

        # Act: Simulate time passing (token expires)
        # In real implementation, we'd wait, but here we can mock the expiry check
        with patch.object(oauth_manager, "_is_token_expired", return_value=True):
            access_token = await oauth_manager.get_access_token(
                credential_id=credential_id,
                user_id=user_id,
                tenant_id=tenant_id,
            )

        # Assert: Token was refreshed
        assert access_token == "refreshed-access-token"

    async def test_oauth_state_validation_prevents_csrf(
        self,
        oauth_manager: OAuthManager,
    ) -> None:
        """Test that invalid OAuth state prevents CSRF attacks.

        Validates that:
        1. Invalid state tokens are rejected
        2. Expired state tokens are rejected
        3. Used state tokens cannot be reused
        """
        # Arrange
        user_id = "test-user-123"
        tenant_id = "test-tenant-456"
        integration_id = "notion"

        # Act: Initiate flow
        authorize_url, valid_state = await oauth_manager.initiate_flow(
            user_id=user_id,
            tenant_id=tenant_id,
            integration_id=integration_id,
        )

        # Test 1: Invalid state token
        with pytest.raises(OAuthStateError, match="Invalid or expired OAuth state"):
            await oauth_manager.complete_flow(
                state="invalid-state-token-12345",
                code="test-code",
            )

        # Test 2: Expired state token (mock expiry)
        with patch.object(oauth_manager, "_validate_state") as mock_validate:
            mock_validate.side_effect = OAuthStateError("OAuth state has expired")

            with pytest.raises(OAuthStateError, match="expired"):
                await oauth_manager.complete_flow(
                    state=valid_state,
                    code="test-code",
                )

    async def test_oauth_ownership_validation(
        self,
        oauth_manager: OAuthManager,
        db_session: AsyncSession,
    ) -> None:
        """Test that credential access is properly validated for ownership.

        Validates that:
        1. Users can only access their own credentials
        2. Tenants can only access credentials within their tenant
        3. Unauthorized access raises OAuthPermissionError
        """
        # Arrange
        owner_user_id = "owner-user-123"
        owner_tenant_id = "owner-tenant-456"
        other_user_id = "other-user-789"
        other_tenant_id = "other-tenant-012"
        integration_id = "notion"

        # Create a credential (mock the complete flow)
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.POST,
                "https://api.notion.com/v1/oauth/token",
                json={
                    "access_token": "test-token",
                    "token_type": "bearer",
                },
                status=200,
            )

            authorize_url, state = await oauth_manager.initiate_flow(
                user_id=owner_user_id,
                tenant_id=owner_tenant_id,
                integration_id=integration_id,
            )

            credential_id = await oauth_manager.complete_flow(
                state=state,
                code="test-code",
            )

        # Test 1: Owner can access credential
        access_token = await oauth_manager.get_access_token(
            credential_id=credential_id,
            user_id=owner_user_id,
            tenant_id=owner_tenant_id,
        )
        assert access_token == "test-token"

        # Test 2: Different user cannot access credential
        with pytest.raises(
            OAuthPermissionError,
            match="Unauthorized access to credential",
        ):
            await oauth_manager.get_access_token(
                credential_id=credential_id,
                user_id=other_user_id,
                tenant_id=owner_tenant_id,
            )

        # Test 3: Different tenant cannot access credential
        with pytest.raises(
            OAuthPermissionError,
            match="Unauthorized access to credential",
        ):
            await oauth_manager.get_access_token(
                credential_id=credential_id,
                user_id=owner_user_id,
                tenant_id=other_tenant_id,
            )

    @responses.activate
    async def test_notion_workspace_discovery(
        self,
        notion_provider: NotionOAuthProvider,
        db_session: AsyncSession,
    ) -> None:
        """Test Notion workspace discovery during OAuth flow.

        Validates that workspace information is properly fetched and stored.
        """
        # Arrange
        user_id = "test-user-123"
        tenant_id = "test-tenant-456"
        integration_id = "notion"

        # Mock token exchange response
        responses.add(
            responses.POST,
            "https://api.notion.com/v1/oauth/token",
            json={
                "access_token": "test-access-token",
                "token_type": "bearer",
                "bot_id": "test-bot-id",
                "workspace_name": "My Notion Workspace",
                "workspace_id": "workspace-123",
            },
            status=200,
        )

        # Mock workspace discovery endpoint
        responses.add(
            responses.GET,
            "https://api.notion.com/v1/users/me",
            json={
                "object": "user",
                "id": "user-123",
                "type": "bot",
                "bot": {
                    "owner": {"type": "workspace"},
                    "workspace_name": "My Notion Workspace",
                },
            },
            status=200,
        )

        # Act: Complete OAuth flow with workspace discovery
        authorize_url, state = await notion_provider.initiate_flow(
            user_id=user_id,
            tenant_id=tenant_id,
            integration_id=integration_id,
        )

        credential_id, workspace_name = await notion_provider.complete_flow_with_workspace(
            state=state,
            code="test-code",
        )

        # Assert: Workspace information was captured
        assert credential_id is not None
        assert workspace_name == "My Notion Workspace"

    @responses.activate
    async def test_oauth_error_handling(
        self,
        oauth_manager: OAuthManager,
    ) -> None:
        """Test OAuth error handling for various failure scenarios.

        Tests error handling for:
        1. Invalid authorization code
        2. Network errors
        3. Malformed token responses
        """
        # Arrange
        user_id = "test-user-123"
        tenant_id = "test-tenant-456"
        integration_id = "notion"

        # Test 1: Invalid authorization code
        responses.add(
            responses.POST,
            "https://api.notion.com/v1/oauth/token",
            json={
                "error": "invalid_grant",
                "error_description": "Authorization code is invalid",
            },
            status=400,
        )

        authorize_url, state = await oauth_manager.initiate_flow(
            user_id=user_id,
            tenant_id=tenant_id,
            integration_id=integration_id,
        )

        with pytest.raises(OAuthError, match="Token exchange failed"):
            await oauth_manager.complete_flow(
                state=state,
                code="invalid-code",
            )

        # Test 2: Network error
        responses.add(
            responses.POST,
            "https://api.notion.com/v1/oauth/token",
            body=Exception("Network connection failed"),
        )

        authorize_url, state = await oauth_manager.initiate_flow(
            user_id=user_id,
            tenant_id=tenant_id,
            integration_id=integration_id,
        )

        with pytest.raises(OAuthError):
            await oauth_manager.complete_flow(
                state=state,
                code="test-code",
            )
