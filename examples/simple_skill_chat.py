#!/usr/bin/env python3
"""
Simple Interactive Skill Creation Chat

This is a simple, user-friendly script that lets you chat with an AI agent
to create custom skills for OmniForge. Just run it and start describing
what skill you want to create!

Usage:
    python examples/simple_skill_chat.py

Commands:
    - Just type what skill you want to create
    - Type 'quit', 'exit', or 'q' to exit
    - Type 'help' for tips on creating skills
    - Type 'new' to start creating a new skill
"""

import asyncio
import sys
from pathlib import Path
from uuid import uuid4

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from omniforge.skills.creation.agent import SkillCreationAgent
from omniforge.chat.llm_generator import LLMResponseGenerator


def print_welcome():
    """Print welcome message."""
    print()
    print("=" * 80)
    print(" " * 20 + "🚀 OmniForge Skill Creation Chat 🚀")
    print("=" * 80)
    print()
    print("Welcome! I'm here to help you create custom skills for OmniForge.")
    print()
    print("📝 How it works:")
    print("   1. Tell me what skill you want to create")
    print("   2. I'll ask you questions to understand your needs")
    print("   3. Once we have all the details, I'll generate your skill")
    print("   4. Your skill will be saved and ready to use!")
    print()
    print("💡 Example requests:")
    print("   • 'Create a skill for processing CSV files'")
    print("   • 'I need a skill to format product names'")
    print("   • 'Help me make a skill for analyzing JSON data'")
    print()
    print("Commands: 'help' for tips, 'new' for new skill, 'quit' or 'exit' to leave")
    print("-" * 80)
    print()


def print_help():
    """Print help message with tips."""
    print()
    print("=" * 80)
    print("💡 Tips for Creating Great Skills")
    print("=" * 80)
    print()
    print("1. Be Specific About Purpose:")
    print("   ✓ 'Create a skill to validate email addresses'")
    print("   ✗ 'Create something for emails'")
    print()
    print("2. Describe What It Should Do:")
    print("   • What inputs does it need?")
    print("   • What outputs should it produce?")
    print("   • What tools does it need? (bash, read files, web access, etc.)")
    print()
    print("3. Provide Examples:")
    print("   • Show example inputs and expected outputs")
    print("   • Describe edge cases or special scenarios")
    print()
    print("4. Skills are Great For:")
    print("   ✓ Repeated tasks with consistent patterns")
    print("   ✓ Domain-specific workflows (data analysis, reports, etc.)")
    print("   ✓ Tasks requiring specific tool combinations")
    print("   ✓ Standardized processes across your team")
    print()
    print("5. Answer My Questions:")
    print("   I'll ask clarifying questions to better understand your needs.")
    print("   The more specific you are, the better your skill will be!")
    print()
    print("-" * 80)
    print()


async def chat_loop():
    """Main chat loop for skill creation."""
    print_welcome()

    # Initialize the skill creation agent
    print("🔧 Initializing agent...")
    try:
        llm_generator = LLMResponseGenerator(temperature=0.7)
        agent = SkillCreationAgent(llm_generator)
        print("✅ Agent ready! Let's create some skills!\n")
    except Exception as e:
        print(f"❌ Error initializing agent: {e}")
        print("Please check your LLM configuration (.env file) and try again.")
        return

    # Generate a unique session ID and tenant ID for this conversation
    session_id = f"session-{uuid4().hex[:8]}"
    tenant_id = "default-user"  # For local/demo usage, use a default tenant
    print(f"💬 Session ID: {session_id}\n")

    # Main chat loop
    while True:
        try:
            # Get user input
            user_input = input("You: ").strip()

            # Handle empty input
            if not user_input:
                continue

            # Handle commands
            if user_input.lower() in ["quit", "exit", "q"]:
                print("\n👋 Thanks for using OmniForge! Happy skill building!\n")
                break

            if user_input.lower() == "help":
                print_help()
                continue

            if user_input.lower() in ["new", "start over", "reset"]:
                # Start a new session
                session_id = f"session-{uuid4().hex[:8]}"
                print(f"\n🆕 Starting new skill creation session: {session_id}")
                print("What skill would you like to create?\n")
                continue

            # Process the message with the agent
            print("\n🤖 Agent: ", end="", flush=True)

            # Stream the agent's response
            response_text = ""
            async for chunk in agent.handle_message(user_input, session_id, tenant_id):
                # Print the chunk as it streams
                print(chunk, end="", flush=True)
                response_text += chunk

            print("\n")  # New line after complete response

            # Check if the skill was saved successfully
            if "saved successfully" in response_text.lower() or "skill is ready" in response_text.lower():
                print("🎉 Your skill is ready to use! Type 'new' to create another skill.\n")
                # Start a new session for the next skill
                session_id = f"session-{uuid4().hex[:8]}"

        except KeyboardInterrupt:
            print("\n\n👋 Interrupted. Goodbye!\n")
            break
        except Exception as e:
            print(f"\n\n❌ Error: {e}\n")
            print("Let's try again. What would you like to do?\n")
            # Optionally restart the session on error
            session_id = f"session-{uuid4().hex[:8]}"


def main():
    """Entry point for the script."""
    try:
        asyncio.run(chat_loop())
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        print("Please check your setup and try again.\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
