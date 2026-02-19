# TASK-005: Skill Hot Reload Support (Optional)

**Phase**: 2 - Loading & Caching
**Complexity**: Simple
**Dependencies**: TASK-004
**Estimated Time**: 20-30 minutes

## Objective

Add optional file watching for hot reload of skills during development.

## What to Build

### Extend `src/omniforge/skills/loader.py`

Add hot reload capabilities to SkillLoader:

1. **start_watching()**
   - Start file watcher using watchdog library (optional dependency)
   - Watch all configured storage directories
   - On SKILL.md changes: invalidate cache and rebuild index

2. **stop_watching()**
   - Stop file watcher gracefully

3. **_on_file_changed(event)**
   - Handler for file system events
   - Filter for SKILL.md files only
   - Debounce rapid changes (100ms)

4. **is_watching property**
   - Return True if file watcher is active

### Update `src/omniforge/skills/__init__.py`
- Export hot reload methods

## Key Requirements

- watchdog is optional dependency (graceful fallback if not installed)
- Only watch existing directories
- Debounce rapid file changes
- Thread-safe interaction with index

## Acceptance Criteria

- [ ] Hot reload works when watchdog is installed
- [ ] Graceful degradation without watchdog
- [ ] File changes trigger index rebuild
- [ ] No memory leaks from watcher threads
- [ ] Unit tests mock file system events

## Notes

This task is marked as optional/nice-to-have. Can be deferred if timeline is tight.
