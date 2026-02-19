# TASK-004: SKILL.md Generator

**Phase**: 1 (MVP)
**Complexity**: Medium-High
**Estimated Effort**: 4-5 hours
**Dependencies**: TASK-001

## Description

Implement the SkillMdGenerator class that generates SKILL.md content strictly following the official Anthropic Agent Skills format. This is a critical component that must ensure 100% compliance with the official specification.

## Requirements

### Location
- Create `src/omniforge/skills/creation/generator.py`
- Update `src/omniforge/skills/creation/prompts.py` with generation prompts

### SkillMdGenerator Class

```python
class SkillMdGenerator:
    """Generate SKILL.md content following official Anthropic format.

    CRITICAL CONSTRAINTS (from official docs):
    - Frontmatter: ONLY `name` and `description` fields
    - Name: max 64 chars, lowercase letters/numbers/hyphens, gerund preferred
    - Description: max 1024 chars, third person, includes WHAT and WHEN
    - Body: under 500 lines (~5k tokens)
    """

    def __init__(self, llm_generator: LLMResponseGenerator) -> None: ...

    async def generate(self, context: ConversationContext) -> str:
        """Generate complete SKILL.md content in official format."""

    def generate_frontmatter(self, context: ConversationContext) -> str:
        """Generate YAML frontmatter with ONLY name and description."""

    async def generate_body(self, context: ConversationContext) -> str:
        """Generate Markdown instruction body under 500 lines."""

    def validate_name_format(self, name: str) -> tuple[bool, Optional[str]]:
        """Validate skill name against official requirements."""

    async def fix_validation_errors(
        self,
        content: str,
        errors: list[str],
    ) -> str:
        """Attempt to fix validation errors in generated content."""
```

### Frontmatter Format (CRITICAL)

```yaml
---
name: skill-name-here           # ONLY these two fields
description: Description here   # No other frontmatter allowed
---
```

### Generation Strategy

1. **Frontmatter**: Use strict template with ONLY name and description
2. **Body Generation**: LLM-powered with conciseness focus
3. **Post-Processing**: Strip any unauthorized frontmatter fields
4. **Line Count Check**: Verify body is under 500 lines

### Prompt Templates

```python
SKILL_MD_GENERATION_PROMPT = """Generate a SKILL.md file following EXACT official Anthropic format.

CRITICAL REQUIREMENTS:
1. Frontmatter must have ONLY `name` and `description` fields (NO other fields)
2. Name: "{name}" (already validated)
3. Description: "{description}" (already validated)
4. Body: Clear, concise instructions under 500 lines
5. Assume Claude is smart - only add knowledge Claude doesn't have
6. Use imperative form in instructions
7. No time-sensitive information

Purpose: {purpose}
Pattern: {pattern}
Examples: {examples}

Generate the complete SKILL.md content.
Start with exactly:
---
name: {name}
description: {description}
---

Then add the Markdown body with instructions:
"""

FIX_VALIDATION_ERRORS_PROMPT = """Fix these validation errors in the SKILL.md:

ERRORS:
{errors}

CURRENT CONTENT:
{content}

CRITICAL RULES:
1. Frontmatter must have ONLY `name` and `description` fields
2. Description must be third person and include WHAT and WHEN
3. Body must be under 500 lines

Fix the errors and output the corrected SKILL.md:
"""
```

## Acceptance Criteria

- [ ] generate() produces valid SKILL.md with only name/description frontmatter
- [ ] generate_frontmatter() outputs exactly 2 fields (name, description)
- [ ] generate_body() produces content under 500 lines
- [ ] validate_name_format() catches all invalid name formats
- [ ] fix_validation_errors() successfully corrects common issues
- [ ] Post-processing strips any unauthorized frontmatter fields
- [ ] Unit tests verify frontmatter compliance
- [ ] Test coverage > 85%

## Technical Notes

- Use string templates for frontmatter (not LLM generation) to ensure compliance
- LLM generates body content only
- Always post-process to remove unauthorized fields
- Count lines accurately (handle edge cases with empty lines)

## Test Cases

```python
async def test_generate_frontmatter_only_two_fields():
    generator = SkillMdGenerator(mock_llm)
    ctx = ConversationContext(
        skill_name="format-names",
        skill_description="Formats names..."
    )
    frontmatter = generator.generate_frontmatter(ctx)
    # Parse YAML and verify only name, description
    parsed = yaml.safe_load(frontmatter.strip("---\n"))
    assert set(parsed.keys()) == {"name", "description"}

def test_validate_name_format_valid():
    is_valid, error = generator.validate_name_format("format-product-names")
    assert is_valid is True
    assert error is None

def test_validate_name_format_invalid_uppercase():
    is_valid, error = generator.validate_name_format("Format-Names")
    assert is_valid is False
    assert "lowercase" in error.lower()
```
