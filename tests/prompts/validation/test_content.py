"""Tests for content validation."""

import pytest

from omniforge.prompts.enums import ValidationSeverity
from omniforge.prompts.validation.content import ContentRules, ContentValidator, ValidationResult


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_validation_result_creation(self) -> None:
        """ValidationResult should initialize with all fields."""
        result = ValidationResult(
            is_valid=False,
            severity=ValidationSeverity.ERROR,
            message="Test error",
            location="line 5",
        )

        assert result.is_valid is False
        assert result.severity == ValidationSeverity.ERROR
        assert result.message == "Test error"
        assert result.location == "line 5"

    def test_validation_result_without_location(self) -> None:
        """ValidationResult location should be optional."""
        result = ValidationResult(
            is_valid=True, severity=ValidationSeverity.INFO, message="Success"
        )

        assert result.is_valid is True
        assert result.location is None


class TestContentRules:
    """Tests for ContentRules dataclass."""

    def test_content_rules_defaults(self) -> None:
        """ContentRules should have sensible defaults."""
        rules = ContentRules()

        assert rules.max_length == 100000
        assert rules.min_length == 1
        assert rules.prohibited_patterns == []
        assert rules.required_patterns == []

    def test_content_rules_custom_values(self) -> None:
        """ContentRules should accept custom values."""
        rules = ContentRules(
            max_length=1000,
            min_length=10,
            prohibited_patterns=[r"\bpassword\b"],
            required_patterns=[r"\buser\b"],
        )

        assert rules.max_length == 1000
        assert rules.min_length == 10
        assert len(rules.prohibited_patterns) == 1
        assert len(rules.required_patterns) == 1


class TestContentValidator:
    """Tests for ContentValidator class."""

    def test_validate_with_valid_content(self) -> None:
        """Validator should return empty list for valid content."""
        validator = ContentValidator()
        results = validator.validate("This is valid content")

        assert results == []

    def test_validate_with_default_rules(self) -> None:
        """Validator should use default rules when none provided."""
        validator = ContentValidator()
        results = validator.validate("Valid content")

        # Should pass with default rules
        assert results == []

    def test_validate_content_too_short(self) -> None:
        """Validator should detect content below minimum length."""
        validator = ContentValidator()
        rules = ContentRules(min_length=10)
        results = validator.validate("Short", rules)

        assert len(results) == 1
        assert not results[0].is_valid
        assert results[0].severity == ValidationSeverity.ERROR
        assert "below minimum" in results[0].message
        assert "length=5" in results[0].location

    def test_validate_content_too_long(self) -> None:
        """Validator should detect content exceeding maximum length."""
        validator = ContentValidator()
        rules = ContentRules(max_length=10)
        content = "This content is way too long"
        results = validator.validate(content, rules)

        assert len(results) == 1
        assert not results[0].is_valid
        assert results[0].severity == ValidationSeverity.ERROR
        assert "exceeds maximum" in results[0].message

    def test_validate_empty_content_with_min_length(self) -> None:
        """Validator should detect empty content."""
        validator = ContentValidator()
        rules = ContentRules(min_length=1)
        results = validator.validate("", rules)

        assert len(results) == 1
        assert not results[0].is_valid
        assert "below minimum" in results[0].message

    def test_validate_prohibited_pattern_found(self) -> None:
        """Validator should detect prohibited patterns."""
        validator = ContentValidator()
        rules = ContentRules(prohibited_patterns=[r"\bpassword\b", r"\bsecret\b"])
        results = validator.validate("My password is secret", rules)

        # Should find both patterns
        assert len(results) == 2
        assert all(not r.is_valid for r in results)
        assert all(r.severity == ValidationSeverity.ERROR for r in results)

    def test_validate_prohibited_pattern_case_insensitive(self) -> None:
        """Validator should detect prohibited patterns case-insensitively."""
        validator = ContentValidator()
        rules = ContentRules(prohibited_patterns=[r"\bPASSWORD\b"])
        results = validator.validate("My password is safe", rules)

        assert len(results) == 1
        assert not results[0].is_valid
        assert "password" in results[0].message.lower()

    def test_validate_prohibited_pattern_with_line_number(self) -> None:
        """Validator should report line number for prohibited patterns."""
        validator = ContentValidator()
        rules = ContentRules(prohibited_patterns=[r"\bsecret\b"])
        content = "Line 1\nLine 2\nMy secret here\nLine 4"
        results = validator.validate(content, rules)

        assert len(results) == 1
        assert "line 3" in results[0].location

    def test_validate_invalid_prohibited_pattern_regex(self) -> None:
        """Validator should handle invalid regex patterns."""
        validator = ContentValidator()
        rules = ContentRules(prohibited_patterns=[r"[invalid("])
        results = validator.validate("Some content", rules)

        assert len(results) == 1
        assert not results[0].is_valid
        assert "Invalid prohibited pattern regex" in results[0].message

    def test_validate_required_pattern_found(self) -> None:
        """Validator should pass when required pattern is present."""
        validator = ContentValidator()
        rules = ContentRules(required_patterns=[r"\buser\b"])
        results = validator.validate("The user is logged in", rules)

        # No errors since required pattern is found
        assert results == []

    def test_validate_required_pattern_missing(self) -> None:
        """Validator should detect missing required patterns."""
        validator = ContentValidator()
        rules = ContentRules(required_patterns=[r"\buser\b", r"\blogin\b"])
        results = validator.validate("Some content without patterns", rules)

        assert len(results) == 2
        assert all(not r.is_valid for r in results)
        assert all(r.severity == ValidationSeverity.WARNING for r in results)

    def test_validate_required_pattern_case_insensitive(self) -> None:
        """Validator should detect required patterns case-insensitively."""
        validator = ContentValidator()
        rules = ContentRules(required_patterns=[r"\bUSER\b"])
        results = validator.validate("The user is here", rules)

        # Should find pattern despite case difference
        assert results == []

    def test_validate_invalid_required_pattern_regex(self) -> None:
        """Validator should handle invalid required pattern regex."""
        validator = ContentValidator()
        rules = ContentRules(required_patterns=[r"[invalid("])
        results = validator.validate("Some content", rules)

        assert len(results) == 1
        assert not results[0].is_valid
        assert "Invalid required pattern regex" in results[0].message

    def test_validate_injection_script_tag(self) -> None:
        """Validator should detect script tag injection."""
        validator = ContentValidator()
        content = "Hello <script>alert('xss')</script> world"
        results = validator.validate(content)

        assert len(results) == 1
        assert not results[0].is_valid
        assert results[0].severity == ValidationSeverity.WARNING
        assert "injection vulnerability" in results[0].message.lower()

    def test_validate_injection_javascript_protocol(self) -> None:
        """Validator should detect javascript: protocol."""
        validator = ContentValidator()
        content = "Click <a href='javascript:void(0)'>here</a>"
        results = validator.validate(content)

        assert len(results) == 1
        assert "injection vulnerability" in results[0].message.lower()

    def test_validate_injection_event_handler(self) -> None:
        """Validator should detect event handler attributes."""
        validator = ContentValidator()
        content = "<div onclick='malicious()'>Click me</div>"
        results = validator.validate(content)

        assert len(results) == 1
        assert "injection vulnerability" in results[0].message.lower()

    def test_validate_injection_iframe(self) -> None:
        """Validator should detect iframe tags."""
        validator = ContentValidator()
        content = "Embed: <iframe src='evil.com'></iframe>"
        results = validator.validate(content)

        assert len(results) == 1
        assert "injection vulnerability" in results[0].message.lower()

    def test_validate_injection_eval_function(self) -> None:
        """Validator should detect eval() function calls."""
        validator = ContentValidator()
        content = "Code: eval('malicious')"
        results = validator.validate(content)

        assert len(results) == 1
        assert "injection vulnerability" in results[0].message.lower()

    def test_validate_injection_with_line_number(self) -> None:
        """Validator should report line number for injection patterns."""
        validator = ContentValidator()
        content = "Line 1\nLine 2\n<script>bad</script>\nLine 4"
        results = validator.validate(content)

        assert len(results) == 1
        assert "line 3" in results[0].location

    def test_validate_multiple_issues(self) -> None:
        """Validator should detect multiple validation issues."""
        validator = ContentValidator()
        rules = ContentRules(
            max_length=50,
            prohibited_patterns=[r"\bpassword\b"],
            required_patterns=[r"\buser\b"],
        )
        content = "This has password and is very very very very very long content here"
        results = validator.validate(content, rules)

        # Should have: too long, prohibited pattern, missing required pattern
        assert len(results) == 3
        error_messages = [r.message for r in results]
        assert any("exceeds maximum" in msg for msg in error_messages)
        assert any("Prohibited pattern" in msg for msg in error_messages)
        assert any("Required pattern" in msg for msg in error_messages)

    def test_validate_no_issues_returns_empty_list(self) -> None:
        """Validator should return empty list when all checks pass."""
        validator = ContentValidator()
        rules = ContentRules(
            min_length=5,
            max_length=100,
            prohibited_patterns=[r"\bpassword\b"],
            required_patterns=[r"\buser\b"],
        )
        content = "The user has valid content"
        results = validator.validate(content, rules)

        assert results == []

    def test_validate_unicode_content(self) -> None:
        """Validator should handle unicode content correctly."""
        validator = ContentValidator()
        rules = ContentRules(min_length=5, max_length=100)
        content = "Hello 世界 🌍"
        results = validator.validate(content, rules)

        # Should validate without errors
        assert results == []

    def test_validate_multiline_content(self) -> None:
        """Validator should handle multiline content correctly."""
        validator = ContentValidator()
        rules = ContentRules(
            prohibited_patterns=[r"\bsecret\b"], required_patterns=[r"\buser\b"]
        )
        content = """Line 1: introduction
        Line 2: user information
        Line 3: more content
        Line 4: conclusion"""
        results = validator.validate(content, rules)

        # Should find required pattern across multiple lines
        assert results == []

    def test_validator_initialization(self) -> None:
        """ContentValidator should initialize without errors."""
        validator = ContentValidator()
        assert validator is not None
