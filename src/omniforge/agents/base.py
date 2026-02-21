"""Base abstract class for all OmniForge agents.

This module defines the BaseAgent abstract class that all agents must extend,
providing the core interface for agent identity, capabilities, task processing,
and A2A protocol compliance.
"""

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Optional
from uuid import UUID, uuid4

from omniforge.agents.events import TaskEvent
from omniforge.agents.models import (
    AgentCapabilities,
    AgentCard,
    AgentIdentity,
    AgentSkill,
    AuthScheme,
    SecurityConfig,
)
from omniforge.tasks.models import Task


class BaseAgent(ABC):
    """Abstract base class for all OmniForge agents.

    All agents in the OmniForge platform must extend this class and implement
    the abstract methods. This class provides:
    - Agent identity and capabilities management
    - A2A protocol compliance via AgentCard generation
    - Abstract task processing interface
    - Default implementations for message handling and task cancellation

    Class Attributes:
        identity: Agent identity information (name, description, version)
        capabilities: Agent capabilities configuration
        skills: List of skills the agent provides

    Instance Attributes:
        _id: Unique identifier for this agent instance
        tenant_id: Tenant identifier for multi-tenancy isolation (optional)

    Example:
        >>> class MyAgent(BaseAgent):
        ...     identity = AgentIdentity(
        ...         id="my-agent",
        ...         name="My Agent",
        ...         description="Does cool things",
        ...         version="1.0.0"
        ...     )
        ...     capabilities = AgentCapabilities(streaming=True)
        ...     skills = [
        ...         AgentSkill(
        ...             id="skill-1",
        ...             name="Cool Skill",
        ...             description="Does something cool",
        ...             input_modes=[SkillInputMode.TEXT],
        ...             output_modes=[SkillOutputMode.TEXT]
        ...         )
        ...     ]
        ...
        ...     async def process_task(self, task: Task) -> AsyncIterator[TaskEvent]:
        ...         # Implementation here
        ...         yield status_event
    """

    # Class-level attributes that subclasses must define
    identity: AgentIdentity
    capabilities: AgentCapabilities
    skills: list[AgentSkill]

    def __init__(
        self,
        agent_id: Optional[UUID] = None,
        tenant_id: Optional[str] = None,
        prompt_config: Optional[Any] = None,
        artifact_store: Optional[Any] = None,
    ) -> None:
        """Initialize the agent with a unique ID and optional tenant.

        Args:
            agent_id: Optional explicit UUID for the agent instance.
                     If not provided, a new UUID will be generated.
            tenant_id: Optional tenant identifier for multi-tenancy isolation.
                      If not provided, the agent is not tenant-scoped.
            prompt_config: Optional PromptConfig for the agent.
                          If provided, the agent will use this configuration
                          to compose prompts. Type is Any to avoid circular import.
            artifact_store: Optional ArtifactStore for persisting agent artifacts.
                           Type is Any to avoid circular import with storage module.
        """
        self._id: UUID = agent_id if agent_id is not None else uuid4()
        self.tenant_id: Optional[str] = tenant_id
        self.prompt_config: Optional[Any] = prompt_config
        self.artifact_store: Optional[Any] = artifact_store

    def get_agent_card(self, service_endpoint: str) -> AgentCard:
        """Generate an A2A-compliant agent card.

        This method creates an AgentCard from the class-level identity,
        capabilities, and skills, along with the provided service endpoint.

        Args:
            service_endpoint: URL endpoint where this agent's API is accessible

        Returns:
            AgentCard containing all agent information for A2A protocol

        Example:
            >>> agent = MyAgent()
            >>> card = agent.get_agent_card("https://api.example.com/agents/my-agent")
            >>> card.identity.name
            'My Agent'
            >>> card.service_endpoint
            'https://api.example.com/agents/my-agent'
        """
        return AgentCard(
            protocol_version="1.0",  # type: ignore[call-arg]
            identity=self.identity,
            capabilities=self.capabilities,
            skills=self.skills,
            service_endpoint=service_endpoint,  # type: ignore[call-arg]
            security=SecurityConfig(
                auth_scheme=AuthScheme.BEARER,
                require_https=True,
            ),
        )

    @abstractmethod
    async def process_task(self, task: Task) -> AsyncIterator[TaskEvent]:
        """Process a task and yield events as the task progresses.

        This is the core method that all agents must implement. It receives
        a task and yields TaskEvent objects to communicate progress, messages,
        artifacts, errors, and completion.

        Args:
            task: The task to process

        Yields:
            TaskEvent objects representing task progress and results

        Raises:
            AgentError: If task processing fails
            NotImplementedError: If subclass doesn't implement this method

        Example:
            >>> async def process_task(self, task: Task) -> AsyncIterator[TaskEvent]:
            ...     # Start working
            ...     yield TaskStatusEvent(
            ...         task_id=task.id,
            ...         timestamp=datetime.utcnow(),
            ...         state=TaskState.WORKING
            ...     )
            ...
            ...     # Send a message
            ...     yield TaskMessageEvent(
            ...         task_id=task.id,
            ...         timestamp=datetime.utcnow(),
            ...         message_parts=[TextPart(text="Processing...")],
            ...         is_partial=False
            ...     )
            ...
            ...     # Complete the task
            ...     yield TaskDoneEvent(
            ...         task_id=task.id,
            ...         timestamp=datetime.utcnow(),
            ...         final_state=TaskState.COMPLETED
            ...     )
        """
        pass

    def handle_message(self, task_id: str, message: str) -> None:
        """Handle an incoming message for a task.

        This is a default stub implementation. Subclasses can override this
        method to implement custom message handling for multi-turn conversations.

        Args:
            task_id: The ID of the task receiving the message
            message: The message content

        Note:
            This default implementation does nothing. Override this method
            in subclasses that support multi-turn conversations.
        """
        pass

    def cancel_task(self, task_id: str) -> None:
        """Cancel a running task.

        This is a default stub implementation. Subclasses can override this
        method to implement custom task cancellation logic.

        Args:
            task_id: The ID of the task to cancel

        Note:
            This default implementation does nothing. Override this method
            in subclasses that need to handle task cancellation.
        """
        pass

    def get_composed_prompt(self, variables: Optional[dict[str, Any]] = None) -> str:
        """Get the composed prompt with variables substituted.

        This method returns the agent's prompt template with any provided
        variables substituted. If the agent has a prompt_config, it uses
        the agent_prompt from the config; otherwise, it returns an empty string.

        Note: This is a basic implementation for accessing the prompt template.
        For full composition with layer hierarchy and merge points, use the
        PromptManager class from the prompts module.

        Args:
            variables: Optional dictionary of variables to substitute in the prompt.
                      If not provided and the agent has a prompt_config with
                      variables, those will be used.

        Returns:
            The prompt template string with variables substituted, or empty string
            if no prompt_config is set

        Example:
            >>> agent = MyAgent(
            ...     prompt_config=PromptConfig(
            ...         agent_prompt="You are {{ role }}. Be {{ style }}.",
            ...         variables={"role": "assistant", "style": "helpful"}
            ...     )
            ... )
            >>> agent.get_composed_prompt()
            'You are {{ role }}. Be {{ style }}.'
            >>> # For full variable substitution, use PromptManager
        """
        if self.prompt_config is None:
            return ""

        # Return the agent_prompt from the config
        # Note: This does not perform variable substitution or composition.
        # For full prompt composition with variable substitution, use PromptManager.
        # Type ignore because prompt_config is typed as Any to avoid circular import
        return str(self.prompt_config.agent_prompt)  # type: ignore[attr-defined]
