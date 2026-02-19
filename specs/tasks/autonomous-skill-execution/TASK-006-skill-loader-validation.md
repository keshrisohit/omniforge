# TASK-006: Update SkillLoader with 500-line limit validation

**Priority:** P0 (Must Have)
**Estimated Effort:** Small (<1 day)
**Dependencies:** TASK-004

---

## Description

Update `SkillLoader` to enforce the 500-line limit for SKILL.md files. This limit is critical for progressive context loading to be effective - keeping SKILL.md concise ensures token savings and encourages moving detailed content to supporting files.

New skills exceeding 500 lines should raise a validation error. Existing skills can be given a grace period with warnings.

## Files to Modify

- `src/omniforge/skills/loader.py` - Add line count validation

## Implementation Requirements

### Validation Logic

```python
MAX_SKILL_MD_LINES = 500

def _validate_skill_content(self, skill: Skill) -> None:
    """Validate skill content meets requirements."""
    line_count = skill.content.count('\n') + 1

    if line_count > MAX_SKILL_MD_LINES:
        # Check for legacy override flag
        if skill.metadata.get("legacy_large_file"):
            logger.warning(
                f"SKILL.md exceeds {MAX_SKILL_MD_LINES} lines "
                f"({line_count} lines). Legacy mode enabled - "
                f"consider migrating to progressive loading."
            )
        else:
            raise SkillValidationError(
                f"SKILL.md must be under {MAX_SKILL_MD_LINES} lines "
                f"(found {line_count} lines). "
                f"Move detailed content to supporting files "
                f"(reference.md, examples.md). "
                f"See migration guide for details."
            )
```

### Error Message

Provide helpful error message with:
1. Current line count
2. Maximum allowed lines
3. Suggestion to use supporting files
4. Reference to migration guide

### Grace Period for Existing Skills

Add metadata field `legacy_large_file: true` to allow existing large skills to continue working with a deprecation warning.

```yaml
---
name: legacy-skill
legacy-large-file: true  # Bypass 500-line limit with warning
---
```

## Acceptance Criteria

- [ ] Skills with >500 lines in SKILL.md raise SkillValidationError
- [ ] Error message is clear and actionable
- [ ] `legacy_large_file` flag bypasses with warning
- [ ] Line count is calculated correctly
- [ ] Validation runs during skill loading
- [ ] Existing valid skills continue to work
- [ ] Unit tests for validation logic

## Testing

```python
def test_skill_loader_rejects_large_skill(tmp_path):
    """Skills exceeding 500 lines should be rejected."""
    skill_dir = tmp_path / "large-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: large-skill\ndescription: Test\n---\n"
        + "\n".join(["Line " + str(i) for i in range(600)])
    )

    loader = SkillLoader(StorageConfig(project_path=str(tmp_path)))
    with pytest.raises(SkillValidationError) as exc_info:
        loader.load_skill("large-skill")

    assert "500 lines" in str(exc_info.value)

def test_skill_loader_allows_legacy_large_skill(tmp_path):
    """Legacy flag allows large skills with warning."""
    skill_dir = tmp_path / "legacy-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: legacy-skill\ndescription: Test\n"
        "legacy-large-file: true\n---\n"
        + "\n".join(["Line " + str(i) for i in range(600)])
    )

    loader = SkillLoader(StorageConfig(project_path=str(tmp_path)))
    skill = loader.load_skill("legacy-skill")  # Should succeed
    assert skill is not None

def test_skill_loader_accepts_normal_skill(tmp_path):
    """Skills under 500 lines work normally."""
    # Create skill with 100 lines
    # Verify it loads without error
```

## Technical Notes

- Line count: `content.count('\n') + 1` handles edge cases
- Add `legacy_large_file` to SkillMetadata model
- Log warning at WARNING level for legacy mode
- Consider adding line count to skill metrics/telemetry
- Update documentation with 500-line best practice
