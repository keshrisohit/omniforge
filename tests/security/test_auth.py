"""Tests for authentication and authorization."""

from omniforge.security.auth import validate_api_key, validate_bearer_token
from omniforge.security.rbac import Role


class TestValidateApiKey:
    """Tests for API key validation."""

    def test_valid_api_key_format(self) -> None:
        """Valid API key should be accepted."""
        api_key = "tenant-123:developer:secret-key-abc123"
        is_valid, tenant_id, role = validate_api_key(api_key)

        assert is_valid is True
        assert tenant_id == "tenant-123"
        assert role == Role.DEVELOPER

    def test_all_roles_accepted(self) -> None:
        """All valid roles should be accepted in API key."""
        for role_value in ["viewer", "operator", "developer", "admin"]:
            api_key = f"tenant-1:{role_value}:secret-key-abc123"
            is_valid, tenant_id, role = validate_api_key(api_key)

            assert is_valid is True
            assert tenant_id == "tenant-1"
            assert role.value == role_value

    def test_invalid_format_missing_parts(self) -> None:
        """API key with missing parts should be rejected."""
        api_key = "tenant-123:developer"  # Missing secret
        is_valid, tenant_id, role = validate_api_key(api_key)

        assert is_valid is False
        assert tenant_id is None
        assert role is None

    def test_invalid_format_too_many_parts(self) -> None:
        """API key with too many parts should be rejected."""
        api_key = "tenant-123:developer:secret:extra"
        is_valid, tenant_id, role = validate_api_key(api_key)

        assert is_valid is False
        assert tenant_id is None
        assert role is None

    def test_invalid_role(self) -> None:
        """API key with invalid role should be rejected."""
        api_key = "tenant-123:invalid-role:secret-key-abc123"
        is_valid, tenant_id, role = validate_api_key(api_key)

        assert is_valid is False
        assert tenant_id is None
        assert role is None

    def test_empty_tenant_id(self) -> None:
        """API key with empty tenant ID should be rejected."""
        api_key = ":developer:secret-key-abc123"
        is_valid, tenant_id, role = validate_api_key(api_key)

        assert is_valid is False
        assert tenant_id is None
        assert role is None

    def test_empty_secret(self) -> None:
        """API key with empty secret should be rejected."""
        api_key = "tenant-123:developer:"
        is_valid, tenant_id, role = validate_api_key(api_key)

        assert is_valid is False
        assert tenant_id is None
        assert role is None

    def test_short_secret_rejected(self) -> None:
        """API key with secret shorter than 10 chars should be rejected."""
        api_key = "tenant-123:developer:short"
        is_valid, tenant_id, role = validate_api_key(api_key)

        assert is_valid is False
        assert tenant_id is None
        assert role is None

    def test_malformed_key(self) -> None:
        """Completely malformed API key should be rejected."""
        api_key = "not-a-valid-key"
        is_valid, tenant_id, role = validate_api_key(api_key)

        assert is_valid is False
        assert tenant_id is None
        assert role is None

    def test_empty_string(self) -> None:
        """Empty string should be rejected."""
        is_valid, tenant_id, role = validate_api_key("")

        assert is_valid is False
        assert tenant_id is None
        assert role is None


class TestValidateBearerToken:
    """Tests for bearer token validation."""

    def test_bearer_token_not_implemented(self) -> None:
        """Bearer token validation should return invalid (stub)."""
        token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
        is_valid, tenant_id, role = validate_bearer_token(token)

        # Currently a stub that returns False
        assert is_valid is False
        assert tenant_id is None
        assert role is None

    def test_empty_bearer_token(self) -> None:
        """Empty bearer token should return invalid."""
        is_valid, tenant_id, role = validate_bearer_token("")

        assert is_valid is False
        assert tenant_id is None
        assert role is None
