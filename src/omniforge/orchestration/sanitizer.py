"""Context sanitization for safe inter-agent communication.

This module provides regex-based PII redaction to ensure sensitive information
is not passed between agents during orchestration and handoffs.
"""

import re


class ContextSanitizer:
    """Sanitizes context data by redacting PII patterns.

    Uses pre-compiled regex patterns to detect and redact sensitive information
    such as email addresses, credit card numbers, and password/token patterns.

    Examples:
        >>> sanitizer = ContextSanitizer()
        >>> sanitizer.sanitize("Contact me at user@example.com")
        'Contact me at [EMAIL]'
        >>> sanitizer.sanitize("Card: 4532-1234-5678-9010")
        'Card: [CARD]'
        >>> sanitizer.is_clean("This is safe text")
        True
    """

    def __init__(self) -> None:
        """Initialize the sanitizer with default patterns."""
        # Pre-compile patterns for performance
        self._patterns: list[tuple[re.Pattern[str], str]] = [
            # Email addresses
            (
                re.compile(
                    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
                    re.IGNORECASE,
                ),
                "[EMAIL]",
            ),
            # 16-digit card numbers (with or without separators)
            (
                re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"),
                "[CARD]",
            ),
            # Password/secret/token key-value pairs
            # Matches patterns like: password=xxx, secret:xxx, token="xxx", api_key='xxx'
            (
                re.compile(
                    r"\b(password|passwd|pwd|secret|token|api[_-]?key|auth[_-]?key)"
                    r"[\s]*[=:]+[\s]*['\"]?[^\s'\"]+['\"]?",
                    re.IGNORECASE,
                ),
                r"\1=[REDACTED]",
            ),
        ]

    def sanitize(self, text: str) -> str:
        """Apply all sanitization patterns to the given text.

        Args:
            text: Input text that may contain sensitive information

        Returns:
            Sanitized text with PII patterns replaced with placeholders

        Examples:
            >>> sanitizer = ContextSanitizer()
            >>> sanitizer.sanitize("Email: john@doe.com, Card: 1234-5678-9012-3456")
            'Email: [EMAIL], Card: [CARD]'
            >>> sanitizer.sanitize("password=secret123")
            'password=[REDACTED]'
        """
        result = text
        for pattern, replacement in self._patterns:
            result = pattern.sub(replacement, result)
        return result

    def add_pattern(self, pattern: str, replacement: str) -> None:
        r"""Add a custom sanitization pattern at runtime.

        Args:
            pattern: Regular expression pattern to match
            replacement: Replacement string for matches

        Examples:
            >>> sanitizer = ContextSanitizer()
            >>> sanitizer.add_pattern(r"\b\d{3}-\d{2}-\d{4}\b", "[SSN]")
            >>> sanitizer.sanitize("SSN: 123-45-6789")
            'SSN: [SSN]'
        """
        compiled_pattern = re.compile(pattern)
        self._patterns.append((compiled_pattern, replacement))

    def is_clean(self, text: str) -> bool:
        """Check if text contains any sensitive patterns.

        Args:
            text: Text to check for sensitive information

        Returns:
            True if no sensitive patterns are detected, False otherwise

        Examples:
            >>> sanitizer = ContextSanitizer()
            >>> sanitizer.is_clean("This is safe text")
            True
            >>> sanitizer.is_clean("Email: user@example.com")
            False
            >>> sanitizer.is_clean("Card: 1234-5678-9012-3456")
            False
        """
        for pattern, _ in self._patterns:
            if pattern.search(text):
                return False
        return True
