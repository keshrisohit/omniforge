"""Simplified agent base class with automatic event scaffolding.

This module provides SimpleAgent, a base class that eliminates boilerplate
by automatically handling event streaming, message extraction, and error handling.
Subclasses only need to implement a single handle() method.
"""

from abc import abstractmethod
from datetime import datetime
from typing import AsyncIterator, Optional

from omniforge.agents.base import BaseAgent
from omniforge.agents.events import (
    TaskDoneEvent,
    TaskErrorEvent,
    TaskEvent,
    TaskMessageEvent,
    TaskStatusEvent,
)
from omniforge.agents.helpers import extract_user_message, generate_agent_id, create_simple_task
from omniforge.agents.models import (
    AgentCapabilities,
    AgentIdentity,
    AgentSkill,
    SkillInputMode,
    SkillOutputMode,
    TextPart,
)
from omniforge.tasks.models import Task, TaskState


class SimpleAgent(BaseAgent):
    """Simplified agent base class that handles event scaffolding automatically.

    This class eliminates boilerplate by:
    - Auto-generating agent identity from class attributes
    - Auto-generating default capabilities and skills
    - Handling all event streaming (status, message, done, error)
    - Extracting user messages automatically
    - Providing a simple handle() method interface

    Subclasses only need to:
    1. Set name class attribute
    2. Implement handle(message: str) -> str method

    Class Attributes:
        name: Agent display name (required)
        description: Agent description (optional, uses docstring if not set)
        version: Semantic version (default: "1.0.0")
        streaming: Enable streaming responses (default: True)
        multi_turn: Support multi-turn conversations (default: False)

    Example:
        >>> class EchoAgent(SimpleAgent):
        ...     '''A friendly echo agent.'''
        ...     name = "Echo Agent"
        ...
        ...     async def handle(self, message: str) -> str:
        ...         return f"You said: {message}"
        ...
        >>> agent = EchoAgent()
        >>> response = await agent.run("Hello!")
        >>> print(response)  # "You said: Hello!"
    """

    # Class attributes with defaults
    name: str = "Simple Agent"
    description: Optional[str] = None
    version: str = "1.0.0"
    streaming: bool = True
    multi_turn: bool = False

    def __init__(self, agent_id=None, tenant_id=None, prompt_config=None):
        """Initialize the simplified agent.

        Args:
            agent_id: Optional explicit UUID for the agent instance
            tenant_id: Optional tenant identifier for multi-tenancy
            prompt_config: Optional PromptConfig for the agent

        Note:
            Identity, capabilities, and skills are auto-generated from
            class attributes on first initialization.
        """
        # Auto-generate identity if not already set
        if not hasattr(self.__class__, "identity") or self.__class__.identity is None:
            self._setup_class_attributes()

        super().__init__(agent_id=agent_id, tenant_id=tenant_id, prompt_config=prompt_config)

    def _setup_class_attributes(self):
        """Auto-generate identity, capabilities, and skills from class attributes."""
        # Generate agent ID from class name if name not explicitly set
        if self.name == "Simple Agent":
            agent_id = generate_agent_id(self.__class__.__name__)
            agent_name = self.__class__.__name__
        else:
            agent_id = generate_agent_id(self.name)
            agent_name = self.name

        # Use docstring as description if description not set
        description = self.description
        if description is None:
            description = self.__class__.__doc__ or f"{agent_name} agent"
            # Clean up docstring
            description = description.strip()

        # Create identity
        self.__class__.identity = AgentIdentity(
            id=agent_id,
            name=agent_name,
            description=description,
            version=self.version,
        )

        # Create capabilities
        self.__class__.capabilities = AgentCapabilities(
            streaming=self.streaming,
            multi_turn=self.multi_turn,
            push_notifications=False,
            hitl_support=False,
        )

        # Create default skill
        self.__class__.skills = [
            AgentSkill(
                id=f"{agent_id}-skill",
                name=f"{agent_name} Skill",
                description=description,
                input_modes=[SkillInputMode.TEXT],
                output_modes=[SkillOutputMode.TEXT],
            )
        ]

    async def process_task(self, task: Task) -> AsyncIterator[TaskEvent]:
        """Process task with automatic event scaffolding.

        This method handles all event streaming automatically:
        1. Emits TaskStatusEvent(WORKING)
        2. Extracts user message from task
        3. Calls abstract handle() method
        4. Emits TaskMessageEvent with response
        5. Emits TaskDoneEvent(COMPLETED)
        6. Handles exceptions and emits error events if needed

        Args:
            task: The task to process

        Yields:
            TaskEvent objects for status, messages, and completion

        Note:
            Subclasses don't need to override this - implement handle() instead.
        """
        # Emit working status
        yield TaskStatusEvent(
            task_id=task.id,
            timestamp=datetime.utcnow(),
            state=TaskState.WORKING,
        )

        try:
            # Extract user message
            message = extract_user_message(task)

            # Call abstract handle method
            response = await self.handle(message)

            # Emit message event
            yield TaskMessageEvent(
                task_id=task.id,
                timestamp=datetime.utcnow(),
                message_parts=[TextPart(text=response)],
                is_partial=False,
            )

            # Emit done event
            yield TaskDoneEvent(
                task_id=task.id,
                timestamp=datetime.utcnow(),
                final_state=TaskState.COMPLETED,
            )

        except Exception as e:
            # Auto error handling
            yield TaskErrorEvent(
                task_id=task.id,
                timestamp=datetime.utcnow(),
                error_code="PROCESSING_ERROR",
                error_message=str(e),
            )

            yield TaskDoneEvent(
                task_id=task.id,
                timestamp=datetime.utcnow(),
                final_state=TaskState.FAILED,
            )

    @abstractmethod
    async def handle(self, message: str) -> str:
        """Handle a user message and return a response.

        This is the only method subclasses need to implement.

        Args:
            message: The user's message text

        Returns:
            The agent's response text

        Example:
            >>> async def handle(self, message: str) -> str:
            ...     return f"Echo: {message}"
        """
        pass

    async def run(self, message: str, user_id: str = "default-user") -> str:
        """Simple API to run agent with a message string.

        This provides a convenient way to run the agent without dealing
        with Task objects and event streaming.

        Args:
            message: The user message text
            user_id: Optional user identifier

        Returns:
            The agent's response as a string

        Example:
            >>> agent = MyAgent()
            >>> response = await agent.run("Hello!")
            >>> print(response)
        """
        # Create task
        task = create_simple_task(
            message=message,
            agent_id=self.identity.id,
            user_id=user_id,
            tenant_id=self.tenant_id,
        )

        # Process and extract response
        response = ""
        async for event in self.process_task(task):
            if isinstance(event, TaskMessageEvent):
                for part in event.message_parts:
                    if hasattr(part, "text"):
                        response += part.text

        return response
