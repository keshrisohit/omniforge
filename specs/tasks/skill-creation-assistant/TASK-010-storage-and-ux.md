# TASK-010: Storage Layer Selection and Advanced UX

**Phase**: 3 (Storage & UX)
**Complexity**: Medium
**Estimated Effort**: 4-5 hours
**Dependencies**: TASK-007

## Description

Implement storage layer selection dialogue, permission checking, duplicate detection, and enhanced user experience features including previews, confirmations, and improved error messages.

## Requirements

### Location
- Update `src/omniforge/skills/creation/agent.py`
- Update `src/omniforge/skills/creation/conversation.py`
- Update `src/omniforge/skills/creation/writer.py`

### Storage Layer Selection

**Supported Layers:**
| Layer | Path | Use Case |
|-------|------|----------|
| Project | `.omniforge/skills/` | Team/project-specific |
| Personal | `~/.omniforge/skills/` | Individual user |
| Enterprise | `~/.omniforge/enterprise/skills/` | Organization-wide |

**Selection Logic:**
```python
async def select_storage_layer(context: ConversationContext) -> str:
    # Check for explicit user preference
    if context.storage_layer_preference:
        return context.storage_layer_preference

    # Default heuristics
    if context.is_enterprise_admin:
        return "enterprise"

    if context.project_context_available:
        return "project"

    return "personal"
```

**User Dialogue:**
```
Where would you like to save this skill?

1. **Project** (.omniforge/skills/) - Team members in this project can use it
2. **Personal** (~/.omniforge/skills/) - Only you can use it
3. **Enterprise** (~/.omniforge/enterprise/skills/) - Available organization-wide

Enter your choice (1-3) or type the layer name:
```

### Permission Checking

```python
def check_storage_permission(
    layer: str, user_context: dict
) -> tuple[bool, str]:
    """Check if user can write to storage layer."""

    if layer == "enterprise":
        if not user_context.get("is_enterprise_admin"):
            return False, "Enterprise skills require admin permissions"

    if layer == "project":
        project_root = user_context.get("project_root")
        if not project_root or not Path(project_root).exists():
            return False, "No project context available"

    return True, ""
```

### Duplicate Detection

Before creating a skill, check for existing skills with similar names:

```python
def check_for_duplicates(
    skill_name: str,
    storage_manager: SkillStorageManager
) -> list[SkillIndexEntry]:
    """Find existing skills with similar names."""
    # Exact match
    # Fuzzy match (Levenshtein distance < 3)
    # Keyword overlap
```

**User Dialogue for Duplicates:**
```
I found an existing skill that might be similar:

- **product-formatter** (project): "Formats product names with title case..."

Would you like to:
1. Use the existing skill
2. Update the existing skill
3. Create a new skill with a different name
4. Proceed with creating '{skill_name}' anyway
```

### Enhanced User Experience

**1. Skill Preview Before Confirmation:**
```
Here's a preview of your skill:

---
name: {name}
description: {description}
---

# {Title}

{First 20 lines of body...}

[Preview truncated - full skill is {total_lines} lines]

Does this look correct? (yes/no/edit)
```

**2. Validation Error Explanations:**
```python
ERROR_MESSAGES = {
    "yaml_parse": "The skill file has a formatting issue. Let me fix that...",
    "unauthorized_fields": (
        "I included some extra fields that aren't allowed. "
        "Fixing to use only name and description..."
    ),
    "name_too_long": "The skill name is too long (max 64 characters). Shortening...",
    "name_format": "Skill names must be lowercase with hyphens. Converting...",
    "description_empty": "The skill needs a description. Generating one...",
    "description_not_third_person": "Description should be third person. Rewriting...",
    "description_missing_when": (
        "Description should explain when to use the skill. Adding..."
    ),
    "too_long": "The instructions are too long. Moving details to reference files...",
    "time_sensitive": (
        "Note: The skill contains potentially time-sensitive information. "
        "Consider using relative terms."
    ),
}
```

**3. Success Confirmation:**
```
Skill '{name}' created successfully!

Location: {full_path}

Your skill will:
- {brief description of behavior}

To invoke manually: "Use the {name} skill"

Would you like to:
- Create another skill
- Edit this skill
- View usage instructions
```

**4. Conversation Recovery:**
Handle interrupted conversations:
```
I see we were working on creating a skill earlier.

Current progress:
- Name: {skill_name}
- Pattern: {pattern}
- Status: {state}

Would you like to continue, or start fresh?
```

### ConversationContext Updates

Add new fields for Phase 3:

```python
class ConversationContext(BaseModel):
    # ... existing fields ...

    # Storage layer selection
    storage_layer_preference: Optional[str] = None
    available_layers: list[str] = ["project", "personal"]

    # Duplicate detection
    similar_skills_found: list[SkillIndexEntry] = []
    duplicate_action: Optional[str] = None  # "use", "update", "rename", "proceed"

    # UX state
    preview_shown: bool = False
    user_confirmed: bool = False
```

## Acceptance Criteria

- [ ] Storage layer selection dialogue implemented
- [ ] All 3 storage layers supported
- [ ] Permission checking prevents unauthorized writes
- [ ] Duplicate detection finds similar skills
- [ ] Skill preview shown before confirmation
- [ ] User-friendly error messages for all validation errors
- [ ] Success confirmation with next steps
- [ ] Conversation recovery for interrupted sessions
- [ ] Unit tests for storage layer logic
- [ ] Integration tests for full UX flow
- [ ] Test coverage > 80%

## Test Cases

```python
def test_check_storage_permission_enterprise_admin():
    can_write, error = check_storage_permission(
        "enterprise", {"is_enterprise_admin": True}
    )
    assert can_write is True

def test_check_storage_permission_enterprise_non_admin():
    can_write, error = check_storage_permission(
        "enterprise", {"is_enterprise_admin": False}
    )
    assert can_write is False
    assert "admin" in error.lower()

async def test_storage_selection_dialogue():
    agent = SkillCreationAgent(...)
    # ... complete skill creation up to SELECTING_STORAGE ...
    response = await agent.handle_message("Save to personal", session_id)
    ctx = agent.get_session_context(session_id)
    assert ctx.storage_layer == "personal"

def test_duplicate_detection():
    # Create existing skill
    # Try to create similar skill
    # Verify duplicate found
    duplicates = check_for_duplicates("format-product", storage_manager)
    assert len(duplicates) >= 1
```
