# TASK-009: Resource Generator (scripts/, references/)

**Phase**: 2 (Full Patterns)
**Complexity**: Medium
**Estimated Effort**: 3-4 hours
**Dependencies**: TASK-008

## Description

Implement the ResourceGenerator class that generates bundled resources for skills, including executable scripts in `scripts/` and reference documentation in `references/`. This supports the progressive disclosure pattern from official Anthropic guidelines.

## Requirements

### Location
- Create `src/omniforge/skills/creation/resources.py`
- Update `src/omniforge/skills/creation/prompts.py`

### ResourceGenerator Class

```python
class ResourceGenerator:
    """Generate bundled resources for skills.

    Following official progressive disclosure pattern:
    - scripts/: Executable code for deterministic operations
    - references/: Documentation loaded as needed
    - assets/: Files used in output (templates, images)
    """

    def __init__(self, llm_generator: LLMResponseGenerator) -> None: ...

    async def generate_reference_doc(
        self,
        topic: str,
        context: ConversationContext,
    ) -> str:
        """Generate reference documentation file.

        Best practices:
        - Keep one level deep from SKILL.md
        - Include table of contents for files >100 lines
        - Structure for grep-ability
        """

    async def generate_script(
        self,
        name: str,
        purpose: str,
        language: str = "python",
    ) -> str:
        """Generate executable script for scripts/ folder.

        Best practices:
        - Scripts should be executable without loading into context
        - Include clear docstrings and error handling
        - Exit with appropriate codes
        """

    def determine_resource_structure(
        self,
        context: ConversationContext,
    ) -> dict[str, list[str]]:
        """Determine what bundled resources are needed.

        Returns:
            {"scripts": [...], "references": [...], "assets": [...]}
        """
```

### Script Generation

**Requirements:**
- Shebang line for bash scripts (`#!/bin/bash`)
- Docstring/header comment explaining purpose
- Clear argument handling
- Error handling with appropriate exit codes
- No hardcoded paths (use arguments or env vars)

**Python Script Template:**
```python
#!/usr/bin/env python3
"""
{description}

Usage:
    python scripts/{name}.py [args]
"""
import sys

def main():
    {implementation}

if __name__ == "__main__":
    main()
```

**Bash Script Template:**
```bash
#!/bin/bash
# {description}
#
# Usage: ./scripts/{name}.sh [args]

set -euo pipefail

{implementation}
```

### Reference Document Generation

**Requirements:**
- Markdown format
- Table of contents for docs >100 lines
- Clear section headings (grep-friendly)
- No time-sensitive information
- Focused on single topic

**Structure:**
```markdown
# {Topic}

{Brief introduction}

## Table of Contents (if >100 lines)
- [Section 1](#section-1)
- [Section 2](#section-2)

## Section 1

{Content}
```

### Prompts

```python
REFERENCE_DOC_GENERATION_PROMPT = """Generate a reference document for a skill's references/ folder.

Topic: {topic}
Skill purpose: {skill_purpose}
Context: {context}

REQUIREMENTS:
1. Keep focused on the specific topic
2. Include table of contents if over 100 lines
3. Structure for grep-ability (clear headings)
4. No time-sensitive information
5. Markdown format

Generate the reference document:
"""

SCRIPT_GENERATION_PROMPT = """Generate a {language} script for a skill's scripts/ folder.

Purpose: {purpose}
Script name: {name}

REQUIREMENTS:
1. Must be executable standalone
2. Include clear docstring and usage
3. Handle errors gracefully
4. Exit with appropriate codes
5. No hardcoded paths

Generate the complete script:
"""
```

### Integration with SkillWriter

Update SkillWriter.write_skill() to handle resources:

```python
async def write_skill(
    self,
    skill_name: str,
    content: str,
    storage_layer: str,
    resources: Optional[dict[str, str]] = None,  # {"scripts/x.py": content}
) -> Path:
    # Write SKILL.md
    # Write each resource file
    for resource_path, resource_content in (resources or {}).items():
        await self.write_bundled_resource(skill_dir, resource_path, resource_content)
```

## Acceptance Criteria

- [ ] generate_script() produces valid Python scripts
- [ ] generate_script() produces valid Bash scripts
- [ ] Generated scripts are syntactically correct
- [ ] generate_reference_doc() produces well-structured docs
- [ ] determine_resource_structure() identifies needed resources
- [ ] Scripts include proper error handling
- [ ] Reference docs include TOC when appropriate
- [ ] Integration with SkillWriter works correctly
- [ ] Unit tests for script generation
- [ ] Test coverage > 80%

## Test Cases

```python
async def test_generate_python_script():
    generator = ResourceGenerator(mock_llm)
    mock_llm.generate.return_value = "def main():\n    print('hello')"

    script = await generator.generate_script(
        name="process.py",
        purpose="Process input files",
        language="python"
    )

    assert "#!/usr/bin/env python3" in script
    assert "def main" in script

async def test_generate_bash_script():
    script = await generator.generate_script(
        name="validate.sh",
        purpose="Validate config",
        language="bash"
    )

    assert "#!/bin/bash" in script
    assert "set -euo pipefail" in script

async def test_generate_reference_doc():
    doc = await generator.generate_reference_doc(
        topic="API Authentication",
        context=mock_context
    )

    assert "# API Authentication" in doc
    assert "##" in doc  # Has sections

def test_determine_resource_structure_script_skill():
    ctx = ConversationContext(
        skill_pattern=SkillPattern.SCRIPT_BASED,
        scripts_needed=[{"name": "process.py", "purpose": "..."}]
    )
    structure = generator.determine_resource_structure(ctx)
    assert "scripts" in structure
    assert len(structure["scripts"]) == 1
```
