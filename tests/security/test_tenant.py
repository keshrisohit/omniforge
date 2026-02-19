"""Tests for tenant context management."""

from omniforge.security.tenant import TenantContext, get_tenant_id


class TestTenantContext:
    """Tests for TenantContext class."""

    def test_get_without_set_returns_none(self) -> None:
        """Getting tenant ID without setting should return None."""
        # Clear context first
        TenantContext.clear()

        assert TenantContext.get() is None

    def test_set_and_get_tenant_id(self) -> None:
        """Setting tenant ID should allow retrieval."""
        tenant_id = "tenant-123"
        TenantContext.set(tenant_id)

        assert TenantContext.get() == tenant_id

        # Cleanup
        TenantContext.clear()

    def test_set_overrides_previous_value(self) -> None:
        """Setting new tenant ID should override previous value."""
        TenantContext.set("tenant-1")
        TenantContext.set("tenant-2")

        assert TenantContext.get() == "tenant-2"

        # Cleanup
        TenantContext.clear()

    def test_clear_removes_tenant_id(self) -> None:
        """Clearing context should remove tenant ID."""
        TenantContext.set("tenant-123")
        TenantContext.clear()

        assert TenantContext.get() is None

    def test_set_none_clears_context(self) -> None:
        """Setting None should clear the context."""
        TenantContext.set("tenant-123")
        TenantContext.set(None)

        assert TenantContext.get() is None


class TestGetTenantId:
    """Tests for get_tenant_id helper function."""

    def test_get_tenant_id_returns_current_tenant(self) -> None:
        """get_tenant_id should return current tenant from context."""
        tenant_id = "tenant-456"
        TenantContext.set(tenant_id)

        assert get_tenant_id() == tenant_id

        # Cleanup
        TenantContext.clear()

    def test_get_tenant_id_returns_none_when_not_set(self) -> None:
        """get_tenant_id should return None when no tenant is set."""
        TenantContext.clear()

        assert get_tenant_id() is None
