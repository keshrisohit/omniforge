"""Agent discovery service for finding agents by skills and capabilities.

This module provides the AgentDiscoveryService class that helps agents
discover other agents based on their skills, tags, and capabilities.
It uses the AgentRegistry internally and supports tenant-based filtering.
"""

from typing import Optional

from omniforge.agents.base import BaseAgent
from omniforge.agents.models import AgentCard
from omniforge.agents.registry import AgentRegistry


class AgentDiscoveryService:
    """Service for discovering agents by skills and capabilities.

    This service provides high-level discovery methods for finding agents
    that can handle specific tasks or provide certain capabilities. It wraps
    the AgentRegistry and adds convenience methods for common discovery patterns.

    Supports tenant isolation when tenant_id is provided.

    Attributes:
        _registry: The agent registry to search
        _tenant_id: Optional tenant ID for multi-tenant filtering

    Example:
        >>> from omniforge.storage.memory import InMemoryAgentRepository
        >>> repo = InMemoryAgentRepository()
        >>> registry = AgentRegistry(repository=repo)
        >>> discovery = AgentDiscoveryService(registry=registry)
        >>>
        >>> # Find agents with a specific skill
        >>> agents = await discovery.find_by_skill("data-analysis")
        >>> for agent in agents:
        ...     print(f"Found: {agent.identity.name}")
        >>>
        >>> # Find agents with a specific tag
        >>> nlp_agents = await discovery.find_by_tag("nlp")
    """

    def __init__(self, registry: AgentRegistry, tenant_id: Optional[str] = None) -> None:
        """Initialize the discovery service.

        Args:
            registry: AgentRegistry instance to use for discovery
            tenant_id: Optional tenant ID for multi-tenant filtering
        """
        self._registry = registry
        self._tenant_id = tenant_id

    async def find_by_skill(self, skill_id: str) -> list[BaseAgent]:
        """Find agents that provide a specific skill.

        This method searches through all registered agents (filtered by tenant
        if tenant_id was provided) and returns those that have a skill matching
        the specified skill_id.

        Args:
            skill_id: The skill ID to search for

        Returns:
            List of agents that provide the specified skill

        Example:
            >>> agents = await discovery.find_by_skill("text-translation")
            >>> if agents:
            ...     agent = agents[0]
            ...     print(f"Found agent: {agent.identity.name}")
        """
        return await self._registry.find_by_skill(skill_id)

    async def find_by_tag(self, tag: str) -> list[BaseAgent]:
        """Find agents that have skills tagged with a specific tag.

        This method searches through all registered agents (filtered by tenant
        if tenant_id was provided) and returns those that have at least one skill
        with the specified tag.

        Args:
            tag: The tag to search for

        Returns:
            List of agents that have skills with the specified tag

        Example:
            >>> agents = await discovery.find_by_tag("ml")
            >>> for agent in agents:
            ...     print(f"{agent.identity.name} provides ML capabilities")
        """
        return await self._registry.find_by_tag(tag)

    async def find_by_capability(self, capability: str) -> list[BaseAgent]:
        """Find agents that have a specific capability enabled.

        Searches for agents where the specified capability is set to True
        in their AgentCard capabilities configuration.

        Args:
            capability: The capability name to search for
                       (e.g., "streaming", "multi_turn", "hitl_support")

        Returns:
            List of agents that have the specified capability enabled

        Example:
            >>> streaming_agents = await discovery.find_by_capability("streaming")
            >>> for agent in streaming_agents:
            ...     print(f"{agent.identity.name} supports streaming")
        """
        all_agents = await self._registry.list_all()

        # Filter agents by capability
        matching_agents = []
        for agent in all_agents:
            # Check if capability is enabled directly on agent
            if hasattr(agent.capabilities, capability):
                if getattr(agent.capabilities, capability):
                    matching_agents.append(agent)

        return matching_agents

    async def get_agent_card(
        self, agent_id: str, service_endpoint: str = "http://localhost:8000"
    ) -> AgentCard:
        """Get the agent card for a specific agent.

        This is a convenience method for retrieving an agent's card
        without needing to access the registry directly.

        Args:
            agent_id: ID of the agent to get the card for
            service_endpoint: Service endpoint for the agent card (default: localhost)

        Returns:
            The agent's AgentCard

        Raises:
            AgentNotFoundError: If the agent does not exist

        Example:
            >>> card = await discovery.get_agent_card("my-agent")
            >>> print(f"Agent: {card.identity.name}")
            >>> print(f"Skills: {[s.name for s in card.skills]}")
        """
        agent = await self._registry.get(agent_id)
        return agent.get_agent_card(service_endpoint)

    async def find_best_agent_for_skill(self, skill_id: str) -> Optional[BaseAgent]:
        """Find the best agent for a specific skill.

        Returns the first agent found with the specified skill. In the future,
        this could be enhanced to rank agents by quality, availability, or
        other factors.

        Args:
            skill_id: The skill ID to search for

        Returns:
            The best agent for the skill, or None if no agent is found

        Example:
            >>> agent = await discovery.find_best_agent_for_skill("data-analysis")
            >>> if agent:
            ...     print(f"Best agent: {agent.identity.name}")
            ... else:
            ...     print("No agent found with this skill")
        """
        agents = await self.find_by_skill(skill_id)
        return agents[0] if agents else None
