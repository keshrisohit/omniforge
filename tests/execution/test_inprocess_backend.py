"""Tests for InProcessBackend and ExecutionBackend contract."""

import pytest

from omniforge.execution import ExecutionBackend, InProcessBackend
from omniforge.tools.executor import ToolExecutor
from omniforge.tools.registry import ToolRegistry
from omniforge.tools.base import BaseTool, ToolCallContext, ToolDefinition, ToolParameter, ToolResult
from omniforge.agents.cot.chain import ReasoningChain, StepType


# ---------------------------------------------------------------------------
# InProcessBackend unit tests
# ---------------------------------------------------------------------------

class TestInProcessBackend:
    def setup_method(self):
        self.backend = InProcessBackend()

    @pytest.mark.asyncio
    async def test_run_activity_returns_result(self):
        async def fn():
            return 42

        result = await self.backend.run_activity(fn)
        assert result == 42

    @pytest.mark.asyncio
    async def test_run_activity_passes_args(self):
        async def fn(a, b):
            return a + b

        result = await self.backend.run_activity(fn, 3, 4)
        assert result == 7

    @pytest.mark.asyncio
    async def test_run_activity_passes_kwargs(self):
        async def fn(x, y=0):
            return x * y

        result = await self.backend.run_activity(fn, 5, y=3)
        assert result == 15

    @pytest.mark.asyncio
    async def test_run_activity_propagates_exception(self):
        async def fn():
            raise ValueError("boom")

        with pytest.raises(ValueError, match="boom"):
            await self.backend.run_activity(fn)

    @pytest.mark.asyncio
    async def test_run_activity_ignores_activity_name(self):
        """activity_name is metadata for Temporal; InProcess ignores it."""
        async def fn():
            return "ok"

        result = await self.backend.run_activity(fn, activity_name="my_activity")
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_run_activity_ignores_timeout_and_retries(self):
        """timeout_ms and max_retries are hints for Temporal; InProcess ignores them."""
        async def fn():
            return "ok"

        result = await self.backend.run_activity(fn, timeout_ms=1, max_retries=0)
        assert result == "ok"

    def test_is_execution_backend(self):
        assert isinstance(self.backend, ExecutionBackend)


# ---------------------------------------------------------------------------
# ToolExecutor + InProcessBackend integration
# ---------------------------------------------------------------------------

class MockTool(BaseTool):
    def __init__(self):
        self._definition = ToolDefinition(
            name="mock_tool",
            type="function",
            description="Test tool",
            parameters=[ToolParameter(name="input", type="string", description="Input", required=True)],
        )

    @property
    def definition(self) -> ToolDefinition:
        return self._definition

    async def execute(self, context: ToolCallContext, arguments: dict) -> ToolResult:
        return ToolResult(success=True, result={"output": arguments.get("input", "")}, duration_ms=1)


class TestToolExecutorWithBackend:
    def setup_method(self):
        self.registry = ToolRegistry()
        self.registry.register(MockTool())
        self.context = ToolCallContext(
            correlation_id="test-corr",
            task_id="task-1",
            agent_id="agent-1",
        )
        self.chain = ReasoningChain(task_id="task-1", agent_id="agent-1")

    @pytest.mark.asyncio
    async def test_default_backend_is_inprocess(self):
        executor = ToolExecutor(self.registry)
        assert isinstance(executor._backend, InProcessBackend)

    @pytest.mark.asyncio
    async def test_custom_backend_is_used(self):
        called = []

        class TrackingBackend(InProcessBackend):
            async def run_activity(self, fn, *args, **kwargs):
                called.append(kwargs.get("activity_name", ""))
                return await super().run_activity(fn, *args, **kwargs)

        executor = ToolExecutor(self.registry, backend=TrackingBackend())
        await executor.execute("mock_tool", {"input": "hi"}, self.context, self.chain)

        assert called == ["mock_tool"]

    @pytest.mark.asyncio
    async def test_execute_still_records_chain_steps(self):
        executor = ToolExecutor(self.registry)
        await executor.execute("mock_tool", {"input": "test"}, self.context, self.chain)

        assert len(self.chain.steps) == 2
        assert self.chain.steps[0].type == StepType.TOOL_CALL
        assert self.chain.steps[1].type == StepType.TOOL_RESULT

    @pytest.mark.asyncio
    async def test_execute_returns_tool_result(self):
        executor = ToolExecutor(self.registry)
        result = await executor.execute("mock_tool", {"input": "hello"}, self.context, self.chain)

        assert result.success is True
        assert result.result == {"output": "hello"}
