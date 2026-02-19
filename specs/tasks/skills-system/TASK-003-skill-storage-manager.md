# TASK-003: Skill Storage Manager

**Phase**: 1 - Foundation
**Complexity**: Simple
**Dependencies**: TASK-001
**Estimated Time**: 20-30 minutes

## Objective

Implement the storage layer management for the 4-layer skill hierarchy.

## What to Build

### Create `src/omniforge/skills/storage.py`

1. **StorageConfig** Pydantic model:
   - enterprise_path: Optional[Path]
   - personal_path: Optional[Path]
   - project_path: Optional[Path]
   - plugin_paths: list[Path]
   - `from_environment(project_root)` class method for defaults:
     - Enterprise: `~/.omniforge/enterprise/skills/`
     - Personal: `~/.omniforge/skills/`
     - Project: `{project_root}/.omniforge/skills/`

2. **SkillStorageManager** class:
   - LAYER_ORDER class constant: ["enterprise", "personal", "project", "plugin"]
   - `__init__(config: StorageConfig)`
   - `get_all_skill_paths() -> Iterator[tuple[str, Path]]`
     - Iterate all SKILL.md files in priority order
     - Yield (storage_layer, skill_path) tuples
   - `_scan_directory(layer, base_path) -> Iterator[tuple[str, Path]]`
     - Find SKILL.md in immediate subdirectories
   - `get_layer_priority(layer: str) -> int`
     - Return priority value (enterprise=4, personal=3, project=2, plugin=1)

## Key Requirements

- Handle missing directories gracefully (skip if not exists)
- Scan only immediate subdirectories (not recursive)
- Each skill directory must contain SKILL.md
- Priority: Enterprise > Personal > Project > Plugin

## Acceptance Criteria

- [ ] StorageConfig.from_environment() creates valid defaults
- [ ] get_all_skill_paths() yields in correct priority order
- [ ] Missing directories silently skipped (no errors)
- [ ] get_layer_priority() returns correct values
- [ ] Unit tests in `tests/skills/test_storage.py` with >80% coverage
- [ ] Tests use tmp_path fixture for isolation
