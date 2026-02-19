# TASK-003: Create ContextLoader for progressive context loading

**Priority:** P0 (Must Have)
**Estimated Effort:** Small (<1 day)
**Dependencies:** None

---

## Description

Create `ContextLoader` class to parse SKILL.md for supporting file references and manage on-demand loading. Extracts references like "See reference.md for details (1,200 lines)" and builds a list of available files for the system prompt.

This enables progressive context loading - only SKILL.md content is loaded initially, supporting files are loaded on-demand via the `read` tool during execution.

## Files to Create

- `src/omniforge/skills/context_loader.py` - ContextLoader implementation

## Implementation Requirements

### FileReference dataclass
- `filename: str` - Name of the file (e.g., "reference.md")
- `path: Path` - Absolute path to the file
- `description: str` - Description extracted from SKILL.md
- `estimated_lines: Optional[int]` - Line count if mentioned
- `loaded: bool = False` - Whether file has been loaded

### LoadedContext dataclass
- `skill_content: str` - SKILL.md content
- `available_files: dict[str, FileReference]` - Map of filename -> reference
- `skill_dir: Path` - Absolute path to skill directory
- `line_count: int` - Number of lines in SKILL.md

### ContextLoader class

**File Reference Patterns to Recognize:**
1. `See reference.md for API documentation (1,200 lines)`
2. `- reference.md: Description`
3. `**reference.md**: Description (300 lines)`
4. `Read examples.md for usage patterns`
5. `Check templates/report.md`

**Methods:**
- `load_initial_context()` -> LoadedContext
- `mark_file_loaded(filename)` - Track loaded files
- `get_loaded_files()` -> set[str]
- `build_available_files_prompt(context)` -> str - Format for system prompt

## Acceptance Criteria

- [ ] Extracts file references from multiple patterns
- [ ] Validates referenced files exist in skill directory
- [ ] Parses line count hints (e.g., "1,200 lines")
- [ ] Generates formatted prompt section for available files
- [ ] Tracks which files have been loaded
- [ ] Handles nested paths (e.g., "templates/report.md")
- [ ] Unit tests achieve 95% coverage

## Testing

```python
def test_extract_file_references():
    content = """
    See reference.md for API documentation (1,200 lines)
    - examples.md: Usage patterns
    """
    loader = ContextLoader(mock_skill)
    refs = loader._extract_file_references(content)

    assert "reference.md" in refs
    assert "examples.md" in refs
    assert refs["reference.md"].estimated_lines == 1200

def test_build_available_files_prompt():
    context = LoadedContext(...)
    prompt = loader.build_available_files_prompt(context)

    assert "AVAILABLE SUPPORTING FILES" in prompt
    assert "reference.md" in prompt

def test_validate_files_exist(tmp_path):
    # Create skill with reference to non-existent file
    # Verify it's excluded from available_files
```

## Technical Notes

- Use regex patterns for flexible matching:
  ```python
  # Pattern 1: "See reference.md for details (1,200 lines)"
  r"(?:see|read|check|refer to)\s+[`'\"]?([a-zA-Z0-9_\-/]+\.(?:md|txt|json|yaml))[`'\"]?"
  ```
- Only include files that actually exist in skill directory
- Support common extensions: .md, .txt, .json, .yaml
- Line count parsing: handle commas in numbers (1,200 -> 1200)
