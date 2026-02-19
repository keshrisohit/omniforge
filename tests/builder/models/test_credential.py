"""Tests for Credential model and encryption."""

import os

import pytest

from omniforge.builder.models import Credential, IntegrationType


class TestCredential:
    """Tests for Credential model."""

    def test_valid_credential(self) -> None:
        """Test creating a valid credential."""
        cred = Credential(
            tenant_id="tenant-123",
            integration_type=IntegrationType.NOTION,
            integration_name="Acme Workspace",
            credentials={
                "access_token": "secret_token",
                "workspace_id": "workspace-123",
            },
        )

        assert cred.tenant_id == "tenant-123"
        assert cred.integration_type == IntegrationType.NOTION
        assert cred.integration_name == "Acme Workspace"
        assert cred.credentials["access_token"] == "secret_token"

    def test_integration_type_validation(self) -> None:
        """Test integration_type must be valid enum."""
        # Valid types
        for integration_type in [
            IntegrationType.NOTION,
            IntegrationType.SLACK,
            IntegrationType.LINEAR,
            IntegrationType.GITHUB,
        ]:
            Credential(
                tenant_id="tenant-123",
                integration_type=integration_type,
                integration_name="Test",
                credentials={},
            )

    def test_generate_encryption_key(self) -> None:
        """Test encryption key generation."""
        key = Credential.generate_encryption_key()

        assert isinstance(key, bytes)
        assert len(key) == 44  # Fernet keys are 44 bytes when base64-encoded

        # Keys should be unique
        key2 = Credential.generate_encryption_key()
        assert key != key2

    def test_encrypt_decrypt_credentials(self) -> None:
        """Test credential encryption and decryption."""
        key = Credential.generate_encryption_key()
        original_creds = {
            "access_token": "secret_abc123",
            "refresh_token": "refresh_xyz789",
            "workspace_id": "workspace-456",
            "expires_at": "2026-12-31T23:59:59Z",
        }

        # Encrypt
        encrypted = Credential.encrypt_credentials(original_creds, key)
        assert isinstance(encrypted, str)
        assert "secret_abc123" not in encrypted  # Should not contain plain text

        # Decrypt
        decrypted = Credential.decrypt_credentials(encrypted, key)
        assert decrypted == original_creds

    def test_decrypt_with_wrong_key_fails(self) -> None:
        """Test decryption fails with wrong key."""
        key1 = Credential.generate_encryption_key()
        key2 = Credential.generate_encryption_key()

        creds = {"token": "secret"}
        encrypted = Credential.encrypt_credentials(creds, key1)

        # Decrypting with wrong key should fail
        with pytest.raises(ValueError, match="Failed to decrypt"):
            Credential.decrypt_credentials(encrypted, key2)

    def test_decrypt_invalid_data_fails(self) -> None:
        """Test decryption fails with invalid data."""
        key = Credential.generate_encryption_key()

        # Try to decrypt invalid base64
        with pytest.raises(ValueError, match="Failed to decrypt"):
            Credential.decrypt_credentials("not-valid-encrypted-data", key)

    def test_get_tenant_key_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test getting tenant-specific key from environment."""
        tenant_id = "tenant-abc-123"
        test_key = Credential.generate_encryption_key()

        # Set tenant-specific key
        monkeypatch.setenv("TENANT_KEY_TENANT_ABC_123", test_key.decode())

        retrieved_key = Credential.get_tenant_key(tenant_id)
        assert retrieved_key == test_key

    def test_get_tenant_key_falls_back_to_master(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test fallback to master key when tenant key not found."""
        master_key = Credential.generate_encryption_key()
        monkeypatch.setenv("MASTER_ENCRYPTION_KEY", master_key.decode())

        # Remove any tenant-specific key
        monkeypatch.delenv("TENANT_KEY_TENANT_123", raising=False)

        retrieved_key = Credential.get_tenant_key("tenant-123")
        assert retrieved_key == master_key

    def test_encrypt_decrypt_round_trip_with_tenant_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test full encryption/decryption cycle with tenant key."""
        tenant_id = "tenant-test"
        tenant_key = Credential.generate_encryption_key()
        monkeypatch.setenv(f"TENANT_KEY_{tenant_id.upper().replace('-', '_')}", tenant_key.decode())

        original_creds = {
            "notion_token": "secret_notion_abc",
            "workspace": "workspace-123",
        }

        # Encrypt with tenant key
        key = Credential.get_tenant_key(tenant_id)
        encrypted = Credential.encrypt_credentials(original_creds, key)

        # Decrypt with same tenant key
        key_again = Credential.get_tenant_key(tenant_id)
        decrypted = Credential.decrypt_credentials(encrypted, key_again)

        assert decrypted == original_creds

    def test_empty_credentials_dict(self) -> None:
        """Test handling empty credentials dict."""
        key = Credential.generate_encryption_key()
        empty_creds: dict = {}

        encrypted = Credential.encrypt_credentials(empty_creds, key)
        decrypted = Credential.decrypt_credentials(encrypted, key)

        assert decrypted == empty_creds

    def test_complex_nested_credentials(self) -> None:
        """Test encrypting complex nested credential structures."""
        key = Credential.generate_encryption_key()
        complex_creds = {
            "oauth": {
                "access_token": "token_abc",
                "refresh_token": "refresh_xyz",
                "scopes": ["read", "write"],
                "expires_in": 3600,
            },
            "workspace": {
                "id": "ws-123",
                "name": "Acme Corp",
                "users": [{"id": "u1", "role": "admin"}],
            },
        }

        encrypted = Credential.encrypt_credentials(complex_creds, key)
        decrypted = Credential.decrypt_credentials(encrypted, key)

        assert decrypted == complex_creds
        assert decrypted["oauth"]["access_token"] == "token_abc"
        assert decrypted["workspace"]["users"][0]["role"] == "admin"
