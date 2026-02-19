"""Stream router for routing messages based on handoff state.

This module provides the StreamRouter class that routes incoming messages
to the correct handler based on whether an active handoff exists for the thread.
"""

import logging
from typing import AsyncIterator

from omniforge.orchestration.handoff import HandoffManager
from omniforge.orchestration.manager import OrchestrationManager

logger = logging.getLogger("omniforge.orchestration")


class StreamRouter:
    """Routes messages based on handoff state.

    This is a routing layer that directs messages to either the handoff path
    or the normal orchestration path based on active handoff state.

    Phase 1 Implementation: Placeholder routing with annotated string yields.
    Phase 2 will add real SSE forwarding without changing the interface.

    Attributes:
        _handoff_manager: Manager for handoff operations
        _orchestration_manager: Manager for multi-agent orchestration
    """

    def __init__(
        self, handoff_manager: HandoffManager, orchestration_manager: OrchestrationManager
    ) -> None:
        """Initialize the stream router.

        Args:
            handoff_manager: Manager for handoff operations
            orchestration_manager: Manager for multi-agent orchestration
        """
        self._handoff_manager = handoff_manager
        self._orchestration_manager = orchestration_manager

    async def route_message(
        self, thread_id: str, tenant_id: str, user_id: str, message: str
    ) -> AsyncIterator[str]:
        """Route message to correct handler based on handoff state.

        Phase 1: Yields annotated strings indicating routing path.
        Phase 2: Will forward via A2AClient SSE for handoff or
        delegate via OrchestrationManager for normal flow.

        Args:
            thread_id: Conversation thread identifier
            tenant_id: Tenant identifier for multi-tenancy
            user_id: User identifier
            message: Message to route

        Yields:
            Annotated strings indicating routing path and target

        Examples:
            Active handoff: "[HANDOFF:agent-123] User message here"
            No handoff: "[ORCHESTRATOR] User message here"
        """
        # Check for active handoff
        active_handoff = await self._handoff_manager.get_active_handoff(thread_id, tenant_id)

        if active_handoff is not None:
            # Route to handoff path with target agent ID
            logger.debug(
                "Message routed to handoff",
                extra={
                    "thread_id": thread_id,
                    "tenant_id": tenant_id,
                    "route_type": "handoff",
                    "target_agent": active_handoff.target_agent_id,
                },
            )
            # Phase 1: Placeholder - just yield annotated message
            # Phase 2: Will use A2AClient to forward via SSE
            yield f"[HANDOFF:{active_handoff.target_agent_id}] {message}"
        else:
            # Route to normal orchestration path
            logger.debug(
                "Message routed to orchestrator",
                extra={"thread_id": thread_id, "tenant_id": tenant_id, "route_type": "normal"},
            )
            # Phase 1: Placeholder - just yield annotated message
            # Phase 2: Will delegate via OrchestrationManager
            yield f"[ORCHESTRATOR] {message}"

    async def is_handoff_active(self, thread_id: str, tenant_id: str) -> bool:
        """Check if there is an active handoff for the thread.

        Args:
            thread_id: Conversation thread identifier
            tenant_id: Tenant identifier for multi-tenancy

        Returns:
            True if there is an active handoff, False otherwise
        """
        active_handoff = await self._handoff_manager.get_active_handoff(thread_id, tenant_id)
        return active_handoff is not None
