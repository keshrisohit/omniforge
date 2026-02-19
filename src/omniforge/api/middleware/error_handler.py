"""Error handling middleware for FastAPI application.

This module provides centralized error handling for the API, converting
domain exceptions and validation errors into appropriate HTTP responses.
"""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError

from omniforge.agents.errors import AgentError
from omniforge.chat.errors import ChatError

# Configure logger for error tracking
logger = logging.getLogger(__name__)


def setup_error_handlers(app: FastAPI) -> None:
    """Configure exception handlers for the FastAPI application.

    This function registers exception handlers that convert various error types
    into appropriate JSON responses with correct HTTP status codes.

    Args:
        app: The FastAPI application instance to configure
    """

    @app.exception_handler(AgentError)
    async def handle_agent_error(request: Request, exc: AgentError) -> JSONResponse:
        """Handle AgentError exceptions and subclasses.

        Converts domain-specific AgentError exceptions into JSON responses
        with appropriate status codes and error information.

        Args:
            request: The incoming request that triggered the error
            exc: The AgentError exception that was raised

        Returns:
            JSONResponse with status code, error code, and message
        """
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.code, "message": exc.message},
        )

    @app.exception_handler(ChatError)
    async def handle_chat_error(request: Request, exc: ChatError) -> JSONResponse:
        """Handle ChatError exceptions and subclasses.

        Converts domain-specific ChatError exceptions into JSON responses
        with appropriate status codes and error information.

        Args:
            request: The incoming request that triggered the error
            exc: The ChatError exception that was raised

        Returns:
            JSONResponse with status code, error code, and message
        """
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.code, "message": exc.message},
        )

    @app.exception_handler(PydanticValidationError)
    async def handle_validation_error(
        request: Request, exc: PydanticValidationError
    ) -> JSONResponse:
        """Handle Pydantic validation errors from request parsing.

        Formats Pydantic validation errors into a user-friendly JSON response
        with detailed field-level error information.

        Args:
            request: The incoming request that failed validation
            exc: The PydanticValidationError with validation details

        Returns:
            JSONResponse with 400 status code and formatted error details
        """
        # Format validation errors into readable messages
        errors: list[dict[str, Any]] = []
        for error in exc.errors():
            field = ".".join(str(loc) for loc in error["loc"])
            errors.append({"field": field, "message": error["msg"]})

        return JSONResponse(
            status_code=400,
            content={
                "code": "validation_error",
                "message": "Request validation failed",
                "errors": errors,
            },
        )

    @app.exception_handler(Exception)
    async def handle_generic_error(request: Request, exc: Exception) -> JSONResponse:
        """Handle unexpected exceptions with generic error response.

        Logs the exception details and returns a generic 500 error to avoid
        exposing internal implementation details to clients.

        Args:
            request: The incoming request that triggered the error
            exc: The unexpected exception that was raised

        Returns:
            JSONResponse with 500 status code and generic error message
        """
        # Log the full exception for debugging
        logger.exception("Unexpected error occurred: %s", exc)

        return JSONResponse(
            status_code=500,
            content={"code": "internal_error", "message": "An internal server error occurred"},
        )
