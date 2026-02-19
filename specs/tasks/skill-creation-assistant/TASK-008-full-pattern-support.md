# TASK-008: Workflow and Script-Based Skill Generation

**Phase**: 2 (Full Patterns)
**Complexity**: Medium-High
**Estimated Effort**: 4-5 hours
**Dependencies**: TASK-004, TASK-007

## Description

Extend the SkillMdGenerator and RequirementsGatherer to support Workflow and Script-based skill patterns beyond the Simple pattern implemented in Phase 1.

## Requirements

### Location
- Update `src/omniforge/skills/creation/generator.py`
- Update `src/omniforge/skills/creation/gatherer.py`
- Update `src/omniforge/skills/creation/prompts.py`

### Workflow Skills

**Characteristics:**
- Sequential procedures with numbered steps
- Checklists for each step
- Error handling guidance
- Clear output format

**Additional Context Needed:**
- workflow_steps: list[str] - ordered steps
- step_validations: dict[str, list[str]] - checklist items per step
- failure_handling: str - what to do on failure

**SKILL.md Body Structure:**
```markdown
# {Skill Title}

{Brief overview}

## Workflow

### Step 1: {Step Name}
- [ ] {Checklist item}
- [ ] {Checklist item}

### Step 2: {Step Name}
- [ ] {Checklist item}

## Error Handling

{What to do if steps fail}
```

### Script-Based Skills

**Characteristics:**
- Skills with executable scripts in scripts/ folder
- Scripts for deterministic operations
- Clear documentation of script usage

**Additional Context Needed:**
- scripts_needed: list[dict] with name, purpose, language
- script_inputs: what inputs each script needs
- when_to_use_scripts: guidance on script vs instruction

**SKILL.md Body Structure:**
```markdown
# {Skill Title}

{Brief overview}

## Available Scripts

### {script-name}.py
{Description of what the script does}

Usage:
```bash
python scripts/{script-name}.py [arguments]
```

## When to Use Scripts vs Instructions

- Use scripts for: {deterministic operations}
- Use instructions for: {flexible tasks}
```

### RequirementsGatherer Updates

Add pattern-specific questions:

```python
QUESTIONS_BY_PATTERN = {
    SkillPattern.WORKFLOW: [
        "What are the steps in this workflow?",
        "What should be checked/validated at each step?",
        "What's the final output or deliverable?",
        "What should happen if a step fails?",
    ],
    SkillPattern.SCRIPT_BASED: [
        "What specific operations should the scripts perform?",
        "What inputs do the scripts need?",
        "What language should the scripts be in (Python/Bash)?",
        "When should the script be used vs. instructions?",
    ],
}
```

Update `has_sufficient_context()` for each pattern:

**Workflow sufficient context:**
- skill_purpose defined
- At least 2 workflow_steps
- At least 1 trigger

**Script-based sufficient context:**
- skill_purpose defined
- At least 1 script_needed with name and purpose
- At least 1 trigger

### SkillMdGenerator Updates

Add pattern-specific generation:

```python
async def generate_body(self, context: ConversationContext) -> str:
    if context.skill_pattern == SkillPattern.WORKFLOW:
        return await self._generate_workflow_body(context)
    elif context.skill_pattern == SkillPattern.SCRIPT_BASED:
        return await self._generate_script_body(context)
    else:
        return await self._generate_simple_body(context)
```

### Prompts

Add pattern-specific generation prompts:

```python
WORKFLOW_SKILL_GENERATION_PROMPT = """Generate the Markdown body for a workflow skill.

Workflow steps:
{workflow_steps}

Validations per step:
{step_validations}

Failure handling:
{failure_handling}

Generate clear step-by-step instructions with checklists.
"""

SCRIPT_SKILL_GENERATION_PROMPT = """Generate the Markdown body for a script-based skill.

Scripts needed:
{scripts}

Generate documentation for each script with usage examples.
"""
```

## Acceptance Criteria

- [ ] RequirementsGatherer asks pattern-specific questions
- [ ] has_sufficient_context() works for all patterns
- [ ] SkillMdGenerator produces Workflow skill bodies
- [ ] SkillMdGenerator produces Script-based skill bodies
- [ ] Generated skills pass validation
- [ ] Unit tests for each pattern
- [ ] Integration test for full conversation with each pattern
- [ ] Test coverage > 80%

## Test Cases

```python
async def test_workflow_skill_generation():
    ctx = ConversationContext(
        skill_pattern=SkillPattern.WORKFLOW,
        skill_name="deployment-workflow",
        skill_description="Guides deployment...",
        workflow_steps=["Build", "Test", "Deploy"],
    )
    body = await generator.generate_body(ctx)
    assert "## Workflow" in body
    assert "### Step 1" in body

async def test_script_skill_generation():
    ctx = ConversationContext(
        skill_pattern=SkillPattern.SCRIPT_BASED,
        skill_name="data-processing",
        skill_description="Processes data...",
        scripts_needed=[{"name": "transform.py", "purpose": "Transform CSV"}],
    )
    body = await generator.generate_body(ctx)
    assert "## Available Scripts" in body
    assert "transform.py" in body
```
