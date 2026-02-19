# TASK-006: Skill Writer

**Phase**: 1 (MVP)
**Complexity**: Low-Medium
**Estimated Effort**: 2-3 hours
**Dependencies**: TASK-001

## Description

Implement the SkillWriter class that writes skill files to the appropriate storage layer in the filesystem. For MVP, this focuses on the Project storage layer with support for creating the skill directory structure and writing SKILL.md files.

## Requirements

### Location
- Create `src/omniforge/skills/creation/writer.py`

### SkillWriter Class

```python
class SkillWriter:
    """Write skills to filesystem following official structure."""

    def __init__(self, storage_manager: SkillStorageManager) -> None: ...

    async def write_skill(
        self,
        skill_name: str,
        content: str,
        storage_layer: str,
        resources: Optional[dict[str, str]] = None,
    ) -> Path:
        """Write skill to storage layer, return path.

        Creates official directory structure:
        skill-name/
        |-- SKILL.md (required)
        |-- scripts/     (optional)
        |-- references/  (optional)
        +-- assets/      (optional)
        """

    def get_skill_directory(
        self, skill_name: str, storage_layer: str
    ) -> Path:
        """Get target directory for skill."""

    def skill_exists(
        self, skill_name: str, storage_layer: str
    ) -> bool:
        """Check if skill already exists."""

    async def write_bundled_resource(
        self,
        skill_dir: Path,
        resource_path: str,  # e.g., "scripts/process.py"
        content: str,
    ) -> Path:
        """Write bundled resource file."""
```

### Directory Structure

```
.omniforge/skills/          # Project layer base
|-- skill-name/
|   |-- SKILL.md            # Main skill file
|   |-- scripts/            # Optional executable scripts
|   |-- references/         # Optional reference docs
|   +-- assets/             # Optional assets
```

### Storage Layer Paths (MVP)

For MVP, focus on Project layer:
- **Project**: `{project_root}/.omniforge/skills/{skill_name}/`

Phase 3 will add:
- **Personal**: `~/.omniforge/skills/{skill_name}/`
- **Enterprise**: `~/.omniforge/enterprise/skills/{skill_name}/`

### Key Behaviors

1. **Directory Creation**: Create skill directory if it doesn't exist
2. **Parent Directory Creation**: Create `.omniforge/skills/` if needed
3. **Overwrite Protection**: Check skill_exists() before writing
4. **Atomic Write**: Write to temp file, then rename (optional for MVP)
5. **Resource Subdirectories**: Create scripts/, references/, assets/ as needed

## Acceptance Criteria

- [ ] write_skill() creates directory structure and writes SKILL.md
- [ ] get_skill_directory() returns correct path for storage layer
- [ ] skill_exists() accurately detects existing skills
- [ ] write_bundled_resource() creates subdirectories as needed
- [ ] Handles path with spaces correctly
- [ ] Returns absolute Path to written skill
- [ ] Unit tests with temporary directories
- [ ] Test coverage > 85%

## Technical Notes

- Use pathlib.Path for all path operations
- Use existing StorageConfig for layer paths
- Ensure UTF-8 encoding for all file writes
- Forward slashes for resource paths per official spec

## Test Cases

```python
async def test_write_skill_creates_directory(tmp_path):
    config = StorageConfig(project_path=tmp_path / ".omniforge/skills")
    storage_manager = SkillStorageManager(config)
    writer = SkillWriter(storage_manager)

    content = "---\nname: test-skill\ndescription: Test\n---\n# Test"
    path = await writer.write_skill("test-skill", content, "project")

    assert path.exists()
    assert (path.parent / "SKILL.md").exists()
    assert (path.parent / "SKILL.md").read_text() == content

def test_skill_exists_returns_true(tmp_path):
    # Create skill directory with SKILL.md
    skill_dir = tmp_path / ".omniforge/skills/existing-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("content")

    config = StorageConfig(project_path=tmp_path / ".omniforge/skills")
    writer = SkillWriter(SkillStorageManager(config))

    assert writer.skill_exists("existing-skill", "project") is True

async def test_write_bundled_resource(tmp_path):
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()

    writer = SkillWriter(...)
    path = await writer.write_bundled_resource(
        skill_dir, "scripts/helper.py", "print('hello')"
    )

    assert path.exists()
    assert path.parent.name == "scripts"
```
