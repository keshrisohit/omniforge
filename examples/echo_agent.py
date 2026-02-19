"""Sample EchoAgent implementation for demonstration purposes.

This module provides a simple agent that echoes back user messages,
demonstrating the complete agent lifecycle including task processing,
message handling, and event streaming.
"""

from datetime import datetime
from typing import AsyncIterator

from omniforge.agents.base import BaseAgent
from omniforge.agents.events import (
    TaskDoneEvent,
    TaskEvent,
    TaskMessageEvent,
    TaskStatusEvent,
)
from omniforge.agents.models import (
    AgentCapabilities,
    AgentIdentity,
    AgentSkill,
    SkillInputMode,
    SkillOutputMode,
    TextPart,
)
from omniforge.tasks.models import Task, TaskState


class EchoAgent(BaseAgent):
    """A simple agent that echoes back messages with a friendly response.

    This agent demonstrates:
    - Basic agent setup with identity, capabilities, and skills
    - Task processing with event streaming
    - Message handling for multi-turn conversations
    - Proper task state transitions
    """

    identity = AgentIdentity(
        id="echo-agent",
        name="Echo Agent",
        description="A friendly agent that echoes your messages back to you",
        version="1.0.0",
    )

    capabilities = AgentCapabilities(
        streaming=True,
        multi_turn=True,
        delegation=False,
    )

    skills = [
        AgentSkill(
            id="echo-skill",
            name="Echo Messages",
            description="Echoes back any message you send with a friendly response",
            input_modes=[SkillInputMode.TEXT],
            output_modes=[SkillOutputMode.TEXT],
            tags=["demo", "echo", "conversation"],
        )
    ]

    async def process_task(self, task: Task) -> AsyncIterator[TaskEvent]:
        """Process a task by echoing back the initial message.

        Args:
            task: The task to process containing initial messages

        Yields:
            TaskEvent objects showing task progress and responses
        """
        # Notify that we're starting work
        yield TaskStatusEvent(
            task_id=task.id,
            timestamp=datetime.utcnow(),
            state=TaskState.WORKING,
            message="Starting to process your message...",
        )

        # Extract the user's message from the task
        user_message = ""
        if task.messages:
            for msg in task.messages:
                for part in msg.parts:
                    if part.type == "text":
                        user_message += part.text + " "

        user_message = user_message.strip() or "Hello!"

        # Send a friendly echo response
        response = f"Echo: You said '{user_message}'. How can I help you further?"

        yield TaskMessageEvent(
            task_id=task.id,
            timestamp=datetime.utcnow(),
            message_parts=[TextPart(text=response)],
            is_partial=False,
        )

        # Mark the task as completed
        yield TaskDoneEvent(
            task_id=task.id,
            timestamp=datetime.utcnow(),
            final_state=TaskState.COMPLETED,
        )

    def handle_message(self, task_id: str, message: str) -> None:
        """Handle follow-up messages in a conversation.

        Args:
            task_id: The ID of the task receiving the message
            message: The message content from the user

        Note:
            In a real implementation, this would trigger new event streaming.
            For this demo, we just log that we received the message.
        """
        print(f"[EchoAgent] Received message for task {task_id}: {message}")
