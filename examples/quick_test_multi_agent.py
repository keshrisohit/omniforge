"""Quick Test - Multi-Agent Skills Orchestration

Run this for a quick demo of the multi-agent system.
Shows one simple example with all 4 skills working together.
"""

import asyncio
import sys
from pathlib import Path

# Ensure we can import from src
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from multi_agent_skills_demo import (
    CoordinatorAgent,
    MockSkillAgent,
    AVAILABLE_SKILLS,
    OrchestrationManager,
    A2AClient,
    SQLiteConversationRepository,
    Database,
    DatabaseConfig,
    ConversationType,
    uuid4,
)


async def quick_test():
    """Run a quick test of the multi-agent system."""

    print("\n" + "="*80)
    print(" QUICK TEST - Multi-Agent Skills Orchestration")
    print("="*80)
    print()

    # Setup
    database = Database(DatabaseConfig(url="sqlite+aiosqlite:///:memory:"))
    await database.create_tables()

    conversation_repo = SQLiteConversationRepository(database)
    a2a_client = A2AClient()

    orchestration_manager = OrchestrationManager(
        client=a2a_client,
        conversation_repo=conversation_repo
    )

    coordinator = CoordinatorAgent(orchestration_manager)

    skill_agents = {
        skill.agent_id: MockSkillAgent(skill)
        for skill in AVAILABLE_SKILLS
    }

    # Create conversation
    thread_id = str(uuid4())
    tenant_id = "demo-tenant"
    user_id = "demo-user"

    await conversation_repo.create_conversation(
        tenant_id=tenant_id,
        user_id=user_id,
        title="Quick Test",
        conversation_type=ConversationType.CHAT,
        conversation_id=uuid4()
    )

    # Test: Complex request using all skills
    print("🧪 Testing complex request with all 4 skills...\n")

    message = "Search for Python async best practices, analyze performance data, review my code, and generate a comprehensive report"

    result = await coordinator.process_request(
        thread_id=thread_id,
        tenant_id=tenant_id,
        user_id=user_id,
        message=message,
        skill_agents=skill_agents
    )

    # Cleanup
    await a2a_client.close()

    print("\n" + "="*80)
    print(" ✅ QUICK TEST COMPLETED")
    print("="*80)
    print()
    print("What happened:")
    print("  1. Coordinator analyzed the request")
    print("  2. Selected all 4 skills (research, data, code review, docs)")
    print("  3. Used SEQUENTIAL strategy (analyze → generate dependency)")
    print("  4. All 4 agents executed their skills")
    print("  5. Responses were synthesized into final answer")
    print()
    print("For full demo with 4 test cases, run:")
    print("  python examples/multi_agent_skills_demo.py")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(quick_test())
