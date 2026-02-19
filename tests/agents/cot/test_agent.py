"""Tests for CoTAgent base class."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from omniforge.agents.cot.agent import CoTAgent
from omniforge.agents.cot.chain import ChainStatus, ReasoningChain, ReasoningStep, StepType
from omniforge.agents.cot.engine import ReasoningEngine
from omniforge.agents.cot.events import (
    ChainCompletedEvent,
    ChainFailedEvent,
    ChainStartedEvent,
    ReasoningStepEvent,
)
from omniforge.agents.events import TaskDoneEvent, TaskStatusEvent
from omniforge.agents.models import (
    AgentCapabilities,
    AgentIdentity,
    AgentSkill,
    SkillInputMode,
    SkillOutputMode,
    TextPart,
)
from omniforge.tasks.models import Task, TaskMessage, TaskState
from omniforge.tools.registry import ToolRegistry


class SimpleCoTAgent(CoTAgent):
    """Simple CoT agent for testing."""

    identity = AgentIdentity(
        id="simple-cot-agent",
        name="Simple CoT Agent",
        description="A simple CoT agent for testing",
        version="1.0.0",
    )
    capabilities = AgentCapabilities(streaming=True)
    skills = [
        AgentSkill(
            id="simple-skill",
            name="Simple Skill",
            description="A simple test skill",
            input_modes=[SkillInputMode.TEXT],
            output_modes=[SkillOutputMode.TEXT],
        )
    ]

    async def reason(self, task: Task, engine: ReasoningEngine) -> str:
        """Simple reasoning: add thinking step and return answer."""
        engine.add_thinking("Analyzing the task")
        return "Task completed"


class FailingCoTAgent(CoTAgent):
    """CoT agent that always fails for testing error handling."""

    identity = AgentIdentity(
        id="failing-cot-agent",
        name="Failing CoT Agent",
        description="A failing CoT agent for testing",
        version="1.0.0",
    )
    capabilities = AgentCapabilities(streaming=True)
    skills = [
        AgentSkill(
            id="failing-skill",
            name="Failing Skill",
            description="A failing test skill",
            input_modes=[SkillInputMode.TEXT],
            output_modes=[SkillOutputMode.TEXT],
        )
    ]

    async def reason(self, task: Task, engine: ReasoningEngine) -> str:
        """Failing reasoning that raises exception."""
        engine.add_thinking("Starting to fail")
        raise ValueError("Intentional failure")


@pytest.fixture
def tool_registry() -> ToolRegistry:
    """Create a tool registry for testing."""
    return ToolRegistry()


@pytest.fixture
def sample_task() -> Task:
    """Create a sample task for testing."""
    return Task(
        id="task-123",
        agent_id="simple-cot-agent",
        state=TaskState.SUBMITTED,
        messages=[
            TaskMessage(
                id="msg-1",
                role="user",
                parts=[TextPart(text="Hello, solve this task")],
                created_at=datetime.utcnow(),
            )
        ],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        user_id="user-123",
    )


@pytest.mark.asyncio
async def test_cot_agent_initialization(tool_registry: ToolRegistry) -> None:
    """Test CoTAgent initialization."""
    agent = SimpleCoTAgent(tool_registry=tool_registry)

    assert agent._tool_registry == tool_registry
    assert agent._executor is not None
    assert agent._chain_repository is None
    assert agent._rate_limiter is None
    assert agent._cost_tracker is None


@pytest.mark.asyncio
async def test_cot_agent_initialization_with_custom_id(
    tool_registry: ToolRegistry,
) -> None:
    """Test CoTAgent initialization with custom agent ID."""
    agent_id = uuid4()
    agent = SimpleCoTAgent(agent_id=agent_id, tool_registry=tool_registry)

    assert agent._id == agent_id


@pytest.mark.asyncio
async def test_cot_agent_initialization_with_tenant(
    tool_registry: ToolRegistry,
) -> None:
    """Test CoTAgent initialization with tenant ID."""
    agent = SimpleCoTAgent(tenant_id="tenant-123", tool_registry=tool_registry)

    assert agent.tenant_id == "tenant-123"


@pytest.mark.asyncio
async def test_process_task_success(tool_registry: ToolRegistry, sample_task: Task) -> None:
    """Test successful task processing with reasoning chain."""
    agent = SimpleCoTAgent(tool_registry=tool_registry)

    events = []
    async for event in agent.process_task(sample_task):
        events.append(event)

    # Verify event sequence
    assert len(events) >= 4  # ChainStarted, Status, Steps..., ChainCompleted, Done

    # Check ChainStartedEvent
    assert isinstance(events[0], ChainStartedEvent)
    assert events[0].task_id == sample_task.id

    # Check TaskStatusEvent(WORKING)
    assert isinstance(events[1], TaskStatusEvent)
    assert events[1].state == TaskState.WORKING

    # Check ReasoningStepEvent(s)
    step_events = [e for e in events if isinstance(e, ReasoningStepEvent)]
    assert len(step_events) >= 1  # At least the thinking step

    # Check ChainCompletedEvent
    completed_events = [e for e in events if isinstance(e, ChainCompletedEvent)]
    assert len(completed_events) == 1
    assert completed_events[0].metrics.total_steps >= 1

    # Check TaskDoneEvent
    assert isinstance(events[-1], TaskDoneEvent)
    assert events[-1].final_state == TaskState.COMPLETED


@pytest.mark.asyncio
async def test_process_task_failure(tool_registry: ToolRegistry, sample_task: Task) -> None:
    """Test task processing with reasoning failure."""
    agent = FailingCoTAgent(tool_registry=tool_registry)

    events = []
    async for event in agent.process_task(sample_task):
        events.append(event)

    # Verify event sequence includes failure events
    assert len(events) >= 4  # ChainStarted, Status, Steps..., ChainFailed, Done

    # Check ChainStartedEvent
    assert isinstance(events[0], ChainStartedEvent)

    # Check TaskStatusEvent(WORKING)
    assert isinstance(events[1], TaskStatusEvent)
    assert events[1].state == TaskState.WORKING

    # Check ChainFailedEvent
    failed_events = [e for e in events if isinstance(e, ChainFailedEvent)]
    assert len(failed_events) == 1
    assert failed_events[0].error_code == "REASONING_FAILED"
    assert "Intentional failure" in failed_events[0].error_message

    # Check TaskDoneEvent with FAILED state
    assert isinstance(events[-1], TaskDoneEvent)
    assert events[-1].final_state == TaskState.FAILED


@pytest.mark.asyncio
async def test_chain_status_transitions(tool_registry: ToolRegistry, sample_task: Task) -> None:
    """Test that chain status transitions correctly during task processing."""
    agent = SimpleCoTAgent(tool_registry=tool_registry)

    # Track chain status through events
    chain_id = None
    events = []

    async for event in agent.process_task(sample_task):
        events.append(event)
        if isinstance(event, ChainStartedEvent):
            chain_id = event.chain_id

    assert chain_id is not None

    # Verify chain completed event has metrics
    completed_events = [e for e in events if isinstance(e, ChainCompletedEvent)]
    assert len(completed_events) == 1
    # Note: completed_at and duration are on the chain, not metrics
    # Metrics contain step counts and costs
    assert completed_events[0].metrics.total_steps >= 1


@pytest.mark.asyncio
async def test_chain_persistence_called(tool_registry: ToolRegistry, sample_task: Task) -> None:
    """Test that chain repository save is called when available."""
    mock_repository = MagicMock()
    mock_repository.save = AsyncMock()

    agent = SimpleCoTAgent(tool_registry=tool_registry, chain_repository=mock_repository)

    events = []
    async for event in agent.process_task(sample_task):
        events.append(event)

    # Verify save was called
    mock_repository.save.assert_called_once()

    # Verify the saved chain
    saved_chain = mock_repository.save.call_args[0][0]
    assert isinstance(saved_chain, ReasoningChain)
    assert saved_chain.status == ChainStatus.COMPLETED


@pytest.mark.asyncio
async def test_chain_persistence_on_failure(tool_registry: ToolRegistry, sample_task: Task) -> None:
    """Test that chain is persisted even on failure."""
    mock_repository = MagicMock()
    mock_repository.save = AsyncMock()

    agent = FailingCoTAgent(tool_registry=tool_registry, chain_repository=mock_repository)

    events = []
    async for event in agent.process_task(sample_task):
        events.append(event)

    # Verify save was called
    mock_repository.save.assert_called_once()

    # Verify the saved chain has failed status
    saved_chain = mock_repository.save.call_args[0][0]
    assert isinstance(saved_chain, ReasoningChain)
    assert saved_chain.status == ChainStatus.FAILED


@pytest.mark.asyncio
async def test_reason_with_events_yields_all_steps(
    tool_registry: ToolRegistry, sample_task: Task
) -> None:
    """Test that _reason_with_events yields events for all steps."""
    agent = SimpleCoTAgent(tool_registry=tool_registry)

    # Create a chain with multiple steps
    chain = ReasoningChain(
        task_id=sample_task.id,
        agent_id=str(agent._id),
        status=ChainStatus.RUNNING,
        steps=[
            ReasoningStep(
                step_number=1,
                type=StepType.THINKING,
                timestamp=datetime.utcnow(),
                thinking={"content": "Step 1", "confidence": 0.9},
            ),
            ReasoningStep(
                step_number=2,
                type=StepType.THINKING,
                timestamp=datetime.utcnow(),
                thinking={"content": "Step 2", "confidence": 0.8},
            ),
        ],
    )

    # Collect events
    events = []
    async for event in agent._reason_with_events(sample_task, chain):
        events.append(event)

    # Verify all steps yielded as events
    assert len(events) == 2
    assert all(isinstance(e, ReasoningStepEvent) for e in events)
    assert events[0].step.step_number == 1
    assert events[1].step.step_number == 2


@pytest.mark.asyncio
async def test_agent_inherits_base_agent_interface(
    tool_registry: ToolRegistry,
) -> None:
    """Test that CoTAgent properly inherits BaseAgent interface."""
    agent = SimpleCoTAgent(tool_registry=tool_registry)

    # Check class attributes
    assert hasattr(agent, "identity")
    assert hasattr(agent, "capabilities")
    assert hasattr(agent, "skills")

    # Check instance attributes
    assert hasattr(agent, "_id")
    assert hasattr(agent, "tenant_id")

    # Check methods
    assert hasattr(agent, "get_agent_card")
    assert hasattr(agent, "process_task")
    assert hasattr(agent, "handle_message")
    assert hasattr(agent, "cancel_task")


@pytest.mark.asyncio
async def test_agent_card_generation(tool_registry: ToolRegistry) -> None:
    """Test that CoTAgent can generate agent cards."""
    agent = SimpleCoTAgent(tool_registry=tool_registry)
    card = agent.get_agent_card("https://api.example.com/agents/simple-cot-agent")

    assert card.identity.id == "simple-cot-agent"
    assert card.identity.name == "Simple CoT Agent"
    assert card.capabilities.streaming is True
    assert card.service_endpoint == "https://api.example.com/agents/simple-cot-agent"
