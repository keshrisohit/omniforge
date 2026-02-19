"""Cost tracking system for budget enforcement.

This module provides cost tracking for tool executions with per-task budget
enforcement, enabling billing, usage analytics, and cost control.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Protocol, Tuple


@dataclass
class CostRecord:
    """Record of a single cost event.

    Attributes:
        tenant_id: Unique tenant identifier
        task_id: Task identifier
        chain_id: Chain of thought identifier
        step_id: Step identifier within the chain
        tool_name: Name of the tool that incurred the cost
        cost_usd: Cost in USD
        tokens: Number of tokens consumed
        model: Model name (for LLM calls)
        created_at: Timestamp when cost was recorded
    """

    tenant_id: str
    task_id: str
    chain_id: str
    step_id: str
    tool_name: str
    cost_usd: float
    tokens: int
    model: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TaskBudget:
    """Budget constraints for a task.

    Attributes:
        max_cost_usd: Maximum cost in USD (None = unlimited)
        max_tokens: Maximum tokens (None = unlimited)
        max_llm_calls: Maximum LLM calls (None = unlimited)
    """

    max_cost_usd: Optional[float] = None
    max_tokens: Optional[int] = None
    max_llm_calls: Optional[int] = None


@dataclass
class TaskCostSummary:
    """Summary of costs for a task.

    Attributes:
        total_cost_usd: Total cost in USD
        total_tokens: Total tokens consumed
        llm_call_count: Number of LLM calls
    """

    total_cost_usd: float = 0.0
    total_tokens: int = 0
    llm_call_count: int = 0


class CostRepository(Protocol):
    """Protocol for cost record persistence."""

    async def save_cost_record(self, record: CostRecord) -> None:
        """Save a cost record.

        Args:
            record: Cost record to save
        """
        ...

    async def get_task_records(self, task_id: str) -> List[CostRecord]:
        """Get all cost records for a task.

        Args:
            task_id: Task identifier

        Returns:
            List of cost records for the task
        """
        ...


class CostTracker:
    """Cost tracker for budget enforcement.

    Tracks costs per task with in-memory aggregation and optional persistence.
    Thread-safe for concurrent access.

    Example:
        >>> tracker = CostTracker()
        >>> budget = TaskBudget(max_cost_usd=10.0, max_tokens=10000)
        >>> record = CostRecord(
        ...     tenant_id="tenant-1",
        ...     task_id="task-1",
        ...     chain_id="chain-1",
        ...     step_id="step-1",
        ...     tool_name="llm",
        ...     cost_usd=0.5,
        ...     tokens=100,
        ...     model="gpt-4"
        ... )
        >>> await tracker.record_cost(record)
        >>> allowed = tracker.check_budget("task-1", budget, 0.5, 100)
    """

    def __init__(self, repository: Optional[CostRepository] = None):
        """Initialize cost tracker.

        Args:
            repository: Optional repository for persistence
        """
        self._repository = repository
        self._task_summaries: Dict[str, TaskCostSummary] = {}
        self._lock = asyncio.Lock()

    async def record_cost(self, record: CostRecord) -> None:
        """Record a cost event.

        Args:
            record: Cost record to save
        """
        async with self._lock:
            # Update in-memory tracking
            if record.task_id not in self._task_summaries:
                self._task_summaries[record.task_id] = TaskCostSummary()

            summary = self._task_summaries[record.task_id]
            summary.total_cost_usd += record.cost_usd
            summary.total_tokens += record.tokens
            if record.tool_name == "llm":
                summary.llm_call_count += 1

        # Persist to repository if available (outside lock for performance)
        if self._repository:
            await self._repository.save_cost_record(record)

    def get_task_cost(self, task_id: str) -> float:
        """Get total cost for a task.

        Args:
            task_id: Task identifier

        Returns:
            Total cost in USD
        """
        summary = self._task_summaries.get(task_id)
        return summary.total_cost_usd if summary else 0.0

    def get_task_tokens(self, task_id: str) -> int:
        """Get total tokens for a task.

        Args:
            task_id: Task identifier

        Returns:
            Total tokens consumed
        """
        summary = self._task_summaries.get(task_id)
        return summary.total_tokens if summary else 0

    def get_llm_call_count(self, task_id: str) -> int:
        """Get LLM call count for a task.

        Args:
            task_id: Task identifier

        Returns:
            Number of LLM calls
        """
        summary = self._task_summaries.get(task_id)
        return summary.llm_call_count if summary else 0

    def check_budget(
        self,
        task_id: str,
        budget: TaskBudget,
        additional_cost: float = 0.0,
        additional_tokens: int = 0,
        is_llm_call: bool = False,
    ) -> bool:
        """Check if adding cost/tokens would exceed budget.

        Args:
            task_id: Task identifier
            budget: Budget constraints
            additional_cost: Additional cost to check
            additional_tokens: Additional tokens to check
            is_llm_call: Whether this is an LLM call

        Returns:
            True if within budget, False if would exceed
        """
        summary = self._task_summaries.get(task_id, TaskCostSummary())

        # Check cost limit
        if budget.max_cost_usd is not None:
            if summary.total_cost_usd + additional_cost > budget.max_cost_usd:
                return False

        # Check token limit
        if budget.max_tokens is not None:
            if summary.total_tokens + additional_tokens > budget.max_tokens:
                return False

        # Check LLM call limit
        if budget.max_llm_calls is not None and is_llm_call:
            if summary.llm_call_count + 1 > budget.max_llm_calls:
                return False

        return True

    def get_remaining_budget(
        self, task_id: str, budget: TaskBudget
    ) -> Tuple[Optional[float], Optional[int], Optional[int]]:
        """Get remaining budget for a task.

        Args:
            task_id: Task identifier
            budget: Budget constraints

        Returns:
            Tuple of (remaining_cost_usd, remaining_tokens, remaining_llm_calls)
            None values indicate unlimited budget for that dimension
        """
        summary = self._task_summaries.get(task_id, TaskCostSummary())

        remaining_cost = (
            budget.max_cost_usd - summary.total_cost_usd
            if budget.max_cost_usd is not None
            else None
        )

        remaining_tokens = (
            budget.max_tokens - summary.total_tokens
            if budget.max_tokens is not None
            else None
        )

        remaining_calls = (
            budget.max_llm_calls - summary.llm_call_count
            if budget.max_llm_calls is not None
            else None
        )

        return (remaining_cost, remaining_tokens, remaining_calls)

    def clear_task(self, task_id: str) -> None:
        """Clear tracking for a completed task.

        Args:
            task_id: Task identifier to clear
        """
        self._task_summaries.pop(task_id, None)

    def get_task_summary(self, task_id: str) -> TaskCostSummary:
        """Get cost summary for a task.

        Args:
            task_id: Task identifier

        Returns:
            Task cost summary (empty if task not found)
        """
        return self._task_summaries.get(task_id, TaskCostSummary())
