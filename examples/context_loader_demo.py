#!/usr/bin/env python
"""Demo of progressive context loading for skills.

This example demonstrates how to use the ContextLoader to progressively load
skill context, saving tokens by initially loading only SKILL.md and deferring
supporting file loading until needed.
"""

from pathlib import Path

from omniforge.skills import ContextLoader, SkillLoader, StorageConfig


def main() -> None:
    """Demo progressive context loading."""
    print("=" * 80)
    print("Progressive Context Loading Demo")
    print("=" * 80)
    print()

    # Setup skill loader
    project_root = Path(__file__).parent.parent
    skills_dir = project_root / "src" / "omniforge" / "skills"

    config = StorageConfig(project_path=skills_dir)
    skill_loader = SkillLoader(config)

    # Build index
    print(f"Scanning skills directory: {skills_dir}")
    count = skill_loader.build_index()
    print(f"Found {count} skills")
    print()

    # List available skills
    print("Available skills:")
    for entry in skill_loader.list_skills():
        print(f"  - {entry.name}: {entry.description}")
    print()

    # Select a skill to load
    skill_name = "data-processor"
    print(f"Loading skill: {skill_name}")
    skill = skill_loader.load_skill(skill_name)
    print(f"Skill path: {skill.path}")
    print()

    # Create context loader
    context_loader = ContextLoader(skill)

    # Load initial context (only SKILL.md content)
    print("Loading initial context...")
    context = context_loader.load_initial_context()

    print(f"Skill content loaded: {context.line_count} lines")
    print(f"Available supporting files: {len(context.available_files)}")
    print()

    # Display available supporting files
    if context.available_files:
        print("Supporting files discovered:")
        for filename, file_ref in context.available_files.items():
            line_info = ""
            if file_ref.estimated_lines:
                line_info = f" (~{file_ref.estimated_lines:,} lines)"
            print(f"  - {filename}{line_info}")
            print(f"    Path: {file_ref.path}")
            print(f"    Description: {file_ref.description}")
            print()
    else:
        print("No supporting files found in SKILL.md")
        print()

    # Build system prompt section
    prompt_section = context_loader.build_available_files_prompt(context)
    if prompt_section:
        print("Generated prompt section:")
        print("-" * 80)
        print(prompt_section)
        print("-" * 80)
        print()

    # Simulate loading files on-demand
    if context.available_files:
        print("Simulating on-demand file loading...")
        first_file = next(iter(context.available_files.keys()))
        print(f"Agent requests: {first_file}")
        context_loader.mark_file_loaded(first_file)
        print(f"Loaded files: {context_loader.get_loaded_files()}")
        print()

    # Calculate token savings
    skill_tokens = context.line_count * 4  # Rough estimate: 4 tokens per line
    supporting_tokens = sum(
        (ref.estimated_lines or 50) * 4 for ref in context.available_files.values()
    )
    total_tokens = skill_tokens + supporting_tokens

    print("Token Usage Estimate:")
    print(f"  Initial load (SKILL.md only): ~{skill_tokens} tokens")
    print(f"  Supporting files (deferred): ~{supporting_tokens} tokens")
    print(f"  Total if loaded upfront: ~{total_tokens} tokens")
    savings_pct = supporting_tokens / total_tokens * 100 if total_tokens > 0 else 0
    print(f"  Token savings: ~{supporting_tokens} tokens ({savings_pct:.1f}%)")
    print()


if __name__ == "__main__":
    main()
