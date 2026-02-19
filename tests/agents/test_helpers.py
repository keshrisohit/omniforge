"""Tests for agent helper utilities."""

from datetime import datetime

import pytest

from omniforge.agents.helpers import (
    create_simple_task,
    extract_user_message,
    generate_agent_id,
    get_latest_user_message,
)
from omniforge.agents.models import TextPart
from omniforge.tasks.models import Task, TaskMessage, TaskState


def test_extract_user_message_with_single_message():
    """Test extracting text from a single user message."""
    task = Task(
        id="task-1",
        agent_id="agent-1",
        state=TaskState.SUBMITTED,
        messages=[
            TaskMessage(
                id="msg-1",
                role="user",
                parts=[TextPart(text="Hello, agent!")],
                created_at=datetime.utcnow(),
            )
        ],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        user_id="user-1",
    )

    result = extract_user_message(task)
    assert result == "Hello, agent!"


def test_extract_user_message_with_multiple_messages():
    """Test extracting text from multiple user messages."""
    task = Task(
        id="task-1",
        agent_id="agent-1",
        state=TaskState.SUBMITTED,
        messages=[
            TaskMessage(
                id="msg-1",
                role="user",
                parts=[TextPart(text="Hello")],
                created_at=datetime.utcnow(),
            ),
            TaskMessage(
                id="msg-2",
                role="agent",
                parts=[TextPart(text="Hi there")],
                created_at=datetime.utcnow(),
            ),
            TaskMessage(
                id="msg-3",
                role="user",
                parts=[TextPart(text="How are you?")],
                created_at=datetime.utcnow(),
            ),
        ],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        user_id="user-1",
    )

    result = extract_user_message(task)
    assert result == "Hello How are you?"


def test_extract_user_message_empty_task():
    """Test extracting from task with no messages."""
    task = Task(
        id="task-1",
        agent_id="agent-1",
        state=TaskState.SUBMITTED,
        messages=[],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        user_id="user-1",
    )

    result = extract_user_message(task)
    assert result == ""


def test_get_latest_user_message():
    """Test getting only the most recent user message."""
    task = Task(
        id="task-1",
        agent_id="agent-1",
        state=TaskState.SUBMITTED,
        messages=[
            TaskMessage(
                id="msg-1",
                role="user",
                parts=[TextPart(text="First message")],
                created_at=datetime.utcnow(),
            ),
            TaskMessage(
                id="msg-2",
                role="agent",
                parts=[TextPart(text="Agent response")],
                created_at=datetime.utcnow(),
            ),
            TaskMessage(
                id="msg-3",
                role="user",
                parts=[TextPart(text="Latest message")],
                created_at=datetime.utcnow(),
            ),
        ],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        user_id="user-1",
    )

    result = get_latest_user_message(task)
    assert result == "Latest message"


def test_create_simple_task():
    """Test creating a task from a simple message."""
    task = create_simple_task(
        message="Hello, agent!", agent_id="test-agent", user_id="user-123", tenant_id="tenant-1"
    )

    assert task.agent_id == "test-agent"
    assert task.user_id == "user-123"
    assert task.tenant_id == "tenant-1"
    assert task.state == TaskState.SUBMITTED
    assert len(task.messages) == 1
    assert task.messages[0].role == "user"
    assert task.messages[0].parts[0].text == "Hello, agent!"


def test_create_simple_task_defaults():
    """Test creating a task with default parameters."""
    task = create_simple_task(message="Test", agent_id="agent-1")

    assert task.user_id == "default-user"
    assert task.tenant_id is None


def test_generate_agent_id_from_camel_case():
    """Test converting CamelCase class names to kebab-case IDs."""
    assert generate_agent_id("MyAgent") == "my-agent"
    assert generate_agent_id("CustomerSupportAgent") == "customer-support-agent"
    assert generate_agent_id("DataAnalyzerAgent") == "data-analyzer-agent"


def test_generate_agent_id_from_spaces():
    """Test converting names with spaces."""
    assert generate_agent_id("My Cool Agent") == "my-cool-agent"
    assert generate_agent_id("Echo Agent") == "echo-agent"


def test_generate_agent_id_from_underscores():
    """Test converting names with underscores."""
    assert generate_agent_id("my_test_agent") == "my-test-agent"
    assert generate_agent_id("data_processor") == "data-processor"


def test_generate_agent_id_removes_invalid_chars():
    """Test removing invalid characters."""
    assert generate_agent_id("My@Agent!") == "myagent"
    assert generate_agent_id("Test#$Agent") == "testagent"


def test_generate_agent_id_handles_consecutive_hyphens():
    """Test handling consecutive hyphens."""
    assert generate_agent_id("My--Agent") == "my-agent"
    assert generate_agent_id("Test   Agent") == "test-agent"
