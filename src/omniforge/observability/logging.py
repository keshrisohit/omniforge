"""Structured logging configuration with correlation ID support.

This module sets up structured logging using structlog with JSON output
and automatic correlation ID injection for distributed tracing.
"""

import logging
import sys
from contextvars import ContextVar
from typing import Any, Optional

import structlog

# Context variable to store correlation ID per request
correlation_id_var: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)


def add_correlation_id(
    logger: logging.Logger, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Add correlation ID to log event if available.

    Args:
        logger: Logger instance
        method_name: Log method name (info, error, etc.)
        event_dict: Event dictionary to modify

    Returns:
        Modified event dictionary with correlation_id
    """
    correlation_id = correlation_id_var.get()
    if correlation_id:
        event_dict["correlation_id"] = correlation_id
    return event_dict


def setup_logging(log_level: str = "INFO", json_logs: bool = True) -> None:
    """Configure structured logging with structlog.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_logs: If True, output logs in JSON format; otherwise use console format

    Example:
        >>> setup_logging(log_level="INFO", json_logs=True)
        >>> logger = get_logger(__name__)
        >>> logger.info("application_started", version="0.1.0")
    """
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )

    # Shared processors for all log events
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        add_correlation_id,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if json_logs:
        # JSON output for production
        structlog.configure(
            processors=shared_processors
            + [
                structlog.processors.format_exc_info,
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
    else:
        # Console-friendly output for development
        structlog.configure(
            processors=shared_processors
            + [
                structlog.processors.ExceptionPrettyPrinter(),
                structlog.dev.ConsoleRenderer(),
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured structlog logger

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("user_action", user_id="123", action="login")
    """
    return structlog.get_logger(name)


def set_correlation_id(correlation_id: str) -> None:
    """Set correlation ID for the current context.

    Args:
        correlation_id: Unique identifier for request tracing

    Example:
        >>> set_correlation_id("req-123-456")
        >>> logger.info("processing_request")  # Will include correlation_id
    """
    correlation_id_var.set(correlation_id)


def get_correlation_id() -> Optional[str]:
    """Get the current correlation ID.

    Returns:
        Correlation ID if set, None otherwise

    Example:
        >>> set_correlation_id("req-123-456")
        >>> get_correlation_id()
        'req-123-456'
    """
    return correlation_id_var.get()


def clear_correlation_id() -> None:
    """Clear the correlation ID from the current context.

    Example:
        >>> set_correlation_id("req-123-456")
        >>> clear_correlation_id()
        >>> get_correlation_id()
        None
    """
    correlation_id_var.set(None)
