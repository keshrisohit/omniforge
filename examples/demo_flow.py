"""Demonstration of complete agent task lifecycle flow.

This script demonstrates:
1. Agent registration in the registry
2. Task creation with initial messages
3. Task processing with event streaming
4. Sending additional messages
5. Viewing task status and results
"""

import asyncio
from datetime import datetime
from uuid import uuid4

from echo_agent import EchoAgent

from omniforge.agents.models import TextPart
from omniforge.agents.registry import AgentRegistry
from omniforge.storage.memory import InMemoryAgentRepository, InMemoryTaskRepository
from omniforge.tasks.models import Task, TaskMessage, TaskState


async def demonstrate_flow() -> None:
    """Run a complete demonstration of the agent task lifecycle."""
    print("=" * 80)
    print("OmniForge Base Agent Interface - Sample Flow Demonstration")
    print("=" * 80)
    print()

    # =========================================================================
    # Step 1: Set up infrastructure
    # =========================================================================
    print("📦 Step 1: Setting up infrastructure...")
    print("-" * 80)

    # Create repositories
    agent_repo = InMemoryAgentRepository()
    task_repo = InMemoryTaskRepository()

    # Create registry
    registry = AgentRegistry(agent_repo)

    print("✅ Created in-memory repositories")
    print("✅ Created agent registry")
    print()

    # =========================================================================
    # Step 2: Register the EchoAgent
    # =========================================================================
    print("🤖 Step 2: Registering EchoAgent...")
    print("-" * 80)

    echo_agent = EchoAgent()
    await registry.register(echo_agent)

    print(f"✅ Registered agent: {echo_agent.identity.name}")
    print(f"   ID: {echo_agent.identity.id}")
    print(f"   Description: {echo_agent.identity.description}")
    print(f"   Skills: {', '.join(skill.name for skill in echo_agent.skills)}")
    print()

    # Verify registration
    all_agents = await registry.list_all()
    print(f"📋 Total agents in registry: {len(all_agents)}")
    print()

    # =========================================================================
    # Step 3: Create a task with initial message
    # =========================================================================
    print("📝 Step 3: Creating a task with initial message...")
    print("-" * 80)

    initial_message = "Hello, Echo Agent! Can you hear me?"

    # Create task manually (simulating API route behavior)
    task_id = str(uuid4())
    now = datetime.utcnow()

    user_message = TaskMessage(
        id=str(uuid4()),
        role="user",
        parts=[TextPart(text=initial_message)],
        created_at=now,
    )

    task = Task(
        id=task_id,
        agent_id=echo_agent.identity.id,
        state=TaskState.SUBMITTED,
        messages=[user_message],
        artifacts=[],
        created_at=now,
        updated_at=now,
        tenant_id="demo-tenant",
        user_id="demo-user",
    )

    # Save task to repository
    await task_repo.save(task)

    print("📤 Created task:")
    print(f"   Task ID: {task_id}")
    print(f"   Initial message: '{initial_message}'")
    print()

    print("🔄 Processing task and streaming events...")
    print("-" * 80)

    event_count = 0
    async for event in echo_agent.process_task(task):
        event_count += 1
        print(f"Event {event_count}: {event.type}")

        if event.type == "status":
            print(f"   State: {event.state}")
            if event.message:
                print(f"   Message: {event.message}")

        elif event.type == "message":
            for part in event.message_parts:
                if part.type == "text":
                    print(f"   Agent says: {part.text}")

        elif event.type == "done":
            print(f"   Final state: {event.final_state}")

        print()

    # =========================================================================
    # Step 4: Retrieve task details
    # =========================================================================
    print("🔍 Step 4: Retrieving task details...")
    print("-" * 80)

    # Get the task we just created
    retrieved_task = await task_repo.get(task_id)
    print(f"✅ Task ID: {retrieved_task.id}")
    print(f"   State: {retrieved_task.state}")
    print(f"   Agent ID: {retrieved_task.agent_id}")
    print(f"   Created: {retrieved_task.created_at}")
    print(f"   Messages in task: {len(retrieved_task.messages)}")
    print()

    # =========================================================================
    # Step 5: Send an additional message to the task
    # =========================================================================
    print("💬 Step 5: Sending additional message to task...")
    print("-" * 80)

    follow_up_message = "Thanks! This is my follow-up message."

    # Add another message to the task
    new_user_message = TaskMessage(
        id=str(uuid4()),
        role="user",
        parts=[TextPart(text=follow_up_message)],
        created_at=datetime.utcnow(),
    )

    # Retrieve task, add message, and save
    task_to_update = await task_repo.get(task_id)
    task_to_update.messages.append(new_user_message)
    task_to_update.state = TaskState.WORKING
    task_to_update.updated_at = datetime.utcnow()
    await task_repo.update(task_to_update)

    print("📤 Sending follow-up message:")
    print(f"   Message: '{follow_up_message}'")
    print()

    print("🔄 Processing message and streaming events...")
    print("-" * 80)

    event_count = 0
    async for event in echo_agent.process_task(task_to_update):
        event_count += 1
        print(f"Event {event_count}: {event.type}")

        if event.type == "status":
            print(f"   State: {event.state}")
            if event.message:
                print(f"   Message: {event.message}")

        elif event.type == "message":
            for part in event.message_parts:
                if part.type == "text":
                    print(f"   Agent says: {part.text}")

        elif event.type == "done":
            print(f"   Final state: {event.final_state}")

        print()

    # =========================================================================
    # Step 6: Retrieve final task state
    # =========================================================================
    print("📊 Step 6: Retrieving final task state...")
    print("-" * 80)

    final_task = await task_repo.get(task_id)
    print(f"✅ Final Task State: {final_task.state}")
    print(f"   Total messages: {len(final_task.messages)}")
    print(f"   Last updated: {final_task.updated_at}")
    print()

    print("📜 Message history:")
    for i, msg in enumerate(final_task.messages, 1):
        role = msg.role
        text = next((p.text for p in msg.parts if p.type == "text"), "")
        print(f"   {i}. [{role.upper()}] {text}")
    print()

    # =========================================================================
    # Summary
    # =========================================================================
    print("=" * 80)
    print("✅ Demonstration Complete!")
    print("=" * 80)
    print()
    print("Summary:")
    print(f"  • Registered {len(all_agents)} agent(s)")
    print("  • Created 1 task")
    print("  • Sent 2 messages (initial + follow-up)")
    print(f"  • Received {event_count} streaming events from the agent")
    print(f"  • Final task state: {final_task.state}")
    print()


if __name__ == "__main__":
    asyncio.run(demonstrate_flow())
