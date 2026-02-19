"""Phase 2 Demo: Public Skill Library & Discovery

Demonstrates skill discovery, search, and usage tracking.

Usage:
    python examples/phase2_demo_public_skills.py
"""

import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from omniforge.builder.models.public_skill import PublicSkill, PublicSkillStatus
from omniforge.builder.models.orm import Base
from omniforge.builder.repository import PublicSkillRepository
from omniforge.builder.discovery.service import SkillDiscoveryService


async def setup_demo_database():
    """Create in-memory database with sample public skills."""

    # Create async engine
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text("PRAGMA foreign_keys=ON"))

    # Create session maker
    async_session_maker = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    return async_session_maker


async def populate_sample_skills(repo: PublicSkillRepository):
    """Populate database with sample public skills."""

    skills = [
        PublicSkill(
            name="notion-fetch-pages",
            version="1.0.0",
            description="Fetch pages from Notion database with filtering and sorting",
            content="""---
name: notion-fetch-pages
description: Fetch pages from Notion database
allowed-tools:
  - ExternalAPI
  - Read
  - Write
model: claude-sonnet-4-5
---

# Notion Fetch Pages

Fetches pages from a Notion database with configurable filters.

## Prerequisites
- Notion API credentials configured
- Target database accessible

## Instructions
1. Connect to Notion API
2. Query database with filters
3. Extract page properties
4. Return formatted results
""",
            author="community",
            integration_type="notion",
            tags=["notion", "fetch", "database", "read"],
            status=PublicSkillStatus.APPROVED,
            usage_count=150,
            rating_avg=4.5,
            rating_count=20
        ),
        PublicSkill(
            name="notion-create-page",
            version="2.0.0",
            description="Create new pages in Notion database with rich content",
            content="# Notion Create Page\n...",
            author="community",
            integration_type="notion",
            tags=["notion", "create", "database", "write"],
            status=PublicSkillStatus.APPROVED,
            usage_count=85,
            rating_avg=4.3,
            rating_count=12
        ),
        PublicSkill(
            name="slack-post-message",
            version="2.1.0",
            description="Post formatted messages to Slack channels with attachments and mentions",
            content="# Slack Post Message\n...",
            author="community",
            integration_type="slack",
            tags=["slack", "post", "message", "notification"],
            status=PublicSkillStatus.APPROVED,
            usage_count=300,
            rating_avg=4.8,
            rating_count=50
        ),
        PublicSkill(
            name="slack-get-conversations",
            version="1.5.0",
            description="Retrieve conversation history from Slack channels",
            content="# Slack Get Conversations\n...",
            author="community",
            integration_type="slack",
            tags=["slack", "fetch", "conversation", "history"],
            status=PublicSkillStatus.APPROVED,
            usage_count=120,
            rating_avg=4.2,
            rating_count=25
        ),
        PublicSkill(
            name="github-create-issue",
            version="1.0.0",
            description="Create issues in GitHub repositories with labels and assignees",
            content="# GitHub Create Issue\n...",
            author="community",
            integration_type="github",
            tags=["github", "issue", "create", "tracking"],
            status=PublicSkillStatus.APPROVED,
            usage_count=200,
            rating_avg=4.6,
            rating_count=35
        ),
        PublicSkill(
            name="data-transform",
            version="3.0.0",
            description="Transform data between different formats (JSON, CSV, XML)",
            content="# Data Transform\n...",
            author="community",
            integration_type="general",
            tags=["transform", "data", "format", "utility"],
            status=PublicSkillStatus.APPROVED,
            usage_count=180,
            rating_avg=4.4,
            rating_count=30
        ),
    ]

    for skill in skills:
        await repo.create(skill)


async def demo_skill_search():
    """Demonstrate skill search and filtering."""

    print("=" * 70)
    print("PHASE 2 DEMO: Public Skill Search")
    print("=" * 70)
    print()

    async_session_maker = await setup_demo_database()

    async with async_session_maker() as session:
        repo = PublicSkillRepository(session)
        await populate_sample_skills(repo)
        await session.commit()

        # Search by keyword
        print("1. Search by keyword: 'notion'")
        print("-" * 70)
        results = await repo.search(keyword="notion", limit=5)
        for skill in results:
            print(f"  {skill.name} v{skill.version}")
            print(f"    {skill.description}")
            print(f"    Usage: {skill.usage_count} | Rating: {skill.rating_avg}/5.0")
            print()

        # Search by tags
        print("2. Search by tags: 'slack', 'post'")
        print("-" * 70)
        results = await repo.search(tags=["slack", "post"], limit=5)
        for skill in results:
            print(f"  {skill.name} v{skill.version}")
            print(f"    Tags: {', '.join(skill.tags)}")
            print(f"    Usage: {skill.usage_count} times")
            print()

        # Get by integration
        print("3. Get all Slack skills")
        print("-" * 70)
        slack_skills = await repo.get_by_integration("slack")
        for skill in slack_skills:
            print(f"  {skill.name} v{skill.version}")
            print(f"    {skill.description}")
            print()

        # Get top skills
        print("4. Top 3 most popular skills")
        print("-" * 70)
        top_skills = await repo.get_top_skills(limit=3)
        for i, skill in enumerate(top_skills, 1):
            print(f"  #{i} {skill.name} v{skill.version}")
            print(f"      Usage: {skill.usage_count} | Rating: {skill.rating_avg}/5.0")
            print()


async def demo_skill_discovery():
    """Demonstrate intelligent skill discovery."""

    print("=" * 70)
    print("PHASE 2 DEMO: Skill Discovery")
    print("=" * 70)
    print()

    async_session_maker = await setup_demo_database()

    async with async_session_maker() as session:
        repo = PublicSkillRepository(session)
        await populate_sample_skills(repo)
        await session.commit()

        discovery = SkillDiscoveryService(repo)

        # Discover skills based on context
        contexts = [
            "I need to fetch data from Notion and post it to Slack",
            "Create GitHub issues from Notion database entries",
            "Transform data and send notifications",
        ]

        for i, context in enumerate(contexts, 1):
            print(f"{i}. Context: \"{context}\"")
            print("-" * 70)

            recommendations = await discovery.discover_by_context(
                description=context,
                integration_filter=None,
                limit=3
            )

            if recommendations:
                for rec in recommendations:
                    print(f"  ✨ {rec.skill.name} v{rec.skill.version}")
                    print(f"     Relevance: {rec.relevance_score:.2f}")
                    print(f"     Reason: {rec.reason}")
                    print(f"     Integration: {rec.skill.integration_type}")
                    print()
            else:
                print("  No recommendations found")
                print()

            print()


async def demo_usage_tracking():
    """Demonstrate skill usage tracking."""

    print("=" * 70)
    print("PHASE 2 DEMO: Usage Tracking")
    print("=" * 70)
    print()

    async_session_maker = await setup_demo_database()

    async with async_session_maker() as session:
        repo = PublicSkillRepository(session)
        await populate_sample_skills(repo)
        await session.commit()

        skill_name = "notion-fetch-pages"
        version = "1.0.0"

        # Get initial usage count
        skill = await repo.get_by_name(skill_name, version)
        initial_count = skill.usage_count
        print(f"Initial usage count for {skill_name} v{version}: {initial_count}")
        print()

        # Simulate usage
        print("Simulating skill usage (5 times)...")
        for i in range(5):
            await repo.increment_usage_count(skill_name, version)
            await session.commit()
            print(f"  Usage #{i+1} recorded")

        print()

        # Get updated usage count
        updated_skill = await repo.get_by_name(skill_name, version)
        final_count = updated_skill.usage_count
        print(f"Final usage count: {final_count}")
        print(f"Increase: +{final_count - initial_count}")
        print()


async def demo_popular_skills():
    """Demonstrate popular skill ranking."""

    print("=" * 70)
    print("PHASE 2 DEMO: Popular Skills Ranking")
    print("=" * 70)
    print()

    async_session_maker = await setup_demo_database()

    async with async_session_maker() as session:
        repo = PublicSkillRepository(session)
        await populate_sample_skills(repo)
        await session.commit()

        discovery = SkillDiscoveryService(repo)

        print("Top 5 Most Popular Skills:")
        print("-" * 70)

        popular = await discovery.get_popular_skills(limit=5)

        for i, skill in enumerate(popular, 1):
            bar_length = int(skill.usage_count / 10)
            bar = "█" * bar_length
            print(f"  {i}. {skill.name} v{skill.version}")
            print(f"     {bar} {skill.usage_count} uses")
            print(f"     ⭐ {skill.rating_avg}/5.0 ({skill.rating_count} ratings)")
            print()


if __name__ == "__main__":
    print()
    asyncio.run(demo_skill_search())
    print()
    asyncio.run(demo_skill_discovery())
    print()
    asyncio.run(demo_usage_tracking())
    print()
    asyncio.run(demo_popular_skills())

    print("=" * 70)
    print("Public Skill Library Demo Complete!")
    print()
    print("Key Features Demonstrated:")
    print("  ✓ Skill search by keyword and tags")
    print("  ✓ Intelligent skill discovery with relevance scoring")
    print("  ✓ Usage tracking and popularity ranking")
    print("  ✓ Integration-based filtering")
    print("  ✓ Multi-factor relevance algorithm")
    print("=" * 70)
    print()
