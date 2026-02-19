# TASK-203: Public Skill Library Storage and Discovery

**Phase**: 2 (Multi-Skill)
**Estimated Effort**: 12 hours
**Dependencies**: TASK-102 (SKILL.md Generator)
**Priority**: P1

## Objective

Create the public skill library that allows users to discover and reuse community-contributed skills during agent creation. This includes storage, search, and skill metadata management.

## Requirements

- Create `public_skills` database table per technical plan schema
- Create `PublicSkill` model with content, author, tags, usage stats
- Implement `PublicSkillRepository` with search and discovery methods
- Create skill discovery service for conversation-based recommendations
- Implement skill usage tracking (increment usage_count on use)
- Add skill rating/feedback collection (optional for MVP)
- Support tagging and categorization for browsing

## Implementation Notes

- Reference technical plan Section 6.2 for public_skills schema
- Full-text search on name, description, tags for discovery
- Skills stored as SKILL.md content in database TEXT field
- `source: public` in SkillReference indicates public library skill
- Order by usage_count DESC for popularity-based discovery

## Acceptance Criteria

- [ ] `public_skills` table created with all required fields
- [ ] `PublicSkillRepository.search()` finds skills by keyword
- [ ] `PublicSkillRepository.get_by_integration()` filters by integration
- [ ] Usage count increments when skill is added to an agent
- [ ] Skill discovery returns top 5 matching public skills
- [ ] Conversation integration suggests public skills during creation
- [ ] Tags and categories enable browsing the library
- [ ] Unit tests cover search and discovery logic

## Files to Create/Modify

- `src/omniforge/builder/models/public_skill.py` - PublicSkill model
- `src/omniforge/builder/repository.py` - Add PublicSkillRepository
- `src/omniforge/builder/discovery/__init__.py` - Discovery package
- `src/omniforge/builder/discovery/service.py` - SkillDiscoveryService
- `src/omniforge/api/routes/skills.py` - Public skill API endpoints
- `tests/builder/test_public_skill_repository.py` - Repository tests
- `tests/builder/discovery/test_service.py` - Discovery service tests
