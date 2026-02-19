# TASK-001: Skill Data Models and Error Hierarchy

**Phase**: 1 - Foundation
**Complexity**: Medium
**Dependencies**: None
**Estimated Time**: 30-45 minutes

## Objective

Create the core data models and exception hierarchy for the Skills System.

## What to Build

### 1. Create `src/omniforge/skills/__init__.py`
- Export public API classes

### 2. Create `src/omniforge/skills/models.py`
Implement Pydantic models:
- `ContextMode` enum (INHERIT, FORK)
- `SkillHooks` model (pre, post script paths)
- `SkillScope` model (agents, tenants, environments)
- `SkillMetadata` model with all YAML frontmatter fields:
  - name (kebab-case validated)
  - description
  - allowed_tools (alias: allowed-tools)
  - model, context, agent, hooks, priority, tags, scope
- `Skill` model (full skill with metadata, content, path, base_path, storage_layer, script_paths)
- `SkillIndexEntry` model (lightweight for discovery)

### 3. Create `src/omniforge/skills/errors.py`
Implement exception hierarchy:
- `SkillError` base class with error_code and context
- `SkillNotFoundError`
- `SkillParseError`
- `SkillToolNotAllowedError`
- `SkillActivationError`
- `SkillScriptReadError`

## Key Requirements

- Use Pydantic v2 patterns (field_validator, model_validate)
- Validate skill names follow kebab-case: `^[a-z][a-z0-9-]*$`
- Support both `allowed_tools` and `allowed-tools` via alias
- All models must pass mypy strict type checking
- Line length: 100 characters (Black/Ruff)

## Acceptance Criteria

- [ ] All models instantiate correctly with valid data
- [ ] Validation errors raise with descriptive messages
- [ ] Skill.is_script_file() method works for path checking
- [ ] Unit tests in `tests/skills/test_models.py` with >80% coverage
- [ ] Unit tests in `tests/skills/test_errors.py` for all exceptions
- [ ] `mypy src/omniforge/skills/` passes with no errors
