"""Correlation ID middleware for request tracing.

This middleware automatically generates and attaches correlation IDs
to all incoming requests for distributed tracing.
"""

import time
import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from omniforge.observability.logging import get_logger, set_correlation_id
from omniforge.observability.metrics import get_metrics_collector

logger = get_logger(__name__)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware to inject correlation IDs into requests.

    Generates a unique correlation ID for each request and:
    - Sets it in the logging context
    - Adds it to response headers
    - Records request metrics
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Process request with correlation ID.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            HTTP response with correlation ID header

        Example:
            Request headers: (none)
            Response headers: X-Correlation-ID: 550e8400-e29b-41d4-a716-446655440000
        """
        # Generate or extract correlation ID
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())

        # Set correlation ID in logging context
        set_correlation_id(correlation_id)

        # Record request start time
        start_time = time.time()

        # Log request
        logger.info(
            "request_started",
            method=request.method,
            path=request.url.path,
            correlation_id=correlation_id,
        )

        try:
            # Process request
            response = await call_next(request)

            # Calculate duration
            duration_seconds = time.time() - start_time

            # Record metrics
            metrics_collector = get_metrics_collector()
            metrics_collector.record_http_request(
                method=request.method,
                endpoint=request.url.path,
                status_code=response.status_code,
                duration_seconds=duration_seconds,
            )

            # Log response
            logger.info(
                "request_completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=int(duration_seconds * 1000),
                correlation_id=correlation_id,
            )

            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = correlation_id

            return response

        except Exception as e:
            # Calculate duration
            duration_seconds = time.time() - start_time

            # Log error
            logger.error(
                "request_failed",
                method=request.method,
                path=request.url.path,
                error=str(e),
                duration_ms=int(duration_seconds * 1000),
                correlation_id=correlation_id,
            )

            # Re-raise to let error handler deal with it
            raise
