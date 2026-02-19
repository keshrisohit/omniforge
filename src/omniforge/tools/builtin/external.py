"""External API tool base class for HTTP-based integrations.

This module provides the ExternalAPITool base class for creating tools that
interact with external HTTP APIs, with built-in error handling, timeout
enforcement, and request/response logging.
"""

import time
from typing import Any, Optional

import httpx

from omniforge.tools.base import (
    BaseTool,
    ParameterType,
    ToolCallContext,
    ToolDefinition,
    ToolParameter,
    ToolResult,
)
from omniforge.tools.types import ToolType


class ExternalAPITool(BaseTool):
    """Base class for external API tools.

    Provides common HTTP functionality for tools that interact with external
    APIs through the unified tool interface with:
    - Async HTTP requests via httpx
    - Automatic timeout enforcement
    - Header management
    - Error handling and conversion to ToolResult
    - Request/response logging

    Subclasses should override:
    - definition property: Define tool name, parameters, and description
    - execute method: Implement tool-specific logic using _get, _post, _request

    Example:
        >>> class MyAPITool(ExternalAPITool):
        ...     def __init__(self):
        ...         super().__init__(
        ...             name="my_api",
        ...             description="My API integration",
        ...             base_url="https://api.example.com",
        ...             headers={"Authorization": "Bearer token"}
        ...         )
        ...
        ...     @property
        ...     def definition(self) -> ToolDefinition:
        ...         return ToolDefinition(
        ...             name=self._name,
        ...             type=ToolType.API,
        ...             description=self._description,
        ...             parameters=[...],
        ...             timeout_ms=self._timeout_ms
        ...         )
        ...
        ...     async def execute(self, arguments: dict, context: ToolCallContext):
        ...         data = await self._get("/endpoint", params={"key": "value"})
        ...         return ToolResult(success=True, result=data, duration_ms=0)
    """

    def __init__(
        self,
        name: str,
        description: str,
        base_url: str,
        headers: Optional[dict[str, str]] = None,
        timeout_ms: int = 30000,
    ) -> None:
        """Initialize ExternalAPITool.

        Args:
            name: Tool name
            description: Tool description
            base_url: Base URL for API requests
            headers: Optional headers to include in all requests
            timeout_ms: Request timeout in milliseconds
        """
        self._name = name
        self._description = description
        self._base_url = base_url.rstrip("/")
        self._headers = headers or {}
        self._timeout_ms = timeout_ms

    async def _request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Make an HTTP request to the API.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: Request path relative to base_url
            **kwargs: Additional arguments for httpx.request

        Returns:
            Response data as dictionary

        Raises:
            Exception: If request fails or times out
        """
        url = f"{self._base_url}/{path.lstrip('/')}"
        timeout_seconds = self._timeout_ms / 1000

        # Merge provided headers with default headers
        request_headers = {**self._headers, **kwargs.pop("headers", {})}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=request_headers,
                    timeout=timeout_seconds,
                    **kwargs,
                )

                # Raise for HTTP errors (4xx, 5xx)
                response.raise_for_status()

                # Return JSON response if available
                try:
                    return response.json()
                except Exception:
                    # If not JSON, return text as dict
                    return {"text": response.text, "status_code": response.status_code}

        except httpx.TimeoutException as e:
            raise Exception(f"Request timed out after {self._timeout_ms}ms: {str(e)}")
        except httpx.HTTPStatusError as e:
            raise Exception(
                f"HTTP error {e.response.status_code}: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise Exception(f"Request failed: {str(e)}")
        except Exception as e:
            raise Exception(f"Unexpected error: {str(e)}")

    async def _get(
        self,
        path: str,
        params: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Make a GET request to the API.

        Args:
            path: Request path relative to base_url
            params: Optional query parameters

        Returns:
            Response data as dictionary

        Raises:
            Exception: If request fails
        """
        return await self._request("GET", path, params=params)

    async def _post(
        self,
        path: str,
        json_data: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Make a POST request to the API.

        Args:
            path: Request path relative to base_url
            json_data: Optional JSON body data

        Returns:
            Response data as dictionary

        Raises:
            Exception: If request fails
        """
        return await self._request("POST", path, json=json_data)

    @property
    def definition(self) -> ToolDefinition:
        """Get tool definition.

        This base implementation should be overridden by subclasses to provide
        specific tool parameters and descriptions.

        Returns:
            ToolDefinition with base configuration
        """
        return ToolDefinition(
            name=self._name,
            type=ToolType.API,
            description=self._description,
            parameters=[],
            timeout_ms=self._timeout_ms,
        )

    async def execute(
        self, context: ToolCallContext, arguments: dict[str, Any]
    ) -> ToolResult:
        """Execute API tool.

        This base implementation should be overridden by subclasses to implement
        specific API logic.

        Args:
            context: Execution context
            arguments: Tool arguments

        Returns:
            ToolResult indicating method should be overridden
        """
        return ToolResult(
            success=False,
            error="execute() method must be overridden by subclass",
            duration_ms=0,
        )


class WeatherAPITool(ExternalAPITool):
    """Example weather API tool demonstrating ExternalAPITool usage.

    This tool demonstrates how to create a specific API integration by
    extending ExternalAPITool. It provides weather information for a location.

    Example:
        >>> tool = WeatherAPITool(api_key="your-key")
        >>> context = ToolCallContext(
        ...     correlation_id="corr-1",
        ...     task_id="task-1",
        ...     agent_id="agent-1"
        ... )
        >>> result = await tool.execute(
        ...     arguments={"location": "San Francisco", "units": "metric"},
        ...     context=context
        ... )
        >>> result.success
        True
    """

    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.weather.example.com"):
        """Initialize WeatherAPITool.

        Args:
            api_key: Optional API key for authentication
            base_url: Base URL for weather API (defaults to example URL)
        """
        headers = {}
        if api_key:
            headers["X-API-Key"] = api_key

        super().__init__(
            name="weather",
            description="Get current weather information for a location",
            base_url=base_url,
            headers=headers,
            timeout_ms=10000,  # 10 seconds
        )

    @property
    def definition(self) -> ToolDefinition:
        """Get tool definition."""
        return ToolDefinition(
            name=self._name,
            type=ToolType.API,
            description=self._description,
            parameters=[
                ToolParameter(
                    name="location",
                    type=ParameterType.STRING,
                    description="City name or location to get weather for",
                    required=True,
                ),
                ToolParameter(
                    name="units",
                    type=ParameterType.STRING,
                    description="Units for temperature (metric or imperial)",
                    required=False,
                ),
            ],
            timeout_ms=self._timeout_ms,
        )

    async def execute(
        self, context: ToolCallContext, arguments: dict[str, Any]
    ) -> ToolResult:
        """Execute weather API request.

        Args:
            context: Execution context
            arguments: Tool arguments containing location and units

        Returns:
            ToolResult with weather data or error
        """
        start_time = time.time()

        # Extract and validate arguments
        location = arguments.get("location", "").strip()
        units = arguments.get("units", "metric").lower()

        if not location:
            return ToolResult(
                success=False,
                error="location parameter is required",
                duration_ms=int((time.time() - start_time) * 1000),
            )

        if units not in ["metric", "imperial"]:
            return ToolResult(
                success=False,
                error="units must be 'metric' or 'imperial'",
                duration_ms=int((time.time() - start_time) * 1000),
            )

        try:
            # Make API request
            response = await self._get(
                "/weather",
                params={
                    "q": location,
                    "units": units,
                },
            )

            duration_ms = int((time.time() - start_time) * 1000)

            # Parse and return weather data
            return ToolResult(
                success=True,
                result={
                    "location": location,
                    "units": units,
                    "weather": response,
                },
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return ToolResult(
                success=False,
                error=f"Weather API request failed: {str(e)}",
                duration_ms=duration_ms,
            )
