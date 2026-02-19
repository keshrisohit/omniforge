"""Tests for SkillDiscoveryService."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from omniforge.builder.discovery import SkillDiscoveryService
from omniforge.builder.models import PublicSkill, PublicSkillStatus
from omniforge.builder.models.orm import Base
from omniforge.builder.repository import PublicSkillRepository


@pytest.fixture
async def engine():
    """Create test database engine."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def session(engine):
    """Create test database session."""
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session


@pytest.fixture
async def populated_repo(session: AsyncSession) -> PublicSkillRepository:
    """Create repository with test data."""
    repo = PublicSkillRepository(session)

    # Create diverse skills for testing
    skills = [
        PublicSkill(
            id="notion-weekly-report",
            name="notion-weekly-report",
            version="1.0.0",
            description="Generates weekly summary reports from Notion databases",
            content="Weekly report skill content",
            author_id="user-1",
            tags=["reporting", "notion", "weekly", "analytics"],
            integrations=["notion"],
            usage_count=150,
            rating_avg=4.8,
            status=PublicSkillStatus.APPROVED,
        ),
        PublicSkill(
            id="slack-notifier",
            name="slack-notifier",
            version="1.0.0",
            description="Sends automated notifications to Slack channels",
            content="Slack notification skill content",
            author_id="user-2",
            tags=["notifications", "slack", "alerts"],
            integrations=["slack"],
            usage_count=200,
            rating_avg=4.5,
            status=PublicSkillStatus.APPROVED,
        ),
        PublicSkill(
            id="notion-task-creator",
            name="notion-task-creator",
            version="1.0.0",
            description="Creates tasks in Notion databases automatically",
            content="Task creator skill content",
            author_id="user-3",
            tags=["tasks", "notion", "automation"],
            integrations=["notion"],
            usage_count=80,
            rating_avg=4.2,
            status=PublicSkillStatus.APPROVED,
        ),
        PublicSkill(
            id="github-pr-analyzer",
            name="github-pr-analyzer",
            version="1.0.0",
            description="Analyzes pull requests and generates reports",
            content="PR analyzer skill content",
            author_id="user-4",
            tags=["github", "pull-requests", "analytics"],
            integrations=["github"],
            usage_count=60,
            rating_avg=4.6,
            status=PublicSkillStatus.APPROVED,
        ),
        PublicSkill(
            id="multi-integration-sync",
            name="multi-integration-sync",
            version="1.0.0",
            description="Syncs data between Notion and Slack",
            content="Sync skill content",
            author_id="user-5",
            tags=["sync", "integration", "automation"],
            integrations=["notion", "slack"],
            usage_count=120,
            rating_avg=4.7,
            status=PublicSkillStatus.APPROVED,
        ),
    ]

    for skill in skills:
        await repo.create(skill)

    return repo


class TestSkillDiscoveryService:
    """Tests for SkillDiscoveryService class."""

    async def test_discover_by_context_with_keyword(self, populated_repo: PublicSkillRepository):
        """SkillDiscoveryService should discover skills matching keywords."""
        service = SkillDiscoveryService(populated_repo)

        recommendations = await service.discover_by_context(
            description="I want to generate weekly reports from my Notion database",
            limit=5,
        )

        assert len(recommendations) > 0
        # Should find notion-weekly-report as most relevant
        assert any(r.skill.id == "notion-weekly-report" for r in recommendations)
        # All recommendations should have relevance scores
        assert all(0.0 <= r.relevance_score <= 1.0 for r in recommendations)
        # All recommendations should have reasons
        assert all(r.reason for r in recommendations)

    async def test_discover_by_context_with_integration_filter(
        self, populated_repo: PublicSkillRepository
    ):
        """SkillDiscoveryService should prioritize skills with required integrations."""
        service = SkillDiscoveryService(populated_repo)

        recommendations = await service.discover_by_context(
            description="I need to automate notifications",
            integrations=["slack"],
            limit=5,
        )

        assert len(recommendations) > 0
        # Should include slack skills
        slack_skills = [r for r in recommendations if "slack" in r.skill.integrations]
        assert len(slack_skills) > 0
        # Should prioritize slack-notifier and multi-integration-sync
        top_ids = [r.skill.id for r in recommendations[:3]]
        assert "slack-notifier" in top_ids or "multi-integration-sync" in top_ids

    async def test_discover_returns_limited_results(self, populated_repo: PublicSkillRepository):
        """SkillDiscoveryService should respect limit parameter."""
        service = SkillDiscoveryService(populated_repo)

        recommendations = await service.discover_by_context(
            description="automation task skill",
            limit=3,
        )

        assert len(recommendations) <= 3

    async def test_discover_orders_by_relevance(self, populated_repo: PublicSkillRepository):
        """SkillDiscoveryService should order results by relevance score."""
        service = SkillDiscoveryService(populated_repo)

        recommendations = await service.discover_by_context(
            description="Notion weekly reports with analytics",
            integrations=["notion"],
            limit=5,
        )

        # Check that results are ordered by relevance
        scores = [r.relevance_score for r in recommendations]
        assert scores == sorted(scores, reverse=True)

    async def test_discover_no_duplicates(self, populated_repo: PublicSkillRepository):
        """SkillDiscoveryService should not return duplicate skills."""
        service = SkillDiscoveryService(populated_repo)

        recommendations = await service.discover_by_context(
            description="notion tasks automation reports",
            integrations=["notion"],
            limit=10,
        )

        # Check no duplicate skill IDs
        skill_ids = [r.skill.id for r in recommendations]
        assert len(skill_ids) == len(set(skill_ids))

    async def test_discover_by_integration(self, populated_repo: PublicSkillRepository):
        """SkillDiscoveryService should discover skills by integration."""
        service = SkillDiscoveryService(populated_repo)

        skills = await service.discover_by_integration("notion", limit=10)

        assert len(skills) > 0
        # All skills should have notion integration
        assert all("notion" in skill.integrations for skill in skills)
        # Should be ordered by usage count
        usage_counts = [skill.usage_count for skill in skills]
        assert usage_counts == sorted(usage_counts, reverse=True)

    async def test_get_popular_skills(self, populated_repo: PublicSkillRepository):
        """SkillDiscoveryService should return popular skills."""
        service = SkillDiscoveryService(populated_repo)

        skills = await service.get_popular_skills(limit=3)

        assert len(skills) == 3
        # Should be ordered by usage count DESC
        assert skills[0].usage_count >= skills[1].usage_count
        assert skills[1].usage_count >= skills[2].usage_count
        # Top skill should be slack-notifier (200 uses)
        assert skills[0].id == "slack-notifier"

    async def test_extract_keywords(self, populated_repo: PublicSkillRepository):
        """SkillDiscoveryService should extract meaningful keywords."""
        service = SkillDiscoveryService(populated_repo)

        keywords = service._extract_keywords(
            "I want to create weekly reports from my Notion database"
        )

        # Should extract meaningful words
        assert "weekly" in keywords
        assert "reports" in keywords
        assert "notion" in keywords
        assert "database" in keywords

        # Should filter out stop words
        assert "i" not in keywords
        assert "to" not in keywords
        assert "from" not in keywords
        assert "want" not in keywords

    async def test_extract_keywords_filters_short_words(
        self, populated_repo: PublicSkillRepository
    ):
        """SkillDiscoveryService should filter out short words."""
        service = SkillDiscoveryService(populated_repo)

        keywords = service._extract_keywords("I am at my job now")

        # Short words should be filtered
        assert len(keywords) == 0  # All words are stop words or too short

    async def test_calculate_relevance_usage_score(self, populated_repo: PublicSkillRepository):
        """SkillDiscoveryService should factor usage count into relevance."""
        service = SkillDiscoveryService(populated_repo)

        high_usage_skill = PublicSkill(
            id="high-usage",
            name="high-usage",
            version="1.0.0",
            description="Test skill",
            content="content",
            author_id="user-1",
            tags=[],
            integrations=[],
            usage_count=150,
            rating_avg=3.0,
            status=PublicSkillStatus.APPROVED,
        )

        low_usage_skill = PublicSkill(
            id="low-usage",
            name="low-usage",
            version="1.0.0",
            description="Test skill",
            content="content",
            author_id="user-1",
            tags=[],
            integrations=[],
            usage_count=10,
            rating_avg=3.0,
            status=PublicSkillStatus.APPROVED,
        )

        high_score = service._calculate_relevance(high_usage_skill, "test", None)
        low_score = service._calculate_relevance(low_usage_skill, "test", None)

        assert high_score > low_score

    async def test_calculate_relevance_rating_score(self, populated_repo: PublicSkillRepository):
        """SkillDiscoveryService should factor rating into relevance."""
        service = SkillDiscoveryService(populated_repo)

        high_rated = PublicSkill(
            id="high-rated",
            name="high-rated",
            version="1.0.0",
            description="Test skill",
            content="content",
            author_id="user-1",
            tags=[],
            integrations=[],
            usage_count=50,
            rating_avg=5.0,
            status=PublicSkillStatus.APPROVED,
        )

        low_rated = PublicSkill(
            id="low-rated",
            name="low-rated",
            version="1.0.0",
            description="Test skill",
            content="content",
            author_id="user-1",
            tags=[],
            integrations=[],
            usage_count=50,
            rating_avg=2.0,
            status=PublicSkillStatus.APPROVED,
        )

        high_score = service._calculate_relevance(high_rated, "test", None)
        low_score = service._calculate_relevance(low_rated, "test", None)

        assert high_score > low_score

    async def test_calculate_relevance_integration_match(
        self, populated_repo: PublicSkillRepository
    ):
        """SkillDiscoveryService should boost relevance for integration match."""
        service = SkillDiscoveryService(populated_repo)

        matching_skill = PublicSkill(
            id="matching",
            name="matching",
            version="1.0.0",
            description="Test skill",
            content="content",
            author_id="user-1",
            tags=[],
            integrations=["notion", "slack"],
            usage_count=50,
            rating_avg=3.0,
            status=PublicSkillStatus.APPROVED,
        )

        non_matching_skill = PublicSkill(
            id="non-matching",
            name="non-matching",
            version="1.0.0",
            description="Test skill",
            content="content",
            author_id="user-1",
            tags=[],
            integrations=["github"],
            usage_count=50,
            rating_avg=3.0,
            status=PublicSkillStatus.APPROVED,
        )

        matching_score = service._calculate_relevance(
            matching_skill, "test", ["notion", "slack"]
        )
        non_matching_score = service._calculate_relevance(
            non_matching_skill, "test", ["notion", "slack"]
        )

        assert matching_score > non_matching_score

    async def test_generate_reason_with_usage(self, populated_repo: PublicSkillRepository):
        """SkillDiscoveryService should generate reason mentioning usage."""
        service = SkillDiscoveryService(populated_repo)

        high_usage_skill = PublicSkill(
            id="popular",
            name="popular",
            version="1.0.0",
            description="Test skill",
            content="content",
            author_id="user-1",
            tags=[],
            integrations=[],
            usage_count=100,
            rating_avg=3.0,
            status=PublicSkillStatus.APPROVED,
        )

        reason = service._generate_reason(high_usage_skill, None, None)

        assert "used" in reason.lower() or "popular" in reason.lower()

    async def test_generate_reason_with_rating(self, populated_repo: PublicSkillRepository):
        """SkillDiscoveryService should generate reason mentioning rating."""
        service = SkillDiscoveryService(populated_repo)

        high_rated_skill = PublicSkill(
            id="highly-rated",
            name="highly-rated",
            version="1.0.0",
            description="Test skill",
            content="content",
            author_id="user-1",
            tags=[],
            integrations=[],
            usage_count=10,
            rating_avg=4.8,
            status=PublicSkillStatus.APPROVED,
        )

        reason = service._generate_reason(high_rated_skill, None, None)

        assert "rated" in reason.lower()
        assert "4.8" in reason

    async def test_generate_reason_with_integration_match(
        self, populated_repo: PublicSkillRepository
    ):
        """SkillDiscoveryService should generate reason mentioning integrations."""
        service = SkillDiscoveryService(populated_repo)

        skill = PublicSkill(
            id="multi-int",
            name="multi-int",
            version="1.0.0",
            description="Test skill",
            content="content",
            author_id="user-1",
            tags=[],
            integrations=["notion", "slack"],
            usage_count=10,
            rating_avg=3.0,
            status=PublicSkillStatus.APPROVED,
        )

        reason = service._generate_reason(skill, None, ["notion", "slack"])

        assert "notion" in reason.lower()
        assert "slack" in reason.lower()
