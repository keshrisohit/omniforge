"""Credential storage models with encryption."""

import json
import os
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from cryptography.fernet import Fernet
from pydantic import BaseModel, Field, field_validator


class IntegrationType(str, Enum):
    """Supported integration types."""

    NOTION = "notion"
    SLACK = "slack"
    LINEAR = "linear"
    GITHUB = "github"


class Credential(BaseModel):
    """Encrypted credential storage.

    Stores OAuth tokens and API credentials securely with per-tenant encryption.

    Attributes:
        id: Unique credential identifier
        tenant_id: Tenant this credential belongs to
        integration_type: Type of integration (notion, slack, etc.)
        integration_name: User-friendly name for this integration
        credentials: Encrypted credential data (OAuth tokens, API keys)
        created_at: Creation timestamp
        updated_at: Last update timestamp
        last_used_at: Last time this credential was used
    """

    id: Optional[str] = None
    tenant_id: str = Field(..., min_length=1)
    integration_type: IntegrationType
    integration_name: str = Field(..., min_length=1, max_length=200)
    credentials: dict[str, Any] = Field(..., description="Encrypted credential data")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None

    @staticmethod
    def generate_encryption_key() -> bytes:
        """Generate a new Fernet encryption key.

        Returns:
            32-byte URL-safe base64-encoded key
        """
        return Fernet.generate_key()

    @staticmethod
    def encrypt_credentials(credentials: dict[str, Any], key: bytes) -> str:
        """Encrypt credential data.

        Args:
            credentials: Credential dictionary to encrypt
            key: Fernet encryption key

        Returns:
            Base64-encoded encrypted string
        """
        f = Fernet(key)
        json_data = json.dumps(credentials).encode()
        encrypted = f.encrypt(json_data)
        return encrypted.decode()

    @staticmethod
    def decrypt_credentials(encrypted_data: str, key: bytes) -> dict[str, Any]:
        """Decrypt credential data.

        Args:
            encrypted_data: Base64-encoded encrypted string
            key: Fernet encryption key

        Returns:
            Decrypted credential dictionary

        Raises:
            ValueError: If decryption fails
        """
        try:
            f = Fernet(key)
            decrypted = f.decrypt(encrypted_data.encode())
            return json.loads(decrypted.decode())
        except Exception as e:
            raise ValueError(f"Failed to decrypt credentials: {e}") from e

    @staticmethod
    def get_tenant_key(tenant_id: str) -> bytes:
        """Get or generate encryption key for a tenant.

        In production, this should be stored in a secure key management system.
        For MVP, we use environment variables.

        Args:
            tenant_id: Tenant identifier

        Returns:
            Encryption key for this tenant
        """
        # Check for tenant-specific key in environment
        env_key = os.getenv(f"TENANT_KEY_{tenant_id.upper().replace('-', '_')}")
        if env_key:
            return env_key.encode()

        # Fall back to master key (NOT RECOMMENDED FOR PRODUCTION)
        master_key = os.getenv("MASTER_ENCRYPTION_KEY")
        if master_key:
            return master_key.encode()

        # For development only - generate and warn
        key = Fernet.generate_key()
        print(
            f"WARNING: No encryption key found for tenant {tenant_id}. "
            f"Generated temporary key. Set TENANT_KEY_{tenant_id} in production."
        )
        return key

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "tenant_id": "tenant-123",
                "integration_type": "notion",
                "integration_name": "Acme Marketing Workspace",
                "credentials": {
                    "access_token": "secret_...",
                    "workspace_id": "workspace-id",
                    "bot_id": "bot-id",
                },
            }
        }
