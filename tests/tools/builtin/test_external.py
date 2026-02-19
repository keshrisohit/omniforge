"""Tests for external API tool."""

from typing import Any
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from omniforge.tools.base import ParameterType, ToolCallContext, ToolDefinition, ToolParameter
from omniforge.tools.builtin.external import ExternalAPITool, WeatherAPITool
from omniforge.tools.types import ToolType


class SimpleAPITool(ExternalAPITool):
    """Simple API tool for testing."""

    def __init__(self, base_url: str = "https://api.example.com"):
        super().__init__(
            name="simple_api",
            description="A simple API tool for testing",
            base_url=base_url,
            headers={"User-Agent": "TestClient"},
            timeout_ms=5000,
        )

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self._name,
            type=ToolType.API,
            description=self._description,
            parameters=[
                ToolParameter(
                    name="query",
                    type=ParameterType.STRING,
                    description="Query parameter",
                    required=True,
                )
            ],
            timeout_ms=self._timeout_ms,
        )

    async def execute(self, arguments: dict[str, Any], context: ToolCallContext):
        query = arguments.get("query", "")
        if not query:
            return self._error_result("query is required")

        try:
            data = await self._get("/test", params={"q": query})
            return self._success_result(data)
        except Exception as e:
            return self._error_result(str(e))

    def _success_result(self, data: dict):
        from omniforge.tools.base import ToolResult

        return ToolResult(success=True, result=data, duration_ms=0)

    def _error_result(self, error: str):
        from omniforge.tools.base import ToolResult

        return ToolResult(success=False, error=error, duration_ms=0)


@pytest.fixture
def tool_context() -> ToolCallContext:
    """Create test tool call context."""
    return ToolCallContext(
        correlation_id="corr-123",
        task_id="task-123",
        agent_id="agent-456",
    )


def test_external_api_tool_initialization():
    """Test ExternalAPITool initializes correctly."""
    tool = SimpleAPITool(base_url="https://test.com")

    assert tool._name == "simple_api"
    assert tool._description == "A simple API tool for testing"
    assert tool._base_url == "https://test.com"
    assert "User-Agent" in tool._headers
    assert tool._timeout_ms == 5000


def test_external_api_tool_base_url_normalization():
    """Test base URL trailing slash is removed."""
    tool = SimpleAPITool(base_url="https://test.com/")

    assert tool._base_url == "https://test.com"


def test_external_api_tool_definition():
    """Test ExternalAPITool definition."""
    tool = SimpleAPITool()
    definition = tool.definition

    assert definition.name == "simple_api"
    assert definition.type == ToolType.API
    assert len(definition.parameters) == 1
    assert definition.parameters[0].name == "query"
    assert definition.timeout_ms == 5000


@pytest.mark.asyncio
async def test_external_api_tool_get_request(tool_context):
    """Test successful GET request."""
    tool = SimpleAPITool()

    # Create a proper mock response
    from unittest.mock import MagicMock

    mock_response = MagicMock()
    mock_response.json = MagicMock(return_value={"result": "success", "data": "test"})
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client:
        async_mock_request = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__.return_value.request = async_mock_request

        result = await tool.execute(
            arguments={"query": "test"},
            context=tool_context,
        )

        assert result.success is True
        assert result.result["result"] == "success"
        assert result.result["data"] == "test"


@pytest.mark.asyncio
async def test_external_api_tool_get_with_params():
    """Test GET request with query parameters."""
    from unittest.mock import MagicMock

    tool = SimpleAPITool()

    mock_response = MagicMock()
    mock_response.json = MagicMock(return_value={"items": [1, 2, 3]})
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client:
        mock_request = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__.return_value.request = mock_request

        data = await tool._get("/test", params={"q": "search", "limit": 10})

        assert data["items"] == [1, 2, 3]
        # Verify params were passed
        call_kwargs = mock_request.call_args[1]
        assert call_kwargs["params"] == {"q": "search", "limit": 10}


@pytest.mark.asyncio
async def test_external_api_tool_post_request():
    """Test successful POST request."""
    from unittest.mock import MagicMock

    tool = SimpleAPITool()

    mock_response = MagicMock()
    mock_response.json = MagicMock(return_value={"created": True, "id": "123"})
    mock_response.status_code = 201
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client:
        mock_request = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__.return_value.request = mock_request

        data = await tool._post("/create", json_data={"name": "test", "value": 42})

        assert data["created"] is True
        assert data["id"] == "123"
        # Verify JSON was passed
        call_kwargs = mock_request.call_args[1]
        assert call_kwargs["json"] == {"name": "test", "value": 42}


@pytest.mark.asyncio
async def test_external_api_tool_headers_passed():
    """Test that headers are passed to requests."""
    from unittest.mock import MagicMock

    tool = SimpleAPITool()

    mock_response = MagicMock()
    mock_response.json = MagicMock(return_value={})
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client:
        mock_request = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__.return_value.request = mock_request

        await tool._get("/test")

        # Verify headers were passed
        call_kwargs = mock_request.call_args[1]
        assert "User-Agent" in call_kwargs["headers"]
        assert call_kwargs["headers"]["User-Agent"] == "TestClient"


@pytest.mark.asyncio
async def test_external_api_tool_http_error():
    """Test HTTP error handling."""
    from unittest.mock import MagicMock

    tool = SimpleAPITool()

    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.text = "Not Found"
    mock_response.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError(
            "404 Not Found",
            request=MagicMock(),
            response=mock_response,
        )
    )

    with patch("httpx.AsyncClient") as mock_client:
        async_mock_request = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__.return_value.request = async_mock_request

        with pytest.raises(Exception, match="HTTP error 404"):
            await tool._get("/missing")


@pytest.mark.asyncio
async def test_external_api_tool_timeout_error():
    """Test timeout error handling."""
    tool = SimpleAPITool()

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.request = AsyncMock(
            side_effect=httpx.TimeoutException("Request timed out")
        )

        with pytest.raises(Exception, match="timed out"):
            await tool._get("/slow")


@pytest.mark.asyncio
async def test_external_api_tool_request_error():
    """Test request error handling."""
    tool = SimpleAPITool()

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.request = AsyncMock(
            side_effect=httpx.RequestError("Connection failed")
        )

        with pytest.raises(Exception, match="Request failed"):
            await tool._get("/test")


@pytest.mark.asyncio
async def test_external_api_tool_non_json_response():
    """Test handling of non-JSON responses."""
    from unittest.mock import MagicMock

    tool = SimpleAPITool()

    mock_response = MagicMock()
    mock_response.json = MagicMock(side_effect=ValueError("Not JSON"))
    mock_response.text = "Plain text response"
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client:
        async_mock_request = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__.return_value.request = async_mock_request

        data = await tool._get("/text")

        assert data["text"] == "Plain text response"
        assert data["status_code"] == 200


def test_weather_api_tool_initialization():
    """Test WeatherAPITool initializes correctly."""
    tool = WeatherAPITool(api_key="test-key")

    assert tool._name == "weather"
    assert "X-API-Key" in tool._headers
    assert tool._headers["X-API-Key"] == "test-key"
    assert tool._timeout_ms == 10000


def test_weather_api_tool_initialization_without_key():
    """Test WeatherAPITool without API key."""
    tool = WeatherAPITool()

    assert tool._name == "weather"
    assert "X-API-Key" not in tool._headers


def test_weather_api_tool_definition():
    """Test WeatherAPITool definition."""
    tool = WeatherAPITool()
    definition = tool.definition

    assert definition.name == "weather"
    assert definition.type == ToolType.API

    param_names = [p.name for p in definition.parameters]
    assert "location" in param_names
    assert "units" in param_names

    # Check location is required
    location_param = next(p for p in definition.parameters if p.name == "location")
    assert location_param.required is True


@pytest.mark.asyncio
async def test_weather_api_tool_successful_request(tool_context):
    """Test successful weather API request."""
    from unittest.mock import MagicMock

    tool = WeatherAPITool()

    mock_weather_data = {
        "temperature": 72,
        "conditions": "Sunny",
        "humidity": 45,
    }

    mock_response = MagicMock()
    mock_response.json = MagicMock(return_value=mock_weather_data)
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client:
        async_mock_request = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__.return_value.request = async_mock_request

        result = await tool.execute(
            arguments={"location": "San Francisco", "units": "metric"},
            context=tool_context,
        )

        assert result.success is True
        assert result.result["location"] == "San Francisco"
        assert result.result["units"] == "metric"
        assert result.result["weather"]["temperature"] == 72
        assert result.result["weather"]["conditions"] == "Sunny"


@pytest.mark.asyncio
async def test_weather_api_tool_missing_location(tool_context):
    """Test error when location is missing."""
    tool = WeatherAPITool()

    result = await tool.execute(
        arguments={"units": "metric"},
        context=tool_context,
    )

    assert result.success is False
    assert "required" in result.error.lower()


@pytest.mark.asyncio
async def test_weather_api_tool_invalid_units(tool_context):
    """Test error with invalid units."""
    tool = WeatherAPITool()

    result = await tool.execute(
        arguments={"location": "New York", "units": "celsius"},
        context=tool_context,
    )

    assert result.success is False
    assert "metric" in result.error.lower() or "imperial" in result.error.lower()


@pytest.mark.asyncio
async def test_weather_api_tool_default_units(tool_context):
    """Test default units when not specified."""
    from unittest.mock import MagicMock

    tool = WeatherAPITool()

    mock_response = MagicMock()
    mock_response.json = MagicMock(return_value={"temperature": 20})
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client:
        mock_request = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__.return_value.request = mock_request

        result = await tool.execute(
            arguments={"location": "London"},
            context=tool_context,
        )

        assert result.success is True
        assert result.result["units"] == "metric"  # Default


@pytest.mark.asyncio
async def test_weather_api_tool_api_failure(tool_context):
    """Test handling of API failure."""
    from unittest.mock import MagicMock

    tool = WeatherAPITool()

    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    mock_response.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError(
            "500 Internal Server Error",
            request=MagicMock(),
            response=mock_response,
        )
    )

    with patch("httpx.AsyncClient") as mock_client:
        async_mock_request = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__.return_value.request = async_mock_request

        result = await tool.execute(
            arguments={"location": "Paris", "units": "metric"},
            context=tool_context,
        )

        assert result.success is False
        assert "failed" in result.error.lower()


@pytest.mark.asyncio
async def test_base_external_api_tool_execute_not_implemented(tool_context):
    """Test base class execute method returns error."""
    tool = ExternalAPITool(
        name="test",
        description="Test",
        base_url="https://api.test.com",
    )

    result = await tool.execute(arguments={}, context=tool_context)

    assert result.success is False
    assert "overridden" in result.error.lower()
