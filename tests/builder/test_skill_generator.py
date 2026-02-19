"""Tests for SKILL.md generator."""

import tempfile
from pathlib import Path

import pytest

from omniforge.builder.skill_generator import (
    FORBIDDEN_FRONTMATTER,
    SkillGenerationRequest,
    SkillMdGenerator,
)


class TestSkillGenerationRequest:
    """Tests for SkillGenerationRequest model."""

    def test_minimal_request(self) -> None:
        """Test creating minimal skill generation request."""
        request = SkillGenerationRequest(
            skill_id="test-skill",
            name="Test Skill",
            description="A test skill for validation",
            purpose="Test purpose",
            steps=["Step 1", "Step 2"],
        )

        assert request.skill_id == "test-skill"
        assert request.name == "Test Skill"
        assert len(request.steps) == 2

    def test_complete_request(self) -> None:
        """Test creating complete skill generation request."""
        request = SkillGenerationRequest(
            skill_id="notion-weekly-report",
            name="Notion Weekly Report",
            description="Generate weekly status reports from Notion databases",
            integration_type="notion",
            purpose="Generate formatted weekly status reports",
            inputs=["Database IDs", "Date range"],
            outputs=["Markdown report file"],
            allowed_tools=["ExternalAPI", "Read", "Write"],
            prerequisites=[
                "Notion API credentials configured",
                "Target databases accessible",
            ],
            steps=[
                "Query Notion API for updated items",
                "Extract project data",
                "Format as markdown report",
                "Write to output file",
            ],
            error_handling=[
                "If API fails: Retry up to 3 times",
                "If database not found: Skip and log error",
            ],
            examples=[
                {
                    "title": "Basic Usage",
                    "description": "Generate report for last 7 days",
                    "code": "python generate_report.py --days 7",
                }
            ],
        )

        assert request.skill_id == "notion-weekly-report"
        assert len(request.inputs) == 2
        assert len(request.outputs) == 1
        assert len(request.allowed_tools) == 3
        assert len(request.prerequisites) == 2
        assert len(request.steps) == 4
        assert len(request.error_handling) == 2
        assert len(request.examples) == 1


class TestSkillMdGenerator:
    """Tests for SkillMdGenerator."""

    def test_generate_minimal_skill(self) -> None:
        """Test generating minimal SKILL.md content."""
        generator = SkillMdGenerator()
        request = SkillGenerationRequest(
            skill_id="simple-skill",
            name="Simple Skill",
            description="A simple test skill",
            purpose="Test purpose",
            steps=["Do something", "Do something else"],
        )

        content = generator.generate(request)

        # Check frontmatter
        assert "---" in content
        assert "name: simple-skill" in content
        assert "description: A simple test skill" in content
        assert "model: claude-sonnet-4-5" in content
        assert "context: inherit" in content
        assert "user-invocable: false" in content
        assert "priority: 0" in content

        # Check instructions
        assert "# Simple Skill" in content
        assert "## Instructions" in content
        assert "1. Do something" in content
        assert "2. Do something else" in content

        # Check forbidden fields NOT present
        assert "schedule:" not in content
        assert "trigger:" not in content
        assert "created-by:" not in content
        assert "source:" not in content

    def test_generate_skill_with_allowed_tools(self) -> None:
        """Test generating skill with allowed-tools restriction."""
        generator = SkillMdGenerator()
        request = SkillGenerationRequest(
            skill_id="restricted-skill",
            name="Restricted Skill",
            description="Skill with tool restrictions",
            purpose="Test restrictions",
            allowed_tools=["Read", "Write", "Bash"],
            steps=["Execute commands"],
        )

        content = generator.generate(request)

        assert "allowed-tools:" in content
        assert "  - Read" in content
        assert "  - Write" in content
        assert "  - Bash" in content

    def test_generate_skill_with_integration_tags(self) -> None:
        """Test generating skill with integration type tags."""
        generator = SkillMdGenerator()
        request = SkillGenerationRequest(
            skill_id="notion-skill",
            name="Notion Skill",
            description="Notion integration skill",
            integration_type="notion",
            purpose="Integrate with Notion",
            steps=["Call Notion API"],
        )

        content = generator.generate(request)

        assert "tags:" in content
        assert "  - notion" in content
        assert "  - automation" in content

    def test_generate_skill_with_prerequisites(self) -> None:
        """Test generating skill with prerequisites section."""
        generator = SkillMdGenerator()
        request = SkillGenerationRequest(
            skill_id="prereq-skill",
            name="Skill with Prerequisites",
            description="Test prerequisites",
            purpose="Test prereqs",
            prerequisites=[
                "API credentials configured",
                "Database accessible",
                "Valid date range",
            ],
            steps=["Execute task"],
        )

        content = generator.generate(request)

        assert "## Prerequisites" in content
        assert "Before executing this skill:" in content
        assert "- API credentials configured" in content
        assert "- Database accessible" in content
        assert "- Valid date range" in content

    def test_generate_skill_with_inputs_outputs(self) -> None:
        """Test generating skill with inputs and outputs."""
        generator = SkillMdGenerator()
        request = SkillGenerationRequest(
            skill_id="io-skill",
            name="I/O Skill",
            description="Skill with I/O",
            purpose="Test I/O",
            inputs=["Database ID", "Date range", "Output format"],
            outputs=["Report file", "Summary statistics"],
            steps=["Process data"],
        )

        content = generator.generate(request)

        assert "## Required Inputs" in content
        assert "- Database ID" in content
        assert "- Date range" in content

        assert "## Expected Outputs" in content
        assert "- Report file" in content
        assert "- Summary statistics" in content

    def test_generate_skill_with_error_handling(self) -> None:
        """Test generating skill with error handling."""
        generator = SkillMdGenerator()
        request = SkillGenerationRequest(
            skill_id="error-skill",
            name="Error Handling Skill",
            description="Skill with error handling",
            purpose="Test errors",
            steps=["Execute task"],
            error_handling=[
                "If API fails: Retry up to 3 times with exponential backoff",
                "If database not found: Log error and skip",
                "If timeout: Return partial results",
            ],
        )

        content = generator.generate(request)

        assert "## Error Handling" in content
        assert "- If API fails: Retry up to 3 times" in content
        assert "- If database not found: Log error and skip" in content

    def test_generate_skill_with_examples(self) -> None:
        """Test generating skill with example usage."""
        generator = SkillMdGenerator()
        request = SkillGenerationRequest(
            skill_id="example-skill",
            name="Skill with Examples",
            description="Test examples",
            purpose="Test example generation",
            steps=["Execute"],
            examples=[
                {
                    "title": "Basic Usage",
                    "description": "Generate a simple report",
                    "code": "python scripts/generate.py --format simple",
                },
                {
                    "title": "Advanced Usage",
                    "description": "Generate detailed report with filters",
                    "code": "python scripts/generate.py --format detailed --filter status=active",
                },
            ],
        )

        content = generator.generate(request)

        assert "## Examples" in content
        assert "**Basic Usage**:" in content
        assert "Generate a simple report" in content
        assert "```" in content
        assert "python scripts/generate.py --format simple" in content

        assert "**Advanced Usage**:" in content
        assert "--filter status=active" in content

    def test_validate_skill_id_rejects_invalid(self) -> None:
        """Test skill_id validation rejects invalid formats."""
        generator = SkillMdGenerator()

        # Invalid: contains special characters
        with pytest.raises(ValueError, match="kebab-case alphanumeric"):
            generator._validate_skill_id("invalid@skill")

        # Invalid: contains spaces
        with pytest.raises(ValueError, match="kebab-case alphanumeric"):
            generator._validate_skill_id("invalid skill")

        # Valid: kebab-case
        generator._validate_skill_id("valid-skill-name")

        # Valid: underscores
        generator._validate_skill_id("valid_skill_name")

    def test_save_creates_file(self) -> None:
        """Test saving SKILL.md creates file in correct location."""
        generator = SkillMdGenerator()
        request = SkillGenerationRequest(
            skill_id="saved-skill",
            name="Saved Skill",
            description="Test file save",
            purpose="Test save",
            steps=["Execute"],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "skills"
            output_file = generator.save(request, output_dir)

            assert output_file.exists()
            assert output_file.name == "saved-skill.md"

            content = output_file.read_text()
            assert "name: saved-skill" in content
            assert "# Saved Skill" in content

    def test_validate_frontmatter_rejects_forbidden_fields(self) -> None:
        """Test frontmatter validation rejects forbidden fields."""
        generator = SkillMdGenerator()

        # Valid frontmatter
        valid = {
            "name": "test-skill",
            "description": "Test skill",
            "allowed-tools": ["Read", "Write"],
        }
        generator.validate_frontmatter(valid)  # Should not raise

        # Invalid: contains forbidden fields
        for forbidden_field in FORBIDDEN_FRONTMATTER:
            invalid = {
                "name": "test",
                forbidden_field: "some-value",
            }
            with pytest.raises(ValueError, match="forbidden fields"):
                generator.validate_frontmatter(invalid)

    def test_description_length_validation(self) -> None:
        """Test description must be <= 80 characters."""
        # Valid: 80 characters exactly
        SkillGenerationRequest(
            skill_id="test",
            name="Test",
            description="A" * 80,
            purpose="Test",
            steps=["Do something"],
        )

        # Invalid: 81 characters
        with pytest.raises(ValueError):
            SkillGenerationRequest(
                skill_id="test",
                name="Test",
                description="A" * 81,
                purpose="Test",
                steps=["Do something"],
            )

    def test_must_have_at_least_one_step(self) -> None:
        """Test skill must have at least one instruction step."""
        # Valid: has steps
        SkillGenerationRequest(
            skill_id="test",
            name="Test",
            description="Test",
            purpose="Test",
            steps=["Step 1"],
        )

        # Invalid: no steps
        with pytest.raises(ValueError):
            SkillGenerationRequest(
                skill_id="test",
                name="Test",
                description="Test",
                purpose="Test",
                steps=[],
            )

    def test_complete_skill_format_compliance(self) -> None:
        """Test generated skill follows complete Claude Code format."""
        generator = SkillMdGenerator()
        request = SkillGenerationRequest(
            skill_id="notion-weekly-report",
            name="Notion Weekly Report Generator",
            description="Generate weekly status reports from Notion project databases",
            integration_type="notion",
            purpose="Generate formatted weekly status reports from Notion.",
            inputs=["Database IDs", "Date range (default: last 7 days)"],
            outputs=["Markdown report file in reports/ directory"],
            allowed_tools=["ExternalAPI", "Read", "Write"],
            prerequisites=[
                "Notion API credentials configured",
                "Target databases accessible",
                "Output directory exists",
            ],
            steps=[
                "Query Notion API for items updated in date range",
                "Extract project name, status, owner, blockers",
                "Group projects by client",
                "Sort by status: At Risk → On Track → Complete",
                "Format as markdown bulleted list",
                "Write to reports/weekly-YYYY-MM-DD.md",
            ],
            error_handling=[
                "If API fails: Retry up to 3 times with exponential backoff",
                "If database not found: Log error, skip that database",
                "If no updates found: Generate report with 'No updates this week'",
            ],
            examples=[
                {
                    "title": "Generate Last Week's Report",
                    "description": "Generate report for previous 7 days",
                    "code": "# Executed automatically on schedule\n# Output: reports/weekly-2026-01-20.md",
                }
            ],
        )

        content = generator.generate(request)

        # Frontmatter compliance
        lines = content.split("\n")
        assert lines[0] == "---"
        assert "name: notion-weekly-report" in content
        assert "description: Generate weekly status reports" in content
        assert "allowed-tools:" in content
        assert "model: claude-sonnet-4-5" in content
        assert "context: inherit" in content
        assert "user-invocable: false" in content
        assert "tags:" in content
        assert "  - notion" in content

        # Instructions compliance
        assert "# Notion Weekly Report Generator" in content
        assert "## Prerequisites" in content
        assert "## Instructions" in content
        assert "1. Query Notion API" in content
        assert "6. Write to reports" in content
        assert "## Required Inputs" in content
        assert "## Expected Outputs" in content
        assert "## Error Handling" in content
        assert "## Examples" in content

        # Progressive disclosure - core instructions only
        # No inline API docs, no inline code - those go in docs/ and scripts/
        assert "See [" not in content  # No references yet (would be added manually)
        assert len(content) < 2000  # Keep it concise (< 2KB for core instructions)
