"""Platform management tools for OmniForge agents.

These tools allow the Master Agent to perform platform operations via the
ReAct reasoning loop: listing agents, creating agents, and managing skills.
All platform state operations are handled through the AgentRegistry.
"""

import os
import re
import time
from typing import Any, Callable, Optional

from omniforge.tools.base import (
    BaseTool,
    ParameterType,
    ToolCallContext,
    ToolDefinition,
    ToolParameter,
    ToolResult,
)
from omniforge.tools.registry import ToolRegistry
from omniforge.tools.types import ToolType

# ---------------------------------------------------------------------------
# Shared skill-library helpers (module-level, importable by other modules)
# ---------------------------------------------------------------------------


def _skills_dir() -> str:
    """Return the absolute path to the skills directory."""
    return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "skills")


def read_skill_meta(skill_id: str) -> Optional[dict]:
    """Read name and description from a skill's SKILL.md frontmatter.

    Args:
        skill_id: Directory name of the skill (e.g. "pdf", "data-processor")

    Returns:
        Dict with ``id``, ``name``, ``description`` keys, or None if not found.
    """
    skill_md = os.path.join(_skills_dir(), skill_id, "SKILL.md")
    if not os.path.exists(skill_md):
        return None
    try:
        with open(skill_md) as f:
            content = f.read()
        name = skill_id
        description = ""
        if content.startswith("---"):
            end = content.find("---", 3)
            if end > 0:
                for line in content[3:end].splitlines():
                    if line.startswith("name:"):
                        name = line[5:].strip()
                    elif line.startswith("description:"):
                        description = line[12:].strip()
        return {"id": skill_id, "name": name, "description": description}
    except Exception:
        return None


def list_all_skills() -> list[dict]:
    """List all skills available in the OmniForge skills library.

    Returns:
        List of dicts with ``id``, ``name``, ``description`` keys,
        sorted alphabetically by skill ID.
    """
    skills_dir = _skills_dir()
    if not os.path.exists(skills_dir):
        return []
    skills = []
    try:
        for entry in sorted(os.scandir(skills_dir), key=lambda e: e.name):
            if entry.is_dir():
                meta = read_skill_meta(entry.name)
                if meta:
                    skills.append(meta)
    except Exception:
        pass
    return skills


def make_agent_id(name: str) -> str:
    """Convert a human-readable agent name to a valid kebab-case ID.

    Args:
        name: Raw agent name from user input

    Returns:
        Kebab-case string safe to use as an agent identifier
    """
    agent_id = name.lower().strip()
    agent_id = re.sub(r"[^a-z0-9]+", "-", agent_id)
    return agent_id.strip("-") or "custom-agent"


# ---------------------------------------------------------------------------
# Platform tool implementations
# ---------------------------------------------------------------------------


class ListAgentsTool(BaseTool):
    """Tool to list all registered agents in the OmniForge platform."""

    def __init__(self, agent_registry: Any) -> None:
        """Initialize with the agent registry.

        Args:
            agent_registry: AgentRegistry instance for agent discovery
        """
        self._registry = agent_registry

    @property
    def definition(self) -> ToolDefinition:
        """Get tool definition."""
        return ToolDefinition(
            name="list_agents",
            type=ToolType.FUNCTION,
            description=(
                "List all agents registered in the OmniForge platform. "
                "Returns agent IDs, names, descriptions, and skill counts. "
                "Use this before creating a new agent to avoid duplicates."
            ),
            parameters=[],
            timeout_ms=10000,
        )

    async def execute(self, context: ToolCallContext, arguments: dict[str, Any]) -> ToolResult:
        """List all registered agents.

        Args:
            context: Execution context
            arguments: Not used

        Returns:
            ToolResult with list of agents
        """
        start = time.time()
        try:
            agents = await self._registry.list_all()
            agent_list = [
                {
                    "id": a.identity.id,
                    "name": a.identity.name,
                    "description": a.identity.description,
                    "skill_count": len(getattr(a, "skills", [])),
                }
                for a in agents
            ]
            return ToolResult(
                success=True,
                result={"agents": agent_list, "count": len(agent_list)},
                duration_ms=int((time.time() - start) * 1000),
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Failed to list agents: {str(e)}",
                duration_ms=int((time.time() - start) * 1000),
            )


class ListSkillsTool(BaseTool):
    """Tool to list all skills available in the skills library."""

    @property
    def definition(self) -> ToolDefinition:
        """Get tool definition."""
        return ToolDefinition(
            name="list_skills",
            type=ToolType.FUNCTION,
            description=(
                "List all skills available in the OmniForge skills library. "
                "Returns skill IDs, names, and descriptions. "
                "Use this to discover what skills can be added to agents."
            ),
            parameters=[],
            timeout_ms=10000,
        )

    async def execute(self, context: ToolCallContext, arguments: dict[str, Any]) -> ToolResult:
        """List all available skills.

        Args:
            context: Execution context
            arguments: Not used

        Returns:
            ToolResult with list of skills
        """
        start = time.time()
        skills = list_all_skills()
        return ToolResult(
            success=True,
            result={"skills": skills, "count": len(skills)},
            duration_ms=int((time.time() - start) * 1000),
        )


class CreateAgentTool(BaseTool):
    """Tool to create and register a new agent in the OmniForge platform."""

    def __init__(self, agent_registry: Any, tenant_id: Optional[str] = None) -> None:
        """Initialize with the agent registry.

        Args:
            agent_registry: AgentRegistry instance for registering agents
            tenant_id: Optional tenant ID for multi-tenant isolation
        """
        self._registry = agent_registry
        self._tenant_id = tenant_id

    @property
    def definition(self) -> ToolDefinition:
        """Get tool definition."""
        return ToolDefinition(
            name="create_agent",
            type=ToolType.FUNCTION,
            description=(
                "Create and register a new agent in the OmniForge platform. "
                "The agent automatically receives all available skills. "
                "Use this when the user wants to build a new agent."
            ),
            parameters=[
                ToolParameter(
                    name="name",
                    type=ParameterType.STRING,
                    description="The agent's display name (e.g., 'Data Processor Bot')",
                    required=True,
                ),
                ToolParameter(
                    name="purpose",
                    type=ParameterType.STRING,
                    description="What this agent does — its main goal or purpose",
                    required=True,
                ),
                ToolParameter(
                    name="capabilities",
                    type=ParameterType.STRING,
                    description=(
                        "Comma-separated capabilities or skills the agent needs "
                        "(e.g., 'data analysis, PDF processing, reporting')"
                    ),
                    required=False,
                    default="general assistance",
                ),
            ],
            timeout_ms=30000,
        )

    async def execute(self, context: ToolCallContext, arguments: dict[str, Any]) -> ToolResult:
        """Create and register a new agent.

        Args:
            context: Execution context
            arguments: Dict with name, purpose, capabilities keys

        Returns:
            ToolResult with created agent info or error
        """
        start = time.time()

        # Lazy imports to avoid circular dependencies at module load time
        from omniforge.agents.autonomous_simple import SimpleAutonomousAgent
        from omniforge.agents.models import (
            AgentCapabilities,
            AgentIdentity,
            AgentSkill,
            SkillInputMode,
            SkillOutputMode,
        )

        name = (arguments.get("name") or "Custom Agent").strip()
        purpose = (arguments.get("purpose") or "A custom AI agent").strip()
        capabilities_str = (arguments.get("capabilities") or "general assistance").strip()

        agent_id = make_agent_id(name)

        # Detect duplicates before creating
        try:
            existing = await self._registry.get(agent_id)
            if existing:
                return ToolResult(
                    success=False,
                    error=f"An agent with ID '{agent_id}' already exists.",
                    duration_ms=int((time.time() - start) * 1000),
                )
        except Exception:
            pass  # AgentNotFoundError means it doesn't exist — proceed

        identity = AgentIdentity(
            id=agent_id,
            name=name,
            description=purpose,
            version="1.0.0",
        )
        agent_capabilities = AgentCapabilities(
            streaming=True,
            multi_turn=True,
            push_notifications=False,
            hitl_support=False,
        )

        # Auto-load all skills from the library so the agent can use them
        all_skill_metas = list_all_skills()
        library_skills = [
            AgentSkill(
                id=s["id"],
                name=s["name"],
                description=s["description"],
                input_modes=[SkillInputMode.TEXT],
                output_modes=[SkillOutputMode.TEXT],
            )
            for s in all_skill_metas
        ]

        # Always include a general capability skill describing the agent's purpose
        general_skill = AgentSkill(
            id=f"{agent_id}-general",
            name=f"{name} General Capability",
            description=f"{purpose}. Capabilities: {capabilities_str}",
            input_modes=[SkillInputMode.TEXT],
            output_modes=[SkillOutputMode.TEXT],
        )
        agent_skills = [general_skill] + library_skills

        # Build a system prompt that includes skill catalog awareness
        skills_catalog = "\n".join(
            f"- {s['name']}: {s['description'][:80]}" for s in all_skill_metas[:10]
        )
        system_prompt = (
            f"You are {name}. {purpose}\n\n"
            f"Your capabilities include: {capabilities_str}\n\n"
            f"Available skills you can use:\n{skills_catalog}\n\n"
            "Assist users with tasks related to your purpose. "
            "Be helpful, focused, and concise."
        )

        # Create dynamic subclass of SimpleAutonomousAgent with custom identity
        class_name = "Agent_" + re.sub(r"[^a-zA-Z0-9]", "_", agent_id)
        dynamic_agent_class = type(
            class_name,
            (SimpleAutonomousAgent,),
            {
                "identity": identity,
                "capabilities": agent_capabilities,
                "skills": agent_skills,
            },
        )

        # Use the env-configured default model so agents work with the project's LLM setup
        from omniforge.llm.config import load_config_from_env

        llm_config = load_config_from_env()
        agent_instance = dynamic_agent_class(
            system_prompt=system_prompt,
            tenant_id=self._tenant_id or "local",
            model=llm_config.default_model,
        )

        try:
            await self._registry.register(agent_instance)
            return ToolResult(
                success=True,
                result={
                    "agent_id": agent_id,
                    "name": name,
                    "skill_count": len(agent_skills),
                    "message": (
                        f"Agent '{name}' created successfully with ID '{agent_id}'. "
                        f"{len(agent_skills)} skills auto-loaded."
                    ),
                },
                duration_ms=int((time.time() - start) * 1000),
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                duration_ms=int((time.time() - start) * 1000),
            )


class AddSkillToAgentTool(BaseTool):
    """Tool to explicitly add a specific skill to an existing agent."""

    def __init__(self, agent_registry: Any) -> None:
        """Initialize with the agent registry.

        Args:
            agent_registry: AgentRegistry instance for agent updates
        """
        self._registry = agent_registry

    @property
    def definition(self) -> ToolDefinition:
        """Get tool definition."""
        return ToolDefinition(
            name="add_skill_to_agent",
            type=ToolType.FUNCTION,
            description=(
                "Explicitly add a specific skill to an existing agent. "
                "Note: all skills are automatically available to agents by default — "
                "use this only for explicit/manual skill assignment. "
                "Use list_agents to find agent IDs and list_skills for skill IDs."
            ),
            parameters=[
                ToolParameter(
                    name="agent_id",
                    type=ParameterType.STRING,
                    description="The target agent's ID (use list_agents to find it)",
                    required=True,
                ),
                ToolParameter(
                    name="skill_id",
                    type=ParameterType.STRING,
                    description="The skill ID to add (use list_skills to find it)",
                    required=True,
                ),
            ],
            timeout_ms=15000,
        )

    async def execute(self, context: ToolCallContext, arguments: dict[str, Any]) -> ToolResult:
        """Add a skill to an agent.

        Args:
            context: Execution context
            arguments: Dict with agent_id and skill_id keys

        Returns:
            ToolResult with success status or error
        """
        start = time.time()

        from omniforge.agents.models import AgentSkill, SkillInputMode, SkillOutputMode

        agent_id = (arguments.get("agent_id") or "").strip()
        skill_id = (arguments.get("skill_id") or "").strip()

        if not agent_id:
            return ToolResult(
                success=False,
                error="agent_id is required.",
                duration_ms=int((time.time() - start) * 1000),
            )
        if not skill_id:
            return ToolResult(
                success=False,
                error="skill_id is required.",
                duration_ms=int((time.time() - start) * 1000),
            )

        skill_meta = read_skill_meta(skill_id)
        if skill_meta is None:
            return ToolResult(
                success=False,
                error=f"Skill '{skill_id}' not found in the skills library.",
                duration_ms=int((time.time() - start) * 1000),
            )

        skill = AgentSkill(
            id=skill_meta["id"],
            name=skill_meta["name"],
            description=skill_meta.get("description", ""),
            input_modes=[SkillInputMode.TEXT],
            output_modes=[SkillOutputMode.TEXT],
        )

        try:
            await self._registry.add_skill_to_agent(agent_id, skill)
            return ToolResult(
                success=True,
                result={
                    "agent_id": agent_id,
                    "skill_id": skill_id,
                    "skill_name": skill_meta["name"],
                    "message": (
                        f"Skill '{skill_meta['name']}' successfully added to agent '{agent_id}'."
                    ),
                },
                duration_ms=int((time.time() - start) * 1000),
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                duration_ms=int((time.time() - start) * 1000),
            )


class DelegateToAgentTool(BaseTool):
    """Tool to delegate the conversation to a specific registered agent.

    When called, the MasterAgent will route all subsequent messages to the
    specified agent until that agent signals completion or the user cancels.
    """

    def __init__(
        self,
        agent_registry: Any,
        on_delegate: Callable[[Any], None],
        local_agents: Optional[dict] = None,
    ) -> None:
        """Initialize with registry, delegation callback, and optional built-in agents.

        Args:
            agent_registry: AgentRegistry for looking up registered agents
            on_delegate: Callback invoked with the resolved agent instance
            local_agents: Dict of agent_id → agent instance for built-in agents
                         that don't need to be in the registry
        """
        self._registry = agent_registry
        self._on_delegate = on_delegate
        self._local_agents: dict[str, Any] = local_agents or {}

    @property
    def definition(self) -> ToolDefinition:
        """Get tool definition."""
        return ToolDefinition(
            name="delegate_to_agent",
            type=ToolType.FUNCTION,
            description=(
                "Delegate the conversation to a specific agent. "
                "The agent will handle all subsequent messages until the task is done. "
                "Use 'skill-creation-assistant' to create a new OmniForge skill. "
                "Use list_agents to find IDs of user-created agents."
            ),
            parameters=[
                ToolParameter(
                    name="agent_id",
                    type=ParameterType.STRING,
                    description=(
                        "The ID of the agent to delegate to. "
                        "Use 'skill-creation-assistant' for skill creation, "
                        "or an agent ID from list_agents for user-created agents."
                    ),
                    required=True,
                ),
            ],
            timeout_ms=10000,
        )

    async def execute(self, context: ToolCallContext, arguments: dict[str, Any]) -> ToolResult:
        """Resolve the agent and invoke the delegation callback.

        Args:
            context: Execution context
            arguments: Dict with agent_id key

        Returns:
            ToolResult confirming delegation or reporting error
        """
        start = time.time()
        agent_id = (arguments.get("agent_id") or "").strip()

        if not agent_id:
            return ToolResult(
                success=False,
                error="agent_id is required.",
                duration_ms=int((time.time() - start) * 1000),
            )

        # Check local (built-in) agents first
        agent = self._local_agents.get(agent_id)

        # Fall back to registry
        if agent is None and self._registry is not None:
            try:
                agent = await self._registry.get(agent_id)
            except Exception:
                pass

        if agent is None:
            return ToolResult(
                success=False,
                error=(
                    f"Agent '{agent_id}' not found. "
                    "Use list_agents to see available agents, "
                    "or 'skill-creation-assistant' for skill creation."
                ),
                duration_ms=int((time.time() - start) * 1000),
            )

        self._on_delegate(agent)
        return ToolResult(
            success=True,
            result={
                "agent_id": agent_id,
                "message": (
                    f"Delegating to '{agent_id}'. "
                    "The next message will be handled by this agent."
                ),
            },
            duration_ms=int((time.time() - start) * 1000),
        )


# ---------------------------------------------------------------------------
# Factory / registration helper
# ---------------------------------------------------------------------------


def register_platform_tools(
    tool_registry: ToolRegistry,
    agent_registry: Any,
    tenant_id: Optional[str] = None,
    on_delegate: Optional[Callable[[Any], None]] = None,
    local_agents: Optional[dict] = None,
) -> None:
    """Register all platform management tools in the given tool registry.

    Registers ListAgentsTool, ListSkillsTool, CreateAgentTool,
    AddSkillToAgentTool, and (when on_delegate is provided) DelegateToAgentTool.

    Args:
        tool_registry: The ToolRegistry to register tools into
        agent_registry: AgentRegistry instance for agent operations
        tenant_id: Optional tenant ID for multi-tenant isolation
        on_delegate: Optional callback invoked when delegate_to_agent fires;
                     if provided, DelegateToAgentTool is registered
        local_agents: Optional dict of built-in agent_id → agent instances
                      (e.g. {"skill-creation-assistant": skill_agent})

    Example:
        >>> registry = ToolRegistry()
        >>> register_platform_tools(registry, agent_registry, tenant_id="my-tenant")
        >>> "create_agent" in registry.list_tools()
        True
    """
    from omniforge.tools.builtin.context import ReadContextTool, WriteContextTool

    tool_registry.register(ListAgentsTool(agent_registry))
    tool_registry.register(ListSkillsTool())
    tool_registry.register(CreateAgentTool(agent_registry, tenant_id))
    tool_registry.register(AddSkillToAgentTool(agent_registry))
    tool_registry.register(WriteContextTool())
    tool_registry.register(ReadContextTool())
    if on_delegate is not None:
        tool_registry.register(
            DelegateToAgentTool(
                agent_registry=agent_registry,
                on_delegate=on_delegate,
                local_agents=local_agents,
            )
        )
