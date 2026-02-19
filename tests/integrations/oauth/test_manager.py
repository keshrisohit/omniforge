"""Tests for OAuth manager."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import select

from omniforge.integrations.oauth.manager import (
    OAuthConfig,
    OAuthManager,
    OAuthPermissionError,
    OAuthStateError,
    OAuthTokenError,
)

# Import directly to avoid circular import
from omniforge.storage.database import Database, DatabaseConfig
from omniforge.storage.models import OAuthCredentialModel, OAuthStateModel


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
def oauth_config() -> OAuthConfig:
    """Create test OAuth configuration."""
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
async def oauth_manager(
    db: Database,
    encryption_key: bytes,
    oauth_config: OAuthConfig,
) -> OAuthManager:
    """Create OAuth manager with test configuration."""
    async with db.session() as session:
        manager = OAuthManager(
            configs={"notion": oauth_config},
            encryption_key=encryption_key,
            db_session=session,
        )
        yield manager


class TestOAuthManager:
    """Tests for OAuthManager class."""

    async def test_initiate_flow_returns_valid_url_and_state(
        self,
        oauth_manager: OAuthManager,
        db: Database,
    ) -> None:
        """Initiate flow should return authorization URL with state."""
        async with db.session() as session:
            manager = OAuthManager(
                configs=oauth_manager._configs,
                encryption_key=oauth_manager._encryptor._fernet._signing_key
                + oauth_manager._encryptor._fernet._encryption_key,
                db_session=session,
            )

            auth_url, state = await manager.initiate_flow(
                integration_id="notion",
                user_id="user-123",
                tenant_id="tenant-456",
                session_id="session-789",
            )

            assert "https://api.notion.com/v1/oauth/authorize" in auth_url
            assert "client_id=test_client_id" in auth_url
            assert f"state={state}" in auth_url
            assert "redirect_uri=" in auth_url
            assert "response_type=code" in auth_url
            assert "scope=" in auth_url
            assert len(state) > 0

    async def test_initiate_flow_stores_state_in_database(
        self,
        oauth_manager: OAuthManager,
        db: Database,
    ) -> None:
        """Initiate flow should store state for validation."""
        async with db.session() as session:
            manager = OAuthManager(
                configs=oauth_manager._configs,
                encryption_key=oauth_manager._encryptor._fernet._signing_key
                + oauth_manager._encryptor._fernet._encryption_key,
                db_session=session,
            )

            auth_url, state = await manager.initiate_flow(
                integration_id="notion",
                user_id="user-123",
                tenant_id="tenant-456",
                session_id="session-789",
            )

            # Verify state is stored
            result = await session.execute(
                select(OAuthStateModel).where(OAuthStateModel.state == state)
            )
            state_model = result.scalar_one()

            assert state_model.user_id == "user-123"
            assert state_model.tenant_id == "tenant-456"
            assert state_model.integration_id == "notion"
            assert state_model.session_id == "session-789"
            assert state_model.expires_at > datetime.utcnow()

    async def test_initiate_flow_with_invalid_integration_raises_error(
        self,
        oauth_manager: OAuthManager,
        db: Database,
    ) -> None:
        """Initiate flow with invalid integration should raise KeyError."""
        async with db.session() as session:
            manager = OAuthManager(
                configs=oauth_manager._configs,
                encryption_key=oauth_manager._encryptor._fernet._signing_key
                + oauth_manager._encryptor._fernet._encryption_key,
                db_session=session,
            )

            with pytest.raises(KeyError):
                await manager.initiate_flow(
                    integration_id="invalid",
                    user_id="user-123",
                    tenant_id="tenant-456",
                    session_id="session-789",
                )

    @patch("omniforge.integrations.oauth.manager.httpx.AsyncClient")
    async def test_complete_flow_exchanges_code_and_stores_credential(
        self,
        mock_client_class: MagicMock,
        oauth_manager: OAuthManager,
        db: Database,
    ) -> None:
        """Complete flow should exchange code and store encrypted credential."""
        # Setup mock HTTP response
        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "access_token": "notion_access_token_123",
            "refresh_token": "notion_refresh_token_456",
            "token_type": "Bearer",
            "expires_in": 3600,
        }
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        async with db.session() as session:
            manager = OAuthManager(
                configs=oauth_manager._configs,
                encryption_key=oauth_manager._encryptor._fernet._signing_key
                + oauth_manager._encryptor._fernet._encryption_key,
                db_session=session,
            )

            # Create state first
            auth_url, state = await manager.initiate_flow(
                integration_id="notion",
                user_id="user-123",
                tenant_id="tenant-456",
                session_id="session-789",
            )

            # Complete flow
            credential_id = await manager.complete_flow(
                code="auth_code_abc",
                state=state,
                workspace_name="Test Workspace",
            )

            # Verify credential was stored
            result = await session.execute(
                select(OAuthCredentialModel).where(OAuthCredentialModel.id == credential_id)
            )
            credential = result.scalar_one()

            assert credential.user_id == "user-123"
            assert credential.tenant_id == "tenant-456"
            assert credential.integration_id == "notion"
            assert credential.workspace_name == "Test Workspace"
            assert credential.token_type == "Bearer"
            assert credential.expires_at is not None

            # Verify tokens are encrypted (not plain text)
            assert credential.access_token_encrypted != b"notion_access_token_123"
            assert credential.refresh_token_encrypted != b"notion_refresh_token_456"

            # Verify state was cleaned up
            result = await session.execute(
                select(OAuthStateModel).where(OAuthStateModel.state == state)
            )
            assert result.scalar_one_or_none() is None

    async def test_complete_flow_with_invalid_state_raises_error(
        self,
        oauth_manager: OAuthManager,
        db: Database,
    ) -> None:
        """Complete flow with invalid state should raise OAuthStateError."""
        async with db.session() as session:
            manager = OAuthManager(
                configs=oauth_manager._configs,
                encryption_key=oauth_manager._encryptor._fernet._signing_key
                + oauth_manager._encryptor._fernet._encryption_key,
                db_session=session,
            )

            with pytest.raises(OAuthStateError, match="Invalid or expired OAuth state"):
                await manager.complete_flow(
                    code="auth_code_abc",
                    state="invalid_state",
                )

    async def test_complete_flow_with_expired_state_raises_error(
        self,
        oauth_manager: OAuthManager,
        db: Database,
    ) -> None:
        """Complete flow with expired state should raise OAuthStateError."""
        async with db.session() as session:
            manager = OAuthManager(
                configs=oauth_manager._configs,
                encryption_key=oauth_manager._encryptor._fernet._signing_key
                + oauth_manager._encryptor._fernet._encryption_key,
                db_session=session,
            )

            # Create expired state manually
            expired_state = OAuthStateModel(
                state="expired_state",
                user_id="user-123",
                tenant_id="tenant-456",
                integration_id="notion",
                session_id="session-789",
                created_at=datetime.utcnow() - timedelta(hours=1),
                expires_at=datetime.utcnow() - timedelta(minutes=1),
            )
            session.add(expired_state)
            await session.commit()

            with pytest.raises(OAuthStateError, match="OAuth state expired"):
                await manager.complete_flow(
                    code="auth_code_abc",
                    state="expired_state",
                )

    @patch("omniforge.integrations.oauth.manager.httpx.AsyncClient")
    async def test_get_access_token_returns_decrypted_token(
        self,
        mock_client_class: MagicMock,
        oauth_manager: OAuthManager,
        db: Database,
    ) -> None:
        """Get access token should return decrypted token."""
        # Setup mock HTTP response for token exchange
        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "access_token": "notion_access_token_123",
            "token_type": "Bearer",
            "expires_in": 3600,
        }
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        async with db.session() as session:
            manager = OAuthManager(
                configs=oauth_manager._configs,
                encryption_key=oauth_manager._encryptor._fernet._signing_key
                + oauth_manager._encryptor._fernet._encryption_key,
                db_session=session,
            )

            # Create credential
            auth_url, state = await manager.initiate_flow(
                integration_id="notion",
                user_id="user-123",
                tenant_id="tenant-456",
                session_id="session-789",
            )
            credential_id = await manager.complete_flow(code="auth_code_abc", state=state)

            # Get access token
            access_token = await manager.get_access_token(
                credential_id=credential_id,
                user_id="user-123",
                tenant_id="tenant-456",
            )

            assert access_token == "notion_access_token_123"

    async def test_get_access_token_with_wrong_user_raises_error(
        self,
        oauth_manager: OAuthManager,
        db: Database,
    ) -> None:
        """Get access token with wrong user should raise OAuthPermissionError."""
        async with db.session() as session:
            manager = OAuthManager(
                configs=oauth_manager._configs,
                encryption_key=oauth_manager._encryptor._fernet._signing_key
                + oauth_manager._encryptor._fernet._encryption_key,
                db_session=session,
            )

            # Create credential for user-123
            encryptor = oauth_manager._encryptor
            credential = OAuthCredentialModel(
                user_id="user-123",
                tenant_id="tenant-456",
                integration_id="notion",
                access_token_encrypted=encryptor.encrypt("token"),
                token_type="Bearer",
                scopes=[],
                expires_at=datetime.utcnow() + timedelta(hours=1),
            )
            session.add(credential)
            await session.commit()
            await session.refresh(credential)

            # Try to access with wrong user
            with pytest.raises(OAuthPermissionError, match="Credential access denied"):
                await manager.get_access_token(
                    credential_id=credential.id,
                    user_id="user-999",
                    tenant_id="tenant-456",
                )

    async def test_get_access_token_with_wrong_tenant_raises_error(
        self,
        oauth_manager: OAuthManager,
        db: Database,
    ) -> None:
        """Get access token with wrong tenant should raise OAuthPermissionError."""
        async with db.session() as session:
            manager = OAuthManager(
                configs=oauth_manager._configs,
                encryption_key=oauth_manager._encryptor._fernet._signing_key
                + oauth_manager._encryptor._fernet._encryption_key,
                db_session=session,
            )

            # Create credential
            encryptor = oauth_manager._encryptor
            credential = OAuthCredentialModel(
                user_id="user-123",
                tenant_id="tenant-456",
                integration_id="notion",
                access_token_encrypted=encryptor.encrypt("token"),
                token_type="Bearer",
                scopes=[],
                expires_at=datetime.utcnow() + timedelta(hours=1),
            )
            session.add(credential)
            await session.commit()
            await session.refresh(credential)

            # Try to access with wrong tenant
            with pytest.raises(OAuthPermissionError, match="Credential access denied"):
                await manager.get_access_token(
                    credential_id=credential.id,
                    user_id="user-123",
                    tenant_id="tenant-999",
                )

    @patch("omniforge.integrations.oauth.manager.httpx.AsyncClient")
    async def test_get_access_token_refreshes_expired_token(
        self,
        mock_client_class: MagicMock,
        oauth_manager: OAuthManager,
        db: Database,
    ) -> None:
        """Get access token should refresh if expired."""
        # Setup mock for refresh
        mock_refresh_response = AsyncMock()
        mock_refresh_response.raise_for_status = MagicMock()
        mock_refresh_response.json.return_value = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 3600,
        }
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post.return_value = mock_refresh_response
        mock_client_class.return_value = mock_client

        async with db.session() as session:
            manager = OAuthManager(
                configs=oauth_manager._configs,
                encryption_key=oauth_manager._encryptor._fernet._signing_key
                + oauth_manager._encryptor._fernet._encryption_key,
                db_session=session,
            )

            # Create expired credential
            encryptor = oauth_manager._encryptor
            credential = OAuthCredentialModel(
                user_id="user-123",
                tenant_id="tenant-456",
                integration_id="notion",
                access_token_encrypted=encryptor.encrypt("old_token"),
                refresh_token_encrypted=encryptor.encrypt("refresh_token"),
                token_type="Bearer",
                scopes=[],
                expires_at=datetime.utcnow() - timedelta(minutes=10),
            )
            session.add(credential)
            await session.commit()
            await session.refresh(credential)

            # Get access token (should trigger refresh)
            access_token = await manager.get_access_token(
                credential_id=credential.id,
                user_id="user-123",
                tenant_id="tenant-456",
            )

            assert access_token == "new_access_token"

            # Verify credential was updated
            result = await session.execute(
                select(OAuthCredentialModel).where(OAuthCredentialModel.id == credential.id)
            )
            updated_credential = result.scalar_one()
            assert updated_credential.expires_at > datetime.utcnow()

    async def test_cleanup_expired_states_removes_old_states(
        self,
        oauth_manager: OAuthManager,
        db: Database,
    ) -> None:
        """Cleanup should remove expired states."""
        async with db.session() as session:
            manager = OAuthManager(
                configs=oauth_manager._configs,
                encryption_key=oauth_manager._encryptor._fernet._signing_key
                + oauth_manager._encryptor._fernet._encryption_key,
                db_session=session,
            )

            # Create expired and valid states
            expired_state = OAuthStateModel(
                state="expired",
                user_id="user-123",
                tenant_id="tenant-456",
                integration_id="notion",
                session_id="session-1",
                created_at=datetime.utcnow() - timedelta(hours=1),
                expires_at=datetime.utcnow() - timedelta(minutes=1),
            )
            valid_state = OAuthStateModel(
                state="valid",
                user_id="user-123",
                tenant_id="tenant-456",
                integration_id="notion",
                session_id="session-2",
                created_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(minutes=10),
            )
            session.add(expired_state)
            session.add(valid_state)
            await session.commit()

            # Cleanup
            removed_count = await manager.cleanup_expired_states()

            assert removed_count == 1

            # Verify only valid state remains
            result = await session.execute(select(OAuthStateModel))
            states = result.scalars().all()
            assert len(states) == 1
            assert states[0].state == "valid"

    async def test_state_generation_is_unique(
        self,
        oauth_manager: OAuthManager,
    ) -> None:
        """State generation should produce unique values."""
        state1 = oauth_manager._generate_state("user-1", "tenant-1", "notion", "session-1")
        state2 = oauth_manager._generate_state("user-1", "tenant-1", "notion", "session-1")
        state3 = oauth_manager._generate_state("user-2", "tenant-1", "notion", "session-1")

        # Different random bytes should produce different states
        assert state1 != state2
        # Different user should produce different states
        assert state1 != state3
        assert state2 != state3

    @patch("omniforge.integrations.oauth.manager.httpx.AsyncClient")
    async def test_token_exchange_http_error_raises_oauth_token_error(
        self,
        mock_client_class: MagicMock,
        oauth_manager: OAuthManager,
        db: Database,
    ) -> None:
        """HTTP error during token exchange should raise OAuthTokenError."""
        # Setup mock to raise HTTP error
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post.side_effect = Exception("Network error")
        mock_client_class.return_value = mock_client

        async with db.session() as session:
            manager = OAuthManager(
                configs=oauth_manager._configs,
                encryption_key=oauth_manager._encryptor._fernet._signing_key
                + oauth_manager._encryptor._fernet._encryption_key,
                db_session=session,
            )

            # Create state
            auth_url, state = await manager.initiate_flow(
                integration_id="notion",
                user_id="user-123",
                tenant_id="tenant-456",
                session_id="session-789",
            )

            # Try to complete flow
            with pytest.raises(OAuthTokenError):
                await manager.complete_flow(code="auth_code_abc", state=state)

    @patch("omniforge.integrations.oauth.manager.httpx.AsyncClient")
    async def test_token_refresh_without_refresh_token_raises_error(
        self,
        mock_client_class: MagicMock,
        oauth_manager: OAuthManager,
        db: Database,
    ) -> None:
        """Attempting refresh without refresh token should raise error."""
        async with db.session() as session:
            manager = OAuthManager(
                configs=oauth_manager._configs,
                encryption_key=oauth_manager._encryptor._fernet._signing_key
                + oauth_manager._encryptor._fernet._encryption_key,
                db_session=session,
            )

            # Create expired credential without refresh token
            encryptor = oauth_manager._encryptor
            credential = OAuthCredentialModel(
                user_id="user-123",
                tenant_id="tenant-456",
                integration_id="notion",
                access_token_encrypted=encryptor.encrypt("old_token"),
                refresh_token_encrypted=None,
                token_type="Bearer",
                scopes=[],
                expires_at=datetime.utcnow() - timedelta(minutes=10),
            )
            session.add(credential)
            await session.commit()
            await session.refresh(credential)

            # Try to get access token (should fail to refresh)
            with pytest.raises(OAuthTokenError, match="No refresh token available"):
                await manager.get_access_token(
                    credential_id=credential.id,
                    user_id="user-123",
                    tenant_id="tenant-456",
                )
