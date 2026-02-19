"""Tests for LLM response generator with fallback logic.

This module tests the LLMResponseGenerator class which provides LLM-powered
responses with comprehensive retry/fallback mechanisms for reliability.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from omniforge.chat.llm_generator import LLMResponseGenerator


class TestLLMResponseGenerator:
    """Tests for LLMResponseGenerator class."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock LLM config."""
        mock = MagicMock()
        mock.default_model = "groq/llama-3.1-8b-instant"
        mock.fallback_models = ["groq/mixtral-8x7b-32768", "openrouter/arcee-ai/trinity-large-preview:free"]
        mock.providers = {"openrouter": MagicMock()}
        return mock

    @pytest.fixture
    def mock_env(self, monkeypatch):
        """Mock environment variables for API keys."""
        monkeypatch.setenv("OMNIFORGE_GROQ_API_KEY", "test-groq-key")
        monkeypatch.setenv("OMNIFORGE_OPENROUTER_API_KEY", "test-openrouter-key")

    @pytest.fixture
    def mock_streaming_response(self):
        """Create a mock streaming response from litellm."""
        async def mock_stream():
            chunks = ["Hello", " ", "world", "!"]
            for chunk_text in chunks:
                chunk = MagicMock()
                chunk.choices = [MagicMock()]
                chunk.choices[0].delta = MagicMock()
                chunk.choices[0].delta.content = chunk_text
                yield chunk

        return mock_stream()

    @pytest.mark.asyncio
    async def test_generate_stream_success(self, mock_config, mock_streaming_response, mock_env):
        """Test successful streaming with primary model."""
        with patch("omniforge.chat.llm_generator.load_config_from_env", return_value=mock_config), \
             patch("omniforge.chat.llm_generator.get_max_tokens_for_model", return_value=2048), \
             patch("omniforge.chat.llm_generator.litellm.acompletion", return_value=mock_streaming_response):

            generator = LLMResponseGenerator()
            chunks = []

            async for chunk in generator.generate_stream("Hello"):
                chunks.append(chunk)

            assert len(chunks) > 0
            assert all(isinstance(chunk, str) for chunk in chunks)
            assert "".join(chunks) == "Hello world!"

    @pytest.mark.asyncio
    async def test_is_transient_error_rate_limit(self, mock_config, mock_env):
        """Test rate limit error detection."""
        with patch("omniforge.chat.llm_generator.load_config_from_env", return_value=mock_config), \
             patch("omniforge.chat.llm_generator.get_max_tokens_for_model", return_value=2048):

            generator = LLMResponseGenerator()

            # Test various rate limit error messages
            assert await generator._is_transient_error(Exception("Rate limit exceeded"))
            assert await generator._is_transient_error(Exception("429 Too Many Requests"))
            assert await generator._is_transient_error(Exception("ratelimit error"))
            assert await generator._is_transient_error(Exception("too many requests"))

    @pytest.mark.asyncio
    async def test_is_transient_error_server_errors(self, mock_config, mock_env):
        """Test server error detection."""
        with patch("omniforge.chat.llm_generator.load_config_from_env", return_value=mock_config), \
             patch("omniforge.chat.llm_generator.get_max_tokens_for_model", return_value=2048):

            generator = LLMResponseGenerator()

            # Test various server error messages
            assert await generator._is_transient_error(Exception("500 Internal Server Error"))
            assert await generator._is_transient_error(Exception("502 Bad Gateway"))
            assert await generator._is_transient_error(Exception("503 Service Unavailable"))
            assert await generator._is_transient_error(Exception("504 Gateway Timeout"))

    @pytest.mark.asyncio
    async def test_is_transient_error_network_errors(self, mock_config, mock_env):
        """Test network/timeout error detection."""
        with patch("omniforge.chat.llm_generator.load_config_from_env", return_value=mock_config), \
             patch("omniforge.chat.llm_generator.get_max_tokens_for_model", return_value=2048):

            generator = LLMResponseGenerator()

            # Test various network error messages
            assert await generator._is_transient_error(Exception("Connection timeout"))
            assert await generator._is_transient_error(Exception("Request timed out"))
            assert await generator._is_transient_error(Exception("Network error"))

    @pytest.mark.asyncio
    async def test_is_transient_error_non_transient(self, mock_config, mock_env):
        """Test non-transient error detection."""
        with patch("omniforge.chat.llm_generator.load_config_from_env", return_value=mock_config), \
             patch("omniforge.chat.llm_generator.get_max_tokens_for_model", return_value=2048):

            generator = LLMResponseGenerator()

            # Test non-transient errors
            assert not await generator._is_transient_error(Exception("Invalid API key"))
            assert not await generator._is_transient_error(Exception("Model not found"))
            assert not await generator._is_transient_error(Exception("Invalid request"))

    @pytest.mark.asyncio
    async def test_fallback_on_rate_limit(self, mock_config, mock_env):
        """Test fallback to next model on rate limit."""
        call_count = 0
        attempted_models = []

        async def mock_completion_rate_limit(**kwargs):
            nonlocal call_count, attempted_models
            call_count += 1
            attempted_models.append(kwargs["model"])

            # First call fails with rate limit
            if call_count == 1:
                raise Exception("Rate limit exceeded (429)")

            # Second call succeeds
            async def mock_stream():
                chunk = MagicMock()
                chunk.choices = [MagicMock()]
                chunk.choices[0].delta = MagicMock()
                chunk.choices[0].delta.content = "Success"
                yield chunk

            return mock_stream()

        with patch("omniforge.chat.llm_generator.load_config_from_env", return_value=mock_config), \
             patch("omniforge.chat.llm_generator.get_max_tokens_for_model", return_value=2048), \
             patch("omniforge.chat.llm_generator.litellm.acompletion", side_effect=mock_completion_rate_limit):

            generator = LLMResponseGenerator()
            chunks = []

            async for chunk in generator.generate_stream("Hello"):
                chunks.append(chunk)

            # Verify fallback happened
            assert call_count == 2
            assert attempted_models[0] == "groq/llama-3.1-8b-instant"  # Primary model
            assert attempted_models[1] == "groq/mixtral-8x7b-32768"  # First fallback
            assert "Success" in "".join(chunks)

    @pytest.mark.asyncio
    async def test_max_tokens_reduction_on_rate_limit(self, mock_config, mock_env):
        """Test that max_tokens is reduced by 30% on rate limit."""
        call_count = 0
        max_tokens_used = []

        async def mock_completion_with_tracking(**kwargs):
            nonlocal call_count
            call_count += 1
            max_tokens_used.append(kwargs["max_tokens"])

            # First call fails with rate limit
            if call_count == 1:
                raise Exception("Rate limit exceeded (429)")

            # Second call succeeds
            async def mock_stream():
                chunk = MagicMock()
                chunk.choices = [MagicMock()]
                chunk.choices[0].delta = MagicMock()
                chunk.choices[0].delta.content = "Success"
                yield chunk

            return mock_stream()

        with patch("omniforge.chat.llm_generator.load_config_from_env", return_value=mock_config), \
             patch("omniforge.chat.llm_generator.get_max_tokens_for_model", return_value=2048), \
             patch("omniforge.chat.llm_generator.litellm.acompletion", side_effect=mock_completion_with_tracking):

            generator = LLMResponseGenerator()
            chunks = []

            async for chunk in generator.generate_stream("Hello"):
                chunks.append(chunk)

            # Verify max_tokens reduction
            assert len(max_tokens_used) == 2
            assert max_tokens_used[0] == 2048  # Initial max_tokens
            assert max_tokens_used[1] == int(2048 * 0.7)  # Reduced by 30%

    @pytest.mark.asyncio
    async def test_fallback_chain_exhaustion(self, mock_config, mock_env):
        """Test error when all models in fallback chain fail."""
        async def mock_completion_always_fails(**kwargs):
            raise Exception("Rate limit exceeded (429)")

        with patch("omniforge.chat.llm_generator.load_config_from_env", return_value=mock_config), \
             patch("omniforge.chat.llm_generator.get_max_tokens_for_model", return_value=2048), \
             patch("omniforge.chat.llm_generator.litellm.acompletion", side_effect=mock_completion_always_fails):

            generator = LLMResponseGenerator()
            chunks = []

            async for chunk in generator.generate_stream("Hello"):
                chunks.append(chunk)

            # Should yield error message
            error_message = "".join(chunks)
            assert "error" in error_message.lower()
            assert "multiple models" in error_message.lower()

    @pytest.mark.asyncio
    async def test_generate_with_tools_fallback(self, mock_config, mock_env):
        """Test fallback logic in generate_with_tools."""
        call_count = 0
        attempted_models = []

        async def mock_completion_with_fallback(**kwargs):
            nonlocal call_count, attempted_models
            call_count += 1
            attempted_models.append(kwargs["model"])

            # First call fails with rate limit
            if call_count == 1:
                raise Exception("Rate limit exceeded (429)")

            # Second call succeeds
            response = MagicMock()
            response.choices = [MagicMock()]
            response.choices[0].message = MagicMock()
            response.choices[0].message.content = "Tool response"
            response.choices[0].message.tool_calls = None
            return response

        with patch("omniforge.chat.llm_generator.load_config_from_env", return_value=mock_config), \
             patch("omniforge.chat.llm_generator.get_max_tokens_for_model", return_value=2048), \
             patch("omniforge.chat.llm_generator.litellm.acompletion", side_effect=mock_completion_with_fallback):

            generator = LLMResponseGenerator()
            result = await generator.generate_with_tools(
                messages=[{"role": "user", "content": "Hello"}],
                tools=[{"type": "function", "function": {"name": "test_tool"}}]
            )

            # Verify fallback happened
            assert call_count == 2
            assert attempted_models[0] == "groq/llama-3.1-8b-instant"  # Primary model
            assert attempted_models[1] == "groq/mixtral-8x7b-32768"  # First fallback
            assert result["content"] == "Tool response"

    def test_count_tokens(self, mock_config, mock_env):
        """Test token counting."""
        with patch("omniforge.chat.llm_generator.load_config_from_env", return_value=mock_config), \
             patch("omniforge.chat.llm_generator.get_max_tokens_for_model", return_value=2048):

            generator = LLMResponseGenerator()

            # Test with normal text
            count = generator.count_tokens("Hello, world!")
            assert isinstance(count, int)
            assert count > 0

            # Test with longer text has more tokens
            long_text = "This is a much longer text with many more words and tokens."
            long_count = generator.count_tokens(long_text)
            assert long_count > count
