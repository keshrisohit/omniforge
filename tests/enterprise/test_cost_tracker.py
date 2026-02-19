"""Tests for cost tracker."""

import asyncio
from datetime import datetime
from typing import List

import pytest

from omniforge.enterprise.cost_tracker import (
    CostRecord,
    CostRepository,
    CostTracker,
    TaskBudget,
    TaskCostSummary,
)


# Mock repository for testing
class MockCostRepository:
    """Mock cost repository for testing."""

    def __init__(self):
        self.records: List[CostRecord] = []

    async def save_cost_record(self, record: CostRecord) -> None:
        """Save a cost record."""
        self.records.append(record)

    async def get_task_records(self, task_id: str) -> List[CostRecord]:
        """Get all cost records for a task."""
        return [r for r in self.records if r.task_id == task_id]


def test_cost_record_creation():
    """Test CostRecord creation."""
    record = CostRecord(
        tenant_id="tenant-1",
        task_id="task-1",
        chain_id="chain-1",
        step_id="step-1",
        tool_name="llm",
        cost_usd=0.5,
        tokens=100,
        model="gpt-4",
    )

    assert record.tenant_id == "tenant-1"
    assert record.task_id == "task-1"
    assert record.chain_id == "chain-1"
    assert record.step_id == "step-1"
    assert record.tool_name == "llm"
    assert record.cost_usd == 0.5
    assert record.tokens == 100
    assert record.model == "gpt-4"
    assert isinstance(record.created_at, datetime)


def test_task_budget_creation():
    """Test TaskBudget creation."""
    budget = TaskBudget(max_cost_usd=10.0, max_tokens=10000, max_llm_calls=50)

    assert budget.max_cost_usd == 10.0
    assert budget.max_tokens == 10000
    assert budget.max_llm_calls == 50


def test_task_budget_unlimited():
    """Test TaskBudget with unlimited constraints."""
    budget = TaskBudget()

    assert budget.max_cost_usd is None
    assert budget.max_tokens is None
    assert budget.max_llm_calls is None


def test_task_cost_summary_defaults():
    """Test TaskCostSummary default values."""
    summary = TaskCostSummary()

    assert summary.total_cost_usd == 0.0
    assert summary.total_tokens == 0
    assert summary.llm_call_count == 0


def test_cost_tracker_initialization():
    """Test CostTracker initializes correctly."""
    tracker = CostTracker()

    assert tracker._repository is None
    assert len(tracker._task_summaries) == 0


def test_cost_tracker_with_repository():
    """Test CostTracker initializes with repository."""
    repository = MockCostRepository()
    tracker = CostTracker(repository=repository)

    assert tracker._repository is repository


@pytest.mark.asyncio
async def test_record_cost_basic():
    """Test basic cost recording."""
    tracker = CostTracker()
    record = CostRecord(
        tenant_id="tenant-1",
        task_id="task-1",
        chain_id="chain-1",
        step_id="step-1",
        tool_name="llm",
        cost_usd=0.5,
        tokens=100,
    )

    await tracker.record_cost(record)

    assert tracker.get_task_cost("task-1") == 0.5
    assert tracker.get_task_tokens("task-1") == 100
    assert tracker.get_llm_call_count("task-1") == 1


@pytest.mark.asyncio
async def test_record_cost_multiple():
    """Test recording multiple costs."""
    tracker = CostTracker()

    record1 = CostRecord(
        tenant_id="tenant-1",
        task_id="task-1",
        chain_id="chain-1",
        step_id="step-1",
        tool_name="llm",
        cost_usd=0.5,
        tokens=100,
    )

    record2 = CostRecord(
        tenant_id="tenant-1",
        task_id="task-1",
        chain_id="chain-1",
        step_id="step-2",
        tool_name="llm",
        cost_usd=0.3,
        tokens=60,
    )

    await tracker.record_cost(record1)
    await tracker.record_cost(record2)

    assert tracker.get_task_cost("task-1") == 0.8
    assert tracker.get_task_tokens("task-1") == 160
    assert tracker.get_llm_call_count("task-1") == 2


@pytest.mark.asyncio
async def test_record_cost_non_llm():
    """Test recording non-LLM costs."""
    tracker = CostTracker()

    record = CostRecord(
        tenant_id="tenant-1",
        task_id="task-1",
        chain_id="chain-1",
        step_id="step-1",
        tool_name="api",
        cost_usd=0.1,
        tokens=0,
    )

    await tracker.record_cost(record)

    assert tracker.get_task_cost("task-1") == 0.1
    assert tracker.get_task_tokens("task-1") == 0
    assert tracker.get_llm_call_count("task-1") == 0  # Not an LLM call


@pytest.mark.asyncio
async def test_record_cost_with_repository():
    """Test cost recording with persistence."""
    repository = MockCostRepository()
    tracker = CostTracker(repository=repository)

    record = CostRecord(
        tenant_id="tenant-1",
        task_id="task-1",
        chain_id="chain-1",
        step_id="step-1",
        tool_name="llm",
        cost_usd=0.5,
        tokens=100,
    )

    await tracker.record_cost(record)

    # Check in-memory tracking
    assert tracker.get_task_cost("task-1") == 0.5

    # Check persistence
    assert len(repository.records) == 1
    assert repository.records[0].cost_usd == 0.5


@pytest.mark.asyncio
async def test_check_budget_cost_limit():
    """Test budget checking with cost limit."""
    tracker = CostTracker()
    budget = TaskBudget(max_cost_usd=1.0)

    # Record 0.6 cost
    record = CostRecord(
        tenant_id="tenant-1",
        task_id="task-1",
        chain_id="chain-1",
        step_id="step-1",
        tool_name="llm",
        cost_usd=0.6,
        tokens=100,
    )
    await tracker.record_cost(record)

    # Check if 0.3 more is allowed (total 0.9, within 1.0)
    assert tracker.check_budget("task-1", budget, additional_cost=0.3) is True

    # Check if 0.5 more is allowed (total 1.1, exceeds 1.0)
    assert tracker.check_budget("task-1", budget, additional_cost=0.5) is False


@pytest.mark.asyncio
async def test_check_budget_token_limit():
    """Test budget checking with token limit."""
    tracker = CostTracker()
    budget = TaskBudget(max_tokens=1000)

    # Record 600 tokens
    record = CostRecord(
        tenant_id="tenant-1",
        task_id="task-1",
        chain_id="chain-1",
        step_id="step-1",
        tool_name="llm",
        cost_usd=0.1,
        tokens=600,
    )
    await tracker.record_cost(record)

    # Check if 300 more tokens allowed (total 900, within 1000)
    assert tracker.check_budget("task-1", budget, additional_tokens=300) is True

    # Check if 500 more tokens allowed (total 1100, exceeds 1000)
    assert tracker.check_budget("task-1", budget, additional_tokens=500) is False


@pytest.mark.asyncio
async def test_check_budget_llm_call_limit():
    """Test budget checking with LLM call limit."""
    tracker = CostTracker()
    budget = TaskBudget(max_llm_calls=3)

    # Record 2 LLM calls
    for i in range(2):
        record = CostRecord(
            tenant_id="tenant-1",
            task_id="task-1",
            chain_id="chain-1",
            step_id=f"step-{i}",
            tool_name="llm",
            cost_usd=0.1,
            tokens=100,
        )
        await tracker.record_cost(record)

    # Check if 1 more LLM call allowed (total 3, within limit)
    assert tracker.check_budget("task-1", budget, is_llm_call=True) is True

    # Record 1 more LLM call
    record = CostRecord(
        tenant_id="tenant-1",
        task_id="task-1",
        chain_id="chain-1",
        step_id="step-3",
        tool_name="llm",
        cost_usd=0.1,
        tokens=100,
    )
    await tracker.record_cost(record)

    # Check if 1 more LLM call allowed (total would be 4, exceeds 3)
    assert tracker.check_budget("task-1", budget, is_llm_call=True) is False


@pytest.mark.asyncio
async def test_check_budget_combined_limits():
    """Test budget checking with multiple limits."""
    tracker = CostTracker()
    budget = TaskBudget(max_cost_usd=1.0, max_tokens=1000, max_llm_calls=5)

    # Record cost and tokens
    record = CostRecord(
        tenant_id="tenant-1",
        task_id="task-1",
        chain_id="chain-1",
        step_id="step-1",
        tool_name="llm",
        cost_usd=0.8,
        tokens=800,
    )
    await tracker.record_cost(record)

    # Check if adding 0.1 cost and 100 tokens is allowed (within all limits)
    assert (
        tracker.check_budget(
            "task-1", budget, additional_cost=0.1, additional_tokens=100, is_llm_call=True
        )
        is True
    )

    # Check if adding 0.3 cost would exceed (token limit OK, cost exceeds)
    assert (
        tracker.check_budget(
            "task-1", budget, additional_cost=0.3, additional_tokens=100, is_llm_call=True
        )
        is False
    )


@pytest.mark.asyncio
async def test_check_budget_new_task():
    """Test budget checking for new task with no history."""
    tracker = CostTracker()
    budget = TaskBudget(max_cost_usd=1.0, max_tokens=1000)

    # New task should allow any amount within budget
    assert tracker.check_budget("new-task", budget, additional_cost=0.5) is True
    assert tracker.check_budget("new-task", budget, additional_tokens=500) is True


@pytest.mark.asyncio
async def test_get_remaining_budget():
    """Test getting remaining budget."""
    tracker = CostTracker()
    budget = TaskBudget(max_cost_usd=1.0, max_tokens=1000, max_llm_calls=5)

    # Record some usage
    record = CostRecord(
        tenant_id="tenant-1",
        task_id="task-1",
        chain_id="chain-1",
        step_id="step-1",
        tool_name="llm",
        cost_usd=0.6,
        tokens=400,
    )
    await tracker.record_cost(record)

    remaining_cost, remaining_tokens, remaining_calls = tracker.get_remaining_budget(
        "task-1", budget
    )

    assert remaining_cost == 0.4
    assert remaining_tokens == 600
    assert remaining_calls == 4


@pytest.mark.asyncio
async def test_get_remaining_budget_unlimited():
    """Test getting remaining budget with unlimited constraints."""
    tracker = CostTracker()
    budget = TaskBudget()  # All unlimited

    # Record some usage
    record = CostRecord(
        tenant_id="tenant-1",
        task_id="task-1",
        chain_id="chain-1",
        step_id="step-1",
        tool_name="llm",
        cost_usd=0.6,
        tokens=400,
    )
    await tracker.record_cost(record)

    remaining_cost, remaining_tokens, remaining_calls = tracker.get_remaining_budget(
        "task-1", budget
    )

    # All should be None (unlimited)
    assert remaining_cost is None
    assert remaining_tokens is None
    assert remaining_calls is None


@pytest.mark.asyncio
async def test_multiple_tasks_isolated():
    """Test that multiple tasks are tracked independently."""
    tracker = CostTracker()

    # Record for task-1
    record1 = CostRecord(
        tenant_id="tenant-1",
        task_id="task-1",
        chain_id="chain-1",
        step_id="step-1",
        tool_name="llm",
        cost_usd=0.5,
        tokens=100,
    )
    await tracker.record_cost(record1)

    # Record for task-2
    record2 = CostRecord(
        tenant_id="tenant-1",
        task_id="task-2",
        chain_id="chain-1",
        step_id="step-1",
        tool_name="llm",
        cost_usd=0.3,
        tokens=60,
    )
    await tracker.record_cost(record2)

    # Check isolation
    assert tracker.get_task_cost("task-1") == 0.5
    assert tracker.get_task_cost("task-2") == 0.3
    assert tracker.get_task_tokens("task-1") == 100
    assert tracker.get_task_tokens("task-2") == 60


def test_clear_task():
    """Test clearing task tracking."""
    tracker = CostTracker()

    # Add summary manually for testing
    tracker._task_summaries["task-1"] = TaskCostSummary(
        total_cost_usd=1.0, total_tokens=100, llm_call_count=2
    )

    assert tracker.get_task_cost("task-1") == 1.0

    # Clear task
    tracker.clear_task("task-1")

    # Should return 0 now
    assert tracker.get_task_cost("task-1") == 0.0


def test_get_task_summary():
    """Test getting task summary."""
    tracker = CostTracker()

    # Add summary manually for testing
    tracker._task_summaries["task-1"] = TaskCostSummary(
        total_cost_usd=1.5, total_tokens=200, llm_call_count=3
    )

    summary = tracker.get_task_summary("task-1")

    assert summary.total_cost_usd == 1.5
    assert summary.total_tokens == 200
    assert summary.llm_call_count == 3


def test_get_task_summary_not_found():
    """Test getting summary for non-existent task."""
    tracker = CostTracker()

    summary = tracker.get_task_summary("nonexistent")

    # Should return empty summary
    assert summary.total_cost_usd == 0.0
    assert summary.total_tokens == 0
    assert summary.llm_call_count == 0


@pytest.mark.asyncio
async def test_concurrent_cost_recording():
    """Test concurrent cost recording is thread-safe."""
    tracker = CostTracker()

    # Create multiple tasks that record costs concurrently
    async def record_costs(task_id: str, count: int):
        for i in range(count):
            record = CostRecord(
                tenant_id="tenant-1",
                task_id=task_id,
                chain_id="chain-1",
                step_id=f"step-{i}",
                tool_name="llm",
                cost_usd=0.1,
                tokens=10,
            )
            await tracker.record_cost(record)

    # Run 5 concurrent tasks, each recording 10 costs
    await asyncio.gather(*[record_costs("task-1", 10) for _ in range(5)])

    # Should have recorded 50 costs total
    assert tracker.get_task_cost("task-1") == pytest.approx(5.0)  # 50 * 0.1
    assert tracker.get_task_tokens("task-1") == 500  # 50 * 10
    assert tracker.get_llm_call_count("task-1") == 50
