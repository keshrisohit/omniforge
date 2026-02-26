"""Tests for the ReasoningEngine."""

from typing import Any
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest

from omniforge.agents.cot.chain import (
    ReasoningChain,
    ReasoningStep,
    StepType,
    ToolType,
    VisibilityLevel,
)
from omniforge.agents.cot.engine import ReasoningEngine, ToolCallResult
from omniforge.tools import ToolCallContext, ToolDefinition, ToolResult


@pytest.fixture
def chain() -> ReasoningChain:
    """Create a test reasoning chain."""
    return ReasoningChain(task_id="test-task", agent_id="test-agent")


@pytest.fixture
def mock_executor() -> Mock:
    """Create a mock tool executor."""
    executor = Mock()
    executor._registry = Mock()
    return executor


@pytest.fixture
def task() -> dict[str, Any]:
    """Create a test task dictionary."""
    return {
        "id": "test-task-123",
        "agent_id": "test-agent-456",
        "tenant_id": "tenant-789",
        "chain_id": "chain-abc",
    }


@pytest.fixture
def engine(chain: ReasoningChain, mock_executor: Mock, task: dict[str, Any]) -> ReasoningEngine:
    """Create a test reasoning engine."""
    return ReasoningEngine(
        chain=chain, executor=mock_executor, task=task, default_llm_model="test-model"
    )


class TestToolCallResult:
    """Tests for ToolCallResult wrapper class."""

    def test_init_stores_references(self) -> None:
        """ToolCallResult should store result and step references."""
        result = ToolResult(success=True, duration_ms=100, result={"key": "value"})
        call_step = ReasoningStep(step_number=0, type=StepType.TOOL_CALL)
        result_step = ReasoningStep(step_number=1, type=StepType.TOOL_RESULT)

        wrapper = ToolCallResult(result=result, call_step=call_step, result_step=result_step)

        assert wrapper.result is result
        assert wrapper.call_step is call_step
        assert wrapper.result_step is result_step

    def test_step_id_returns_result_step_id(self) -> None:
        """step_id property should return result step ID as string."""
        result = ToolResult(success=True, duration_ms=100)
        call_step = ReasoningStep(step_number=0, type=StepType.TOOL_CALL)
        result_step = ReasoningStep(step_number=1, type=StepType.TOOL_RESULT)

        wrapper = ToolCallResult(result=result, call_step=call_step, result_step=result_step)

        assert wrapper.step_id == str(result_step.id)
        assert isinstance(wrapper.step_id, str)

    def test_success_property(self) -> None:
        """success property should return underlying result success status."""
        result_success = ToolResult(success=True, duration_ms=100)
        result_failure = ToolResult(success=False, duration_ms=100, error="Test error")
        call_step = ReasoningStep(step_number=0, type=StepType.TOOL_CALL)
        result_step = ReasoningStep(step_number=1, type=StepType.TOOL_RESULT)

        wrapper_success = ToolCallResult(result_success, call_step, result_step)
        wrapper_failure = ToolCallResult(result_failure, call_step, result_step)

        assert wrapper_success.success is True
        assert wrapper_failure.success is False

    def test_value_property(self) -> None:
        """value property should return result data or None."""
        result_data = {"key": "value", "count": 42}
        result_with_value = ToolResult(success=True, duration_ms=100, result=result_data)
        result_without_value = ToolResult(success=False, duration_ms=100, error="Error")

        call_step = ReasoningStep(step_number=0, type=StepType.TOOL_CALL)
        result_step = ReasoningStep(step_number=1, type=StepType.TOOL_RESULT)

        wrapper_with = ToolCallResult(result_with_value, call_step, result_step)
        wrapper_without = ToolCallResult(result_without_value, call_step, result_step)

        assert wrapper_with.value == result_data
        assert wrapper_without.value is None

    def test_error_property(self) -> None:
        """error property should return error message or None."""
        result_success = ToolResult(success=True, duration_ms=100)
        result_failure = ToolResult(success=False, duration_ms=100, error="Test error")

        call_step = ReasoningStep(step_number=0, type=StepType.TOOL_CALL)
        result_step = ReasoningStep(step_number=1, type=StepType.TOOL_RESULT)

        wrapper_success = ToolCallResult(result_success, call_step, result_step)
        wrapper_failure = ToolCallResult(result_failure, call_step, result_step)

        assert wrapper_success.error is None
        assert wrapper_failure.error == "Test error"


class TestReasoningEngine:
    """Tests for ReasoningEngine class."""

    def test_init_stores_parameters(
        self, chain: ReasoningChain, mock_executor: Mock, task: dict[str, Any]
    ) -> None:
        """Engine should store constructor parameters."""
        engine = ReasoningEngine(
            chain=chain, executor=mock_executor, task=task, default_llm_model="custom-model"
        )

        assert engine.chain is chain
        assert engine.task is task
        assert engine._executor is mock_executor
        assert engine._default_llm_model == "custom-model"

    def test_default_llm_model(
        self, chain: ReasoningChain, mock_executor: Mock, task: dict[str, Any]
    ) -> None:
        """Engine should use default LLM model if not specified."""
        engine = ReasoningEngine(chain=chain, executor=mock_executor, task=task)

        assert engine._default_llm_model == "claude-sonnet-4"

    def test_add_thinking_creates_step(self, engine: ReasoningEngine) -> None:
        """add_thinking should create and add THINKING step to chain."""
        step = engine.add_thinking("This is a thought", confidence=0.85)

        assert step.type == StepType.THINKING
        assert step.thinking is not None
        assert step.thinking.content == "This is a thought"
        assert step.thinking.confidence == 0.85
        assert len(engine.chain.steps) == 1
        assert engine.chain.steps[0] is step

    def test_add_thinking_without_confidence(self, engine: ReasoningEngine) -> None:
        """add_thinking should work without confidence parameter."""
        step = engine.add_thinking("Another thought")

        assert step.thinking is not None
        assert step.thinking.content == "Another thought"
        assert step.thinking.confidence is None

    def test_add_synthesis_creates_step(self, engine: ReasoningEngine) -> None:
        """add_synthesis should create SYNTHESIS step with source references."""
        source_id1 = str(uuid4())
        source_id2 = str(uuid4())

        step = engine.add_synthesis("Final conclusion", [source_id1, source_id2])

        assert step.type == StepType.SYNTHESIS
        assert step.synthesis is not None
        assert step.synthesis.content == "Final conclusion"
        assert len(step.synthesis.sources) == 2
        assert isinstance(step.synthesis.sources[0], UUID)
        assert str(step.synthesis.sources[0]) == source_id1
        assert str(step.synthesis.sources[1]) == source_id2

    def test_add_synthesis_converts_string_ids_to_uuids(self, engine: ReasoningEngine) -> None:
        """add_synthesis should convert string step IDs to UUIDs."""
        source_id = str(uuid4())

        step = engine.add_synthesis("Conclusion", [source_id])

        assert step.synthesis is not None
        assert isinstance(step.synthesis.sources[0], UUID)
        assert str(step.synthesis.sources[0]) == source_id

    @pytest.mark.asyncio
    async def test_call_llm_with_prompt(self, engine: ReasoningEngine) -> None:
        """call_llm should work with simple prompt parameter."""
        # Setup mock executor
        mock_result = ToolResult(success=True, duration_ms=100, result={"response": "LLM response"})
        call_step = ReasoningStep(step_number=0, type=StepType.TOOL_CALL)
        result_step = ReasoningStep(step_number=1, type=StepType.TOOL_RESULT)

        async def mock_execute(
            tool_name: str, arguments: dict, context: ToolCallContext, chain: ReasoningChain
        ) -> ToolResult:
            # Add steps to chain like real executor
            chain.add_step(call_step)
            chain.add_step(result_step)
            return mock_result

        engine._executor.execute = mock_execute

        result = await engine.call_llm(prompt="Test prompt")

        # Verify call_tool was used correctly
        assert result.success is True
        assert result.value == {"response": "LLM response"}
        assert len(engine.chain.steps) == 2

    @pytest.mark.asyncio
    async def test_call_llm_with_messages(self, engine: ReasoningEngine) -> None:
        """call_llm should work with messages parameter."""
        mock_result = ToolResult(success=True, duration_ms=100, result={"response": "OK"})
        call_step = ReasoningStep(step_number=0, type=StepType.TOOL_CALL)
        result_step = ReasoningStep(step_number=1, type=StepType.TOOL_RESULT)

        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]

        captured_args = None

        async def mock_execute(
            tool_name: str, arguments: dict, context: ToolCallContext, chain: ReasoningChain
        ) -> ToolResult:
            nonlocal captured_args
            captured_args = arguments
            chain.add_step(call_step)
            chain.add_step(result_step)
            return mock_result

        engine._executor.execute = mock_execute

        await engine.call_llm(messages=messages)

        assert captured_args is not None
        assert captured_args["messages"] == messages

    @pytest.mark.asyncio
    async def test_call_llm_uses_default_model(self, engine: ReasoningEngine) -> None:
        """call_llm should use default model if not specified."""
        mock_result = ToolResult(success=True, duration_ms=100)
        call_step = ReasoningStep(step_number=0, type=StepType.TOOL_CALL)
        result_step = ReasoningStep(step_number=1, type=StepType.TOOL_RESULT)

        captured_args = None

        async def mock_execute(
            tool_name: str, arguments: dict, context: ToolCallContext, chain: ReasoningChain
        ) -> ToolResult:
            nonlocal captured_args
            captured_args = arguments
            chain.add_step(call_step)
            chain.add_step(result_step)
            return mock_result

        engine._executor.execute = mock_execute

        await engine.call_llm(prompt="Test")

        assert captured_args is not None
        assert captured_args["model"] == "test-model"

    @pytest.mark.asyncio
    async def test_call_llm_with_custom_model(self, engine: ReasoningEngine) -> None:
        """call_llm should use custom model when specified."""
        mock_result = ToolResult(success=True, duration_ms=100)
        call_step = ReasoningStep(step_number=0, type=StepType.TOOL_CALL)
        result_step = ReasoningStep(step_number=1, type=StepType.TOOL_RESULT)

        captured_args = None

        async def mock_execute(
            tool_name: str, arguments: dict, context: ToolCallContext, chain: ReasoningChain
        ) -> ToolResult:
            nonlocal captured_args
            captured_args = arguments
            chain.add_step(call_step)
            chain.add_step(result_step)
            return mock_result

        engine._executor.execute = mock_execute

        await engine.call_llm(prompt="Test", model="custom-model")

        assert captured_args is not None
        assert captured_args["model"] == "custom-model"

    @pytest.mark.asyncio
    async def test_call_llm_with_optional_parameters(self, engine: ReasoningEngine) -> None:
        """call_llm should pass through optional parameters."""
        mock_result = ToolResult(success=True, duration_ms=100)
        call_step = ReasoningStep(step_number=0, type=StepType.TOOL_CALL)
        result_step = ReasoningStep(step_number=1, type=StepType.TOOL_RESULT)

        captured_args = None

        async def mock_execute(
            tool_name: str, arguments: dict, context: ToolCallContext, chain: ReasoningChain
        ) -> ToolResult:
            nonlocal captured_args
            captured_args = arguments
            chain.add_step(call_step)
            chain.add_step(result_step)
            return mock_result

        engine._executor.execute = mock_execute

        await engine.call_llm(
            prompt="Test",
            system="System prompt",
            temperature=0.9,
            max_tokens=500,
        )

        assert captured_args is not None
        assert captured_args["system"] == "System prompt"
        assert captured_args["temperature"] == 0.9
        assert captured_args["max_tokens"] == 500

    @pytest.mark.asyncio
    async def test_call_llm_raises_without_prompt_or_messages(
        self, engine: ReasoningEngine
    ) -> None:
        """call_llm should raise ValueError if neither prompt nor messages provided."""
        with pytest.raises(ValueError, match="Either 'prompt' or 'messages' must be provided"):
            await engine.call_llm()

    @pytest.mark.asyncio
    async def test_call_tool_executes_tool(self, engine: ReasoningEngine) -> None:
        """call_tool should execute tool through executor."""
        mock_result = ToolResult(success=True, duration_ms=100, result={"output": "test"})
        call_step = ReasoningStep(step_number=0, type=StepType.TOOL_CALL)
        result_step = ReasoningStep(step_number=1, type=StepType.TOOL_RESULT)

        captured_context = None

        async def mock_execute(
            tool_name: str, arguments: dict, context: ToolCallContext, chain: ReasoningChain
        ) -> ToolResult:
            nonlocal captured_context
            captured_context = context
            chain.add_step(call_step)
            chain.add_step(result_step)
            return mock_result

        engine._executor.execute = mock_execute

        result = await engine.call_tool("my_tool", {"arg1": "value1"})

        assert result.success is True
        assert result.value == {"output": "test"}
        assert captured_context is not None
        assert captured_context.task_id == "test-task-123"
        assert captured_context.agent_id == "test-agent-456"

    @pytest.mark.asyncio
    async def test_call_tool_builds_correct_context(self, engine: ReasoningEngine) -> None:
        """call_tool should build ToolCallContext from task info."""
        mock_result = ToolResult(success=True, duration_ms=100)
        call_step = ReasoningStep(step_number=0, type=StepType.TOOL_CALL)
        result_step = ReasoningStep(step_number=1, type=StepType.TOOL_RESULT)

        captured_context = None

        async def mock_execute(
            tool_name: str, arguments: dict, context: ToolCallContext, chain: ReasoningChain
        ) -> ToolResult:
            nonlocal captured_context
            captured_context = context
            chain.add_step(call_step)
            chain.add_step(result_step)
            return mock_result

        engine._executor.execute = mock_execute

        await engine.call_tool("test_tool", {})

        assert captured_context is not None
        assert captured_context.task_id == "test-task-123"
        assert captured_context.agent_id == "test-agent-456"
        assert captured_context.tenant_id == "tenant-789"
        assert captured_context.chain_id == "chain-abc"

    @pytest.mark.asyncio
    async def test_call_tool_with_visibility_override(self, engine: ReasoningEngine) -> None:
        """call_tool should override visibility level when specified."""
        mock_result = ToolResult(success=True, duration_ms=100)
        call_step = ReasoningStep(step_number=0, type=StepType.TOOL_CALL)
        result_step = ReasoningStep(step_number=1, type=StepType.TOOL_RESULT)

        async def mock_execute(
            tool_name: str, arguments: dict, context: ToolCallContext, chain: ReasoningChain
        ) -> ToolResult:
            chain.add_step(call_step)
            chain.add_step(result_step)
            return mock_result

        engine._executor.execute = mock_execute

        await engine.call_tool("test_tool", {}, visibility=VisibilityLevel.HIDDEN)

        # Check that visibility was overridden
        assert engine.chain.steps[-2].visibility.level == VisibilityLevel.HIDDEN
        assert engine.chain.steps[-1].visibility.level == VisibilityLevel.HIDDEN

    @pytest.mark.asyncio
    async def test_call_tool_returns_wrapped_result(self, engine: ReasoningEngine) -> None:
        """call_tool should return ToolCallResult with step references."""
        mock_result = ToolResult(success=True, duration_ms=100, result={"data": "value"})
        call_step = ReasoningStep(step_number=0, type=StepType.TOOL_CALL)
        result_step = ReasoningStep(step_number=1, type=StepType.TOOL_RESULT)

        async def mock_execute(
            tool_name: str, arguments: dict, context: ToolCallContext, chain: ReasoningChain
        ) -> ToolResult:
            chain.add_step(call_step)
            chain.add_step(result_step)
            return mock_result

        engine._executor.execute = mock_execute

        result = await engine.call_tool("test_tool", {})

        assert isinstance(result, ToolCallResult)
        assert result.result is mock_result
        assert result.call_step is call_step
        assert result.result_step is result_step

    def test_get_available_tools_returns_definitions(self, engine: ReasoningEngine) -> None:
        """get_available_tools should return all registered tool definitions."""
        # Setup mock registry
        mock_registry = Mock()
        mock_registry.list_tools.return_value = ["tool1", "tool2", "tool3"]

        def_tool1 = ToolDefinition(name="tool1", type=ToolType.FUNCTION, description="Tool 1")
        def_tool2 = ToolDefinition(name="tool2", type=ToolType.API, description="Tool 2")
        def_tool3 = ToolDefinition(name="tool3", type=ToolType.DATABASE, description="Tool 3")

        def mock_get_definition(name: str) -> ToolDefinition:
            definitions = {"tool1": def_tool1, "tool2": def_tool2, "tool3": def_tool3}
            return definitions[name]

        mock_registry.get_definition.side_effect = mock_get_definition
        engine._executor._registry = mock_registry

        definitions = engine.get_available_tools()

        assert len(definitions) == 3
        assert def_tool1 in definitions
        assert def_tool2 in definitions
        assert def_tool3 in definitions

    def test_get_available_tools_handles_errors(self, engine: ReasoningEngine) -> None:
        """get_available_tools should skip tools that raise errors."""
        mock_registry = Mock()
        mock_registry.list_tools.return_value = ["tool1", "tool2"]

        def_tool1 = ToolDefinition(name="tool1", type=ToolType.FUNCTION, description="Tool 1")

        def mock_get_definition(name: str) -> ToolDefinition:
            if name == "tool1":
                return def_tool1
            raise Exception("Tool not found")

        mock_registry.get_definition.side_effect = mock_get_definition
        engine._executor._registry = mock_registry

        definitions = engine.get_available_tools()

        # Should only return tool1, skipping tool2 which raised error
        assert len(definitions) == 1
        assert definitions[0] == def_tool1

