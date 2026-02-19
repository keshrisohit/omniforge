# Skills System: Required Fixes Based on Claude Code Documentation

**Date**: 2026-01-17
**Reference**: https://code.claude.com/docs/en/skills
**Status**: Action Required

---

## Executive Summary

The OmniForge skills system is largely well-designed and follows Claude Code patterns, but several critical gaps exist between the current implementation and the official Claude Code documentation. This document outlines required fixes to ensure full compliance with Claude Code standards and best practices.

**Priority Fixes**:
1. ✅ Add missing metadata fields (`user-invocable`, `disable-model-invocation`)
2. ✅ Fix hooks structure to match Claude Code format (PreToolUse/PostToolUse/Stop)
3. ✅ Improve skill tool description for better auto-discovery
4. ✅ Update SKILL.md examples to follow best practices
5. ✅ Add description length validation (max 1024 chars)
6. ✅ Add name length validation (max 64 chars)

---

## 1. Missing Metadata Fields

### Issue: `user-invocable` Field Missing

**Current State**: Not implemented in `SkillMetadata`

**Official Documentation**:
```yaml
user-invocable: false  # Hide from slash menu (default: true)
```

**Use Cases**:
- Model-only skills that users shouldn't invoke directly
- Internal skills for agent-to-agent communication
- Auto-applied skills based on context

**Impact**: Medium - Users cannot create skills that are hidden from manual invocation but available for model auto-discovery

**Fix Required**:
```python
# src/omniforge/skills/models.py - SkillMetadata class
user_invocable: bool = Field(True, alias="user-invocable")
```

---

### Issue: `disable-model-invocation` Field Missing

**Current State**: Not implemented in `SkillMetadata`

**Official Documentation**:
```yaml
disable-model-invocation: true  # Users can invoke, Claude cannot call programmatically
```

**Use Cases**:
- User-triggered workflows that shouldn't auto-activate
- Skills requiring explicit user consent
- Manual-only operations

**Impact**: Low - Edge case, but needed for complete Claude Code compatibility

**Fix Required**:
```python
# src/omniforge/skills/models.py - SkillMetadata class
disable_model_invocation: bool = Field(False, alias="disable-model-invocation")
```

---

## 2. Hooks Structure Incompatibility

### Issue: Current hooks don't match Claude Code format

**Current Implementation**:
```python
class SkillHooks(BaseModel):
    pre: Optional[str] = None   # Path to pre-activation script
    post: Optional[str] = None  # Path to post-execution script
```

**Claude Code Format**:
```yaml
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./scripts/security-check.sh $TOOL_INPUT"
          once: true
  PostToolUse:
    - matcher: "Read"
      hooks:
        - type: command
          command: "./scripts/audit-log.sh"
  Stop:
    - hooks:
        - type: command
          command: "./scripts/cleanup.sh"
```

**Key Differences**:
1. **Event-based structure**: PreToolUse, PostToolUse, Stop (not pre/post)
2. **Matchers**: Can specify which tools trigger hooks
3. **Hook properties**: `type`, `command`, `once` fields
4. **Multiple hooks per event**: Arrays of hooks

**Impact**: High - Current implementation doesn't support event-based hooks with tool matchers

**Fix Required**: Complete redesign of hooks structure

```python
# src/omniforge/skills/models.py

class HookDefinition(BaseModel):
    """Individual hook definition."""
    type: str = "command"  # Type of hook (currently only 'command')
    command: str          # Command to execute
    once: bool = False    # Run only once per session

class HookMatcher(BaseModel):
    """Hook with optional tool matcher."""
    matcher: Optional[str] = None  # Tool name pattern (e.g., "Bash", "Read")
    hooks: list[HookDefinition]    # Hooks to run for this matcher

class SkillHooks(BaseModel):
    """Skill lifecycle hooks configuration."""
    PreToolUse: Optional[list[HookMatcher]] = None
    PostToolUse: Optional[list[HookMatcher]] = None
    Stop: Optional[list[HookMatcher]] = None
```

**Migration Path**: Support both old and new formats for backward compatibility, deprecate old format

---

## 3. Skill Tool Description Quality

### Issue: Current description doesn't emphasize auto-discovery

**Current Implementation** (src/omniforge/skills/tool.py:210-233):
```python
description = f"""Load and activate an agent skill from a SKILL.md file.

PROGRESSIVE DISCLOSURE:
This tool uses a two-stage loading pattern:
1. Stage 1 (Tool Description): Lists available skills by name and description
2. Stage 2 (Activation): Loads full skill content when you invoke the tool

AVAILABLE SKILLS:
{skills_section}

USAGE:
Invoke this tool with a skill_name to load the skill's instructions...
"""
```

**Claude Code Best Practices**:
- Emphasize **when to use** the skill (trigger keywords)
- Make it **action-oriented** and specific
- Include **concrete capabilities**
- Focus on **auto-discovery** (model-invoked)

**Improved Description**:
```python
description = f"""Execute specialized skills within the main conversation.

WHEN TO USE:
Use this tool when you identify a task that matches one of the available specialized skills listed below. Skills are **model-invoked** — you should automatically select and activate the appropriate skill based on the user's request.

AVAILABLE SKILLS:
{skills_section}

HOW IT WORKS:
1. **Discovery**: You see skill names and descriptions above (Stage 1)
2. **Activation**: Invoke this tool with skill_name to load full instructions (Stage 2)
3. **Execution**: Follow the loaded skill's step-by-step guidance
4. **Reference**: Access additional docs and scripts as needed (Stage 3)

IMPORTANT:
- Invoke skills IMMEDIATELY when you detect a matching task
- Skills are auto-triggered based on description matching
- Don't wait for explicit user commands like "/skill-name"
- Full skill content only loads when you invoke this tool (progressive disclosure)

EXAMPLE:
User: "Review this code for quality issues"
→ You identify this matches "code-review" skill
→ Invoke: {{"skill_name": "code-review"}}
→ Receive full SKILL.md content with review procedures
→ Follow skill instructions to perform review
"""
```

**Impact**: Medium - Improves model understanding of when and how to use skills

---

## 4. SKILL.md Example Improvements

### Issue: pdf-generator SKILL.md doesn't follow all best practices

**Current pdf-generator/SKILL.md**:
```yaml
---
name: pdf-generator
description: Generate PDF documents from text descriptions using Python
allowed-tools:
  - Bash
  - Read
  - Write
model: claude-opus-4-5-20251101
context: inherit
priority: 0
tags:
  - pdf
  - document-generation
  - python
---
```

**Improvements Needed**:

1. **Description lacks trigger keywords**:
```yaml
# ❌ Current
description: Generate PDF documents from text descriptions using Python

# ✅ Improved (includes trigger keywords)
description: Generate PDF documents from text descriptions using Python. Use when working with PDF files, creating documents, converting text to PDF, or when the user mentions PDFs, reports, or document generation.
```

2. **Missing user-invocable field**:
```yaml
# Add if this should be model-only or user-invocable
user-invocable: true  # or false for model-only
```

3. **Remove OmniForge-specific fields** (if targeting Claude Code compatibility):
```yaml
# These are OmniForge extensions, document them separately
priority: 0  # OmniForge-specific
tags:        # OmniForge-specific
  - pdf
```

**Full Improved Example**:
```yaml
---
name: pdf-generator
description: Generate PDF documents from text descriptions using Python's reportlab library. Use when working with PDF files, creating documents, converting text to PDF, or when the user mentions PDFs, reports, document generation, or exportable formats.
allowed-tools:
  - Bash
  - Read
  - Write
model: claude-opus-4-5-20251101
context: inherit
user-invocable: true
# OmniForge extensions (not in Claude Code spec):
priority: 0
tags:
  - pdf
  - document-generation
  - python
---
```

**Impact**: Low - Improves discoverability but current version works

---

## 5. Metadata Validation Missing

### Issue: No max length validation for fields

**Claude Code Documentation**:
- `name`: max 64 characters
- `description`: max 1024 characters

**Current Implementation**:
```python
name: str = Field(..., min_length=1, max_length=255)  # 255 > 64 ❌
description: str  # No max length ❌
```

**Fix Required**:
```python
# src/omniforge/skills/models.py - SkillMetadata class
name: str = Field(..., min_length=1, max_length=64)  # Match Claude Code
description: str = Field(..., min_length=1, max_length=1024)  # Add validation
```

**Impact**: Low - Compatibility issue, current implementation more lenient

---

## 6. Skills Discovery Pattern

### Issue: Current implementation may not emphasize auto-triggering enough

**Claude Code Pattern**:
> "Skills are **model-invoked** — Claude automatically decides when to use them based on matching your request to the Skill's description."

**Current System Prompt** (from specs/skills-system-spec.md:596-598):
```markdown
## OmniForge Tool System
You have access to tools that extend your capabilities. Tools are functions you can invoke...
```

**Missing Emphasis**:
- Skills should be presented as **auto-trigger** based on task matching
- Description matching is the **primary discovery mechanism**
- No need for explicit "/skill-name" commands

**Recommended Addition to System Prompt**:
```markdown
## Skills: Auto-Applied Capabilities

Skills are specialized capabilities that you should automatically apply when you detect a matching task. Unlike tools that you explicitly choose, skills are **model-invoked** based on description matching.

**How Skills Work**:
1. **Discovery**: Available skills are listed in the Skill tool description
2. **Matching**: When you receive a task, compare it against skill descriptions
3. **Auto-Activation**: Invoke the Skill tool when you identify a match
4. **Execution**: Follow the loaded skill's instructions

**Example**:
- User: "Can you review this code?"
- You see: "code-review: Review code changes following team standards..."
- Action: Immediately invoke Skill tool with skill_name="code-review"
- Then: Follow the loaded skill instructions

**Important**: Don't wait for users to explicitly request a skill. Auto-trigger skills when task descriptions match.
```

**Impact**: Medium - Improves agent understanding of skill auto-discovery

---

## 7. Progressive Disclosure Documentation

### Issue: Need clearer explanation of what "progressive disclosure" means

**Current Explanation** (in tool description):
> "This tool uses a two-stage loading pattern..."

**Claude Code Emphasis**:
- Skill descriptions are **always available** (in tool description)
- Full SKILL.md content loads **only when invoked**
- Reference docs load **only when accessed**
- Scripts are **executed, never loaded** into context

**Recommended Enhancement**:
```markdown
## Progressive Disclosure Pattern

Skills minimize context consumption through three-stage loading:

**Stage 1 - Discovery (Always Loaded)**:
- Skill name and description visible in Skill tool description
- Cost: ~50-100 bytes per skill
- Purpose: Enable task matching without loading full content

**Stage 2 - Activation (On Tool Invocation)**:
- Full SKILL.md content loaded when you invoke the Skill tool
- Cost: 1-10KB per activated skill
- Purpose: Provide complete instructions when skill is relevant

**Stage 3 - Reference (On Demand)**:
- Reference docs loaded via Read tool only when skill instructs you to
- Scripts executed via Bash without loading their source code
- Cost: Only what you actually access
- Purpose: Make extensive docs available without bloating context

**Key Benefit**: 100+ skills available = ~10KB overhead, not 1MB+
```

**Impact**: Low - Educational, doesn't change functionality

---

## 8. Tool Restrictions Language

### Issue: Terminology mismatch with Claude Code

**Current**: `allowed-tools` (correct)
**Claude Code**: `allowed-tools` (matches ✅)

**Current Implementation**: Uses `allowed_tools` field correctly

**Terminology Check**:
- ✅ `allowed-tools` in YAML (correct)
- ✅ `allowed_tools` in Python (correct with alias)
- ✅ Tool restriction enforcement (implemented)

**No fix needed** - current implementation matches Claude Code

---

## Priority Action Items

### P0 - Critical (Breaks Compatibility)
1. **Add `user-invocable` field** to SkillMetadata
2. **Fix hooks structure** to support PreToolUse/PostToolUse/Stop format
3. **Update name max_length** from 255 to 64 characters
4. **Add description max_length** validation (1024 chars)

### P1 - High (Improves Functionality)
5. **Improve Skill tool description** to emphasize auto-discovery
6. **Add system prompt section** explaining skill auto-triggering
7. **Update pdf-generator example** with trigger keywords

### P2 - Medium (Nice to Have)
8. **Add `disable-model-invocation` field** for completeness
9. **Enhance progressive disclosure** documentation
10. **Create skill authoring guide** with best practices

---

## Backward Compatibility Strategy

### For Hooks Migration
```python
# Support both old and new formats
class SkillHooks(BaseModel):
    # New format (Claude Code)
    PreToolUse: Optional[list[HookMatcher]] = None
    PostToolUse: Optional[list[HookMatcher]] = None
    Stop: Optional[list[HookMatcher]] = None

    # Old format (deprecated)
    pre: Optional[str] = None
    post: Optional[str] = None

    @model_validator(mode='after')
    def migrate_old_format(self):
        """Migrate old pre/post format to new event-based format."""
        if self.pre and not self.PreToolUse:
            # Convert old 'pre' to PreToolUse
            self.PreToolUse = [HookMatcher(
                hooks=[HookDefinition(command=self.pre)]
            )]
        if self.post and not self.PostToolUse:
            # Convert old 'post' to PostToolUse
            self.PostToolUse = [HookMatcher(
                hooks=[HookDefinition(command=self.post)]
            )]
        return self
```

### For Name Length
- Current: max_length=255
- Required: max_length=64
- **Action**: Update validation, warn on existing skills > 64 chars

### For Missing Fields
- Add with sensible defaults
- Existing skills without these fields continue to work
- Document OmniForge-specific extensions separately

---

## Testing Requirements

### After Fixes
1. **Metadata Parsing**: Test all field formats (old and new hooks)
2. **Validation**: Test name/description length enforcement
3. **Tool Description**: Verify dynamic skills list generation
4. **Auto-Discovery**: Test model correctly matches task to skill description
5. **Hooks**: Test PreToolUse/PostToolUse/Stop execution
6. **Backward Compatibility**: Test existing SKILL.md files still work

---

## Documentation Updates Needed

1. **Update skills-system-spec.md**:
   - Add `user-invocable` and `disable-model-invocation` fields
   - Update hooks examples to new format
   - Clarify OmniForge extensions vs Claude Code standard

2. **Create SKILL.md authoring guide**:
   - Best practices for descriptions (trigger keywords)
   - Progressive disclosure patterns
   - Hook usage examples
   - Tool restriction examples

3. **Update .claude/skills/README.md**:
   - Document metadata fields
   - Show hook format examples
   - Explain auto-discovery mechanism

---

## Claude Code Compliance Scorecard

| Feature | Current | Required | Status |
|---------|---------|----------|--------|
| name field (kebab-case) | ✅ | ✅ | ✅ Pass |
| description field | ✅ | ✅ | ✅ Pass |
| allowed-tools field | ✅ | ✅ | ✅ Pass |
| model field | ✅ | ✅ | ✅ Pass |
| context field (inherit/fork) | ✅ | ✅ | ✅ Pass |
| agent field | ✅ | ✅ | ✅ Pass |
| hooks (event-based) | ❌ | ✅ | ❌ **Needs Fix** |
| user-invocable field | ❌ | ✅ | ❌ **Needs Fix** |
| disable-model-invocation | ❌ | Optional | ⚠️ Optional |
| name max 64 chars | ❌ (255) | ✅ | ❌ **Needs Fix** |
| description max 1024 chars | ❌ (none) | ✅ | ❌ **Needs Fix** |
| Progressive disclosure | ✅ | ✅ | ✅ Pass |
| Tool restrictions | ✅ | ✅ | ✅ Pass |
| SKILL.md format | ✅ | ✅ | ✅ Pass |

**Overall Compliance**: 9/14 = 64% (4 critical fixes needed)

---

## Recommendation

**Proceed with P0 fixes immediately** to achieve full Claude Code compatibility:

1. Update `SkillMetadata` model with missing fields
2. Redesign hooks structure (support both old and new)
3. Fix validation lengths
4. Update examples and documentation

**Estimated Effort**: 2-3 days for P0 fixes + testing

**Benefits**:
- Full Claude Code compatibility
- Better skill auto-discovery
- Industry-standard skill format
- Easier community skill sharing

---

## References

- **Claude Code Skills Documentation**: https://code.claude.com/docs/en/skills
- **OmniForge Skills Spec**: `/specs/skills-system-spec.md`
- **Current Implementation**: `/src/omniforge/skills/models.py`
- **Example Skill**: `/.claude/skills/pdf-generator/SKILL.md`
