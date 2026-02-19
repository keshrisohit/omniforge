"""SKILL.md generator following Claude Code format.

Generates skill files from conversational requirements with proper frontmatter,
instructions, and progressive disclosure.
"""

import re
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field


class SkillGenerationRequest(BaseModel):
    """Request to generate a SKILL.md file.

    Attributes:
        skill_id: Unique skill identifier (kebab-case)
        name: Human-readable skill name
        description: One-line description for agent discovery (max 80 chars)
        integration_type: What integration this skill uses (notion, slack, etc.)
        purpose: What the skill accomplishes
        inputs: Expected inputs/parameters
        outputs: What the skill produces
        allowed_tools: Tools the skill can use
        prerequisites: Requirements before skill execution
        steps: Step-by-step instructions
        error_handling: How to handle failures
        examples: Example usage scenarios
    """

    skill_id: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=80)
    integration_type: Optional[str] = None
    purpose: str = Field(..., min_length=1)
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    allowed_tools: list[str] = Field(default_factory=list)
    prerequisites: list[str] = Field(default_factory=list)
    steps: list[str] = Field(..., min_length=1)
    error_handling: list[str] = Field(default_factory=list)
    examples: list[dict[str, str]] = Field(default_factory=list)


# Claude Code allowed frontmatter fields
ALLOWED_FRONTMATTER = {
    "name",
    "description",
    "allowed-tools",
    "model",
    "context",
    "user-invocable",
    "priority",
    "tags",
}

# Forbidden fields (belong in agent.json, not SKILL.md)
FORBIDDEN_FRONTMATTER = {
    "schedule",
    "trigger",
    "created-by",
    "source",
    "author",
    "created-at",
    "updated-at",
}


class SkillMdGenerator:
    """Generates Claude Code-compliant SKILL.md files."""

    def __init__(self) -> None:
        """Initialize generator."""
        pass

    def generate(self, request: SkillGenerationRequest) -> str:
        """Generate SKILL.md content from request.

        Args:
            request: Skill generation parameters

        Returns:
            Complete SKILL.md file content following Claude Code format

        Raises:
            ValueError: If skill_id is invalid
        """
        self._validate_skill_id(request.skill_id)

        # Build frontmatter
        frontmatter = self._build_frontmatter(request)

        # Build skill instructions
        instructions = self._build_instructions(request)

        # Combine into complete SKILL.md
        return f"{frontmatter}\n\n{instructions}"

    def _validate_skill_id(self, skill_id: str) -> None:
        """Validate skill_id follows kebab-case naming.

        Args:
            skill_id: Skill identifier to validate

        Raises:
            ValueError: If skill_id is invalid
        """
        if not skill_id.replace("-", "").replace("_", "").isalnum():
            raise ValueError(
                f"skill_id must be kebab-case alphanumeric with hyphens: {skill_id}"
            )

    def _build_frontmatter(self, request: SkillGenerationRequest) -> str:
        """Build YAML frontmatter following Claude Code format.

        Args:
            request: Skill generation parameters

        Returns:
            YAML frontmatter string with --- delimiters
        """
        lines = ["---"]

        # Required fields
        lines.append(f"name: {request.skill_id}")
        lines.append(f"description: {request.description}")

        # Optional: allowed-tools
        if request.allowed_tools:
            lines.append("allowed-tools:")
            for tool in request.allowed_tools:
                lines.append(f"  - {tool}")

        # Optional: model (default to sonnet for most use cases)
        lines.append("model: claude-sonnet-4-5")

        # Optional: context (default to inherit)
        lines.append("context: inherit")

        # Optional: user-invocable (default false for agent-internal skills)
        lines.append("user-invocable: false")

        # OmniForge extensions
        lines.append("priority: 0")

        # Tags based on integration type
        if request.integration_type:
            lines.append("tags:")
            lines.append(f"  - {request.integration_type}")
            lines.append("  - automation")

        lines.append("---")

        return "\n".join(lines)

    def _build_instructions(self, request: SkillGenerationRequest) -> str:
        """Build skill instructions in natural language.

        Args:
            request: Skill generation parameters

        Returns:
            Markdown-formatted skill instructions
        """
        sections = []

        # Title
        sections.append(f"# {request.name}")
        sections.append("")
        sections.append(request.purpose)
        sections.append("")

        # Prerequisites
        if request.prerequisites:
            sections.append("## Prerequisites")
            sections.append("")
            sections.append("Before executing this skill:")
            for prereq in request.prerequisites:
                sections.append(f"- {prereq}")
            sections.append("")

        # Instructions
        sections.append("## Instructions")
        sections.append("")
        for i, step in enumerate(request.steps, 1):
            sections.append(f"{i}. {step}")
        sections.append("")

        # Inputs/Outputs (if specified)
        if request.inputs:
            sections.append("## Required Inputs")
            sections.append("")
            for inp in request.inputs:
                sections.append(f"- {inp}")
            sections.append("")

        if request.outputs:
            sections.append("## Expected Outputs")
            sections.append("")
            for out in request.outputs:
                sections.append(f"- {out}")
            sections.append("")

        # Error Handling
        if request.error_handling:
            sections.append("## Error Handling")
            sections.append("")
            for error_step in request.error_handling:
                sections.append(f"- {error_step}")
            sections.append("")

        # Examples
        if request.examples:
            sections.append("## Examples")
            sections.append("")
            for example in request.examples:
                sections.append(f"**{example.get('title', 'Example')}**:")
                sections.append("")
                sections.append(example.get("description", ""))
                if "code" in example:
                    sections.append("")
                    sections.append("```")
                    sections.append(example["code"])
                    sections.append("```")
                sections.append("")

        return "\n".join(sections)

    def save(self, request: SkillGenerationRequest, output_dir: Path) -> Path:
        """Generate and save SKILL.md file.

        Args:
            request: Skill generation parameters
            output_dir: Directory to save skill file

        Returns:
            Path to created SKILL.md file
        """
        content = self.generate(request)

        # Create output directory if needed
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save to {skill_id}.md
        output_file = output_dir / f"{request.skill_id}.md"
        output_file.write_text(content, encoding="utf-8")

        return output_file

    def validate_frontmatter(self, frontmatter: dict[str, Any]) -> None:
        """Validate frontmatter contains only allowed fields.

        Args:
            frontmatter: Frontmatter dictionary to validate

        Raises:
            ValueError: If frontmatter contains forbidden fields
        """
        forbidden_found = set(frontmatter.keys()) & FORBIDDEN_FRONTMATTER
        if forbidden_found:
            raise ValueError(
                f"Frontmatter contains forbidden fields: {forbidden_found}. "
                f"These fields belong in agent.json, not SKILL.md"
            )

        # Warn about unknown fields (not forbidden, but not standard)
        unknown = set(frontmatter.keys()) - ALLOWED_FRONTMATTER
        if unknown:
            print(
                f"Warning: Frontmatter contains non-standard fields: {unknown}. "
                f"These may not be recognized by Claude Code."
            )
