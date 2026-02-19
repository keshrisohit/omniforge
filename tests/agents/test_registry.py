"""Tests for agent registry module."""

import pytest

from omniforge.agents.base import BaseAgent
from omniforge.agents.errors import AgentNotFoundError
from omniforge.agents.models import (
    AgentCapabilities,
    AgentIdentity,
    AgentSkill,
    SkillInputMode,
    SkillOutputMode,
)
from omniforge.agents.registry import AgentRegistry
from omniforge.storage.memory import InMemoryAgentRepository
from omniforge.tasks.models import Task


class SimpleTestAgent(BaseAgent):
    """Concrete test agent implementation."""

    identity = AgentIdentity(
        id="test-agent",
        name="Test Agent",
        description="Agent for testing",
        version="1.0.0",
    )

    capabilities = AgentCapabilities(streaming=True, multi_turn=True)

    skills = [
        AgentSkill(
            id="skill-1",
            name="Skill One",
            description="First test skill",
            tags=["test", "basic"],
            input_modes=[SkillInputMode.TEXT],
            output_modes=[SkillOutputMode.TEXT],
        ),
        AgentSkill(
            id="skill-2",
            name="Skill Two",
            description="Second test skill",
            tags=["test", "advanced"],
            input_modes=[SkillInputMode.TEXT],
            output_modes=[SkillOutputMode.TEXT],
        ),
    ]

    async def process_task(self, task: Task):
        """Stub implementation."""
        yield  # Make it an async generator


class AnalyticsAgent(BaseAgent):
    """Analytics agent for testing."""

    identity = AgentIdentity(
        id="analytics-agent",
        name="Analytics Agent",
        description="Data analytics agent",
        version="1.0.0",
    )

    capabilities = AgentCapabilities(streaming=False)

    skills = [
        AgentSkill(
            id="data-analysis",
            name="Data Analysis",
            description="Analyze datasets",
            tags=["analytics", "data"],
            input_modes=[SkillInputMode.STRUCTURED],
            output_modes=[SkillOutputMode.STRUCTURED],
        ),
    ]

    async def process_task(self, task: Task):
        """Stub implementation."""
        yield


class NLPAgent(BaseAgent):
    """NLP agent for testing."""

    identity = AgentIdentity(
        id="nlp-agent",
        name="NLP Agent",
        description="Natural language processing agent",
        version="2.0.0",
    )

    capabilities = AgentCapabilities(streaming=True)

    skills = [
        AgentSkill(
            id="text-analysis",
            name="Text Analysis",
            description="Analyze text content",
            tags=["nlp", "text"],
            input_modes=[SkillInputMode.TEXT],
            output_modes=[SkillOutputMode.TEXT],
        ),
        AgentSkill(
            id="sentiment-analysis",
            name="Sentiment Analysis",
            description="Detect sentiment in text",
            tags=["nlp", "sentiment"],
            input_modes=[SkillInputMode.TEXT],
            output_modes=[SkillOutputMode.STRUCTURED],
        ),
    ]

    async def process_task(self, task: Task):
        """Stub implementation."""
        yield


class TestAgentRegistry:
    """Tests for AgentRegistry class."""

    @pytest.fixture
    def repository(self):
        """Create an in-memory repository for testing."""
        return InMemoryAgentRepository()

    @pytest.fixture
    def registry(self, repository):
        """Create a registry instance for testing."""
        return AgentRegistry(repository=repository)

    @pytest.mark.asyncio
    async def test_register_agent(self, registry):
        """Agent should be successfully registered."""
        agent = SimpleTestAgent()

        await registry.register(agent)

        # Verify agent can be retrieved
        retrieved = await registry.get(agent.identity.id)
        assert retrieved is agent
        assert retrieved.identity.id == "test-agent"

    @pytest.mark.asyncio
    async def test_register_duplicate_agent_raises_error(self, registry):
        """Registering agent with duplicate ID should raise ValueError."""
        agent1 = SimpleTestAgent()
        agent2 = SimpleTestAgent()

        await registry.register(agent1)

        with pytest.raises(ValueError, match="already exists"):
            await registry.register(agent2)

    @pytest.mark.asyncio
    async def test_get_agent_by_id(self, registry):
        """Agent should be retrievable by ID."""
        agent = SimpleTestAgent()
        await registry.register(agent)

        retrieved = await registry.get(agent.identity.id)

        assert retrieved is agent
        assert retrieved.identity.id == agent.identity.id

    @pytest.mark.asyncio
    async def test_get_nonexistent_agent_raises_error(self, registry):
        """Getting nonexistent agent should raise AgentNotFoundError."""
        nonexistent_id = "nonexistent-agent"

        with pytest.raises(AgentNotFoundError) as exc_info:
            await registry.get(nonexistent_id)

        assert nonexistent_id in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_unregister_agent(self, registry):
        """Agent should be successfully unregistered."""
        agent = SimpleTestAgent()
        await registry.register(agent)

        await registry.unregister(agent.identity.id)

        # Verify agent is no longer retrievable
        with pytest.raises(AgentNotFoundError):
            await registry.get(agent.identity.id)

    @pytest.mark.asyncio
    async def test_unregister_nonexistent_agent_raises_error(self, registry):
        """Unregistering nonexistent agent should raise AgentNotFoundError."""
        nonexistent_id = "nonexistent-agent"

        with pytest.raises(AgentNotFoundError):
            await registry.unregister(nonexistent_id)

    @pytest.mark.asyncio
    async def test_list_all_agents(self, registry):
        """All registered agents should be returned."""
        agent1 = SimpleTestAgent()
        agent2 = AnalyticsAgent()
        agent3 = NLPAgent()

        await registry.register(agent1)
        await registry.register(agent2)
        await registry.register(agent3)

        agents = await registry.list_all()

        assert len(agents) == 3
        agent_ids = {agent.identity.id for agent in agents}
        assert agent_ids == {"test-agent", "analytics-agent", "nlp-agent"}

    @pytest.mark.asyncio
    async def test_list_all_empty_registry(self, registry):
        """Empty registry should return empty list."""
        agents = await registry.list_all()

        assert agents == []

    @pytest.mark.asyncio
    async def test_find_by_skill_single_match(self, registry):
        """Should find agent with specific skill."""
        agent1 = SimpleTestAgent()
        agent2 = AnalyticsAgent()
        agent3 = NLPAgent()

        await registry.register(agent1)
        await registry.register(agent2)
        await registry.register(agent3)

        # Find agents with data-analysis skill
        matching = await registry.find_by_skill("data-analysis")

        assert len(matching) == 1
        assert matching[0].identity.id == "analytics-agent"

    @pytest.mark.asyncio
    async def test_find_by_skill_multiple_matches(self, registry):
        """Should find all agents with specific skill."""
        agent1 = SimpleTestAgent()
        agent2 = AnalyticsAgent()

        await registry.register(agent1)
        await registry.register(agent2)

        # Find agents with skill-1
        matching = await registry.find_by_skill("skill-1")

        assert len(matching) == 1
        assert matching[0].identity.id == "test-agent"

    @pytest.mark.asyncio
    async def test_find_by_skill_no_matches(self, registry):
        """Should return empty list when no agents have the skill."""
        agent1 = SimpleTestAgent()
        await registry.register(agent1)

        matching = await registry.find_by_skill("nonexistent-skill")

        assert matching == []

    @pytest.mark.asyncio
    async def test_find_by_skill_empty_registry(self, registry):
        """Should return empty list when registry is empty."""
        matching = await registry.find_by_skill("any-skill")

        assert matching == []

    @pytest.mark.asyncio
    async def test_find_by_tag_single_match(self, registry):
        """Should find agents with specific tag."""
        agent1 = SimpleTestAgent()
        agent2 = AnalyticsAgent()
        agent3 = NLPAgent()

        await registry.register(agent1)
        await registry.register(agent2)
        await registry.register(agent3)

        # Find agents with analytics tag
        matching = await registry.find_by_tag("analytics")

        assert len(matching) == 1
        assert matching[0].identity.id == "analytics-agent"

    @pytest.mark.asyncio
    async def test_find_by_tag_multiple_matches(self, registry):
        """Should find all agents with specific tag."""
        agent1 = SimpleTestAgent()
        agent2 = AnalyticsAgent()
        agent3 = NLPAgent()

        await registry.register(agent1)
        await registry.register(agent2)
        await registry.register(agent3)

        # Find agents with nlp tag
        matching = await registry.find_by_tag("nlp")

        assert len(matching) == 1
        assert matching[0].identity.id == "nlp-agent"

    @pytest.mark.asyncio
    async def test_find_by_tag_shared_tag(self, registry):
        """Should find all agents that share a tag."""
        agent1 = SimpleTestAgent()
        agent2 = NLPAgent()

        await registry.register(agent1)
        await registry.register(agent2)

        # Both agents have skills with "test" or "text" tag
        # TestAgent has "test", NLPAgent has "text"
        # Let's search for "test" which only TestAgent has
        matching = await registry.find_by_tag("test")

        assert len(matching) == 1
        assert matching[0].identity.id == "test-agent"

    @pytest.mark.asyncio
    async def test_find_by_tag_no_matches(self, registry):
        """Should return empty list when no agents have the tag."""
        agent1 = SimpleTestAgent()
        await registry.register(agent1)

        matching = await registry.find_by_tag("nonexistent-tag")

        assert matching == []

    @pytest.mark.asyncio
    async def test_find_by_tag_empty_registry(self, registry):
        """Should return empty list when registry is empty."""
        matching = await registry.find_by_tag("any-tag")

        assert matching == []

    @pytest.mark.asyncio
    async def test_find_by_tag_agent_with_no_tags(self, registry):
        """Should not match agents with skills that have no tags."""

        class NoTagAgent(BaseAgent):
            identity = AgentIdentity(
                id="no-tag-agent",
                name="No Tag Agent",
                description="Agent with no tags",
                version="1.0.0",
            )
            capabilities = AgentCapabilities()
            skills = [
                AgentSkill(
                    id="no-tag-skill",
                    name="No Tag Skill",
                    description="Skill without tags",
                    tags=None,
                    input_modes=[SkillInputMode.TEXT],
                    output_modes=[SkillOutputMode.TEXT],
                )
            ]

            async def process_task(self, task: Task):
                yield

        agent = NoTagAgent()
        await registry.register(agent)

        matching = await registry.find_by_tag("any-tag")

        assert matching == []

    @pytest.mark.asyncio
    async def test_registry_with_tenant_isolation(self, repository):
        """Registry should filter agents by tenant when tenant_id is provided."""

        # Create tenant-aware agents with unique IDs
        class TenantAgent1(BaseAgent):
            identity = AgentIdentity(
                id="tenant-agent-1",
                name="Tenant Agent 1",
                description="Tenant-specific agent 1",
                version="1.0.0",
            )
            capabilities = AgentCapabilities()
            skills = [
                AgentSkill(
                    id="tenant-skill",
                    name="Tenant Skill",
                    description="Skill for tenant",
                    input_modes=[SkillInputMode.TEXT],
                    output_modes=[SkillOutputMode.TEXT],
                )
            ]

            def __init__(self, tenant_id: str):
                super().__init__()
                self.tenant_id = tenant_id

            async def process_task(self, task: Task):
                yield

        class TenantAgent2(BaseAgent):
            identity = AgentIdentity(
                id="tenant-agent-2",
                name="Tenant Agent 2",
                description="Tenant-specific agent 2",
                version="1.0.0",
            )
            capabilities = AgentCapabilities()
            skills = [
                AgentSkill(
                    id="tenant-skill",
                    name="Tenant Skill",
                    description="Skill for tenant",
                    input_modes=[SkillInputMode.TEXT],
                    output_modes=[SkillOutputMode.TEXT],
                )
            ]

            def __init__(self, tenant_id: str):
                super().__init__()
                self.tenant_id = tenant_id

            async def process_task(self, task: Task):
                yield

        # Register agents for different tenants
        agent1 = TenantAgent1(tenant_id="tenant-1")
        agent2 = TenantAgent2(tenant_id="tenant-2")
        agent3 = SimpleTestAgent()  # No tenant

        await repository.save(agent1)
        await repository.save(agent2)
        await repository.save(agent3)

        # Create registry with tenant isolation
        tenant_registry = AgentRegistry(repository=repository, tenant_id="tenant-1")

        agents = await tenant_registry.list_all()

        # Should only return agents for tenant-1
        assert len(agents) == 1
        assert agents[0].tenant_id == "tenant-1"

    @pytest.mark.asyncio
    async def test_registry_without_tenant_lists_all(self, repository):
        """Registry without tenant_id should list all agents."""

        class TenantAgentA(BaseAgent):
            identity = AgentIdentity(
                id="tenant-agent-a",
                name="Tenant Agent A",
                description="Tenant-specific agent A",
                version="1.0.0",
            )
            capabilities = AgentCapabilities()
            skills = [
                AgentSkill(
                    id="tenant-skill",
                    name="Tenant Skill",
                    description="Skill for tenant",
                    input_modes=[SkillInputMode.TEXT],
                    output_modes=[SkillOutputMode.TEXT],
                )
            ]

            def __init__(self, tenant_id: str):
                super().__init__()
                self.tenant_id = tenant_id

            async def process_task(self, task: Task):
                yield

        class TenantAgentB(BaseAgent):
            identity = AgentIdentity(
                id="tenant-agent-b",
                name="Tenant Agent B",
                description="Tenant-specific agent B",
                version="1.0.0",
            )
            capabilities = AgentCapabilities()
            skills = [
                AgentSkill(
                    id="tenant-skill",
                    name="Tenant Skill",
                    description="Skill for tenant",
                    input_modes=[SkillInputMode.TEXT],
                    output_modes=[SkillOutputMode.TEXT],
                )
            ]

            def __init__(self, tenant_id: str):
                super().__init__()
                self.tenant_id = tenant_id

            async def process_task(self, task: Task):
                yield

        agent1 = TenantAgentA(tenant_id="tenant-1")
        agent2 = TenantAgentB(tenant_id="tenant-2")
        agent3 = SimpleTestAgent()

        await repository.save(agent1)
        await repository.save(agent2)
        await repository.save(agent3)

        # Create registry without tenant isolation
        global_registry = AgentRegistry(repository=repository)

        agents = await global_registry.list_all()

        # Should return all agents
        assert len(agents) == 3
