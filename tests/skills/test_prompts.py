"""Tests for system prompt building utilities."""

from pathlib import Path

import pytest

from omniforge.prompts import get_default_registry
from omniforge.skills.context_loader import FileReference, LoadedContext
from omniforge.skills.models import Skill, SkillMetadata
from omniforge.skills.prompts import PromptBuilder
from omniforge.tools.base import ParameterType, ToolDefinition, ToolParameter
from omniforge.tools.types import ToolType


@pytest.fixture
def sample_skill() -> Skill:
    """Create a sample skill for testing."""
    metadata = SkillMetadata(
        name="test-skill",
        description="A test skill for unit testing",
    )
    return Skill(
        metadata=metadata,
        content="This is the test skill content.\n\nFollow these instructions carefully.",
        path=Path("/skills/test-skill/SKILL.md"),
        base_path=Path("/skills/test-skill"),
        storage_layer="test",
    )


@pytest.fixture
def sample_tools() -> list[ToolDefinition]:
    """Create sample tool definitions."""
    return [
        ToolDefinition(
            name="read",
            type=ToolType.FILE_SYSTEM,
            description="Read a file from the filesystem",
            parameters=[
                ToolParameter(
                    name="file_path",
                    type=ParameterType.STRING,
                    description="Path to the file to read",
                    required=True,
                )
            ],
        ),
        ToolDefinition(
            name="bash",
            type=ToolType.BASH,
            description="Execute bash commands",
            parameters=[
                ToolParameter(
                    name="command",
                    type=ParameterType.STRING,
                    description="Command to execute",
                    required=True,
                )
            ],
        ),
        ToolDefinition(
            name="write",
            type=ToolType.FILE_SYSTEM,
            description="Write content to a file",
            parameters=[
                ToolParameter(
                    name="file_path",
                    type=ParameterType.STRING,
                    description="Path where to write",
                    required=True,
                ),
                ToolParameter(
                    name="content",
                    type=ParameterType.STRING,
                    description="Content to write",
                    required=True,
                ),
            ],
        ),
    ]


@pytest.fixture
def loaded_context_with_files() -> LoadedContext:
    """Create a loaded context with available files."""
    return LoadedContext(
        skill_content="Test skill content",
        available_files={
            "reference.md": FileReference(
                filename="reference.md",
                path=Path("/skills/test-skill/reference.md"),
                description="API reference documentation",
                estimated_lines=1200,
            ),
            "examples.txt": FileReference(
                filename="examples.txt",
                path=Path("/skills/test-skill/examples.txt"),
                description="Usage examples",
                estimated_lines=500,
            ),
            "config.json": FileReference(
                filename="config.json",
                path=Path("/skills/test-skill/config.json"),
                description="Configuration file",
                estimated_lines=None,  # No line count
            ),
        },
        skill_dir=Path("/skills/test-skill"),
        line_count=50,
    )


@pytest.fixture
def empty_context() -> LoadedContext:
    """Create an empty loaded context."""
    return LoadedContext(
        skill_content="Test content",
        available_files={},
        skill_dir=Path("/skills/test-skill"),
        line_count=10,
    )


class TestPromptTemplate:
    """Tests for skill_prompt_simple template from registry."""

    def test_template_has_required_placeholders(self) -> None:
        """Template should contain all required placeholders."""
        registry = get_default_registry()
        template = registry.get("skill_prompt_simple")

        assert "{skill_name}" in template
        assert "{skill_description}" in template
        assert "{skill_content}" in template
        assert "{available_files_section}" in template
        assert "{tool_descriptions}" in template
        assert "{iteration}" in template
        assert "{max_iterations}" in template

    def test_template_includes_json_format(self) -> None:
        """Template should include JSON format instructions."""
        registry = get_default_registry()
        template = registry.get("skill_prompt_simple")

        assert "JSON format" in template
        assert '"thought"' in template
        assert '"action"' in template
        assert '"action_input"' in template
        assert '"is_final"' in template
        assert '"final_answer"' in template

    def test_template_includes_react_instructions(self) -> None:
        """Template should include ReAct pattern instructions."""
        registry = get_default_registry()
        template = registry.get("skill_prompt_simple")

        # Check for key ReAct concepts
        assert "tool" in template.lower()
        assert (
            "reasoning" in template.lower()
            or "thought" in template.lower()
        )


class TestPromptBuilder:
    """Tests for PromptBuilder class."""

    def test_build_system_prompt_includes_skill_name(
        self, sample_skill: Skill, sample_tools: list[ToolDefinition]
    ) -> None:
        """System prompt should include skill name."""
        builder = PromptBuilder()
        tool_descriptions = builder.format_tool_descriptions(sample_tools)
        prompt = builder.build_system_prompt(
            skill=sample_skill,
            tool_descriptions=tool_descriptions,
            available_files_section="",
            iteration=1,
            max_iterations=15,
        )

        assert sample_skill.metadata.name in prompt
        assert "test-skill" in prompt

    def test_build_system_prompt_includes_skill_description(
        self, sample_skill: Skill, sample_tools: list[ToolDefinition]
    ) -> None:
        """System prompt should include skill description."""
        builder = PromptBuilder()
        tool_descriptions = builder.format_tool_descriptions(sample_tools)
        prompt = builder.build_system_prompt(
            skill=sample_skill,
            tool_descriptions=tool_descriptions,
            available_files_section="",
            iteration=1,
            max_iterations=15,
        )

        assert sample_skill.metadata.description in prompt
        assert "A test skill for unit testing" in prompt

    def test_build_system_prompt_includes_skill_content(
        self, sample_skill: Skill, sample_tools: list[ToolDefinition]
    ) -> None:
        """System prompt should include skill content."""
        builder = PromptBuilder()
        tool_descriptions = builder.format_tool_descriptions(sample_tools)
        prompt = builder.build_system_prompt(
            skill=sample_skill,
            tool_descriptions=tool_descriptions,
            available_files_section="",
            iteration=1,
            max_iterations=15,
        )

        assert sample_skill.content in prompt
        assert "Follow these instructions carefully" in prompt

    def test_build_system_prompt_includes_tool_descriptions(
        self, sample_skill: Skill, sample_tools: list[ToolDefinition]
    ) -> None:
        """System prompt should include tool descriptions."""
        builder = PromptBuilder()
        tool_descriptions = builder.format_tool_descriptions(sample_tools)
        prompt = builder.build_system_prompt(
            skill=sample_skill,
            tool_descriptions=tool_descriptions,
            available_files_section="",
            iteration=1,
            max_iterations=15,
        )

        assert "read: Read a file" in prompt
        assert "bash: Execute bash commands" in prompt

    def test_build_system_prompt_includes_available_files(
        self,
        sample_skill: Skill,
        sample_tools: list[ToolDefinition],
        loaded_context_with_files: LoadedContext,
    ) -> None:
        """System prompt should include available files section."""
        builder = PromptBuilder()
        tool_descriptions = builder.format_tool_descriptions(sample_tools)
        files_section = builder.build_available_files_section(loaded_context_with_files)
        prompt = builder.build_system_prompt(
            skill=sample_skill,
            tool_descriptions=tool_descriptions,
            available_files_section=files_section,
            iteration=1,
            max_iterations=15,
        )

        assert "reference.md" in prompt
        assert "API reference documentation" in prompt

    def test_build_system_prompt_includes_iteration(
        self, sample_skill: Skill, sample_tools: list[ToolDefinition]
    ) -> None:
        """System prompt should include current iteration number."""
        builder = PromptBuilder()
        tool_descriptions = builder.format_tool_descriptions(sample_tools)
        prompt = builder.build_system_prompt(
            skill=sample_skill,
            tool_descriptions=tool_descriptions,
            available_files_section="",
            iteration=3,
            max_iterations=15,
        )

        assert "3/15" in prompt

    def test_format_tool_descriptions_with_parameters(
        self, sample_tools: list[ToolDefinition]
    ) -> None:
        """Tool descriptions should include parameter information."""
        builder = PromptBuilder()
        result = builder.format_tool_descriptions(sample_tools)

        assert "- read: Read a file" in result
        assert "file_path" in result
        assert "required" in result

    def test_format_tool_descriptions_empty_list(self) -> None:
        """Empty tool list should return appropriate message."""
        builder = PromptBuilder()
        result = builder.format_tool_descriptions([])

        assert result == "No tools available."

    def test_format_tool_descriptions_filters_allowed_tools(
        self, sample_tools: list[ToolDefinition]
    ) -> None:
        """Tool descriptions should filter by allowed_tools list."""
        builder = PromptBuilder()
        result = builder.format_tool_descriptions(sample_tools, allowed_tools=["read", "bash"])

        assert "- read:" in result
        assert "- bash:" in result
        assert "- write:" not in result

    def test_format_tool_descriptions_with_no_parameters(self) -> None:
        """Tool without parameters should format correctly."""
        builder = PromptBuilder()
        tool = ToolDefinition(
            name="simple_tool",
            type=ToolType.FUNCTION,
            description="A simple tool with no parameters",
            parameters=[],
        )
        result = builder.format_tool_descriptions([tool])

        assert "- simple_tool: A simple tool" in result

    def test_build_available_files_section_with_files(
        self, loaded_context_with_files: LoadedContext
    ) -> None:
        """Available files section should include all files."""
        builder = PromptBuilder()
        section = builder.build_available_files_section(loaded_context_with_files)

        assert "AVAILABLE SUPPORTING FILES" in section
        assert "reference.md" in section
        assert "API reference documentation" in section
        assert "1,200 lines" in section
        assert "examples.txt" in section
        assert "Usage examples" in section
        assert "500 lines" in section

    def test_build_available_files_section_includes_skill_dir(
        self, loaded_context_with_files: LoadedContext
    ) -> None:
        """Available files section should include skill directory."""
        builder = PromptBuilder()
        section = builder.build_available_files_section(loaded_context_with_files)

        assert "Skill directory: /skills/test-skill" in section

    def test_build_available_files_section_includes_usage_instruction(
        self, loaded_context_with_files: LoadedContext
    ) -> None:
        """Available files section should include usage instruction."""
        builder = PromptBuilder()
        section = builder.build_available_files_section(loaded_context_with_files)

        assert "'read' tool" in section.lower()

    def test_build_available_files_section_empty_context(
        self, empty_context: LoadedContext
    ) -> None:
        """Empty context should return empty string."""
        builder = PromptBuilder()
        section = builder.build_available_files_section(empty_context)

        assert section == ""

    def test_build_available_files_section_handles_missing_line_count(
        self, loaded_context_with_files: LoadedContext
    ) -> None:
        """Files without line count should still be included."""
        builder = PromptBuilder()
        section = builder.build_available_files_section(loaded_context_with_files)

        # config.json has no line count
        assert "config.json" in section
        assert "Configuration file" in section
        # Should not show line count for config.json
        config_line = [line for line in section.split("\n") if "config.json" in line][0]
        assert "lines)" not in config_line

    def test_build_available_files_section_sorts_files(
        self, loaded_context_with_files: LoadedContext
    ) -> None:
        """Files should be sorted alphabetically."""
        builder = PromptBuilder()
        section = builder.build_available_files_section(loaded_context_with_files)

        # Check order: config.json, examples.txt, reference.md
        config_pos = section.find("config.json")
        examples_pos = section.find("examples.txt")
        reference_pos = section.find("reference.md")

        assert config_pos < examples_pos < reference_pos

    def test_build_error_observation_includes_tool_name(self) -> None:
        """Error observation should include tool name."""
        builder = PromptBuilder()
        message = builder.build_error_observation(
            tool_name="read",
            error="File not found",
            retry_count=1,
        )

        assert "read" in message

    def test_build_error_observation_includes_error_message(self) -> None:
        """Error observation should include error message."""
        builder = PromptBuilder()
        message = builder.build_error_observation(
            tool_name="read",
            error="File not found: /missing/file.txt",
            retry_count=1,
        )

        assert "File not found: /missing/file.txt" in message

    def test_build_error_observation_includes_retry_count(self) -> None:
        """Error observation should include retry attempt number."""
        builder = PromptBuilder()
        message = builder.build_error_observation(
            tool_name="read",
            error="Error",
            retry_count=2,
        )

        assert "Attempt 2" in message

    def test_build_error_observation_suggests_alternatives(self) -> None:
        """Error observation should suggest trying alternatives."""
        builder = PromptBuilder()
        message = builder.build_error_observation(
            tool_name="read",
            error="Error",
            retry_count=1,
        )

        assert "alternative approach" in message.lower()
        assert "different parameters" in message.lower()


class TestIntegration:
    """Integration tests combining multiple components."""

    def test_complete_prompt_generation(
        self,
        sample_skill: Skill,
        sample_tools: list[ToolDefinition],
        loaded_context_with_files: LoadedContext,
    ) -> None:
        """Test complete prompt generation with all components."""
        builder = PromptBuilder()

        # Format tools
        tool_descriptions = builder.format_tool_descriptions(sample_tools)

        # Build files section
        files_section = builder.build_available_files_section(loaded_context_with_files)

        # Build complete prompt
        prompt = builder.build_system_prompt(
            skill=sample_skill,
            tool_descriptions=tool_descriptions,
            available_files_section=files_section,
            iteration=5,
            max_iterations=15,
        )

        # Verify all components are included
        assert "test-skill" in prompt
        assert "A test skill for unit testing" in prompt
        assert "Follow these instructions carefully" in prompt
        assert "read: Read a file" in prompt
        assert "reference.md" in prompt
        assert "5/15" in prompt
        assert "JSON format" in prompt

    def test_minimal_prompt_generation(self, sample_skill: Skill) -> None:
        """Test minimal prompt generation with no tools or files."""
        builder = PromptBuilder()

        prompt = builder.build_system_prompt(
            skill=sample_skill,
            tool_descriptions="No tools available.",
            available_files_section="",
            iteration=1,
            max_iterations=10,
        )

        # Verify essential components are still present
        assert "test-skill" in prompt
        assert "1/10" in prompt
        assert "JSON format" in prompt
