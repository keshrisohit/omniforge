"""Demo: Master Agent Response Generator

This demo shows how the Master Agent orchestrates tasks, creates agents,
and manages the platform through natural language conversation.
"""

import asyncio
from omniforge.chat.response_generator import ResponseGenerator
from omniforge.agents.registry import AgentRegistry
from omniforge.storage.memory import InMemoryAgentRepository


async def demo_master_agent():
    """Demonstrate Master Agent capabilities."""
    print("=" * 70)
    print("🤖 MASTER AGENT DEMO - OmniForge Platform Orchestration")
    print("=" * 70)
    print()

    # Create agent registry
    repository = InMemoryAgentRepository()
    registry = AgentRegistry(repository=repository)

    # Create response generator with Master Agent enabled
    generator = ResponseGenerator(
        use_master_agent=True, agent_registry=registry, tenant_id="demo-tenant"
    )

    # Demo scenarios
    scenarios = [
        {
            "name": "Agent Creation Request",
            "message": "Create an agent that processes customer data",
        },
        {
            "name": "Skill Creation Request",
            "message": "Create a skill for data validation",
        },
        {
            "name": "Task Execution Request",
            "message": "Analyze the sales data from last quarter",
        },
        {
            "name": "Information Query",
            "message": "List my agents",
        },
        {
            "name": "Platform Help",
            "message": "Help me understand what you can do",
        },
        {
            "name": "Unclear Request (Clarification)",
            "message": "Do something with the data",
        },
    ]

    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{'─' * 70}")
        print(f"Scenario {i}: {scenario['name']}")
        print(f"{'─' * 70}")
        print(f"\n💬 User: {scenario['message']}\n")
        print("🤖 Master Agent:\n")

        # Generate response
        try:
            async for chunk in generator.generate_stream(scenario["message"]):
                print(chunk, end="", flush=True)
            print("\n")  # Add spacing after response

        except Exception as e:
            print(f"\n❌ Error: {e}\n")

        # Pause between scenarios
        if i < len(scenarios):
            await asyncio.sleep(1)

    print("\n" + "=" * 70)
    print("✅ Demo Complete!")
    print("=" * 70)


async def demo_with_custom_agent():
    """Demonstrate Master Agent routing to custom agents."""
    print("\n" + "=" * 70)
    print("🔀 ADVANCED DEMO - Routing to Custom Agents")
    print("=" * 70)
    print()

    # Create registry and register a custom agent
    from omniforge.agents.base import BaseAgent
    from omniforge.agents.models import AgentIdentity, AgentCapabilities
    from omniforge.agents.events import TaskMessageEvent
    from omniforge.agents.models import TextPart
    from omniforge.tasks.models import Task

    class CustomDataAgent(BaseAgent):
        """Custom agent for data processing."""

        identity = AgentIdentity(
            id="data-processor",
            name="Data Processor",
            description="Analyzes and processes customer data and sales reports",
            version="1.0.0",
        )

        capabilities = AgentCapabilities(
            streaming=True,
            multi_turn=False,
        )

        async def process_task(self, task: Task):
            yield TaskMessageEvent(
                task_id=task.id,
                message_parts=[
                    TextPart(
                        text="📊 Data Processor Agent activated!\n\n"
                        "Analyzing your data:\n"
                        "- Customer records: 1,250\n"
                        "- Sales transactions: 3,840\n"
                        "- Revenue: $458,200\n\n"
                        "✅ Analysis complete!"
                    )
                ],
            )

    # Set up registry with custom agent
    repository = InMemoryAgentRepository()
    registry = AgentRegistry(repository=repository)

    custom_agent = CustomDataAgent(tenant_id="demo-tenant")
    await registry.register(custom_agent)

    # Create generator
    generator = ResponseGenerator(
        use_master_agent=True, agent_registry=registry, tenant_id="demo-tenant"
    )

    print("💬 User: Analyze the customer data\n")
    print("🤖 Master Agent:\n")

    async for chunk in generator.generate_stream("Analyze the customer data"):
        print(chunk, end="", flush=True)

    print("\n\n" + "=" * 70)
    print("✅ Advanced Demo Complete!")
    print("=" * 70)


async def demo_environment_modes():
    """Demonstrate different response generator modes."""
    print("\n" + "=" * 70)
    print("⚙️  CONFIGURATION DEMO - Response Generator Modes")
    print("=" * 70)
    print()

    test_message = "Hello, what can you help me with?"

    # Mode 1: Master Agent
    print("Mode 1: Master Agent Mode (Intelligent Orchestration)")
    print("-" * 70)
    print(f"💬 User: {test_message}\n")
    print("🤖 Master Agent:\n")

    generator_master = ResponseGenerator(use_master_agent=True)
    async for chunk in generator_master.generate_stream(test_message):
        print(chunk, end="", flush=True)

    print("\n\n")

    # Mode 2: Placeholder
    print("Mode 2: Placeholder Mode (Testing without API)")
    print("-" * 70)
    print(f"💬 User: {test_message}\n")
    print("🤖 Placeholder:\n")

    import os

    os.environ["OMNIFORGE_USE_PLACEHOLDER_LLM"] = "true"
    os.environ["OMNIFORGE_USE_MASTER_AGENT"] = "false"

    generator_placeholder = ResponseGenerator()
    async for chunk in generator_placeholder.generate_stream(test_message):
        print(chunk, end="", flush=True)

    # Clean up env vars
    os.environ["OMNIFORGE_USE_PLACEHOLDER_LLM"] = "false"
    os.environ["OMNIFORGE_USE_MASTER_AGENT"] = "true"

    print("\n\n" + "=" * 70)
    print("✅ Configuration Demo Complete!")
    print("=" * 70)


async def main():
    """Run all demos."""
    print("\n\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 15 + "OMNIFORGE MASTER AGENT DEMO" + " " * 25 + "║")
    print("║" + " " * 10 + "Intelligent Platform Orchestration" + " " * 23 + "║")
    print("╚" + "=" * 68 + "╝")
    print()

    try:
        # Run basic demo
        await demo_master_agent()

        # Run advanced demo with custom agent
        await demo_with_custom_agent()

        # Run configuration demo
        await demo_environment_modes()

        print("\n\n" + "=" * 70)
        print("🎉 ALL DEMOS COMPLETED SUCCESSFULLY!")
        print("=" * 70)
        print()
        print("Key Takeaways:")
        print("• Master Agent intelligently routes requests")
        print("• Can orchestrate agent creation, skills, and tasks")
        print("• Discovers and delegates to specialized agents")
        print("• Provides helpful guidance and clarifications")
        print("• Configurable via environment variables")
        print()

    except Exception as e:
        print(f"\n\n❌ Demo failed with error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
