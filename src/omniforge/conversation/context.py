"""Context assembly functions for conversation history.

Provides pure functions for assembling conversation context from message history,
formatting messages for LLM consumption, and estimating token counts.
"""

import logging
from typing import Any, Union

from omniforge.conversation.models import Message, MessageRole

logger = logging.getLogger(__name__)


def estimate_tokens(text: str) -> int:
    """Estimate token count for text using tiktoken with fallback.

    Attempts to use tiktoken (OpenAI's tokenizer) for accurate token counting.
    Falls back to character-based estimation (len(text) // 3) if tiktoken is
    unavailable. Logs a warning on fallback.

    Args:
        text: Text to estimate token count for

    Returns:
        Estimated number of tokens

    Examples:
        >>> estimate_tokens("Hello world")
        4
        >>> estimate_tokens("")
        0
    """
    if not text:
        return 0

    try:
        import tiktoken

        # Use cl100k_base encoding (GPT-4, GPT-3.5-turbo)
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    except ImportError:
        logger.warning(
            "tiktoken not available, using fallback token estimation (len(text) // 3). "
            "Install tiktoken for accurate token counting: pip install tiktoken"
        )
        # Conservative estimate: ~3 characters per token
        return len(text) // 3


def assemble_context(messages: list[Message], max_messages: int = 20) -> list[Message]:
    """Assemble conversation context using message-count sliding window.

    Returns the most recent N messages in chronological order. This is a
    simplified v1 approach using message count instead of token budgets.

    Args:
        messages: List of messages in chronological order
        max_messages: Maximum number of messages to include (default: 20)

    Returns:
        List of most recent messages (up to max_messages) in chronological order

    Examples:
        >>> msgs = [msg1, msg2, msg3, msg4, msg5]
        >>> assemble_context(msgs, max_messages=3)
        [msg3, msg4, msg5]
        >>> assemble_context([], max_messages=10)
        []
        >>> assemble_context([msg1, msg2], max_messages=10)
        [msg1, msg2]
    """
    if not messages:
        return []

    if max_messages <= 0:
        return []

    # Return most recent max_messages in chronological order
    return messages[-max_messages:]


def format_context_for_llm(messages: list[Message]) -> list[dict[str, Any]]:
    """Format messages for LLM API consumption.

    Converts Message objects to the standard LLM API format with
    "role" and "content" fields.

    Args:
        messages: List of Message objects to format

    Returns:
        List of dicts with "role" and "content" fields suitable for LLM APIs

    Examples:
        >>> msgs = [
        ...     Message(role=MessageRole.USER, content="Hello"),
        ...     Message(role=MessageRole.ASSISTANT, content="Hi there!")
        ... ]
        >>> format_context_for_llm(msgs)
        [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]
    """
    if not messages:
        return []

    formatted: list[dict[str, Any]] = []
    for msg in messages:
        formatted.append(
            {
                "role": _get_role_value(msg.role),
                "content": msg.content,
            }
        )

    return formatted


def _format_message(msg: Message) -> str:
    """Format a single message for token counting.

    Creates a text representation of a message suitable for token estimation.
    Format: "role: content"

    Args:
        msg: Message to format

    Returns:
        Formatted message string

    Examples:
        >>> msg = Message(role=MessageRole.USER, content="Hello")
        >>> _format_message(msg)
        "user: Hello"
    """
    role = _get_role_value(msg.role)
    return f"{role}: {msg.content}"


def _get_role_value(role: Union[MessageRole, str]) -> str:
    """Extract string value from MessageRole enum or string.

    Handles both MessageRole enum values and raw string roles.

    Args:
        role: MessageRole enum or string

    Returns:
        String representation of the role

    Examples:
        >>> _get_role_value(MessageRole.USER)
        "user"
        >>> _get_role_value("assistant")
        "assistant"
    """
    if isinstance(role, MessageRole):
        return role.value
    return role
