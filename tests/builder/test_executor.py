"""Tests for agent execution service."""

import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from omniforge.builder.executor import AgentExecutionService, AgentExecutor
from omniforge.builder.models import (
    AgentConfig,
    AgentStatus,
    ExecutionStatus,
    SkillReference,
    TriggerType,
)
from omniforge.builder.models.orm import Base
from omniforge.builder.repository import AgentConfigRepository, AgentExecutionRepository
from omniforge.builder.skill_generator import SkillGenerationRequest, SkillMdGenerator


@pytest.fixture
async def async_session() -> AsyncSession:
    """Create async test database session."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text("PRAGMA foreign_keys=ON"))

    async_session_maker = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session_maker() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def skills_dir() -> Path:
    """Create temporary skills directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def agent_executor(skills_dir: Path) -> AgentExecutor:
    """Create agent executor."""
    skill_generator = SkillMdGenerator()
    return AgentExecutor(skill_generator, skills_dir)


class TestAgentExecutor:
    """Tests for AgentExecutor."""

    @pytest.mark.asyncio
    async def test_prepare_agent_skills(
        self,
        agent_executor: AgentExecutor,
        skills_dir: Path,
    ) -> None:
        """Test preparing agent skills by generating SKILL.md files."""
        agent_config = AgentConfig(
            tenant_id="tenant-1",
            name="Test Agent",
            description="Test",
            skills=[SkillReference(skill_id="test-skill", name="Test", order=1)],
            created_by="user-1",
        )

        skill_request = SkillGenerationRequest(
            skill_id="test-skill",
            name="Test Skill",
            description="A test skill",
            purpose="Test purpose",
            steps=["Do something"],
        )

        await agent_executor.prepare_agent_skills(agent_config, [skill_request])

        # Verify skill file was created
        skill_file = skills_dir / "tenant-1" / "skills" / "test-skill.md"
        assert skill_file.exists()

        content = skill_file.read_text()
        assert "name: test-skill" in content
        assert "# Test Skill" in content

    @pytest.mark.asyncio
    async def test_execute_skill_not_found(
        self,
        agent_executor: AgentExecutor,
    ) -> None:
        """Test executing non-existent skill raises error."""
        with pytest.raises(FileNotFoundError, match="Skill not found"):
            await agent_executor._execute_skill(
                "tenant-1",
                "nonexistent-skill",
                {},
            )

    @pytest.mark.asyncio
    async def test_execute_skill_success(
        self,
        agent_executor: AgentExecutor,
        skills_dir: Path,
    ) -> None:
        """Test successful skill execution."""
        # Create skill file
        skill_dir = skills_dir / "tenant-1" / "skills"
        skill_dir.mkdir(parents=True)

        skill_content = """---
name: test-skill
description: Test skill
---

# Test Skill

Test instructions.
"""
        (skill_dir / "test-skill.md").write_text(skill_content)

        result = await agent_executor._execute_skill(
            "tenant-1",
            "test-skill",
            {"param": "value"},
        )

        assert result["skill_id"] == "test-skill"
        assert result["status"] == "success"
        assert result["output"]["config"]["param"] == "value"

    @pytest.mark.asyncio
    async def test_execute_agent_single_skill(
        self,
        agent_executor: AgentExecutor,
        async_session: AsyncSession,
        skills_dir: Path,
    ) -> None:
        """Test executing agent with single skill."""
        # Setup agent
        agent_repo = AgentConfigRepository(async_session)
        exec_repo = AgentExecutionRepository(async_session)

        agent = await agent_repo.create(
            AgentConfig(
                tenant_id="tenant-1",
                name="Test Agent",
                description="Test",
                skills=[SkillReference(skill_id="test-skill", name="Test", order=1)],
                created_by="user-1",
            )
        )
        await async_session.commit()

        # Create skill file
        skill_dir = skills_dir / "tenant-1" / "skills"
        skill_dir.mkdir(parents=True)
        (skill_dir / "test-skill.md").write_text(
            "---\nname: test-skill\ndescription: Test skill\n---\n\n# Test\n"
        )

        # Execute agent
        execution = await agent_executor.execute_agent(
            agent, exec_repo, "on_demand"
        )

        if execution.status != ExecutionStatus.SUCCESS:
            print(f"Execution failed with error: {execution.error}")

        assert execution.status == ExecutionStatus.SUCCESS
        assert execution.duration_ms is not None
        assert execution.duration_ms > 0

    @pytest.mark.asyncio
    async def test_execute_agent_skill_failure(
        self,
        agent_executor: AgentExecutor,
        async_session: AsyncSession,
    ) -> None:
        """Test agent execution handles skill failure."""
        agent_repo = AgentConfigRepository(async_session)
        exec_repo = AgentExecutionRepository(async_session)

        agent = await agent_repo.create(
            AgentConfig(
                tenant_id="tenant-1",
                name="Test Agent",
                description="Test",
                skills=[
                    SkillReference(skill_id="nonexistent-skill", name="Test", order=1)
                ],
                created_by="user-1",
            )
        )
        await async_session.commit()

        # Execute agent (should fail)
        execution = await agent_executor.execute_agent(
            agent, exec_repo, "on_demand"
        )

        assert execution.status == ExecutionStatus.FAILED
        assert execution.error is not None
        assert "not found" in execution.error.lower()


class TestAgentExecutionService:
    """Tests for AgentExecutionService."""

    @pytest.mark.asyncio
    async def test_execute_agent_by_id(
        self,
        agent_executor: AgentExecutor,
        async_session: AsyncSession,
        skills_dir: Path,
    ) -> None:
        """Test executing agent by ID."""
        agent_repo = AgentConfigRepository(async_session)
        exec_repo = AgentExecutionRepository(async_session)
        service = AgentExecutionService(agent_executor, agent_repo, exec_repo)

        # Create agent
        agent = await agent_repo.create(
            AgentConfig(
                tenant_id="tenant-1",
                name="Test Agent",
                description="Test",
                skills=[SkillReference(skill_id="test-skill", name="Test", order=1)],
                created_by="user-1",
            )
        )
        await async_session.commit()

        # Create skill file
        skill_dir = skills_dir / "tenant-1" / "skills"
        skill_dir.mkdir(parents=True)
        (skill_dir / "test-skill.md").write_text(
            "---\nname: test-skill\ndescription: Test skill\n---\n\n# Test\n"
        )

        # Execute by ID
        execution = await service.execute_agent_by_id(
            agent.id or "",
            "tenant-1",
            "scheduled",
        )

        assert execution.status == ExecutionStatus.SUCCESS
        assert execution.trigger_type == "scheduled"

    @pytest.mark.asyncio
    async def test_execute_agent_by_id_not_found(
        self,
        agent_executor: AgentExecutor,
        async_session: AsyncSession,
    ) -> None:
        """Test executing non-existent agent raises error."""
        agent_repo = AgentConfigRepository(async_session)
        exec_repo = AgentExecutionRepository(async_session)
        service = AgentExecutionService(agent_executor, agent_repo, exec_repo)

        with pytest.raises(ValueError, match="not found"):
            await service.execute_agent_by_id(
                "nonexistent-id",
                "tenant-1",
            )

    @pytest.mark.asyncio
    async def test_execute_agent_test_mode(
        self,
        agent_executor: AgentExecutor,
    ) -> None:
        """Test executing agent in test mode."""
        agent_config = AgentConfig(
            tenant_id="tenant-1",
            name="Test Agent",
            description="Test",
            skills=[SkillReference(skill_id="test-skill", name="Test", order=1)],
            created_by="user-1",
        )

        skill_request = SkillGenerationRequest(
            skill_id="test-skill",
            name="Test Skill",
            description="Test",
            purpose="Test",
            steps=["Do something"],
        )

        agent_repo = AgentConfigRepository(None)  # type: ignore
        exec_repo = AgentExecutionRepository(None)  # type: ignore
        service = AgentExecutionService(agent_executor, agent_repo, exec_repo)

        result = await service.execute_agent_test(agent_config, [skill_request])

        assert result["status"] == "success"
        assert result["skills_executed"] == 1

    @pytest.mark.asyncio
    async def test_execute_agent_test_mode_failure(
        self,
        agent_executor: AgentExecutor,
    ) -> None:
        """Test agent test mode handles failures."""
        agent_config = AgentConfig(
            tenant_id="tenant-1",
            name="Test Agent",
            description="Test",
            skills=[
                SkillReference(skill_id="nonexistent-skill", name="Test", order=1)
            ],
            created_by="user-1",
        )

        agent_repo = AgentConfigRepository(None)  # type: ignore
        exec_repo = AgentExecutionRepository(None)  # type: ignore
        service = AgentExecutionService(agent_executor, agent_repo, exec_repo)

        result = await service.execute_agent_test(agent_config, [])

        assert result["status"] == "failed"
        assert "error" in result
