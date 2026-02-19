"""Tests for repository layer with database operations."""

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from omniforge.builder.models import (
    AgentConfig,
    AgentExecution,
    AgentStatus,
    Credential,
    ExecutionStatus,
    IntegrationType,
    SkillReference,
    TriggerType,
)
from omniforge.builder.models.orm import AgentConfigModel, AgentExecutionModel, CredentialModel
from omniforge.builder.repository import (
    AgentConfigRepository,
    AgentExecutionRepository,
    CredentialRepository,
)
from omniforge.storage.base_model import Base
from omniforge.storage.model_registry import register_all_models


@pytest.fixture
async def async_session() -> AsyncSession:
    """Create async test database session."""
    # Register all models before creating tables
    register_all_models()

    # Use in-memory SQLite for tests
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create tables and enable foreign keys for SQLite
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Enable foreign key constraints in SQLite
        await conn.execute(text("PRAGMA foreign_keys=ON"))

    # Create session
    async_session_maker = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session_maker() as session:
        yield session

    # Clean up: drop all tables after the test to ensure fresh state for next test
    # This is necessary because StaticPool keeps the same in-memory database connection
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


class TestAgentConfigRepository:
    """Tests for AgentConfigRepository."""

    @pytest.mark.asyncio
    async def test_create_agent(self, async_session: AsyncSession) -> None:
        """Test creating an agent configuration."""
        repo = AgentConfigRepository(async_session)

        config = AgentConfig(
            tenant_id="tenant-123",
            name="Test Agent",
            description="Test description",
            skills=[SkillReference(skill_id="test-skill", name="Test", order=1)],
            created_by="user-456",
        )

        created = await repo.create(config)

        assert created.id is not None
        assert created.tenant_id == "tenant-123"
        assert created.name == "Test Agent"
        assert created.created_at is not None
        assert created.updated_at is not None

    @pytest.mark.asyncio
    async def test_get_by_id_with_tenant_isolation(
        self, async_session: AsyncSession
    ) -> None:
        """Test getting agent by ID with tenant isolation."""
        repo = AgentConfigRepository(async_session)

        # Create agent for tenant-1
        config = AgentConfig(
            tenant_id="tenant-1",
            name="Agent 1",
            description="Test",
            skills=[SkillReference(skill_id="test", name="Test", order=1)],
            created_by="user-1",
        )
        created = await repo.create(config)
        await async_session.commit()

        # Should find it for same tenant
        found = await repo.get_by_id(created.id, "tenant-1")
        assert found is not None
        assert found.id == created.id

        # Should NOT find it for different tenant
        not_found = await repo.get_by_id(created.id, "tenant-2")
        assert not_found is None

    @pytest.mark.asyncio
    async def test_list_by_tenant(self, async_session: AsyncSession) -> None:
        """Test listing agents by tenant."""
        repo = AgentConfigRepository(async_session)

        # Create agents for two tenants
        for i in range(3):
            await repo.create(
                AgentConfig(
                    tenant_id="tenant-1",
                    name=f"Agent {i}",
                    description="Test",
                    skills=[SkillReference(skill_id=f"skill-{i}", name="Test", order=1)],
                    created_by="user-1",
                )
            )

        await repo.create(
            AgentConfig(
                tenant_id="tenant-2",
                name="Agent Other",
                description="Test",
                skills=[SkillReference(skill_id="skill-x", name="Test", order=1)],
                created_by="user-2",
            )
        )
        await async_session.commit()

        # List tenant-1 agents
        agents = await repo.list_by_tenant("tenant-1")
        assert len(agents) == 3
        assert all(a.tenant_id == "tenant-1" for a in agents)

        # List tenant-2 agents
        agents = await repo.list_by_tenant("tenant-2")
        assert len(agents) == 1
        assert agents[0].tenant_id == "tenant-2"

    @pytest.mark.asyncio
    async def test_list_by_tenant_with_status_filter(
        self, async_session: AsyncSession
    ) -> None:
        """Test listing agents filtered by status."""
        repo = AgentConfigRepository(async_session)

        # Create agents with different statuses
        await repo.create(
            AgentConfig(
                tenant_id="tenant-1",
                name="Draft Agent",
                description="Test",
                status=AgentStatus.DRAFT,
                skills=[SkillReference(skill_id="skill-1", name="Test", order=1)],
                created_by="user-1",
            )
        )

        await repo.create(
            AgentConfig(
                tenant_id="tenant-1",
                name="Active Agent",
                description="Test",
                status=AgentStatus.ACTIVE,
                skills=[SkillReference(skill_id="skill-2", name="Test", order=1)],
                created_by="user-1",
            )
        )
        await async_session.commit()

        # Filter by status
        active_agents = await repo.list_by_tenant("tenant-1", status="active")
        assert len(active_agents) == 1
        assert active_agents[0].status == AgentStatus.ACTIVE

        draft_agents = await repo.list_by_tenant("tenant-1", status="draft")
        assert len(draft_agents) == 1
        assert draft_agents[0].status == AgentStatus.DRAFT

    @pytest.mark.asyncio
    async def test_update_agent(self, async_session: AsyncSession) -> None:
        """Test updating an agent configuration."""
        repo = AgentConfigRepository(async_session)

        # Create agent
        config = AgentConfig(
            tenant_id="tenant-1",
            name="Original Name",
            description="Original description",
            skills=[SkillReference(skill_id="skill-1", name="Test", order=1)],
            created_by="user-1",
        )
        created = await repo.create(config)
        await async_session.commit()

        # Update agent
        created.name = "Updated Name"
        created.description = "Updated description"
        created.status = AgentStatus.ACTIVE

        updated = await repo.update(created)
        await async_session.commit()

        assert updated.name == "Updated Name"
        assert updated.description == "Updated description"
        assert updated.status == AgentStatus.ACTIVE

        # Verify in database
        fetched = await repo.get_by_id(created.id, "tenant-1")
        assert fetched.name == "Updated Name"

    @pytest.mark.asyncio
    async def test_delete_agent(self, async_session: AsyncSession) -> None:
        """Test deleting an agent configuration."""
        repo = AgentConfigRepository(async_session)

        # Create agent
        config = AgentConfig(
            tenant_id="tenant-1",
            name="To Delete",
            description="Test",
            skills=[SkillReference(skill_id="skill-1", name="Test", order=1)],
            created_by="user-1",
        )
        created = await repo.create(config)
        await async_session.commit()

        # Delete agent
        deleted = await repo.delete(created.id, "tenant-1")
        await async_session.commit()

        assert deleted is True

        # Verify it's gone
        not_found = await repo.get_by_id(created.id, "tenant-1")
        assert not_found is None

    @pytest.mark.asyncio
    async def test_delete_respects_tenant_isolation(
        self, async_session: AsyncSession
    ) -> None:
        """Test deletion respects tenant boundaries."""
        repo = AgentConfigRepository(async_session)

        # Create agent for tenant-1
        config = AgentConfig(
            tenant_id="tenant-1",
            name="Agent",
            description="Test",
            skills=[SkillReference(skill_id="skill-1", name="Test", order=1)],
            created_by="user-1",
        )
        created = await repo.create(config)
        await async_session.commit()

        # Try to delete as tenant-2 (should fail)
        deleted = await repo.delete(created.id, "tenant-2")
        await async_session.commit()

        assert deleted is False

        # Verify agent still exists for tenant-1
        still_there = await repo.get_by_id(created.id, "tenant-1")
        assert still_there is not None


class TestCredentialRepository:
    """Tests for CredentialRepository."""

    @pytest.mark.asyncio
    async def test_create_credential(self, async_session: AsyncSession) -> None:
        """Test creating a credential."""
        repo = CredentialRepository(async_session)

        credential = Credential(
            tenant_id="tenant-123",
            integration_type=IntegrationType.NOTION,
            integration_name="Test Workspace",
            credentials={"token": "secret"},
        )

        # Encrypt credentials
        key = Credential.generate_encryption_key()
        encrypted = Credential.encrypt_credentials(credential.credentials, key)

        created = await repo.create(credential, encrypted)
        await async_session.commit()

        assert created.id is not None
        assert created.tenant_id == "tenant-123"
        assert created.integration_type == IntegrationType.NOTION

    @pytest.mark.asyncio
    async def test_get_credential_with_encrypted_data(
        self, async_session: AsyncSession
    ) -> None:
        """Test retrieving credential with encrypted data."""
        repo = CredentialRepository(async_session)

        original_creds = {"access_token": "secret_abc", "workspace": "ws-123"}
        key = Credential.generate_encryption_key()
        encrypted = Credential.encrypt_credentials(original_creds, key)

        credential = Credential(
            tenant_id="tenant-1",
            integration_type=IntegrationType.NOTION,
            integration_name="Workspace",
            credentials=original_creds,
        )

        created = await repo.create(credential, encrypted)
        await async_session.commit()

        # Get credential
        result = await repo.get_by_id(created.id, "tenant-1")
        assert result is not None

        cred, encrypted_data = result

        # Decrypt and verify
        decrypted = Credential.decrypt_credentials(encrypted_data, key)
        assert decrypted == original_creds

    @pytest.mark.asyncio
    async def test_list_credentials_by_tenant(
        self, async_session: AsyncSession
    ) -> None:
        """Test listing credentials by tenant."""
        repo = CredentialRepository(async_session)
        key = Credential.generate_encryption_key()

        # Create credentials for tenant-1
        for i in range(2):
            cred = Credential(
                tenant_id="tenant-1",
                integration_type=IntegrationType.NOTION,
                integration_name=f"Workspace {i}",
                credentials={},
            )
            encrypted = Credential.encrypt_credentials({}, key)
            await repo.create(cred, encrypted)

        # Create credential for tenant-2
        cred = Credential(
            tenant_id="tenant-2",
            integration_type=IntegrationType.SLACK,
            integration_name="Other",
            credentials={},
        )
        encrypted = Credential.encrypt_credentials({}, key)
        await repo.create(cred, encrypted)

        await async_session.commit()

        # List tenant-1 credentials
        creds = await repo.list_by_tenant("tenant-1")
        assert len(creds) == 2
        assert all(c.tenant_id == "tenant-1" for c in creds)

    @pytest.mark.asyncio
    async def test_update_last_used(self, async_session: AsyncSession) -> None:
        """Test updating last_used_at timestamp."""
        repo = CredentialRepository(async_session)
        key = Credential.generate_encryption_key()

        cred = Credential(
            tenant_id="tenant-1",
            integration_type=IntegrationType.NOTION,
            integration_name="Workspace",
            credentials={},
        )
        encrypted = Credential.encrypt_credentials({}, key)
        created = await repo.create(cred, encrypted)
        await async_session.commit()

        # Update last used
        await repo.update_last_used(created.id, "tenant-1")
        await async_session.commit()

        # Verify timestamp was set
        result = await repo.get_by_id(created.id, "tenant-1")
        assert result is not None
        fetched, _ = result
        assert fetched.last_used_at is not None


class TestAgentExecutionRepository:
    """Tests for AgentExecutionRepository."""

    @pytest.mark.asyncio
    async def test_create_execution(self, async_session: AsyncSession) -> None:
        """Test creating an execution log."""
        # First create an agent
        agent_repo = AgentConfigRepository(async_session)
        agent = await agent_repo.create(
            AgentConfig(
                tenant_id="tenant-1",
                name="Test Agent",
                description="Test",
                skills=[SkillReference(skill_id="skill-1", name="Test", order=1)],
                created_by="user-1",
            )
        )
        await async_session.commit()

        # Create execution
        exec_repo = AgentExecutionRepository(async_session)
        execution = AgentExecution(
            agent_id=agent.id,
            tenant_id="tenant-1",
            trigger_type="on_demand",
            started_at=datetime.now(timezone.utc),
        )

        created = await exec_repo.create(execution)
        await async_session.commit()

        assert created.id is not None
        assert created.agent_id == agent.id
        assert created.status == ExecutionStatus.PENDING

    @pytest.mark.asyncio
    async def test_list_executions_by_agent(
        self, async_session: AsyncSession
    ) -> None:
        """Test listing executions for an agent."""
        # Create agent
        agent_repo = AgentConfigRepository(async_session)
        agent = await agent_repo.create(
            AgentConfig(
                tenant_id="tenant-1",
                name="Test Agent",
                description="Test",
                skills=[SkillReference(skill_id="skill-1", name="Test", order=1)],
                created_by="user-1",
            )
        )
        await async_session.commit()

        # Create executions
        exec_repo = AgentExecutionRepository(async_session)
        for i in range(3):
            await exec_repo.create(
                AgentExecution(
                    agent_id=agent.id,
                    tenant_id="tenant-1",
                    trigger_type="scheduled",
                    started_at=datetime.now(timezone.utc),
                )
            )
        await async_session.commit()

        # List executions
        executions = await exec_repo.list_by_agent(agent.id, "tenant-1")
        assert len(executions) == 3
        assert all(e.agent_id == agent.id for e in executions)

    @pytest.mark.asyncio
    async def test_update_execution_status(
        self, async_session: AsyncSession
    ) -> None:
        """Test updating execution status and completion details."""
        # Create agent and execution
        agent_repo = AgentConfigRepository(async_session)
        agent = await agent_repo.create(
            AgentConfig(
                tenant_id="tenant-1",
                name="Test Agent",
                description="Test",
                skills=[SkillReference(skill_id="skill-1", name="Test", order=1)],
                created_by="user-1",
            )
        )

        exec_repo = AgentExecutionRepository(async_session)
        execution = await exec_repo.create(
            AgentExecution(
                agent_id=agent.id,
                tenant_id="tenant-1",
                trigger_type="on_demand",
                started_at=datetime.now(timezone.utc),
            )
        )
        await async_session.commit()

        # Update status to success
        updated = await exec_repo.update_status(
            execution.id,
            "tenant-1",
            status="success",
            completed_at=datetime.now(timezone.utc),
            duration_ms=5000,
            output={"result": "completed"},
        )
        await async_session.commit()

        assert updated is not None
        assert updated.status == ExecutionStatus.SUCCESS
        assert updated.duration_ms == 5000
        assert updated.output["result"] == "completed"

    @pytest.mark.asyncio
    async def test_cascade_delete_executions(
        self, async_session: AsyncSession
    ) -> None:
        """Test executions are deleted when agent is deleted."""
        # Create agent
        agent_repo = AgentConfigRepository(async_session)
        agent = await agent_repo.create(
            AgentConfig(
                tenant_id="tenant-1",
                name="Test Agent",
                description="Test",
                skills=[SkillReference(skill_id="skill-1", name="Test", order=1)],
                created_by="user-1",
            )
        )

        # Create executions
        exec_repo = AgentExecutionRepository(async_session)
        execution = await exec_repo.create(
            AgentExecution(
                agent_id=agent.id,
                tenant_id="tenant-1",
                trigger_type="on_demand",
            )
        )
        await async_session.commit()

        # Delete agent
        await agent_repo.delete(agent.id, "tenant-1")
        await async_session.commit()

        # Verify executions are gone
        not_found = await exec_repo.get_by_id(execution.id, "tenant-1")
        assert not_found is None
