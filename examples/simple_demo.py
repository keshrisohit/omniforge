#!/usr/bin/env python
"""Simple demo of SimpleAutonomousAgent.

Run this to see the autonomous agent in action!
"""

import asyncio
from omniforge.agents import SimpleAutonomousAgent


async def demo_1_simplest():
    """Demo 1: Simplest possible usage."""
    print("\n" + "=" * 70)
    print("Demo 1: Simplest Usage - Just Pass a Prompt")
    print("=" * 70 + "\n")

    agent = SimpleAutonomousAgent()

    result = await agent.run(
        "List all Python files in the src/omniforge/agents/ directory"
    )

    print(f"Result:\n{result}\n")


async def demo_2_custom_prompt():
    """Demo 2: Custom system prompt."""
    print("\n" + "=" * 70)
    print("Demo 2: Custom System Prompt")
    print("=" * 70 + "\n")

    agent = SimpleAutonomousAgent(
        system_prompt="""You are a helpful file system assistant.

When listing files:
- Show file sizes in KB
- Sort by size (largest first)
- Be concise"""
    )

    result = await agent.run(
        "Show me the 5 largest Python files in src/"
    )

    print(f"Result:\n{result}\n")


async def demo_3_multi_step():
    """Demo 3: Multi-step task."""
    print("\n" + "=" * 70)
    print("Demo 3: Multi-Step Task")
    print("=" * 70 + "\n")

    agent = SimpleAutonomousAgent(
        system_prompt="You are a code analyst. Present findings clearly.",
        max_iterations=20,  # More iterations for complex task
    )

    result = await agent.run("""
    Analyze the agents module:
    1. Count how many Python files are in src/omniforge/agents/
    2. Find the largest file
    3. Count total lines of code (approximately)
    4. List the main agent classes
    """)

    print(f"Analysis:\n{result}\n")


async def demo_4_streaming():
    """Demo 4: Watch agent reasoning in real-time."""
    print("\n" + "=" * 70)
    print("Demo 4: Streaming - Watch the Agent Think")
    print("=" * 70 + "\n")

    from omniforge.agents.helpers import create_simple_task

    agent = SimpleAutonomousAgent(max_iterations=10)

    task = create_simple_task(
        message="Count how many test files exist in tests/agents/",
        agent_id=agent.identity.id,
    )

    print("Streaming agent reasoning:\n")

    async for event in agent.process_task(task):
        if hasattr(event, "step"):
            step = event.step
            if step.type == "thinking":
                print(f"💭 {step.thinking.content}")
            elif step.type == "tool_call":
                print(f"🔧 Calling: {step.tool_call.tool_name}")
            elif step.type == "tool_result":
                if step.tool_result.success:
                    print(f"✅ Success")
                else:
                    print(f"❌ Error: {step.tool_result.error}")
        elif hasattr(event, "message_parts"):
            print(f"\n📝 Final Answer:")
            for part in event.message_parts:
                if hasattr(part, "text"):
                    print(f"{part.text}")

    print()


async def demo_5_one_liner():
    """Demo 5: One-liner convenience function."""
    print("\n" + "=" * 70)
    print("Demo 5: One-Liner - run_autonomous_agent()")
    print("=" * 70 + "\n")

    from omniforge.agents import run_autonomous_agent

    result = await run_autonomous_agent(
        "How many directories are in the src/ folder?"
    )

    print(f"Result:\n{result}\n")


async def main():
    """Run all demos."""
    print("\n" + "=" * 70)
    print("SimpleAutonomousAgent Demo")
    print("=" * 70)

    demos = [
        demo_1_simplest,
        demo_2_custom_prompt,
        demo_3_multi_step,
        demo_4_streaming,
        demo_5_one_liner,
    ]

    for demo in demos:
        try:
            await demo()
        except Exception as e:
            print(f"⚠️  Demo failed: {e}\n")

    print("\n" + "=" * 70)
    print("Demo Complete!")
    print("=" * 70)
    print("\nNext steps:")
    print("- See examples/autonomous_agent_examples.py for 15 more examples")
    print("- Read docs/autonomous_agent_quickstart.md for full guide")
    print("- Check tests/agents/test_autonomous_simple.py for usage patterns")
    print()


if __name__ == "__main__":
    # Run all demos
    asyncio.run(main())

    # Or run individual demo:
    # asyncio.run(demo_1_simplest())
