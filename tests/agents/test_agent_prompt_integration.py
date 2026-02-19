"""Tests for agent prompt configuration integration."""

from typing import AsyncIterator
from uuid import uuid4

from omniforge.agents.base import BaseAgent
from omniforge.agents.events import TaskEvent
from omniforge.agents.models import (
    AgentCapabilities,
    AgentIdentity,
    AgentSkill,
    SkillInputMode,
    SkillOutputMode,
)
from omniforge.prompts.enums import MergeBehavior
from omniforge.prompts.sdk import PromptConfig
from omniforge.tasks.models import Task


class TestAgent(BaseAgent):
    """Test agent implementation for testing."""

    identity = AgentIdentity(
        id="test-agent",
        name="Test Agent",
        description="Agent for testing",
        version="1.0.0",
    )
    capabilities = AgentCapabilities(streaming=False)
    skills = [
        AgentSkill(
            id="test-skill",
            name="Test Skill",
            description="A test skill",
            input_modes=[SkillInputMode.TEXT],
            output_modes=[SkillOutputMode.TEXT],
        )
    ]

    async def process_task(self, task: Task) -> AsyncIterator[TaskEvent]:
        """Stub implementation for testing."""
        yield  # type: ignore[misc]


class TestAgentPromptConfigIntegration:
    """Tests for agent prompt_config integration."""

    def test_agent_without_prompt_config(self) -> None:
        """Agent without prompt_config should return empty string."""
        agent = TestAgent()
        assert agent.prompt_config is None
        assert agent.get_composed_prompt() == ""

    def test_agent_with_prompt_config(self) -> None:
        """Agent with prompt_config should return the agent_prompt."""
        config = PromptConfig(
            agent_prompt="You are a helpful assistant.",
            variables={},
        )
        agent = TestAgent(prompt_config=config)
        assert agent.prompt_config is config
        assert agent.get_composed_prompt() == "You are a helpful assistant."

    def test_agent_with_prompt_config_and_variables(self) -> None:
        """Agent with variables should return template (not substituted)."""
        config = PromptConfig(
            agent_prompt="You are {{ role }}. Be {{ style }}.",
            variables={"role": "assistant", "style": "helpful"},
        )
        agent = TestAgent(prompt_config=config)
        # get_composed_prompt returns the template, not substituted
        assert agent.get_composed_prompt() == "You are {{ role }}. Be {{ style }}."

    def test_agent_with_merge_behavior(self) -> None:
        """Agent with merge_behavior should store the configuration."""
        config = PromptConfig(
            agent_prompt="System: {{ system }}\nAgent: {{ agent }}",
            variables={"system": "Be helpful", "agent": "Process tasks"},
            merge_behavior={
                "context": MergeBehavior.APPEND,
                "instructions": MergeBehavior.PREPEND,
            },
        )
        agent = TestAgent(prompt_config=config)
        assert agent.prompt_config.merge_behavior["context"] == MergeBehavior.APPEND
        assert agent.prompt_config.merge_behavior["instructions"] == MergeBehavior.PREPEND

    def test_agent_initialized_with_all_parameters(self) -> None:
        """Agent should accept agent_id, tenant_id, and prompt_config."""
        agent_id = uuid4()
        config = PromptConfig(agent_prompt="Test prompt")

        agent = TestAgent(
            agent_id=agent_id,
            tenant_id="tenant-123",
            prompt_config=config,
        )

        assert agent._id == agent_id
        assert agent.tenant_id == "tenant-123"
        assert agent.prompt_config is config

    def test_agent_get_composed_prompt_ignores_variables_param(self) -> None:
        """get_composed_prompt variables parameter is for future use."""
        config = PromptConfig(
            agent_prompt="You are {{ role }}.",
            variables={"role": "assistant"},
        )
        agent = TestAgent(prompt_config=config)

        # Variables parameter doesn't affect output in basic implementation
        result = agent.get_composed_prompt(variables={"role": "different"})
        assert result == "You are {{ role }}."

    def test_multiple_agents_with_different_configs(self) -> None:
        """Multiple agents can have different prompt configurations."""
        config1 = PromptConfig(agent_prompt="Config 1")
        config2 = PromptConfig(agent_prompt="Config 2")

        agent1 = TestAgent(prompt_config=config1)
        agent2 = TestAgent(prompt_config=config2)

        assert agent1.get_composed_prompt() == "Config 1"
        assert agent2.get_composed_prompt() == "Config 2"

    def test_agent_prompt_config_is_optional(self) -> None:
        """prompt_config parameter should be optional."""
        # Should not raise any errors
        agent = TestAgent()
        assert agent.prompt_config is None

        agent_with_tenant = TestAgent(tenant_id="tenant-1")
        assert agent_with_tenant.prompt_config is None
        assert agent_with_tenant.tenant_id == "tenant-1"
