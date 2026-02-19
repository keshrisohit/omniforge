"""Tests for platform management tools.

Tests ListAgentsTool, ListSkillsTool, CreateAgentTool, AddSkillToAgentTool,
and the register_platform_tools factory function.
"""

import pytest

from omniforge.agents.registry import AgentRegistry
from omniforge.storage.memory import InMemoryAgentRepository
from omniforge.tools.base import ToolCallContext
from omniforge.tools.builtin.platform import (
    AddSkillToAgentTool,
    CreateAgentTool,
    ListAgentsTool,
    ListSkillsTool,
    list_all_skills,
    make_agent_id,
    read_skill_meta,
    register_platform_tools,
)
from omniforge.tools.registry import ToolRegistry
from omniforge.tools.types import ToolType

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def registry() -> AgentRegistry:
    return AgentRegistry(repository=InMemoryAgentRepository())


@pytest.fixture
def ctx() -> ToolCallContext:
    return ToolCallContext(
        correlation_id="corr-1",
        task_id="task-1",
        agent_id="master-agent",
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class TestHelpers:
    """Tests for module-level helper functions."""

    def test_make_agent_id_lowercase(self) -> None:
        assert make_agent_id("MyAgent") == "myagent"

    def test_make_agent_id_spaces_to_hyphens(self) -> None:
        assert make_agent_id("My Data Agent") == "my-data-agent"

    def test_make_agent_id_special_chars(self) -> None:
        assert make_agent_id("Agent!!!") == "agent"

    def test_make_agent_id_empty_fallback(self) -> None:
        assert make_agent_id("!!!") == "custom-agent"

    def test_read_skill_meta_nonexistent(self) -> None:
        assert read_skill_meta("nonexistent-skill-xyz-abc") is None

    def test_list_all_skills_returns_list(self) -> None:
        skills = list_all_skills()
        assert isinstance(skills, list)
        for s in skills:
            assert "id" in s
            assert "name" in s
            assert "description" in s


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------


class TestToolDefinitions:
    """Tests that tool definitions are correctly configured."""

    def test_list_agents_definition(self, registry: AgentRegistry) -> None:
        tool = ListAgentsTool(registry)
        defn = tool.definition
        assert defn.name == "list_agents"
        assert defn.type == ToolType.FUNCTION
        assert defn.description

    def test_list_skills_definition(self) -> None:
        tool = ListSkillsTool()
        defn = tool.definition
        assert defn.name == "list_skills"
        assert defn.type == ToolType.FUNCTION

    def test_create_agent_definition(self, registry: AgentRegistry) -> None:
        tool = CreateAgentTool(registry)
        defn = tool.definition
        assert defn.name == "create_agent"
        param_names = [p.name for p in defn.parameters]
        assert "name" in param_names
        assert "purpose" in param_names
        assert "capabilities" in param_names

    def test_add_skill_definition(self, registry: AgentRegistry) -> None:
        tool = AddSkillToAgentTool(registry)
        defn = tool.definition
        assert defn.name == "add_skill_to_agent"
        param_names = [p.name for p in defn.parameters]
        assert "agent_id" in param_names
        assert "skill_id" in param_names

    def test_required_params_on_create_agent(self, registry: AgentRegistry) -> None:
        tool = CreateAgentTool(registry)
        required = [p.name for p in tool.definition.parameters if p.required]
        assert "name" in required
        assert "purpose" in required

    def test_required_params_on_add_skill(self, registry: AgentRegistry) -> None:
        tool = AddSkillToAgentTool(registry)
        required = [p.name for p in tool.definition.parameters if p.required]
        assert "agent_id" in required
        assert "skill_id" in required


# ---------------------------------------------------------------------------
# ListAgentsTool execution
# ---------------------------------------------------------------------------


class TestListAgentsToolExecution:
    """Execution tests for ListAgentsTool."""

    @pytest.mark.asyncio
    async def test_empty_registry(self, registry: AgentRegistry, ctx: ToolCallContext) -> None:
        tool = ListAgentsTool(registry)
        result = await tool.execute(ctx, {})
        assert result.success is True
        assert result.result["count"] == 0
        assert result.result["agents"] == []

    @pytest.mark.asyncio
    async def test_lists_created_agent(self, registry: AgentRegistry, ctx: ToolCallContext) -> None:
        # Create an agent first
        create = CreateAgentTool(registry)
        await create.execute(ctx, {"name": "Alpha", "purpose": "Test"})

        tool = ListAgentsTool(registry)
        result = await tool.execute(ctx, {})
        assert result.success is True
        assert result.result["count"] == 1
        assert result.result["agents"][0]["name"] == "Alpha"

    @pytest.mark.asyncio
    async def test_agent_entry_has_all_fields(
        self, registry: AgentRegistry, ctx: ToolCallContext
    ) -> None:
        create = CreateAgentTool(registry)
        await create.execute(ctx, {"name": "Beta", "purpose": "Field test"})

        tool = ListAgentsTool(registry)
        result = await tool.execute(ctx, {})
        agent = result.result["agents"][0]
        assert "id" in agent
        assert "name" in agent
        assert "description" in agent
        assert "skill_count" in agent


# ---------------------------------------------------------------------------
# ListSkillsTool execution
# ---------------------------------------------------------------------------


class TestListSkillsToolExecution:
    """Execution tests for ListSkillsTool."""

    @pytest.mark.asyncio
    async def test_returns_skills(self, ctx: ToolCallContext) -> None:
        tool = ListSkillsTool()
        result = await tool.execute(ctx, {})
        assert result.success is True
        assert "skills" in result.result
        assert "count" in result.result
        assert result.result["count"] == len(result.result["skills"])

    @pytest.mark.asyncio
    async def test_skill_entries_have_required_fields(self, ctx: ToolCallContext) -> None:
        tool = ListSkillsTool()
        result = await tool.execute(ctx, {})
        for skill in result.result["skills"]:
            assert "id" in skill
            assert "name" in skill
            assert "description" in skill


# ---------------------------------------------------------------------------
# CreateAgentTool execution
# ---------------------------------------------------------------------------


class TestCreateAgentToolExecution:
    """Execution tests for CreateAgentTool."""

    @pytest.mark.asyncio
    async def test_creates_agent_successfully(
        self, registry: AgentRegistry, ctx: ToolCallContext
    ) -> None:
        tool = CreateAgentTool(registry)
        result = await tool.execute(ctx, {"name": "Gamma", "purpose": "Gamma purpose"})
        assert result.success is True
        assert result.result["agent_id"] == "gamma"
        assert result.result["name"] == "Gamma"

    @pytest.mark.asyncio
    async def test_agent_persisted_in_registry(
        self, registry: AgentRegistry, ctx: ToolCallContext
    ) -> None:
        tool = CreateAgentTool(registry)
        await tool.execute(ctx, {"name": "Delta", "purpose": "Delta purpose"})
        agent = await registry.get("delta")
        assert agent.identity.id == "delta"
        assert agent.identity.name == "Delta"

    @pytest.mark.asyncio
    async def test_auto_loads_all_skills(
        self, registry: AgentRegistry, ctx: ToolCallContext
    ) -> None:
        available = list_all_skills()
        tool = CreateAgentTool(registry)
        result = await tool.execute(ctx, {"name": "Epsilon", "purpose": "Skill test"})
        assert result.success is True

        agent = await registry.get("epsilon")
        agent_skill_ids = {s.id for s in agent.skills}
        for lib_skill in available:
            assert lib_skill["id"] in agent_skill_ids

    @pytest.mark.asyncio
    async def test_duplicate_returns_error(
        self, registry: AgentRegistry, ctx: ToolCallContext
    ) -> None:
        tool = CreateAgentTool(registry)
        await tool.execute(ctx, {"name": "Zeta", "purpose": "First"})
        result = await tool.execute(ctx, {"name": "Zeta", "purpose": "Second"})
        assert result.success is False
        assert "already exists" in result.error

    @pytest.mark.asyncio
    async def test_name_with_spaces(self, registry: AgentRegistry, ctx: ToolCallContext) -> None:
        tool = CreateAgentTool(registry)
        result = await tool.execute(ctx, {"name": "My Cool Agent", "purpose": "Spacing"})
        assert result.success is True
        assert result.result["agent_id"] == "my-cool-agent"

    @pytest.mark.asyncio
    async def test_skill_count_in_result(
        self, registry: AgentRegistry, ctx: ToolCallContext
    ) -> None:
        available = list_all_skills()
        tool = CreateAgentTool(registry)
        result = await tool.execute(ctx, {"name": "CountBot", "purpose": "Count test"})
        # skill_count = 1 (general) + len(available library skills)
        assert result.result["skill_count"] == 1 + len(available)

    @pytest.mark.asyncio
    async def test_with_tenant_id(self, registry: AgentRegistry, ctx: ToolCallContext) -> None:
        tool = CreateAgentTool(registry, tenant_id="acme-corp")
        result = await tool.execute(ctx, {"name": "TenantBot", "purpose": "Tenant test"})
        assert result.success is True


# ---------------------------------------------------------------------------
# AddSkillToAgentTool execution
# ---------------------------------------------------------------------------


class TestAddSkillToAgentToolExecution:
    """Execution tests for AddSkillToAgentTool."""

    @pytest.mark.asyncio
    async def test_missing_agent_id(self, registry: AgentRegistry, ctx: ToolCallContext) -> None:
        tool = AddSkillToAgentTool(registry)
        result = await tool.execute(ctx, {"agent_id": "", "skill_id": "pdf"})
        assert result.success is False
        assert "agent_id" in result.error.lower()

    @pytest.mark.asyncio
    async def test_missing_skill_id(self, registry: AgentRegistry, ctx: ToolCallContext) -> None:
        tool = AddSkillToAgentTool(registry)
        result = await tool.execute(ctx, {"agent_id": "my-agent", "skill_id": ""})
        assert result.success is False
        assert "skill_id" in result.error.lower()

    @pytest.mark.asyncio
    async def test_nonexistent_skill(self, registry: AgentRegistry, ctx: ToolCallContext) -> None:
        tool = AddSkillToAgentTool(registry)
        result = await tool.execute(
            ctx, {"agent_id": "any-agent", "skill_id": "nonexistent-skill-xyz"}
        )
        assert result.success is False
        assert "not found" in result.error.lower()


# ---------------------------------------------------------------------------
# register_platform_tools factory
# ---------------------------------------------------------------------------


class TestRegisterPlatformTools:
    """Tests for the register_platform_tools factory function."""

    def test_registers_all_four_tools(self, registry: AgentRegistry) -> None:
        tool_registry = ToolRegistry()
        register_platform_tools(tool_registry, registry)
        names = set(tool_registry.list_tools())
        assert "list_agents" in names
        assert "list_skills" in names
        assert "create_agent" in names
        assert "add_skill_to_agent" in names

    def test_registers_with_tenant_id(self, registry: AgentRegistry) -> None:
        """Factory accepts optional tenant_id without error."""
        tool_registry = ToolRegistry()
        register_platform_tools(tool_registry, registry, tenant_id="test-tenant")
        assert "create_agent" in tool_registry.list_tools()

    def test_duplicate_registration_raises(self, registry: AgentRegistry) -> None:
        """Registering tools twice into the same registry should raise."""
        from omniforge.tools.errors import ToolAlreadyRegisteredError

        tool_registry = ToolRegistry()
        register_platform_tools(tool_registry, registry)
        with pytest.raises(ToolAlreadyRegisteredError):
            register_platform_tools(tool_registry, registry)
