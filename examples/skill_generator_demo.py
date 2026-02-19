"""Demo of SkillMdGenerator for creating SKILL.md files.

This example demonstrates how to use the SkillMdGenerator to create
Anthropic-compliant SKILL.md files with proper frontmatter and body content.
"""

import asyncio

from omniforge.chat.llm_generator import LLMResponseGenerator
from omniforge.skills.creation import (
    ConversationContext,
    ConversationState,
    SkillMdGenerator,
    SkillPattern,
)


async def main() -> None:
    """Demonstrate SKILL.md generation."""
    print("=== SkillMdGenerator Demo ===\n")

    # Initialize LLM generator (will use configured default model)
    llm_generator = LLMResponseGenerator()

    # Create SKILL.md generator
    generator = SkillMdGenerator(llm_generator)

    # Create sample context with skill information
    context = ConversationContext(
        state=ConversationState.GENERATING,
        skill_name="format-product-names",
        skill_description=(
            "Formats product names into their full display form when writing "
            "documentation. Use when abbreviations need to be expanded consistently."
        ),
        skill_purpose="Expand product abbreviations consistently across documentation",
        skill_pattern=SkillPattern.SIMPLE,
        examples=[
            "API -> Application Programming Interface",
            "DB -> Database",
            "UI -> User Interface",
        ],
        triggers=[
            "Writing documentation",
            "Creating customer-facing content",
            "Generating reports",
        ],
    )

    print("Context:")
    print(f"  Name: {context.skill_name}")
    print(f"  Pattern: {context.skill_pattern.value}")
    print(f"  Examples: {len(context.examples)}")
    print()

    # Generate frontmatter (fast, no LLM call)
    print("Generating frontmatter...")
    frontmatter = generator.generate_frontmatter(context)
    print(frontmatter)
    print()

    # Validate name format
    print("Validating name format...")
    is_valid, error = generator.validate_name_format(context.skill_name)
    if is_valid:
        print(f"  ✓ Name '{context.skill_name}' is valid")
    else:
        print(f"  ✗ Name validation error: {error}")
    print()

    # Generate complete SKILL.md (uses LLM for body)
    print("Generating complete SKILL.md content...")
    print("(This will call the LLM to generate the body content)\n")

    try:
        skill_md_content = await generator.generate(context)

        print("=== Generated SKILL.md ===")
        print(skill_md_content)
        print()

        # Show some statistics
        lines = skill_md_content.split("\n")
        print(f"Statistics:")
        print(f"  Total lines: {len(lines)}")
        print(f"  Body lines: {len(lines) - 4}")  # Subtract frontmatter lines
        print(f"  Under 500 line limit: {len(lines) < 500}")
        print()

        # Validate frontmatter compliance
        print("Frontmatter compliance check:")
        if skill_md_content.startswith("---\n"):
            frontmatter_end = skill_md_content.find("---", 4)
            if frontmatter_end > 0:
                frontmatter_section = skill_md_content[4:frontmatter_end].strip()
                lines_in_frontmatter = frontmatter_section.split("\n")

                # Check that we have exactly 2 fields
                has_name = any(line.startswith("name:") for line in lines_in_frontmatter)
                has_desc = any(
                    line.startswith("description:") for line in lines_in_frontmatter
                )

                if has_name and has_desc and len(lines_in_frontmatter) == 2:
                    print("  ✓ Frontmatter has ONLY name and description fields")
                else:
                    print(f"  ✗ Frontmatter has {len(lines_in_frontmatter)} fields")

    except Exception as e:
        print(f"Error generating SKILL.md: {e}")


if __name__ == "__main__":
    asyncio.run(main())
