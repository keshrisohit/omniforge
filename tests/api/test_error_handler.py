"""Tests for error handler middleware."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError as PydanticValidationError

from omniforge.api.middleware.error_handler import setup_error_handlers
from omniforge.chat.errors import InternalError, ValidationError


class TestErrorHandlers:
    """Tests for error handler middleware."""

    @pytest.fixture
    def app(self) -> FastAPI:
        """Create test FastAPI app with error handlers."""
        test_app = FastAPI()
        setup_error_handlers(test_app)
        return test_app

    @pytest.fixture
    def client(self, app: FastAPI) -> TestClient:
        """Create test client."""
        return TestClient(app)

    def test_chat_error_handler_returns_correct_response(self, app: FastAPI) -> None:
        """ChatError handler should return JSON with status code and error details."""

        @app.get("/test-chat-error")
        async def test_endpoint() -> None:
            raise ValidationError("Invalid input")

        client = TestClient(app)
        response = client.get("/test-chat-error")

        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "validation_error"
        assert data["message"] == "Invalid input"

    def test_internal_error_handler_returns_500(self, app: FastAPI) -> None:
        """InternalError handler should return 500 status code."""

        @app.get("/test-internal-error")
        async def test_endpoint() -> None:
            raise InternalError("Something went wrong")

        client = TestClient(app)
        response = client.get("/test-internal-error")

        assert response.status_code == 500
        data = response.json()
        assert data["code"] == "internal_error"
        assert data["message"] == "Something went wrong"

    def test_pydantic_validation_error_handler_formats_errors(self, app: FastAPI) -> None:
        """Pydantic validation error handler should format field errors."""

        @app.get("/test-validation-error")
        async def test_endpoint() -> None:
            # Create a Pydantic validation error
            from pydantic import BaseModel, Field

            class TestModel(BaseModel):
                name: str = Field(..., min_length=1)

            try:
                TestModel(name="")
            except PydanticValidationError as e:
                raise e

        client = TestClient(app)
        response = client.get("/test-validation-error")

        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "validation_error"
        assert data["message"] == "Request validation failed"
        assert "errors" in data

    def test_generic_exception_handler_returns_500(self, app: FastAPI) -> None:
        """Generic exception handler should return 500 for unexpected errors."""

        @app.get("/test-generic-error")
        async def test_endpoint() -> None:
            raise RuntimeError("Unexpected error")

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/test-generic-error")

        assert response.status_code == 500
        data = response.json()
        assert data["code"] == "internal_error"
        assert data["message"] == "An internal server error occurred"

    def test_generic_exception_handler_does_not_expose_details(self, app: FastAPI) -> None:
        """Generic exception handler should not expose internal error details."""

        @app.get("/test-hidden-error")
        async def test_endpoint() -> None:
            raise ValueError("Secret internal information")

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/test-hidden-error")

        data = response.json()
        # Should not contain the original error message
        assert "Secret internal information" not in data["message"]
        assert data["message"] == "An internal server error occurred"
