"""Tests for placeholder response generator.

This module tests the ResponseGenerator class which provides placeholder
responses for initial chat system development.
"""

import pytest

from omniforge.chat.response_generator import ResponseGenerator


class TestResponseGenerator:
    """Tests for ResponseGenerator class."""

    @pytest.mark.asyncio
    async def test_generate_stream_yields_chunks(self, monkeypatch) -> None:
        """generate_stream should yield multiple string chunks via async iteration."""
        # Use placeholder mode to avoid LLM calls in unit tests
        monkeypatch.setenv("OMNIFORGE_USE_PLACEHOLDER_LLM", "true")
        generator = ResponseGenerator()
        chunks: list[str] = []

        async for chunk in generator.generate_stream("Hello"):
            chunks.append(chunk)
            # Verify each chunk is a string
            assert isinstance(chunk, str)

        # Verify we received multiple chunks (placeholder mode always yields chunks)
        assert len(chunks) > 0, "Should yield at least one chunk"

        # Verify all chunks are non-empty strings
        for chunk in chunks:
            assert isinstance(chunk, str), "Each chunk should be a string"
            assert len(chunk) > 0, "Each chunk should be non-empty"

    def test_count_tokens_returns_positive_int(self) -> None:
        """count_tokens should return a positive integer for token count."""
        generator = ResponseGenerator()

        # Test with normal text
        result = generator.count_tokens("Hello, world!")
        assert isinstance(result, int), "Token count should be an integer"
        assert result > 0, "Token count should be positive"

        # Test with empty string (should return minimum of 1)
        result_empty = generator.count_tokens("")
        assert isinstance(result_empty, int)
        assert result_empty > 0, "Token count should be at least 1 even for empty string"

        # Test with longer text
        long_text = "This is a longer piece of text with many words."
        result_long = generator.count_tokens(long_text)
        assert isinstance(result_long, int)
        assert result_long > 0

        # Verify longer text has more tokens than shorter text
        assert result_long > result, "Longer text should have more tokens"
