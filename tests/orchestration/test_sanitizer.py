"""Tests for context sanitization."""


from omniforge.orchestration.sanitizer import ContextSanitizer


class TestContextSanitizer:
    """Tests for ContextSanitizer class."""

    def test_sanitize_email_addresses(self) -> None:
        """Should redact email addresses with [EMAIL] placeholder."""
        sanitizer = ContextSanitizer()

        # Single email
        assert sanitizer.sanitize("Contact me at user@example.com") == "Contact me at [EMAIL]"

        # Multiple emails
        result = sanitizer.sanitize("Emails: john@doe.com and jane@smith.org")
        assert result == "Emails: [EMAIL] and [EMAIL]"

        # Email in various contexts
        assert sanitizer.sanitize("Email: admin@company.co.uk") == "Email: [EMAIL]"
        assert (
            sanitizer.sanitize("Reply to support+tag@example.com for help")
            == "Reply to [EMAIL] for help"
        )

    def test_sanitize_card_numbers(self) -> None:
        """Should redact 16-digit card numbers with [CARD] placeholder."""
        sanitizer = ContextSanitizer()

        # Card with dashes
        assert sanitizer.sanitize("Card: 4532-1234-5678-9010") == "Card: [CARD]"

        # Card with spaces
        assert sanitizer.sanitize("Card: 4532 1234 5678 9010") == "Card: [CARD]"

        # Card without separators
        assert sanitizer.sanitize("Card: 4532123456789010") == "Card: [CARD]"

        # Multiple cards
        result = sanitizer.sanitize("Cards: 1234-5678-9012-3456 and 9876-5432-1098-7654")
        assert result == "Cards: [CARD] and [CARD]"

    def test_sanitize_password_patterns(self) -> None:
        """Should redact password/secret/token patterns with [REDACTED]."""
        sanitizer = ContextSanitizer()

        # Various key formats
        assert sanitizer.sanitize("password=secret123") == "password=[REDACTED]"
        assert sanitizer.sanitize("Password=MyP@ssw0rd") == "Password=[REDACTED]"
        assert sanitizer.sanitize("passwd: admin123") == "passwd=[REDACTED]"
        assert sanitizer.sanitize("pwd='test123'") == "pwd=[REDACTED]"

        # Secrets and tokens
        assert sanitizer.sanitize("secret=abc123xyz") == "secret=[REDACTED]"
        assert sanitizer.sanitize("token: bearer-token-here") == "token=[REDACTED]"
        assert sanitizer.sanitize('api_key="sk-1234567890"') == "api_key=[REDACTED]"
        assert sanitizer.sanitize("api-key='key_value'") == "api-key=[REDACTED]"
        assert sanitizer.sanitize("apikey=xyz789") == "apikey=[REDACTED]"
        assert sanitizer.sanitize("auth_key: secret") == "auth_key=[REDACTED]"
        assert sanitizer.sanitize("auth-key = value") == "auth-key=[REDACTED]"

    def test_sanitize_combined_patterns(self) -> None:
        """Should handle multiple pattern types in the same text."""
        sanitizer = ContextSanitizer()

        text = (
            "User john@doe.com with card 1234-5678-9012-3456 "
            "and password=secret123 wants to login"
        )
        expected = "User [EMAIL] with card [CARD] " "and password=[REDACTED] wants to login"
        assert sanitizer.sanitize(text) == expected

    def test_sanitize_clean_text_unchanged(self) -> None:
        """Should leave clean text without sensitive patterns unchanged."""
        sanitizer = ContextSanitizer()

        clean_texts = [
            "This is a normal sentence",
            "The user wants to process data",
            "Agent completed task successfully",
            "Results: 42 items processed",
            "Contact support for help",  # No email
            "Number: 1234",  # Not 16 digits
        ]

        for text in clean_texts:
            assert sanitizer.sanitize(text) == text

    def test_add_custom_pattern(self) -> None:
        """Should allow adding custom patterns at runtime."""
        sanitizer = ContextSanitizer()

        # Add SSN pattern
        sanitizer.add_pattern(r"\b\d{3}-\d{2}-\d{4}\b", "[SSN]")

        assert sanitizer.sanitize("SSN: 123-45-6789") == "SSN: [SSN]"
        assert sanitizer.sanitize("Invalid: 12-345-6789") == "Invalid: 12-345-6789"

    def test_add_multiple_custom_patterns(self) -> None:
        """Should support multiple custom patterns."""
        sanitizer = ContextSanitizer()

        # Add phone and SSN patterns
        sanitizer.add_pattern(r"\b\d{3}-\d{3}-\d{4}\b", "[PHONE]")
        sanitizer.add_pattern(r"\b\d{3}-\d{2}-\d{4}\b", "[SSN]")

        text = "Call 555-123-4567 or use SSN 123-45-6789"
        expected = "Call [PHONE] or use SSN [SSN]"
        assert sanitizer.sanitize(text) == expected

    def test_is_clean_detects_sensitive_data(self) -> None:
        """Should return False when text contains sensitive patterns."""
        sanitizer = ContextSanitizer()

        # Email detected
        assert sanitizer.is_clean("Contact: user@example.com") is False

        # Card detected
        assert sanitizer.is_clean("Card: 1234-5678-9012-3456") is False

        # Password detected
        assert sanitizer.is_clean("password=secret") is False
        assert sanitizer.is_clean("token: abc123") is False

    def test_is_clean_returns_true_for_safe_text(self) -> None:
        """Should return True when text contains no sensitive patterns."""
        sanitizer = ContextSanitizer()

        safe_texts = [
            "This is safe text",
            "Processing completed successfully",
            "User requested data analysis",
            "Task ID: task-12345",
            "Numbers: 42, 100, 256",
        ]

        for text in safe_texts:
            assert sanitizer.is_clean(text) is True

    def test_is_clean_with_custom_patterns(self) -> None:
        """Should detect custom patterns added at runtime."""
        sanitizer = ContextSanitizer()

        # Initially clean
        assert sanitizer.is_clean("SSN: 123-45-6789") is True

        # Add pattern and recheck
        sanitizer.add_pattern(r"\b\d{3}-\d{2}-\d{4}\b", "[SSN]")
        assert sanitizer.is_clean("SSN: 123-45-6789") is False

    def test_edge_cases(self) -> None:
        """Should handle edge cases gracefully."""
        sanitizer = ContextSanitizer()

        # Empty string
        assert sanitizer.sanitize("") == ""
        assert sanitizer.is_clean("") is True

        # Whitespace only
        assert sanitizer.sanitize("   ") == "   "
        assert sanitizer.is_clean("   ") is True

        # Special characters
        text = "Special: !@#$%^&*()"
        assert sanitizer.sanitize(text) == text
        assert sanitizer.is_clean(text) is True

    def test_partial_matches_not_over_sanitized(self) -> None:
        """Should not over-match partial patterns."""
        sanitizer = ContextSanitizer()

        # Incomplete card number
        assert sanitizer.sanitize("Card: 1234-5678-9012") == "Card: 1234-5678-9012"

        # Text containing "password" but not a pattern
        assert sanitizer.sanitize("Reset your password") == "Reset your password"

        # Domain without @ is not an email
        assert sanitizer.sanitize("Visit example.com") == "Visit example.com"

    def test_case_insensitive_password_patterns(self) -> None:
        """Should detect password patterns regardless of case."""
        sanitizer = ContextSanitizer()

        patterns = [
            "PASSWORD=secret",
            "Password=secret",
            "password=secret",
            "SECRET=value",
            "Secret=value",
            "secret=value",
            "TOKEN=abc",
            "Token=abc",
            "token=abc",
        ]

        for pattern in patterns:
            result = sanitizer.sanitize(pattern)
            assert "[REDACTED]" in result

    def test_pattern_compilation_at_init(self) -> None:
        """Should pre-compile patterns at initialization for performance."""
        sanitizer = ContextSanitizer()

        # Verify patterns are compiled
        assert len(sanitizer._patterns) > 0
        for pattern, _ in sanitizer._patterns:
            assert hasattr(pattern, "search")
            assert hasattr(pattern, "sub")

    def test_realistic_context_sanitization(self) -> None:
        """Should handle realistic agent context data."""
        sanitizer = ContextSanitizer()

        # Realistic agent handoff context
        context = """
        User requested account information.
        Email: customer@company.com
        Card on file: 4532-1234-5678-9010
        Auth token: bearer-abc123xyz
        Next step: Process refund request
        """

        result = sanitizer.sanitize(context)

        # Verify all sensitive data is redacted
        assert "customer@company.com" not in result
        assert "[EMAIL]" in result
        assert "4532-1234-5678-9010" not in result
        assert "[CARD]" in result
        assert "bearer-abc123xyz" not in result
        assert "[REDACTED]" in result

        # Verify non-sensitive data is preserved
        assert "User requested account information" in result
        assert "Next step: Process refund request" in result
