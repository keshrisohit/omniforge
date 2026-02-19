"""Tests for PublicSkill version management in repository."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

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
def skill_v1() -> PublicSkill:
    """Create version 1.0.0 of a skill."""
    return PublicSkill(
        id="notion-report-v1",
        name="notion-report",
        version="1.0.0",
        description="Generates reports from Notion",
        content="---\nname: notion-report\nversion: 1.0.0\n---\nContent v1",
        author_id="user-123",
        tags=["reporting", "notion"],
        integrations=["notion"],
        status=PublicSkillStatus.APPROVED,
    )


@pytest.fixture
def skill_v2() -> PublicSkill:
    """Create version 2.0.0 of a skill."""
    return PublicSkill(
        id="notion-report-v2",
        name="notion-report",
        version="2.0.0",
        description="Generates reports from Notion (v2)",
        content="---\nname: notion-report\nversion: 2.0.0\n---\nContent v2",
        author_id="user-123",
        tags=["reporting", "notion"],
        integrations=["notion"],
        status=PublicSkillStatus.APPROVED,
    )


@pytest.fixture
def skill_v1_1() -> PublicSkill:
    """Create version 1.1.0 of a skill."""
    return PublicSkill(
        id="notion-report-v1-1",
        name="notion-report",
        version="1.1.0",
        description="Generates reports from Notion (v1.1)",
        content="---\nname: notion-report\nversion: 1.1.0\n---\nContent v1.1",
        author_id="user-123",
        tags=["reporting", "notion"],
        integrations=["notion"],
        status=PublicSkillStatus.APPROVED,
    )


class TestPublicSkillVersioning:
    """Tests for PublicSkill version management."""

    async def test_create_multiple_versions(
        self,
        session: AsyncSession,
        skill_v1: PublicSkill,
        skill_v2: PublicSkill,
    ):
        """Repository should store multiple versions of same skill."""
        repo = PublicSkillRepository(session)

        created_v1 = await repo.create(skill_v1)
        created_v2 = await repo.create(skill_v2)

        assert created_v1.version == "1.0.0"
        assert created_v2.version == "2.0.0"
        assert created_v1.name == created_v2.name

    async def test_get_by_name_specific_version(
        self,
        session: AsyncSession,
        skill_v1: PublicSkill,
        skill_v2: PublicSkill,
    ):
        """Repository should retrieve specific version by name and version."""
        repo = PublicSkillRepository(session)
        await repo.create(skill_v1)
        await repo.create(skill_v2)

        retrieved_v1 = await repo.get_by_name("notion-report", version="1.0.0")
        retrieved_v2 = await repo.get_by_name("notion-report", version="2.0.0")

        assert retrieved_v1 is not None
        assert retrieved_v1.version == "1.0.0"
        assert retrieved_v2 is not None
        assert retrieved_v2.version == "2.0.0"

    async def test_get_by_name_latest_version(
        self,
        session: AsyncSession,
        skill_v1: PublicSkill,
        skill_v2: PublicSkill,
        skill_v1_1: PublicSkill,
    ):
        """Repository should retrieve latest version when version not specified."""
        repo = PublicSkillRepository(session)
        await repo.create(skill_v1)
        await repo.create(skill_v1_1)
        await repo.create(skill_v2)

        latest = await repo.get_by_name("notion-report")

        assert latest is not None
        assert latest.version == "2.0.0"

    async def test_get_by_name_nonexistent_version(
        self,
        session: AsyncSession,
        skill_v1: PublicSkill,
    ):
        """Repository should return None for nonexistent version."""
        repo = PublicSkillRepository(session)
        await repo.create(skill_v1)

        retrieved = await repo.get_by_name("notion-report", version="3.0.0")

        assert retrieved is None

    async def test_get_versions_for_skill(
        self,
        session: AsyncSession,
        skill_v1: PublicSkill,
        skill_v2: PublicSkill,
        skill_v1_1: PublicSkill,
    ):
        """Repository should list all versions for a skill."""
        repo = PublicSkillRepository(session)
        await repo.create(skill_v1)
        await repo.create(skill_v2)
        await repo.create(skill_v1_1)

        versions = await repo.get_versions("notion-report")

        assert len(versions) == 3
        assert "1.0.0" in versions
        assert "1.1.0" in versions
        assert "2.0.0" in versions

    async def test_get_versions_empty_for_nonexistent_skill(
        self, session: AsyncSession
    ):
        """Repository should return empty list for nonexistent skill."""
        repo = PublicSkillRepository(session)

        versions = await repo.get_versions("nonexistent-skill")

        assert versions == []

    async def test_increment_usage_count_specific_version(
        self,
        session: AsyncSession,
        skill_v1: PublicSkill,
        skill_v2: PublicSkill,
    ):
        """Repository should increment usage count for specific version."""
        repo = PublicSkillRepository(session)
        await repo.create(skill_v1)
        await repo.create(skill_v2)

        updated = await repo.increment_usage_count("notion-report", version="1.0.0")

        assert updated is not None
        assert updated.version == "1.0.0"
        assert updated.usage_count == 1

        # V2 should still have 0
        v2_check = await repo.get_by_name("notion-report", version="2.0.0")
        assert v2_check is not None
        assert v2_check.usage_count == 0

    async def test_increment_usage_count_latest_version(
        self,
        session: AsyncSession,
        skill_v1: PublicSkill,
        skill_v2: PublicSkill,
    ):
        """Repository should increment usage count for latest version when not specified."""
        repo = PublicSkillRepository(session)
        await repo.create(skill_v1)
        await repo.create(skill_v2)

        updated = await repo.increment_usage_count("notion-report")

        assert updated is not None
        assert updated.version == "2.0.0"
        assert updated.usage_count == 1

    async def test_unique_constraint_name_version(
        self,
        session: AsyncSession,
        skill_v1: PublicSkill,
    ):
        """Repository should enforce unique constraint on (name, version)."""
        repo = PublicSkillRepository(session)
        await repo.create(skill_v1)

        # Try to create duplicate with same name and version
        duplicate = PublicSkill(
            id="different-id",
            name="notion-report",
            version="1.0.0",
            description="Different description",
            content="Different content",
            author_id="user-456",
            tags=["different"],
            integrations=["notion"],
            status=PublicSkillStatus.APPROVED,
        )

        with pytest.raises(Exception):  # SQLAlchemy IntegrityError
            await repo.create(duplicate)
            await session.commit()

    async def test_search_returns_all_versions(
        self,
        session: AsyncSession,
        skill_v1: PublicSkill,
        skill_v2: PublicSkill,
    ):
        """Repository search should return all matching versions."""
        repo = PublicSkillRepository(session)
        await repo.create(skill_v1)
        await repo.create(skill_v2)

        results = await repo.search(keyword="notion")

        assert len(results) == 2
        versions_found = {skill.version for skill in results}
        assert "1.0.0" in versions_found
        assert "2.0.0" in versions_found

    async def test_get_top_skills_includes_all_versions(
        self,
        session: AsyncSession,
        skill_v1: PublicSkill,
        skill_v2: PublicSkill,
    ):
        """Repository top skills should include all versions."""
        repo = PublicSkillRepository(session)
        await repo.create(skill_v1)
        await repo.increment_usage_count("notion-report", version="1.0.0")

        await repo.create(skill_v2)
        await repo.increment_usage_count("notion-report", version="2.0.0")
        await repo.increment_usage_count("notion-report", version="2.0.0")

        top_skills = await repo.get_top_skills(limit=10)

        assert len(top_skills) == 2
        # V2 should be first (higher usage)
        assert top_skills[0].version == "2.0.0"
        assert top_skills[0].usage_count == 2
        assert top_skills[1].version == "1.0.0"
        assert top_skills[1].usage_count == 1
