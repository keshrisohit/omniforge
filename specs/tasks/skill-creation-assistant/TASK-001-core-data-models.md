# TASK-001: Core Data Models and Enums

**Phase**: 1 (MVP)
**Complexity**: Medium
**Estimated Effort**: 2-3 hours
**Dependencies**: None

## Description

Create the foundational Pydantic data models and enums for the skill creation conversation flow. These models define conversation state, context accumulation, skill patterns, and validation results following official Anthropic Agent Skills guidelines.

## Requirements

### Location
- Create `src/omniforge/skills/creation/__init__.py`
- Create `src/omniforge/skills/creation/models.py`

### Models to Implement

1. **ConversationState** (Enum)
   - IDLE, INTENT_DETECTION, GATHERING_PURPOSE, GATHERING_DETAILS
   - CONFIRMING_SPEC, GENERATING, VALIDATING, FIXING_ERRORS
   - SELECTING_STORAGE, SAVING, COMPLETED, ERROR

2. **SkillPattern** (Enum)
   - SIMPLE, WORKFLOW, REFERENCE_HEAVY, SCRIPT_BASED

3. **OfficialSkillSpec** (BaseModel)
   - name: str (max 64 chars, kebab-case validation)
   - description: str (max 1024 chars)
   - Pydantic validators for official format compliance

4. **ConversationContext** (BaseModel)
   - session_id, state, skill_name, skill_description, skill_purpose
   - skill_pattern, examples, workflow_steps, triggers
   - references_topics, scripts_needed
   - storage_layer, generated_content, generated_resources
   - validation_attempts, validation_errors, max_validation_retries
   - message_history
   - Method: `to_official_spec()` -> Optional[OfficialSkillSpec]

5. **ValidationResult** (BaseModel)
   - is_valid: bool
   - errors: list[str]
   - warnings: list[str]
   - skill_path: Optional[str]

### Validation Rules (per Official Anthropic Spec)
- Name: max 64 chars, lowercase letters/numbers/hyphens, must start with letter
- Description: max 1024 chars, non-empty

## Acceptance Criteria

- [ ] All models pass mypy type checking
- [ ] Pydantic validators enforce official name format (kebab-case)
- [ ] ConversationState enum has all 12 states
- [ ] SkillPattern enum has all 4 patterns
- [ ] Unit tests for model validation (valid/invalid cases)
- [ ] Test coverage > 90% for models.py

## Technical Notes

- Follow existing patterns from `src/omniforge/skills/models.py`
- Use `Field` for validation constraints and aliases
- Use `field_validator` for custom validation logic
- Import path: `from omniforge.skills.creation.models import ...`

## Test Cases

```python
def test_official_skill_spec_valid_name():
    spec = OfficialSkillSpec(name="format-products", description="Formats...")
    assert spec.name == "format-products"

def test_official_skill_spec_invalid_name_uppercase():
    with pytest.raises(ValidationError):
        OfficialSkillSpec(name="Format-Products", description="...")

def test_conversation_context_to_official_spec():
    ctx = ConversationContext(
        skill_name="test-skill",
        skill_description="Test desc..."
    )
    spec = ctx.to_official_spec()
    assert spec.name == "test-skill"
```
