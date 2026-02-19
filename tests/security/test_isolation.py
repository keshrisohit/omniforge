"""Tests for tenant isolation enforcement."""

from datetime import datetime

import pytest

from omniforge.agents.base import BaseAgent
from omniforge.agents.errors import TenantIsolationError
from omniforge.agents.models import (
    AgentCapabilities,
    AgentIdentity,
    AgentSkill,
    SkillInputMode,
    SkillOutputMode,
)
from omniforge.security.isolation import (
    enforce_agent_isolation,
    enforce_task_isolation,
    filter_by_tenant,
)
from omniforge.security.tenant import TenantContext
from omniforge.tasks.models import Task, TaskState


class TestAgent(BaseAgent):
    """Test agent for isolation testing."""

    identity = AgentIdentity(
        id="test-agent",
        name="Test Agent",
        description="Test agent for isolation",
        version="1.0.0",
    )
    capabilities = AgentCapabilities(streaming=False)
    skills = [
        AgentSkill(
            id="test-skill",
            name="Test Skill",
            description="Test skill",
            input_modes=[SkillInputMode.TEXT],
            output_modes=[SkillOutputMode.TEXT],
        )
    ]

    async def process_task(self, task):  # type: ignore[override]
        """Stub implementation."""
        pass


class TestEnforceAgentIsolation:
    """Tests for enforce_agent_isolation function."""

    def test_no_tenant_context_allows_access(self) -> None:
        """Without tenant context, access should be allowed."""
        TenantContext.clear()
        agent = TestAgent(tenant_id="tenant-1")

        # Should not raise
        enforce_agent_isolation(agent)

    def test_agent_without_tenant_id_is_shared(self) -> None:
        """Agent without tenant_id is shared and accessible."""
        TenantContext.set("tenant-1")
        agent = TestAgent(tenant_id=None)

        # Should not raise - shared agents are accessible
        enforce_agent_isolation(agent)

        # Cleanup
        TenantContext.clear()

    def test_matching_tenant_allows_access(self) -> None:
        """Matching tenant ID should allow access."""
        TenantContext.set("tenant-1")
        agent = TestAgent(tenant_id="tenant-1")

        # Should not raise
        enforce_agent_isolation(agent)

        # Cleanup
        TenantContext.clear()

    def test_different_tenant_raises_error(self) -> None:
        """Different tenant ID should raise TenantIsolationError."""
        TenantContext.set("tenant-1")
        agent = TestAgent(tenant_id="tenant-2")

        with pytest.raises(TenantIsolationError) as exc_info:
            enforce_agent_isolation(agent)

        assert "different tenant" in str(exc_info.value)
        assert exc_info.value.resource_type == "agent"
        assert exc_info.value.resource_id == "test-agent"

        # Cleanup
        TenantContext.clear()


class TestEnforceTaskIsolation:
    """Tests for enforce_task_isolation function."""

    def test_no_tenant_context_allows_access(self) -> None:
        """Without tenant context, access should be allowed."""
        TenantContext.clear()
        task = Task(
            id="task-1",
            agent_id="agent-1",
            state=TaskState.SUBMITTED,
            messages=[],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            tenant_id="tenant-1",
            user_id="user-1",
        )

        # Should not raise
        enforce_task_isolation(task)

    def test_task_without_tenant_id_is_shared(self) -> None:
        """Task without tenant_id is shared and accessible."""
        TenantContext.set("tenant-1")
        task = Task(
            id="task-1",
            agent_id="agent-1",
            state=TaskState.SUBMITTED,
            messages=[],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            tenant_id=None,
            user_id="user-1",
        )

        # Should not raise - shared tasks are accessible
        enforce_task_isolation(task)

        # Cleanup
        TenantContext.clear()

    def test_matching_tenant_allows_access(self) -> None:
        """Matching tenant ID should allow access."""
        TenantContext.set("tenant-1")
        task = Task(
            id="task-1",
            agent_id="agent-1",
            state=TaskState.SUBMITTED,
            messages=[],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            tenant_id="tenant-1",
            user_id="user-1",
        )

        # Should not raise
        enforce_task_isolation(task)

        # Cleanup
        TenantContext.clear()

    def test_different_tenant_raises_error(self) -> None:
        """Different tenant ID should raise TenantIsolationError."""
        TenantContext.set("tenant-1")
        task = Task(
            id="task-1",
            agent_id="agent-1",
            state=TaskState.SUBMITTED,
            messages=[],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            tenant_id="tenant-2",
            user_id="user-1",
        )

        with pytest.raises(TenantIsolationError) as exc_info:
            enforce_task_isolation(task)

        assert "task-1" in str(exc_info.value)
        assert exc_info.value.resource_type == "task"
        assert exc_info.value.resource_id == "task-1"

        # Cleanup
        TenantContext.clear()


class TestFilterByTenant:
    """Tests for filter_by_tenant function."""

    def test_no_tenant_context_returns_all(self) -> None:
        """Without tenant context, all resources should be returned."""
        TenantContext.clear()
        agents = [
            TestAgent(tenant_id="tenant-1"),
            TestAgent(tenant_id="tenant-2"),
            TestAgent(tenant_id=None),
        ]

        filtered = filter_by_tenant(agents)

        assert len(filtered) == 3

    def test_filters_to_matching_tenant(self) -> None:
        """Should return only resources for current tenant."""
        TenantContext.set("tenant-1")
        agents = [
            TestAgent(tenant_id="tenant-1"),
            TestAgent(tenant_id="tenant-2"),
            TestAgent(tenant_id="tenant-1"),
        ]

        filtered = filter_by_tenant(agents)

        assert len(filtered) == 2
        for agent in filtered:
            assert agent.tenant_id == "tenant-1"

        # Cleanup
        TenantContext.clear()

    def test_includes_shared_resources(self) -> None:
        """Should include resources with no tenant_id (shared)."""
        TenantContext.set("tenant-1")
        agents = [
            TestAgent(tenant_id="tenant-1"),
            TestAgent(tenant_id="tenant-2"),
            TestAgent(tenant_id=None),
        ]

        filtered = filter_by_tenant(agents)

        assert len(filtered) == 2
        tenant_ids = [agent.tenant_id for agent in filtered]
        assert "tenant-1" in tenant_ids
        assert None in tenant_ids

        # Cleanup
        TenantContext.clear()

    def test_explicit_tenant_parameter(self) -> None:
        """Should use explicit tenant parameter if provided."""
        TenantContext.clear()  # No context
        agents = [
            TestAgent(tenant_id="tenant-1"),
            TestAgent(tenant_id="tenant-2"),
            TestAgent(tenant_id=None),
        ]

        filtered = filter_by_tenant(agents, current_tenant="tenant-2")

        assert len(filtered) == 2
        tenant_ids = [agent.tenant_id for agent in filtered]
        assert "tenant-2" in tenant_ids
        assert None in tenant_ids
