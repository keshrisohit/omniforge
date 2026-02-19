"""Tests for security-related exceptions."""

from omniforge.agents.errors import (
    ForbiddenError,
    TenantIsolationError,
    UnauthorizedError,
)


class TestUnauthorizedError:
    """Tests for UnauthorizedError."""

    def test_default_message(self) -> None:
        """Default message should be 'Authentication required'."""
        error = UnauthorizedError()

        assert error.message == "Authentication required"
        assert error.code == "unauthorized"
        assert error.status_code == 401

    def test_custom_message(self) -> None:
        """Custom message should be preserved."""
        error = UnauthorizedError("Invalid credentials")

        assert error.message == "Invalid credentials"
        assert error.code == "unauthorized"
        assert error.status_code == 401


class TestForbiddenError:
    """Tests for ForbiddenError."""

    def test_default_message(self) -> None:
        """Default message should be 'Insufficient permissions'."""
        error = ForbiddenError()

        assert error.message == "Insufficient permissions"
        assert error.code == "forbidden"
        assert error.status_code == 403

    def test_custom_message(self) -> None:
        """Custom message should be preserved."""
        error = ForbiddenError("Access denied to resource")

        assert error.message == "Access denied to resource"
        assert error.code == "forbidden"
        assert error.status_code == 403


class TestTenantIsolationError:
    """Tests for TenantIsolationError."""

    def test_agent_isolation_error(self) -> None:
        """Error for agent isolation violation should have correct format."""
        error = TenantIsolationError("agent", "agent-123")

        assert "agent" in error.message
        assert "agent-123" in error.message
        assert "different tenant" in error.message
        assert error.code == "tenant_isolation_violation"
        assert error.status_code == 403
        assert error.resource_type == "agent"
        assert error.resource_id == "agent-123"

    def test_task_isolation_error(self) -> None:
        """Error for task isolation violation should have correct format."""
        error = TenantIsolationError("task", "task-456")

        assert "task" in error.message
        assert "task-456" in error.message
        assert "different tenant" in error.message
        assert error.code == "tenant_isolation_violation"
        assert error.status_code == 403
        assert error.resource_type == "task"
        assert error.resource_id == "task-456"
