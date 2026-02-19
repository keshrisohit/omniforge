"""
Skill Orchestrator Agent Demo

This script demonstrates a real agent that:
1. Loads all available skills dynamically
2. Figures out which skill(s) to use based on the prompt
3. Actually executes the skill(s) to get the job done

Usage:
    python examples/skill_orchestrator_demo.py
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path
from uuid import uuid4

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from omniforge.agents.models import TextPart
from omniforge.agents.skill_orchestrator import SkillOrchestratorAgent
from omniforge.tasks.models import Task, TaskMessage, TaskState


def create_task(message: str, agent_id: str = "skill-orchestrator") -> Task:
    """Create a task from a user message.

    Args:
        message: User's request
        agent_id: Agent identifier

    Returns:
        Task object
    """
    task_id = f"task-{uuid4().hex[:8]}"
    message_id = f"msg-{uuid4().hex[:8]}"

    return Task(
        id=task_id,
        agent_id=agent_id,
        state=TaskState.SUBMITTED,
        messages=[
            TaskMessage(
                id=message_id,
                role="user",
                parts=[TextPart(text=message)],
                created_at=datetime.utcnow(),
            )
        ],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        user_id="demo-user",
    )


async def run_agent_demo():
    """Run the skill orchestrator agent demo."""
    print("=" * 80)
    print("SKILL ORCHESTRATOR AGENT - LIVE DEMO")
    print("=" * 80)
    print()

    # Initialize agent with skills from src/omniforge/skills
    skills_path = Path(__file__).parent.parent / "src" / "omniforge" / "skills"
    print(f"📦 Initializing agent with skills from: {skills_path}")

    agent = SkillOrchestratorAgent(
        agent_id="skill-orchestrator-demo",
        skills_path=skills_path,
    )

    print(f"✅ Agent initialized: {agent.get_identity().name}")
    print(f"📚 Agent description: {agent.get_identity().description}")
    print()

    # Test cases with different types of requests
    test_cases = [
        {
            "name": "Data Analysis Only",
            "message": "Analyze the sales data and show me the key metrics",
        },
        {
            "name": "Report Generation Only",
            "message": "Generate a professional executive summary report",
        },
        {
            "name": "Multi-Skill Task",
            "message": "Analyze the Q1 sales data and create a comprehensive report with insights",
        },
        {
            "name": "Unclear Request",
            "message": "Help me with my work",
        },
    ]

    for i, test_case in enumerate(test_cases, 1):
        print("\n" + "=" * 80)
        print(f"TEST {i}: {test_case['name']}")
        print("=" * 80)
        print(f"📨 Request: {test_case['message']}")
        print("-" * 80)
        print()

        # Create task
        task = create_task(test_case["message"], agent_id=agent.get_identity().id)

        # Process task and stream events
        try:
            async for event in agent.process_task(task):
                if event.type == "status":
                    print(f"[Status] {event.state}")

                elif event.type == "message":
                    # Extract message content
                    for part in event.message_parts:
                        if hasattr(part, "text"):
                            print(part.text, end="")
                    print()  # New line after message

                elif event.type == "done":
                    print(f"\n[Done] Final state: {event.final_state}")

        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback

            traceback.print_exc()

        print()

    print("=" * 80)
    print("✅ DEMO COMPLETED")
    print("=" * 80)
    print()
    print("🎓 What just happened:")
    print("  1. Agent loaded all available skills (data-processor, report-generator)")
    print("  2. For each request, agent analyzed which skill(s) to use")
    print("  3. Agent loaded the full skill instructions")
    print("  4. Agent executed the skill(s) using LLM reasoning")
    print("  5. Agent returned the results")
    print()
    print("💡 Key Features Demonstrated:")
    print("  ✓ Dynamic skill discovery and loading")
    print("  ✓ Intelligent skill selection based on prompts")
    print("  ✓ Multi-skill orchestration for complex tasks")
    print("  ✓ Real-time execution with streaming results")
    print("  ✓ Tool restrictions enforcement")
    print()


async def interactive_mode():
    """Run agent in interactive mode."""
    print("=" * 80)
    print("SKILL ORCHESTRATOR AGENT - INTERACTIVE MODE")
    print("=" * 80)
    print()

    # Initialize agent
    skills_path = Path(__file__).parent.parent / "src" / "omniforge" / "skills"
    agent = SkillOrchestratorAgent(
        agent_id="skill-orchestrator-interactive",
        skills_path=skills_path,
    )

    print(f"✅ Agent: {agent.get_identity().name}")
    print(f"📚 Available skills: data-processor, report-generator")
    print()
    print("Type your requests below. Type 'quit' or 'exit' to stop.")
    print("-" * 80)
    print()

    while True:
        try:
            # Get user input
            user_input = input("You: ").strip()

            if user_input.lower() in ["quit", "exit", "q"]:
                print("\n👋 Goodbye!")
                break

            if not user_input:
                continue

            print()

            # Create and process task
            task = create_task(user_input, agent_id=agent.get_identity().id)

            async for event in agent.process_task(task):
                if event.type == "message":
                    for part in event.message_parts:
                        if hasattr(part, "text"):
                            print(part.text, end="")
                    print()

            print()

        except KeyboardInterrupt:
            print("\n\n👋 Interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print()


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Skill Orchestrator Agent Demo")
    parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Run in interactive mode",
    )
    args = parser.parse_args()

    if args.interactive:
        asyncio.run(interactive_mode())
    else:
        asyncio.run(run_agent_demo())


if __name__ == "__main__":
    main()
