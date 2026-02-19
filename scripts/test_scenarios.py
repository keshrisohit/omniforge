"""Common test scenarios and utilities for testing agent flows.

This module provides pre-built test scenarios that can be used across
different tests to ensure consistency and reduce boilerplate.
"""

import asyncio
from datetime import datetime
from typing import Optional
from uuid import uuid4

from omniforge.agents.base import BaseAgent
from omniforge.agents.models import TextPart
from omniforge.agents.registry import AgentRegistry
from omniforge.storage.memory import InMemoryAgentRepository, InMemoryTaskRepository
from omniforge.tasks.models import Task, TaskMessage, TaskState


async def create_test_task(
    agent_id: str,
    message: str,
    tenant_id: str = "test-tenant",
    user_id: str = "test-user",
    parent_task_id: Optional[str] = None,
) -> Task:
    """Create a test task with a simple text message.

    Args:
        agent_id: ID of the agent to handle the task
        message: Initial message content
        tenant_id: Tenant identifier (default: "test-tenant")
        user_id: User identifier (default: "test-user")
        parent_task_id: Optional parent task ID for subtasks

    Returns:
        Task object ready for processing
    """
    task_id = str(uuid4())
    now = datetime.utcnow()

    user_message = TaskMessage(
        id=str(uuid4()),
        role="user",
        parts=[TextPart(text=message)],
        created_at=now,
    )

    return Task(
        id=task_id,
        agent_id=agent_id,
        state=TaskState.SUBMITTED,
        messages=[user_message],
        artifacts=[],
        created_at=now,
        updated_at=now,
        tenant_id=tenant_id,
        user_id=user_id,
        parent_task_id=parent_task_id,
    )


async def setup_test_environment() -> tuple[AgentRegistry, InMemoryTaskRepository]:
    """Set up a clean test environment with empty repositories.

    Returns:
        Tuple of (AgentRegistry, InMemoryTaskRepository)
    """
    agent_repo = InMemoryAgentRepository()
    task_repo = InMemoryTaskRepository()
    registry = AgentRegistry(agent_repo)

    return registry, task_repo


async def process_task_and_collect_events(agent: BaseAgent, task: Task) -> tuple[list, TaskState]:
    """Process a task and collect all events.

    Args:
        agent: Agent to process the task
        task: Task to process

    Returns:
        Tuple of (list of events, final task state)
    """
    events = []
    final_state = TaskState.SUBMITTED

    async for event in agent.process_task(task):
        events.append(event)
        if event.type == "done":
            final_state = event.final_state

    return events, final_state


# Common test scenarios


async def scenario_simple_task_completion(
    registry: AgentRegistry,
    task_repo: InMemoryTaskRepository,
    agent_id: str,
    message: str = "Hello, agent!",
) -> tuple[Task, list]:
    """Scenario: Create and complete a simple task.

    Args:
        registry: Agent registry with registered agents
        task_repo: Task repository for persistence
        agent_id: ID of the agent to use
        message: Message to send (default: "Hello, agent!")

    Returns:
        Tuple of (completed task, list of events)
    """
    # Get agent
    agent = await registry.get(agent_id)

    # Create task
    task = await create_test_task(agent_id, message)
    await task_repo.save(task)

    # Process task
    events, final_state = await process_task_and_collect_events(agent, task)

    # Update task state
    task.state = final_state
    task.updated_at = datetime.utcnow()
    await task_repo.update(task)

    return task, events


async def scenario_multi_turn_conversation(
    registry: AgentRegistry,
    task_repo: InMemoryTaskRepository,
    agent_id: str,
    messages: list[str],
) -> tuple[Task, list]:
    """Scenario: Multi-turn conversation with an agent.

    Args:
        registry: Agent registry with registered agents
        task_repo: Task repository for persistence
        agent_id: ID of the agent to use
        messages: List of messages to send in sequence

    Returns:
        Tuple of (final task state, all events from all turns)
    """
    agent = await registry.get(agent_id)

    # Create initial task
    task = await create_test_task(agent_id, messages[0])
    await task_repo.save(task)

    all_events = []

    # Process initial message
    events, final_state = await process_task_and_collect_events(agent, task)
    all_events.extend(events)

    # Update task
    task.state = final_state
    task.updated_at = datetime.utcnow()
    await task_repo.update(task)

    # Send follow-up messages
    for message in messages[1:]:
        # Add message to task
        new_message = TaskMessage(
            id=str(uuid4()),
            role="user",
            parts=[TextPart(text=message)],
            created_at=datetime.utcnow(),
        )
        task.messages.append(new_message)
        task.state = TaskState.WORKING
        task.updated_at = datetime.utcnow()
        await task_repo.update(task)

        # Process task again
        events, final_state = await process_task_and_collect_events(agent, task)
        all_events.extend(events)

        # Update task
        task.state = final_state
        task.updated_at = datetime.utcnow()
        await task_repo.update(task)

    return task, all_events


async def scenario_agent_discovery_by_skill(
    registry: AgentRegistry, skill_id: str
) -> list[BaseAgent]:
    """Scenario: Discover agents that provide a specific skill.

    Args:
        registry: Agent registry with registered agents
        skill_id: Skill ID to search for

    Returns:
        List of agents that provide the skill
    """
    return await registry.find_by_skill(skill_id)


async def scenario_agent_discovery_by_tag(registry: AgentRegistry, tag: str) -> list[BaseAgent]:
    """Scenario: Discover agents by tag.

    Args:
        registry: Agent registry with registered agents
        tag: Tag to search for

    Returns:
        List of agents with skills tagged with the specified tag
    """
    return await registry.find_by_tag(tag)


async def scenario_multi_tenant_isolation(
    agent_repo: InMemoryAgentRepository,
) -> tuple[list[BaseAgent], list[BaseAgent]]:
    """Scenario: Test multi-tenant isolation.

    Args:
        agent_repo: Agent repository

    Returns:
        Tuple of (tenant1 agents, tenant2 agents)
    """
    # Create registries for different tenants
    tenant1_registry = AgentRegistry(agent_repo, tenant_id="tenant-1")
    tenant2_registry = AgentRegistry(agent_repo, tenant_id="tenant-2")

    # This scenario assumes agents have been registered with tenant_id
    # In practice, you'd need to modify BaseAgent to accept tenant_id

    tenant1_agents = await tenant1_registry.list_all()
    tenant2_agents = await tenant2_registry.list_all()

    return tenant1_agents, tenant2_agents


async def demo_all_scenarios() -> None:
    """Demonstrate all test scenarios."""
    from scripts.seed_data import seed_agents

    print("=" * 80)
    print("OmniForge - Test Scenarios Demo")
    print("=" * 80)
    print()

    # Seed data
    registry, task_repo = await seed_agents()

    print()
    print("🧪 Running Test Scenarios...")
    print("=" * 80)

    # Scenario 1: Simple task completion
    print()
    print("Scenario 1: Simple Task Completion")
    print("-" * 80)
    task, events = await scenario_simple_task_completion(
        registry, task_repo, "data-analysis-agent", "Analyze my sales data"
    )
    print(f"✅ Task completed with {len(events)} events")
    print(f"   Final state: {task.state}")

    # Scenario 2: Multi-turn conversation
    print()
    print("Scenario 2: Multi-turn Conversation")
    print("-" * 80)
    task, events = await scenario_multi_turn_conversation(
        registry,
        task_repo,
        "code-generation-agent",
        [
            "Write a Python function to calculate fibonacci numbers",
            "Can you add error handling?",
            "Now add type hints",
        ],
    )
    print(f"✅ Conversation completed with {len(task.messages)} messages")
    print(f"   Total events: {len(events)}")
    print(f"   Final state: {task.state}")

    # Scenario 3: Agent discovery by skill
    print()
    print("Scenario 3: Agent Discovery by Skill")
    print("-" * 80)
    agents = await scenario_agent_discovery_by_skill(registry, "data-analysis")
    print(f"✅ Found {len(agents)} agent(s) with 'data-analysis' skill:")
    for agent in agents:
        print(f"   • {agent.identity.name}")

    # Scenario 4: Agent discovery by tag
    print()
    print("Scenario 4: Agent Discovery by Tag")
    print("-" * 80)
    agents = await scenario_agent_discovery_by_tag(registry, "coding")
    print(f"✅ Found {len(agents)} agent(s) with 'coding' tag:")
    for agent in agents:
        print(f"   • {agent.identity.name}")

    print()
    print("=" * 80)
    print("✅ All scenarios completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(demo_all_scenarios())
