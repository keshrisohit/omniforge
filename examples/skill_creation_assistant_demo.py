#!/usr/bin/env python3
"""
Skill Creation Assistant Demo

This demo shows how to use the SkillCreationAgent to create skills
through natural conversation, following official Anthropic Agent Skills format.

The agent guides users through skill creation with intelligent questions,
generates SKILL.md files with proper structure, validates against official
specifications, and saves to the filesystem.
"""

import asyncio
from omniforge.skills.creation import SkillCreationAgent
from omniforge.chat.llm_generator import LLMResponseGenerator


async def demo_conversational_creation():
    """Demo: Create a skill through natural conversation."""
    print("=" * 80)
    print("DEMO 1: Conversational Skill Creation")
    print("=" * 80)
    print()

    # Initialize the agent
    llm_generator = LLMResponseGenerator()
    agent = SkillCreationAgent(llm_generator)

    print(f"Agent: {agent.identity.name}")
    print(f"Description: {agent.identity.description}")
    print(f"Version: {agent.identity.version}")
    print()

    # Simulate a conversation
    messages = [
        "I want to create a skill that helps format product names consistently",
        "It should convert to title case, remove extra spaces, and expand abbreviations",
        "PA -> Pro Analytics, ES -> Enterprise Suite",
        "Yes, that looks good!",
    ]

    print("Starting conversation...")
    print("-" * 80)

    session_id = None
    for user_message in messages:
        print(f"\nUser: {user_message}")

        # Process message and stream responses
        async for response in agent.handle_message(user_message, session_id):
            session_id = response.get("session_id")
            message = response.get("message", "")
            state = response.get("state")
            skill_path = response.get("skill_path")

            if message:
                print(f"Agent: {message}")
            if state:
                print(f"[State: {state}]")
            if skill_path:
                print(f"✓ Skill saved to: {skill_path}")

    print("\n" + "-" * 80)
    print("Conversation complete!")


async def demo_programmatic_creation():
    """Demo: Create a skill programmatically without conversation."""
    print("\n")
    print("=" * 80)
    print("DEMO 2: Programmatic Skill Creation")
    print("=" * 80)
    print()

    # Initialize the agent
    llm_generator = LLMResponseGenerator()
    agent = SkillCreationAgent(llm_generator)

    # Create skill directly with parameters
    print("Creating skill programmatically...")

    result = await agent.create_skill(
        name="data-validator",
        description=(
            "Validates data against schemas with type checking and constraint "
            "validation. Use when working with data validation, schema checking, "
            "or data quality tasks."
        ),
        purpose="Validate data against predefined schemas",
        examples=[
            "Input: {'age': -5} → Error: age must be positive",
            "Input: {'email': 'invalid'} → Error: invalid email format",
        ],
        pattern="SIMPLE",
        storage_layer="project",
    )

    if result.get("success"):
        print(f"✓ Skill created successfully!")
        print(f"  Path: {result['path']}")
        print(f"  Name: {result['name']}")
    else:
        print(f"✗ Skill creation failed: {result.get('error')}")


async def demo_validation_retry():
    """Demo: Automatic validation retry when content doesn't meet specs."""
    print("\n")
    print("=" * 80)
    print("DEMO 3: Validation with Auto-Retry")
    print("=" * 80)
    print()

    # Initialize the agent
    llm_generator = LLMResponseGenerator()
    agent = SkillCreationAgent(llm_generator)

    print("Creating skill with validation retry simulation...")
    print("(The agent will automatically retry if validation fails)")
    print()

    # Simulate a skill creation that might need validation retry
    messages = [
        "Create a skill for analyzing sales data",
        "It should query databases, aggregate metrics, and generate reports",
        "Yes, create the skill",
    ]

    session_id = None
    for user_message in messages:
        print(f"\nUser: {user_message}")

        async for response in agent.handle_message(user_message, session_id):
            session_id = response.get("session_id")
            message = response.get("message", "")
            state = response.get("state")

            if message:
                print(f"Agent: {message}")

            # Show validation attempts
            if state == "VALIDATING":
                print("  [Validating generated content...]")
            elif state == "FIXING_ERRORS":
                print("  [Validation failed, attempting to fix errors...]")


async def demo_session_management():
    """Demo: Multiple concurrent sessions."""
    print("\n")
    print("=" * 80)
    print("DEMO 4: Concurrent Session Management")
    print("=" * 80)
    print()

    # Initialize the agent
    llm_generator = LLMResponseGenerator()
    agent = SkillCreationAgent(llm_generator)

    print("Starting two concurrent conversations...")
    print()

    # Session 1
    print("Session 1 - Creating PDF skill:")
    session_1 = None
    async for response in agent.handle_message(
        "Create a skill for processing PDF files", session_1
    ):
        session_1 = response.get("session_id")
        print(f"  [{response.get('state')}] {response.get('message', '')[:60]}...")

    # Session 2
    print("\nSession 2 - Creating Excel skill:")
    session_2 = None
    async for response in agent.handle_message(
        "Create a skill for analyzing Excel spreadsheets", session_2
    ):
        session_2 = response.get("session_id")
        print(f"  [{response.get('state')}] {response.get('message', '')[:60]}...")

    print(f"\n✓ Both sessions running independently!")
    print(f"  Session 1 ID: {session_1}")
    print(f"  Session 2 ID: {session_2}")


def demo_agent_info():
    """Demo: Agent metadata and capabilities."""
    print("\n")
    print("=" * 80)
    print("DEMO 5: Agent Information")
    print("=" * 80)
    print()

    llm_generator = LLMResponseGenerator()
    agent = SkillCreationAgent(llm_generator)

    print("Agent Metadata:")
    print(f"  ID: {agent.identity.id}")
    print(f"  Name: {agent.identity.name}")
    print(f"  Version: {agent.identity.version}")
    print(f"  Description: {agent.identity.description}")
    print()

    print("Capabilities:")
    print("  ✓ Conversational skill creation")
    print("  ✓ Programmatic skill creation")
    print("  ✓ Intelligent pattern detection (Simple, Workflow, Reference, Script)")
    print("  ✓ Official Anthropic format compliance")
    print("  ✓ Automatic validation with retry (up to 3 attempts)")
    print("  ✓ Concurrent session management")
    print("  ✓ Progressive disclosure support")
    print("  ✓ Atomic filesystem operations")
    print()

    print("Official Anthropic Format:")
    print("  • Frontmatter: Only 'name' and 'description' fields")
    print("  • Name: kebab-case, max 64 chars")
    print("  • Description: Third person, includes WHAT + WHEN")
    print("  • Body: Under 500 lines, progressive disclosure patterns")


async def main():
    """Run all demos."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "SKILL CREATION ASSISTANT DEMO" + " " * 29 + "║")
    print("╚" + "=" * 78 + "╝")
    print()

    # Run demos
    demo_agent_info()

    # Uncomment to run interactive demos (requires LLM)
    # await demo_conversational_creation()
    # await demo_programmatic_creation()
    # await demo_validation_retry()
    # await demo_session_management()

    print("\n")
    print("=" * 80)
    print("Demo Complete!")
    print("=" * 80)
    print()
    print("To try the agent yourself:")
    print("  1. Initialize: agent = SkillCreationAgent(llm_generator)")
    print("  2. Send message: async for response in agent.handle_message(msg):")
    print("  3. Or create directly: result = await agent.create_skill(...)")
    print()


if __name__ == "__main__":
    asyncio.run(main())
