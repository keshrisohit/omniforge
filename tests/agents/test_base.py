"""Tests for BaseAgent abstract class."""

from datetime import datetime
from typing import AsyncIterator
from uuid import UUID, uuid4

import pytest

from omniforge.agents import BaseAgent
from omniforge.agents.events import TaskDoneEvent, TaskEvent, TaskStatusEvent
from omniforge.agents.models import (
    AgentCapabilities,
    AgentIdentity,
    AgentSkill,
    AuthScheme,
    SkillInputMode,
    SkillOutputMode,
    TextPart,
)
from omniforge.tasks.models import Task, TaskMessage, TaskState


class ConcreteAgent(BaseAgent):
    """Concrete test agent implementation for testing BaseAgent."""

    identity = AgentIdentity(
        id="test-agent",
        name="Test Agent",
        description="A test agent for unit testing",
        version="1.0.0",
    )

    capabilities = AgentCapabilities(
        streaming=True,
        multi_turn=True,
        push_notifications=False,
        hitl_support=False,
    )

    skills = [
        AgentSkill(
            id="test-skill",
            name="Test Skill",
            description="A test skill",
            tags=["testing"],
            examples=["test example"],
            input_modes=[SkillInputMode.TEXT],
            output_modes=[SkillOutputMode.TEXT],
        )
    ]

    async def process_task(self, task: Task) -> AsyncIterator[TaskEvent]:
        """Minimal implementation of process_task for testing.

        Args:
            task: The task to process

        Yields:
            Task events indicating processing
        """
        yield TaskStatusEvent(
            task_id=task.id,
            timestamp=datetime.utcnow(),
            state=TaskState.WORKING,
            message="Processing task",
        )
        yield TaskDoneEvent(
            task_id=task.id,
            timestamp=datetime.utcnow(),
            final_state=TaskState.COMPLETED,
        )


class TestBaseAgent:
    """Tests for BaseAgent class."""

    def test_cannot_instantiate_base_agent_directly(self) -> None:
        """BaseAgent cannot be instantiated directly due to abstract methods."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            BaseAgent()  # type: ignore

    def test_create_agent_with_generated_id(self) -> None:
        """Agent should generate a UUID when no ID is provided."""
        agent = ConcreteAgent()

        assert isinstance(agent._id, UUID)
        assert agent._id is not None

    def test_create_agent_with_explicit_id(self) -> None:
        """Agent should accept an explicit UUID during initialization."""
        explicit_id = uuid4()
        agent = ConcreteAgent(agent_id=explicit_id)

        assert agent._id == explicit_id

    def test_multiple_agents_have_unique_ids(self) -> None:
        """Multiple agent instances should have unique generated IDs."""
        agent1 = ConcreteAgent()
        agent2 = ConcreteAgent()

        assert agent1._id != agent2._id

    def test_get_agent_card_returns_valid_card(self) -> None:
        """get_agent_card should return a valid A2A-compliant AgentCard."""
        agent = ConcreteAgent()
        service_endpoint = "https://api.example.com/agents/test-agent"

        card = agent.get_agent_card(service_endpoint)

        assert card.protocol_version == "1.0"
        assert card.identity == ConcreteAgent.identity
        assert card.capabilities == ConcreteAgent.capabilities
        assert card.skills == ConcreteAgent.skills
        assert card.service_endpoint == service_endpoint
        assert card.security.auth_scheme == AuthScheme.BEARER
        assert card.security.require_https is True

    def test_get_agent_card_with_different_endpoints(self) -> None:
        """get_agent_card should use the provided service endpoint."""
        agent = ConcreteAgent()
        endpoint1 = "https://api.example.com/agent1"
        endpoint2 = "https://api.example.com/agent2"

        card1 = agent.get_agent_card(endpoint1)
        card2 = agent.get_agent_card(endpoint2)

        assert card1.service_endpoint == endpoint1
        assert card2.service_endpoint == endpoint2

    def test_agent_card_includes_all_skills(self) -> None:
        """AgentCard should include all skills from the agent class."""
        agent = ConcreteAgent()
        card = agent.get_agent_card("https://api.example.com")

        assert len(card.skills) == 1
        assert card.skills[0].id == "test-skill"
        assert card.skills[0].name == "Test Skill"

    def test_agent_card_includes_capabilities(self) -> None:
        """AgentCard should include all capabilities from the agent class."""
        agent = ConcreteAgent()
        card = agent.get_agent_card("https://api.example.com")

        assert card.capabilities.streaming is True
        assert card.capabilities.multi_turn is True
        assert card.capabilities.push_notifications is False
        assert card.capabilities.hitl_support is False

    def test_agent_card_includes_identity(self) -> None:
        """AgentCard should include identity information from the agent class."""
        agent = ConcreteAgent()
        card = agent.get_agent_card("https://api.example.com")

        assert card.identity.id == "test-agent"
        assert card.identity.name == "Test Agent"
        assert card.identity.description == "A test agent for unit testing"
        assert card.identity.version == "1.0.0"

    @pytest.mark.asyncio
    async def test_process_task_yields_events(self) -> None:
        """process_task should yield TaskEvent objects."""
        agent = ConcreteAgent()
        task = Task(
            id="task-123",
            agent_id="test-agent",
            state=TaskState.SUBMITTED,
            messages=[
                TaskMessage(
                    id="msg-1",
                    role="user",
                    parts=[TextPart(text="Test message")],
                    created_at=datetime.utcnow(),
                )
            ],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            tenant_id="tenant-1",
            user_id="user-1",
        )

        events = []
        async for event in agent.process_task(task):
            events.append(event)

        assert len(events) == 2
        assert isinstance(events[0], TaskStatusEvent)
        assert events[0].state == TaskState.WORKING
        assert isinstance(events[1], TaskDoneEvent)
        assert events[1].final_state == TaskState.COMPLETED

    def test_handle_message_default_implementation(self) -> None:
        """handle_message default implementation should do nothing."""
        agent = ConcreteAgent()

        # Should not raise an error
        agent.handle_message("task-123", "Test message")

    def test_cancel_task_default_implementation(self) -> None:
        """cancel_task default implementation should do nothing."""
        agent = ConcreteAgent()

        # Should not raise an error
        agent.cancel_task("task-123")

    def test_subclass_must_implement_process_task(self) -> None:
        """Subclass without process_task implementation cannot be instantiated."""

        class IncompleteAgent(BaseAgent):
            """Agent missing process_task implementation."""

            identity = ConcreteAgent.identity
            capabilities = ConcreteAgent.capabilities
            skills = ConcreteAgent.skills

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteAgent()  # type: ignore

    def test_class_attributes_accessible_on_instance(self) -> None:
        """Class-level attributes should be accessible on agent instances."""
        agent = ConcreteAgent()

        assert agent.identity == ConcreteAgent.identity
        assert agent.capabilities == ConcreteAgent.capabilities
        assert agent.skills == ConcreteAgent.skills

    def test_agent_with_multiple_skills(self) -> None:
        """Agent should support multiple skills in agent card."""

        class MultiSkillAgent(ConcreteAgent):
            """Agent with multiple skills."""

            skills = [
                AgentSkill(
                    id="skill-1",
                    name="Skill 1",
                    description="First skill",
                    input_modes=[SkillInputMode.TEXT],
                    output_modes=[SkillOutputMode.TEXT],
                ),
                AgentSkill(
                    id="skill-2",
                    name="Skill 2",
                    description="Second skill",
                    input_modes=[SkillInputMode.FILE],
                    output_modes=[SkillOutputMode.ARTIFACT],
                ),
            ]

        agent = MultiSkillAgent()
        card = agent.get_agent_card("https://api.example.com")

        assert len(card.skills) == 2
        assert card.skills[0].id == "skill-1"
        assert card.skills[1].id == "skill-2"
