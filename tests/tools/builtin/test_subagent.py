"""Tests for sub-agent delegation tool."""

import asyncio
from datetime import datetime, timezone
from typing import AsyncIterator
from uuid import uuid4

import pytest

from omniforge.agents.base import BaseAgent
from omniforge.agents.errors import AgentNotFoundError
from omniforge.agents.events import (
    TaskArtifactEvent,
    TaskDoneEvent,
    TaskErrorEvent,
    TaskEvent,
    TaskMessageEvent,
    TaskStatusEvent,
)
from omniforge.agents.models import (
    AgentCapabilities,
    AgentIdentity,
    AgentSkill,
    Artifact,
    ArtifactType,
    SkillInputMode,
    SkillOutputMode,
    TextPart,
)
from omniforge.agents.registry import AgentRegistry
from omniforge.storage.memory import InMemoryAgentRepository
from omniforge.tasks.models import Task, TaskState
from omniforge.tools.base import ToolCallContext
from omniforge.tools.builtin.subagent import SubAgentTool


class MockSubAgent(BaseAgent):
    """Mock sub-agent for testing."""

    identity = AgentIdentity(
        id="mock-sub-agent",
        name="Mock Sub Agent",
        description="A mock agent for testing",
        version="1.0.0",
    )
    capabilities = AgentCapabilities(streaming=False, multi_turn=False)
    skills = [
        AgentSkill(
            id="test-skill",
            name="Test Skill",
            description="A test skill",
            input_modes=[SkillInputMode.TEXT],
            output_modes=[SkillOutputMode.TEXT],
        )
    ]

    def __init__(self, response_text: str = "Mock response", should_fail: bool = False):
        """Initialize mock agent.

        Args:
            response_text: Text to return in response
            should_fail: Whether to simulate failure
        """
        super().__init__()
        self.response_text = response_text
        self.should_fail = should_fail

    async def process_task(self, task: Task) -> AsyncIterator[TaskEvent]:
        """Process task and yield events."""
        # Yield status event
        yield TaskStatusEvent(
            task_id=task.id,
            timestamp=datetime.now(timezone.utc),
            state=TaskState.WORKING,
        )

        if self.should_fail:
            # Yield error event
            yield TaskErrorEvent(
                task_id=task.id,
                timestamp=datetime.now(timezone.utc),
                error_code="TEST_ERROR",
                error_message="Test error occurred",
            )
            # Yield done event with failed state
            yield TaskDoneEvent(
                task_id=task.id,
                timestamp=datetime.now(timezone.utc),
                final_state=TaskState.FAILED,
            )
        else:
            # Yield message event
            yield TaskMessageEvent(
                task_id=task.id,
                timestamp=datetime.now(timezone.utc),
                message_parts=[TextPart(text=self.response_text)],
                is_partial=False,
            )
            # Yield done event with completed state
            yield TaskDoneEvent(
                task_id=task.id,
                timestamp=datetime.now(timezone.utc),
                final_state=TaskState.COMPLETED,
            )


class SlowMockAgent(BaseAgent):
    """Mock agent that takes too long to respond."""

    identity = AgentIdentity(
        id="slow-agent",
        name="Slow Agent",
        description="A slow mock agent",
        version="1.0.0",
    )
    capabilities = AgentCapabilities(streaming=False)
    skills = [
        AgentSkill(
            id="slow-skill",
            name="Slow Skill",
            description="A slow skill",
            input_modes=[SkillInputMode.TEXT],
            output_modes=[SkillOutputMode.TEXT],
        )
    ]

    async def process_task(self, task: Task) -> AsyncIterator[TaskEvent]:
        """Process task slowly."""
        yield TaskStatusEvent(
            task_id=task.id,
            timestamp=datetime.now(timezone.utc),
            state=TaskState.WORKING,
        )
        # Sleep longer than timeout
        await asyncio.sleep(10)
        yield TaskDoneEvent(
            task_id=task.id,
            timestamp=datetime.now(timezone.utc),
            final_state=TaskState.COMPLETED,
        )


@pytest.fixture
def agent_registry():
    """Create agent registry with in-memory storage."""
    repository = InMemoryAgentRepository()
    return AgentRegistry(repository=repository)


@pytest.fixture
def tool_context() -> ToolCallContext:
    """Create test tool call context."""
    return ToolCallContext(
        correlation_id="corr-123",
        task_id="task-123",
        agent_id="parent-agent",
    )


def test_subagent_tool_initialization(agent_registry):
    """Test SubAgentTool initializes correctly."""
    tool = SubAgentTool(agent_registry=agent_registry, timeout_ms=60000)

    assert tool._agent_registry is agent_registry
    assert tool._timeout_ms == 60000


def test_subagent_tool_definition(agent_registry):
    """Test SubAgentTool definition."""
    tool = SubAgentTool(agent_registry=agent_registry)
    definition = tool.definition

    assert definition.name == "sub_agent"
    assert definition.type.value == "sub_agent"

    # Check parameters
    param_names = [p.name for p in definition.parameters]
    assert "agent_id" in param_names
    assert "task_description" in param_names
    assert "context" in param_names

    assert definition.timeout_ms == 300000  # 5 minutes default


@pytest.mark.asyncio
async def test_subagent_tool_successful_delegation(agent_registry, tool_context):
    """Test successful sub-agent delegation."""
    # Register mock agent
    mock_agent = MockSubAgent(response_text="Task completed successfully")
    await agent_registry.register(mock_agent)

    tool = SubAgentTool(agent_registry=agent_registry)

    result = await tool.execute(
        arguments={
            "agent_id": "mock-sub-agent",
            "task_description": "Do some work",
            "context": {"key": "value"},
        },
        context=tool_context,
    )

    assert result.success is True
    assert "sub_chain_id" in result.result
    assert result.result["agent_id"] == "mock-sub-agent"
    assert result.result["final_state"] == "completed"
    assert "Task completed successfully" in result.result["messages"]
    assert result.result["context"]["key"] == "value"
    assert result.duration_ms >= 0


@pytest.mark.asyncio
async def test_subagent_tool_agent_not_found(agent_registry, tool_context):
    """Test error when agent not found."""
    tool = SubAgentTool(agent_registry=agent_registry)

    result = await tool.execute(
        arguments={
            "agent_id": "nonexistent-agent",
            "task_description": "Do some work",
        },
        context=tool_context,
    )

    assert result.success is False
    assert "not found" in result.error.lower()
    assert result.duration_ms >= 0


@pytest.mark.asyncio
async def test_subagent_tool_empty_agent_id(agent_registry, tool_context):
    """Test error when agent_id is empty."""
    tool = SubAgentTool(agent_registry=agent_registry)

    result = await tool.execute(
        arguments={
            "agent_id": "",
            "task_description": "Do some work",
        },
        context=tool_context,
    )

    assert result.success is False
    assert "cannot be empty" in result.error.lower()


@pytest.mark.asyncio
async def test_subagent_tool_empty_task_description(agent_registry, tool_context):
    """Test error when task_description is empty."""
    tool = SubAgentTool(agent_registry=agent_registry)

    result = await tool.execute(
        arguments={
            "agent_id": "mock-sub-agent",
            "task_description": "",
        },
        context=tool_context,
    )

    assert result.success is False
    assert "cannot be empty" in result.error.lower()


@pytest.mark.asyncio
async def test_subagent_tool_cycle_detection(agent_registry, tool_context):
    """Test cycle detection prevents infinite loops."""
    mock_agent = MockSubAgent()
    await agent_registry.register(mock_agent)

    tool = SubAgentTool(agent_registry=agent_registry)

    # Simulate a delegation chain with a cycle
    result = await tool.execute(
        arguments={
            "agent_id": "parent-agent",  # Same as context.agent_id
            "task_description": "Do some work",
            "context": {"_agent_chain": ["agent-A", "parent-agent"]},
        },
        context=tool_context,
    )

    assert result.success is False
    assert "cycle detected" in result.error.lower()


@pytest.mark.asyncio
async def test_subagent_tool_timeout(agent_registry, tool_context):
    """Test timeout enforcement."""
    slow_agent = SlowMockAgent()
    await agent_registry.register(slow_agent)

    tool = SubAgentTool(agent_registry=agent_registry, timeout_ms=1000)  # 1 second timeout

    result = await tool.execute(
        arguments={
            "agent_id": "slow-agent",
            "task_description": "Do slow work",
        },
        context=tool_context,
    )

    assert result.success is False
    assert "timed out" in result.error.lower()


@pytest.mark.asyncio
async def test_subagent_tool_sub_agent_failure(agent_registry, tool_context):
    """Test handling of sub-agent failures."""
    failing_agent = MockSubAgent(should_fail=True)
    await agent_registry.register(failing_agent)

    tool = SubAgentTool(agent_registry=agent_registry)

    result = await tool.execute(
        arguments={
            "agent_id": "mock-sub-agent",
            "task_description": "Do some work",
        },
        context=tool_context,
    )

    assert result.success is False
    assert "failed" in result.error.lower()


@pytest.mark.asyncio
async def test_subagent_tool_context_propagation(agent_registry, tool_context):
    """Test context data is propagated to sub-agent."""
    mock_agent = MockSubAgent()
    await agent_registry.register(mock_agent)

    tool = SubAgentTool(agent_registry=agent_registry)

    custom_context = {
        "user_id": "user-123",
        "session_id": "session-456",
        "data": {"key1": "value1", "key2": "value2"},
    }

    result = await tool.execute(
        arguments={
            "agent_id": "mock-sub-agent",
            "task_description": "Process data",
            "context": custom_context,
        },
        context=tool_context,
    )

    assert result.success is True
    assert result.result["context"]["user_id"] == "user-123"
    assert result.result["context"]["session_id"] == "session-456"
    assert result.result["context"]["data"]["key1"] == "value1"
    # Check that agent chain was added
    assert "_agent_chain" in result.result["context"]
    assert "parent-agent" in result.result["context"]["_agent_chain"]


@pytest.mark.asyncio
async def test_subagent_tool_agent_chain_tracking(agent_registry, tool_context):
    """Test agent chain is tracked for cycle detection."""
    mock_agent = MockSubAgent()
    await agent_registry.register(mock_agent)

    tool = SubAgentTool(agent_registry=agent_registry)

    result = await tool.execute(
        arguments={
            "agent_id": "mock-sub-agent",
            "task_description": "Do work",
            "context": {"_agent_chain": ["agent-A", "agent-B"]},
        },
        context=tool_context,
    )

    assert result.success is True
    # Check that parent agent was added to chain
    agent_chain = result.result["context"]["_agent_chain"]
    assert "agent-A" in agent_chain
    assert "agent-B" in agent_chain
    assert "parent-agent" in agent_chain


@pytest.mark.asyncio
async def test_subagent_tool_without_context(agent_registry, tool_context):
    """Test delegation without context parameter."""
    mock_agent = MockSubAgent()
    await agent_registry.register(mock_agent)

    tool = SubAgentTool(agent_registry=agent_registry)

    result = await tool.execute(
        arguments={
            "agent_id": "mock-sub-agent",
            "task_description": "Do work",
            # No context provided
        },
        context=tool_context,
    )

    assert result.success is True
    assert result.result["context"]["_agent_chain"] == ["parent-agent"]


@pytest.mark.asyncio
async def test_subagent_tool_multiple_messages(agent_registry, tool_context):
    """Test collecting multiple messages from sub-agent."""

    class MultiMessageAgent(BaseAgent):
        identity = AgentIdentity(
            id="multi-msg-agent",
            name="Multi Message Agent",
            description="Agent that sends multiple messages",
            version="1.0.0",
        )
        capabilities = AgentCapabilities()
        skills = [
            AgentSkill(
                id="test-skill",
                name="Test",
                description="Test",
                input_modes=[SkillInputMode.TEXT],
                output_modes=[SkillOutputMode.TEXT],
            )
        ]

        async def process_task(self, task: Task) -> AsyncIterator[TaskEvent]:
            yield TaskStatusEvent(
                task_id=task.id, timestamp=datetime.now(timezone.utc), state=TaskState.WORKING
            )
            yield TaskMessageEvent(
                task_id=task.id,
                timestamp=datetime.now(timezone.utc),
                message_parts=[TextPart(text="Message 1")],
            )
            yield TaskMessageEvent(
                task_id=task.id,
                timestamp=datetime.now(timezone.utc),
                message_parts=[TextPart(text="Message 2")],
            )
            yield TaskMessageEvent(
                task_id=task.id,
                timestamp=datetime.now(timezone.utc),
                message_parts=[TextPart(text="Message 3")],
            )
            yield TaskDoneEvent(
                task_id=task.id,
                timestamp=datetime.now(timezone.utc),
                final_state=TaskState.COMPLETED,
            )

    agent = MultiMessageAgent()
    await agent_registry.register(agent)

    tool = SubAgentTool(agent_registry=agent_registry)

    result = await tool.execute(
        arguments={
            "agent_id": "multi-msg-agent",
            "task_description": "Send multiple messages",
        },
        context=tool_context,
    )

    assert result.success is True
    assert len(result.result["messages"]) == 3
    assert "Message 1" in result.result["messages"]
    assert "Message 2" in result.result["messages"]
    assert "Message 3" in result.result["messages"]


@pytest.mark.asyncio
async def test_subagent_tool_collects_artifacts(agent_registry, tool_context):
    """Artifacts emitted by sub-agent are collected and returned in result."""

    class ArtifactAgent(BaseAgent):
        identity = AgentIdentity(
            id="artifact-agent",
            name="Artifact Agent",
            description="Agent that produces artifacts",
            version="1.0.0",
        )
        capabilities = AgentCapabilities()
        skills = [
            AgentSkill(
                id="artifact-skill",
                name="Artifact",
                description="Produces an artifact",
                input_modes=[SkillInputMode.TEXT],
                output_modes=[SkillOutputMode.TEXT],
            )
        ]

        async def process_task(self, task: Task) -> AsyncIterator[TaskEvent]:
            yield TaskArtifactEvent(
                task_id=task.id,
                timestamp=datetime.now(timezone.utc),
                artifact=Artifact(
                    id="artifact-1",
                    type=ArtifactType.DOCUMENT,
                    title="Result doc",
                    inline_content="Some content here",
                    tenant_id="test-tenant",
                ),
            )
            yield TaskMessageEvent(
                task_id=task.id,
                timestamp=datetime.now(timezone.utc),
                message_parts=[TextPart(text="Done")],
            )
            yield TaskDoneEvent(
                task_id=task.id,
                timestamp=datetime.now(timezone.utc),
                final_state=TaskState.COMPLETED,
            )

    agent = ArtifactAgent()
    await agent_registry.register(agent)

    tool = SubAgentTool(agent_registry=agent_registry)
    result = await tool.execute(
        arguments={"agent_id": "artifact-agent", "task_description": "Produce artifact"},
        context=tool_context,
    )

    assert result.success is True
    assert "artifacts" in result.result
    assert len(result.result["artifacts"]) == 1
    assert result.result["artifacts"][0]["id"] == "artifact-1"
    assert result.result["artifacts"][0]["type"] == "document"


@pytest.mark.asyncio
async def test_subagent_not_found_error_names_agent(agent_registry, tool_context):
    """Agent-not-found error message must include the requested agent_id."""
    tool = SubAgentTool(agent_registry=agent_registry)

    result = await tool.execute(
        arguments={"agent_id": "missing-xyz-agent", "task_description": "Do work"},
        context=tool_context,
    )

    assert result.success is False
    assert "missing-xyz-agent" in result.error


@pytest.mark.asyncio
async def test_subagent_timeout_error_names_agent(agent_registry, tool_context):
    """Timeout error message must include the agent_id and duration."""
    slow_agent = SlowMockAgent()
    await agent_registry.register(slow_agent)

    tool = SubAgentTool(agent_registry=agent_registry, timeout_ms=500)
    result = await tool.execute(
        arguments={"agent_id": "slow-agent", "task_description": "Do slow work"},
        context=tool_context,
    )

    assert result.success is False
    assert "slow-agent" in result.error
    assert "timed out" in result.error.lower()


@pytest.mark.asyncio
async def test_subagent_failure_includes_error_code(agent_registry, tool_context):
    """When sub-agent fails with a TaskErrorEvent, error code must appear in the ToolResult."""
    failing_agent = MockSubAgent(should_fail=True)
    await agent_registry.register(failing_agent)

    tool = SubAgentTool(agent_registry=agent_registry)
    result = await tool.execute(
        arguments={"agent_id": "mock-sub-agent", "task_description": "Do work"},
        context=tool_context,
    )

    assert result.success is False
    # Error from MockSubAgent uses code "TEST_ERROR" and message "Test error occurred"
    assert "TEST_ERROR" in result.error or "Test error occurred" in result.error


@pytest.mark.asyncio
async def test_subagent_no_done_event_raises_error(agent_registry, tool_context):
    """Sub-agent that never sends a terminal event results in ToolResult failure."""

    class NoDoneAgent(BaseAgent):
        identity = AgentIdentity(
            id="no-done-agent",
            name="No Done Agent",
            description="Agent that never sends done",
            version="1.0.0",
        )
        capabilities = AgentCapabilities()
        skills = []

        async def process_task(self, task: Task) -> AsyncIterator[TaskEvent]:
            yield TaskStatusEvent(
                task_id=task.id,
                timestamp=datetime.now(timezone.utc),
                state=TaskState.WORKING,
            )
            # No TaskDoneEvent emitted

    agent = NoDoneAgent()
    await agent_registry.register(agent)

    tool = SubAgentTool(agent_registry=agent_registry)
    result = await tool.execute(
        arguments={"agent_id": "no-done-agent", "task_description": "Do work"},
        context=tool_context,
    )

    assert result.success is False
    assert "completion signal" in result.error or "no-done-agent" in result.error
