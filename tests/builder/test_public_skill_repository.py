"""Tests for PublicSkillRepository."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from omniforge.builder.models import PublicSkill, PublicSkillStatus
from omniforge.builder.models.orm import Base, PublicSkillModel
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
def sample_skill() -> PublicSkill:
    """Create sample public skill."""
    return PublicSkill(
        id="notion-weekly-report",
        name="notion-weekly-report",
        version="1.0.0",
        description="Generates weekly summary from Notion database",
        content="---\nname: notion-weekly-report\ndescription: Weekly report\n---\n\nContent",
        author_id="user-123",
        tags=["reporting", "notion", "weekly"],
        integrations=["notion"],
        status=PublicSkillStatus.APPROVED,
    )


class TestPublicSkillRepository:
    """Tests for PublicSkillRepository class."""

    async def test_create_public_skill(self, session: AsyncSession, sample_skill: PublicSkill):
        """PublicSkillRepository should create a new public skill."""
        repo = PublicSkillRepository(session)

        created = await repo.create(sample_skill)

        assert created.id == sample_skill.id
        assert created.name == sample_skill.name
        assert created.description == sample_skill.description
        assert created.author_id == sample_skill.author_id
        assert created.tags == sample_skill.tags
        assert created.integrations == sample_skill.integrations
        assert created.usage_count == 0
        assert created.created_at is not None

    async def test_get_by_id_existing_skill(
        self, session: AsyncSession, sample_skill: PublicSkill
    ):
        """PublicSkillRepository should retrieve skill by ID."""
        repo = PublicSkillRepository(session)
        await repo.create(sample_skill)

        retrieved = await repo.get_by_id(sample_skill.id)

        assert retrieved is not None
        assert retrieved.id == sample_skill.id
        assert retrieved.name == sample_skill.name

    async def test_get_by_id_nonexistent_skill(self, session: AsyncSession):
        """PublicSkillRepository should return None for nonexistent skill."""
        repo = PublicSkillRepository(session)

        retrieved = await repo.get_by_id("nonexistent-skill")

        assert retrieved is None

    async def test_get_by_name_existing_skill(
        self, session: AsyncSession, sample_skill: PublicSkill
    ):
        """PublicSkillRepository should retrieve skill by name."""
        repo = PublicSkillRepository(session)
        await repo.create(sample_skill)

        retrieved = await repo.get_by_name(sample_skill.name)

        assert retrieved is not None
        assert retrieved.id == sample_skill.id
        assert retrieved.name == sample_skill.name

    async def test_search_by_keyword_in_name(self, session: AsyncSession):
        """PublicSkillRepository should search by keyword in name."""
        repo = PublicSkillRepository(session)

        # Create multiple skills
        skill1 = PublicSkill(
            id="notion-report",
            name="notion-report",
            version="1.0.0",
            description="Generates reports from Notion",
            content="content1",
            author_id="user-1",
            tags=["reporting"],
            integrations=["notion"],
            status=PublicSkillStatus.APPROVED,
        )
        skill2 = PublicSkill(
            id="slack-notifier",
            name="slack-notifier",
            version="1.0.0",
            description="Sends notifications to Slack",
            content="content2",
            author_id="user-1",
            tags=["notifications"],
            integrations=["slack"],
            status=PublicSkillStatus.APPROVED,
        )

        await repo.create(skill1)
        await repo.create(skill2)

        results = await repo.search(keyword="notion")

        assert len(results) == 1
        assert results[0].id == "notion-report"

    async def test_search_by_keyword_in_description(self, session: AsyncSession):
        """PublicSkillRepository should search by keyword in description."""
        repo = PublicSkillRepository(session)

        skill = PublicSkill(
            id="weekly-analyzer",
            name="weekly-analyzer",
            version="1.0.0",
            description="Analyzes weekly metrics from various sources",
            content="content",
            author_id="user-1",
            tags=["analytics"],
            integrations=["notion"],
            status=PublicSkillStatus.APPROVED,
        )

        await repo.create(skill)

        results = await repo.search(keyword="weekly")

        assert len(results) == 1
        assert results[0].id == "weekly-analyzer"

    async def test_search_by_tags(self, session: AsyncSession):
        """PublicSkillRepository should filter by tags."""
        repo = PublicSkillRepository(session)

        skill1 = PublicSkill(
            id="skill1",
            name="skill1",
            version="1.0.0",
            description="Description 1",
            content="content1",
            author_id="user-1",
            tags=["reporting", "analytics"],
            integrations=["notion"],
            status=PublicSkillStatus.APPROVED,
        )
        skill2 = PublicSkill(
            id="skill2",
            name="skill2",
            version="1.0.0",
            description="Description 2",
            content="content2",
            author_id="user-1",
            tags=["notifications", "alerts"],
            integrations=["slack"],
            status=PublicSkillStatus.APPROVED,
        )

        await repo.create(skill1)
        await repo.create(skill2)

        results = await repo.search(tags=["reporting"])

        assert len(results) == 1
        assert results[0].id == "skill1"

    async def test_search_orders_by_usage_count(self, session: AsyncSession):
        """PublicSkillRepository should order results by usage_count DESC."""
        repo = PublicSkillRepository(session)

        # Create skills with different usage counts
        skill1 = PublicSkill(
            id="popular-skill",
            name="popular-skill",
            version="1.0.0",
            description="Very popular skill",
            content="content1",
            author_id="user-1",
            tags=["test"],
            integrations=["notion"],
            usage_count=100,
            status=PublicSkillStatus.APPROVED,
        )
        skill2 = PublicSkill(
            id="less-popular",
            name="less-popular",
            version="1.0.0",
            description="Less popular skill",
            content="content2",
            author_id="user-1",
            tags=["test"],
            integrations=["notion"],
            usage_count=10,
            status=PublicSkillStatus.APPROVED,
        )

        await repo.create(skill2)  # Create in reverse order
        await repo.create(skill1)

        results = await repo.search(keyword="skill")

        assert len(results) == 2
        assert results[0].id == "popular-skill"
        assert results[1].id == "less-popular"

    async def test_get_by_integration(self, session: AsyncSession):
        """PublicSkillRepository should filter by integration type."""
        repo = PublicSkillRepository(session)

        skill1 = PublicSkill(
            id="notion-skill",
            name="notion-skill",
            version="1.0.0",
            description="Notion integration skill",
            content="content1",
            author_id="user-1",
            tags=["notion"],
            integrations=["notion"],
            status=PublicSkillStatus.APPROVED,
        )
        skill2 = PublicSkill(
            id="slack-skill",
            name="slack-skill",
            version="1.0.0",
            description="Slack integration skill",
            content="content2",
            author_id="user-1",
            tags=["slack"],
            integrations=["slack"],
            status=PublicSkillStatus.APPROVED,
        )

        await repo.create(skill1)
        await repo.create(skill2)

        results = await repo.get_by_integration("notion")

        assert len(results) == 1
        assert results[0].id == "notion-skill"

    async def test_get_top_skills(self, session: AsyncSession):
        """PublicSkillRepository should return top skills by usage."""
        repo = PublicSkillRepository(session)

        # Create skills with different usage counts
        for i in range(15):
            skill = PublicSkill(
                id=f"skill-{i}",
                name=f"skill-{i}",
                version="1.0.0",
                description=f"Description {i}",
                content=f"content{i}",
                author_id="user-1",
                tags=["test"],
                integrations=["notion"],
                usage_count=i * 10,
                status=PublicSkillStatus.APPROVED,
            )
            await repo.create(skill)

        results = await repo.get_top_skills(limit=5)

        assert len(results) == 5
        # Should be ordered by usage_count DESC
        assert results[0].usage_count == 140
        assert results[4].usage_count == 100

    async def test_increment_usage_count(self, session: AsyncSession, sample_skill: PublicSkill):
        """PublicSkillRepository should increment usage count."""
        repo = PublicSkillRepository(session)
        await repo.create(sample_skill)

        initial_count = sample_skill.usage_count

        updated = await repo.increment_usage_count(sample_skill.id)

        assert updated is not None
        assert updated.usage_count == initial_count + 1

    async def test_increment_usage_count_multiple_times(
        self, session: AsyncSession, sample_skill: PublicSkill
    ):
        """PublicSkillRepository should handle multiple usage increments."""
        repo = PublicSkillRepository(session)
        await repo.create(sample_skill)

        for i in range(5):
            await repo.increment_usage_count(sample_skill.id)

        updated = await repo.get_by_id(sample_skill.id)

        assert updated is not None
        assert updated.usage_count == 5

    async def test_update_rating(self, session: AsyncSession, sample_skill: PublicSkill):
        """PublicSkillRepository should update skill rating."""
        repo = PublicSkillRepository(session)
        await repo.create(sample_skill)

        updated = await repo.update_rating(sample_skill.id, 4.5)

        assert updated is not None
        assert updated.rating_avg == 4.5

    async def test_update_status(self, session: AsyncSession, sample_skill: PublicSkill):
        """PublicSkillRepository should update skill status."""
        repo = PublicSkillRepository(session)
        await repo.create(sample_skill)

        updated = await repo.update_status(sample_skill.id, "archived")

        assert updated is not None
        assert updated.status == PublicSkillStatus.ARCHIVED

    async def test_delete_skill(self, session: AsyncSession, sample_skill: PublicSkill):
        """PublicSkillRepository should delete a skill."""
        repo = PublicSkillRepository(session)
        await repo.create(sample_skill)

        deleted = await repo.delete(sample_skill.id)

        assert deleted is True

        retrieved = await repo.get_by_id(sample_skill.id)
        assert retrieved is None

    async def test_delete_nonexistent_skill(self, session: AsyncSession):
        """PublicSkillRepository should return False when deleting nonexistent skill."""
        repo = PublicSkillRepository(session)

        deleted = await repo.delete("nonexistent-skill")

        assert deleted is False

    async def test_search_respects_status_filter(self, session: AsyncSession):
        """PublicSkillRepository should filter by status."""
        repo = PublicSkillRepository(session)

        approved_skill = PublicSkill(
            id="approved",
            name="approved",
            version="1.0.0",
            description="Approved skill",
            content="content1",
            author_id="user-1",
            tags=["test"],
            integrations=["notion"],
            status=PublicSkillStatus.APPROVED,
        )
        pending_skill = PublicSkill(
            id="pending",
            name="pending",
            version="1.0.0",
            description="Pending skill",
            content="content2",
            author_id="user-1",
            tags=["test"],
            integrations=["notion"],
            status=PublicSkillStatus.PENDING,
        )

        await repo.create(approved_skill)
        await repo.create(pending_skill)

        # Search with default status (approved)
        approved_results = await repo.search(keyword="skill")
        assert len(approved_results) == 1
        assert approved_results[0].status == PublicSkillStatus.APPROVED

        # Search for pending skills
        pending_results = await repo.search(keyword="skill", status="pending")
        assert len(pending_results) == 1
        assert pending_results[0].status == PublicSkillStatus.PENDING
