"""Skill validator for Anthropic Agent Skills specification compliance.

This module validates generated SKILL.md content against official Anthropic
Agent Skills specifications, ensuring strict compliance with frontmatter fields,
name format, description format, and body length constraints.
"""

import re
from typing import Any, Optional

import yaml  # type: ignore

from omniforge.skills.creation.models import ValidationResult


class SkillValidator:
    """Validate SKILL.md content against official Anthropic specification.

    Validation Rules (from official docs):
    1. Frontmatter has ONLY `name` and `description` fields
    2. Name: max 64 chars, lowercase letters/numbers/hyphens, starts with letter
    3. Description: non-empty, max 1024 chars, third person
    4. Body: under 500 lines
    5. No time-sensitive information (warning only)

    Attributes:
        FRONTMATTER_PATTERN: Regex pattern for matching YAML frontmatter
        NAME_PATTERN: Regex pattern for valid skill names
        RESERVED_NAMES: Set of reserved skill names
        IMPERATIVE_STARTS: List of imperative verb starts (for third person check)
        TIME_SENSITIVE_PATTERNS: List of patterns indicating time-sensitive content
    """

    # Pattern to extract YAML frontmatter
    FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.MULTILINE | re.DOTALL)

    # Name validation pattern (kebab-case)
    NAME_PATTERN = re.compile(r"^[a-z][a-z0-9-]*$")

    # Reserved skill names
    RESERVED_NAMES = {"skill", "agent", "tool", "system", "admin", "root"}

    # Imperative verb starts (indicates non-third person description)
    IMPERATIVE_STARTS = [
        "format",
        "create",
        "build",
        "process",
        "handle",
        "generate",
        "convert",
        "extract",
        "analyze",
        "transform",
        "validate",
        "parse",
        "execute",
        "run",
        "compile",
        "deploy",
    ]

    # Time-sensitive content patterns
    TIME_SENSITIVE_PATTERNS = [
        r"\b20\d{2}\b",  # Years like 2024
        r"\bcurrently\b",
        r"\bas of\b",
        r"\btoday\b",
        r"\bnow\b",
        r"\brecent\b",
        r"\blatest\b",
        r"\bthis (year|month|week)\b",
    ]

    def __init__(self) -> None:
        """Initialize the SkillValidator."""
        pass

    def validate(self, content: str, skill_name: str) -> ValidationResult:
        """Validate SKILL.md content string against official spec.

        Args:
            content: The SKILL.md file content to validate
            skill_name: The expected skill name for validation

        Returns:
            ValidationResult with errors and warnings
        """
        result = ValidationResult(is_valid=True)

        # Step 1: Parse YAML frontmatter
        frontmatter_dict, body = self._parse_frontmatter(content, result)
        if not frontmatter_dict:
            return result  # Parse error already added

        # Step 2: Validate frontmatter fields (STRICT: only name and description)
        field_errors = self.validate_frontmatter_fields(frontmatter_dict)
        for error in field_errors:
            result.add_error(error)

        # Step 3: Validate name
        name = frontmatter_dict.get("name", "")
        if not name:
            result.add_error("Frontmatter missing required field: 'name'")
        else:
            name_errors = self.validate_name(name)
            for error in name_errors:
                result.add_error(error)

            # Verify name matches expected
            if name != skill_name:
                result.add_error(
                    f"Frontmatter name '{name}' does not match expected name '{skill_name}'"
                )

        # Step 4: Validate description
        description = frontmatter_dict.get("description", "")
        if not description:
            result.add_error("Frontmatter missing required field: 'description'")
        else:
            desc_errors = self.validate_description(description)
            for error in desc_errors:
                result.add_error(error)

        # Step 4a: Validate allowed-tools if present
        allowed_tools = frontmatter_dict.get("allowed-tools", "")
        if allowed_tools:
            tool_errors = self.validate_allowed_tools(allowed_tools)
            for error in tool_errors:
                result.add_error(error)

        # Step 5: Validate body
        if body:
            body_errors = self.validate_body_length(body)
            for error in body_errors:
                result.add_error(error)

            # Step 5a: Validate word count (5,000 word limit)
            word_count_result = self.validate_word_count(body)
            for error in word_count_result.get("errors", []):
                result.add_error(error)
            for warning in word_count_result.get("warnings", []):
                result.add_warning(warning)

            # Step 6: Check for hardcoded paths (critical for portability)
            path_errors = self.check_hardcoded_paths(content)
            for error in path_errors:
                result.add_error(error)

            # Step 7: Check for time-sensitive content (warnings only)
            time_warnings = self.check_time_sensitive_content(content)
            for warning in time_warnings:
                result.add_warning(warning)

            # Step 8: Check for broken single-quoted strings (apostrophe inside single quotes)
            quote_errors = self.check_broken_single_quotes(body)
            for error in quote_errors:
                result.add_error(error)
        else:
            result.add_error("Skill body is empty. Body must contain skill instructions.")

        return result

    def validate_frontmatter_fields(self, frontmatter: dict[str, Any]) -> list[str]:
        """Validate frontmatter fields.

        Per Anthropic spec, required fields are:
        - name (required)
        - description (required)

        Optional but recommended fields:
        - allowed-tools (critical for security)
        - license, version, model, mode (optional)

        Args:
            frontmatter: Parsed frontmatter dictionary

        Returns:
            List of validation errors
        """
        errors: list[str] = []

        # Required fields
        required_fields = {"name", "description"}

        # Optional fields per Anthropic spec
        optional_fields = {
            "allowed-tools",
            "license",
            "version",
            "model",
            "mode",
            "disable-model-invocation",
        }

        allowed_fields = required_fields | optional_fields
        actual_fields = set(frontmatter.keys())

        # Check for unauthorized fields
        unauthorized_fields = actual_fields - allowed_fields
        if unauthorized_fields:
            errors.append(
                f"Frontmatter contains unauthorized fields: {sorted(unauthorized_fields)}. "
                f"Allowed fields: {sorted(allowed_fields)}"
            )

        # Check for missing required fields
        missing_fields = required_fields - actual_fields
        if missing_fields:
            errors.append(
                f"Frontmatter missing required fields: {sorted(missing_fields)}. "
                f"Both 'name' and 'description' are required."
            )

        return errors

    def validate_name(self, name: str) -> list[str]:
        """Validate name against official requirements.

        Per Anthropic spec:
        - Max 64 characters
        - Lowercase letters, numbers, and hyphens only
        - Must start with a lowercase letter
        - Cannot be a reserved word

        Args:
            name: The skill name to validate

        Returns:
            List of validation errors
        """
        errors: list[str] = []

        # Check length
        if len(name) > 64:
            errors.append(f"Skill name exceeds 64 character limit (got {len(name)} characters)")

        # Check pattern (kebab-case)
        if not self.NAME_PATTERN.match(name):
            errors.append(
                "Skill name must be kebab-case: start with lowercase letter, "
                "contain only lowercase letters, numbers, and hyphens"
            )

        # Check reserved names
        if name.lower() in self.RESERVED_NAMES:
            errors.append(
                f"Skill name '{name}' is reserved. "
                f"Reserved names: {sorted(self.RESERVED_NAMES)}"
            )

        return errors

    def validate_description(self, description: str) -> list[str]:
        """Validate description against official requirements.

        Per Anthropic spec:
        - Non-empty
        - Max 1024 characters
        - Should be third person (not imperative form)
        - Should include WHEN/trigger context

        Args:
            description: The skill description to validate

        Returns:
            List of validation errors
        """
        errors: list[str] = []

        # Check length
        if len(description) > 1024:
            errors.append(
                f"Description exceeds 1024 character limit (got {len(description)} characters)"
            )

        # Check for imperative form (third person heuristic)
        first_word = description.strip().split()[0].lower() if description.strip() else ""
        if first_word in self.IMPERATIVE_STARTS:
            errors.append(
                f"Description appears to be in imperative form (starts with '{first_word}'). "
                "Use third person instead (e.g., 'Formats...' -> 'A skill that formats...')"
            )

        return errors

    def validate_body_length(self, body: str) -> list[str]:
        """Validate body is under 500 lines.

        Per Anthropic spec, skill bodies should be concise and under 500 lines.

        Args:
            body: The skill body content

        Returns:
            List of validation errors
        """
        errors: list[str] = []

        lines = body.split("\n")
        line_count = len(lines)

        if line_count > 500:
            errors.append(
                f"Skill body exceeds 500 line limit (got {line_count} lines). "
                "Consider breaking into multiple skills or condensing content."
            )

        return errors

    def validate_word_count(self, body: str) -> dict[str, list[str]]:
        """Validate body word count is under 5,000 words.

        Per Anthropic spec and best practices, skill bodies should be concise.
        The 5,000 word limit ensures skills remain focused and don't overwhelm
        the model's context window.

        Args:
            body: The skill body content

        Returns:
            Dictionary with 'errors' and 'warnings' lists
        """
        errors: list[str] = []
        warnings: list[str] = []

        # Count words (split on whitespace)
        words = body.split()
        word_count = len(words)

        # Hard limit: 5,000 words
        if word_count > 5000:
            errors.append(
                f"Skill body exceeds 5,000 word limit (got {word_count} words). "
                "Consider moving detailed content to references/ directory for progressive disclosure."
            )
        # Warning threshold: 90% of limit (4,500 words)
        elif word_count > 4500:
            warnings.append(
                f"Skill body approaching 5,000 word limit (currently {word_count} words). "
                "Consider condensing content or moving details to references/ directory."
            )

        return {"errors": errors, "warnings": warnings}

    def validate_allowed_tools(self, allowed_tools: str) -> list[str]:
        """Validate allowed-tools format and syntax.

        Per Anthropic spec, allowed-tools should be a comma-separated list of:
        - Tool names: "Read", "Write", "Grep"
        - Scoped tools with wildcards: "Bash(git:*)", "Bash(python {baseDir}/scripts/*:*)"

        Args:
            allowed_tools: The allowed-tools string from frontmatter

        Returns:
            List of validation errors
        """
        errors: list[str] = []

        if not allowed_tools or not isinstance(allowed_tools, str):
            return errors  # Empty or missing is valid (optional field)

        # Split by comma and trim whitespace
        tools = [tool.strip() for tool in allowed_tools.split(",")]

        valid_tool_names = {
            "Read",
            "Write",
            "Edit",
            "Grep",
            "Glob",
            "Bash",
            "Task",
            "WebSearch",
            "WebFetch",
        }

        # Pattern for scoped Bash commands: Bash(command:*) or Bash(command {baseDir}/path:*)
        bash_scope_pattern = re.compile(r"^Bash\([^)]+:\*\)$")

        for tool in tools:
            if not tool:
                continue  # Skip empty entries

            # Check if it's a simple tool name
            if tool in valid_tool_names:
                continue

            # Check if it's a scoped Bash command
            if bash_scope_pattern.match(tool):
                # Validate it uses {baseDir} for paths if it contains a path
                if "/" in tool and "{baseDir}" not in tool:
                    errors.append(
                        f"Scoped tool '{tool}' should use {{baseDir}} placeholder for paths"
                    )
                continue

            # Unknown tool format
            errors.append(
                f"Invalid tool specification: '{tool}'. "
                f"Must be a valid tool name ({', '.join(sorted(valid_tool_names))}) "
                "or scoped Bash command like 'Bash(git:*)'"
            )

        return errors

    def check_hardcoded_paths(self, content: str) -> list[str]:
        """Detect hardcoded absolute paths that should use {baseDir}.

        Skills must be portable across environments. Hardcoded paths break portability.

        Args:
            content: The full SKILL.md content to check

        Returns:
            List of validation errors for hardcoded paths
        """
        errors: list[str] = []

        # Patterns for absolute paths
        path_patterns = [
            (r"/home/[^\s]+", "Unix home directory"),
            (r"/Users/[^\s]+", "Mac home directory"),
            (r"C:\\[^\s]+", "Windows absolute path"),
            (r"/(?:usr|var|opt|etc)/[^\s]+", "Unix system path"),
            # Look for paths without {{baseDir}} to scripts, references, assets
            # The pattern checks that /scripts/, /references/, or /assets/ is NOT preceded by a }
            # which would indicate it's part of {{baseDir}}/scripts/
            (
                r"(?<!})/(?:scripts|references|assets)/[^\s]+",
                "skill resource path without {baseDir}",
            ),
        ]

        for pattern, description in path_patterns:
            matches = re.findall(pattern, content)
            if matches:
                # Take first few matches as examples
                examples = matches[:3]
                errors.append(
                    f"Hardcoded {description} detected: {', '.join(examples)}. "
                    "Use {{baseDir}} placeholder for portability (e.g., {{baseDir}}/scripts/file.py)"
                )

        return errors

    def check_broken_single_quotes(self, body: str) -> list[str]:
        """Detect single-quoted strings that contain apostrophes, causing parse errors.

        A pattern like ``'I'd like...'`` is ambiguous — the parser sees an empty string
        ``''`` followed by orphaned text. This happens in generated examples when the LLM
        uses single quotes around text that contains contractions (I'd, can't, won't, etc.).

        Args:
            body: The skill body content

        Returns:
            List of validation errors, one per offending line
        """
        errors: list[str] = []
        # Contractions / possessives that break single-quoted strings
        contraction_pattern = re.compile(r"'[^']*\b\w+'[tdslmre]\b[^']*'")

        for i, line in enumerate(body.splitlines(), start=1):
            if contraction_pattern.search(line):
                errors.append(
                    f"Line {i}: single-quoted string contains an apostrophe/contraction "
                    f"which breaks string parsing. Use double quotes for strings that "
                    f"contain apostrophes (e.g., \"I'd\" instead of 'I\\'d')."
                )

        return errors

    def check_time_sensitive_content(self, content: str) -> list[str]:
        """Warn about time-sensitive information (warning only).

        Time-sensitive content (dates, years, "currently", etc.) can become
        outdated and should be avoided in skill definitions.

        Args:
            content: The full SKILL.md content to check

        Returns:
            List of validation warnings
        """
        warnings: list[str] = []

        for pattern in self.TIME_SENSITIVE_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                warnings.append(
                    f"Content may contain time-sensitive information (pattern: '{pattern}'). "
                    "Consider using timeless language to avoid outdated content."
                )
                # Only warn once to avoid spam
                break

        return warnings

    def _parse_frontmatter(
        self, content: str, result: ValidationResult
    ) -> tuple[Optional[dict[str, Any]], str]:
        """Parse and extract YAML frontmatter from content.

        Args:
            content: The SKILL.md file content
            result: ValidationResult to add errors to

        Returns:
            Tuple of (frontmatter_dict, body_content) or (None, "") on error
        """
        # Extract frontmatter
        match = self.FRONTMATTER_PATTERN.match(content)
        if not match:
            result.add_error(
                "Missing YAML frontmatter. File must start with '---' delimiter and "
                "end with '---' delimiter."
            )
            return None, ""

        frontmatter_yaml = match.group(1)
        body = content[match.end() :]

        # Parse YAML
        try:
            frontmatter_dict = yaml.safe_load(frontmatter_yaml)
            if not isinstance(frontmatter_dict, dict):
                result.add_error("Frontmatter must be a YAML dictionary")
                return None, ""
        except yaml.YAMLError as e:
            line_number = getattr(e, "problem_mark", None)
            line_num = line_number.line + 1 if line_number else "unknown"
            result.add_error(f"Invalid YAML frontmatter at line {line_num}: {e}")
            return None, ""

        return frontmatter_dict, body
