"""Tests for template renderer and loader."""

import pytest

from omniforge.prompts.composition.renderer import PromptTemplateLoader, TemplateRenderer
from omniforge.prompts.errors import PromptRenderError


class TestPromptTemplateLoader:
    """Tests for PromptTemplateLoader class."""

    def test_get_source_returns_template_string(self) -> None:
        """Loader should return template string as source."""
        loader = PromptTemplateLoader()
        template = "Hello {{ name }}"

        source, filename, uptodate = loader.get_source(None, template)  # type: ignore

        assert source == template
        assert filename is None
        assert uptodate is None

    def test_get_source_with_complex_template(self) -> None:
        """Loader should handle complex templates."""
        loader = PromptTemplateLoader()
        template = """
        {% for item in items %}
        - {{ item }}
        {% endfor %}
        """

        source, filename, uptodate = loader.get_source(None, template)  # type: ignore

        assert source == template
        assert filename is None


class TestTemplateRenderer:
    """Tests for TemplateRenderer class."""

    @pytest.mark.asyncio
    async def test_render_simple_template(self) -> None:
        """Renderer should handle simple variable substitution."""
        renderer = TemplateRenderer()
        template = "Hello {{ name }}!"

        result = await renderer.render(template, {"name": "World"})

        assert result == "Hello World!"

    @pytest.mark.asyncio
    async def test_render_without_variables(self) -> None:
        """Renderer should handle templates without variables."""
        renderer = TemplateRenderer()
        template = "Hello World!"

        result = await renderer.render(template)

        assert result == "Hello World!"

    @pytest.mark.asyncio
    async def test_render_with_empty_variables(self) -> None:
        """Renderer should handle empty variable dictionary."""
        renderer = TemplateRenderer()
        template = "Static text"

        result = await renderer.render(template, {})

        assert result == "Static text"

    @pytest.mark.asyncio
    async def test_render_with_control_structures(self) -> None:
        """Renderer should handle Jinja2 control structures."""
        renderer = TemplateRenderer()
        template = """
        {% if show_greeting %}
        Hello {{ name }}!
        {% endif %}
        """

        result = await renderer.render(template, {"show_greeting": True, "name": "Alice"})

        assert "Hello Alice!" in result

    @pytest.mark.asyncio
    async def test_render_with_loops(self) -> None:
        """Renderer should handle loops."""
        renderer = TemplateRenderer()
        template = """
        {% for item in items %}
        - {{ item }}
        {% endfor %}
        """

        result = await renderer.render(template, {"items": ["apple", "banana", "cherry"]})

        assert "- apple" in result
        assert "- banana" in result
        assert "- cherry" in result

    @pytest.mark.asyncio
    async def test_render_with_undefined_variable_raises_error(self) -> None:
        """Renderer should raise PromptRenderError for undefined variables."""
        renderer = TemplateRenderer()
        template = "Hello {{ undefined_var }}!"

        with pytest.raises(PromptRenderError) as exc_info:
            await renderer.render(template, {})

        assert exc_info.value.variable is not None
        assert "undefined" in exc_info.value.message.lower()

    @pytest.mark.asyncio
    async def test_render_error_includes_template_context(self) -> None:
        """PromptRenderError should include template and variable context."""
        renderer = TemplateRenderer()
        template = "Hello {{ missing }}!"

        with pytest.raises(PromptRenderError) as exc_info:
            await renderer.render(template, {"other": "value"})

        assert exc_info.value.details["template"] == template
        assert "other" in exc_info.value.details["variables"]

    @pytest.mark.asyncio
    async def test_render_with_syntax_error_raises_error(self) -> None:
        """Renderer should raise PromptRenderError for syntax errors."""
        renderer = TemplateRenderer()
        template = "Hello {{ name }"  # Missing closing brace

        with pytest.raises(PromptRenderError):
            await renderer.render(template, {"name": "World"})

    @pytest.mark.asyncio
    async def test_trim_blocks_removes_newlines(self) -> None:
        """Renderer should trim blocks correctly."""
        renderer = TemplateRenderer()
        template = "Start\n{% if true %}\nMiddle\n{% endif %}\nEnd"

        result = await renderer.render(template, {})

        # trim_blocks should remove the first newline after block tags
        assert "Start" in result
        assert "Middle" in result
        assert "End" in result

    @pytest.mark.asyncio
    async def test_sandbox_prevents_attribute_access(self) -> None:
        """Sandboxed environment should prevent access to dangerous attributes."""
        renderer = TemplateRenderer()
        template = "{{ obj.__class__ }}"

        # SandboxedEnvironment should prevent this
        with pytest.raises(PromptRenderError):
            await renderer.render(template, {"obj": object()})


class TestTemplateRendererFilters:
    """Tests for custom template filters."""

    @pytest.mark.asyncio
    async def test_default_filter_with_value(self) -> None:
        """Default filter should return value if present."""
        renderer = TemplateRenderer()
        template = "{{ name | default('Guest') }}"

        result = await renderer.render(template, {"name": "Alice"})

        assert result == "Alice"

    @pytest.mark.asyncio
    async def test_default_filter_with_none(self) -> None:
        """Default filter should return default for None."""
        renderer = TemplateRenderer()
        template = "{{ name | default('Guest') }}"

        result = await renderer.render(template, {"name": None})

        assert result == "Guest"

    @pytest.mark.asyncio
    async def test_default_filter_with_empty_string(self) -> None:
        """Default filter should return default for empty string."""
        renderer = TemplateRenderer()
        template = "{{ name | default('Guest') }}"

        result = await renderer.render(template, {"name": ""})

        assert result == "Guest"

    @pytest.mark.asyncio
    async def test_default_filter_with_whitespace(self) -> None:
        """Default filter should return default for whitespace-only string."""
        renderer = TemplateRenderer()
        template = "{{ name | default('Guest') }}"

        result = await renderer.render(template, {"name": "   "})

        assert result == "Guest"

    @pytest.mark.asyncio
    async def test_truncate_filter_short_text(self) -> None:
        """Truncate filter should not modify text shorter than limit."""
        renderer = TemplateRenderer()
        template = "{{ text | truncate(20) }}"

        result = await renderer.render(template, {"text": "Short text"})

        assert result == "Short text"

    @pytest.mark.asyncio
    async def test_truncate_filter_long_text(self) -> None:
        """Truncate filter should truncate long text with suffix."""
        renderer = TemplateRenderer()
        template = "{{ text | truncate(10, '...') }}"

        result = await renderer.render(
            template, {"text": "This is a very long text that needs truncation"}
        )

        assert len(result) == 10
        assert result.endswith("...")

    @pytest.mark.asyncio
    async def test_truncate_filter_custom_suffix(self) -> None:
        """Truncate filter should support custom suffix."""
        renderer = TemplateRenderer()
        template = "{{ text | truncate(15, ' [more]') }}"

        result = await renderer.render(template, {"text": "This is a long text"})

        assert result.endswith("[more]")
        assert len(result) == 15

    @pytest.mark.asyncio
    async def test_truncate_filter_non_string(self) -> None:
        """Truncate filter should convert non-strings."""
        renderer = TemplateRenderer()
        template = "{{ number | truncate(5) }}"

        result = await renderer.render(template, {"number": 12345678})

        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_capitalize_first_filter(self) -> None:
        """Capitalize_first filter should capitalize first character only."""
        renderer = TemplateRenderer()
        template = "{{ text | capitalize_first }}"

        result = await renderer.render(template, {"text": "hello world"})

        assert result == "Hello world"

    @pytest.mark.asyncio
    async def test_capitalize_first_filter_empty_string(self) -> None:
        """Capitalize_first filter should handle empty string."""
        renderer = TemplateRenderer()
        template = "{{ text | capitalize_first }}"

        result = await renderer.render(template, {"text": ""})

        assert result == ""

    @pytest.mark.asyncio
    async def test_capitalize_first_filter_already_capitalized(self) -> None:
        """Capitalize_first filter should work on already capitalized text."""
        renderer = TemplateRenderer()
        template = "{{ text | capitalize_first }}"

        result = await renderer.render(template, {"text": "Hello World"})

        assert result == "Hello World"

    @pytest.mark.asyncio
    async def test_bullet_list_filter(self) -> None:
        """Bullet_list filter should format list as bullet points."""
        renderer = TemplateRenderer()
        template = "{{ items | bullet_list }}"

        result = await renderer.render(template, {"items": ["apple", "banana", "cherry"]})

        assert "• apple" in result
        assert "• banana" in result
        assert "• cherry" in result

    @pytest.mark.asyncio
    async def test_bullet_list_filter_empty_list(self) -> None:
        """Bullet_list filter should handle empty list."""
        renderer = TemplateRenderer()
        template = "{{ items | bullet_list }}"

        result = await renderer.render(template, {"items": []})

        assert result == ""

    @pytest.mark.asyncio
    async def test_bullet_list_filter_custom_bullet(self) -> None:
        """Bullet_list filter should support custom bullet character."""
        renderer = TemplateRenderer()
        template = "{{ items | bullet_list('-') }}"

        result = await renderer.render(template, {"items": ["item1", "item2"]})

        assert "- item1" in result
        assert "- item2" in result

    @pytest.mark.asyncio
    async def test_bullet_list_filter_custom_indent(self) -> None:
        """Bullet_list filter should support custom indentation."""
        renderer = TemplateRenderer()
        template = "{{ items | bullet_list('*', '    ') }}"

        result = await renderer.render(template, {"items": ["item1"]})

        assert "    * item1" in result

    @pytest.mark.asyncio
    async def test_bullet_list_filter_non_list(self) -> None:
        """Bullet_list filter should handle non-list values."""
        renderer = TemplateRenderer()
        template = "{{ items | bullet_list }}"

        result = await renderer.render(template, {"items": "not a list"})

        assert result == "not a list"

    @pytest.mark.asyncio
    async def test_bullet_list_filter_tuple(self) -> None:
        """Bullet_list filter should handle tuples."""
        renderer = TemplateRenderer()
        template = "{{ items | bullet_list }}"

        result = await renderer.render(template, {"items": ("first", "second")})

        assert "• first" in result
        assert "• second" in result


class TestTemplateRendererValidation:
    """Tests for template syntax validation."""

    def test_validate_syntax_valid_template(self) -> None:
        """Validate should return empty list for valid template."""
        renderer = TemplateRenderer()
        template = "Hello {{ name }}!"

        errors = renderer.validate_syntax(template)

        assert errors == []

    def test_validate_syntax_invalid_template(self) -> None:
        """Validate should return errors for invalid template."""
        renderer = TemplateRenderer()
        template = "Hello {{ name }"  # Missing closing brace

        errors = renderer.validate_syntax(template)

        assert len(errors) > 0
        assert any("expect" in error.lower() for error in errors)

    def test_validate_syntax_unclosed_block(self) -> None:
        """Validate should detect unclosed blocks."""
        renderer = TemplateRenderer()
        template = "{% if condition %}No endif"

        errors = renderer.validate_syntax(template)

        assert len(errors) > 0

    def test_validate_syntax_multiple_errors(self) -> None:
        """Validate should detect syntax errors."""
        renderer = TemplateRenderer()
        template = "{{ unclosed "  # Multiple syntax issues

        errors = renderer.validate_syntax(template)

        assert len(errors) > 0

    def test_validate_syntax_complex_valid_template(self) -> None:
        """Validate should pass complex valid templates."""
        renderer = TemplateRenderer()
        template = """
        {% for item in items %}
            {{ item | capitalize_first }}
        {% endfor %}
        """

        errors = renderer.validate_syntax(template)

        assert errors == []
