"""Response generator for chat interactions with Master Agent orchestration.

This module provides the ResponseGenerator class that can operate in different modes:
- Master Agent mode: Intelligent orchestration of agents and tasks (default)
- LLM mode: Direct LLM responses
- Placeholder mode: Testing without API keys

Set OMNIFORGE_USE_MASTER_AGENT=true to enable Master Agent mode (recommended).
"""

import os
from typing import AsyncIterator, Optional

from omniforge.chat.llm_generator import LLMResponseGenerator
from omniforge.chat.master_response_generator import MasterResponseGenerator
from omniforge.agents.registry import AgentRegistry


class ResponseGenerator:
    """Generates chat responses using Master Agent orchestration or LLM.

    This is the main response generator for the chat service. It automatically
    configures based on environment variables:

    - OMNIFORGE_USE_MASTER_AGENT=true: Use Master Agent (intelligent routing)
    - OMNIFORGE_USE_PLACEHOLDER_LLM=true: Use placeholder (no API calls)
    - Default: Use direct LLM

    The Master Agent mode enables:
    - Agent creation and management
    - Skill development
    - Task orchestration
    - Intelligent routing to specialized agents

    Examples:
        >>> # Master Agent mode (default)
        >>> generator = ResponseGenerator(use_master_agent=True)
        >>> async for chunk in generator.generate_stream("Create an agent"):
        ...     print(chunk)
        🤖 Master Agent analyzing your request...

        >>> # LLM mode
        >>> generator = ResponseGenerator(use_master_agent=False)
        >>> async for chunk in generator.generate_stream("Hello"):
        ...     print(chunk)
        Hello! How can I help you today?
    """

    def __init__(
        self,
        use_master_agent: Optional[bool] = None,
        agent_registry: Optional[AgentRegistry] = None,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> None:
        """Initialize the response generator with configuration from environment.

        Args:
            use_master_agent: Override to force Master Agent mode (True) or LLM mode (False).
                             If None, reads from OMNIFORGE_USE_MASTER_AGENT env var.
            agent_registry: Agent registry for Master Agent mode
            tenant_id: Tenant identifier for multi-tenancy
            user_id: User identifier (defaults to "default-user")
        """
        # Determine mode
        if use_master_agent is None:
            use_master_agent = (
                os.getenv("OMNIFORGE_USE_MASTER_AGENT", "true").lower() == "true"
            )

        self._use_master_agent = use_master_agent

        # Check if we should use placeholder mode (for testing without API keys)
        use_placeholder = (
            os.getenv("OMNIFORGE_USE_PLACEHOLDER_LLM", "false").lower() == "true"
        )

        if use_placeholder:
            self._generator = None  # Use placeholder mode
            self._master_generator = None
        elif self._use_master_agent:
            # Initialize Master Agent Response Generator
            self._master_generator = MasterResponseGenerator(
                agent_registry=agent_registry,
                tenant_id=tenant_id,
                user_id=user_id,
            )
            self._generator = None
        else:
            # Initialize standard LLM generator
            self._generator = LLMResponseGenerator()
            self._master_generator = None

    async def generate_stream(
        self,
        message: str,
        conversation_history: Optional[list] = None,
        session_id: str = "default",
    ) -> AsyncIterator[str]:
        """Generate a streaming response to the user's message.

        Routes to appropriate generator based on configuration:
        - Master Agent: Intelligent orchestration and task routing
        - LLM: Direct language model response
        - Placeholder: Testing mode without API calls

        Args:
            message: The user's input message
            conversation_history: Optional list of previous messages for context
            session_id: Stable identifier for this chat session (for multi-turn flows)

        Yields:
            Response parts as strings to be formatted as SSE chunks

        Examples:
            >>> # Master Agent mode
            >>> generator = ResponseGenerator(use_master_agent=True)
            >>> async for chunk in generator.generate_stream("Create an agent"):
            ...     print(chunk)
            🤖 Master Agent analyzing your request...

            >>> # LLM mode
            >>> generator = ResponseGenerator(use_master_agent=False)
            >>> async for chunk in generator.generate_stream("Hello"):
            ...     print(chunk)
            Hello! How can I help you today?
        """
        if self._master_generator:
            # Use Master Agent for intelligent orchestration
            async for chunk in self._master_generator.generate_stream(
                message, conversation_history=conversation_history, session_id=session_id
            ):
                yield chunk
        elif self._generator:
            # Use direct LLM generator
            async for chunk in self._generator.generate_stream(message):
                yield chunk
        else:
            # Fallback to placeholder for testing
            yield "Thank you for your message! "
            yield f'You said: "{message}" '
            yield "This is a placeholder response. "
            yield "Set OMNIFORGE_USE_MASTER_AGENT=true to enable Master Agent mode."

    def count_tokens(self, text: str) -> int:
        """Count tokens in the given text.

        Uses tiktoken if LLM generator is available, otherwise uses simple approximation.

        Args:
            text: The text to count tokens for

        Returns:
            Token count (minimum 1)

        Examples:
            >>> generator = ResponseGenerator()
            >>> generator.count_tokens("Hello, world!")
            4
        """
        if self._master_generator:
            return self._master_generator.count_tokens(text)
        elif self._generator:
            return self._generator.count_tokens(text)
        else:
            # Simple approximation: average token is ~4 characters
            return max(1, len(text) // 4)
