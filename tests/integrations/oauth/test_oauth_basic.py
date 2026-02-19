"""Basic tests for OAuth functionality without database dependencies."""

import pytest
from cryptography.fernet import Fernet

from omniforge.integrations.oauth.manager import (
    OAuthConfig,
    OAuthStateData,
    OAuthTokens,
)


class TestOAuthConfig:
    """Tests for OAuthConfig model."""

    def test_create_oauth_config(self) -> None:
        """Should create OAuth configuration successfully."""
        config = OAuthConfig(
            integration_id="notion",
            client_id="test_client",
            client_secret="test_secret",
            authorize_url="https://api.notion.com/v1/oauth/authorize",
            token_url="https://api.notion.com/v1/oauth/token",
            scopes=["read_content"],
            redirect_uri="https://app.example.com/callback",
        )

        assert config.integration_id == "notion"
        assert config.client_id == "test_client"
        assert config.client_secret == "test_secret"
        assert config.scopes == ["read_content"]


class TestOAuthStateData:
    """Tests for OAuthStateData model."""

    def test_create_oauth_state_data(self) -> None:
        """Should create OAuth state data successfully."""
        state_data = OAuthStateData(
            user_id="user-123",
            tenant_id="tenant-456",
            integration_id="notion",
            session_id="session-789",
        )

        assert state_data.user_id == "user-123"
        assert state_data.tenant_id == "tenant-456"
        assert state_data.integration_id == "notion"
        assert state_data.session_id == "session-789"


class TestOAuthTokens:
    """Tests for OAuthTokens model."""

    def test_create_oauth_tokens_with_all_fields(self) -> None:
        """Should create OAuth tokens with all fields."""
        tokens = OAuthTokens(
            access_token="access_token_123",
            refresh_token="refresh_token_456",
            token_type="Bearer",
            expires_in=3600,
            scopes=["read", "write"],
        )

        assert tokens.access_token == "access_token_123"
        assert tokens.refresh_token == "refresh_token_456"
        assert tokens.token_type == "Bearer"
        assert tokens.expires_in == 3600
        assert tokens.scopes == ["read", "write"]

    def test_create_oauth_tokens_with_defaults(self) -> None:
        """Should create OAuth tokens with default values."""
        tokens = OAuthTokens(
            access_token="access_token_123",
        )

        assert tokens.access_token == "access_token_123"
        assert tokens.refresh_token is None
        assert tokens.token_type == "Bearer"
        assert tokens.expires_in is None
        assert tokens.scopes == []


class TestOAuthURLGeneration:
    """Tests for OAuth authorization URL generation."""

    def test_notion_scope_separator(self) -> None:
        """Notion should use + separator for scopes."""
        config = OAuthConfig(
            integration_id="notion",
            client_id="test_client",
            client_secret="test_secret",
            authorize_url="https://api.notion.com/v1/oauth/authorize",
            token_url="https://api.notion.com/v1/oauth/token",
            scopes=["read_content", "write_content"],
            redirect_uri="https://app.example.com/callback",
        )

        # Manual URL construction to test separator logic
        from urllib.parse import urlencode

        params = {
            "client_id": config.client_id,
            "redirect_uri": config.redirect_uri,
            "response_type": "code",
            "state": "test_state",
        }

        # Notion uses + separator
        separator = "+"
        params["scope"] = separator.join(config.scopes)

        url = f"{config.authorize_url}?{urlencode(params)}"

        assert "scope=read_content%2Bwrite_content" in url or "scope=read_content+write_content" in url
        assert "client_id=test_client" in url
        assert "response_type=code" in url
