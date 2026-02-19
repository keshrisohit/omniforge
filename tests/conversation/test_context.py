"""Tests for conversation context assembly functions."""

import logging
from uuid import uuid4

import pytest

from omniforge.conversation.context import (
    _format_message,
    _get_role_value,
    assemble_context,
    estimate_tokens,
    format_context_for_llm,
)
from omniforge.conversation.models import Message, MessageRole


class TestEstimateTokens:
    """Tests for token estimation function."""

    def test_empty_string_returns_zero(self) -> None:
        """Empty string should return 0 tokens."""
        assert estimate_tokens("") == 0

    def test_simple_text_returns_positive_count(self) -> None:
        """Simple text should return a positive token count."""
        count = estimate_tokens("Hello world")
        assert count > 0

    def test_longer_text_returns_higher_count(self) -> None:
        """Longer text should return more tokens than shorter text."""
        short_count = estimate_tokens("Hi")
        long_count = estimate_tokens("This is a much longer piece of text")
        assert long_count > short_count

    def test_fallback_logs_warning_when_tiktoken_unavailable(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Should log warning when falling back to character estimation.

        Note: This test only verifies the warning is logged if tiktoken
        is actually unavailable. If tiktoken is installed, no warning occurs.
        """
        with caplog.at_level(logging.WARNING):
            estimate_tokens("test")

        # If tiktoken is not available, warning should be logged
        if any("tiktoken not available" in record.message for record in caplog.records):
            assert "fallback token estimation" in caplog.text

    def test_consistent_results_for_same_input(self) -> None:
        """Same input should return same token count."""
        text = "The quick brown fox jumps over the lazy dog"
        count1 = estimate_tokens(text)
        count2 = estimate_tokens(text)
        assert count1 == count2

    def test_unicode_text_handled_correctly(self) -> None:
        """Unicode characters should be handled correctly."""
        # Should not raise an error and should return positive count
        count = estimate_tokens("Hello 世界 🌍")
        assert count > 0


class TestAssembleContext:
    """Tests for context assembly function."""

    def create_message(self, content: str, role: MessageRole = MessageRole.USER) -> Message:
        """Helper to create a test message."""
        return Message(
            conversation_id=uuid4(),
            role=role,
            content=content,
        )

    def test_empty_messages_returns_empty_list(self) -> None:
        """Empty message list should return empty context."""
        result = assemble_context([], max_messages=10)
        assert result == []

    def test_messages_within_limit_returns_all(self) -> None:
        """When messages < max_messages, should return all messages."""
        messages = [
            self.create_message("msg1"),
            self.create_message("msg2"),
            self.create_message("msg3"),
        ]

        result = assemble_context(messages, max_messages=10)
        assert len(result) == 3
        assert result == messages

    def test_messages_exceeding_limit_returns_most_recent(self) -> None:
        """When messages > max_messages, should return most recent N."""
        messages = [
            self.create_message("msg1"),
            self.create_message("msg2"),
            self.create_message("msg3"),
            self.create_message("msg4"),
            self.create_message("msg5"),
        ]

        result = assemble_context(messages, max_messages=3)
        assert len(result) == 3
        assert result[0].content == "msg3"
        assert result[1].content == "msg4"
        assert result[2].content == "msg5"

    def test_maintains_chronological_order(self) -> None:
        """Returned messages should maintain chronological order."""
        messages = [
            self.create_message("first"),
            self.create_message("second"),
            self.create_message("third"),
        ]

        result = assemble_context(messages, max_messages=2)
        assert result[0].content == "second"
        assert result[1].content == "third"

    def test_single_message_handled_correctly(self) -> None:
        """Single message should be handled correctly."""
        messages = [self.create_message("only message")]

        result = assemble_context(messages, max_messages=10)
        assert len(result) == 1
        assert result[0].content == "only message"

    def test_max_messages_equals_count_returns_all(self) -> None:
        """When max_messages equals message count, should return all."""
        messages = [
            self.create_message("msg1"),
            self.create_message("msg2"),
            self.create_message("msg3"),
        ]

        result = assemble_context(messages, max_messages=3)
        assert len(result) == 3
        assert result == messages

    def test_max_messages_zero_returns_empty(self) -> None:
        """max_messages=0 should return empty list."""
        messages = [self.create_message("msg1")]

        result = assemble_context(messages, max_messages=0)
        assert result == []

    def test_max_messages_negative_returns_empty(self) -> None:
        """Negative max_messages should return empty list."""
        messages = [self.create_message("msg1")]

        result = assemble_context(messages, max_messages=-5)
        assert result == []

    def test_default_max_messages_is_20(self) -> None:
        """Default max_messages should be 20."""
        messages = [self.create_message(f"msg{i}") for i in range(25)]

        result = assemble_context(messages)
        assert len(result) == 20
        # Should return messages 5-24 (0-indexed)
        assert result[0].content == "msg5"
        assert result[-1].content == "msg24"

    def test_mixed_roles_preserved(self) -> None:
        """Different message roles should be preserved."""
        messages = [
            self.create_message("user msg", MessageRole.USER),
            self.create_message("assistant msg", MessageRole.ASSISTANT),
            self.create_message("system msg", MessageRole.SYSTEM),
        ]

        result = assemble_context(messages, max_messages=10)
        assert result[0].role == MessageRole.USER
        assert result[1].role == MessageRole.ASSISTANT
        assert result[2].role == MessageRole.SYSTEM


class TestFormatContextForLLM:
    """Tests for LLM context formatting function."""

    def create_message(self, content: str, role: MessageRole = MessageRole.USER) -> Message:
        """Helper to create a test message."""
        return Message(
            conversation_id=uuid4(),
            role=role,
            content=content,
        )

    def test_empty_messages_returns_empty_list(self) -> None:
        """Empty message list should return empty formatted list."""
        result = format_context_for_llm([])
        assert result == []

    def test_single_message_formatted_correctly(self) -> None:
        """Single message should be formatted with role and content."""
        messages = [self.create_message("Hello", MessageRole.USER)]

        result = format_context_for_llm(messages)
        assert len(result) == 1
        assert result[0] == {"role": "user", "content": "Hello"}

    def test_multiple_messages_formatted_correctly(self) -> None:
        """Multiple messages should all be formatted correctly."""
        messages = [
            self.create_message("Hello", MessageRole.USER),
            self.create_message("Hi there!", MessageRole.ASSISTANT),
        ]

        result = format_context_for_llm(messages)
        assert len(result) == 2
        assert result[0] == {"role": "user", "content": "Hello"}
        assert result[1] == {"role": "assistant", "content": "Hi there!"}

    def test_all_message_roles_handled(self) -> None:
        """All MessageRole values should be handled correctly."""
        messages = [
            self.create_message("user msg", MessageRole.USER),
            self.create_message("assistant msg", MessageRole.ASSISTANT),
            self.create_message("system msg", MessageRole.SYSTEM),
        ]

        result = format_context_for_llm(messages)
        assert result[0]["role"] == "user"
        assert result[1]["role"] == "assistant"
        assert result[2]["role"] == "system"

    def test_empty_content_preserved(self) -> None:
        """Empty message content should be preserved."""
        messages = [self.create_message("", MessageRole.USER)]

        result = format_context_for_llm(messages)
        assert result[0]["content"] == ""

    def test_long_content_preserved(self) -> None:
        """Long message content should be preserved without truncation."""
        long_content = "x" * 10000
        messages = [self.create_message(long_content, MessageRole.USER)]

        result = format_context_for_llm(messages)
        assert result[0]["content"] == long_content
        assert len(result[0]["content"]) == 10000

    def test_maintains_message_order(self) -> None:
        """Message order should be preserved in formatted output."""
        messages = [
            self.create_message("first", MessageRole.USER),
            self.create_message("second", MessageRole.ASSISTANT),
            self.create_message("third", MessageRole.USER),
        ]

        result = format_context_for_llm(messages)
        assert result[0]["content"] == "first"
        assert result[1]["content"] == "second"
        assert result[2]["content"] == "third"


class TestFormatMessage:
    """Tests for single message formatting helper."""

    def create_message(self, content: str, role: MessageRole = MessageRole.USER) -> Message:
        """Helper to create a test message."""
        return Message(
            conversation_id=uuid4(),
            role=role,
            content=content,
        )

    def test_user_message_formatted_correctly(self) -> None:
        """User message should be formatted as 'user: content'."""
        msg = self.create_message("Hello", MessageRole.USER)
        result = _format_message(msg)
        assert result == "user: Hello"

    def test_assistant_message_formatted_correctly(self) -> None:
        """Assistant message should be formatted as 'assistant: content'."""
        msg = self.create_message("Hi there!", MessageRole.ASSISTANT)
        result = _format_message(msg)
        assert result == "assistant: Hi there!"

    def test_system_message_formatted_correctly(self) -> None:
        """System message should be formatted as 'system: content'."""
        msg = self.create_message("System prompt", MessageRole.SYSTEM)
        result = _format_message(msg)
        assert result == "system: System prompt"

    def test_empty_content_handled(self) -> None:
        """Empty content should be handled correctly."""
        msg = self.create_message("", MessageRole.USER)
        result = _format_message(msg)
        assert result == "user: "


class TestGetRoleValue:
    """Tests for role value extraction helper."""

    def test_message_role_enum_returns_value(self) -> None:
        """MessageRole enum should return string value."""
        assert _get_role_value(MessageRole.USER) == "user"
        assert _get_role_value(MessageRole.ASSISTANT) == "assistant"
        assert _get_role_value(MessageRole.SYSTEM) == "system"

    def test_string_role_returns_unchanged(self) -> None:
        """String role should be returned unchanged."""
        assert _get_role_value("user") == "user"
        assert _get_role_value("assistant") == "assistant"
        assert _get_role_value("system") == "system"

    def test_custom_string_role_handled(self) -> None:
        """Custom string roles should be handled correctly."""
        assert _get_role_value("custom_role") == "custom_role"


class TestIntegration:
    """Integration tests combining multiple functions."""

    def create_message(self, content: str, role: MessageRole = MessageRole.USER) -> Message:
        """Helper to create a test message."""
        return Message(
            conversation_id=uuid4(),
            role=role,
            content=content,
        )

    def test_full_context_assembly_pipeline(self) -> None:
        """Test complete pipeline: create -> assemble -> format."""
        # Create conversation history
        messages = [
            self.create_message("msg1", MessageRole.USER),
            self.create_message("msg2", MessageRole.ASSISTANT),
            self.create_message("msg3", MessageRole.USER),
            self.create_message("msg4", MessageRole.ASSISTANT),
            self.create_message("msg5", MessageRole.USER),
        ]

        # Assemble context with limit
        context = assemble_context(messages, max_messages=3)

        # Format for LLM
        formatted = format_context_for_llm(context)

        # Verify results
        assert len(formatted) == 3
        assert formatted[0] == {"role": "user", "content": "msg3"}
        assert formatted[1] == {"role": "assistant", "content": "msg4"}
        assert formatted[2] == {"role": "user", "content": "msg5"}

    def test_token_estimation_for_context(self) -> None:
        """Test token estimation for assembled context."""
        messages = [
            self.create_message("Hello", MessageRole.USER),
            self.create_message("Hi there!", MessageRole.ASSISTANT),
        ]

        # Format messages for token counting
        formatted_msgs = [_format_message(msg) for msg in messages]
        combined_text = "\n".join(formatted_msgs)

        # Estimate tokens
        token_count = estimate_tokens(combined_text)

        # Should return a reasonable count
        assert token_count > 0
        assert token_count < 100  # Should be relatively small for short messages
