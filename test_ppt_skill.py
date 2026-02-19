"""
Test script for automatic PPT skill selection and execution.

This demonstrates:
1. Pass a natural language message
2. System figures out pptx skill is needed
3. Executes the skill automatically
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path
from uuid import uuid4

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from omniforge.agents.models import TextPart
from omniforge.agents.skill_orchestrator import SkillOrchestratorAgent
from omniforge.tasks.models import Task, TaskMessage, TaskState


def create_task(message: str) -> Task:
    """Create a task from a user message."""
    task_id = f"task-{uuid4().hex[:8]}"
    message_id = f"msg-{uuid4().hex[:8]}"

    return Task(
        id=task_id,
        agent_id="skill-orchestrator",
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
        user_id="test-user",
    )


async def test_ppt_skill():
    """Test automatic PPT skill selection."""
    print("=" * 80)
    print("TESTING AUTOMATIC SKILL SELECTION FOR PPT CREATION")
    print("=" * 80)
    print()

    # Initialize agent with skills from src/omniforge/skills
    skills_path = Path(__file__).parent / "src" / "omniforge" / "skills"
    print(f"📦 Loading skills from: {skills_path}")

    agent = SkillOrchestratorAgent(
        agent_id="ppt-test-agent",
        skills_path=skills_path,
    )

    print(f"✅ Agent initialized: {agent.get_identity().name}")
    print()

    # Test message - should automatically select pptx skill
    test_message = "Create a PDF about how to build agentic system and tool calling make it detailed, once the pdf is created create a excle fils having word count of the pdf"

    print(f"📨 User Message: {test_message}")
    print("-" * 80)
    print()

    # Create and process task
    task = create_task(test_message)

    # Stream execution events
    async for event in agent.process_task(task):
        if event.type == "status":
            print(f"[Status] {event.state}")

        elif event.type == "message":
            # Print message content
            for part in event.message_parts:
                if hasattr(part, "text"):
                    print(part.text, end="")
            print()

        elif event.type == "done":
            print(f"\n[Done] Final state: {event.final_state}")



if __name__ == "__main__":
    asyncio.run(test_ppt_skill())
