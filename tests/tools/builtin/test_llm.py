"""Tests for LLM tool."""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from omniforge.llm.config import LLMConfig, ProviderConfig
from omniforge.tools import ToolType
from omniforge.tools.base import ToolCallContext
from omniforge.tools.builtin.llm import LLMTool


def create_llm_response(
    content: str, prompt_tokens: int, completion_tokens: int, model: str = "gpt-4"
):
    """Create a properly mocked LLM response that works with both attribute and dict access."""
    mock = MagicMock()
    mock.choices = [MagicMock()]
    mock.choices[0].message = MagicMock()
    mock.choices[0].message.content = content
    mock.usage = MagicMock()
    mock.usage.prompt_tokens = prompt_tokens
    mock.usage.completion_tokens = completion_tokens
    mock.model = model

    # Configure dict-like access for calculate_cost_from_response
    mock.__contains__ = MagicMock(side_effect=lambda x: x in ["usage", "model"])
    mock.get = MagicMock(
        side_effect=lambda k, default=None: {"usage": mock.usage, "model": mock.model}.get(
            k, default
        )
    )

    # Add model_dump for Pydantic compatibility
    mock.model_dump = MagicMock(
        return_value={
            "usage": {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens},
            "model": model,
        }
    )

    return mock


@pytest.fixture
def llm_config() -> LLMConfig:
    """Create test LLM configuration."""
    return LLMConfig(
        default_model="gpt-4",
        fallback_models=["gpt-3.5-turbo"],
        timeout_ms=30000,
        max_retries=2,
        cost_tracking_enabled=True,
        approved_models=["gpt-4", "gpt-3.5-turbo", "claude-sonnet-4"],
        providers={
            "openai": ProviderConfig(api_key="sk-test-key"),
            "anthropic": ProviderConfig(api_key="sk-ant-test-key"),
        },
    )


@pytest.fixture
def tool_context() -> ToolCallContext:
    """Create test tool call context."""
    return ToolCallContext(
        correlation_id="corr-123",
        task_id="task-123",
        agent_id="agent-456",
        tenant_id="tenant-789",
    )


def test_llm_tool_initialization_default_config() -> None:
    """Test LLM tool initializes with default config."""
    tool = LLMTool()

    assert tool._config is not None
    assert tool._config.default_model == "groq/qwen/qwen3-32b"
    assert tool._config.cost_tracking_enabled is False


def test_llm_tool_initialization_custom_config(llm_config: LLMConfig) -> None:
    """Test LLM tool initializes with custom config."""
    tool = LLMTool(config=llm_config)

    assert tool._config == llm_config
    assert tool._config.default_model == "gpt-4"


def test_llm_tool_definition(llm_config: LLMConfig) -> None:
    """Test LLM tool definition."""
    tool = LLMTool(config=llm_config)
    definition = tool.definition

    assert definition.name == "llm"
    assert definition.type == ToolType.LLM

    # Check parameters (now a list)
    param_names = [p.name for p in definition.parameters]
    assert "prompt" in param_names
    assert "messages" in param_names
    assert "model" in param_names
    assert "temperature" in param_names
    assert "max_tokens" in param_names

    assert definition.timeout_ms == 30000
    assert definition.retry_config.max_retries == 2


def test_llm_tool_build_messages_from_prompt(llm_config: LLMConfig) -> None:
    """Test building messages from simple prompt."""
    tool = LLMTool(config=llm_config)

    arguments = {"prompt": "What is 2+2?"}
    messages = tool._build_messages(arguments)

    assert len(messages) == 1
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "What is 2+2?"


def test_llm_tool_build_messages_with_system(llm_config: LLMConfig) -> None:
    """Test building messages with system prompt."""
    tool = LLMTool(config=llm_config)

    arguments = {"prompt": "What is 2+2?", "system": "You are a math tutor"}
    messages = tool._build_messages(arguments)

    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == "You are a math tutor"
    assert messages[1]["role"] == "user"
    assert messages[1]["content"] == "What is 2+2?"


def test_llm_tool_build_messages_from_messages_array(llm_config: LLMConfig) -> None:
    """Test using provided messages array."""
    tool = LLMTool(config=llm_config)

    messages_input = [
        {"role": "system", "content": "You are helpful"},
        {"role": "user", "content": "Hello"},
    ]
    arguments = {"messages": messages_input}
    messages = tool._build_messages(arguments)

    assert messages == messages_input


def test_llm_tool_build_messages_empty(llm_config: LLMConfig) -> None:
    """Test building messages with no prompt or messages."""
    tool = LLMTool(config=llm_config)

    arguments: dict = {}
    messages = tool._build_messages(arguments)

    assert messages == []


@pytest.mark.asyncio
async def test_llm_tool_execute_success(
    llm_config: LLMConfig, tool_context: ToolCallContext
) -> None:
    """Test successful LLM execution."""
    tool = LLMTool(config=llm_config)
    mock_response = create_llm_response("2+2 equals 4", 10, 5)

    with patch("litellm.acompletion", new_callable=AsyncMock) as mock_acompletion:
        mock_acompletion.return_value = mock_response

        result = await tool.execute(arguments={"prompt": "What is 2+2?"}, context=tool_context)

        assert result.success is True
        assert result.result["content"] == "2+2 equals 4"
        assert result.result["model"] == "gpt-4"
        assert result.tokens_used == 15
        assert result.cost_usd > 0
        assert result.duration_ms >= 0


@pytest.mark.asyncio
async def test_llm_tool_execute_with_custom_model(
    llm_config: LLMConfig, tool_context: ToolCallContext
) -> None:
    """Test LLM execution with custom model."""
    tool = LLMTool(config=llm_config)
    mock_response = create_llm_response("Claude response", 8, 12, "claude-sonnet-4")

    with patch("litellm.acompletion", new_callable=AsyncMock) as mock_acompletion:
        mock_acompletion.return_value = mock_response

        result = await tool.execute(
            arguments={"prompt": "Hello", "model": "claude-sonnet-4"}, context=tool_context
        )

        assert result.success is True
        assert result.result["model"] == "claude-sonnet-4"
        assert result.result["provider"] == "anthropic"

        # Verify LiteLLM was called with correct model
        mock_acompletion.assert_called_once()
        call_kwargs = mock_acompletion.call_args[1]
        assert call_kwargs["model"] == "claude-sonnet-4"


@pytest.mark.asyncio
async def test_llm_tool_execute_unapproved_model(
    llm_config: LLMConfig, tool_context: ToolCallContext
) -> None:
    """Test LLM execution rejects unapproved model."""
    tool = LLMTool(config=llm_config)

    result = await tool.execute(
        arguments={"prompt": "Hello", "model": "unknown-model"}, context=tool_context
    )

    assert result.success is False
    assert "not in approved models list" in result.error


@pytest.mark.asyncio
async def test_llm_tool_execute_no_prompt_or_messages(
    llm_config: LLMConfig, tool_context: ToolCallContext
) -> None:
    """Test LLM execution requires prompt or messages."""
    tool = LLMTool(config=llm_config)

    result = await tool.execute(arguments={}, context=tool_context)

    assert result.success is False
    assert "required" in result.error.lower()


@pytest.mark.asyncio
async def test_llm_tool_execute_with_temperature_and_max_tokens(
    llm_config: LLMConfig, tool_context: ToolCallContext
) -> None:
    """Test LLM execution with custom temperature and max_tokens."""
    tool = LLMTool(config=llm_config)
    mock_response = create_llm_response("Response", 5, 10)

    with patch("litellm.acompletion", new_callable=AsyncMock) as mock_acompletion:
        mock_acompletion.return_value = mock_response

        result = await tool.execute(
            arguments={"prompt": "Test", "temperature": 0.5, "max_tokens": 500},
            context=tool_context,
        )

        assert result.success is True
        assert result.result["temperature"] == 0.5
        assert result.result["max_tokens"] == 500

        # Verify parameters passed to LiteLLM
        call_kwargs = mock_acompletion.call_args[1]
        assert call_kwargs["temperature"] == 0.5
        assert call_kwargs["max_tokens"] == 500


@pytest.mark.asyncio
async def test_llm_tool_execute_error_handling(
    llm_config: LLMConfig, tool_context: ToolCallContext
) -> None:
    """Test LLM execution handles errors gracefully."""
    tool = LLMTool(config=llm_config)

    with patch("litellm.acompletion", new_callable=AsyncMock) as mock_acompletion:
        mock_acompletion.side_effect = Exception("API error")

        result = await tool.execute(arguments={"prompt": "Test"}, context=tool_context)

        assert result.success is False
        assert "LLM call failed" in result.error
        assert "API error" in result.error


@pytest.mark.asyncio
async def test_llm_tool_execute_streaming_success(
    llm_config: LLMConfig, tool_context: ToolCallContext
) -> None:
    """Test successful LLM streaming execution."""
    tool = LLMTool(config=llm_config)

    # Mock streaming response
    async def mock_streaming_response():
        chunks = [
            Mock(choices=[Mock(delta=Mock(content="Hello"))]),
            Mock(choices=[Mock(delta=Mock(content=" world"))]),
            Mock(choices=[Mock(delta=Mock(content="!"))]),
        ]
        for chunk in chunks:
            yield chunk

    with patch("litellm.acompletion", new_callable=AsyncMock) as mock_acompletion:
        mock_acompletion.return_value = mock_streaming_response()

        results = []
        async for chunk in tool.execute_streaming(
            arguments={"prompt": "Say hello"}, context=tool_context
        ):
            results.append(chunk)

        # Should have token chunks + final result
        assert len(results) == 4

        # Check token chunks
        assert results[0]["token"] == "Hello"
        assert results[1]["token"] == " world"
        assert results[2]["token"] == "!"

        # Check final result
        assert results[3]["done"] is True
        assert results[3]["content"] == "Hello world!"
        assert results[3]["model"] == "gpt-4"
        assert results[3]["output_tokens"] == 3


@pytest.mark.asyncio
async def test_llm_tool_execute_streaming_unapproved_model(
    llm_config: LLMConfig, tool_context: ToolCallContext
) -> None:
    """Test streaming rejects unapproved model."""
    tool = LLMTool(config=llm_config)

    results = []
    async for chunk in tool.execute_streaming(
        arguments={"prompt": "Test", "model": "unknown-model"}, context=tool_context
    ):
        results.append(chunk)

    assert len(results) == 1
    assert "error" in results[0]
    assert "not in approved models list" in results[0]["error"]


@pytest.mark.asyncio
async def test_llm_tool_execute_streaming_error(
    llm_config: LLMConfig, tool_context: ToolCallContext
) -> None:
    """Test streaming handles errors gracefully."""
    tool = LLMTool(config=llm_config)

    with patch("litellm.acompletion", new_callable=AsyncMock) as mock_acompletion:
        mock_acompletion.side_effect = Exception("Streaming error")

        results = []
        async for chunk in tool.execute_streaming(
            arguments={"prompt": "Test"}, context=tool_context
        ):
            results.append(chunk)

        assert len(results) == 1
        assert "error" in results[0]
        assert "Streaming error" in results[0]["error"]


def test_llm_tool_get_provider_env_var(llm_config: LLMConfig) -> None:
    """Test provider environment variable mapping."""
    tool = LLMTool(config=llm_config)

    assert tool._get_provider_env_var("openai") == "OPENAI_API_KEY"
    assert tool._get_provider_env_var("anthropic") == "ANTHROPIC_API_KEY"
    assert tool._get_provider_env_var("azure") == "AZURE_API_KEY"
    assert tool._get_provider_env_var("google") == "GOOGLE_API_KEY"
    assert tool._get_provider_env_var("groq") == "GROQ_API_KEY"
    assert tool._get_provider_env_var("unknown") is None


@pytest.mark.asyncio
async def test_llm_tool_cost_tracking(llm_config: LLMConfig, tool_context: ToolCallContext) -> None:
    """Test cost tracking in LLM calls."""
    tool = LLMTool(config=llm_config)
    mock_response = create_llm_response("Response", 100, 50)

    with patch("litellm.acompletion", new_callable=AsyncMock) as mock_acompletion:
        mock_acompletion.return_value = mock_response

        result = await tool.execute(arguments={"prompt": "Test"}, context=tool_context)

        assert result.success is True
        assert result.cost_usd > 0
        assert result.tokens_used == 150


@pytest.mark.asyncio
async def test_llm_tool_with_messages_array(
    llm_config: LLMConfig, tool_context: ToolCallContext
) -> None:
    """Test LLM execution with messages array."""
    tool = LLMTool(config=llm_config)
    mock_response = create_llm_response("Conversation response", 20, 10)

    messages = [
        {"role": "user", "content": "First message"},
        {"role": "assistant", "content": "First response"},
        {"role": "user", "content": "Follow up"},
    ]

    with patch("litellm.acompletion", new_callable=AsyncMock) as mock_acompletion:
        mock_acompletion.return_value = mock_response

        result = await tool.execute(arguments={"messages": messages}, context=tool_context)

        assert result.success is True

        # Verify messages passed to LiteLLM
        call_kwargs = mock_acompletion.call_args[1]
        assert call_kwargs["messages"] == messages
