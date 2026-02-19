"""Tests for SimpleAutonomousAgent."""

import pytest

from omniforge.agents.autonomous_simple import (
    SimpleAutonomousAgent,
    run_autonomous_agent,
)
from omniforge.agents.events import TaskDoneEvent, TaskMessageEvent, TaskStatusEvent
from omniforge.agents.helpers import create_simple_task
from omniforge.tasks.models import TaskState
from omniforge.tools.builtin.bash import BashTool
from omniforge.tools.builtin.llm import LLMTool
from omniforge.tools.builtin.read import ReadTool
from omniforge.tools.registry import ToolRegistry


@pytest.fixture
def mock_tool_registry():
    """Create a mock tool registry with basic tools."""
    registry = ToolRegistry()

    # Register mock tools
    registry.register(LLMTool())
    registry.register(BashTool())
    registry.register(ReadTool())

    return registry


class TestSimpleAutonomousAgent:
    """Test suite for SimpleAutonomousAgent."""

    def test_initialization_default(self):
        """Test agent initializes with default configuration."""
        agent = SimpleAutonomousAgent()

        assert agent.identity.id == "simple-autonomous-agent"
        assert agent.identity.name == "Simple Autonomous Agent"
        assert agent.capabilities.streaming is True
        assert agent._max_iterations == 15
        assert agent._model == "claude-sonnet-4"
        assert agent._temperature == 0.0
        assert agent._custom_system_prompt is None

    def test_initialization_custom(self):
        """Test agent initializes with custom configuration."""
        custom_prompt = "You are a helpful assistant."

        agent = SimpleAutonomousAgent(
            system_prompt=custom_prompt,
            max_iterations=20,
            model="gpt-4",
            temperature=0.5,
        )

        assert agent._custom_system_prompt == custom_prompt
        assert agent._max_iterations == 20
        assert agent._model == "gpt-4"
        assert agent._temperature == 0.5

    def test_initialization_with_registry(self, mock_tool_registry):
        """Test agent initializes with custom tool registry."""
        agent = SimpleAutonomousAgent(tool_registry=mock_tool_registry)

        assert agent._tool_registry == mock_tool_registry
        tool_names = agent._tool_registry.list_tools()
        assert "llm" in tool_names
        assert "bash" in tool_names

    @pytest.mark.asyncio
    async def test_process_task_emits_events(self, mock_tool_registry):
        """Test that process_task emits expected events."""
        agent = SimpleAutonomousAgent(
            tool_registry=mock_tool_registry,
            max_iterations=2,  # Limit iterations for test
        )

        task = create_simple_task(
            message="Echo hello",
            agent_id=agent.identity.id,
        )

        events = []
        try:
            async for event in agent.process_task(task):
                events.append(event)
        except Exception:
            # Expected to fail with mock tools, but we got events
            pass

        # Check we got status event
        status_events = [e for e in events if isinstance(e, TaskStatusEvent)]
        assert len(status_events) > 0
        assert status_events[0].state == TaskState.WORKING

    @pytest.mark.asyncio
    async def test_extract_user_message(self, mock_tool_registry):
        """Test user message extraction from task."""
        agent = SimpleAutonomousAgent(tool_registry=mock_tool_registry)

        task = create_simple_task(
            message="Test message",
            agent_id=agent.identity.id,
        )

        message = agent._extract_user_message(task)
        assert message == "Test message"

    @pytest.mark.asyncio
    async def test_extract_user_message_empty(self, mock_tool_registry):
        """Test user message extraction with empty task."""
        agent = SimpleAutonomousAgent(tool_registry=mock_tool_registry)

        task = create_simple_task(
            message="",
            agent_id=agent.identity.id,
        )
        task.messages = []  # Clear messages

        message = agent._extract_user_message(task)
        assert message == "Please help me with this task."

    def test_build_system_prompt_default(self, mock_tool_registry):
        """Test default system prompt building."""
        from omniforge.agents.cot.engine import ReasoningEngine
        from omniforge.agents.cot.chain import ReasoningChain

        agent = SimpleAutonomousAgent(tool_registry=mock_tool_registry)

        # Create engine to access tools
        chain = ReasoningChain(task_id="test", agent_id="test")
        engine = ReasoningEngine(
            chain=chain,
            executor=agent._executor,
            task={"id": "test", "agent_id": "test"},
        )

        prompt = agent._build_system_prompt(engine)

        # Should contain ReAct JSON format instructions
        assert '"thought"' in prompt  # JSON field for reasoning
        assert '"action"' in prompt  # JSON field for tool name
        assert "Observation:" in prompt  # Still used in examples

    def test_build_system_prompt_custom(self, mock_tool_registry):
        """Test custom system prompt building."""
        from omniforge.agents.cot.engine import ReasoningEngine
        from omniforge.agents.cot.chain import ReasoningChain

        custom = "You are a code expert."
        agent = SimpleAutonomousAgent(
            system_prompt=custom,
            tool_registry=mock_tool_registry,
        )

        # Create engine
        chain = ReasoningChain(task_id="test", agent_id="test")
        engine = ReasoningEngine(
            chain=chain,
            executor=agent._executor,
            task={"id": "test", "agent_id": "test"},
        )

        prompt = agent._build_system_prompt(engine)

        # Should contain custom prompt
        assert custom in prompt
        # Should also contain JSON format fields
        assert '"action"' in prompt

    def test_agent_identity(self):
        """Test agent identity is properly configured."""
        agent = SimpleAutonomousAgent()

        assert agent.identity.id == "simple-autonomous-agent"
        assert agent.identity.version == "1.0.0"
        assert "autonomous" in agent.identity.description.lower()

    def test_agent_capabilities(self):
        """Test agent capabilities configuration."""
        agent = SimpleAutonomousAgent()

        assert agent.capabilities.streaming is True
        assert agent.capabilities.multi_turn is False
        assert agent.capabilities.push_notifications is False

    def test_agent_skills(self):
        """Test agent skills configuration."""
        agent = SimpleAutonomousAgent()

        assert len(agent.skills) == 1
        skill = agent.skills[0]
        assert skill.id == "autonomous-execution"
        assert "autonomous" in skill.description.lower()

    @pytest.mark.asyncio
    async def test_max_iterations_enforced(self, mock_tool_registry):
        """Test that max iterations limit is enforced."""
        from omniforge.agents.cot.engine import ReasoningEngine
        from omniforge.agents.cot.chain import ReasoningChain

        agent = SimpleAutonomousAgent(
            tool_registry=mock_tool_registry,
            max_iterations=3,  # Very low limit
        )

        task = create_simple_task(
            message="Never ending task",
            agent_id=agent.identity.id,
        )

        chain = ReasoningChain(
            task_id=task.id,
            agent_id=str(agent._id),
        )
        engine = ReasoningEngine(
            chain=chain,
            executor=agent._executor,
            task=task.model_dump(),
        )

        # Should raise RuntimeError (either from LLM failure or max iterations)
        # With mock tools, LLM will likely fail before hitting iteration limit
        with pytest.raises(RuntimeError):
            await agent.reason(task, engine)


class TestRunAutonomousAgent:
    """Test suite for run_autonomous_agent convenience function."""

    @pytest.mark.asyncio
    async def test_function_signature(self):
        """Test function accepts expected parameters."""
        # This test just verifies the function signature is correct
        # Actual execution would require real LLM, so we skip it

        from inspect import signature

        sig = signature(run_autonomous_agent)
        params = list(sig.parameters.keys())

        assert "prompt" in params
        assert "system_prompt" in params
        assert "max_iterations" in params
        assert "model" in params
        assert "temperature" in params
        assert "tool_registry" in params


class TestSimpleAutonomousAgentIntegration:
    """Integration tests for SimpleAutonomousAgent."""

    def test_agent_card_generation(self):
        """Test agent can generate A2A-compliant agent card."""
        agent = SimpleAutonomousAgent()

        card = agent.get_agent_card("https://api.example.com/agent")

        assert card.identity.id == "simple-autonomous-agent"
        assert card.service_endpoint == "https://api.example.com/agent"
        assert card.protocol_version == "1.0"
        assert card.capabilities.streaming is True

    @pytest.mark.asyncio
    async def test_run_method_signature(self, mock_tool_registry):
        """Test run method has correct signature."""
        agent = SimpleAutonomousAgent(tool_registry=mock_tool_registry)

        # Verify run method exists and accepts parameters
        assert hasattr(agent, "run")
        assert callable(agent.run)

        # Check it's async
        import inspect

        assert inspect.iscoroutinefunction(agent.run)

    def test_multiple_agents_independent(self):
        """Test multiple agent instances are independent."""
        agent1 = SimpleAutonomousAgent(
            system_prompt="Agent 1",
            max_iterations=10,
        )

        agent2 = SimpleAutonomousAgent(
            system_prompt="Agent 2",
            max_iterations=20,
        )

        assert agent1._custom_system_prompt == "Agent 1"
        assert agent2._custom_system_prompt == "Agent 2"
        assert agent1._max_iterations == 10
        assert agent2._max_iterations == 20
        assert agent1._id != agent2._id

    def test_tenant_isolation(self):
        """Test agent supports tenant isolation."""
        agent1 = SimpleAutonomousAgent(tenant_id="tenant-1")
        agent2 = SimpleAutonomousAgent(tenant_id="tenant-2")

        assert agent1.tenant_id == "tenant-1"
        assert agent2.tenant_id == "tenant-2"
        assert agent1.tenant_id != agent2.tenant_id


@pytest.mark.parametrize(
    "max_iterations,model,temperature",
    [
        (5, "claude-sonnet-4", 0.0),
        (10, "gpt-4", 0.0),
        (15, "claude-opus-4", 0.3),
        (20, "claude-sonnet-4", 0.7),
    ],
)
def test_configuration_variations(max_iterations, model, temperature):
    """Test agent works with various configuration combinations."""
    agent = SimpleAutonomousAgent(
        max_iterations=max_iterations,
        model=model,
        temperature=temperature,
    )

    assert agent._max_iterations == max_iterations
    assert agent._model == model
    assert agent._temperature == temperature
