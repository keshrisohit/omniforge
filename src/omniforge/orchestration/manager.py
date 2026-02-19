"""Orchestration manager for multi-agent coordination.

This module provides the OrchestrationManager class for coordinating
tasks across multiple agents using different delegation strategies.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from omniforge.agents.events import TaskMessageEvent
from omniforge.agents.models import AgentCard, TextPart
from omniforge.conversation.sqlite_repository import SQLiteConversationRepository
from omniforge.orchestration.client import A2AClient
from omniforge.tasks.models import TaskCreateRequest

logger = logging.getLogger("omniforge.orchestration")


class DelegationStrategy(str, Enum):
    """Delegation strategies for multi-agent coordination.

    Attributes:
        PARALLEL: Execute all agents concurrently
        SEQUENTIAL: Execute agents one at a time in order
        FIRST_SUCCESS: Execute concurrently, return first successful result
    """

    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"
    FIRST_SUCCESS = "first_success"


@dataclass
class SubAgentResult:
    """Result from a sub-agent execution.

    Attributes:
        agent_id: ID of the agent that produced this result
        success: Whether the agent completed successfully
        response: Text response from the agent (None if failed)
        error: Error message if agent failed (None if successful)
        latency_ms: Execution time in milliseconds
    """

    agent_id: str
    success: bool
    response: Optional[str] = None
    error: Optional[str] = None
    latency_ms: int = 0


class OrchestrationManager:
    """Manages multi-agent orchestration and response synthesis.

    This class coordinates task delegation to multiple agents using
    various strategies and synthesizes their responses.

    Attributes:
        _client: A2A client for agent communication
        _conversation_repo: Repository for conversation persistence
    """

    def __init__(self, client: A2AClient, conversation_repo: SQLiteConversationRepository) -> None:
        """Initialize the orchestration manager.

        Args:
            client: A2A client for agent communication
            conversation_repo: Repository for conversation persistence
        """
        self._client = client
        self._conversation_repo = conversation_repo

    async def delegate_to_agents(
        self,
        thread_id: str,
        tenant_id: str,
        user_id: str,
        message: str,
        target_agent_cards: list[AgentCard],
        strategy: DelegationStrategy,
        timeout_ms: int = 30000,
    ) -> list[SubAgentResult]:
        """Delegate a task to multiple agents using the specified strategy.

        Args:
            thread_id: Conversation thread ID
            tenant_id: Tenant identifier for multi-tenancy
            user_id: User identifier
            message: Message to send to agents
            target_agent_cards: List of agent cards to delegate to
            strategy: Delegation strategy to use
            timeout_ms: Timeout in milliseconds (default: 30000)

        Returns:
            List of SubAgentResult objects, one per agent

        Raises:
            ValueError: If target_agent_cards is empty
        """
        if not target_agent_cards:
            raise ValueError("Must provide at least one target agent")

        # Log delegation start
        target_agent_ids = [card.identity.id for card in target_agent_cards]
        strategy_value = strategy.value if isinstance(strategy, DelegationStrategy) else str(strategy)
        logger.info(
            "Delegation started",
            extra={
                "thread_id": thread_id,
                "tenant_id": tenant_id,
                "strategy": strategy_value,
                "target_agents": target_agent_ids,
                "total_agents": len(target_agent_cards),
            },
        )

        start_time = time.time()

        # Route to appropriate strategy implementation
        if strategy == DelegationStrategy.PARALLEL:
            results = await self._delegate_parallel(
                thread_id, tenant_id, user_id, message, target_agent_cards, timeout_ms
            )
        elif strategy == DelegationStrategy.SEQUENTIAL:
            results = await self._delegate_sequential(
                thread_id, tenant_id, user_id, message, target_agent_cards, timeout_ms
            )
        elif strategy == DelegationStrategy.FIRST_SUCCESS:
            results = await self._delegate_first_success(
                thread_id, tenant_id, user_id, message, target_agent_cards, timeout_ms
            )
        else:
            raise ValueError(f"Unknown delegation strategy: {strategy}")

        # Log delegation completion
        total_latency_ms = int((time.time() - start_time) * 1000)
        successful_count = sum(1 for r in results if r.success)

        logger.info(
            "Delegation completed",
            extra={
                "thread_id": thread_id,
                "tenant_id": tenant_id,
                "total_agents": len(results),
                "successful_count": successful_count,
                "total_latency_ms": total_latency_ms,
            },
        )

        # Log per-agent results at DEBUG level
        for result in results:
            logger.debug(
                "Agent result",
                extra={
                    "thread_id": thread_id,
                    "agent_id": result.agent_id,
                    "success": result.success,
                    "latency_ms": result.latency_ms,
                    "error": result.error if not result.success else None,
                },
            )

        return results

    async def _delegate_parallel(
        self,
        thread_id: str,
        tenant_id: str,
        user_id: str,
        message: str,
        agent_cards: list[AgentCard],
        timeout_ms: int,
    ) -> list[SubAgentResult]:
        """Execute all agents concurrently.

        Args:
            thread_id: Conversation thread ID
            tenant_id: Tenant identifier
            user_id: User identifier
            message: Message to send
            agent_cards: List of agent cards
            timeout_ms: Timeout in milliseconds

        Returns:
            List of results from all agents
        """
        # Create tasks for all agents
        tasks = [
            self._execute_agent(agent_card, tenant_id, user_id, message, timeout_ms)
            for agent_card in agent_cards
        ]

        # Execute all concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert any exceptions to failed results
        return [
            (
                result
                if isinstance(result, SubAgentResult)
                else SubAgentResult(
                    agent_id="unknown",
                    success=False,
                    error=str(result),
                    latency_ms=0,
                )
            )
            for result in results
        ]

    async def _delegate_sequential(
        self,
        thread_id: str,
        tenant_id: str,
        user_id: str,
        message: str,
        agent_cards: list[AgentCard],
        timeout_ms: int,
    ) -> list[SubAgentResult]:
        """Execute agents one at a time in order.

        Args:
            thread_id: Conversation thread ID
            tenant_id: Tenant identifier
            user_id: User identifier
            message: Message to send
            agent_cards: List of agent cards
            timeout_ms: Timeout in milliseconds

        Returns:
            List of results from all agents in order
        """
        results = []
        for agent_card in agent_cards:
            result = await self._execute_agent(agent_card, tenant_id, user_id, message, timeout_ms)
            results.append(result)
        return results

    async def _delegate_first_success(
        self,
        thread_id: str,
        tenant_id: str,
        user_id: str,
        message: str,
        agent_cards: list[AgentCard],
        timeout_ms: int,
    ) -> list[SubAgentResult]:
        """Execute agents concurrently, return first successful result.

        Args:
            thread_id: Conversation thread ID
            tenant_id: Tenant identifier
            user_id: User identifier
            message: Message to send
            agent_cards: List of agent cards
            timeout_ms: Timeout in milliseconds

        Returns:
            List containing only the first successful result, or all failed results
        """
        # Create tasks (not coroutines) for all agents
        tasks = [
            asyncio.create_task(
                self._execute_agent(agent_card, tenant_id, user_id, message, timeout_ms)
            )
            for agent_card in agent_cards
        ]

        # Use asyncio.as_completed to process results as they arrive
        for task in asyncio.as_completed(tasks):
            try:
                result = await task
                if result.success:
                    # Found first success - cancel remaining tasks
                    for t in tasks:
                        if not t.done():
                            t.cancel()
                    return [result]
            except Exception:
                # Continue to next result
                continue

        # All failed - return all results
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [
            (
                result
                if isinstance(result, SubAgentResult)
                else SubAgentResult(
                    agent_id="unknown",
                    success=False,
                    error=str(result),
                    latency_ms=0,
                )
            )
            for result in results
        ]

    async def _execute_agent(
        self,
        agent_card: AgentCard,
        tenant_id: str,
        user_id: str,
        message: str,
        timeout_ms: int,
    ) -> SubAgentResult:
        """Execute a single agent and collect its response.

        Args:
            agent_card: Agent card for the target agent
            tenant_id: Tenant identifier
            user_id: User identifier
            message: Message to send
            timeout_ms: Timeout in milliseconds

        Returns:
            SubAgentResult with the agent's response or error
        """
        agent_id = agent_card.identity.id
        start_time = time.time()

        try:
            # Create task request
            request = TaskCreateRequest(
                message_parts=[TextPart(text=message)],
                tenant_id=tenant_id,
                user_id=user_id,
                parent_task_id=None,
            )

            # Collect response text from message events
            response_parts = []

            # Send task and collect events with timeout
            timeout_seconds = timeout_ms / 1000.0

            async def collect_events() -> None:
                async for event in self._client.send_task(agent_card, request):
                    # Collect text from message events
                    if isinstance(event, TaskMessageEvent):
                        for part in event.message_parts:
                            if hasattr(part, "text"):
                                response_parts.append(part.text)

            await asyncio.wait_for(collect_events(), timeout=timeout_seconds)

            # Calculate latency
            latency_ms = int((time.time() - start_time) * 1000)

            # Build response
            response = "".join(response_parts) if response_parts else None

            # Check if we got a response
            if response:
                return SubAgentResult(
                    agent_id=agent_id,
                    success=True,
                    response=response,
                    latency_ms=latency_ms,
                )
            else:
                return SubAgentResult(
                    agent_id=agent_id,
                    success=False,
                    error="No response received from agent",
                    latency_ms=latency_ms,
                )

        except asyncio.TimeoutError:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.warning(
                "Agent execution timed out",
                extra={
                    "agent_id": agent_id,
                    "tenant_id": tenant_id,
                    "timeout_ms": timeout_ms,
                    "latency_ms": latency_ms,
                },
            )
            return SubAgentResult(
                agent_id=agent_id,
                success=False,
                error=f"Agent timed out after {timeout_ms}ms",
                latency_ms=latency_ms,
            )
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.warning(
                "Agent execution failed",
                extra={
                    "agent_id": agent_id,
                    "tenant_id": tenant_id,
                    "error": str(e),
                    "latency_ms": latency_ms,
                },
            )
            return SubAgentResult(
                agent_id=agent_id,
                success=False,
                error=str(e),
                latency_ms=latency_ms,
            )

    def synthesize_responses(self, sub_results: list[SubAgentResult]) -> str:
        """Synthesize multiple agent responses into a single response.

        This performs simple text concatenation with attribution.
        Future versions may use LLM-based synthesis.

        Args:
            sub_results: List of sub-agent results to synthesize

        Returns:
            Synthesized response text

        Examples:
            No results: "No responses received from sub-agents."
            All failed: "All sub-agents failed to provide responses."
            Single success: Returns the response directly
            Multiple successes: Concatenates with attribution
        """
        if not sub_results:
            return "No responses received from sub-agents."

        # Filter successful results
        successful = [r for r in sub_results if r.success and r.response]

        if not successful:
            return "All sub-agents failed to provide responses."

        if len(successful) == 1:
            # Single success - return directly
            return successful[0].response or ""

        # Multiple successes - concatenate with attribution
        parts = []
        for result in successful:
            parts.append(f"From {result.agent_id}:\n{result.response}")

        return "\n\n".join(parts)
