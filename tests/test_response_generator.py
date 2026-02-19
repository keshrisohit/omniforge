"""Tests for chat response generator."""

import pytest

from omniforge.chat.response_generator import ResponseGenerator


class TestResponseGenerator:
    """Tests for ResponseGenerator class using placeholder mode."""

    @pytest.mark.asyncio
    async def test_generate_stream_yields_multiple_parts(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should yield response in multiple parts."""
        monkeypatch.setenv("OMNIFORGE_USE_PLACEHOLDER_LLM", "true")
        generator = ResponseGenerator()

        parts = []
        async for part in generator.generate_stream("Hello"):
            parts.append(part)

        # Should receive multiple parts
        assert len(parts) > 0
        # All parts should be strings
        assert all(isinstance(part, str) for part in parts)

    @pytest.mark.asyncio
    async def test_generate_stream_includes_user_message(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should include the user's message in the response."""
        monkeypatch.setenv("OMNIFORGE_USE_PLACEHOLDER_LLM", "true")
        generator = ResponseGenerator()

        full_response = ""
        async for part in generator.generate_stream("Test message"):
            full_response += part

        # Response should mention the user's message
        assert "Test message" in full_response

    @pytest.mark.asyncio
    async def test_generate_stream_has_thank_you(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should include thank you message in response."""
        monkeypatch.setenv("OMNIFORGE_USE_PLACEHOLDER_LLM", "true")
        generator = ResponseGenerator()

        full_response = ""
        async for part in generator.generate_stream("Hi"):
            full_response += part

        # Should contain thank you
        assert "Thank you" in full_response

    @pytest.mark.asyncio
    async def test_generate_stream_indicates_placeholder(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should indicate this is a placeholder response."""
        monkeypatch.setenv("OMNIFORGE_USE_PLACEHOLDER_LLM", "true")
        generator = ResponseGenerator()

        full_response = ""
        async for part in generator.generate_stream("Test"):
            full_response += part

        # Should mention it's a placeholder
        assert "placeholder" in full_response.lower()

    @pytest.mark.asyncio
    async def test_generate_stream_with_empty_message(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should handle empty message."""
        monkeypatch.setenv("OMNIFORGE_USE_PLACEHOLDER_LLM", "true")
        generator = ResponseGenerator()

        parts = []
        async for part in generator.generate_stream(""):
            parts.append(part)

        # Should still generate response
        assert len(parts) > 0

    @pytest.mark.asyncio
    async def test_generate_stream_with_long_message(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should handle long messages."""
        monkeypatch.setenv("OMNIFORGE_USE_PLACEHOLDER_LLM", "true")
        generator = ResponseGenerator()
        long_message = "A" * 1000

        parts = []
        async for part in generator.generate_stream(long_message):
            parts.append(part)

        # Should still generate response
        assert len(parts) > 0
        full_response = "".join(parts)
        # Should include the long message
        assert long_message in full_response


class TestCountTokens:
    """Tests for count_tokens method."""

    def test_count_tokens_short_text(self) -> None:
        """Should count tokens for short text."""
        generator = ResponseGenerator()
        # "Hello, world!" is 13 characters, so ~3 tokens
        assert generator.count_tokens("Hello, world!") == 3

    def test_count_tokens_long_text(self) -> None:
        """Should count tokens for longer text."""
        generator = ResponseGenerator()
        # 100 characters should be ~25 tokens
        text = "A" * 100
        assert generator.count_tokens(text) == 25

    def test_count_tokens_empty_string_returns_minimum(self) -> None:
        """Should return minimum of 1 token for empty string."""
        generator = ResponseGenerator()
        assert generator.count_tokens("") == 1

    def test_count_tokens_single_character_returns_minimum(self) -> None:
        """Should return minimum of 1 token for single character."""
        generator = ResponseGenerator()
        assert generator.count_tokens("A") == 1

    def test_count_tokens_three_characters_returns_minimum(self) -> None:
        """Should return minimum of 1 token for 1-3 characters."""
        generator = ResponseGenerator()
        assert generator.count_tokens("ABC") == 1

    def test_count_tokens_four_characters(self) -> None:
        """Should return 1 token for exactly 4 characters."""
        generator = ResponseGenerator()
        assert generator.count_tokens("ABCD") == 1

    def test_count_tokens_five_characters(self) -> None:
        """Should return 1 token for 5 characters (5 // 4 = 1)."""
        generator = ResponseGenerator()
        assert generator.count_tokens("ABCDE") == 1

    def test_count_tokens_eight_characters(self) -> None:
        """Should return 2 tokens for 8 characters (8 // 4 = 2)."""
        generator = ResponseGenerator()
        assert generator.count_tokens("ABCDEFGH") == 2

    def test_count_tokens_with_whitespace(self) -> None:
        """Should count whitespace as characters."""
        generator = ResponseGenerator()
        # 16 characters including spaces
        text = "Hello world test"
        assert generator.count_tokens(text) == 4

    def test_count_tokens_with_special_characters(self) -> None:
        """Should count special characters."""
        generator = ResponseGenerator()
        # Special chars count as characters
        text = "!@#$%^&*()"  # 10 chars
        assert generator.count_tokens(text) == 2
