"""Tests for SkillValidator.

This module tests validation of SKILL.md content against official Anthropic
Agent Skills specifications.
"""

import pytest

from omniforge.skills.creation.validator import SkillValidator


class TestSkillValidator:
    """Tests for SkillValidator class."""

    @pytest.fixture
    def validator(self) -> SkillValidator:
        """Create a SkillValidator instance."""
        return SkillValidator()

    @pytest.fixture
    def valid_skill_content(self) -> str:
        """Create a valid SKILL.md content."""
        return """---
name: test-skill
description: A skill that processes data. Use when you need to transform input formats.
---

This skill helps you process various data formats.

## Usage

Invoke this skill when you need to handle data transformations.
"""

    def test_validate_valid_skill(
        self, validator: SkillValidator, valid_skill_content: str
    ) -> None:
        """Validator should accept valid SKILL.md content."""
        result = validator.validate(valid_skill_content, "test-skill")

        assert result.is_valid is True
        assert len(result.errors) == 0
        assert not result.has_errors()

    def test_validate_missing_frontmatter(self, validator: SkillValidator) -> None:
        """Validator should reject content without frontmatter."""
        content = "This is just body content without frontmatter."

        result = validator.validate(content, "test-skill")

        assert result.is_valid is False
        assert result.has_errors()
        assert any("missing yaml frontmatter" in e.lower() for e in result.errors)

    def test_validate_invalid_yaml(self, validator: SkillValidator) -> None:
        """Validator should reject invalid YAML frontmatter."""
        content = """---
name: test-skill
description: [invalid yaml structure
---

Body content
"""

        result = validator.validate(content, "test-skill")

        assert result.is_valid is False
        assert result.has_errors()
        assert any("invalid yaml" in e.lower() for e in result.errors)

    def test_validate_frontmatter_with_extra_fields(self, validator: SkillValidator) -> None:
        """Validator should reject frontmatter with unauthorized fields."""
        frontmatter = {
            "name": "test-skill",
            "description": "Test description",
            "tags": ["test"],
            "priority": 1,
        }

        errors = validator.validate_frontmatter_fields(frontmatter)

        assert len(errors) == 1
        assert "unauthorized" in errors[0].lower()
        assert "tags" in errors[0]
        assert "priority" in errors[0]

    def test_validate_frontmatter_missing_name(self, validator: SkillValidator) -> None:
        """Validator should reject frontmatter without name."""
        frontmatter = {"description": "Test description"}

        errors = validator.validate_frontmatter_fields(frontmatter)

        assert len(errors) == 1
        assert "missing" in errors[0].lower()
        assert "name" in errors[0]

    def test_validate_frontmatter_missing_description(self, validator: SkillValidator) -> None:
        """Validator should reject frontmatter without description."""
        frontmatter = {"name": "test-skill"}

        errors = validator.validate_frontmatter_fields(frontmatter)

        assert len(errors) == 1
        assert "missing" in errors[0].lower()
        assert "description" in errors[0]

    def test_validate_frontmatter_missing_both(self, validator: SkillValidator) -> None:
        """Validator should reject frontmatter without required fields."""
        frontmatter = {"tags": ["test"]}

        errors = validator.validate_frontmatter_fields(frontmatter)

        assert len(errors) == 2  # unauthorized fields + missing required
        assert any("unauthorized" in e.lower() for e in errors)
        assert any("missing" in e.lower() for e in errors)

    def test_validate_name_valid(self, validator: SkillValidator) -> None:
        """Validator should accept valid skill names."""
        valid_names = [
            "test",
            "test-skill",
            "skill-123",
            "my-test-skill-1",
            "a",
            "a" * 64,  # Max length
        ]

        for name in valid_names:
            errors = validator.validate_name(name)
            assert len(errors) == 0, f"Name '{name}' should be valid"

    def test_validate_name_too_long(self, validator: SkillValidator) -> None:
        """Validator should reject names over 64 characters."""
        name = "a" * 65

        errors = validator.validate_name(name)

        assert len(errors) == 1
        assert "64 character limit" in errors[0]

    def test_validate_name_invalid_format(self, validator: SkillValidator) -> None:
        """Validator should reject names with invalid format."""
        # Only test truly invalid names per pattern
        invalid_names = [
            "Test-Skill",
            "test_skill",
            "test skill",
            "test.skill",
            "-test-skill",
            "123-skill",
        ]

        for name in invalid_names:
            errors = validator.validate_name(name)
            assert len(errors) > 0, f"Name '{name}' should be invalid"
            assert any("kebab-case" in e for e in errors)

    def test_validate_name_reserved(self, validator: SkillValidator) -> None:
        """Validator should reject reserved skill names."""
        reserved_names = ["skill", "agent", "tool", "system", "admin", "root"]

        for name in reserved_names:
            errors = validator.validate_name(name)
            assert len(errors) > 0
            assert any("reserved" in e.lower() for e in errors)

    def test_validate_description_valid(self, validator: SkillValidator) -> None:
        """Validator should accept valid descriptions."""
        valid_descriptions = [
            "A skill that processes data. Use when you need transformations.",
            "Helps format documents. Designed for text processing tasks.",
            "Converts formats automatically. Helpful for data migration.",
        ]

        for desc in valid_descriptions:
            errors = validator.validate_description(desc)
            # May have trigger warning, but should not be an error
            assert all("third person" not in e.lower() for e in errors)

    def test_validate_description_too_long(self, validator: SkillValidator) -> None:
        """Validator should reject descriptions over 1024 characters."""
        description = "a" * 1025

        errors = validator.validate_description(description)

        assert len(errors) > 0
        assert any("1024 character limit" in e for e in errors)

    def test_validate_description_imperative(self, validator: SkillValidator) -> None:
        """Validator should detect imperative descriptions."""
        imperative_descriptions = [
            "Format all product names correctly.",
            "Create new reports from templates.",
            "Process incoming data files.",
            "Generate documentation automatically.",
        ]

        for desc in imperative_descriptions:
            errors = validator.validate_description(desc)
            assert any("imperative" in e.lower() or "third person" in e.lower() for e in errors)

    def test_validate_body_length_valid(self, validator: SkillValidator) -> None:
        """Validator should accept bodies under 500 lines."""
        body = "\n".join([f"Line {i}" for i in range(499)])

        errors = validator.validate_body_length(body)

        assert len(errors) == 0

    def test_validate_body_length_at_limit(self, validator: SkillValidator) -> None:
        """Validator should accept bodies at 500 line limit."""
        body = "\n".join([f"Line {i}" for i in range(500)])

        errors = validator.validate_body_length(body)

        assert len(errors) == 0

    def test_validate_body_over_500_lines(self, validator: SkillValidator) -> None:
        """Validator should reject bodies over 500 lines."""
        body = "\n".join([f"Line {i}" for i in range(501)])

        errors = validator.validate_body_length(body)

        assert len(errors) == 1
        assert "500" in errors[0]

    def test_validate_empty_body(self, validator: SkillValidator) -> None:
        """Validator should reject skills with empty body."""
        content = """---
name: test-skill
description: A skill that processes data. Use when needed.
---

"""

        result = validator.validate(content, "test-skill")

        assert result.is_valid is False
        assert any("empty" in e.lower() for e in result.errors)

    def test_check_time_sensitive_content_years(self, validator: SkillValidator) -> None:
        """Validator should warn about year mentions."""
        content = """---
name: test-skill
description: A skill that processes data. Use when needed.
---

This skill was updated in 2024 to support new formats.
"""

        warnings = validator.check_time_sensitive_content(content)

        assert len(warnings) > 0
        assert any("time-sensitive" in w.lower() for w in warnings)

    def test_check_time_sensitive_content_currently(self, validator: SkillValidator) -> None:
        """Validator should warn about temporal words."""
        temporal_words = ["currently", "now", "today", "recent", "latest"]

        for word in temporal_words:
            content = f"""---
name: test-skill
description: A skill that processes data. Use when needed.
---

This skill {word} supports various formats.
"""

            warnings = validator.check_time_sensitive_content(content)
            assert len(warnings) > 0, f"Should warn about '{word}'"

    def test_check_time_sensitive_content_clean(self, validator: SkillValidator) -> None:
        """Validator should not warn about timeless content."""
        content = """---
name: test-skill
description: A skill that processes data. Use when needed.
---

This skill helps you process data formats efficiently.
"""

        warnings = validator.check_time_sensitive_content(content)

        assert len(warnings) == 0

    def test_validate_name_mismatch(self, validator: SkillValidator) -> None:
        """Validator should reject when frontmatter name doesn't match expected."""
        content = """---
name: wrong-name
description: A skill that processes data. Use when needed.
---

Body content
"""

        result = validator.validate(content, "expected-name")

        assert result.is_valid is False
        assert any("does not match" in e for e in result.errors)

    def test_validate_integration_multiple_errors(self, validator: SkillValidator) -> None:
        """Validator should accumulate multiple errors."""
        content = """---
name: Invalid_Name
description: Format all data
tags: ["extra"]
---

Body content
"""

        result = validator.validate(content, "test-skill")

        assert result.is_valid is False
        assert len(result.errors) > 1
        # Should have errors for: unauthorized fields, invalid name, imperative desc,
        # name mismatch, missing trigger
        assert any("unauthorized" in e.lower() for e in result.errors)
        assert any("kebab-case" in e.lower() for e in result.errors)
        assert any("imperative" in e.lower() or "third person" in e.lower() for e in result.errors)

    def test_validate_integration_warnings_not_blocking(self, validator: SkillValidator) -> None:
        """Validator should separate warnings from errors."""
        content = """---
name: test-skill
description: A skill that processes data. Use when you need transformations.
---

This skill was last updated in 2024 to support new features.
It currently supports various formats.
"""

        result = validator.validate(content, "test-skill")

        assert result.is_valid is True  # Warnings don't block validation
        assert len(result.errors) == 0
        assert result.has_warnings()
        assert any("time-sensitive" in w.lower() for w in result.warnings)

    def test_validate_frontmatter_only_allowed_fields(self, validator: SkillValidator) -> None:
        """Validator should accept frontmatter with only name and description."""
        frontmatter = {"name": "test-skill", "description": "Test description"}

        errors = validator.validate_frontmatter_fields(frontmatter)

        assert len(errors) == 0


class TestValidationResultIntegration:
    """Integration tests using ValidationResult."""

    def test_validation_result_error_tracking(self) -> None:
        """ValidationResult should properly track errors."""
        validator = SkillValidator()

        content = """---
name: invalid_name
description: Format all data
---

Body
"""

        result = validator.validate(content, "test-skill")

        assert not result.is_valid
        assert result.has_errors()
        assert len(result.errors) > 0

    def test_validation_result_warning_tracking(self) -> None:
        """ValidationResult should properly track warnings."""
        validator = SkillValidator()

        content = """---
name: test-skill
description: A skill that processes data. Use when needed.
---

Updated in 2024.
"""

        result = validator.validate(content, "test-skill")

        assert result.is_valid  # Warnings don't block
        assert result.has_warnings()
        assert len(result.warnings) > 0
        assert not result.has_errors()


class TestWordCountValidation:
    """Test word count validation (5,000 word limit)."""

    def test_validate_word_count_valid(self) -> None:
        """Test word count under limit passes."""
        validator = SkillValidator()
        # Create a body with ~500 words (well under limit)
        body = " ".join(["word"] * 500)

        result = validator.validate_word_count(body)

        assert len(result["errors"]) == 0
        assert len(result["warnings"]) == 0

    def test_validate_word_count_at_warning_threshold(self) -> None:
        """Test word count at warning threshold (4,500+)."""
        validator = SkillValidator()
        # Create a body with 4,600 words (90%+ of limit)
        body = " ".join(["word"] * 4600)

        result = validator.validate_word_count(body)

        assert len(result["errors"]) == 0
        assert len(result["warnings"]) == 1
        assert "approaching 5,000 word limit" in result["warnings"][0]
        assert "4600 words" in result["warnings"][0]

    def test_validate_word_count_exceeds_limit(self) -> None:
        """Test word count exceeding limit."""
        validator = SkillValidator()
        # Create a body with 5,500 words (over limit)
        body = " ".join(["word"] * 5500)

        result = validator.validate_word_count(body)

        assert len(result["errors"]) == 1
        assert len(result["warnings"]) == 0
        assert "exceeds 5,000 word limit" in result["errors"][0]
        assert "5500 words" in result["errors"][0]
        assert "references/ directory" in result["errors"][0]

    def test_validate_word_count_exactly_at_limit(self) -> None:
        """Test word count exactly at limit (5,000 words)."""
        validator = SkillValidator()
        # Create a body with exactly 5,000 words
        body = " ".join(["word"] * 5000)

        result = validator.validate_word_count(body)

        # Exactly 5,000 should pass without error (not > 5,000)
        # but may trigger warning since it's at the limit
        assert len(result["errors"]) == 0
        assert len(result["warnings"]) == 1
        assert "approaching 5,000 word limit" in result["warnings"][0]

    def test_validate_word_count_integration(self) -> None:
        """Test word count validation integration in full validation."""
        validator = SkillValidator()
        # Create skill content with excessive word count
        body_words = " ".join(["word"] * 5500)
        content = f"""---
name: test-skill
description: A test skill for validating word count limits when creating skills.
---

# Test Skill

{body_words}
"""

        result = validator.validate(content, "test-skill")

        assert not result.is_valid
        assert any("5,000 word limit" in error for error in result.errors)
