# TASK-004: Skill Loader with Caching and Priority Resolution

**Phase**: 2 - Loading & Caching
**Complexity**: Medium
**Dependencies**: TASK-001, TASK-002, TASK-003
**Estimated Time**: 45-60 minutes

## Objective

Implement the SkillLoader for indexing, caching, and loading skills with priority resolution.

## What to Build

### Create `src/omniforge/skills/loader.py`

Implement `SkillLoader` class:

1. **__init__(config, cache_ttl_seconds=300)**
   - Initialize with StorageConfig
   - Create SkillStorageManager and SkillParser instances
   - Initialize thread-safe data structures (RLock)

2. **build_index(force=False) -> int**
   - Scan all storage layers via storage manager
   - Parse metadata only (Stage 1) for each skill
   - Handle name conflicts via priority resolution:
     - Compare effective priority = (layer_priority * 1000) + explicit_priority
     - Higher wins
   - Skip individual parse errors (log but don't fail)
   - Return count of indexed skills
   - Cache index with 60s rebuild cooldown

3. **list_skills() -> list[SkillIndexEntry]**
   - Return sorted list of all indexed skills

4. **get_skill_metadata(name) -> SkillIndexEntry**
   - Return index entry by name
   - Raise SkillNotFoundError if not found

5. **load_skill(name) -> Skill**
   - Full skill loading (Stage 2)
   - Check skill cache first (TTL-based)
   - Parse full skill if not cached
   - Pass storage_layer explicitly to parser

6. **has_skill(name) -> bool**
   - Check if skill exists in index

7. **invalidate_cache(name=None)**
   - Clear specific skill or entire cache

8. **_get_effective_priority(entry) -> int**
   - Calculate combined layer + explicit priority

## Key Requirements

- Thread-safe with threading.RLock for concurrent access
- Cache TTL configurable (default 5 minutes)
- Index rebuild cooldown of 60 seconds
- Performance target: < 100ms for indexing 1000 skills
- Pass storage_layer explicitly (no path heuristics)

## Acceptance Criteria

- [ ] Index builds correctly from multiple storage layers
- [ ] Priority resolution: Enterprise > Personal > Project > Plugin
- [ ] Cache works correctly with TTL expiration
- [ ] Thread-safe operations verified
- [ ] SkillNotFoundError raised for missing skills
- [ ] Unit tests in `tests/skills/test_loader.py` with >80% coverage
- [ ] Performance benchmark test for 1000 skills < 100ms
