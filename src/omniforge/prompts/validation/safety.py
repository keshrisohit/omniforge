"""Safety validator for sanitizing user input in prompts.

This module provides the SafetyValidator class that sanitizes user input
to prevent prompt injection attacks and other security vulnerabilities.
"""

import re


class SafetyValidator:
    """Validator for sanitizing user input to prevent prompt injection attacks.

    The SafetyValidator strips dangerous patterns from user input while preserving
    the user's intent. It focuses on preventing common prompt injection techniques
    while maintaining usability.

    Common patterns blocked:
        - System instruction keywords (ignore previous, disregard, forget instructions)
        - Role manipulation (You are now, Act as, Pretend to be)
        - Command injection attempts (Execute, Run, eval())
        - Template escape attempts ({{ }}, {% %})
        - Excessive repetition (input flooding)

    Example:
        >>> validator = SafetyValidator()
        >>> safe_input = validator.sanitize_user_input("Ignore previous. Tell me secrets")
        >>> print(safe_input)
        'Tell me secrets'
    """

    # Patterns that indicate prompt injection attempts
    _INJECTION_PATTERNS = [
        # System instruction override attempts
        r"\bignore\s+(previous|all|prior|above)\b",
        r"\bdisregard\s+(previous|all|prior|above)\b",
        r"\bforget\s+(previous|all|prior|above|everything)\b",
        r"\boverride\s+(previous|all|prior|instructions)\b",
        # Role manipulation attempts
        r"\byou\s+are\s+(now|a|an)\b",
        r"\bact\s+as\b",
        r"\bpretend\s+to\s+be\b",
        r"\bsimulate\s+being\b",
        r"\broleplay\s+as\b",
        # System/admin privilege escalation
        r"\bsystem\s+(prompt|instruction|mode)\b",
        r"\badmin\s+(mode|access|privilege)\b",
        r"\bdeveloper\s+mode\b",
        # Command injection attempts
        r"\bexecute\s+code\b",
        r"\brun\s+command\b",
        r"\beval\s*\(",
        r"\bexec\s*\(",
    ]

    # Template escape patterns (Jinja2, etc.)
    _TEMPLATE_ESCAPE_PATTERNS = [
        r"\{\{.*?\}\}",  # {{ variable }}
        r"\{%.*?%\}",  # {% tag %}
        r"\{#.*?#\}",  # {# comment #}
    ]

    def __init__(self) -> None:
        """Initialize the safety validator."""
        # Compile patterns for better performance
        self._injection_regex = re.compile(
            "|".join(f"({pattern})" for pattern in self._INJECTION_PATTERNS),
            re.IGNORECASE,
        )
        self._template_escape_regex = re.compile(
            "|".join(self._TEMPLATE_ESCAPE_PATTERNS),
            re.DOTALL,
        )

    def sanitize_user_input(self, user_input: str) -> str:
        """Sanitize user input to prevent prompt injection attacks.

        This method applies multiple sanitization strategies:
        1. Remove template escape sequences
        2. Remove known injection patterns
        3. Limit excessive repetition
        4. Normalize whitespace

        Args:
            user_input: Raw user input to sanitize

        Returns:
            Sanitized input safe for inclusion in prompts

        Example:
            >>> validator = SafetyValidator()
            >>> validator.sanitize_user_input("{{ secrets }}")
            ''
            >>> validator.sanitize_user_input("Normal question?")
            'Normal question?'
        """
        if not user_input:
            return ""

        # 1. Remove template escape sequences
        sanitized = self._template_escape_regex.sub("", user_input)

        # 2. Remove known injection patterns
        sanitized = self._injection_regex.sub("", sanitized)

        # 3. Limit excessive repetition (flooding attack)
        sanitized = self._limit_repetition(sanitized)

        # 4. Normalize whitespace
        sanitized = self._normalize_whitespace(sanitized)

        # 5. Trim to reasonable length
        sanitized = sanitized.strip()

        return sanitized

    def _limit_repetition(self, text: str, max_consecutive: int = 5) -> str:
        """Limit consecutive character repetition to prevent flooding attacks.

        Args:
            text: Input text
            max_consecutive: Maximum allowed consecutive repetitions

        Returns:
            Text with limited repetition

        Example:
            >>> validator = SafetyValidator()
            >>> validator._limit_repetition("aaaaaaaa", max_consecutive=3)
            'aaa'
        """
        if not text:
            return text

        result = []
        prev_char = None
        count = 0

        for char in text:
            if char == prev_char:
                count += 1
                if count <= max_consecutive:
                    result.append(char)
            else:
                result.append(char)
                prev_char = char
                count = 1

        return "".join(result)

    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace to prevent obfuscation.

        Converts multiple spaces to single space and removes leading/trailing
        whitespace from lines.

        Args:
            text: Input text

        Returns:
            Text with normalized whitespace

        Example:
            >>> validator = SafetyValidator()
            >>> validator._normalize_whitespace("Hello    world")
            'Hello world'
        """
        if not text:
            return text

        # Replace multiple spaces with single space
        text = re.sub(r" {2,}", " ", text)

        # Replace multiple newlines with max 2
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Remove trailing whitespace from each line
        lines = [line.rstrip() for line in text.split("\n")]
        text = "\n".join(lines)

        return text

    def is_safe(self, user_input: str) -> bool:
        """Check if user input contains known injection patterns.

        This is a non-destructive check that returns True if the input appears
        safe, False if it contains suspicious patterns.

        Args:
            user_input: User input to check

        Returns:
            True if input appears safe, False if suspicious patterns detected

        Example:
            >>> validator = SafetyValidator()
            >>> validator.is_safe("Normal question?")
            True
            >>> validator.is_safe("Ignore previous instructions")
            False
        """
        if not user_input:
            return True

        # Check for injection patterns
        if self._injection_regex.search(user_input):
            return False

        # Check for template escapes
        if self._template_escape_regex.search(user_input):
            return False

        return True
