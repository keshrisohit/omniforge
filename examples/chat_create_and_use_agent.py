"""Chat → Create Agent → Use Agent (Same Session)

Demonstrates the full lifecycle:
  1. User chats — describes what skill they want
  2. SkillCreationAgent writes a SKILL.md to the filesystem
  3. In the same session, load and activate that skill via SkillTool
  4. Skill persists on disk — future sessions find it automatically

Run:
  python examples/chat_create_and_use_agent.py
"""

import asyncio
from pathlib import Path

from omniforge.skills.creation.writer import SkillExistsError, SkillWriter
from omniforge.skills.loader import SkillLoader
from omniforge.skills.storage import SkillStorageManager, StorageConfig
from omniforge.skills.tool import SkillTool
from omniforge.tools.base import ToolCallContext

# Where skills will be stored (survives across sessions)
SKILLS_DIR = Path(__file__).parent.parent / ".omniforge" / "skills"
SKILL_NAME = "python-code-reviewer"


# ============================================================================
# Phase 1: Chat session — user describes what they want, agent saves the skill
# ============================================================================

async def phase1_create_via_chat() -> Path | None:
    print("=" * 70)
    print("PHASE 1 — Chat session: describe the agent, it gets created")
    print("=" * 70)
    print()

    # This is what the user types in a chat session:
    chat = [
        "I want an agent that reviews Python code for quality issues",
        "It should flag missing type hints, absent docstrings, and bad names",
        "Example: given `def add(x, y): return x+y`, it should warn about "
        "missing type hints and docstring",
        "Yes, save it",
    ]
    for msg in chat:
        print(f"  You:   {msg}")
    print()

    # The SkillCreationAgent processes the conversation and calls write_skill()
    # at the end. Here we call the writer directly with the content that the
    # agent's generator would produce — same result, no API key required.
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)

    skill_content = """\
---
name: python-code-reviewer
description: Reviews Python code for quality issues including missing type hints,
  absent docstrings, and poor naming conventions. Use when auditing code quality
  or enforcing Python style standards.
---

# Python Code Reviewer

You are a Python code quality expert. When given code, review it for:

1. **Type hints** — flag functions without parameter or return type annotations
2. **Docstrings** — flag public functions/classes with no docstring
3. **Naming** — flag single-letter variable names (outside loops) and non-descriptive names

## Output Format

For each issue found, report:
- Location (function/class name)
- Issue type (missing type hint / missing docstring / naming)
- Suggested fix

## Example

Input:
```python
def add(x, y):
    return x + y
```

Output:
- `add`: Missing type hints on `x`, `y`, and return value
- `add`: Missing docstring
"""

    config = StorageConfig(project_path=SKILLS_DIR)
    storage_manager = SkillStorageManager(config)
    writer = SkillWriter(storage_manager)

    print("  Agent: Let me create that skill for you...")
    print()
    try:
        skill_path = await writer.write_skill(
            skill_name=SKILL_NAME,
            content=skill_content,
            storage_layer="project",
        )
        print(f"  Agent: Done! Skill saved.")
        print(f"         Path: {skill_path}")
        return skill_path
    except SkillExistsError:
        existing = SKILLS_DIR / SKILL_NAME / "SKILL.md"
        print(f"  Agent: Skill already exists from a previous session.")
        print(f"         Path: {existing}")
        return existing


# ============================================================================
# Phase 2: Same session — immediately load and activate the skill
# ============================================================================

async def phase2_use_same_session() -> None:
    print()
    print("=" * 70)
    print("PHASE 2 — Same session: activate and use the new agent")
    print("=" * 70)
    print()

    config = StorageConfig(project_path=SKILLS_DIR)
    loader = SkillLoader(config)

    count = loader.build_index()
    print(f"  Skills on disk: {count}")

    if not loader.has_skill(SKILL_NAME):
        print(f"  ERROR: '{SKILL_NAME}' not found")
        return

    # Load full skill
    skill = loader.load_skill(SKILL_NAME)
    print(f"  Loaded:      {skill.metadata.name}")
    print(f"  Description: {skill.metadata.description[:80]}...")
    print()

    # Activate via SkillTool — this is how an agent picks up the skill
    skill_tool = SkillTool(loader)
    ctx = ToolCallContext(
        correlation_id="session-001",
        task_id="task-001",
        agent_id="user-session",
    )

    result = await skill_tool.execute(ctx, {"skill_name": SKILL_NAME})

    if result.success:
        print("  Skill activated! The agent now follows these instructions:")
        print()
        for line in result.result["content"].strip().splitlines()[:20]:
            print(f"    {line}")
        print("    ...")
    else:
        print(f"  Activation failed: {result.error}")


# ============================================================================
# Phase 3: Simulate a future session — skill is already on disk
# ============================================================================

def phase3_future_session() -> None:
    print()
    print("=" * 70)
    print("PHASE 3 — Future session: skill is persisted, no re-creation needed")
    print("=" * 70)
    print()

    # Fresh loader — same as a brand new process starting up
    config = StorageConfig(project_path=SKILLS_DIR)
    fresh_loader = SkillLoader(config)
    fresh_loader.build_index()

    if fresh_loader.has_skill(SKILL_NAME):
        entry = fresh_loader.get_skill_metadata(SKILL_NAME)
        print(f"  Found '{entry.name}' at:")
        print(f"  {entry.path}")
        print()
        print("  Any future session pointing to the same skills directory")
        print("  will automatically discover this skill without re-creating it.")
    else:
        print(f"  ERROR: '{SKILL_NAME}' not found in future session")


# ============================================================================
# Main
# ============================================================================

async def main() -> None:
    print()
    print("  OmniForge: Chat → Create Agent → Use Agent (Same Session)")
    print(f"  Skills dir: {SKILLS_DIR}")
    print()

    # 1. Chat session creates the skill
    skill_path = await phase1_create_via_chat()
    if not skill_path:
        return

    # 2. Use it immediately in the same session
    await phase2_use_same_session()

    # 3. Show it persists
    phase3_future_session()

    print()
    print("=" * 70)
    print("  Summary")
    print("=" * 70)
    print(f"  SKILL.md on disk : {SKILLS_DIR / SKILL_NAME / 'SKILL.md'}")
    print("  Re-run this script — Phase 1 will say 'already exists'")
    print("  and Phases 2 & 3 will work identically.")
    print("=" * 70)
    print()


if __name__ == "__main__":
    asyncio.run(main())
