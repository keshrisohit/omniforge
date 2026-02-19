"""Agent discovery API route handlers.

This module provides FastAPI route handlers for agent discovery,
including agent card retrieval and agent listing operations.
"""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from omniforge.agents.base import BaseAgent
from omniforge.agents.models import AgentCard
from omniforge.agents.registry import AgentRegistry
from omniforge.security.isolation import enforce_agent_isolation, filter_by_tenant
from omniforge.storage.base import AgentRepository
from omniforge.storage.memory import InMemoryAgentRepository

# Create router with tags
router = APIRouter(tags=["agents"])

# Shared in-memory repository instance
# TODO: Replace with persistent storage in production
_agent_repository: AgentRepository = InMemoryAgentRepository()


def get_agent_registry() -> AgentRegistry:
    """Dependency for getting the agent registry instance.

    Returns:
        AgentRegistry instance configured with the repository
    """
    return AgentRegistry(repository=_agent_repository)


@router.get("/.well-known/agent-card.json")
async def get_default_agent_card() -> JSONResponse:
    """Get the default OmniForge platform agent card.

    This endpoint provides a default agent card representing the OmniForge
    platform itself, following the A2A protocol specification.

    Returns:
        JSONResponse containing the default agent card

    Example:
        >>> GET /.well-known/agent-card.json
        >>> {
        >>>     "protocolVersion": "1.0",
        >>>     "identity": {
        >>>         "id": "omniforge-platform",
        >>>         "name": "OmniForge Platform",
        >>>         "description": "Enterprise-grade agent orchestration platform",
        >>>         "version": "0.1.0"
        >>>     },
        >>>     ...
        >>> }
    """
    from omniforge.agents.models import (
        AgentCapabilities,
        AgentIdentity,
        AgentSkill,
        AuthScheme,
        SecurityConfig,
        SkillInputMode,
        SkillOutputMode,
    )

    # Create default platform agent card
    default_card = AgentCard(
        protocol_version="1.0",  # type: ignore[call-arg]
        identity=AgentIdentity(
            id="omniforge-platform",
            name="OmniForge Platform",
            description="Enterprise-grade agent orchestration platform",
            version="0.1.0",
        ),
        capabilities=AgentCapabilities(
            streaming=True,
            push_notifications=False,
            multi_turn=True,
            hitl_support=True,
        ),
        skills=[
            AgentSkill(
                id="agent-orchestration",
                name="Agent Orchestration",
                description="Coordinate and manage multiple AI agents",
                tags=["orchestration", "coordination"],
                inputModes=[SkillInputMode.TEXT, SkillInputMode.STRUCTURED],
                outputModes=[SkillOutputMode.TEXT, SkillOutputMode.ARTIFACT],
            )
        ],
        service_endpoint="http://localhost:8000",  # type: ignore[call-arg]
        security=SecurityConfig(
            auth_scheme=AuthScheme.BEARER,
            require_https=True,
        ),
    )

    # Return JSON response with proper A2A field names (camelCase)
    return JSONResponse(
        content=default_card.model_dump(mode="json", by_alias=True),
        headers={"Content-Type": "application/json"},
    )


@router.get("/api/v1/agents")
async def list_agents(
    registry: AgentRegistry = Depends(get_agent_registry),
) -> list[dict]:
    """List all registered agents.

    This endpoint returns a list of all agents currently registered
    in the platform registry. If a tenant context is set, only agents
    belonging to that tenant (or shared agents) are returned.

    Args:
        registry: Injected AgentRegistry dependency

    Returns:
        List of agent summary objects with id, name, description, and version

    Example:
        >>> GET /api/v1/agents
        >>> [
        >>>     {
        >>>         "id": "my-agent",
        >>>         "name": "My Agent",
        >>>         "description": "Does cool things",
        >>>         "version": "1.0.0"
        >>>     }
        >>> ]
    """
    agents: list[BaseAgent] = await registry.list_all()

    # Filter agents by tenant (only show agents for current tenant)
    agents = filter_by_tenant(agents)

    # Return simplified agent summaries
    return [
        {
            "id": agent.identity.id,
            "name": agent.identity.name,
            "description": agent.identity.description,
            "version": agent.identity.version,
        }
        for agent in agents
    ]


@router.get("/api/v1/agents/{agent_id}")
async def get_agent_card(
    agent_id: str,
    registry: AgentRegistry = Depends(get_agent_registry),
) -> JSONResponse:
    """Get the agent card for a specific agent.

    This endpoint returns the full A2A-compliant agent card for the
    specified agent, including identity, capabilities, and skills.
    Tenant isolation is enforced - users can only access agents
    belonging to their tenant.

    Args:
        agent_id: The ID of the agent to retrieve
        registry: Injected AgentRegistry dependency

    Returns:
        JSONResponse containing the agent card

    Raises:
        AgentNotFoundError: If the agent does not exist (handled by middleware)
        TenantIsolationError: If agent belongs to different tenant (handled by middleware)

    Example:
        >>> GET /api/v1/agents/my-agent
        >>> {
        >>>     "protocolVersion": "1.0",
        >>>     "identity": {
        >>>         "id": "my-agent",
        >>>         "name": "My Agent",
        >>>         ...
        >>>     },
        >>>     ...
        >>> }
    """
    # Get agent from registry (raises AgentNotFoundError if not found)
    agent: BaseAgent = await registry.get(agent_id)

    # Enforce tenant isolation (raises TenantIsolationError if violation)
    enforce_agent_isolation(agent)

    # Generate agent card with service endpoint
    service_endpoint = f"http://localhost:8000/api/v1/agents/{agent_id}"
    agent_card: AgentCard = agent.get_agent_card(service_endpoint)

    # Return JSON response with proper A2A field names (camelCase)
    return JSONResponse(
        content=agent_card.model_dump(mode="json", by_alias=True),
        headers={"Content-Type": "application/json"},
    )
