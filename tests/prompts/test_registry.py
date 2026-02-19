"""Tests for PromptTemplateRegistry."""

import pytest

from omniforge.prompts import PromptTemplateRegistry, get_default_registry
from omniforge.prompts.errors import PromptNotFoundError, PromptRenderError


class TestPromptTemplateRegistry:
    """Test cases for PromptTemplateRegistry."""

    def test_register_and_get(self) -> None:
        """Test registering and retrieving templates."""
        registry = PromptTemplateRegistry()

        # Register a template
        registry.register(
            name="greeting",
            content="Hello, {name}!",
            variables_schema={"name": str},
        )

        # Retrieve the template
        content = registry.get("greeting")
        assert content == "Hello, {name}!"

    def test_register_empty_name_raises_error(self) -> None:
        """Test that registering with empty name raises ValueError."""
        registry = PromptTemplateRegistry()

        with pytest.raises(ValueError, match="Template name cannot be empty"):
            registry.register(name="", content="test")

        with pytest.raises(ValueError, match="Template name cannot be empty"):
            registry.register(name="   ", content="test")

    def test_get_nonexistent_template_raises_error(self) -> None:
        """Test that getting non-existent template raises PromptNotFoundError."""
        registry = PromptTemplateRegistry()

        with pytest.raises(PromptNotFoundError, match="Template 'missing' not found"):
            registry.get("missing")

    def test_render_with_variables(self) -> None:
        """Test rendering template with variables."""
        registry = PromptTemplateRegistry()
        registry.register(
            name="greeting",
            content="Hello, {name}! You are {age} years old.",
            variables_schema={"name": str, "age": int},
        )

        rendered = registry.render("greeting", name="Alice", age=30)
        assert rendered == "Hello, Alice! You are 30 years old."

    def test_render_missing_variable_raises_error(self) -> None:
        """Test that rendering with missing variable raises PromptRenderError."""
        registry = PromptTemplateRegistry()
        registry.register(
            name="greeting",
            content="Hello, {name}!",
            variables_schema={"name": str},
        )

        with pytest.raises(PromptRenderError, match="Missing required variable"):
            registry.render("greeting")

    def test_render_nonexistent_template_raises_error(self) -> None:
        """Test that rendering non-existent template raises PromptNotFoundError."""
        registry = PromptTemplateRegistry()

        with pytest.raises(PromptNotFoundError, match="Template 'missing' not found"):
            registry.render("missing", name="Alice")

    def test_list_templates(self) -> None:
        """Test listing all template names."""
        registry = PromptTemplateRegistry()

        # Initially empty
        assert registry.list_templates() == []

        # Register some templates
        registry.register("template1", "content1")
        registry.register("template2", "content2")
        registry.register("template3", "content3")

        # Should return sorted list
        templates = registry.list_templates()
        assert templates == ["template1", "template2", "template3"]

    def test_exists(self) -> None:
        """Test checking template existence."""
        registry = PromptTemplateRegistry()

        assert not registry.exists("greeting")

        registry.register("greeting", "Hello!")

        assert registry.exists("greeting")
        assert not registry.exists("missing")

    def test_remove(self) -> None:
        """Test removing templates."""
        registry = PromptTemplateRegistry()
        registry.register("greeting", "Hello!")

        assert registry.exists("greeting")

        registry.remove("greeting")

        assert not registry.exists("greeting")

    def test_remove_nonexistent_raises_error(self) -> None:
        """Test that removing non-existent template raises PromptNotFoundError."""
        registry = PromptTemplateRegistry()

        with pytest.raises(PromptNotFoundError, match="Template 'missing' not found"):
            registry.remove("missing")

    def test_clear(self) -> None:
        """Test clearing all templates."""
        registry = PromptTemplateRegistry()

        # Register some templates
        registry.register("template1", "content1")
        registry.register("template2", "content2")
        registry.register("template3", "content3")

        assert len(registry.list_templates()) == 3

        # Clear all
        registry.clear()

        assert len(registry.list_templates()) == 0

    def test_thread_safety(self) -> None:
        """Test that registry is thread-safe (basic check)."""
        import threading

        registry = PromptTemplateRegistry()
        errors = []

        def register_templates() -> None:
            try:
                for i in range(100):
                    registry.register(f"template_{i}", f"content_{i}")
            except Exception as e:
                errors.append(e)

        # Run concurrent registrations
        threads = [threading.Thread(target=register_templates) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Check no errors occurred
        assert len(errors) == 0

        # Check templates were registered (last write wins for duplicates)
        templates = registry.list_templates()
        assert len(templates) == 100


class TestDefaultRegistry:
    """Test cases for default registry with pre-populated templates."""

    def test_get_default_registry_has_templates(self) -> None:
        """Test that default registry comes with expected templates."""
        registry = get_default_registry()

        expected_templates = [
            "react_base",
            "skill_navigation",
            "script_execution",
            "multi_llm_paths",
            "tool_calling_examples",
            "skill_wrapper",
            "skill_prompt_simple",
        ]

        templates = registry.list_templates()
        for expected in expected_templates:
            assert expected in templates, f"Expected template '{expected}' not found"

    def test_react_base_template(self) -> None:
        """Test that react_base template can be rendered."""
        registry = get_default_registry()

        rendered = registry.render("react_base", tool_descriptions="Test tools")

        assert "Test tools" in rendered
        assert "CRITICAL EXECUTION RULES" in rendered
        assert "Response Format (JSON)" in rendered

    def test_skill_wrapper_template(self) -> None:
        """Test that skill_wrapper template can be rendered."""
        registry = get_default_registry()

        rendered = registry.render(
            "skill_wrapper",
            skill_name="test-skill",
            skill_description="A test skill",
            skill_content="Do something useful",
            available_files_section="",
            base_react_prompt="React instructions here",
            allowed_tools="read, bash",
        )

        assert "test-skill" in rendered
        assert "A test skill" in rendered
        assert "Do something useful" in rendered
        assert "React instructions here" in rendered
        assert "read, bash" in rendered

    def test_skill_prompt_simple_template(self) -> None:
        """Test that skill_prompt_simple template can be rendered."""
        registry = get_default_registry()

        rendered = registry.render(
            "skill_prompt_simple",
            skill_name="test-skill",
            skill_description="A test skill",
            skill_content="Do something",
            available_files_section="",
            tool_descriptions="- read: Read files",
            iteration=1,
            max_iterations=15,
        )

        assert "test-skill" in rendered
        assert "Iteration 1/15" in rendered
        assert "- read: Read files" in rendered

    def test_skill_navigation_template(self) -> None:
        """Test that skill_navigation template exists and has expected content."""
        registry = get_default_registry()

        content = registry.get("skill_navigation")

        assert "Skill Path Resolution" in content
        assert "base_path" in content
        assert "Path Resolution Rules" in content

    def test_script_execution_template(self) -> None:
        """Test that script_execution template exists and has expected content."""
        registry = get_default_registry()

        content = registry.get("script_execution")

        assert "Script Execution" in content
        assert "NEVER load script contents with Read tool" in content
        assert "Execute script" in content

    def test_multi_llm_paths_template(self) -> None:
        """Test that multi_llm_paths template exists and has expected content."""
        registry = get_default_registry()

        content = registry.get("multi_llm_paths")

        assert "Multi-LLM Path Resolution" in content
        assert "Loading Files:" in content
        assert "Executing Scripts:" in content

    def test_tool_calling_examples_template(self) -> None:
        """Test that tool_calling_examples template exists and has expected content."""
        registry = get_default_registry()

        content = registry.get("tool_calling_examples")

        assert "Tool Calling Format Examples" in content
        assert "Read Tool:" in content
        assert "bash Tool" in content
        assert "Skill Tool:" in content
