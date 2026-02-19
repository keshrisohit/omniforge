"""Tests for reasoning chain repository."""

from datetime import datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from omniforge.agents.cot.chain import (
    ChainMetrics,
    ChainStatus,
    ReasoningChain,
    ReasoningStep,
    StepType,
    ThinkingInfo,
    ToolCallInfo,
    ToolResultInfo,
    VisibilityConfig,
)
from omniforge.storage.chain_repository import ChainRepository
from omniforge.storage.database import Database, DatabaseConfig
from omniforge.storage.models import ReasoningChainModel, ReasoningStepModel
from omniforge.tools.types import ToolType, VisibilityLevel


@pytest.fixture(scope="function")
async def db():
    """Create test database for each test."""
    config = DatabaseConfig(url="sqlite+aiosqlite:///:memory:")
    database = Database(config)
    await database.create_tables()
    yield database
    await database.close()


@pytest.fixture
async def session(db):
    """Create database session shared by repository and test."""
    async with db.session() as s:
        yield s


@pytest.fixture
def repository(session):
    """Create chain repository using test session."""
    return ChainRepository(session)


def create_test_chain(task_id: str = "task-1", agent_id: str = "agent-1") -> ReasoningChain:
    """Create a test reasoning chain."""
    chain = ReasoningChain(
        task_id=task_id,
        agent_id=agent_id,
        status=ChainStatus.RUNNING,
        tenant_id="tenant-1",
    )

    # Add a thinking step
    thinking_step = ReasoningStep(
        step_number=0,
        type=StepType.THINKING,
        thinking=ThinkingInfo(content="Analyzing the problem..."),
        tokens_used=50,
        cost=0.001,
    )
    chain.add_step(thinking_step)

    # Add a tool call step
    tool_call_step = ReasoningStep(
        step_number=1,
        type=StepType.TOOL_CALL,
        tool_call=ToolCallInfo(
            tool_name="calculator",
            tool_type=ToolType.FUNCTION,
            parameters={"operation": "add", "a": 1, "b": 2},
        ),
        tokens_used=0,
        cost=0.0,
    )
    chain.add_step(tool_call_step)

    return chain


@pytest.mark.asyncio
async def test_save_chain(repository, session):
    """Test saving a chain."""
    chain = create_test_chain()

    await repository.save(chain)

    # Verify chain was saved
    stmt = select(ReasoningChainModel).where(ReasoningChainModel.id == str(chain.id))
    result = await session.execute(stmt)
    saved_model = result.scalar_one()

    assert saved_model.task_id == "task-1"
    assert saved_model.agent_id == "agent-1"
    assert saved_model.status == "running"
    assert saved_model.tenant_id == "tenant-1"


@pytest.mark.asyncio
async def test_save_chain_with_steps(repository, session):
    """Test saving a chain with multiple steps."""
    chain = create_test_chain()

    await repository.save(chain)

    # Verify steps were saved
    stmt = select(ReasoningStepModel).where(ReasoningStepModel.chain_id == str(chain.id))
    result = await session.execute(stmt)
    steps = result.scalars().all()

    assert len(steps) == 2
    assert steps[0].type == "thinking"
    assert steps[1].type == "tool_call"


@pytest.mark.asyncio
async def test_get_by_id_found(repository):
    """Test retrieving a chain by ID."""
    chain = create_test_chain()
    await repository.save(chain)

    retrieved = await repository.get_by_id(chain.id)

    assert retrieved is not None
    assert retrieved.id == chain.id
    assert retrieved.task_id == "task-1"
    assert retrieved.agent_id == "agent-1"
    assert len(retrieved.steps) == 2


@pytest.mark.asyncio
async def test_get_by_id_not_found(repository):
    """Test retrieving non-existent chain."""
    result = await repository.get_by_id(uuid4())

    assert result is None


@pytest.mark.asyncio
async def test_get_by_id_reconstructs_steps(repository):
    """Test that retrieved chain has properly reconstructed steps."""
    chain = create_test_chain()
    await repository.save(chain)

    retrieved = await repository.get_by_id(chain.id)

    # Check first step (thinking)
    step1 = retrieved.steps[0]
    assert step1.type == StepType.THINKING
    assert step1.thinking.content == "Analyzing the problem..."
    assert step1.tokens_used == 50
    assert step1.cost == 0.001

    # Check second step (tool call)
    step2 = retrieved.steps[1]
    assert step2.type == StepType.TOOL_CALL
    assert step2.tool_call.tool_name == "calculator"
    assert step2.tool_call.parameters["operation"] == "add"


@pytest.mark.asyncio
async def test_get_by_task(repository):
    """Test retrieving chains by task ID."""
    chain1 = create_test_chain(task_id="task-1")
    chain2 = create_test_chain(task_id="task-1")
    chain3 = create_test_chain(task_id="task-2")

    await repository.save(chain1)
    await repository.save(chain2)
    await repository.save(chain3)

    chains = await repository.get_by_task("task-1")

    assert len(chains) == 2
    assert all(c.task_id == "task-1" for c in chains)


@pytest.mark.asyncio
async def test_get_by_task_empty(repository):
    """Test retrieving chains for task with no chains."""
    chains = await repository.get_by_task("nonexistent")

    assert chains == []


@pytest.mark.asyncio
async def test_list_by_tenant(repository):
    """Test listing chains for a tenant."""
    chain1 = create_test_chain()
    chain1.tenant_id = "tenant-1"
    chain2 = create_test_chain()
    chain2.tenant_id = "tenant-1"
    chain3 = create_test_chain()
    chain3.tenant_id = "tenant-2"

    await repository.save(chain1)
    await repository.save(chain2)
    await repository.save(chain3)

    chains = await repository.list_by_tenant("tenant-1")

    assert len(chains) == 2
    assert all(c.tenant_id == "tenant-1" for c in chains)


@pytest.mark.asyncio
async def test_list_by_tenant_pagination(repository):
    """Test pagination for tenant chain listing."""
    # Create 5 chains for tenant-1
    for i in range(5):
        chain = create_test_chain(task_id=f"task-{i}")
        chain.tenant_id = "tenant-1"
        await repository.save(chain)

    # Get first page
    page1 = await repository.list_by_tenant("tenant-1", limit=2, offset=0)
    assert len(page1) == 2

    # Get second page
    page2 = await repository.list_by_tenant("tenant-1", limit=2, offset=2)
    assert len(page2) == 2

    # Get third page
    page3 = await repository.list_by_tenant("tenant-1", limit=2, offset=4)
    assert len(page3) == 1

    # Verify no overlap
    page1_ids = {c.id for c in page1}
    page2_ids = {c.id for c in page2}
    page3_ids = {c.id for c in page3}
    assert len(page1_ids & page2_ids) == 0
    assert len(page1_ids & page3_ids) == 0
    assert len(page2_ids & page3_ids) == 0


@pytest.mark.asyncio
async def test_delete_chain(repository, session):
    """Test deleting a chain."""
    chain = create_test_chain()
    await repository.save(chain)

    # Delete chain
    deleted = await repository.delete(chain.id)

    assert deleted is True

    # Verify chain is gone
    stmt = select(ReasoningChainModel).where(ReasoningChainModel.id == str(chain.id))
    result = await session.execute(stmt)
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_delete_chain_not_found(repository):
    """Test deleting non-existent chain."""
    deleted = await repository.delete(uuid4())

    assert deleted is False


@pytest.mark.asyncio
async def test_delete_chain_cascades_to_steps(repository, session):
    """Test that deleting a chain also deletes its steps."""
    chain = create_test_chain()
    await repository.save(chain)

    # Delete chain
    await repository.delete(chain.id)

    # Verify steps are gone
    stmt = select(ReasoningStepModel).where(ReasoningStepModel.chain_id == str(chain.id))
    result = await session.execute(stmt)
    assert len(result.scalars().all()) == 0


@pytest.mark.asyncio
async def test_chain_metrics_persisted(repository):
    """Test that chain metrics are persisted and restored."""
    chain = create_test_chain()
    chain.metrics.total_steps = 10
    chain.metrics.llm_calls = 3
    chain.metrics.tool_calls = 2
    chain.metrics.total_tokens = 500
    chain.metrics.total_cost = 0.05

    await repository.save(chain)
    retrieved = await repository.get_by_id(chain.id)

    assert retrieved.metrics.total_steps == 10
    assert retrieved.metrics.llm_calls == 3
    assert retrieved.metrics.tool_calls == 2
    assert retrieved.metrics.total_tokens == 500
    assert retrieved.metrics.total_cost == 0.05


@pytest.mark.asyncio
async def test_child_chain_ids_persisted(repository):
    """Test that child chain IDs are persisted."""
    chain = create_test_chain()
    chain.child_chain_ids = ["child-1", "child-2", "child-3"]

    await repository.save(chain)
    retrieved = await repository.get_by_id(chain.id)

    assert retrieved.child_chain_ids == ["child-1", "child-2", "child-3"]


@pytest.mark.asyncio
async def test_completed_chain(repository):
    """Test persisting a completed chain."""
    chain = create_test_chain()
    chain.status = ChainStatus.COMPLETED
    chain.completed_at = datetime.utcnow()

    await repository.save(chain)
    retrieved = await repository.get_by_id(chain.id)

    assert retrieved.status == ChainStatus.COMPLETED
    assert retrieved.completed_at is not None


@pytest.mark.asyncio
async def test_failed_chain(repository):
    """Test persisting a failed chain."""
    chain = create_test_chain()
    chain.status = ChainStatus.FAILED
    chain.completed_at = datetime.utcnow()

    await repository.save(chain)
    retrieved = await repository.get_by_id(chain.id)

    assert retrieved.status == ChainStatus.FAILED


@pytest.mark.asyncio
async def test_step_visibility_persisted(repository):
    """Test that step visibility config is persisted."""
    chain = create_test_chain()
    step = chain.steps[0]
    step.visibility = VisibilityConfig(level=VisibilityLevel.HIDDEN, reason="Security")

    await repository.save(chain)
    retrieved = await repository.get_by_id(chain.id)

    assert retrieved.steps[0].visibility.level == VisibilityLevel.HIDDEN
    assert retrieved.steps[0].visibility.reason == "Security"


@pytest.mark.asyncio
async def test_tool_result_step(repository):
    """Test persisting and retrieving tool result step."""
    chain = create_test_chain()

    tool_result_step = ReasoningStep(
        step_number=2,
        type=StepType.TOOL_RESULT,
        tool_result=ToolResultInfo(
            correlation_id="test-id", success=True, result={"answer": 42}
        ),
    )
    chain.add_step(tool_result_step)

    await repository.save(chain)
    retrieved = await repository.get_by_id(chain.id)

    result_step = retrieved.steps[2]
    assert result_step.type == StepType.TOOL_RESULT
    assert result_step.tool_result.success is True
    assert result_step.tool_result.result["answer"] == 42


@pytest.mark.asyncio
async def test_parent_step_id(repository):
    """Test persisting parent step relationships."""
    chain = create_test_chain()

    parent_step = chain.steps[0]
    child_step = ReasoningStep(
        step_number=2,
        type=StepType.THINKING,
        thinking=ThinkingInfo(content="Child thought"),
        parent_step_id=parent_step.id,
    )
    chain.add_step(child_step)

    await repository.save(chain)
    retrieved = await repository.get_by_id(chain.id)

    assert retrieved.steps[2].parent_step_id == parent_step.id


@pytest.mark.asyncio
async def test_steps_ordered_by_step_number(repository):
    """Test that steps are returned in correct order."""
    chain = create_test_chain()

    # Add more steps out of order (shouldn't happen in practice, but test it)
    for i in range(3, 10):
        step = ReasoningStep(
            step_number=i,
            type=StepType.THINKING,
            thinking=ThinkingInfo(content=f"Step {i}"),
        )
        chain.add_step(step)

    await repository.save(chain)
    retrieved = await repository.get_by_id(chain.id)

    # Verify steps are ordered
    for i, step in enumerate(retrieved.steps):
        assert step.step_number == i


@pytest.mark.asyncio
async def test_none_tenant_id(repository):
    """Test chain with no tenant ID."""
    chain = create_test_chain()
    chain.tenant_id = None

    await repository.save(chain)
    retrieved = await repository.get_by_id(chain.id)

    assert retrieved.tenant_id is None


@pytest.mark.asyncio
async def test_empty_steps_chain(repository):
    """Test persisting chain with no steps."""
    chain = ReasoningChain(
        task_id="task-1",
        agent_id="agent-1",
        status=ChainStatus.RUNNING,
        tenant_id="tenant-1",
    )

    await repository.save(chain)
    retrieved = await repository.get_by_id(chain.id)

    assert len(retrieved.steps) == 0


@pytest.mark.asyncio
async def test_list_by_tenant_ordered_by_started_at(repository):
    """Test that tenant listing returns chains ordered by start time."""
    import asyncio

    chain1 = create_test_chain(task_id="task-1")
    await repository.save(chain1)

    # Small delay to ensure different timestamps
    await asyncio.sleep(0.01)

    chain2 = create_test_chain(task_id="task-2")
    await repository.save(chain2)

    chains = await repository.list_by_tenant("tenant-1")

    # Should be ordered by started_at DESC (newest first)
    assert chains[0].task_id == "task-2"
    assert chains[1].task_id == "task-1"
