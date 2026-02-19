# TASK-005: Skill Validator (Anthropic Spec)

**Phase**: 1 (MVP)
**Complexity**: Medium
**Estimated Effort**: 3-4 hours
**Dependencies**: TASK-004

## Description

Implement the SkillValidator class that validates generated SKILL.md content against the official Anthropic Agent Skills specification. This validator ensures strict compliance with frontmatter fields, name format, description format, and body length constraints.

## Requirements

### Location
- Create `src/omniforge/skills/creation/validator.py`

### SkillValidator Class

```python
class SkillValidator:
    """Validate SKILL.md content against official Anthropic specification.

    Validation Rules (from official docs):
    1. Frontmatter has ONLY `name` and `description` fields
    2. Name: max 64 chars, lowercase letters/numbers/hyphens, starts with letter
    3. Description: non-empty, max 1024 chars, third person
    4. Description: includes WHAT and WHEN (trigger context)
    5. Body: under 500 lines
    6. No time-sensitive information (warning only)
    """

    def __init__(self, parser: SkillParser) -> None: ...

    def validate(self, content: str, skill_name: str) -> ValidationResult:
        """Validate SKILL.md content string against official spec."""

    def validate_frontmatter_fields(
        self, frontmatter: dict[str, Any]
    ) -> list[str]:
        """Ensure frontmatter has ONLY name and description."""

    def validate_name(self, name: str) -> list[str]:
        """Validate name against official requirements."""

    def validate_description(self, description: str) -> list[str]:
        """Validate description against official requirements."""

    def validate_body_length(self, body: str) -> list[str]:
        """Validate body is under 500 lines."""

    def check_time_sensitive_content(self, content: str) -> list[str]:
        """Warn about time-sensitive information (warning only)."""
```

### Validation Pipeline

```
Generated Content
       |
       v
+------------------------+
| YAML Parse Check       | --> Invalid YAML? Return parse error
+------------------------+
       |
       v
+------------------------+
| Frontmatter Fields     | --> Has ANY field other than name/description?
| (STRICT: only 2)       |     Return "unauthorized fields" error
+------------------------+
       |
       v
+------------------------+
| Name Validation        | --> Max 64 chars, lowercase+numbers+hyphens,
|                        |     starts with letter, no reserved words
+------------------------+
       |
       v
+------------------------+
| Description Validation | --> Non-empty, max 1024 chars, third person,
|                        |     includes WHAT and WHEN
+------------------------+
       |
       v
+------------------------+
| Body Line Count        | --> Over 500 lines? Return size error
+------------------------+
       |
       v
+------------------------+
| Time-Sensitive Check   | --> Contains dates, "currently", etc.?
| (Warning only)         |     Add warning
+------------------------+
       |
       v
    VALID
```

### Validation Details

**Name Validation:**
- Max 64 characters
- Pattern: `^[a-z][a-z0-9-]*$`
- Reserved words: skill, agent, tool, system, admin, root

**Description Validation:**
- Non-empty
- Max 1024 characters
- Third person check: Should not start with imperative verb
- WHEN trigger check: Should contain trigger indicators

**Third Person Heuristics:**
```python
imperative_starts = ["format", "create", "build", "process", "handle",
                     "generate", "convert", "extract", "analyze"]
```

**WHEN Trigger Indicators:**
```python
trigger_indicators = ["use when", "use for", "applies when", "triggered by",
                      "invoke when", "helpful for", "designed for"]
```

## Acceptance Criteria

- [ ] validate() returns ValidationResult with errors/warnings
- [ ] validate_frontmatter_fields() rejects unauthorized fields
- [ ] validate_name() catches all invalid name formats
- [ ] validate_description() detects imperative descriptions
- [ ] validate_description() warns about missing WHEN context
- [ ] validate_body_length() catches >500 line bodies
- [ ] check_time_sensitive_content() warns about dates/years
- [ ] Integration with existing SkillParser
- [ ] Unit tests for all validation rules
- [ ] Test coverage > 90%

## Technical Notes

- Reuse existing SkillParser for YAML parsing
- Use regex for pattern matching
- Return errors as list for easy aggregation
- Separate errors (blocking) from warnings (informational)

## Test Cases

```python
def test_validate_frontmatter_with_extra_fields():
    validator = SkillValidator(parser)
    frontmatter = {"name": "test", "description": "Test", "tags": ["a"]}
    errors = validator.validate_frontmatter_fields(frontmatter)
    assert len(errors) == 1
    assert "unauthorized" in errors[0].lower()

def test_validate_description_imperative():
    errors = validator.validate_description("Format all product names...")
    assert any("third person" in e.lower() for e in errors)

def test_validate_description_missing_when():
    errors = validator.validate_description("Formats product names correctly.")
    assert any("when" in e.lower() for e in errors)

def test_validate_body_over_500_lines():
    body = "\n".join(["line"] * 501)
    errors = validator.validate_body_length(body)
    assert len(errors) == 1
    assert "500" in errors[0]
```
