# TASK-004: Extend SkillMetadata with autonomous execution fields

**Priority:** P0 (Must Have)
**Estimated Effort:** Small (<1 day)
**Dependencies:** None

---

## Description

Extend the existing `SkillMetadata` model to support autonomous execution configuration fields. Add new fields for execution_mode, max_iterations, max_retries, timeout, and early_termination. Ensure backward compatibility - skills without these fields should work unchanged.

## Files to Modify

- `src/omniforge/skills/models.py` - Add new fields to SkillMetadata
- `src/omniforge/skills/parser.py` - Update parser for new metadata fields

## Implementation Requirements

### New SkillMetadata Fields

```python
class SkillMetadata(BaseModel):
    # Existing fields remain unchanged...

    # NEW: Autonomous execution fields
    execution_mode: str = Field(
        default="autonomous",
        description="Execution mode: 'autonomous' or 'simple'",
    )
    max_iterations: Optional[int] = Field(
        None,
        alias="max-iterations",
        ge=1,
        le=100,
        description="Max ReAct iterations (default: 15)",
    )
    max_retries_per_tool: Optional[int] = Field(
        None,
        alias="max-retries-per-tool",
        ge=0,
        le=10,
        description="Max retries per tool (default: 3)",
    )
    timeout_per_iteration: Optional[str] = Field(
        None,
        alias="timeout-per-iteration",
        description="Timeout per iteration (e.g., '30s')",
    )
    early_termination: Optional[bool] = Field(
        None,
        alias="early-termination",
        description="Allow early termination on confidence",
    )
```

### SKILL.md Example

```yaml
---
name: data-processor
description: Process data files autonomously
execution-mode: autonomous
max-iterations: 20
max-retries-per-tool: 5
timeout-per-iteration: 30s
early-termination: true
allowed-tools:
  - read
  - write
  - Bash(python:*)
---
```

### Backward Compatibility

- Skills without new fields default to autonomous mode
- Skills with `execution-mode: simple` use legacy executor
- All existing skills must continue to work unchanged

## Acceptance Criteria

- [ ] New fields added to SkillMetadata with proper validation
- [ ] Alias names support kebab-case (max-iterations) in YAML
- [ ] Defaults applied when fields not specified
- [ ] Validation errors for out-of-range values
- [ ] Existing skill tests still pass
- [ ] Parser correctly handles new fields
- [ ] Unit tests for all new fields

## Testing

```python
def test_skill_metadata_defaults():
    """New skills default to autonomous mode."""
    metadata = SkillMetadata(name="test", description="Test")
    assert metadata.execution_mode == "autonomous"
    assert metadata.max_iterations is None  # Use config default

def test_skill_metadata_custom_values():
    """Custom values are parsed correctly."""
    metadata = SkillMetadata(
        name="test",
        description="Test",
        max_iterations=20,
        execution_mode="autonomous",
    )
    assert metadata.max_iterations == 20

def test_skill_metadata_validation():
    """Invalid values raise validation errors."""
    with pytest.raises(ValidationError):
        SkillMetadata(
            name="test",
            description="Test",
            max_iterations=200,  # Exceeds 100 limit
        )

def test_existing_skill_backward_compatible(existing_skill_fixture):
    """Existing skills without new fields work unchanged."""
    skill = load_skill("existing-skill")
    assert skill.metadata.execution_mode == "autonomous"
```

## Technical Notes

- Use Pydantic `Field` with `alias` for kebab-case support
- Validation bounds: max_iterations 1-100, max_retries 0-10
- Timeout parsing: accept strings like "30s", "1m", "500ms"
- Test with existing skills in `src/omniforge/skills/` directory
