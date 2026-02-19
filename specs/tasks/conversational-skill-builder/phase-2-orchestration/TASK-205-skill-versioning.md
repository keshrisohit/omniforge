# TASK-205: Skill Version Management

**Phase**: 2 (Multi-Skill)
**Estimated Effort**: 8 hours
**Dependencies**: TASK-203 (Public Skill Library)
**Priority**: P1

## Objective

Add version management to public skills so agents can pin to specific versions. This prevents breaking changes when public skills are updated.

## Requirements

- Add `version` column to `public_skills` table (semantic versioning)
- Update `SkillReference` to include optional `version` field
- Implement "latest" version resolution (default if version not specified)
- Create version comparison and compatibility checking
- Add version selection during agent creation conversation
- Notify users when newer versions of pinned skills are available

## Implementation Notes

- Per review finding: version management prevents breaking changes
- Semantic versioning (1.0.0, 1.1.0, 2.0.0)
- UNIQUE constraint on (name, version) allows multiple versions
- When version=None, resolve to latest version at execution time
- Major version changes may indicate breaking changes

## Acceptance Criteria

- [ ] Public skills can have multiple versions stored
- [ ] SkillReference.version pins to specific version
- [ ] Version=None resolves to latest at execution time
- [ ] Agent creation offers version selection for public skills
- [ ] Version compatibility warnings for major version differences
- [ ] Notification when newer version available for pinned skill
- [ ] Migration script adds version column to existing public_skills
- [ ] Unit tests cover version resolution logic

## Files to Create/Modify

- `src/omniforge/builder/models/public_skill.py` - Add version field
- `src/omniforge/builder/models/agent_config.py` - Add version to SkillReference
- `src/omniforge/builder/repository.py` - Version-aware skill queries
- `src/omniforge/builder/versioning/__init__.py` - Versioning package
- `src/omniforge/builder/versioning/resolver.py` - Version resolution logic
- `alembic/versions/xxx_add_skill_version.py` - Migration script
- `tests/builder/versioning/test_resolver.py` - Version resolution tests
