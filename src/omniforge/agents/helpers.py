"""Helper utilities for simplified agent creation.

This module provides convenience functions that reduce boilerplate when
creating and using agents.
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from omniforge.agents.models import TextPart
from omniforge.tasks.models import Task, TaskMessage, TaskState


def extract_user_message(task: Task) -> str:
    """Extract concatenated text from all user messages in a task.

    Args:
        task: The task containing messages

    Returns:
        Concatenated text from all user message parts, or empty string if none

    Example:
        >>> task = Task(...)
        >>> text = extract_user_message(task)
        >>> print(text)  # "Hello, how are you?"
    """
    text_parts = []

    if task.messages:
        for msg in task.messages:
            if msg.role == "user":
                for part in msg.parts:
                    if hasattr(part, "text"):  # TextPart
                        text_parts.append(part.text)

    return " ".join(text_parts).strip()


def get_latest_user_message(task: Task) -> str:
    """Get text from the most recent user message.

    Args:
        task: The task containing messages

    Returns:
        Text from the latest user message, or empty string if none

    Example:
        >>> task = Task(...)
        >>> text = get_latest_user_message(task)
        >>> print(text)  # "What's the weather?"
    """
    if not task.messages:
        return ""

    # Find last user message
    for msg in reversed(task.messages):
        if msg.role == "user":
            for part in msg.parts:
                if hasattr(part, "text"):
                    return part.text

    return ""


def create_simple_task(
    message: str,
    agent_id: str,
    user_id: str = "default-user",
    tenant_id: Optional[str] = None,
    task_id: Optional[str] = None,
) -> Task:
    """Create a task from a simple message string.

    This eliminates the boilerplate of creating Task and TaskMessage objects
    manually, generating IDs and timestamps automatically.

    Args:
        message: The user message text
        agent_id: ID of the agent that will process this task
        user_id: User identifier (defaults to "default-user")
        tenant_id: Optional tenant identifier for multi-tenancy
        task_id: Optional specific task ID (auto-generated if not provided)

    Returns:
        A Task object ready to be processed

    Example:
        >>> task = create_simple_task(
        ...     message="Hello, agent!",
        ...     agent_id="my-agent",
        ...     user_id="user-123"
        ... )
        >>> print(task.id)  # "550e8400-e29b-41d4-a716-446655440000"
        >>> print(task.messages[0].parts[0].text)  # "Hello, agent!"
    """
    task_id = task_id or str(uuid4())
    msg_id = str(uuid4())
    now = datetime.utcnow()

    return Task(
        id=task_id,
        agent_id=agent_id,
        state=TaskState.SUBMITTED,
        messages=[
            TaskMessage(
                id=msg_id,
                role="user",
                parts=[TextPart(text=message)],
                created_at=now,
            )
        ],
        created_at=now,
        updated_at=now,
        user_id=user_id,
        tenant_id=tenant_id,
    )


def generate_agent_id(name: str) -> str:
    """Generate a URL-friendly agent ID from an agent name.

    Converts a human-readable name to a kebab-case ID suitable for use
    in URLs and as unique identifiers.

    Args:
        name: The agent name (e.g., "My Cool Agent", "DataAnalyzer")

    Returns:
        Kebab-case ID (e.g., "my-cool-agent", "data-analyzer")

    Example:
        >>> generate_agent_id("My Cool Agent")
        'my-cool-agent'
        >>> generate_agent_id("DataAnalyzer")
        'data-analyzer'
        >>> generate_agent_id("CustomerSupportAgent")
        'customer-support-agent'
    """
    import re

    # Convert CamelCase to kebab-case
    # Insert hyphen before capital letters
    name = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", name)

    # Replace spaces and underscores with hyphens
    name = re.sub(r"[\s_]+", "-", name)

    # Convert to lowercase
    name = name.lower()

    # Remove invalid characters
    name = re.sub(r"[^a-z0-9-]", "", name)

    # Remove duplicate hyphens
    name = re.sub(r"-+", "-", name)

    # Strip leading/trailing hyphens
    name = name.strip("-")

    return name
