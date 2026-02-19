"""Tests for agent discovery service."""

import pytest

from omniforge.agents.base import BaseAgent
from omniforge.agents.models import (
    AgentCapabilities,
    AgentIdentity,
    AgentSkill,
    SkillInputMode,
    SkillOutputMode,
)
from omniforge.agents.registry import AgentRegistry
from omniforge.orchestration.discovery import AgentDiscoveryService
from omniforge.storage.memory import InMemoryAgentRepository
from omniforge.tasks.models import Task


class DataAgent(BaseAgent):
    """Test agent with data analysis skills."""

    identity = AgentIdentity(
        id="data-agent",
        name="Data Agent",
        description="Data analysis agent",
        version="1.0.0",
    )

    capabilities = AgentCapabilities(streaming=True, multi_turn=False)

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


class MLAgent(BaseAgent):
    """Test agent with ML skills."""

    identity = AgentIdentity(
        id="ml-agent",
        name="ML Agent",
        description="Machine learning agent",
        version="2.0.0",
    )

    capabilities = AgentCapabilities(streaming=True, multi_turn=True, hitl_support=True)

    skills = [
        AgentSkill(
            id="model-training",
            name="Model Training",
            description="Train ML models",
            tags=["ml", "training"],
            input_modes=[SkillInputMode.STRUCTURED],
            output_modes=[SkillOutputMode.ARTIFACT],
        ),
    ]

    async def process_task(self, task: Task):
        """Stub implementation."""
        yield


class TextAgent(BaseAgent):
    """Test agent with text processing skills."""

    identity = AgentIdentity(
        id="text-agent",
        name="Text Agent",
        description="Text processing agent",
        version="1.0.0",
    )

    capabilities = AgentCapabilities(streaming=False, multi_turn=True)

    skills = [
        AgentSkill(
            id="text-summarization",
            name="Text Summarization",
            description="Summarize text",
            tags=["nlp", "text"],
            input_modes=[SkillInputMode.TEXT],
            output_modes=[SkillOutputMode.TEXT],
        ),
    ]

    async def process_task(self, task: Task):
        """Stub implementation."""
        yield


class TestAgentDiscoveryService:
    """Tests for AgentDiscoveryService class."""

    @pytest.fixture
    def repository(self):
        """Create an in-memory repository for testing."""
        return InMemoryAgentRepository()

    @pytest.fixture
    def registry(self, repository):
        """Create a registry instance for testing."""
        return AgentRegistry(repository=repository)

    @pytest.fixture
    def discovery(self, registry):
        """Create a discovery service instance for testing."""
        return AgentDiscoveryService(registry=registry)

    @pytest.mark.asyncio
    async def test_find_by_skill(self, discovery, registry):
        """Should find agents with specific skill."""
        data_agent = DataAgent()
        ml_agent = MLAgent()
        text_agent = TextAgent()

        await registry.register(data_agent)
        await registry.register(ml_agent)
        await registry.register(text_agent)

        # Find data analysis skill
        matching = await discovery.find_by_skill("data-analysis")

        assert len(matching) == 1
        assert matching[0].identity.id == "data-agent"

    @pytest.mark.asyncio
    async def test_find_by_skill_no_matches(self, discovery, registry):
        """Should return empty list when no agents have the skill."""
        data_agent = DataAgent()
        await registry.register(data_agent)

        matching = await discovery.find_by_skill("nonexistent-skill")

        assert matching == []

    @pytest.mark.asyncio
    async def test_find_by_tag(self, discovery, registry):
        """Should find agents with specific tag."""
        data_agent = DataAgent()
        ml_agent = MLAgent()
        text_agent = TextAgent()

        await registry.register(data_agent)
        await registry.register(ml_agent)
        await registry.register(text_agent)

        # Find ML tag
        matching = await discovery.find_by_tag("ml")

        assert len(matching) == 1
        assert matching[0].identity.id == "ml-agent"

    @pytest.mark.asyncio
    async def test_find_by_tag_multiple_matches(self, discovery, registry):
        """Should find all agents with specific tag."""
        data_agent = DataAgent()
        text_agent = TextAgent()

        await registry.register(data_agent)
        await registry.register(text_agent)

        # Both have different tags, so test with specific one
        matching = await discovery.find_by_tag("nlp")

        assert len(matching) == 1
        assert matching[0].identity.id == "text-agent"

    @pytest.mark.asyncio
    async def test_find_by_capability_streaming(self, discovery, registry):
        """Should find agents with streaming capability."""
        data_agent = DataAgent()
        ml_agent = MLAgent()
        text_agent = TextAgent()

        await registry.register(data_agent)
        await registry.register(ml_agent)
        await registry.register(text_agent)

        # Find streaming agents
        matching = await discovery.find_by_capability("streaming")

        assert len(matching) == 2
        agent_ids = {agent.identity.id for agent in matching}
        assert agent_ids == {"data-agent", "ml-agent"}

    @pytest.mark.asyncio
    async def test_find_by_capability_multi_turn(self, discovery, registry):
        """Should find agents with multi-turn capability."""
        data_agent = DataAgent()
        ml_agent = MLAgent()
        text_agent = TextAgent()

        await registry.register(data_agent)
        await registry.register(ml_agent)
        await registry.register(text_agent)

        # Find multi-turn agents
        matching = await discovery.find_by_capability("multi_turn")

        assert len(matching) == 2
        agent_ids = {agent.identity.id for agent in matching}
        assert agent_ids == {"ml-agent", "text-agent"}

    @pytest.mark.asyncio
    async def test_find_by_capability_hitl_support(self, discovery, registry):
        """Should find agents with HITL support capability."""
        data_agent = DataAgent()
        ml_agent = MLAgent()

        await registry.register(data_agent)
        await registry.register(ml_agent)

        # Find HITL agents
        matching = await discovery.find_by_capability("hitl_support")

        assert len(matching) == 1
        assert matching[0].identity.id == "ml-agent"

    @pytest.mark.asyncio
    async def test_find_by_capability_no_matches(self, discovery, registry):
        """Should return empty list when no agents have capability."""
        data_agent = DataAgent()
        await registry.register(data_agent)

        # Find push_notifications capability (no agent has it)
        matching = await discovery.find_by_capability("push_notifications")

        assert matching == []

    @pytest.mark.asyncio
    async def test_get_agent_card(self, discovery, registry):
        """Should retrieve agent card successfully."""
        ml_agent = MLAgent()
        await registry.register(ml_agent)

        card = await discovery.get_agent_card("ml-agent")

        assert card.identity.id == "ml-agent"
        assert card.identity.name == "ML Agent"
        assert len(card.skills) == 1
        assert card.skills[0].id == "model-training"

    @pytest.mark.asyncio
    async def test_get_agent_card_nonexistent_raises_error(self, discovery):
        """Should raise AgentNotFoundError for nonexistent agent."""
        from omniforge.agents.errors import AgentNotFoundError

        with pytest.raises(AgentNotFoundError):
            await discovery.get_agent_card("nonexistent-agent")

    @pytest.mark.asyncio
    async def test_find_best_agent_for_skill(self, discovery, registry):
        """Should return the best agent for a skill."""
        data_agent = DataAgent()
        ml_agent = MLAgent()

        await registry.register(data_agent)
        await registry.register(ml_agent)

        # Find best agent for data-analysis
        best = await discovery.find_best_agent_for_skill("data-analysis")

        assert best is not None
        assert best.identity.id == "data-agent"

    @pytest.mark.asyncio
    async def test_find_best_agent_for_skill_no_match(self, discovery, registry):
        """Should return None when no agent has the skill."""
        data_agent = DataAgent()
        await registry.register(data_agent)

        best = await discovery.find_best_agent_for_skill("nonexistent-skill")

        assert best is None

    @pytest.mark.asyncio
    async def test_discovery_with_tenant_isolation(self, repository):
        """Discovery service should respect tenant isolation."""

        class TenantDataAgent1(BaseAgent):
            identity = AgentIdentity(
                id="tenant-data-agent-1",
                name="Tenant Data Agent 1",
                description="Tenant-specific data agent 1",
                version="1.0.0",
            )
            capabilities = AgentCapabilities()
            skills = [
                AgentSkill(
                    id="tenant-analysis",
                    name="Tenant Analysis",
                    description="Analysis for tenant",
                    input_modes=[SkillInputMode.TEXT],
                    output_modes=[SkillOutputMode.TEXT],
                )
            ]

            def __init__(self, tenant_id: str):
                super().__init__()
                self.tenant_id = tenant_id

            async def process_task(self, task: Task):
                yield

        class TenantDataAgent2(BaseAgent):
            identity = AgentIdentity(
                id="tenant-data-agent-2",
                name="Tenant Data Agent 2",
                description="Tenant-specific data agent 2",
                version="1.0.0",
            )
            capabilities = AgentCapabilities()
            skills = [
                AgentSkill(
                    id="tenant-analysis",
                    name="Tenant Analysis",
                    description="Analysis for tenant",
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
        agent1 = TenantDataAgent1(tenant_id="tenant-1")
        agent2 = TenantDataAgent2(tenant_id="tenant-2")

        await repository.save(agent1)
        await repository.save(agent2)

        # Create discovery with tenant isolation
        tenant_registry = AgentRegistry(repository=repository, tenant_id="tenant-1")
        tenant_discovery = AgentDiscoveryService(registry=tenant_registry)

        # Should only find agents for tenant-1
        agents = await tenant_discovery.find_by_skill("tenant-analysis")

        assert len(agents) == 1
        assert agents[0].tenant_id == "tenant-1"
