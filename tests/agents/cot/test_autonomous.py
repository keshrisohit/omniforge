"""Tests for AutonomousCoTAgent with ReAct pattern."""

from datetime import datetime
from unittest.mock import patch

import pytest

from omniforge.agents.cot.autonomous import AutonomousCoTAgent, MaxIterationsError
from omniforge.agents.cot.chain import ChainStatus, ToolType
from omniforge.agents.models import TextPart
from omniforge.tasks.models import Task, TaskMessage, TaskState
from omniforge.tools.base import (
    ToolCallContext,
    ToolDefinition,
    ToolParameter,
    ToolPermissions,
    ToolRetryConfig,
    ToolVisibilityConfig,
)
from omniforge.tools.registry import ToolRegistry


@pytest.fixture
def tool_registry() -> ToolRegistry:
    """Create a tool registry with a mock tool and default tools."""
    from omniforge.tools.base import BaseTool, ToolResult
    from omniforge.tools.builtin.llm import LLMTool

    class MockCalculatorTool(BaseTool):
        """Mock calculator tool for testing."""

        @property
        def definition(self) -> ToolDefinition:
            from omniforge.tools.base import ParameterType

            return ToolDefinition(
                name="calculator",
                type=ToolType.FUNCTION,
                description="Perform arithmetic calculations",
                parameters=[
                    ToolParameter(
                        name="expression",
                        type=ParameterType.STRING,
                        description="Mathematical expression to evaluate",
                        required=True,
                    )
                ],
                returns={"description": "Calculation result"},
                timeout_ms=5000,
                retry_config=ToolRetryConfig(),
                visibility=ToolVisibilityConfig(),
                permissions=ToolPermissions(),
            )

        async def execute(self, context: ToolCallContext, arguments: dict[str, any]) -> ToolResult:
            """Execute calculator operation."""
            try:
                result = eval(arguments["expression"])
                return ToolResult(success=True, result={"value": str(result)}, duration_ms=0)
            except Exception as e:
                return ToolResult(success=False, error=str(e), duration_ms=0)

    # Create a fresh registry for each test to avoid conflicts
    registry = ToolRegistry()
    registry.register(LLMTool())
    registry.register(MockCalculatorTool())
    return registry


@pytest.fixture
def sample_task() -> Task:
    """Create a sample task for testing."""
    return Task(
        id="task-123",
        agent_id="autonomous-cot-agent",
        state=TaskState.SUBMITTED,
        messages=[
            TaskMessage(
                id="msg-1",
                role="user",
                parts=[TextPart(text="What is 5 + 3?")],
                created_at=datetime.utcnow(),
            )
        ],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        user_id="user-123",
    )


@pytest.mark.asyncio
async def test_autonomous_agent_initialization() -> None:
    """Test AutonomousCoTAgent initialization with default parameters."""
    agent = AutonomousCoTAgent()

    assert agent._max_iterations == 10
    assert agent._reasoning_model == "claude-sonnet-4"
    assert agent._temperature == 0.0
    assert agent._parser is not None


@pytest.mark.asyncio
async def test_autonomous_agent_custom_initialization() -> None:
    """Test AutonomousCoTAgent initialization with custom parameters."""
    agent = AutonomousCoTAgent(max_iterations=5, reasoning_model="gpt-4", temperature=0.7)

    assert agent._max_iterations == 5
    assert agent._reasoning_model == "gpt-4"
    assert agent._temperature == 0.7


@pytest.mark.asyncio
async def test_simple_single_tool_task(tool_registry: ToolRegistry, sample_task: Task) -> None:
    """Test agent completes simple single-tool task autonomously."""
    agent = AutonomousCoTAgent(tool_registry=tool_registry, max_iterations=3)

    # Mock LLM response that uses calculator and provides final answer (JSON format)
    mock_llm_responses = [
        # First iteration: use calculator
        """{
  "thought": "I need to calculate 5 + 3 using the calculator tool.",
  "action": "calculator",
  "action_input": {"expression": "5 + 3"},
  "is_final": false
}""",
        # Second iteration: provide final answer after seeing result
        """{
  "thought": "The calculator returned 8, which is the answer to 5 + 3.",
  "final_answer": "The result of 5 + 3 is 8.",
  "is_final": true
}""",
    ]

    call_count = 0

    async def mock_llm_call(*args, **kwargs):
        """Mock LLM tool execution."""
        nonlocal call_count
        response = mock_llm_responses[call_count]
        call_count += 1

        # Return a mock ToolCallResult
        from uuid import uuid4

        from omniforge.agents.cot.chain import (
            ReasoningStep,
            StepType,
            ToolCallInfo,
            ToolResultInfo,
        )
        from omniforge.agents.cot.engine import ToolCallResult
        from omniforge.tools.base import ToolResult

        correlation_id = str(uuid4())

        call_step = ReasoningStep(
            step_number=0,
            type=StepType.TOOL_CALL,
            timestamp=datetime.utcnow(),
            tool_call=ToolCallInfo(
                correlation_id=correlation_id,
                tool_name="llm",
                tool_type=ToolType.LLM,
                parameters=kwargs,
            ),
        )
        result_step = ReasoningStep(
            step_number=1,
            type=StepType.TOOL_RESULT,
            timestamp=datetime.utcnow(),
            tool_result=ToolResultInfo(
                correlation_id=correlation_id,
                success=True,
                result={"content": response},
            ),
        )
        return ToolCallResult(
            result=ToolResult(success=True, result={"content": response}, duration_ms=0),
            call_step=call_step,
            result_step=result_step,
        )

    # Patch the engine's call_llm method
    with patch.object(
        (
            agent._executor._registry.get("llm").__class__
            if hasattr(agent._executor._registry, "get")
            else type(None)
        ),
        "execute",
        side_effect=mock_llm_call,
    ):
        # Since we can't easily patch the engine (it's created inside process_task),
        # we'll test the reason method directly
        from omniforge.agents.cot.chain import ReasoningChain
        from omniforge.agents.cot.engine import ReasoningEngine

        chain = ReasoningChain(
            task_id=sample_task.id, agent_id=str(agent._id), status=ChainStatus.RUNNING
        )
        engine = ReasoningEngine(
            chain=chain,
            executor=agent._executor,
            task=sample_task.model_dump(),
        )

        # Mock the engine.call_llm method
        engine.call_llm = mock_llm_call

        result = await agent.reason(sample_task, engine)

        assert result == "The result of 5 + 3 is 8."
        assert call_count == 2  # Two LLM calls made


@pytest.mark.asyncio
async def test_max_iterations_error(tool_registry: ToolRegistry, sample_task: Task) -> None:
    """Test agent raises MaxIterationsError when reaching limit."""
    agent = AutonomousCoTAgent(tool_registry=tool_registry, max_iterations=2)

    # Mock LLM responses that never provide final answer (JSON format)
    mock_response = """{
  "thought": "I'm thinking about the problem.",
  "action": "calculator",
  "action_input": {"expression": "1 + 1"},
  "is_final": false
}"""

    async def mock_llm_call(*args, **kwargs):
        """Mock LLM that never finishes."""
        from uuid import uuid4

        from omniforge.agents.cot.chain import (
            ReasoningStep,
            StepType,
            ToolCallInfo,
            ToolResultInfo,
        )
        from omniforge.agents.cot.engine import ToolCallResult
        from omniforge.tools.base import ToolResult

        correlation_id = str(uuid4())

        call_step = ReasoningStep(
            step_number=0,
            type=StepType.TOOL_CALL,
            timestamp=datetime.utcnow(),
            tool_call=ToolCallInfo(
                correlation_id=correlation_id,
                tool_name="llm",
                tool_type=ToolType.LLM,
                parameters=kwargs,
            ),
        )
        result_step = ReasoningStep(
            step_number=1,
            type=StepType.TOOL_RESULT,
            timestamp=datetime.utcnow(),
            tool_result=ToolResultInfo(
                correlation_id=correlation_id,
                success=True,
                result={"content": mock_response},
            ),
        )
        return ToolCallResult(
            result=ToolResult(success=True, result={"content": mock_response}, duration_ms=0),
            call_step=call_step,
            result_step=result_step,
        )

    from omniforge.agents.cot.chain import ReasoningChain
    from omniforge.agents.cot.engine import ReasoningEngine

    chain = ReasoningChain(
        task_id=sample_task.id, agent_id=str(agent._id), status=ChainStatus.RUNNING
    )
    engine = ReasoningEngine(chain=chain, executor=agent._executor, task=sample_task.model_dump())
    engine.call_llm = mock_llm_call

    with pytest.raises(MaxIterationsError) as exc_info:
        await agent.reason(sample_task, engine)

    assert exc_info.value.max_iterations == 2
    assert len(exc_info.value.final_conversation) > 0


@pytest.mark.asyncio
async def test_tool_execution_error_handling(
    tool_registry: ToolRegistry, sample_task: Task
) -> None:
    """Test agent handles tool execution errors gracefully."""
    agent = AutonomousCoTAgent(tool_registry=tool_registry, max_iterations=3)

    # Mock LLM responses (JSON format)
    mock_llm_responses = [
        # First iteration: try to use calculator with bad expression
        """{
  "thought": "I'll try to calculate with an invalid expression.",
  "action": "calculator",
  "action_input": {"expression": "invalid expression"},
  "is_final": false
}""",
        # Second iteration: provide final answer after error
        """{
  "thought": "The tool failed, but I can still answer based on the original question.",
  "final_answer": "5 + 3 equals 8.",
  "is_final": true
}""",
    ]

    call_count = 0

    async def mock_llm_call(*args, **kwargs):
        """Mock LLM tool execution."""
        nonlocal call_count
        response = mock_llm_responses[call_count]
        call_count += 1

        from uuid import uuid4

        from omniforge.agents.cot.chain import (
            ReasoningStep,
            StepType,
            ToolCallInfo,
            ToolResultInfo,
        )
        from omniforge.agents.cot.engine import ToolCallResult
        from omniforge.tools.base import ToolResult

        correlation_id = str(uuid4())

        call_step = ReasoningStep(
            step_number=0,
            type=StepType.TOOL_CALL,
            timestamp=datetime.utcnow(),
            tool_call=ToolCallInfo(
                correlation_id=correlation_id,
                tool_name="llm",
                tool_type=ToolType.LLM,
                parameters=kwargs,
            ),
        )
        result_step = ReasoningStep(
            step_number=1,
            type=StepType.TOOL_RESULT,
            timestamp=datetime.utcnow(),
            tool_result=ToolResultInfo(
                correlation_id=correlation_id,
                success=True,
                result={"content": response},
            ),
        )
        return ToolCallResult(
            result=ToolResult(success=True, result={"content": response}, duration_ms=0),
            call_step=call_step,
            result_step=result_step,
        )

    from omniforge.agents.cot.chain import ReasoningChain
    from omniforge.agents.cot.engine import ReasoningEngine

    chain = ReasoningChain(
        task_id=sample_task.id, agent_id=str(agent._id), status=ChainStatus.RUNNING
    )
    engine = ReasoningEngine(chain=chain, executor=agent._executor, task=sample_task.model_dump())
    engine.call_llm = mock_llm_call

    # Agent should complete despite tool error
    result = await agent.reason(sample_task, engine)
    assert "8" in result


@pytest.mark.asyncio
async def test_extract_user_message_with_text_part(sample_task: Task) -> None:
    """Test extracting user message from task with text part."""
    agent = AutonomousCoTAgent()

    message = agent._extract_user_message(sample_task)

    assert message == "What is 5 + 3?"


@pytest.mark.asyncio
async def test_extract_user_message_empty_task() -> None:
    """Test extracting user message from empty task."""
    agent = AutonomousCoTAgent()

    task = Task(
        id="task-empty",
        agent_id="autonomous-cot-agent",
        state=TaskState.SUBMITTED,
        messages=[],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        user_id="user-123",
    )

    message = agent._extract_user_message(task)

    assert message == "Please help me with this task."


@pytest.mark.asyncio
async def test_agent_identity() -> None:
    """Test agent identity configuration."""
    agent = AutonomousCoTAgent()

    assert agent.identity.id == "autonomous-cot-agent"
    assert agent.identity.name == "Autonomous CoT Agent"
    assert "ReAct" in agent.identity.description
    assert agent.capabilities.streaming is True


@pytest.mark.asyncio
async def test_invalid_llm_response(tool_registry: ToolRegistry, sample_task: Task) -> None:
    """Test agent raises error on invalid LLM response."""
    agent = AutonomousCoTAgent(tool_registry=tool_registry, max_iterations=1)

    # Mock LLM response with no action or final answer
    async def mock_llm_call(*args, **kwargs):
        """Mock LLM with invalid response."""
        from uuid import uuid4

        from omniforge.agents.cot.chain import (
            ReasoningStep,
            StepType,
            ToolCallInfo,
            ToolResultInfo,
        )
        from omniforge.agents.cot.engine import ToolCallResult
        from omniforge.tools.base import ToolResult

        invalid_response = """{
  "thought": "I'm thinking but not providing action or answer.",
  "is_final": false
}"""

        correlation_id = str(uuid4())

        call_step = ReasoningStep(
            step_number=0,
            type=StepType.TOOL_CALL,
            timestamp=datetime.utcnow(),
            tool_call=ToolCallInfo(
                correlation_id=correlation_id,
                tool_name="llm",
                tool_type=ToolType.LLM,
                parameters=kwargs,
            ),
        )
        result_step = ReasoningStep(
            step_number=1,
            type=StepType.TOOL_RESULT,
            timestamp=datetime.utcnow(),
            tool_result=ToolResultInfo(
                correlation_id=correlation_id,
                success=True,
                result={"content": invalid_response},
            ),
        )
        return ToolCallResult(
            result=ToolResult(success=True, result={"content": invalid_response}, duration_ms=0),
            call_step=call_step,
            result_step=result_step,
        )

    from omniforge.agents.cot.chain import ReasoningChain
    from omniforge.agents.cot.engine import ReasoningEngine

    chain = ReasoningChain(
        task_id=sample_task.id, agent_id=str(agent._id), status=ChainStatus.RUNNING
    )
    engine = ReasoningEngine(chain=chain, executor=agent._executor, task=sample_task.model_dump())
    engine.call_llm = mock_llm_call

    with pytest.raises(ValueError) as exc_info:
        await agent.reason(sample_task, engine)

    assert "neither action nor final answer" in str(exc_info.value)
