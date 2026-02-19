"""Tests for SimpleAgent base class."""

from datetime import datetime

import pytest

from omniforge.agents.events import TaskDoneEvent, TaskErrorEvent, TaskMessageEvent, TaskStatusEvent
from omniforge.agents.models import TextPart
from omniforge.agents.simple import SimpleAgent
from omniforge.tasks.models import Task, TaskMessage, TaskState


class TestAgent(SimpleAgent):
    """Test agent for testing SimpleAgent functionality."""

    name = "Test Agent"
    description = "Agent for testing"
    version = "2.0.0"

    async def handle(self, message: str) -> str:
        return f"Echo: {message}"


class DocstringAgent(SimpleAgent):
    """This is a docstring description."""

    name = "Docstring Agent"

    async def handle(self, message: str) -> str:
        return "response"


class ErrorAgent(SimpleAgent):
    """Agent that raises errors for testing error handling."""

    name = "Error Agent"

    async def handle(self, message: str) -> str:
        raise ValueError("Test error")


def test_simple_agent_auto_generates_identity():
    """Test that SimpleAgent auto-generates identity from class attributes."""
    agent = TestAgent()

    assert agent.identity.id == "test-agent"
    assert agent.identity.name == "Test Agent"
    assert agent.identity.description == "Agent for testing"
    assert agent.identity.version == "2.0.0"


def test_simple_agent_uses_docstring_as_description():
    """Test that docstring is used as description if not explicitly set."""
    agent = DocstringAgent()

    assert agent.identity.description == "This is a docstring description."


def test_simple_agent_auto_generates_capabilities():
    """Test that capabilities are auto-generated."""
    agent = TestAgent()

    assert agent.capabilities.streaming is True
    assert agent.capabilities.multi_turn is False
    assert agent.capabilities.push_notifications is False
    assert agent.capabilities.hitl_support is False


def test_simple_agent_auto_generates_skills():
    """Test that skills are auto-generated."""
    agent = TestAgent()

    assert len(agent.skills) == 1
    assert agent.skills[0].id == "test-agent-skill"
    assert agent.skills[0].name == "Test Agent Skill"


@pytest.mark.asyncio
async def test_simple_agent_process_task_success():
    """Test successful task processing."""
    agent = TestAgent()

    task = Task(
        id="task-1",
        agent_id=agent.identity.id,
        state=TaskState.SUBMITTED,
        messages=[
            TaskMessage(
                id="msg-1",
                role="user",
                parts=[TextPart(text="Hello")],
                created_at=datetime.utcnow(),
            )
        ],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        user_id="user-1",
    )

    events = []
    async for event in agent.process_task(task):
        events.append(event)

    # Should have 3 events: status, message, done
    assert len(events) == 3

    # Check status event
    assert isinstance(events[0], TaskStatusEvent)
    assert events[0].state == TaskState.WORKING

    # Check message event
    assert isinstance(events[1], TaskMessageEvent)
    assert events[1].message_parts[0].text == "Echo: Hello"

    # Check done event
    assert isinstance(events[2], TaskDoneEvent)
    assert events[2].final_state == TaskState.COMPLETED


@pytest.mark.asyncio
async def test_simple_agent_process_task_error():
    """Test task processing with error."""
    agent = ErrorAgent()

    task = Task(
        id="task-1",
        agent_id=agent.identity.id,
        state=TaskState.SUBMITTED,
        messages=[
            TaskMessage(
                id="msg-1",
                role="user",
                parts=[TextPart(text="Hello")],
                created_at=datetime.utcnow(),
            )
        ],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        user_id="user-1",
    )

    events = []
    async for event in agent.process_task(task):
        events.append(event)

    # Should have 3 events: status, error, done
    assert len(events) == 3

    # Check status event
    assert isinstance(events[0], TaskStatusEvent)

    # Check error event
    assert isinstance(events[1], TaskErrorEvent)
    assert events[1].error_code == "PROCESSING_ERROR"
    assert "Test error" in events[1].error_message

    # Check done event
    assert isinstance(events[2], TaskDoneEvent)
    assert events[2].final_state == TaskState.FAILED


@pytest.mark.asyncio
async def test_simple_agent_run_api():
    """Test the simple run() API."""
    agent = TestAgent()

    response = await agent.run("Hello, agent!")

    assert response == "Echo: Hello, agent!"


@pytest.mark.asyncio
async def test_simple_agent_run_with_user_id():
    """Test run() with custom user_id."""
    agent = TestAgent()

    response = await agent.run("Test", user_id="custom-user")

    assert response == "Echo: Test"


def test_simple_agent_with_tenant_id():
    """Test creating agent with tenant_id."""
    agent = TestAgent(tenant_id="tenant-123")

    assert agent.tenant_id == "tenant-123"


def test_simple_agent_custom_streaming():
    """Test custom streaming configuration."""

    class CustomAgent(SimpleAgent):
        name = "Custom"
        streaming = False
        multi_turn = True

        async def handle(self, message: str) -> str:
            return "response"

    agent = CustomAgent()

    assert agent.capabilities.streaming is False
    assert agent.capabilities.multi_turn is True


@pytest.mark.asyncio
async def test_simple_agent_extracts_multiple_text_parts():
    """Test that agent correctly extracts multiple text parts."""
    agent = TestAgent()

    task = Task(
        id="task-1",
        agent_id=agent.identity.id,
        state=TaskState.SUBMITTED,
        messages=[
            TaskMessage(
                id="msg-1",
                role="user",
                parts=[TextPart(text="Hello"), TextPart(text="World")],
                created_at=datetime.utcnow(),
            )
        ],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        user_id="user-1",
    )

    response = await agent.run("This will be overwritten by task messages")

    # Note: run() creates a new task, so we need to test via process_task
    events = []
    async for event in agent.process_task(task):
        if isinstance(event, TaskMessageEvent):
            events.append(event)

    assert len(events) == 1
    # Message should contain concatenated text
    assert "Hello" in events[0].message_parts[0].text
    assert "World" in events[0].message_parts[0].text
