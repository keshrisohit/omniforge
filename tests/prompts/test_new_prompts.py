"""Tests for new system prompts added based on Claude Code patterns."""

import pytest

from omniforge.prompts import get_default_registry


class TestNewPromptTemplates:
    """Test suite for newly added prompt templates."""

    def setup_method(self):
        """Set up test fixtures."""
        self.registry = get_default_registry()

    def test_skill_creation_prompt_registered(self):
        """Test that skill creation prompt is registered."""
        templates = self.registry.list_templates()
        assert "skill_creation" in templates

    def test_skill_update_prompt_registered(self):
        """Test that skill update prompt is registered."""
        templates = self.registry.list_templates()
        assert "skill_update" in templates

    def test_verification_specialist_prompt_registered(self):
        """Test that verification specialist prompt is registered."""
        templates = self.registry.list_templates()
        assert "verification_specialist" in templates

    def test_config_management_prompt_registered(self):
        """Test that config management prompt is registered."""
        templates = self.registry.list_templates()
        assert "config_management" in templates

    def test_skill_creation_prompt_renders(self):
        """Test that skill creation prompt can be rendered."""
        prompt = self.registry.render("skill_creation")

        # Check key sections are present
        assert "Skill Structure" in prompt
        assert "Creation Process" in prompt
        assert "Validation Checklist" in prompt
        assert "Best Practices" in prompt
        assert "Tool Descriptions" in prompt

        # Check key concepts
        assert "SKILL.md" in prompt
        assert "allowed_tools" in prompt
        assert "Supporting Files" in prompt

        # Ensure it's substantial
        assert len(prompt) > 1000

    def test_skill_update_prompt_renders(self):
        """Test that skill update prompt can be rendered."""
        prompt = self.registry.render("skill_update")

        # Check key sections
        assert "Update Process" in prompt
        assert "Backward Compatibility" in prompt
        assert "semantic versioning" in prompt.lower()  # Case-insensitive check
        assert "Testing Checklist" in prompt

        # Check key concepts
        assert "MAJOR" in prompt
        assert "MINOR" in prompt
        assert "PATCH" in prompt
        assert "Breaking Changes" in prompt

        # Ensure it's substantial
        assert len(prompt) > 1000

    def test_verification_specialist_prompt_renders(self):
        """Test that verification specialist prompt can be rendered."""
        prompt = self.registry.render("verification_specialist")

        # Check workflow phases
        assert "Phase 1: Discover Verifiers" in prompt
        assert "Phase 2: Analyze Changes" in prompt
        assert "Phase 3: Choose Verifier(s)" in prompt
        assert "Phase 4: Generate Verification Plan" in prompt
        assert "Phase 5: Trigger Verifier(s)" in prompt

        # Check key concepts
        assert "git status" in prompt
        assert "git diff" in prompt
        assert "verifier" in prompt.lower()

        # Ensure it's substantial
        assert len(prompt) > 2000

    def test_config_management_prompt_renders(self):
        """Test that config management prompt can be rendered."""
        prompt = self.registry.render("config_management")

        # Check key sections
        assert "Always Read, Then Merge" in prompt
        assert "Configuration Types" in prompt
        assert "Update Process" in prompt
        assert "Hooks vs Memory" in prompt

        # Check key concepts
        assert "read first" in prompt.lower()
        assert "merge" in prompt.lower()
        assert "WRONG" in prompt  # Anti-patterns
        assert "RIGHT" in prompt  # Correct patterns

        # Ensure it's substantial
        assert len(prompt) > 2000

    def test_skill_creation_has_validation_checklist(self):
        """Test that skill creation prompt includes validation checklist."""
        prompt = self.registry.render("skill_creation")

        # Should have checklist items
        assert "☐" in prompt or "[ ]" in prompt
        assert "Name is unique" in prompt
        assert "allowed tools" in prompt.lower()
        assert "Instructions are" in prompt

    def test_skill_update_has_version_guidance(self):
        """Test that skill update prompt includes version guidance."""
        prompt = self.registry.render("skill_update")

        # Should explain semantic versioning
        assert "1.0.0" in prompt
        assert "2.0.0" in prompt or "breaking" in prompt.lower()
        assert "backward compatible" in prompt.lower()

    def test_verification_has_git_commands(self):
        """Test that verification prompt includes git integration."""
        prompt = self.registry.render("verification_specialist")

        # Should have git commands
        assert "git status" in prompt
        assert "git diff" in prompt

    def test_config_management_has_merge_examples(self):
        """Test that config management prompt has merge examples."""
        prompt = self.registry.render("config_management")

        # Should have before/after examples
        assert "BEFORE" in prompt
        assert "AFTER" in prompt
        assert "merged" in prompt.lower()

        # Should warn against replacing
        assert "Never replace" in prompt or "WRONG: Replace" in prompt

    def test_all_new_prompts_have_examples(self):
        """Test that all new prompts include concrete examples."""
        prompts = [
            "skill_creation",
            "skill_update",
            "verification_specialist",
            "config_management",
        ]

        for prompt_name in prompts:
            prompt = self.registry.render(prompt_name)

            # Each should have example markers
            assert (
                "Example" in prompt
                or "```" in prompt
                or "## Example" in prompt
                or "### Example" in prompt
            ), f"Prompt '{prompt_name}' should include examples"

    def test_prompts_have_anti_patterns(self):
        """Test that prompts include anti-pattern guidance."""
        prompts_with_antipatterns = [
            "skill_creation",
            "config_management",
        ]

        for prompt_name in prompts_with_antipatterns:
            prompt = self.registry.render(prompt_name)

            # Should explicitly call out what NOT to do
            assert (
                "Don't" in prompt
                or "MUST NOT" in prompt
                or "❌" in prompt
                or "WRONG" in prompt
            ), f"Prompt '{prompt_name}' should include anti-patterns"

    def test_prompts_have_do_patterns(self):
        """Test that prompts include positive guidance."""
        prompts = [
            "skill_creation",
            "skill_update",
            "verification_specialist",
            "config_management",
        ]

        for prompt_name in prompts:
            prompt = self.registry.render(prompt_name)

            # Should explicitly show what TO do
            assert (
                "Do:" in prompt
                or "MUST DO" in prompt
                or "✅" in prompt
                or "RIGHT" in prompt
                or "Best Practices" in prompt
            ), f"Prompt '{prompt_name}' should include positive guidance"

    def test_backward_compatibility_preserved(self):
        """Test that existing prompts still work."""
        existing_prompts = [
            "react_base",
            "skill_wrapper",
            "skill_prompt_simple",
            "skill_navigation",
            "script_execution",
        ]

        for prompt_name in existing_prompts:
            # Should still be registered
            templates = self.registry.list_templates()
            assert (
                prompt_name in templates
            ), f"Existing prompt '{prompt_name}' should still be registered"

            # Should still render (with required variables for some)
            if prompt_name == "react_base":
                prompt = self.registry.render(
                    prompt_name, tool_descriptions="- test: Test tool"
                )
            elif prompt_name == "skill_wrapper":
                prompt = self.registry.render(
                    prompt_name,
                    skill_name="test",
                    skill_description="Test skill",
                    skill_content="Test content",
                    available_files_section="",
                    base_react_prompt="Test prompt",
                    allowed_tools="bash, read",
                )
            elif prompt_name == "skill_prompt_simple":
                prompt = self.registry.render(
                    prompt_name,
                    skill_name="test",
                    skill_description="Test skill",
                    skill_content="Test content",
                    available_files_section="",
                    tool_descriptions="- test: Test tool",
                    iteration=1,
                    max_iterations=10,
                )
            else:
                prompt = self.registry.render(prompt_name)

            assert prompt, f"Existing prompt '{prompt_name}' should render"
            assert len(prompt) > 0, f"Rendered prompt '{prompt_name}' should not be empty"


class TestPromptQuality:
    """Test suite for prompt quality and content."""

    def setup_method(self):
        """Set up test fixtures."""
        self.registry = get_default_registry()

    def test_prompts_are_not_too_short(self):
        """Test that prompts have sufficient content."""
        min_lengths = {
            "skill_creation": 1000,
            "skill_update": 1000,
            "verification_specialist": 2000,
            "config_management": 2000,
        }

        for prompt_name, min_length in min_lengths.items():
            prompt = self.registry.render(prompt_name)
            assert (
                len(prompt) >= min_length
            ), f"Prompt '{prompt_name}' should be at least {min_length} chars"

    def test_prompts_use_consistent_formatting(self):
        """Test that prompts use consistent markdown formatting."""
        prompts = [
            "skill_creation",
            "skill_update",
            "verification_specialist",
            "config_management",
        ]

        for prompt_name in prompts:
            prompt = self.registry.render(prompt_name)

            # Should use markdown headers
            assert "#" in prompt, f"Prompt '{prompt_name}' should use markdown headers"

            # Should use code blocks for examples
            assert (
                "```" in prompt or "{{{{" in prompt
            ), f"Prompt '{prompt_name}' should include code examples"

    def test_prompts_have_clear_structure(self):
        """Test that prompts are well-structured."""
        prompts = [
            "skill_creation",
            "skill_update",
            "verification_specialist",
            "config_management",
        ]

        for prompt_name in prompts:
            prompt = self.registry.render(prompt_name)

            # Should have multiple sections
            header_count = prompt.count("##")
            assert (
                header_count >= 3
            ), f"Prompt '{prompt_name}' should have multiple sections"

    def test_prompts_include_security_guidance(self):
        """Test that prompts include security considerations."""
        security_prompts = [
            "skill_creation",
            "config_management",
        ]

        for prompt_name in security_prompts:
            prompt = self.registry.render(prompt_name)

            # Should mention security or sensitive data
            assert (
                "security" in prompt.lower()
                or "sensitive" in prompt.lower()
                or "secret" in prompt.lower()
            ), f"Prompt '{prompt_name}' should include security guidance"


class TestPromptUsability:
    """Test suite for prompt usability and practical application."""

    def setup_method(self):
        """Set up test fixtures."""
        self.registry = get_default_registry()

    def test_skill_creation_guides_tool_selection(self):
        """Test that skill creation prompt helps with tool selection."""
        prompt = self.registry.render("skill_creation")

        # Should list and describe tools
        tool_keywords = ["bash", "read", "write", "glob", "grep", "llm"]
        found_tools = [kw for kw in tool_keywords if kw in prompt.lower()]

        assert (
            len(found_tools) >= 4
        ), "Skill creation should describe multiple tools"

    def test_verification_prompt_has_clear_phases(self):
        """Test that verification prompt has distinct phases."""
        prompt = self.registry.render("verification_specialist")

        # Should have 5 phases
        for i in range(1, 6):
            assert (
                f"Phase {i}" in prompt
            ), f"Verification prompt should have Phase {i}"

    def test_config_management_shows_merge_patterns(self):
        """Test that config management shows specific merge patterns."""
        prompt = self.registry.render("config_management")

        # Should show patterns for different data types
        assert "Objects" in prompt or "object" in prompt.lower()
        assert "Arrays" in prompt or "array" in prompt.lower()
        assert "Primitives" in prompt or "primitive" in prompt.lower()

    def test_prompts_encourage_best_practices(self):
        """Test that prompts actively encourage best practices."""
        prompts = [
            "skill_creation",
            "skill_update",
            "config_management",
        ]

        for prompt_name in prompts:
            prompt = self.registry.render(prompt_name)

            # Should have explicit best practices section or guidance
            assert (
                "Best Practices" in prompt
                or "Do:" in prompt
                or "✅" in prompt
            ), f"Prompt '{prompt_name}' should encourage best practices"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
