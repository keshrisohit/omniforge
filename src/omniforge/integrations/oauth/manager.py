"""OAuth 2.0 flow manager for integrations.

This module manages OAuth authorization flows, token exchange, refresh,
and secure credential storage for integration providers.
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Optional
from urllib.parse import urlencode

import httpx
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from omniforge.integrations.credentials.encryption import CredentialEncryption

if TYPE_CHECKING:
    from omniforge.storage.models import OAuthCredentialModel


class OAuthConfig(BaseModel):
    """OAuth configuration for an integration.

    Attributes:
        integration_id: Unique identifier (e.g., "notion", "slack")
        client_id: OAuth client ID from provider
        client_secret: OAuth client secret from provider
        authorize_url: Provider's authorization endpoint URL
        token_url: Provider's token exchange endpoint URL
        scopes: List of OAuth scopes to request
        redirect_uri: Callback URL for OAuth redirect
    """

    integration_id: str
    client_id: str
    client_secret: str
    authorize_url: str
    token_url: str
    scopes: list[str]
    redirect_uri: str


class OAuthStateData(BaseModel):
    """OAuth state data for callback validation.

    Attributes:
        user_id: User identifier
        tenant_id: Tenant identifier
        integration_id: Integration identifier
        session_id: Session identifier for routing
    """

    user_id: str
    tenant_id: str
    integration_id: str
    session_id: str


class OAuthTokens(BaseModel):
    """OAuth tokens from provider.

    Attributes:
        access_token: OAuth access token
        refresh_token: Optional refresh token
        token_type: Token type (usually "Bearer")
        expires_in: Token lifetime in seconds (optional)
        scopes: Granted scopes
    """

    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_in: Optional[int] = None
    scopes: list[str] = []


class OAuthError(Exception):
    """Base exception for OAuth errors."""

    pass


class OAuthStateError(OAuthError):
    """Raised when OAuth state validation fails."""

    pass


class OAuthTokenError(OAuthError):
    """Raised when token exchange or refresh fails."""

    pass


class OAuthPermissionError(OAuthError):
    """Raised when credential access is denied."""

    pass


class OAuthManager:
    """Manages OAuth flows for integrations.

    MVP uses Fernet encryption for credentials with a single key from
    environment variables. Phase 2+ will migrate to per-tenant keys via AWS KMS.

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
        >>> manager = OAuthManager(
        ...     configs={"notion": config},
        ...     encryption_key=b"...",
        ...     db_session=session
        ... )
        >>> auth_url, state = await manager.initiate_flow(
        ...     integration_id="notion",
        ...     user_id="user-123",
        ...     tenant_id="tenant-456",
        ...     session_id="session-789"
        ... )
    """

    def __init__(
        self,
        configs: dict[str, OAuthConfig],
        encryption_key: bytes,
        db_session: AsyncSession,
    ) -> None:
        """Initialize OAuth manager.

        Args:
            configs: Dictionary of integration configs keyed by integration_id
            encryption_key: Fernet encryption key for credentials
            db_session: Async database session
        """
        self._configs = configs
        self._encryptor = CredentialEncryption(encryption_key)
        self._db = db_session

    async def initiate_flow(
        self,
        integration_id: str,
        user_id: str,
        tenant_id: str,
        session_id: str,
    ) -> tuple[str, str]:
        """Initiate OAuth authorization flow.

        Generates a secure state token, stores it for CSRF protection,
        and returns the authorization URL for redirect.

        Args:
            integration_id: Integration to authorize (e.g., "notion")
            user_id: User initiating the flow
            tenant_id: Tenant identifier
            session_id: Session identifier for callback routing

        Returns:
            Tuple of (authorization_url, state_token)

        Raises:
            KeyError: If integration_id not configured
        """
        config = self._configs[integration_id]
        state = self._generate_state(user_id, tenant_id, integration_id, session_id)

        # Store state for callback validation (expires in 10 minutes)
        await self._store_state(
            state=state,
            user_id=user_id,
            tenant_id=tenant_id,
            integration_id=integration_id,
            session_id=session_id,
            expires_in_seconds=600,
        )

        # Build authorization URL
        params = {
            "client_id": config.client_id,
            "redirect_uri": config.redirect_uri,
            "response_type": "code",
            "state": state,
        }

        # Add scopes if present
        if config.scopes:
            # Use + separator for Notion, space for most others
            separator = "+" if integration_id == "notion" else " "
            params["scope"] = separator.join(config.scopes)

        auth_url = f"{config.authorize_url}?{urlencode(params)}"
        return auth_url, state

    async def complete_flow(
        self,
        code: str,
        state: str,
        workspace_name: Optional[str] = None,
    ) -> str:
        """Complete OAuth flow and store credentials.

        Validates the state token, exchanges the authorization code for tokens,
        encrypts and stores the credentials in the database.

        Args:
            code: Authorization code from provider
            state: State token from authorization redirect
            workspace_name: Optional workspace name from provider

        Returns:
            Credential ID for stored tokens

        Raises:
            OAuthStateError: If state validation fails
            OAuthTokenError: If token exchange fails
        """
        from omniforge.storage.models import OAuthStateModel

        # Validate and retrieve state
        state_data = await self._validate_state(state)
        config = self._configs[state_data.integration_id]

        # Exchange code for tokens
        tokens = await self._exchange_code(config, code)

        # Encrypt and store credential
        credential_id = await self._store_credential(
            user_id=state_data.user_id,
            tenant_id=state_data.tenant_id,
            integration_id=state_data.integration_id,
            tokens=tokens,
            workspace_name=workspace_name,
        )

        # Clean up used state
        await self._db.execute(delete(OAuthStateModel).where(OAuthStateModel.state == state))
        await self._db.commit()

        return credential_id

    async def get_access_token(
        self,
        credential_id: str,
        user_id: str,
        tenant_id: str,
    ) -> str:
        """Get access token, refreshing if expired.

        Retrieves the credential, verifies ownership, checks expiration,
        and refreshes if needed before returning the decrypted token.

        Args:
            credential_id: Credential identifier
            user_id: User requesting access
            tenant_id: Tenant identifier

        Returns:
            Decrypted access token

        Raises:
            OAuthPermissionError: If ownership check fails
            OAuthTokenError: If refresh fails
        """

        credential = await self._get_credential(credential_id)

        # Verify ownership
        if credential.user_id != user_id or credential.tenant_id != tenant_id:
            raise OAuthPermissionError("Credential access denied")

        # Check expiry and refresh if needed
        if self._is_expired(credential):
            credential = await self._refresh_token(credential)

        # Decrypt and return
        return self._encryptor.decrypt(credential.access_token_encrypted)

    async def cleanup_expired_states(self) -> int:
        """Clean up expired OAuth states.

        Returns:
            Number of expired states removed
        """
        from omniforge.storage.models import OAuthStateModel

        result = await self._db.execute(
            delete(OAuthStateModel).where(OAuthStateModel.expires_at < datetime.utcnow())
        )
        await self._db.commit()
        return result.rowcount  # type: ignore

    def _generate_state(
        self,
        user_id: str,
        tenant_id: str,
        integration_id: str,
        session_id: str,
    ) -> str:
        """Generate secure state token for CSRF protection.

        Uses cryptographically secure random bytes combined with user context
        to create a unique, non-guessable state token.

        Args:
            user_id: User identifier
            tenant_id: Tenant identifier
            integration_id: Integration identifier
            session_id: Session identifier

        Returns:
            URL-safe state token
        """
        random_bytes = secrets.token_bytes(32)
        context = f"{user_id}:{tenant_id}:{integration_id}:{session_id}"
        combined = random_bytes + context.encode()
        return hashlib.sha256(combined).hexdigest()

    async def _store_state(
        self,
        state: str,
        user_id: str,
        tenant_id: str,
        integration_id: str,
        session_id: str,
        expires_in_seconds: int,
    ) -> None:
        """Store OAuth state for callback validation.

        Args:
            state: State token
            user_id: User identifier
            tenant_id: Tenant identifier
            integration_id: Integration identifier
            session_id: Session identifier
            expires_in_seconds: State lifetime in seconds
        """
        from omniforge.storage.models import OAuthStateModel

        state_model = OAuthStateModel(
            state=state,
            user_id=user_id,
            tenant_id=tenant_id,
            integration_id=integration_id,
            session_id=session_id,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(seconds=expires_in_seconds),
        )
        self._db.add(state_model)
        await self._db.commit()

    async def _validate_state(self, state: str) -> OAuthStateData:
        """Validate OAuth state and return associated data.

        Args:
            state: State token to validate

        Returns:
            State data if valid

        Raises:
            OAuthStateError: If state is invalid or expired
        """
        from omniforge.storage.models import OAuthStateModel

        result = await self._db.execute(
            select(OAuthStateModel).where(OAuthStateModel.state == state)
        )
        state_model = result.scalar_one_or_none()

        if not state_model:
            raise OAuthStateError("Invalid or expired OAuth state")

        if state_model.expires_at < datetime.utcnow():
            raise OAuthStateError("OAuth state expired")

        return OAuthStateData(
            user_id=state_model.user_id,
            tenant_id=state_model.tenant_id,
            integration_id=state_model.integration_id,
            session_id=state_model.session_id,
        )

    async def _exchange_code(self, config: OAuthConfig, code: str) -> OAuthTokens:
        """Exchange authorization code for access tokens.

        Args:
            config: OAuth configuration
            code: Authorization code from provider

        Returns:
            OAuth tokens

        Raises:
            OAuthTokenError: If token exchange fails
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    config.token_url,
                    data={
                        "grant_type": "authorization_code",
                        "code": code,
                        "redirect_uri": config.redirect_uri,
                    },
                    auth=(config.client_id, config.client_secret),
                    headers={"Accept": "application/json"},
                )
                response.raise_for_status()
                data = response.json()

                return OAuthTokens(
                    access_token=data["access_token"],
                    refresh_token=data.get("refresh_token"),
                    token_type=data.get("token_type", "Bearer"),
                    expires_in=data.get("expires_in"),
                    scopes=data.get("scope", "").split() if "scope" in data else config.scopes,
                )
            except httpx.HTTPError as e:
                raise OAuthTokenError(f"Token exchange failed: {e}") from e

    async def _store_credential(
        self,
        user_id: str,
        tenant_id: str,
        integration_id: str,
        tokens: OAuthTokens,
        workspace_name: Optional[str] = None,
    ) -> str:
        """Encrypt and store OAuth credential.

        Args:
            user_id: User identifier
            tenant_id: Tenant identifier
            integration_id: Integration identifier
            tokens: OAuth tokens to store
            workspace_name: Optional workspace name

        Returns:
            Credential ID
        """
        from omniforge.storage.models import OAuthCredentialModel

        # Encrypt tokens
        access_token_encrypted = self._encryptor.encrypt(tokens.access_token)
        refresh_token_encrypted = (
            self._encryptor.encrypt(tokens.refresh_token) if tokens.refresh_token else None
        )

        # Calculate expiration
        expires_at = None
        if tokens.expires_in:
            expires_at = datetime.utcnow() + timedelta(seconds=tokens.expires_in)

        # Create credential model
        credential = OAuthCredentialModel(
            user_id=user_id,
            tenant_id=tenant_id,
            integration_id=integration_id,
            workspace_name=workspace_name,
            access_token_encrypted=access_token_encrypted,
            refresh_token_encrypted=refresh_token_encrypted,
            token_type=tokens.token_type,
            expires_at=expires_at,
            scopes=tokens.scopes,
        )

        self._db.add(credential)
        await self._db.commit()
        await self._db.refresh(credential)

        return credential.id

    async def _get_credential(self, credential_id: str) -> "OAuthCredentialModel":
        """Retrieve credential by ID.

        Args:
            credential_id: Credential identifier

        Returns:
            OAuth credential model

        Raises:
            OAuthPermissionError: If credential not found
        """
        from omniforge.storage.models import OAuthCredentialModel

        result = await self._db.execute(
            select(OAuthCredentialModel).where(OAuthCredentialModel.id == credential_id)
        )
        credential = result.scalar_one_or_none()

        if not credential:
            raise OAuthPermissionError("Credential not found")

        return credential

    def _is_expired(self, credential: "OAuthCredentialModel") -> bool:
        """Check if credential is expired.

        Args:
            credential: OAuth credential model

        Returns:
            True if expired or expiring within 5 minutes
        """
        if not credential.expires_at:
            return False

        # Refresh if expiring within 5 minutes
        buffer = timedelta(minutes=5)
        return credential.expires_at < datetime.utcnow() + buffer

    async def _refresh_token(self, credential: "OAuthCredentialModel") -> "OAuthCredentialModel":
        """Refresh expired access token.

        Args:
            credential: OAuth credential model

        Returns:
            Updated credential model

        Raises:
            OAuthTokenError: If refresh fails
        """
        if not credential.refresh_token_encrypted:
            raise OAuthTokenError("No refresh token available")

        config = self._configs[credential.integration_id]
        refresh_token = self._encryptor.decrypt(credential.refresh_token_encrypted)

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    config.token_url,
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": refresh_token,
                    },
                    auth=(config.client_id, config.client_secret),
                    headers={"Accept": "application/json"},
                )
                response.raise_for_status()
                data = response.json()

                # Update credential with new tokens
                credential.access_token_encrypted = self._encryptor.encrypt(data["access_token"])

                if "refresh_token" in data:
                    credential.refresh_token_encrypted = self._encryptor.encrypt(
                        data["refresh_token"]
                    )

                if "expires_in" in data:
                    credential.expires_at = datetime.utcnow() + timedelta(
                        seconds=data["expires_in"]
                    )

                credential.updated_at = datetime.utcnow()

                await self._db.commit()
                await self._db.refresh(credential)

                return credential

            except httpx.HTTPError as e:
                raise OAuthTokenError(f"Token refresh failed: {e}") from e
