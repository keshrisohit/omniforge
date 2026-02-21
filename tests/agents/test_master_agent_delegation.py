"""Tests for MasterAgent stateful delegation architecture.

Verifies that MasterAgent correctly:
- Tracks _delegated_agent state
- Forwards messages to the delegated agent
- Clears delegation on TaskDoneEvent(COMPLETED)
- Handles cancel words when delegation is active
- Keeps delegation active on TaskStatusEvent(INPUT_REQUIRED)
"""

from datetime import datetime
from typing import AsyncIterator, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

from omniforge.agents.events import TaskDoneEvent, TaskMessageEvent, TaskStatusEvent
from omniforge.agents.master_agent import MasterAgent
from omniforge.agents.models import TextPart
from omniforge.agents.registry import AgentRegistry
from omniforge.storage.memory import InMemoryAgentRepository
from omniforge.tasks.models import Task, TaskMessage, TaskState


def make_task(
    message: str = "hello",
    user_id: str = "user-1",
    conversation_id: Optional[str] = None,
) -> Task:
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
        conversation_id=conversation_id,
    )


@pytest.fixture
def registry() -> AgentRegistry:
    return AgentRegistry(repository=InMemoryAgentRepository())


@pytest.fixture
def agent(registry: AgentRegistry) -> MasterAgent:
    return MasterAgent(agent_registry=registry)


class TestMasterAgentInit:
    """Smoke tests for MasterAgent initialisation to catch missing attributes."""

    def test_init_without_registry(self) -> None:
        agent = MasterAgent()
        assert agent._delegated_agent is None
        assert agent._last_delegation_error is None
        assert agent._mcp_initialized is False
        assert agent._mcp_manager is None

    def test_init_with_registry(self, registry: AgentRegistry) -> None:
        agent = MasterAgent(agent_registry=registry)
        assert agent._mcp_initialized is False
        assert agent._mcp_manager is None

    @pytest.mark.asyncio
    async def test_ensure_mcp_initialized_is_callable(self) -> None:
        """_ensure_mcp_initialized must not raise NameError or AttributeError."""
        agent = MasterAgent()
        # Runs without error (no MCP config set, so it's a no-op)
        await agent._ensure_mcp_initialized()
        assert agent._mcp_initialized is True


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


class TestDelegationStatusSignal:
    """Tests for the delegation WORKING status event emitted before forwarding."""

    @pytest.mark.asyncio
    async def test_delegation_emits_working_status_first(self, agent: MasterAgent) -> None:
        """First event when delegating must be TaskStatusEvent(WORKING)."""
        now = datetime.utcnow()

        async def mock_process(task: Task) -> AsyncIterator:
            yield TaskMessageEvent(
                task_id=task.id,
                timestamp=now,
                message_parts=[TextPart(text="Hello from sub-agent")],
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

        # First event must be a WORKING status
        assert isinstance(events[0], TaskStatusEvent)
        assert events[0].state == TaskState.WORKING

    @pytest.mark.asyncio
    async def test_delegation_status_message_names_agent(self, agent: MasterAgent) -> None:
        """WORKING status message should mention the delegated agent id."""
        now = datetime.utcnow()

        async def mock_process(task: Task) -> AsyncIterator:
            yield TaskDoneEvent(
                task_id=task.id,
                timestamp=now,
                final_state=TaskState.COMPLETED,
            )

        mock_sub = MagicMock()
        mock_sub.identity.id = "my-special-agent"
        mock_sub.process_task = mock_process
        agent._delegated_agent = mock_sub

        task = make_task("Something")
        events = [e async for e in agent.process_task(task)]

        status_events = [e for e in events if isinstance(e, TaskStatusEvent)]
        assert any(
            e.state == TaskState.WORKING and "my-special-agent" in (e.message or "")
            for e in status_events
        )


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
        """Single-message parent produces a 1-message subtask (no prior context to include)."""
        mock_sub = MagicMock()
        mock_sub.identity.id = "test-sub"
        agent._delegated_agent = mock_sub

        parent = make_task("Create a skill for formatting names")
        subtask = agent._make_subtask(parent)

        assert len(subtask.messages) == 1
        assert subtask.messages[0].parts[0].text == "Create a skill for formatting names"

    def test_subtask_inherits_conversation_id(self, agent: MasterAgent) -> None:
        """Subtask inherits conversation_id from parent task."""
        mock_sub = MagicMock()
        mock_sub.identity.id = "test-sub"
        agent._delegated_agent = mock_sub

        parent = make_task("hello", conversation_id="conv-abc-123")
        subtask = agent._make_subtask(parent)

        assert subtask.conversation_id == "conv-abc-123"

    def test_subtask_conversation_id_none_when_parent_has_none(self, agent: MasterAgent) -> None:
        """Subtask conversation_id is None when parent has no conversation_id."""
        mock_sub = MagicMock()
        mock_sub.identity.id = "test-sub"
        agent._delegated_agent = mock_sub

        parent = make_task("hello", conversation_id=None)
        subtask = agent._make_subtask(parent)

        assert subtask.conversation_id is None

    def test_subtask_includes_prior_context(self, agent: MasterAgent) -> None:
        """Multi-message parent includes up to 5 prior messages in subtask."""
        from omniforge.agents.models import TextPart as TP

        mock_sub = MagicMock()
        mock_sub.identity.id = "test-sub"
        agent._delegated_agent = mock_sub

        # Build a parent with 3 messages: 2 context + 1 current user message
        now = datetime.utcnow()
        parent = Task(
            id="parent-task",
            agent_id="master-agent",
            state=TaskState.SUBMITTED,
            messages=[
                TaskMessage(id="m1", role="user", parts=[TP(text="First msg")], created_at=now),
                TaskMessage(id="m2", role="agent", parts=[TP(text="First reply")], created_at=now),
                TaskMessage(id="m3", role="user", parts=[TP(text="Current msg")], created_at=now),
            ],
            created_at=now,
            updated_at=now,
            user_id="user-1",
            tenant_id="test-tenant",
        )

        subtask = agent._make_subtask(parent)

        # Should have 2 prior messages + 1 current = 3 total
        assert len(subtask.messages) == 3
        assert subtask.messages[0].parts[0].text == "First msg"
        assert subtask.messages[1].parts[0].text == "First reply"
        assert subtask.messages[2].parts[0].text == "Current msg"

    def test_subtask_prior_context_capped_at_five(self, agent: MasterAgent) -> None:
        """Subtask prior context is capped at 5 messages even if parent has more."""
        from omniforge.agents.models import TextPart as TP

        mock_sub = MagicMock()
        mock_sub.identity.id = "test-sub"
        agent._delegated_agent = mock_sub

        # Build a parent with 8 messages (7 prior + 1 current)
        now = datetime.utcnow()
        prior_msgs = [
            TaskMessage(
                id=f"m{i}",
                role="user" if i % 2 == 0 else "agent",
                parts=[TP(text=f"msg {i}")],
                created_at=now,
            )
            for i in range(7)
        ]
        current_msg = TaskMessage(
            id="m7", role="user", parts=[TP(text="current")], created_at=now
        )
        parent = Task(
            id="parent-task",
            agent_id="master-agent",
            state=TaskState.SUBMITTED,
            messages=prior_msgs + [current_msg],
            created_at=now,
            updated_at=now,
            user_id="user-1",
            tenant_id="test-tenant",
        )

        subtask = agent._make_subtask(parent)

        # Should have at most 5 prior + 1 current = 6 messages
        assert len(subtask.messages) == 6
        # The last message should be the current user message
        assert subtask.messages[-1].parts[0].text == "current"
