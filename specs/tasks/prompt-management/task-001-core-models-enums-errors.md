# TASK-001: Create Core Models, Enums, and Error Classes

## Objective

Implement the foundational data models, enumerations, and exception hierarchy for the Prompt Management Module.

## Requirements

### Enums (`src/omniforge/prompts/enums.py`)
- `PromptLayer`: SYSTEM, TENANT, FEATURE, AGENT, USER
- `MergeBehavior`: APPEND, PREPEND, REPLACE, INJECT
- `ExperimentStatus`: DRAFT, RUNNING, PAUSED, COMPLETED, CANCELLED
- `ValidationSeverity`: ERROR, WARNING, INFO

### Models (`src/omniforge/prompts/models.py`)
- `MergePointDefinition`: name, behavior, required, locked, description
- `VariableSchema`: properties dict, required list
- `Prompt`: Full model with layer, scope_id, content, merge_points, variables_schema, tenant isolation
- `PromptVersion`: Immutable version with version_number, content, change_message
- `ExperimentVariant`: id, name, prompt_version_id, traffic_percentage, metrics
- `PromptExperiment`: Full experiment model with status, variants, success_metric
- `ComposedPrompt`: Result model with content, layer_versions, cache_key, composition_time_ms

### Errors (`src/omniforge/prompts/errors.py`)
- `PromptError`: Base exception with message, code, status_code
- `PromptNotFoundError`, `PromptVersionNotFoundError`
- `PromptValidationError`, `PromptCompositionError`, `PromptRenderError`
- `ExperimentNotFoundError`, `ExperimentStateError`
- `MergePointConflictError`, `PromptLockViolationError`, `PromptConcurrencyError`

### Technical Notes
- Use Pydantic BaseModel for all models
- Add field validators for content validation (non-empty, non-whitespace)
- Add validator for experiment traffic allocation (must sum to 100%)
- Follow existing codebase patterns from `agents/errors.py`
- All models must have complete type annotations

## Acceptance Criteria
- [ ] All enums define correct values as string Enums
- [ ] All Pydantic models validate correctly with proper field constraints
- [ ] Prompt content validator rejects empty/whitespace-only content
- [ ] Experiment validator ensures traffic percentages sum to 100%
- [ ] Error classes include appropriate HTTP status codes
- [ ] Unit tests cover all model validations
- [ ] 100% type annotation coverage (mypy passes)
- [ ] Code formatted with black, passes ruff checks

## Dependencies
None - this is the first task

## Estimated Complexity
Medium
