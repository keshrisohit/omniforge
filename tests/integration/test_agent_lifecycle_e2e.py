"""End-to-end integration test: create agent → add skill → execute.

Tests the complete OmniForge agent lifecycle using real LLM calls (no mocking):
  1. Create an agent via MasterAgent's ReAct loop (create_agent tool)
  2. Verify the agent is registered with all library skills auto-loaded
  3. Add a new custom skill explicitly via the registry
  4. Execute the created agent on a real task

Requires ANTHROPIC_API_KEY to be set. Skipped otherwise.

Run:
    pytest tests/integration/test_agent_lifecycle_e2e.py -v -s
    python tests/integration/test_agent_lifecycle_e2e.py
"""

import asyncio
import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

# Load project .env so OMNIFORGE_* vars are available when running standalone
_env_path = Path(__file__).parent.parent.parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path)

pytestmark = pytest.mark.asyncio

# ---------------------------------------------------------------------------
# Skip if no LLM key is configured
# ---------------------------------------------------------------------------

_has_api_key = bool(
    os.environ.get("OMNIFORGE_OPENROUTER_API_KEY")
    or os.environ.get("OMNIFORGE_GROQ_API_KEY")
    or os.environ.get("OMNIFORGE_ANTHROPIC_API_KEY")
    or os.environ.get("OMNIFORGE_OPENAI_API_KEY")
)
skip_no_key = pytest.mark.skipif(not _has_api_key, reason="No LLM API key configured")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def collect_stream(gen) -> str:
    """Collect all chunks from an async generator into a single string."""
    chunks = []
    async for chunk in gen:
        print(chunk, end="", flush=True)
        chunks.append(chunk)
    return "".join(chunks)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def registry():
    from omniforge.agents.registry import AgentRegistry
    from omniforge.storage.memory import InMemoryAgentRepository

    return AgentRegistry(repository=InMemoryAgentRepository())


@pytest.fixture
def generator(registry):
    from omniforge.chat.master_response_generator import MasterResponseGenerator

    return MasterResponseGenerator(
        agent_registry=registry,
        tenant_id="e2e-test",
        user_id="test-user",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@skip_no_key
class TestAgentLifecycleE2E:
    """Full agent lifecycle integration tests using real LLM calls."""

    async def test_step1_create_agent_via_master_agent(self, generator, registry):
        """MasterAgent creates an agent via its ReAct loop using the create_agent tool."""
        from omniforge.tools.builtin.platform import list_all_skills

        print("\n" + "=" * 60)
        print("STEP 1 — Create agent via MasterAgent ReAct loop")
        print("=" * 60)

        response = await collect_stream(
            generator.generate_stream(
                "Create an agent called DataBot that helps with data analysis and reporting",
                session_id="step1",
            )
        )

        print(f"\n\nMasterAgent response:\n{response}")

        # Verify agent was registered in the registry
        agent = await registry.get("databot")
        assert agent is not None, "Agent 'databot' should be in registry after creation"
        assert agent.identity.name == "DataBot"

        # Verify the general skill was added
        skill_ids = {s.id for s in agent.skills}
        assert "databot-general" in skill_ids, "General skill should be auto-created"

        # Verify ALL library skills are auto-loaded
        library_skills = list_all_skills()
        for lib_skill in library_skills:
            assert lib_skill["id"] in skill_ids, (
                f"Library skill '{lib_skill['id']}' should be auto-loaded on creation"
            )

        print(f"\n✓ Agent '{agent.identity.name}' created with {len(agent.skills)} skills")
        print(f"  Skill IDs: {sorted(skill_ids)[:5]} ... ({len(skill_ids)} total)")

    async def test_step2_add_skill_to_agent(self, registry):
        """Add a new custom skill to the agent directly via the registry."""
        from omniforge.agents.models import AgentSkill, SkillInputMode, SkillOutputMode
        from omniforge.tools.base import ToolCallContext
        from omniforge.tools.builtin.platform import CreateAgentTool

        print("\n" + "=" * 60)
        print("STEP 2 — Add custom skill to agent")
        print("=" * 60)

        # Create agent via tool (deterministic, no LLM needed for this step)
        ctx = ToolCallContext(correlation_id="c1", task_id="t1", agent_id="master-agent")
        tool = CreateAgentTool(registry, tenant_id="e2e-test")
        result = await tool.execute(
            ctx,
            {"name": "ReportBot", "purpose": "Generate detailed reports", "capabilities": "reporting"},
        )
        assert result.success is True, f"Failed to create agent: {result.error}"

        agent_before = await registry.get("reportbot")
        skill_count_before = len(agent_before.skills)

        # Add a brand-new custom skill not in the library
        new_skill = AgentSkill(
            id="custom-analytics-v2",
            name="Custom Analytics v2",
            description="Advanced analytics capability added post-creation",
            input_modes=[SkillInputMode.TEXT],
            output_modes=[SkillOutputMode.TEXT],
        )
        await registry.add_skill_to_agent("reportbot", new_skill)

        # Verify the skill was persisted
        agent_after = await registry.get("reportbot")
        skill_ids = {s.id for s in agent_after.skills}

        assert "custom-analytics-v2" in skill_ids, "Custom skill should appear in agent's skills"
        assert len(agent_after.skills) == skill_count_before + 1, "Skill count should increase by 1"

        print(f"✓ Custom skill 'custom-analytics-v2' added to 'ReportBot'")
        print(f"  Skills before: {skill_count_before} → after: {len(agent_after.skills)}")

    @skip_no_key
    async def test_step3_execute_agent(self, registry):
        """Execute the created agent on a real task using the LLM."""
        from omniforge.agents.helpers import create_simple_task
        from omniforge.tools.base import ToolCallContext
        from omniforge.tools.builtin.platform import CreateAgentTool

        print("\n" + "=" * 60)
        print("STEP 3 — Execute created agent on a real task")
        print("=" * 60)

        # Create a simple agent
        ctx = ToolCallContext(correlation_id="c2", task_id="t2", agent_id="master-agent")
        tool = CreateAgentTool(registry, tenant_id="e2e-test")
        result = await tool.execute(
            ctx,
            {
                "name": "GreeterBot",
                "purpose": "Greet users warmly",
                "capabilities": "greeting, introduction",
            },
        )
        assert result.success is True

        agent = await registry.get("greeterbot")
        assert agent is not None

        # Execute the agent with a simple request
        task = create_simple_task(
            message="Say exactly: 'Hello from GreeterBot!'",
            agent_id="greeterbot",
            user_id="test-user",
            tenant_id="e2e-test",
        )

        print(f"\nSending task to '{agent.identity.name}'...")
        response_parts: list[str] = []

        async for event in agent.process_task(task):
            if hasattr(event, "message_parts"):
                for part in event.message_parts:
                    if hasattr(part, "text"):
                        print(part.text, end="", flush=True)
                        response_parts.append(part.text)

        print()
        full_response = "".join(response_parts).strip()

        assert full_response, "Agent should return a non-empty response"
        print(f"\n✓ Agent executed and responded: {full_response!r}")

    @skip_no_key
    async def test_full_lifecycle_end_to_end(self, generator, registry):
        """Complete flow: create agent (LLM) → add skill → execute agent (LLM)."""
        from omniforge.agents.helpers import create_simple_task
        from omniforge.agents.models import AgentSkill, SkillInputMode, SkillOutputMode
        from omniforge.tools.builtin.platform import list_all_skills

        print("\n" + "=" * 60)
        print("FULL E2E LIFECYCLE TEST")
        print("=" * 60)

        # ── STEP 1: Create agent via MasterAgent ReAct loop ──────────────
        print("\n[1/3] Creating agent via MasterAgent...")
        response = await collect_stream(
            generator.generate_stream(
                "Create an agent called AssistantBot that helps users answer questions",
                session_id="full-e2e",
            )
        )
        print()

        agent = await registry.get("assistantbot")
        assert agent is not None, "AssistantBot should be registered"
        assert agent.identity.name == "AssistantBot"

        library_skills = list_all_skills()
        agent_skill_ids = {s.id for s in agent.skills}
        for lib_skill in library_skills:
            assert lib_skill["id"] in agent_skill_ids

        print(f"✓ AssistantBot created — {len(agent.skills)} skills auto-loaded")

        # ── STEP 2: Add a new custom skill ───────────────────────────────
        print("\n[2/3] Adding custom skill to AssistantBot...")
        custom_skill = AgentSkill(
            id="e2e-custom-skill",
            name="E2E Custom Skill",
            description="A skill added as part of the e2e lifecycle test",
            input_modes=[SkillInputMode.TEXT],
            output_modes=[SkillOutputMode.TEXT],
        )
        await registry.add_skill_to_agent("assistantbot", custom_skill)

        agent = await registry.get("assistantbot")
        assert "e2e-custom-skill" in {s.id for s in agent.skills}
        print(f"✓ Custom skill added — total skills: {len(agent.skills)}")

        # ── STEP 3: Execute the agent ─────────────────────────────────────
        print("\n[3/3] Executing AssistantBot...")
        task = create_simple_task(
            message="Reply with exactly: 'AssistantBot is online!'",
            agent_id="assistantbot",
            user_id="test-user",
        )

        parts: list[str] = []
        async for event in agent.process_task(task):
            if hasattr(event, "message_parts"):
                for part in event.message_parts:
                    if hasattr(part, "text"):
                        print(part.text, end="", flush=True)
                        parts.append(part.text)
        print()

        response_text = "".join(parts).strip()
        assert response_text, "Agent should produce output"
        print(f"✓ Agent responded: {response_text!r}")

        print("\n" + "=" * 60)
        print("✓ FULL LIFECYCLE COMPLETE — all 3 steps passed")
        print("=" * 60)


# ---------------------------------------------------------------------------
# Standalone runner
# ---------------------------------------------------------------------------


async def run_demo() -> None:
    """Run the full e2e demo as a standalone script."""
    from omniforge.agents.helpers import create_simple_task
    from omniforge.agents.models import AgentSkill, SkillInputMode, SkillOutputMode
    from omniforge.agents.registry import AgentRegistry
    from omniforge.chat.master_response_generator import MasterResponseGenerator
    from omniforge.storage.memory import InMemoryAgentRepository
    from omniforge.tools.builtin.platform import list_all_skills

    if not _has_api_key:
        print("ERROR: No LLM API key configured.")
        print("Set OMNIFORGE_OPENROUTER_API_KEY or OMNIFORGE_GROQ_API_KEY in .env")
        sys.exit(1)

    registry = AgentRegistry(repository=InMemoryAgentRepository())
    generator = MasterResponseGenerator(
        agent_registry=registry,
        tenant_id="demo",
        user_id="demo-user",
    )

    # ── STEP 1: Create agent ──────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("[1/3] CREATE AGENT via MasterAgent ReAct loop")
    print("=" * 60)
    print("Sending: 'Create an agent called DataBot that helps with data analysis'\n")

    async for chunk in generator.generate_stream(
        "Create an agent called DataBot that helps with data analysis",
        session_id="demo",
    ):
        print(chunk, end="", flush=True)

    print("\n")

    try:
        agent = await registry.get("databot")
    except Exception:
        print("WARN: MasterAgent stream didn't create agent (LLM may have failed). Retrying...")
        async for chunk in generator.generate_stream(
            "Create an agent called DataBot for data analysis",
            session_id="demo-retry",
        ):
            print(chunk, end="", flush=True)
        print()
        agent = await registry.get("databot")

    library_skills = list_all_skills()
    print(f"✓ Agent '{agent.identity.name}' registered")
    print(f"  Skills auto-loaded: {len(agent.skills)} ({len(library_skills)} from library + 1 general)")

    # ── STEP 2: Add skill ─────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("[2/3] ADD CUSTOM SKILL to DataBot")
    print("=" * 60)

    new_skill = AgentSkill(
        id="advanced-charting",
        name="Advanced Charting",
        description="Generates advanced data visualizations and charts",
        input_modes=[SkillInputMode.TEXT],
        output_modes=[SkillOutputMode.TEXT],
    )
    await registry.add_skill_to_agent("databot", new_skill)
    agent = await registry.get("databot")
    print(f"✓ 'advanced-charting' skill added — total skills: {len(agent.skills)}")

    # ── STEP 3: Execute agent ─────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("[3/3] EXECUTE DataBot on a real task")
    print("=" * 60)
    print("Task: 'What does a data analyst do? Give me a 2-sentence answer.'\n")

    task = create_simple_task(
        message="What does a data analyst do? Give me a 2-sentence answer.",
        agent_id="databot",
        user_id="demo-user",
        tenant_id="demo",
    )

    response_parts: list[str] = []
    async for event in agent.process_task(task):
        if hasattr(event, "message_parts"):
            for part in event.message_parts:
                if hasattr(part, "text"):
                    print(part.text, end="", flush=True)
                    response_parts.append(part.text)

    print("\n")
    full_response = "".join(response_parts).strip()
    assert full_response, "Agent must produce a response"

    print("=" * 60)
    print("✓ FULL LIFECYCLE COMPLETE")
    print(f"  Agent created: DataBot (ID: databot)")
    print(f"  Skills: {len(agent.skills)}")
    print(f"  Response length: {len(full_response)} chars")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_demo())
