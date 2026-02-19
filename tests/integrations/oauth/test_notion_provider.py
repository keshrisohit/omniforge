"""Tests for Notion OAuth provider."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cryptography.fernet import Fernet

from omniforge.integrations.oauth.manager import OAuthConfig, OAuthManager, OAuthTokenError
from omniforge.integrations.oauth.providers.notion import NotionOAuthProvider
from omniforge.storage.database import Database, DatabaseConfig
from omniforge.storage.models import OAuthCredentialModel


@pytest.fixture
async def db() -> Database:
    """Create in-memory test database."""
    config = DatabaseConfig(url="sqlite+aiosqlite:///:memory:")
    database = Database(config)
    await database.create_tables()
    return database


@pytest.fixture
def encryption_key() -> bytes:
    """Generate test encryption key."""
    return Fernet.generate_key()


@pytest.fixture
def notion_config() -> OAuthConfig:
    """Create Notion OAuth configuration."""
    return OAuthConfig(
        integration_id="notion",
        client_id="test_client_id",
        client_secret="test_client_secret",
        authorize_url="https://api.notion.com/v1/oauth/authorize",
        token_url="https://api.notion.com/v1/oauth/token",
        scopes=["read_content"],
        redirect_uri="https://app.example.com/oauth/callback",
    )


@pytest.fixture
async def notion_provider(
    db: Database,
    encryption_key: bytes,
    notion_config: OAuthConfig,
) -> NotionOAuthProvider:
    """Create Notion OAuth provider."""
    async with db.session() as session:
        manager = OAuthManager(
            configs={"notion": notion_config},
            encryption_key=encryption_key,
            db_session=session,
        )
        provider = NotionOAuthProvider(manager, notion_config)
        yield provider


class TestNotionOAuthProvider:
    """Tests for NotionOAuthProvider class."""

    @patch("omniforge.integrations.oauth.manager.httpx.AsyncClient")
    @patch("omniforge.integrations.oauth.providers.notion.httpx.AsyncClient")
    async def test_complete_flow_with_workspace_discovers_workspace_name(
        self,
        mock_notion_client_class: MagicMock,
        mock_manager_client_class: MagicMock,
        db: Database,
        encryption_key: bytes,
        notion_config: OAuthConfig,
    ) -> None:
        """Complete flow should discover workspace name from Notion API."""
        # Setup mock for token exchange
        mock_token_response = AsyncMock()
        mock_token_response.raise_for_status = MagicMock()
        mock_token_response.json.return_value = {
            "access_token": "notion_access_token_123",
            "token_type": "Bearer",
            "expires_in": 3600,
        }
        mock_manager_client = AsyncMock()
        mock_manager_client.__aenter__.return_value = mock_manager_client
        mock_manager_client.__aexit__.return_value = None
        mock_manager_client.post.return_value = mock_token_response
        mock_manager_client_class.return_value = mock_manager_client

        # Setup mock for workspace discovery
        mock_workspace_response = AsyncMock()
        mock_workspace_response.raise_for_status = MagicMock()
        mock_workspace_response.json.return_value = {
            "bot": {
                "workspace_name": "Acme Corp Workspace",
                "owner": {"type": "workspace"},
            }
        }
        mock_notion_client = AsyncMock()
        mock_notion_client.__aenter__.return_value = mock_notion_client
        mock_notion_client.__aexit__.return_value = None
        mock_notion_client.get.return_value = mock_workspace_response
        mock_notion_client_class.return_value = mock_notion_client

        async with db.session() as session:
            manager = OAuthManager(
                configs={"notion": notion_config},
                encryption_key=encryption_key,
                db_session=session,
            )
            provider = NotionOAuthProvider(manager, notion_config)

            # Initiate flow first
            auth_url, state = await manager.initiate_flow(
                integration_id="notion",
                user_id="user-123",
                tenant_id="tenant-456",
                session_id="session-789",
            )

            # Complete flow with workspace discovery
            credential_id = await provider.complete_flow_with_workspace(
                code="auth_code_abc",
                state=state,
            )

            # Verify workspace name was stored
            from sqlalchemy import select

            result = await session.execute(
                select(OAuthCredentialModel).where(OAuthCredentialModel.id == credential_id)
            )
            credential = result.scalar_one()
            assert credential.workspace_name == "Acme Corp Workspace"

            # Verify Notion API was called
            mock_notion_client.get.assert_called_once()
            call_args = mock_notion_client.get.call_args
            assert "users/me" in call_args[0][0]
            assert call_args[1]["headers"]["Authorization"] == "Bearer notion_access_token_123"

    @patch("omniforge.integrations.oauth.manager.httpx.AsyncClient")
    @patch("omniforge.integrations.oauth.providers.notion.httpx.AsyncClient")
    async def test_complete_flow_continues_if_workspace_discovery_fails(
        self,
        mock_notion_client_class: MagicMock,
        mock_manager_client_class: MagicMock,
        db: Database,
        encryption_key: bytes,
        notion_config: OAuthConfig,
    ) -> None:
        """Complete flow should continue even if workspace discovery fails."""
        # Setup mock for token exchange
        mock_token_response = AsyncMock()
        mock_token_response.raise_for_status = MagicMock()
        mock_token_response.json.return_value = {
            "access_token": "notion_access_token_123",
            "token_type": "Bearer",
            "expires_in": 3600,
        }
        mock_manager_client = AsyncMock()
        mock_manager_client.__aenter__.return_value = mock_manager_client
        mock_manager_client.__aexit__.return_value = None
        mock_manager_client.post.return_value = mock_token_response
        mock_manager_client_class.return_value = mock_manager_client

        # Setup mock for workspace discovery failure
        mock_notion_client = AsyncMock()
        mock_notion_client.__aenter__.return_value = mock_notion_client
        mock_notion_client.__aexit__.return_value = None
        mock_notion_client.get.side_effect = Exception("Network error")
        mock_notion_client_class.return_value = mock_notion_client

        async with db.session() as session:
            manager = OAuthManager(
                configs={"notion": notion_config},
                encryption_key=encryption_key,
                db_session=session,
            )
            provider = NotionOAuthProvider(manager, notion_config)

            # Initiate flow first
            auth_url, state = await manager.initiate_flow(
                integration_id="notion",
                user_id="user-123",
                tenant_id="tenant-456",
                session_id="session-789",
            )

            # Complete flow (should not raise error even if discovery fails)
            credential_id = await provider.complete_flow_with_workspace(
                code="auth_code_abc",
                state=state,
            )

            # Verify credential was still created without workspace name
            from sqlalchemy import select

            result = await session.execute(
                select(OAuthCredentialModel).where(OAuthCredentialModel.id == credential_id)
            )
            credential = result.scalar_one()
            assert credential.workspace_name is None

    @patch("omniforge.integrations.oauth.providers.notion.httpx.AsyncClient")
    async def test_get_databases_returns_notion_databases(
        self,
        mock_client_class: MagicMock,
        db: Database,
        encryption_key: bytes,
        notion_config: OAuthConfig,
    ) -> None:
        """Get databases should return list of Notion databases."""
        # Setup mock response
        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {"id": "db-1", "object": "database", "title": [{"plain_text": "Projects"}]},
                {"id": "db-2", "object": "database", "title": [{"plain_text": "Tasks"}]},
            ]
        }
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        async with db.session() as session:
            manager = OAuthManager(
                configs={"notion": notion_config},
                encryption_key=encryption_key,
                db_session=session,
            )
            provider = NotionOAuthProvider(manager, notion_config)

            # Create credential
            encryptor = manager._encryptor
            credential = OAuthCredentialModel(
                user_id="user-123",
                tenant_id="tenant-456",
                integration_id="notion",
                access_token_encrypted=encryptor.encrypt("test_token"),
                token_type="Bearer",
                scopes=[],
                expires_at=datetime.utcnow() + timedelta(hours=1),
            )
            session.add(credential)
            await session.commit()
            await session.refresh(credential)

            # Get databases
            databases = await provider.get_databases(
                credential_id=credential.id,
                user_id="user-123",
                tenant_id="tenant-456",
            )

            assert len(databases) == 2
            assert databases[0]["id"] == "db-1"
            assert databases[1]["id"] == "db-2"

            # Verify API was called correctly
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert "search" in call_args[0][0]
            assert call_args[1]["headers"]["Authorization"] == "Bearer test_token"
            assert call_args[1]["json"]["filter"]["value"] == "database"

    @patch("omniforge.integrations.oauth.providers.notion.httpx.AsyncClient")
    async def test_get_databases_raises_error_on_api_failure(
        self,
        mock_client_class: MagicMock,
        db: Database,
        encryption_key: bytes,
        notion_config: OAuthConfig,
    ) -> None:
        """Get databases should raise OAuthTokenError on API failure."""
        # Setup mock to raise error
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post.side_effect = Exception("API error")
        mock_client_class.return_value = mock_client

        async with db.session() as session:
            manager = OAuthManager(
                configs={"notion": notion_config},
                encryption_key=encryption_key,
                db_session=session,
            )
            provider = NotionOAuthProvider(manager, notion_config)

            # Create credential
            encryptor = manager._encryptor
            credential = OAuthCredentialModel(
                user_id="user-123",
                tenant_id="tenant-456",
                integration_id="notion",
                access_token_encrypted=encryptor.encrypt("test_token"),
                token_type="Bearer",
                scopes=[],
                expires_at=datetime.utcnow() + timedelta(hours=1),
            )
            session.add(credential)
            await session.commit()
            await session.refresh(credential)

            # Try to get databases
            with pytest.raises(OAuthTokenError, match="Failed to fetch Notion databases"):
                await provider.get_databases(
                    credential_id=credential.id,
                    user_id="user-123",
                    tenant_id="tenant-456",
                )

    @patch("omniforge.integrations.oauth.providers.notion.httpx.AsyncClient")
    async def test_get_pages_returns_notion_pages(
        self,
        mock_client_class: MagicMock,
        db: Database,
        encryption_key: bytes,
        notion_config: OAuthConfig,
    ) -> None:
        """Get pages should return list of Notion pages."""
        # Setup mock response
        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {
                    "id": "page-1",
                    "object": "page",
                    "properties": {"title": {"title": [{"plain_text": "Meeting Notes"}]}},
                },
                {
                    "id": "page-2",
                    "object": "page",
                    "properties": {"title": {"title": [{"plain_text": "Project Plan"}]}},
                },
            ]
        }
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        async with db.session() as session:
            manager = OAuthManager(
                configs={"notion": notion_config},
                encryption_key=encryption_key,
                db_session=session,
            )
            provider = NotionOAuthProvider(manager, notion_config)

            # Create credential
            encryptor = manager._encryptor
            credential = OAuthCredentialModel(
                user_id="user-123",
                tenant_id="tenant-456",
                integration_id="notion",
                access_token_encrypted=encryptor.encrypt("test_token"),
                token_type="Bearer",
                scopes=[],
                expires_at=datetime.utcnow() + timedelta(hours=1),
            )
            session.add(credential)
            await session.commit()
            await session.refresh(credential)

            # Get pages
            pages = await provider.get_pages(
                credential_id=credential.id,
                user_id="user-123",
                tenant_id="tenant-456",
            )

            assert len(pages) == 2
            assert pages[0]["id"] == "page-1"
            assert pages[1]["id"] == "page-2"

            # Verify API was called correctly
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert "search" in call_args[0][0]
            assert call_args[1]["headers"]["Authorization"] == "Bearer test_token"
            assert call_args[1]["json"]["filter"]["value"] == "page"

    @patch("omniforge.integrations.oauth.providers.notion.httpx.AsyncClient")
    async def test_notion_api_version_header_is_set(
        self,
        mock_client_class: MagicMock,
        db: Database,
        encryption_key: bytes,
        notion_config: OAuthConfig,
    ) -> None:
        """Notion API calls should include Notion-Version header."""
        # Setup mock response
        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"results": []}
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        async with db.session() as session:
            manager = OAuthManager(
                configs={"notion": notion_config},
                encryption_key=encryption_key,
                db_session=session,
            )
            provider = NotionOAuthProvider(manager, notion_config)

            # Create credential
            encryptor = manager._encryptor
            credential = OAuthCredentialModel(
                user_id="user-123",
                tenant_id="tenant-456",
                integration_id="notion",
                access_token_encrypted=encryptor.encrypt("test_token"),
                token_type="Bearer",
                scopes=[],
                expires_at=datetime.utcnow() + timedelta(hours=1),
            )
            session.add(credential)
            await session.commit()
            await session.refresh(credential)

            # Make API call
            await provider.get_databases(
                credential_id=credential.id,
                user_id="user-123",
                tenant_id="tenant-456",
            )

            # Verify Notion-Version header
            call_args = mock_client.post.call_args
            assert call_args[1]["headers"]["Notion-Version"] == "2022-06-28"
