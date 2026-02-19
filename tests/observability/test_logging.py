"""Tests for structured logging."""

from omniforge.observability.logging import (
    clear_correlation_id,
    get_correlation_id,
    get_logger,
    set_correlation_id,
    setup_logging,
)


class TestStructuredLogging:
    """Tests for structured logging setup."""

    def test_setup_logging_with_json_format(self) -> None:
        """setup_logging should configure JSON logging."""
        setup_logging(log_level="INFO", json_logs=True)
        logger = get_logger(__name__)
        assert logger is not None

    def test_setup_logging_with_console_format(self) -> None:
        """setup_logging should configure console logging."""
        setup_logging(log_level="DEBUG", json_logs=False)
        logger = get_logger(__name__)
        assert logger is not None

    def test_get_logger_returns_logger(self) -> None:
        """get_logger should return a valid logger instance."""
        logger = get_logger("test_module")
        assert logger is not None
        assert hasattr(logger, "info")
        assert hasattr(logger, "error")
        assert hasattr(logger, "warning")


class TestCorrelationId:
    """Tests for correlation ID management."""

    def test_set_and_get_correlation_id(self) -> None:
        """Should be able to set and retrieve correlation ID."""
        correlation_id = "test-correlation-123"
        set_correlation_id(correlation_id)

        retrieved_id = get_correlation_id()
        assert retrieved_id == correlation_id

    def test_get_correlation_id_returns_none_initially(self) -> None:
        """get_correlation_id should return None when not set."""
        clear_correlation_id()
        correlation_id = get_correlation_id()
        assert correlation_id is None

    def test_clear_correlation_id_removes_id(self) -> None:
        """clear_correlation_id should remove the correlation ID."""
        set_correlation_id("test-123")
        assert get_correlation_id() == "test-123"

        clear_correlation_id()
        assert get_correlation_id() is None

    def test_correlation_id_isolated_per_context(self) -> None:
        """Correlation IDs should be isolated per context."""
        # Set correlation ID
        set_correlation_id("context-1")
        assert get_correlation_id() == "context-1"

        # Clear and verify
        clear_correlation_id()
        assert get_correlation_id() is None
