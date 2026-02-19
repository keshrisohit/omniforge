# TASK-002: Skill Parser for YAML Frontmatter

**Phase**: 1 - Foundation
**Complexity**: Medium
**Dependencies**: TASK-001
**Estimated Time**: 30-45 minutes

## Objective

Implement the SkillParser for extracting YAML frontmatter from SKILL.md files.

## What to Build

### Create `src/omniforge/skills/parser.py`

Implement `SkillParser` class with:

1. **FRONTMATTER_PATTERN** regex for `---\n...\n---` extraction
2. **SCRIPT_EXTENSIONS** set (.sh, .py, .rb, .js, .ts, .pl)
3. **SCRIPT_DIRS** set (scripts, bin, tools)

4. **parse_metadata(path, storage_layer) -> SkillIndexEntry**
   - Parse only frontmatter for index building (Stage 1)
   - Accept storage_layer as explicit parameter (no path heuristics)
   - Handle YAML errors gracefully with SkillParseError

5. **parse_full(path, storage_layer) -> Skill**
   - Parse complete SKILL.md (Stage 2)
   - Extract frontmatter and body content
   - Auto-detect script files in skill directory
   - Return complete Skill model

6. **_read_file(path) -> str**
   - UTF-8 file reading with error handling

7. **_extract_frontmatter(content, path) -> tuple[str, str]**
   - Split frontmatter YAML from body markdown

8. **_detect_script_files(base_path) -> list[Path]**
   - Scan SCRIPT_DIRS for files with SCRIPT_EXTENSIONS

## Key Requirements

- Use PyYAML safe_load for YAML parsing
- Storage layer passed explicitly (addresses HIGH-1 from review)
- Script detection supports nested directories (rglob)
- All errors wrapped in SkillParseError with path context

## Acceptance Criteria

- [ ] Valid SKILL.md files parse correctly
- [ ] Invalid YAML raises SkillParseError with clear message
- [ ] Missing frontmatter raises SkillParseError
- [ ] Script files auto-detected in scripts/, bin/, tools/
- [ ] Unit tests in `tests/skills/test_parser.py` with >80% coverage
- [ ] Tests cover edge cases: empty files, no frontmatter, invalid YAML
