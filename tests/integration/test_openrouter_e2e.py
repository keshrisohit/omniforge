"""End-to-end OpenRouter integration test.

This test creates a skill file, registers an agent, and runs the agent
with real LLM calls via OpenRouter (no mocking).
"""

import os
from pathlib import Path

import pytest

from omniforge.agents.helpers import create_simple_task
from omniforge.agents.registry import AgentRegistry
from omniforge.agents.skill_orchestrator import SkillOrchestratorAgent
from omniforge.llm.config import load_config_from_env
from omniforge.chat.llm_generator import LLMResponseGenerator
from omniforge.storage.memory import InMemoryAgentRepository


@pytest.mark.integration
@pytest.mark.asyncio
async def test_openrouter_skill_orchestrator_e2e(tmp_path: Path) -> None:
    """Create a skill, register an agent, and execute it with OpenRouter."""
    api_key = os.getenv("OMNIFORGE_OPENROUTER_API_KEY")
    if not api_key:
        pytest.skip("OMNIFORGE_OPENROUTER_API_KEY is not set")

    config = load_config_from_env()
    model = config.default_model
    if not model.startswith("openrouter/"):
        pytest.skip("OMNIFORGE_LLM_DEFAULT_MODEL must be an openrouter/* model")

    # Create a minimal skill in a temporary skills directory
    skill_id = "e2e-test-skill"
    skills_root = tmp_path / "skills"
    skill_dir = skills_root / skill_id
    skill_dir.mkdir(parents=True, exist_ok=True)

    skill_md = """---
name: e2e-test-skill
description: End-to-end test skill using OpenRouter
allowed-tools:
  - llm
priority: 0
tags:
  - e2e
---

# E2E Test Skill

You are a testing skill. Follow the user's request precisely.
When asked to return a specific token, return it exactly with no extra text.
"""

    (skill_dir / "SKILL.md").write_text(skill_md, encoding="utf-8")

    # Create an agent that can discover and execute skills
    llm = LLMResponseGenerator(model=model)
    agent = SkillOrchestratorAgent(
        agent_id="e2e-skill-orchestrator",
        skills_path=skills_root,
        tenant_id="e2e-tenant",
        llm_generator=llm,
    )

    # Register agent (simulates creation + registry persistence)
    repo = InMemoryAgentRepository()
    registry = AgentRegistry(repository=repo)
    await registry.register(agent)

    # Run the agent against the skill
    task = create_simple_task(
        message=(
            "Use the skill named 'e2e-test-skill'. "
            "Return exactly: E2E_OK"
        ),
        agent_id=agent.identity.id,
        tenant_id="e2e-tenant",
        user_id="e2e-user",
    )

    events = []
    async for event in agent.process_task(task):
        events.append(event)

    assert events, "No events emitted by agent"

    # Confirm we reached a terminal event
    final_event = events[-1]
    assert getattr(final_event, "type", None) == "done"

    # Aggregate all message text for a simple assertion
    output_text = "".join(
        part.text
        for event in events
        if getattr(event, "type", None) == "message"
        for part in getattr(event, "message_parts", [])
        if hasattr(part, "text")
    )

    assert "E2E_OK" in output_text
