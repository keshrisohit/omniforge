"""Agent registry for discovering and managing registered agents.

This module provides the AgentRegistry class for registering agents,
discovering them by various criteria (ID, skill, tag), and managing
agent lifecycle with persistence support.
"""

from typing import Optional

from omniforge.agents.base import BaseAgent
from omniforge.agents.errors import AgentNotFoundError
from omniforge.agents.models import AgentSkill
from omniforge.storage.base import AgentRepository


class AgentRegistry:
    """Registry for managing and discovering agents.

    The registry provides a high-level interface for agent management,
    including registration, discovery by various criteria, and persistence
    through an AgentRepository backend.

    Supports tenant isolation when tenant_id is provided for operations.

    Attributes:
        _repository: Storage backend for agent persistence
        _tenant_id: Optional tenant ID for multi-tenant isolation

    Example:
        >>> from omniforge.storage.memory import InMemoryAgentRepository
        >>> repo = InMemoryAgentRepository()
        >>> registry = AgentRegistry(repository=repo)
        >>>
        >>> # Register an agent
        >>> await registry.register(my_agent)
        >>>
        >>> # Find by skill
        >>> agents = await registry.find_by_skill("data-analysis")
        >>> for agent in agents:
        ...     print(agent.identity.name)
    """

    def __init__(self, repository: AgentRepository, tenant_id: Optional[str] = None) -> None:
        """Initialize the agent registry.

        Args:
            repository: Storage backend implementing AgentRepository protocol
            tenant_id: Optional tenant ID for multi-tenant isolation
        """
        self._repository = repository
        self._tenant_id = tenant_id

    async def register(self, agent: BaseAgent) -> None:
        """Register a new agent in the registry.

        Persists the agent using the configured repository backend.
        The agent is stored by its identity.id (agent type ID), not by
        the instance UUID.

        Args:
            agent: Agent instance to register

        Raises:
            ValueError: If an agent with the same ID already exists

        Example:
            >>> agent = MyAgent()
            >>> await registry.register(agent)
        """
        await self._repository.save(agent)

    async def unregister(self, agent_id: str) -> None:
        """Unregister an agent from the registry.

        Removes the agent from persistent storage.

        Args:
            agent_id: ID of the agent to unregister (identity.id)

        Raises:
            AgentNotFoundError: If the agent does not exist

        Example:
            >>> await registry.unregister("my-agent")
        """
        # Verify agent exists before attempting deletion
        existing = await self._repository.get(agent_id)
        if existing is None:
            raise AgentNotFoundError(agent_id)

        await self._repository.delete(agent_id)

    async def get(self, agent_id: str) -> BaseAgent:
        """Retrieve an agent by its ID.

        Args:
            agent_id: ID of the agent to retrieve (identity.id)

        Returns:
            The agent instance

        Raises:
            AgentNotFoundError: If the agent does not exist

        Example:
            >>> agent = await registry.get("my-agent")
            >>> print(agent.identity.name)
        """
        agent = await self._repository.get(agent_id)

        if agent is None:
            raise AgentNotFoundError(agent_id)

        return agent

    async def list_all(self) -> list[BaseAgent]:
        """List all registered agents.

        If a tenant_id was provided during initialization, only returns
        agents belonging to that tenant.

        Returns:
            List of all registered agents (up to 100)

        Example:
            >>> agents = await registry.list_all()
            >>> for agent in agents:
            ...     print(f"{agent.identity.name}: {len(agent.skills)} skills")
        """
        if self._tenant_id is not None:
            return await self._repository.list_by_tenant(self._tenant_id)
        return await self._repository.list_all()

    async def find_by_skill(self, skill_id: str) -> list[BaseAgent]:
        """Find agents that provide a specific skill.

        Searches through all registered agents and returns those that
        have a skill with the matching skill ID.

        Args:
            skill_id: The skill ID to search for

        Returns:
            List of agents that provide the specified skill

        Example:
            >>> agents = await registry.find_by_skill("data-analysis")
            >>> for agent in agents:
            ...     skill = next(s for s in agent.skills if s.id == "data-analysis")
            ...     print(f"{agent.identity.name}: {skill.description}")
        """
        all_agents = await self.list_all()

        matching_agents = [
            agent for agent in all_agents if any(skill.id == skill_id for skill in agent.skills)
        ]

        return matching_agents

    async def add_skill_to_agent(self, agent_id: str, skill: AgentSkill) -> None:
        """Add a skill to an existing agent.

        Retrieves the agent, appends the skill to its skills list (instance-level
        override), then persists the update.

        Args:
            agent_id: ID of the agent to update (identity.id)
            skill: AgentSkill to add

        Raises:
            AgentNotFoundError: If the agent does not exist
            ValueError: If agent already has a skill with the same ID
        """
        agent = await self.get(agent_id)

        # Check for duplicate skill id
        if any(s.id == skill.id for s in agent.skills):
            raise ValueError(
                f"Agent '{agent_id}' already has a skill with id '{skill.id}'"
            )

        # Create instance-level skills list (shadows class attribute)
        agent.skills = list(agent.skills) + [skill]

        # Persist the updated agent (requires the repository to support update)
        if hasattr(self._repository, "update"):
            await self._repository.update(agent)

    async def find_by_tag(self, tag: str) -> list[BaseAgent]:
        """Find agents that have a specific tag in any of their skills.

        Searches through all registered agents and returns those that
        have at least one skill tagged with the specified tag.

        Args:
            tag: The tag to search for

        Returns:
            List of agents that have skills with the specified tag

        Example:
            >>> agents = await registry.find_by_tag("nlp")
            >>> for agent in agents:
            ...     nlp_skills = [s for s in agent.skills if s.tags and "nlp" in s.tags]
            ...     print(f"{agent.identity.name}: {len(nlp_skills)} NLP skills")
        """
        all_agents = await self.list_all()

        matching_agents = [
            agent
            for agent in all_agents
            if any(skill.tags and tag in skill.tags for skill in agent.skills)
        ]

        return matching_agents
