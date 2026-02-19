"""Example: Using seed data and test scenarios in your code.

This example demonstrates how to use the seeding utilities and
test scenarios to quickly set up test environments.
"""

import asyncio

from scripts.seed_data import seed_agents
from scripts.test_scenarios import (
    create_test_task,
    scenario_agent_discovery_by_skill,
    scenario_simple_task_completion,
)


async def example_using_seed_data() -> None:
    """Demonstrate using seed data in your application."""
    print("=" * 80)
    print("Example: Using Seed Data and Test Scenarios")
    print("=" * 80)
    print()

    # Step 1: Get pre-seeded repositories
    print("Step 1: Loading pre-seeded data...")
    print("-" * 80)
    registry, task_repo = await seed_agents()
    print()

    # Step 2: Use agents from the seeded data
    print("Step 2: Working with seeded agents...")
    print("-" * 80)

    # Get a specific agent
    data_agent = await registry.get("data-analysis-agent")
    print(f"✅ Retrieved agent: {data_agent.identity.name}")
    print(f"   Version: {data_agent.identity.version}")
    print(f"   Skills: {', '.join(s.name for s in data_agent.skills)}")
    print()

    # Step 3: Create and process a task
    print("Step 3: Creating and processing a task...")
    print("-" * 80)

    task = await create_test_task(
        agent_id="data-analysis-agent", message="Analyze quarterly sales trends"
    )
    await task_repo.save(task)
    print(f"✅ Created task: {task.id}")

    # Process the task
    event_count = 0
    async for event in data_agent.process_task(task):
        event_count += 1
        if event.type == "message":
            for part in event.message_parts:
                if part.type == "text":
                    print(f"   Agent: {part.text}")

    print(f"✅ Processed task with {event_count} events")
    print()

    # Step 4: Use pre-built test scenarios
    print("Step 4: Using pre-built test scenarios...")
    print("-" * 80)

    # Run a simple task completion scenario
    completed_task, events = await scenario_simple_task_completion(
        registry,
        task_repo,
        "code-generation-agent",
        "Write a function to reverse a string",
    )

    print("✅ Scenario completed!")
    print(f"   Task state: {completed_task.state}")
    print(f"   Events received: {len(events)}")
    print()

    # Step 5: Discover agents by capability
    print("Step 5: Discovering agents by skill...")
    print("-" * 80)

    coding_agents = await scenario_agent_discovery_by_skill(registry, "code-generation")
    print(f"✅ Found {len(coding_agents)} agent(s) with code-generation skill")
    for agent in coding_agents:
        print(f"   • {agent.identity.name}")
        print("     Capabilities: ", end="")
        caps = []
        if agent.capabilities.streaming:
            caps.append("streaming")
        if agent.capabilities.multi_turn:
            caps.append("multi-turn")
        print(", ".join(caps))
    print()

    # Step 6: List all available agents
    print("Step 6: Listing all available agents...")
    print("-" * 80)

    all_agents = await registry.list_all()
    print(f"✅ Total agents available: {len(all_agents)}")
    print()
    print("Agent Catalog:")
    for agent in all_agents:
        print(f"\n  📦 {agent.identity.name}")
        print(f"     ID: {agent.identity.id}")
        print(f"     Version: {agent.identity.version}")
        print(f"     Description: {agent.identity.description}")
        print(f"     Skills ({len(agent.skills)}):")
        for skill in agent.skills:
            print(f"       • {skill.name}")
            print(f"         Tags: {', '.join(skill.tags or [])}")

    print()
    print("=" * 80)
    print("✅ Example complete!")
    print("=" * 80)
    print()
    print("Key Takeaways:")
    print("  • Use seed_agents() to quickly get pre-populated repositories")
    print("  • Use create_test_task() to generate test tasks easily")
    print("  • Use scenario_* functions for common testing patterns")
    print("  • All agents are fully functional and can process tasks")
    print()


if __name__ == "__main__":
    asyncio.run(example_using_seed_data())
