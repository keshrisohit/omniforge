"""Tests for MasterAgent stateful delegation architecture.

Verifies that MasterAgent correctly:
- Tracks _delegated_agent state
- Forwards messages to the delegated agent
- Clears delegation on TaskDoneEvent(COMPLETED)
- Handles cancel words when delegation is active
- Keeps delegation active on TaskStatusEvent(INPUT_REQUIRED)
"""

from datetime import datetime
from typing import AsyncIterator
from unittest.mock import AsyncMock, MagicMock

import pytest

from omniforge.agents.events import TaskDoneEvent, TaskMessageEvent, TaskStatusEvent
from omniforge.agents.master_agent import MasterAgent
from omniforge.agents.models import TextPart
from omniforge.agents.registry import AgentRegistry
from omniforge.storage.memory import InMemoryAgentRepository
from omniforge.tasks.models import Task, TaskMessage, TaskState


def make_task(message: str = "hello", user_id: str = "user-1") -> Task:
    now = datetime.utcnow()
    return Task(
        id="task-1",
        agent_id="master-agent",
        state=TaskState.SUBMITTED,
        messages=[
            TaskMessage(
                id="msg-1",
                role="user",
                parts=[TextPart(text=message)],
                created_at=now,
            )
        ],
        created_at=now,
        updated_at=now,
        user_id=user_id,
        tenant_id="test-tenant",
    )


@pytest.fixture
def registry() -> AgentRegistry:
    return AgentRegistry(repository=InMemoryAgentRepository())


@pytest.fixture
def agent(registry: AgentRegistry) -> MasterAgent:
    return MasterAgent(agent_registry=registry)


class TestDelegateToAgentTool:
    """Tests for the DelegateToAgentTool registration and behaviour."""

    def test_delegate_tool_registered_with_registry(self, agent: MasterAgent) -> None:
        """delegate_to_agent tool is available when registry is provided."""
        assert "delegate_to_agent" in agent._tool_registry.list_tools()

    def test_delegate_tool_not_registered_without_registry(self) -> None:
        """delegate_to_agent tool is NOT registered when no registry is provided."""
        agent = MasterAgent(agent_registry=None)
        assert "delegate_to_agent" not in agent._tool_registry.list_tools()

    def test_skill_creation_agent_in_local_agents(self, agent: MasterAgent) -> None:
        """SkillCreationAgent is available as a local agent for delegation."""
        tool = agent._tool_registry.get("delegate_to_agent")
        assert "skill-creation-assistant" in tool._local_agents

    def test_set_delegated_agent_callback(self, agent: MasterAgent) -> None:
        """_set_delegated_agent sets _delegated_agent on the MasterAgent."""
        mock_agent = MagicMock()
        assert agent._delegated_agent is None
        agent._set_delegated_agent(mock_agent)
        assert agent._delegated_agent is mock_agent


class TestDelegationForwarding:
    """Tests for message forwarding when delegation is active."""

    @pytest.mark.asyncio
    async def test_cancel_clears_delegation(self, agent: MasterAgent) -> None:
        """Cancel word clears the delegated agent and yields a confirmation."""
        mock_sub = MagicMock()
        agent._delegated_agent = mock_sub

        task = make_task("cancel")
        events = [e async for e in agent.process_task(task)]

        # Delegation should be cleared
        assert agent._delegated_agent is None
        # Should yield at least a message event
        message_events = [e for e in events if isinstance(e, TaskMessageEvent)]
        assert len(message_events) >= 1
        text = "".join(
            part.text for e in message_events for part in e.message_parts
        )
        assert "cancel" in text.lower() or "help" in text.lower()

    @pytest.mark.asyncio
    async def test_cancel_synonyms_clear_delegation(self, agent: MasterAgent) -> None:
        """Various cancel synonyms all clear delegation."""
        for word in ["exit", "quit", "stop", "reset"]:
            mock_sub = MagicMock()
            agent._delegated_agent = mock_sub
            task = make_task(word)
            async for _ in agent.process_task(task):
                pass
            assert agent._delegated_agent is None, f"'{word}' should clear delegation"

    @pytest.mark.asyncio
    async def test_delegation_forwards_to_sub_agent(self, agent: MasterAgent) -> None:
        """When delegated, messages are forwarded to the sub-agent."""
        now = datetime.utcnow()

        async def mock_process(task: Task) -> AsyncIterator:
            yield TaskMessageEvent(
                task_id=task.id,
                timestamp=now,
                message_parts=[TextPart(text="Sub-agent response")],
                is_partial=False,
            )
            yield TaskDoneEvent(
                task_id=task.id,
                timestamp=now,
                final_state=TaskState.COMPLETED,
            )

        mock_sub = MagicMock()
        mock_sub.identity.id = "test-agent"
        mock_sub.process_task = mock_process
        agent._delegated_agent = mock_sub

        task = make_task("Do something")
        events = [e async for e in agent.process_task(task)]

        message_events = [e for e in events if isinstance(e, TaskMessageEvent)]
        assert any(
            any(p.text == "Sub-agent response" for p in e.message_parts)
            for e in message_events
        )

    @pytest.mark.asyncio
    async def test_delegation_clears_on_completed(self, agent: MasterAgent) -> None:
        """Delegation is cleared when sub-agent yields TaskDoneEvent(COMPLETED)."""
        now = datetime.utcnow()

        async def mock_process(task: Task) -> AsyncIterator:
            yield TaskDoneEvent(
                task_id=task.id,
                timestamp=now,
                final_state=TaskState.COMPLETED,
            )

        mock_sub = MagicMock()
        mock_sub.identity.id = "test-agent"
        mock_sub.process_task = mock_process
        agent._delegated_agent = mock_sub

        task = make_task("something")
        async for _ in agent.process_task(task):
            pass

        assert agent._delegated_agent is None

    @pytest.mark.asyncio
    async def test_delegation_kept_on_input_required(self, agent: MasterAgent) -> None:
        """Delegation is NOT cleared when sub-agent yields INPUT_REQUIRED."""
        now = datetime.utcnow()

        async def mock_process(task: Task) -> AsyncIterator:
            yield TaskStatusEvent(
                task_id=task.id,
                timestamp=now,
                state=TaskState.INPUT_REQUIRED,
            )

        mock_sub = MagicMock()
        mock_sub.identity.id = "test-agent"
        mock_sub.process_task = mock_process
        agent._delegated_agent = mock_sub

        task = make_task("first turn")
        async for _ in agent.process_task(task):
            pass

        # Delegation should remain active
        assert agent._delegated_agent is mock_sub

    @pytest.mark.asyncio
    async def test_delegation_remaps_task_id(self, agent: MasterAgent) -> None:
        """Events from sub-agent have task_id remapped to parent task's id."""
        now = datetime.utcnow()

        async def mock_process(task: Task) -> AsyncIterator:
            yield TaskMessageEvent(
                task_id=task.id,  # sub-task id, different from parent
                timestamp=now,
                message_parts=[TextPart(text="response")],
            )
            yield TaskDoneEvent(
                task_id=task.id,
                timestamp=now,
                final_state=TaskState.COMPLETED,
            )

        mock_sub = MagicMock()
        mock_sub.identity.id = "test-agent"
        mock_sub.process_task = mock_process
        agent._delegated_agent = mock_sub

        task = make_task("msg")
        events = [e async for e in agent.process_task(task)]

        # All events should have the parent task id
        for event in events:
            assert event.task_id == task.id


class TestMakeSubtask:
    """Tests for _make_subtask helper."""

    def test_subtask_has_parent_id(self, agent: MasterAgent) -> None:
        """Subtask carries parent_task_id from parent task."""
        mock_sub = MagicMock()
        mock_sub.identity.id = "test-sub"
        agent._delegated_agent = mock_sub

        parent = make_task("hello")
        subtask = agent._make_subtask(parent)

        assert subtask.parent_task_id == parent.id

    def test_subtask_inherits_user_and_tenant(self, agent: MasterAgent) -> None:
        """Subtask inherits user_id and tenant_id from parent."""
        mock_sub = MagicMock()
        mock_sub.identity.id = "test-sub"
        agent._delegated_agent = mock_sub

        parent = make_task("hello", user_id="my-user")
        subtask = agent._make_subtask(parent)

        assert subtask.user_id == "my-user"
        assert subtask.tenant_id == "test-tenant"

    def test_subtask_contains_user_message(self, agent: MasterAgent) -> None:
        """Subtask contains the latest user message from the parent."""
        mock_sub = MagicMock()
        mock_sub.identity.id = "test-sub"
        agent._delegated_agent = mock_sub

        parent = make_task("Create a skill for formatting names")
        subtask = agent._make_subtask(parent)

        assert len(subtask.messages) == 1
        assert subtask.messages[0].parts[0].text == "Create a skill for formatting names"
