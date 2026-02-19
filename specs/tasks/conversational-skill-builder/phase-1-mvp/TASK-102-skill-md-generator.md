# TASK-102: SKILL.md Generator with Claude Code Compliance

**Phase**: 1 (MVP)
**Estimated Effort**: 12 hours
**Dependencies**: TASK-101
**Priority**: P0

## Objective

Create the SKILL.md generator that produces Claude Code-compliant skill files. The generator must strictly enforce frontmatter rules and integrate with existing SkillParser for validation.

## Requirements

- Create `SkillMdGenerator` class that generates valid SKILL.md content
- Create `SkillMdContent` model with `to_markdown()` method
- Implement `SkillSpec` model for skill specification input
- Enforce allowed frontmatter fields (name, description, allowed-tools, model, context, user-invocable, priority, tags)
- Block forbidden fields (schedule, trigger, created-by, source, author)
- Integrate with existing `SkillParser` for validation after generation
- Use LLM to generate natural language instructions body
- Create `SkillWriter` class to write SKILL.md files to tenant storage

## Implementation Notes

- Reference technical plan Section 5.1.3 for `SkillMdGenerator` specification
- Reference technical plan Section 7.3 for `SkillWriter` specification
- Use existing `SkillParser` from `src/omniforge/skills/parser.py` for validation
- Follow Claude Code frontmatter rules exactly (Section 2.3 of technical plan)
- SKILL.md body should use imperative voice with clear sections
- Maximum 5KB total size per skill file

## Acceptance Criteria

- [ ] `SkillMdGenerator.generate()` produces valid SKILL.md content
- [ ] `validate_frontmatter()` rejects forbidden fields with clear error messages
- [ ] Generated SKILL.md passes existing `SkillParser.parse_full()` validation
- [ ] `SkillWriter` writes files to correct tenant/agent directory structure
- [ ] LLM-generated body follows template: heading, prerequisites, instructions, error handling
- [ ] Unit tests cover frontmatter validation edge cases
- [ ] Integration test verifies end-to-end generation and parsing
- [ ] 90%+ test coverage for frontmatter validation (per review requirements)

## Files to Create/Modify

- `src/omniforge/builder/generation/__init__.py` - Generation package init
- `src/omniforge/builder/generation/skill_md_generator.py` - SkillMdGenerator, SkillMdContent, SkillSpec
- `src/omniforge/builder/generation/prompts.py` - LLM prompts for body generation
- `src/omniforge/builder/storage/__init__.py` - Storage package init
- `src/omniforge/builder/storage/skill_writer.py` - SkillWriter class
- `tests/builder/generation/__init__.py` - Test package
- `tests/builder/generation/test_skill_md_generator.py` - Generator tests
- `tests/builder/storage/test_skill_writer.py` - Writer tests
