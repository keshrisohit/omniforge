"""Master Agent Response Generator for chat interactions.

Pure transport layer: creates a Task from each user message and delegates
processing entirely to MasterAgent. All routing, session state, and intent
detection live in MasterAgent — this module contains no routing logic.
"""

import logging
from datetime import datetime
from typing import AsyncIterator, Optional
from uuid import uuid4

from omniforge.agents.cot.chain import StepType
from omniforge.agents.cot.events import ReasoningStepEvent
from omniforge.agents.events import TaskErrorEvent, TaskStatusEvent
from omniforge.agents.master_agent import MasterAgent
from omniforge.agents.models import TextPart
from omniforge.agents.registry import AgentRegistry
from omniforge.conversation.context import assemble_context
from omniforge.conversation.models import Message
from omniforge.storage.memory import InMemoryAgentRepository
from omniforge.tasks.models import Task, TaskMessage, TaskState

logger = logging.getLogger(__name__)


class MasterResponseGenerator:
    """Pure transport layer: routes each message to MasterAgent.process_task().

    All routing, skill-creation detection, and session management are handled
    inside MasterAgent. This class only:
      - Creates Task objects from user messages + conversation history
      - Calls master_agent.process_task(task)
      - Yields text chunks from TaskMessageEvents

    Examples:
        >>> generator = MasterResponseGenerator()
        >>> async for chunk in generator.generate_stream("Create an agent"):
        ...     print(chunk)
        Agent 'Custom Agent' created successfully ...
    """

    def __init__(
        self,
        agent_registry: Optional[AgentRegistry] = None,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        intent_analyzer: Optional[object] = None,  # kept for API compatibility
    ) -> None:
        """Initialize Master Response Generator.

        Args:
            agent_registry: Registry of available agents
            tenant_id: Tenant identifier for multi-tenancy
            user_id: User identifier (defaults to "default-user")
            intent_analyzer: Unused — kept for backward API compatibility
        """
        # Create a default in-memory registry if none provided
        if agent_registry is None:
            agent_registry = AgentRegistry(repository=InMemoryAgentRepository())

        self._agent_registry = agent_registry
        self._tenant_id = tenant_id
        self._user_id = user_id or "default-user"

        # Default agent — used when no session_id is given (or session_id="default").
        # Keeping this attribute lets tests inject a mock via generator._master_agent.
        self._master_agent = MasterAgent(
            agent_registry=agent_registry,
            tenant_id=tenant_id,
        )

        # Per-session agents for conversation state isolation.
        # Each unique session_id gets its own MasterAgent so delegation state
        # (e.g. _delegated_agent for skill creation) cannot bleed between users.
        self._session_agents: dict[str, MasterAgent] = {}

    async def generate_stream(
        self,
        message: str,
        conversation_history: Optional[list[Message]] = None,
        session_id: str = "default",
    ) -> AsyncIterator[str]:
        """Generate streaming response using the Master Agent.

        Creates a Task from the user message (with optional conversation context)
        and delegates processing to MasterAgent. Text from TaskMessageEvents is
        yielded as streaming chunks.

        Args:
            message: User's input message
            conversation_history: Optional list of previous messages for context
            session_id: Stable identifier for this chat session (kept for API compat)

        Yields:
            Response chunks as strings for SSE streaming
        """
        context_messages: list[Message] = []
        if conversation_history:
            context_messages = assemble_context(conversation_history, max_messages=20)

        task = self._create_task_from_message(message, context_messages)
        agent = self._get_or_create_session_agent(session_id)

        async for event in agent.process_task(task):
            # Reasoning steps: thought process, tool calls, tool results
            if isinstance(event, ReasoningStepEvent):
                step = event.step
                if step.type == StepType.THINKING and step.thinking:
                    yield f"\n[Thought] {step.thinking.content}\n"
                elif step.type == StepType.TOOL_CALL and step.tool_call:
                    tc = step.tool_call
                    params = ", ".join(f"{k}={v!r}" for k, v in tc.parameters.items())
                    yield f"\n[Tool] {tc.tool_name}({params})\n"
                elif step.type == StepType.TOOL_RESULT and step.tool_result:
                    tr = step.tool_result
                    status = "ok" if tr.success else f"error: {tr.error}"
                    yield f"[Result] {status}\n"

            # Status transitions (only when there's a human-readable message)
            elif isinstance(event, TaskStatusEvent) and event.message:
                yield f"\n[{event.message}]\n"

            # Final answer text
            elif hasattr(event, "message_parts"):
                for part in event.message_parts:
                    if hasattr(part, "text"):
                        yield part.text

            # Errors
            elif isinstance(event, TaskErrorEvent):
                yield f"\n[Error] {event.error_message}\n"

    def count_tokens(self, text: str) -> int:
        """Count tokens in the given text.

        Args:
            text: The text to count tokens for

        Returns:
            Token count (minimum 1)
        """
        return max(1, len(text) // 4)

    def _create_task_from_message(
        self, message: str, context_messages: Optional[list[Message]] = None
    ) -> Task:
        """Create a Task object from user message with optional conversation context.

        Args:
            message: User's message
            context_messages: Optional list of previous messages for context

        Returns:
            Task object ready for processing
        """
        task_id = str(uuid4())
        message_id = str(uuid4())

        task_messages = []

        if context_messages:
            for ctx_msg in context_messages:
                role_str = ctx_msg.role.value if hasattr(ctx_msg.role, "value") else ctx_msg.role
                task_role = "agent" if role_str == "assistant" else role_str
                task_messages.append(
                    TaskMessage(
                        id=str(uuid4()),
                        role=task_role,
                        parts=[TextPart(text=ctx_msg.content)],
                        created_at=ctx_msg.created_at,
                    )
                )

        task_messages.append(
            TaskMessage(
                id=message_id,
                role="user",
                parts=[TextPart(text=message)],
                created_at=datetime.utcnow(),
            )
        )

        return Task(
            id=task_id,
            agent_id="master-agent",
            state=TaskState.SUBMITTED,
            messages=task_messages,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            tenant_id=self._tenant_id,
            user_id=self._user_id,
        )

    def _get_or_create_session_agent(self, session_id: str) -> MasterAgent:
        """Return the MasterAgent for *session_id*, creating one if needed.

        Using ``session_id="default"`` returns ``self._master_agent`` so that
        tests can still inject mocks via ``generator._master_agent = mock``.
        All real sessions (UUID strings from conversation_id) get their own
        isolated MasterAgent instance, preventing delegation state from leaking
        between concurrent users.

        Args:
            session_id: Stable identifier for the chat session

        Returns:
            MasterAgent bound to this session
        """
        if session_id == "default":
            return self._master_agent
        if session_id not in self._session_agents:
            self._session_agents[session_id] = MasterAgent(
                agent_registry=self._agent_registry,
                tenant_id=self._tenant_id,
            )
        return self._session_agents[session_id]
