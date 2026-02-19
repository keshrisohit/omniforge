"""Quick Start: Create and Run a Custom Agent in 5 Minutes.

This is the simplest possible example of creating and running an agent.
Perfect for getting started quickly!
"""

import asyncio
from datetime import datetime

from omniforge.agents.cot.agent import CoTAgent
from omniforge.agents.cot.engine import ReasoningEngine
from omniforge.agents.models import (
    AgentCapabilities,
    AgentIdentity,
    AgentSkill,
    SkillInputMode,
    SkillOutputMode,
    TextPart,
)
from omniforge.prompts.sdk import PromptConfig
from omniforge.tasks.models import Task, TaskMessage, TaskState
from omniforge.tools.registry import ToolRegistry


# Step 1: Define Your Agent
class MyFirstAgent(CoTAgent):
    """My first custom agent!"""

    # Define who your agent is
    identity = AgentIdentity(
        id="my-first-agent",
        name="My First Agent",
        description="A simple agent that helps with tasks",
        version="1.0.0",
    )

    # Define what your agent can do
    capabilities = AgentCapabilities(streaming=True)

    # Define your agent's skills
    skills = [
        AgentSkill(
            id="helper-skill",
            name="Helper",
            description="Helps with various tasks",
            input_modes=[SkillInputMode.TEXT],
            output_modes=[SkillOutputMode.TEXT],
        )
    ]

    # Step 2: Implement the reasoning logic
    async def reason(self, task: Task, engine: ReasoningEngine) -> str:
        """This is where your agent does its work!"""

        # Get the user's message
        user_message = task.messages[0].parts[0].text

        # Add a thinking step (visible to users)
        engine.add_thinking(f"The user asked: '{user_message}'. Let me think about how to help...")

        # Do some reasoning
        engine.add_thinking("I'll provide a helpful and friendly response.")

        # Return your final answer
        return f"Hello! You said: '{user_message}'\n\nI'm here to help! What would you like to know?"


# Step 3: Run Your Agent
async def main():
    # Create your agent
    # Note: You can add a prompt_config when calling reason() or via your LLM calls
    agent = MyFirstAgent(
        tool_registry=ToolRegistry(),
    )

    print(f"✓ Created agent: {agent.identity.name}\n")

    # Create a task for your agent
    task = Task(
        id="test-task",
        agent_id=agent.identity.id,
        state=TaskState.SUBMITTED,
        messages=[
            TaskMessage(
                id="msg-1",
                role="user",
                parts=[TextPart(text="Hello! Can you help me?")],
                created_at=datetime.utcnow(),
            )
        ],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        user_id="user-123",
    )

    print(f"User: {task.messages[0].parts[0].text}\n")
    print("Agent is thinking...\n")

    # Run your agent!
    from omniforge.agents.cot.events import ReasoningStepEvent
    from omniforge.agents.events import TaskMessageEvent

    async for event in agent.process_task(task):
        # Show reasoning steps
        if isinstance(event, ReasoningStepEvent):
            if event.step.thinking:
                print(f"💭 {event.step.thinking.content}")

        # Show final response
        elif isinstance(event, TaskMessageEvent):
            print(f"\n🤖 Agent Response:")
            print(f"{event.message_parts[0].text}\n")

    print("✅ Task completed!")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Quick Start: Running Your First Agent")
    print("=" * 60 + "\n")

    asyncio.run(main())

    print("\n" + "=" * 60)
    print("🎉 Success! You've created and run your first agent!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Modify the reason() method to add your own logic")
    print("2. Call LLM tools: await engine.call_llm(prompt='...')")
    print("3. Call other tools: await engine.call_tool('tool_name', params)")
    print("4. See custom_agent_with_prompt.py for more examples")
    print("=" * 60 + "\n")
