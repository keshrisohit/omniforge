"""Content validation for prompt templates.

This module provides validation for prompt content including length limits,
prohibited patterns, required patterns, and injection vulnerability detection.
"""

import re
from dataclasses import dataclass, field
from typing import Optional

from omniforge.prompts.enums import ValidationSeverity


@dataclass
class ValidationResult:
    """Result of a validation check.

    Attributes:
        is_valid: Whether the validation passed
        severity: Severity level of the validation issue
        message: Human-readable description of the issue
        location: Optional location information (e.g., line number, pattern match)
    """

    is_valid: bool
    severity: ValidationSeverity
    message: str
    location: Optional[str] = None


@dataclass
class ContentRules:
    """Configuration for content validation rules.

    Attributes:
        max_length: Maximum allowed content length in characters
        min_length: Minimum required content length in characters
        prohibited_patterns: List of regex patterns that should not appear in content
        required_patterns: List of regex patterns that must appear in content
    """

    max_length: int = 100000
    min_length: int = 1
    prohibited_patterns: list[str] = field(default_factory=list)
    required_patterns: list[str] = field(default_factory=list)


class ContentValidator:
    """Validator for prompt content.

    This validator checks content against configurable rules including
    length constraints, prohibited patterns, required patterns, and
    potential injection vulnerabilities.

    Example:
        >>> rules = ContentRules(max_length=1000, prohibited_patterns=[r'\\b(password|secret)\\b'])
        >>> validator = ContentValidator()
        >>> results = validator.validate("My secret is safe", rules)
        >>> any(not r.is_valid for r in results)
        True
    """

    # Common injection patterns to detect
    INJECTION_PATTERNS = [
        r"<script[^>]*>.*?</script>",  # Script tags
        r"javascript:",  # JavaScript protocol
        r"on\w+\s*=",  # Event handlers (onclick, onload, etc.)
        r"<iframe[^>]*>",  # Iframe tags
        r"eval\s*\(",  # Eval function calls
        r"exec\s*\(",  # Exec function calls
    ]

    def __init__(self) -> None:
        """Initialize content validator."""
        pass

    def validate(
        self, content: str, rules: Optional[ContentRules] = None
    ) -> list[ValidationResult]:
        """Validate content against specified rules.

        Args:
            content: The content to validate
            rules: Optional validation rules (uses defaults if not provided)

        Returns:
            List of validation results (empty list if all checks pass)

        Example:
            >>> validator = ContentValidator()
            >>> results = validator.validate("Hello world")
            >>> all(r.is_valid for r in results)
            True
        """
        if rules is None:
            rules = ContentRules()

        results: list[ValidationResult] = []

        # Check length constraints
        results.extend(self._check_length(content, rules))

        # Check prohibited patterns
        results.extend(self._check_prohibited_patterns(content, rules))

        # Check required patterns
        results.extend(self._check_required_patterns(content, rules))

        # Check for injection vulnerabilities
        results.extend(self._check_injection_vulnerabilities(content))

        return results

    def _check_length(self, content: str, rules: ContentRules) -> list[ValidationResult]:
        """Check if content meets length constraints.

        Args:
            content: Content to check
            rules: Validation rules with length constraints

        Returns:
            List of validation results for length checks
        """
        results: list[ValidationResult] = []
        content_length = len(content)

        if content_length < rules.min_length:
            results.append(
                ValidationResult(
                    is_valid=False,
                    severity=ValidationSeverity.ERROR,
                    message=(
                        f"Content length {content_length} is below minimum "
                        f"required length {rules.min_length}"
                    ),
                    location=f"length={content_length}",
                )
            )

        if content_length > rules.max_length:
            results.append(
                ValidationResult(
                    is_valid=False,
                    severity=ValidationSeverity.ERROR,
                    message=(
                        f"Content length {content_length} exceeds maximum "
                        f"allowed length {rules.max_length}"
                    ),
                    location=f"length={content_length}",
                )
            )

        return results

    def _check_prohibited_patterns(
        self, content: str, rules: ContentRules
    ) -> list[ValidationResult]:
        """Check if content contains prohibited patterns.

        Args:
            content: Content to check
            rules: Validation rules with prohibited patterns

        Returns:
            List of validation results for prohibited pattern checks
        """
        results: list[ValidationResult] = []

        for pattern in rules.prohibited_patterns:
            try:
                matches = list(re.finditer(pattern, content, re.IGNORECASE))
                if matches:
                    # Get first match for location info
                    first_match = matches[0]
                    match_text = first_match.group(0)

                    # Find line number
                    line_num = content[: first_match.start()].count("\n") + 1

                    results.append(
                        ValidationResult(
                            is_valid=False,
                            severity=ValidationSeverity.ERROR,
                            message=(
                                f"Prohibited pattern found: '{match_text}' " f"(pattern: {pattern})"
                            ),
                            location=f"line {line_num}",
                        )
                    )
            except re.error as e:
                results.append(
                    ValidationResult(
                        is_valid=False,
                        severity=ValidationSeverity.ERROR,
                        message=f"Invalid prohibited pattern regex: {pattern} ({str(e)})",
                        location=None,
                    )
                )

        return results

    def _check_required_patterns(self, content: str, rules: ContentRules) -> list[ValidationResult]:
        """Check if content contains required patterns.

        Args:
            content: Content to check
            rules: Validation rules with required patterns

        Returns:
            List of validation results for required pattern checks
        """
        results: list[ValidationResult] = []

        for pattern in rules.required_patterns:
            try:
                if not re.search(pattern, content, re.IGNORECASE):
                    results.append(
                        ValidationResult(
                            is_valid=False,
                            severity=ValidationSeverity.WARNING,
                            message=f"Required pattern not found: {pattern}",
                            location=None,
                        )
                    )
            except re.error as e:
                results.append(
                    ValidationResult(
                        is_valid=False,
                        severity=ValidationSeverity.ERROR,
                        message=f"Invalid required pattern regex: {pattern} ({str(e)})",
                        location=None,
                    )
                )

        return results

    def _check_injection_vulnerabilities(self, content: str) -> list[ValidationResult]:
        """Check for potential injection vulnerabilities.

        Args:
            content: Content to check for injection patterns

        Returns:
            List of validation results for injection vulnerability checks
        """
        results: list[ValidationResult] = []

        for pattern in self.INJECTION_PATTERNS:
            matches = list(re.finditer(pattern, content, re.IGNORECASE))
            if matches:
                first_match = matches[0]
                match_text = first_match.group(0)
                line_num = content[: first_match.start()].count("\n") + 1

                results.append(
                    ValidationResult(
                        is_valid=False,
                        severity=ValidationSeverity.WARNING,
                        message=(
                            f"Potential injection vulnerability detected: '{match_text}' "
                            f"This pattern may pose a security risk."
                        ),
                        location=f"line {line_num}",
                    )
                )

        return results
