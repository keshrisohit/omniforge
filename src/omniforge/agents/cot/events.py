"""Reasoning-specific SSE events for streaming chain of thought updates.

This module defines event types for streaming reasoning chain updates to clients
via SSE, enabling real-time visibility into agent reasoning processes.
"""

from typing import Literal

from omniforge.agents.cot.chain import ChainMetrics, ReasoningStep
from omniforge.agents.events import BaseTaskEvent


class ChainStartedEvent(BaseTaskEvent):
    """Event emitted when a reasoning chain begins execution.

    Attributes:
        type: Event type discriminator (always "chain_started")
        task_id: ID of the task
        timestamp: When the event occurred
        chain_id: Unique identifier for the reasoning chain
    """

    type: Literal["chain_started"] = "chain_started"
    chain_id: str


class ReasoningStepEvent(BaseTaskEvent):
    """Event emitted when a new reasoning step is added to the chain.

    Attributes:
        type: Event type discriminator (always "reasoning_step")
        task_id: ID of the task
        timestamp: When the event occurred
        chain_id: Unique identifier for the reasoning chain
        step: The complete reasoning step data
    """

    type: Literal["reasoning_step"] = "reasoning_step"
    chain_id: str
    step: ReasoningStep


class ChainCompletedEvent(BaseTaskEvent):
    """Event emitted when a reasoning chain successfully completes.

    Attributes:
        type: Event type discriminator (always "chain_completed")
        task_id: ID of the task
        timestamp: When the event occurred
        chain_id: Unique identifier for the reasoning chain
        metrics: Aggregated metrics for the completed chain
    """

    type: Literal["chain_completed"] = "chain_completed"
    chain_id: str
    metrics: ChainMetrics


class ChainFailedEvent(BaseTaskEvent):
    """Event emitted when a reasoning chain fails.

    Attributes:
        type: Event type discriminator (always "chain_failed")
        task_id: ID of the task
        timestamp: When the event occurred
        chain_id: Unique identifier for the reasoning chain
        error_code: Machine-readable error code
        error_message: Human-readable error message
    """

    type: Literal["chain_failed"] = "chain_failed"
    chain_id: str
    error_code: str
    error_message: str
