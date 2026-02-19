# TASK-101: Database Models and Repository Layer

**Phase**: 1 (MVP)
**Estimated Effort**: 8 hours
**Dependencies**: None
**Priority**: P0

## Objective

Create the core database models (AgentConfig, Credentials, ExecutionLog) and repository layer for the Conversational Skill Builder. This task establishes the data foundation that all other components depend on.

## Requirements

- Create `AgentConfig` Pydantic model with all fields from technical plan (Section 6.1)
- Add Pydantic validators for cron expressions, skill order uniqueness, and integration IDs (per review findings)
- Create `SkillReference`, `TriggerType`, `AgentStatus`, `SharingLevel` models
- Create SQLAlchemy ORM models for `agent_configs`, `credentials`, `agent_executions` tables
- Implement repository classes with CRUD operations (async SQLAlchemy 2.0)
- Support both SQLite (dev) and PostgreSQL (prod) via SQLAlchemy

## Implementation Notes

- Follow existing patterns in `src/omniforge/storage/models.py` and `src/omniforge/storage/database.py`
- Use Fernet encryption for credential storage (cryptography library)
- All models must have type annotations and docstrings per coding guidelines
- Place new models in `src/omniforge/builder/models/`
- Place repository in `src/omniforge/builder/repository.py`

## Acceptance Criteria

- [ ] `AgentConfig` model validates cron expressions using `croniter`
- [ ] `AgentConfig` model validates skill order uniqueness
- [ ] `AgentConfig` model validates integration IDs against known list
- [ ] SQLAlchemy models match schema from technical plan (Section 6.2)
- [ ] Repository provides async CRUD operations for AgentConfig
- [ ] Credential encryption/decryption works correctly
- [ ] Unit tests achieve 80%+ coverage
- [ ] All tests pass with `pytest tests/builder/test_models.py`

## Files to Create/Modify

- `src/omniforge/builder/__init__.py` - New package init
- `src/omniforge/builder/models/__init__.py` - Models package init
- `src/omniforge/builder/models/agent_config.py` - AgentConfig, SkillReference, enums
- `src/omniforge/builder/models/credentials.py` - Credential model with encryption
- `src/omniforge/builder/models/execution.py` - ExecutionLog model
- `src/omniforge/builder/models/errors.py` - Builder-specific exceptions
- `src/omniforge/builder/repository.py` - AgentConfigRepository class
- `tests/builder/__init__.py` - Test package
- `tests/builder/test_models.py` - Model unit tests
- `tests/builder/test_repository.py` - Repository unit tests
