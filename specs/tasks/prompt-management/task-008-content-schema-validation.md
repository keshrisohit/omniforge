# TASK-008: Implement Content and Schema Validation

## Objective

Create validators for prompt content rules and variable schema validation.

## Requirements

### Content Validator (`src/omniforge/prompts/validation/content.py`)

**ContentValidator class**:

`validate(content: str, rules: Optional[ContentRules] = None) -> list[ValidationResult]`:
- Check content length against limits
- Detect prohibited content patterns (configurable blocklist)
- Verify required sections are present (for compliance)
- Check for injection vulnerabilities

**ContentRules dataclass**:
```python
@dataclass
class ContentRules:
    max_length: int = 100000
    min_length: int = 1
    prohibited_patterns: list[str] = field(default_factory=list)
    required_patterns: list[str] = field(default_factory=list)
```

**ValidationResult dataclass**:
```python
@dataclass
class ValidationResult:
    is_valid: bool
    severity: ValidationSeverity
    message: str
    location: Optional[str] = None
```

### Schema Validator (`src/omniforge/prompts/validation/schema.py`)

**SchemaValidator class**:

`validate_schema(schema: VariableSchema) -> list[str]`:
- Validate that schema is well-formed JSON Schema
- Check property definitions have valid types
- Return list of schema errors

`validate_variables(variables: dict[str, Any], schema: VariableSchema) -> list[str]`:
- Validate variables against schema
- Check required variables are present
- Validate types match schema definitions
- Use jsonschema library for validation

### Comprehensive Validator (`src/omniforge/prompts/validation/validator.py`)

**PromptValidator class** (facade for all validators):
- `syntax_validator: SyntaxValidator`
- `content_validator: ContentValidator`
- `schema_validator: SchemaValidator`

`validate_prompt(prompt: Prompt) -> list[ValidationResult]`:
- Run syntax validation
- Run content validation
- Run schema validation
- Aggregate and return all results

## Acceptance Criteria
- [ ] Content length limits are enforced
- [ ] Prohibited patterns are detected
- [ ] Required patterns check works
- [ ] Variable schema validation uses JSON Schema
- [ ] Required variables are checked
- [ ] Type mismatches are reported
- [ ] PromptValidator aggregates all validation results
- [ ] Unit tests cover all validation rules
- [ ] Tests for edge cases (empty, max length, unicode)

## Dependencies
- TASK-001 (models, enums)
- TASK-003 (SyntaxValidator)

## Estimated Complexity
Medium
