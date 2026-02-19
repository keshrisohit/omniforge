"""Tests for syntax validator."""

from omniforge.prompts.validation.syntax import SyntaxValidator


class TestSyntaxValidator:
    """Tests for SyntaxValidator class."""

    def test_validate_valid_template(self) -> None:
        """Validator should return empty list for valid template."""
        validator = SyntaxValidator()
        template = "Hello {{ name }}!"

        errors = validator.validate(template)

        assert errors == []

    def test_validate_valid_template_with_blocks(self) -> None:
        """Validator should accept valid templates with control blocks."""
        validator = SyntaxValidator()
        template = """
        {% if condition %}
        Hello {{ name }}
        {% endif %}
        """

        errors = validator.validate(template)

        assert errors == []

    def test_validate_valid_template_with_loops(self) -> None:
        """Validator should accept valid templates with loops."""
        validator = SyntaxValidator()
        template = """
        {% for item in items %}
        - {{ item }}
        {% endfor %}
        """

        errors = validator.validate(template)

        assert errors == []

    def test_validate_invalid_missing_closing_brace(self) -> None:
        """Validator should detect missing closing brace."""
        validator = SyntaxValidator()
        template = "Hello {{ name }"

        errors = validator.validate(template)

        assert len(errors) == 1
        assert "expect" in errors[0].lower() or "}" in errors[0]

    def test_validate_invalid_unclosed_block(self) -> None:
        """Validator should detect unclosed blocks."""
        validator = SyntaxValidator()
        template = "{% if condition %}No endif"

        errors = validator.validate(template)

        assert len(errors) == 1
        assert "if" in errors[0].lower() or "end" in errors[0].lower()

    def test_validate_invalid_unclosed_for_loop(self) -> None:
        """Validator should detect unclosed for loops."""
        validator = SyntaxValidator()
        template = """
        {% for item in items %}
        {{ item }}
        """

        errors = validator.validate(template)

        assert len(errors) == 1
        assert "for" in errors[0].lower() or "end" in errors[0].lower()

    def test_validate_invalid_malformed_expression(self) -> None:
        """Validator should detect malformed expressions."""
        validator = SyntaxValidator()
        template = "{{ name + }}"

        errors = validator.validate(template)

        assert len(errors) == 1

    def test_validate_empty_template(self) -> None:
        """Validator should accept empty template."""
        validator = SyntaxValidator()
        template = ""

        errors = validator.validate(template)

        assert errors == []

    def test_validate_template_with_only_text(self) -> None:
        """Validator should accept template with only text."""
        validator = SyntaxValidator()
        template = "This is just plain text with no variables"

        errors = validator.validate(template)

        assert errors == []

    def test_validate_error_includes_line_number(self) -> None:
        """Validator should include line numbers in error messages."""
        validator = SyntaxValidator()
        template = """
        Line 1
        Line 2 {{ unclosed
        Line 3
        """

        errors = validator.validate(template)

        assert len(errors) == 1
        # Error message should contain line number or position information
        assert any(char.isdigit() for char in errors[0])

    def test_validate_complex_valid_template(self) -> None:
        """Validator should accept complex valid templates."""
        validator = SyntaxValidator()
        template = """
        {% for user in users %}
            {% if user.active %}
                Name: {{ user.name | capitalize_first }}
                Email: {{ user.email | default('N/A') }}
            {% endif %}
        {% endfor %}
        """

        errors = validator.validate(template)

        assert errors == []

    def test_validate_nested_blocks(self) -> None:
        """Validator should accept nested control blocks."""
        validator = SyntaxValidator()
        template = """
        {% for item in items %}
            {% if item.visible %}
                {% for tag in item.tags %}
                    {{ tag }}
                {% endfor %}
            {% endif %}
        {% endfor %}
        """

        errors = validator.validate(template)

        assert errors == []

    def test_validate_invalid_nested_blocks(self) -> None:
        """Validator should detect errors in nested blocks."""
        validator = SyntaxValidator()
        template = """
        {% for item in items %}
            {% if item.visible %}
                Content
            {% endfor %}
        {% endif %}
        """

        errors = validator.validate(template)

        assert len(errors) == 1

    def test_validate_with_comments(self) -> None:
        """Validator should accept templates with comments."""
        validator = SyntaxValidator()
        template = """
        {# This is a comment #}
        {{ name }}
        """

        errors = validator.validate(template)

        assert errors == []

    def test_validate_invalid_comment_syntax(self) -> None:
        """Validator should detect invalid comment syntax."""
        validator = SyntaxValidator()
        template = "{# Unclosed comment"

        errors = validator.validate(template)

        assert len(errors) == 1

    def test_validate_with_filters(self) -> None:
        """Validator should accept templates with filters."""
        validator = SyntaxValidator()
        template = "{{ name | upper | truncate(10) }}"

        errors = validator.validate(template)

        assert errors == []

    def test_validate_multiline_template(self) -> None:
        """Validator should handle multiline templates correctly."""
        validator = SyntaxValidator()
        template = """
        First line
        {% for i in range(3) %}
        Item {{ i }}
        {% endfor %}
        Last line
        """

        errors = validator.validate(template)

        assert errors == []

    def test_validate_template_with_special_characters(self) -> None:
        """Validator should handle special characters in templates."""
        validator = SyntaxValidator()
        template = "Special chars: @#$%^&*() {{ name }}"

        errors = validator.validate(template)

        assert errors == []

    def test_validate_invalid_unknown_tag(self) -> None:
        """Validator should detect unknown tags."""
        validator = SyntaxValidator()
        template = "{% unknowntag %}"

        errors = validator.validate(template)

        assert len(errors) == 1
        assert "unknown" in errors[0].lower() or "tag" in errors[0].lower()
