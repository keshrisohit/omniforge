"""Chat service for orchestrating chat request processing.

This module provides the main ChatService class that coordinates chat request
processing, response streaming, and event formatting.
"""

import logging
from typing import AsyncIterator, Optional
from uuid import UUID, uuid4

from omniforge.chat.master_response_generator import MasterResponseGenerator
from omniforge.chat.models import ChatRequest, DoneEvent, ErrorEvent, UsageInfo
from omniforge.chat.response_generator import ResponseGenerator
from omniforge.chat.streaming import format_chunk_event, format_done_event, format_error_event
from omniforge.conversation.models import MessageRole
from omniforge.conversation.repository import ConversationRepository

logger = logging.getLogger(__name__)


class ChatService:
    """Orchestrates chat request processing and response streaming.

    This service coordinates the chat interaction flow, including request
    validation, response generation, token counting, and SSE event formatting.
    """

    def __init__(
        self,
        response_generator: Optional[ResponseGenerator] = None,
        user_id: Optional[str] = None,
        conversation_repository: Optional[ConversationRepository] = None,
        tenant_id: Optional[str] = None,
    ) -> None:
        """Initialize the chat service.

        Args:
            response_generator: Optional ResponseGenerator for dependency injection.
                If not provided, creates a new ResponseGenerator instance.
            user_id: Optional user identifier (defaults to "default-user")
            conversation_repository: Optional repository for conversation storage.
                If None, no conversation history is stored or retrieved.
            tenant_id: Optional tenant identifier (defaults to "default-tenant")
        """
        self._response_generator = response_generator or MasterResponseGenerator(
            user_id=user_id
        )
        self._conversation_repository = conversation_repository
        self._tenant_id = tenant_id or "default-tenant"
        self._user_id = user_id or "default-user"

    async def process_chat(self, request: ChatRequest) -> AsyncIterator[str]:
        """Process a chat request and stream SSE-formatted responses.

        This method orchestrates the entire chat processing flow:
        1. Validate conversation_id if provided (raises ValueError if invalid)
        2. Create new conversation if conversation_id not provided
        3. Store user message (with error handling)
        4. Retrieve conversation history (with error handling)
        5. Stream response chunks from the response generator
        6. Accumulate content for token counting
        7. Store assistant response (with error handling)
        8. Yield formatted SSE chunk events
        9. Yield done event with usage info on completion
        10. Yield error event if an exception occurs

        Args:
            request: The ChatRequest containing the user's message and optional
                conversation_id

        Yields:
            SSE-formatted event strings (chunk events, done event, or error event)

        Raises:
            ValueError: If conversation_id is provided but not found in repository

        Examples:
            >>> service = ChatService()
            >>> request = ChatRequest(message="Hello")
            >>> async for event in service.process_chat(request):
            ...     print(event)  # SSE-formatted events
        """
        conversation_id: UUID
        conversation_history: list = []

        try:
            # Handle conversation management if repository is available
            if self._conversation_repository:
                conversation_id = await self._manage_conversation(request)
                # Get history BEFORE storing user message (to avoid including current msg)
                conversation_history = await self._get_conversation_history(
                    conversation_id
                )
                # Store user message AFTER getting history
                await self._store_user_message(conversation_id, request.message)
            else:
                # No repository - generate conversation_id if not provided
                conversation_id = request.conversation_id or uuid4()

            # Accumulate content for token counting
            accumulated_content = ""

            # Stream response chunks and yield formatted chunk events
            async for chunk in self._response_generator.generate_stream(
                request.message,
                conversation_history=conversation_history,
                session_id=str(conversation_id),
            ):
                accumulated_content += chunk
                yield format_chunk_event(chunk)

            # Store assistant response if repository is available
            if self._conversation_repository:
                await self._store_assistant_message(conversation_id, accumulated_content)

            # Calculate token usage
            token_count = self._response_generator.count_tokens(accumulated_content)
            usage = UsageInfo(tokens=token_count)

            # Yield done event with conversation_id and usage
            done_event = DoneEvent(conversation_id=conversation_id, usage=usage)
            yield format_done_event(done_event)

        except Exception as e:
            # Yield error event on any exception
            error_event = ErrorEvent(code="processing_error", message=str(e))
            yield format_error_event(error_event)

    async def _manage_conversation(self, request: ChatRequest) -> UUID:
        """Manage conversation creation or validation.

        Args:
            request: Chat request with optional conversation_id

        Returns:
            Conversation ID (validated or newly created)

        Raises:
            ValueError: If conversation_id provided but not found
        """
        if request.conversation_id:
            # Validate existing conversation
            conversation = await self._conversation_repository.get_conversation(
                request.conversation_id, self._tenant_id
            )
            if conversation is None:
                raise ValueError(
                    f"Conversation {request.conversation_id} not found or "
                    f"does not belong to tenant {self._tenant_id}"
                )
            return request.conversation_id
        else:
            # Create new conversation
            try:
                conversation = await self._conversation_repository.create_conversation(
                    tenant_id=self._tenant_id,
                    user_id=self._user_id,
                )
                logger.info(
                    f"Created new conversation {conversation.id} for "
                    f"tenant {self._tenant_id}, user {self._user_id}"
                )
                return conversation.id
            except Exception as e:
                logger.error(
                    f"Failed to create conversation for tenant {self._tenant_id}: {e}",
                    exc_info=True,
                )
                # Fall back to generating UUID (storage failure should not block)
                return uuid4()

    async def _get_conversation_history(self, conversation_id: UUID) -> list:
        """Retrieve conversation history for context.

        Args:
            conversation_id: Conversation to get history from

        Returns:
            List of recent messages (empty list on failure)
        """
        try:
            messages = await self._conversation_repository.get_recent_messages(
                conversation_id=conversation_id,
                tenant_id=self._tenant_id,
                count=20,  # Get last 20 messages for context
            )
            logger.debug(
                f"Retrieved {len(messages)} messages from conversation {conversation_id}"
            )
            return messages
        except Exception as e:
            logger.warning(
                f"Failed to retrieve conversation history for {conversation_id}: {e}",
                exc_info=True,
            )
            # Return empty list on failure (storage failure should not block)
            return []

    async def _store_user_message(self, conversation_id: UUID, content: str) -> None:
        """Store user message in conversation.

        Args:
            conversation_id: Conversation to add message to
            content: User message content
        """
        try:
            message = await self._conversation_repository.add_message(
                conversation_id=conversation_id,
                tenant_id=self._tenant_id,
                role=MessageRole.USER,
                content=content,
            )
            logger.debug(f"Stored user message {message.id} in conversation {conversation_id}")
        except Exception as e:
            logger.warning(
                f"Failed to store user message in conversation {conversation_id}: {e}",
                exc_info=True,
            )
            # Continue on failure (storage failure should not block response)

    async def _store_assistant_message(
        self, conversation_id: UUID, content: str
    ) -> None:
        """Store assistant response in conversation.

        Args:
            conversation_id: Conversation to add message to
            content: Assistant response content
        """
        try:
            message = await self._conversation_repository.add_message(
                conversation_id=conversation_id,
                tenant_id=self._tenant_id,
                role=MessageRole.ASSISTANT,
                content=content,
            )
            logger.debug(
                f"Stored assistant message {message.id} in conversation {conversation_id}"
            )
        except Exception as e:
            logger.warning(
                f"Failed to store assistant message in conversation {conversation_id}: {e}",
                exc_info=True,
            )
            # Continue on failure (storage failure should not block response)
