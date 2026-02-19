"""Interactive Conversational Agent Builder.

A simple interactive CLI to test the conversational agent creation flow.

Usage:
    python examples/interactive_agent_builder.py
"""

import asyncio

from omniforge.builder.conversation import ConversationManager


def print_banner():
    """Print welcome banner."""
    print()
    print("=" * 70)
    print("  OMNIFORGE - CONVERSATIONAL AGENT BUILDER (INTERACTIVE DEMO)")
    print("=" * 70)
    print()
    print("This demo lets you create an automation agent through conversation.")
    print("Just answer the questions naturally!")
    print()
    print("Type 'quit' or 'exit' at any time to stop.")
    print("=" * 70)
    print()


async def interactive_session():
    """Run interactive agent creation session."""
    print_banner()

    # Setup
    manager = ConversationManager()
    conversation_id = "interactive-session"
    tenant_id = "demo-tenant"
    user_id = "demo-user"

    # Start conversation
    context = manager.start_conversation(conversation_id, tenant_id, user_id)

    print("🤖 Assistant: Hello! I can help you create an automation agent.")
    print()

    # Initial prompt
    print("🤖 Assistant: What would you like to automate?")
    print("              (e.g., 'weekly reports from Notion', 'daily standup summaries')")
    print()

    # Conversation loop
    turn = 0
    while context.state.value != "complete":
        turn += 1

        # Get user input
        user_input = input("👤 You: ").strip()
        print()

        # Check for exit
        if user_input.lower() in ["quit", "exit", "stop"]:
            print("👋 Goodbye!")
            return

        if not user_input:
            print("⚠️  Please enter something!")
            print()
            continue

        # Process input
        try:
            context, response = manager.process_user_input(conversation_id, user_input)

            # Display response
            print(f"🤖 Assistant: {response}")
            print()

            # Show progress
            state_progress = {
                "initial": "🔵",
                "understanding_goal": "🟢",
                "integration_setup": "🟡",
                "requirements_gathering": "🟠",
                "skill_design": "🟣",
                "testing": "🔴",
                "deployment": "⚪",
                "complete": "✅",
            }

            progress_icon = state_progress.get(context.state.value, "❓")
            print(f"   [{progress_icon} State: {context.state.value}]")
            print()

        except Exception as e:
            print(f"❌ Error: {e}")
            print()
            continue

    # Agent creation complete!
    print("=" * 70)
    print("🎉 AGENT CREATED SUCCESSFULLY!")
    print("=" * 70)
    print()

    if context.agent_config:
        print("📋 Your Agent Configuration:")
        print()
        print(f"   Name: {context.agent_config.name}")
        print(f"   Description: {context.agent_config.description}")
        print(f"   Trigger: {context.agent_config.trigger.value}")
        if context.agent_config.schedule:
            print(f"   Schedule: {context.agent_config.schedule}")
        print(f"   Skills: {len(context.agent_config.skills)}")
        print()

        print("🎯 Skills:")
        for skill in context.agent_config.skills:
            print(f"   {skill.order}. {skill.name}")
            print(f"      ID: {skill.skill_id}")
            print(f"      Source: {skill.source}")
        print()

        print("📝 Conversation Summary:")
        print(f"   Total messages: {len(context.messages)}")
        print(f"   Integration: {context.integration_type}")
        print()

    print("=" * 70)
    print()
    print("Next Steps:")
    print("  1. Review the agent configuration above")
    print("  2. Run the full demo: python examples/test_conversational_builder.py")
    print("  3. Run unit tests: pytest tests/builder/ -v")
    print()


def main():
    """Main entry point."""
    try:
        asyncio.run(interactive_session())
    except KeyboardInterrupt:
        print()
        print("👋 Interrupted. Goodbye!")
    except Exception as e:
        print()
        print(f"❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
