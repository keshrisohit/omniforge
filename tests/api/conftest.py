"""Shared fixtures for API route tests."""

from datetime import datetime
from typing import AsyncIterator
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import omniforge.api.routes.chat as chat_module
from omniforge.tasks.models import Task


class _MockChatAgent:
    """Minimal agent that emits a fixed event sequence without calling an LLM.

    Yields exactly: ChainStarted → Status(WORKING) → ReasoningStep(THINKING)
                    → Message → ChainCompleted → Done(COMPLETED)
    """

    async def process_task(self, task: Task) -> AsyncIterator:
        from omniforge.agents.cot.chain import (
            ChainMetrics,
            ReasoningStep,
            StepType,
            ThinkingInfo,
        )
        from omniforge.agents.cot.events import (
            ChainCompletedEvent,
            ChainStartedEvent,
            ReasoningStepEvent,
        )
        from omniforge.agents.events import TaskDoneEvent, TaskMessageEvent, TaskStatusEvent
        from omniforge.agents.models import TextPart
        from omniforge.tasks.models import TaskState

        now = datetime.utcnow()

        yield ChainStartedEvent(task_id=task.id, timestamp=now, chain_id="test-chain")
        yield TaskStatusEvent(task_id=task.id, timestamp=now, state=TaskState.WORKING)
        yield ReasoningStepEvent(
            task_id=task.id,
            timestamp=now,
            chain_id="test-chain",
            step=ReasoningStep(
                step_number=1,
                type=StepType.THINKING,
                thinking=ThinkingInfo(content="Thinking..."),
            ),
        )
        yield TaskMessageEvent(
            task_id=task.id,
            timestamp=now,
            message_parts=[TextPart(text="Hello!")],
            is_partial=False,
        )
        yield ChainCompletedEvent(
            task_id=task.id,
            timestamp=now,
            chain_id="test-chain",
            metrics=ChainMetrics(total_steps=1),
        )
        yield TaskDoneEvent(task_id=task.id, timestamp=now, final_state=TaskState.COMPLETED)


@pytest.fixture
def client() -> TestClient:
    """FastAPI TestClient with the chat router and a mocked agent."""
    from omniforge.api.middleware.error_handler import setup_error_handlers
    from omniforge.api.routes.chat import router

    app = FastAPI()
    app.include_router(router)
    setup_error_handlers(app)

    mock_agent = _MockChatAgent()

    with patch.object(chat_module, "_get_session_agent", return_value=mock_agent):
        with TestClient(app) as c:
            yield c
