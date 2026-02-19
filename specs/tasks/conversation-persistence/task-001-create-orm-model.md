# TASK-001: Create ORM Model for Skill Creation Sessions

## Description

Create the SQLAlchemy ORM model for persisting skill creation session data. This model stores the full `ConversationContext` as a JSON blob with denormalized fields for efficient querying.

## Dependencies

None - This is the foundation task.

## Files to Create/Modify

- **Create**: `src/omniforge/skills/creation/orm.py`

## Key Requirements

- Define `SkillCreationSessionModel` class extending `Base` from `omniforge.storage.database`
- Include all fields: `id` (UUID), `session_id`, `tenant_id`, `context_json` (TEXT), `state`, `skill_name`, `created_at`, `updated_at`, `status`
- Add `UniqueConstraint` on (`session_id`, `tenant_id`)
- Create indexes: `idx_tenant_session`, `idx_tenant_state`, `idx_tenant_updated`, `idx_status_updated`
- Use `mapped_column` with proper type annotations (SQLAlchemy 2.0 style)

## Acceptance Criteria

- [ ] ORM model imports successfully without errors
- [ ] All fields have proper type annotations
- [ ] Unique constraint and indexes are defined in `__table_args__`
- [ ] Model can be imported alongside existing models
- [ ] Unit test verifies model can be instantiated with valid data

## Testing

Create `tests/skills/creation/test_orm.py`:
- Test model instantiation with valid data
- Test default values (`status="active"`, auto-generated `id`)
- Test `updated_at` defaults to current time

## Estimated Complexity

Simple (1-2 hours)

## Technical Notes

Follow the pattern from existing ORM models in the codebase. Use `datetime.utcnow` for timestamps (not timezone-aware for SQLite compatibility).
