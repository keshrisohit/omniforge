"""Seed script to populate in-memory storage with sample agents for testing.

This script creates various sample agents with different capabilities and skills
to test different scenarios in the OmniForge platform.

Usage:
    python -m scripts.seed_data
"""

import asyncio
from datetime import datetime
from typing import AsyncIterator

from omniforge.agents.base import BaseAgent
from omniforge.agents.events import (
    TaskDoneEvent,
    TaskEvent,
    TaskMessageEvent,
    TaskStatusEvent,
)
from omniforge.agents.models import (
    AgentCapabilities,
    AgentIdentity,
    AgentSkill,
    SkillInputMode,
    SkillOutputMode,
    TextPart,
)
from omniforge.agents.registry import AgentRegistry
from omniforge.storage.memory import InMemoryAgentRepository, InMemoryTaskRepository
from omniforge.tasks.models import Task, TaskState


class DataAnalysisAgent(BaseAgent):
    """Agent specialized in data analysis and visualization tasks."""

    identity = AgentIdentity(
        id="data-analysis-agent",
        name="Data Analysis Agent",
        description="Analyzes datasets and generates insights with visualizations",
        version="1.0.0",
    )

    capabilities = AgentCapabilities(
        streaming=True,
        multi_turn=True,
        hitl_support=True,
    )

    skills = [
        AgentSkill(
            id="data-analysis",
            name="Data Analysis",
            description="Analyze structured datasets and generate statistical insights",
            input_modes=[SkillInputMode.FILE, SkillInputMode.STRUCTURED],
            output_modes=[SkillOutputMode.TEXT, SkillOutputMode.ARTIFACT],
            tags=["data", "analytics", "statistics"],
            examples=["Analyze sales data for Q4", "Find correlations in customer data"],
        ),
        AgentSkill(
            id="data-visualization",
            name="Data Visualization",
            description="Create charts and visualizations from data",
            input_modes=[SkillInputMode.STRUCTURED],
            output_modes=[SkillOutputMode.ARTIFACT],
            tags=["data", "visualization", "charts"],
            examples=["Create a bar chart of monthly revenue", "Visualize trend over time"],
        ),
    ]

    async def process_task(self, task: Task) -> AsyncIterator[TaskEvent]:
        """Process data analysis tasks."""
        yield TaskStatusEvent(
            task_id=task.id,
            timestamp=datetime.utcnow(),
            state=TaskState.WORKING,
            message="Analyzing your data...",
        )

        yield TaskMessageEvent(
            task_id=task.id,
            timestamp=datetime.utcnow(),
            message_parts=[
                TextPart(text="Data analysis complete! Found 3 key insights in your dataset.")
            ],
            is_partial=False,
        )

        yield TaskDoneEvent(
            task_id=task.id,
            timestamp=datetime.utcnow(),
            final_state=TaskState.COMPLETED,
        )


class CodeGenerationAgent(BaseAgent):
    """Agent specialized in code generation and software development tasks."""

    identity = AgentIdentity(
        id="code-generation-agent",
        name="Code Generation Agent",
        description="Generates code snippets and complete functions based on requirements",
        version="1.0.0",
    )

    capabilities = AgentCapabilities(
        streaming=True,
        multi_turn=True,
    )

    skills = [
        AgentSkill(
            id="code-generation",
            name="Code Generation",
            description="Generate code in multiple programming languages",
            input_modes=[SkillInputMode.TEXT],
            output_modes=[SkillOutputMode.TEXT, SkillOutputMode.ARTIFACT],
            tags=["coding", "development", "programming"],
            examples=[
                "Write a Python function to sort a list",
                "Create a React component for a login form",
            ],
        ),
        AgentSkill(
            id="code-review",
            name="Code Review",
            description="Review code for bugs, security issues, and best practices",
            input_modes=[SkillInputMode.TEXT, SkillInputMode.FILE],
            output_modes=[SkillOutputMode.TEXT],
            tags=["coding", "review", "quality"],
            examples=["Review this function for bugs", "Check for security vulnerabilities"],
        ),
    ]

    async def process_task(self, task: Task) -> AsyncIterator[TaskEvent]:
        """Process code generation tasks."""
        yield TaskStatusEvent(
            task_id=task.id,
            timestamp=datetime.utcnow(),
            state=TaskState.WORKING,
            message="Generating code...",
        )

        yield TaskMessageEvent(
            task_id=task.id,
            timestamp=datetime.utcnow(),
            message_parts=[TextPart(text="Here's the generated code based on your requirements.")],
            is_partial=False,
        )

        yield TaskDoneEvent(
            task_id=task.id,
            timestamp=datetime.utcnow(),
            final_state=TaskState.COMPLETED,
        )


class ContentWritingAgent(BaseAgent):
    """Agent specialized in content creation and writing tasks."""

    identity = AgentIdentity(
        id="content-writing-agent",
        name="Content Writing Agent",
        description="Creates blog posts, articles, and marketing content",
        version="1.0.0",
    )

    capabilities = AgentCapabilities(
        streaming=True,
        multi_turn=True,
    )

    skills = [
        AgentSkill(
            id="blog-writing",
            name="Blog Writing",
            description="Write engaging blog posts on various topics",
            input_modes=[SkillInputMode.TEXT],
            output_modes=[SkillOutputMode.TEXT, SkillOutputMode.ARTIFACT],
            tags=["writing", "content", "blog"],
            examples=["Write a blog post about AI trends", "Create an article on productivity"],
        ),
        AgentSkill(
            id="copywriting",
            name="Marketing Copywriting",
            description="Create compelling marketing copy and ad text",
            input_modes=[SkillInputMode.TEXT],
            output_modes=[SkillOutputMode.TEXT],
            tags=["writing", "marketing", "advertising"],
            examples=["Write ad copy for a product", "Create email marketing content"],
        ),
    ]

    async def process_task(self, task: Task) -> AsyncIterator[TaskEvent]:
        """Process content writing tasks."""
        yield TaskStatusEvent(
            task_id=task.id,
            timestamp=datetime.utcnow(),
            state=TaskState.WORKING,
            message="Writing content...",
        )

        yield TaskMessageEvent(
            task_id=task.id,
            timestamp=datetime.utcnow(),
            message_parts=[
                TextPart(text="Here's your content draft. Let me know if you'd like any changes!")
            ],
            is_partial=False,
        )

        yield TaskDoneEvent(
            task_id=task.id,
            timestamp=datetime.utcnow(),
            final_state=TaskState.COMPLETED,
        )


class ResearchAgent(BaseAgent):
    """Agent specialized in research and information gathering."""

    identity = AgentIdentity(
        id="research-agent",
        name="Research Agent",
        description="Conducts research and gathers information on various topics",
        version="1.0.0",
    )

    capabilities = AgentCapabilities(
        streaming=True,
        multi_turn=True,
        hitl_support=True,
    )

    skills = [
        AgentSkill(
            id="web-research",
            name="Web Research",
            description="Search and gather information from online sources",
            input_modes=[SkillInputMode.TEXT],
            output_modes=[SkillOutputMode.TEXT, SkillOutputMode.ARTIFACT],
            tags=["research", "information", "web"],
            examples=[
                "Research the history of AI",
                "Find information about renewable energy trends",
            ],
        ),
        AgentSkill(
            id="fact-checking",
            name="Fact Checking",
            description="Verify claims and check facts against reliable sources",
            input_modes=[SkillInputMode.TEXT],
            output_modes=[SkillOutputMode.TEXT],
            tags=["research", "verification", "facts"],
            examples=[
                "Verify this claim about climate change",
                "Check if this statistic is accurate",
            ],
        ),
    ]

    async def process_task(self, task: Task) -> AsyncIterator[TaskEvent]:
        """Process research tasks."""
        yield TaskStatusEvent(
            task_id=task.id,
            timestamp=datetime.utcnow(),
            state=TaskState.WORKING,
            message="Researching your topic...",
        )

        yield TaskMessageEvent(
            task_id=task.id,
            timestamp=datetime.utcnow(),
            message_parts=[
                TextPart(text="Research complete! I've gathered information from multiple sources.")
            ],
            is_partial=False,
        )

        yield TaskDoneEvent(
            task_id=task.id,
            timestamp=datetime.utcnow(),
            final_state=TaskState.COMPLETED,
        )


class CustomerSupportAgent(BaseAgent):
    """Agent specialized in customer support and help desk tasks."""

    identity = AgentIdentity(
        id="customer-support-agent",
        name="Customer Support Agent",
        description="Provides customer support and answers common questions",
        version="1.0.0",
    )

    capabilities = AgentCapabilities(
        streaming=True,
        multi_turn=True,
        hitl_support=True,
        push_notifications=True,
    )

    skills = [
        AgentSkill(
            id="customer-inquiry",
            name="Customer Inquiry Handling",
            description="Answer customer questions and resolve issues",
            input_modes=[SkillInputMode.TEXT],
            output_modes=[SkillOutputMode.TEXT],
            tags=["support", "customer-service", "help"],
            examples=["How do I reset my password?", "Track my order status"],
        ),
        AgentSkill(
            id="ticket-management",
            name="Ticket Management",
            description="Create and manage support tickets",
            input_modes=[SkillInputMode.TEXT, SkillInputMode.STRUCTURED],
            output_modes=[SkillOutputMode.TEXT, SkillOutputMode.STRUCTURED],
            tags=["support", "tickets", "management"],
            examples=["Create a support ticket", "Update ticket status"],
        ),
    ]

    async def process_task(self, task: Task) -> AsyncIterator[TaskEvent]:
        """Process customer support tasks."""
        yield TaskStatusEvent(
            task_id=task.id,
            timestamp=datetime.utcnow(),
            state=TaskState.WORKING,
            message="Looking up your issue...",
        )

        yield TaskMessageEvent(
            task_id=task.id,
            timestamp=datetime.utcnow(),
            message_parts=[
                TextPart(
                    text="I understand your concern. Let me help you resolve this issue right away."
                )
            ],
            is_partial=False,
        )

        yield TaskDoneEvent(
            task_id=task.id,
            timestamp=datetime.utcnow(),
            final_state=TaskState.COMPLETED,
        )


async def seed_agents() -> tuple[AgentRegistry, InMemoryTaskRepository]:
    """Seed the in-memory repositories with sample agents.

    Returns:
        Tuple of (AgentRegistry, InMemoryTaskRepository) with seeded data
    """
    print("=" * 80)
    print("OmniForge - Seeding Sample Agents")
    print("=" * 80)
    print()

    # Create repositories
    agent_repo = InMemoryAgentRepository()
    task_repo = InMemoryTaskRepository()

    # Create registry
    registry = AgentRegistry(agent_repo)

    # List of sample agents to seed
    sample_agents = [
        DataAnalysisAgent(),
        CodeGenerationAgent(),
        ContentWritingAgent(),
        ResearchAgent(),
        CustomerSupportAgent(),
    ]

    print("📦 Seeding agents into registry...")
    print("-" * 80)

    for agent in sample_agents:
        await registry.register(agent)
        print(f"✅ Registered: {agent.identity.name}")
        print(f"   ID: {agent.identity.id}")
        print(f"   Skills: {len(agent.skills)}")
        print("   Capabilities: ", end="")
        caps = []
        if agent.capabilities.streaming:
            caps.append("streaming")
        if agent.capabilities.multi_turn:
            caps.append("multi-turn")
        if agent.capabilities.hitl_support:
            caps.append("HITL")
        if agent.capabilities.push_notifications:
            caps.append("push-notifications")
        print(", ".join(caps) if caps else "none")
        print()

    # List all agents
    all_agents = await registry.list_all()
    print("=" * 80)
    print(f"✅ Successfully seeded {len(all_agents)} agents!")
    print("=" * 80)
    print()

    # Show summary by skill tags
    print("📊 Agents by Category:")
    print("-" * 80)

    tag_categories = {}
    for agent in all_agents:
        for skill in agent.skills:
            if skill.tags:
                for tag in skill.tags:
                    if tag not in tag_categories:
                        tag_categories[tag] = []
                    if agent.identity.name not in tag_categories[tag]:
                        tag_categories[tag].append(agent.identity.name)

    for tag, agent_names in sorted(tag_categories.items()):
        print(f"  {tag}: {len(agent_names)} agent(s) - {', '.join(agent_names)}")

    print()
    print("=" * 80)
    print("Seed complete! Use these repositories in your tests:")
    print("  • agent_registry: AgentRegistry")
    print("  • task_repository: InMemoryTaskRepository")
    print("=" * 80)
    print()

    return registry, task_repo


async def main() -> None:
    """Main entry point for the seed script."""
    registry, task_repo = await seed_agents()

    # Demonstrate finding agents by skill
    print()
    print("🔍 Example: Finding agents by skill...")
    print("-" * 80)

    # Find agents with data analysis skill
    data_agents = await registry.find_by_skill("data-analysis")
    print(f"Agents with 'data-analysis' skill: {len(data_agents)}")
    for agent in data_agents:
        print(f"  • {agent.identity.name}")

    print()

    # Find agents by tag
    coding_agents = await registry.find_by_tag("coding")
    print(f"Agents with 'coding' tag: {len(coding_agents)}")
    for agent in coding_agents:
        print(f"  • {agent.identity.name}")

    print()


if __name__ == "__main__":
    asyncio.run(main())
