"""Tests for tool executor with retry, timeout, and chain integration."""

import asyncio
from typing import Any
from unittest.mock import AsyncMock

import pytest

from omniforge.agents.cot.chain import (
    ChainStatus,
    ReasoningChain,
    StepType,
)
from omniforge.tools import (
    BaseTool,
    ToolCallContext,
    ToolDefinition,
    ToolParameter,
    ToolResult,
    ToolRetryConfig,
)
from omniforge.tools.errors import (
    RateLimitExceededError,
    ToolNotFoundError,
    ToolTimeoutError,
    ToolValidationError,
)
from omniforge.tools.executor import ToolExecutor
from omniforge.tools.registry import ToolRegistry


class MockTool(BaseTool):
    """Mock tool for testing."""

    def __init__(
        self,
        name: str = "mock_tool",
        execute_fn: Any = None,
        timeout_ms: int = 30000,
        retry_config: ToolRetryConfig | None = None,
    ) -> None:
        """Initialize mock tool with configurable behavior."""
        self._definition = ToolDefinition(
            name=name,
            type="function",
            description="Mock tool for testing",
            timeout_ms=timeout_ms,
            retry_config=retry_config or ToolRetryConfig(),
            parameters=[
                ToolParameter(
                    name="input",
                    type="string",
                    description="Input parameter",
                    required=True,
                )
            ],
        )
        self._execute_fn = execute_fn or self._default_execute

    @property
    def definition(self) -> ToolDefinition:
        """Get tool definition."""
        return self._definition

    async def execute(self, context: ToolCallContext, arguments: dict[str, Any]) -> ToolResult:
        """Execute the tool using configured function."""
        return await self._execute_fn(context, arguments)

    async def _default_execute(
        self, context: ToolCallContext, arguments: dict[str, Any]
    ) -> ToolResult:
        """Default successful execution."""
        return ToolResult(
            success=True,
            result={"output": f"processed: {arguments.get('input')}"},
            duration_ms=100,
        )


@pytest.fixture
def registry() -> ToolRegistry:
    """Create a fresh tool registry for testing."""
    return ToolRegistry()


@pytest.fixture
def context() -> ToolCallContext:
    """Create a test execution context."""
    return ToolCallContext(
        correlation_id="test-correlation-123",
        task_id="test-task-456",
        agent_id="test-agent-789",
        tenant_id="test-tenant-001",
        chain_id="test-chain-111",
    )


@pytest.fixture
def chain() -> ReasoningChain:
    """Create a test reasoning chain."""
    return ReasoningChain(
        task_id="test-task-456",
        agent_id="test-agent-789",
        tenant_id="test-tenant-001",
        status=ChainStatus.RUNNING,
    )


class TestToolExecutor:
    """Tests for ToolExecutor class."""

    @pytest.mark.asyncio
    async def test_execute_success(
        self, registry: ToolRegistry, context: ToolCallContext, chain: ReasoningChain
    ) -> None:
        """Should execute tool successfully and add steps to chain."""
        # Arrange
        tool = MockTool()
        registry.register(tool)
        executor = ToolExecutor(registry)
        arguments = {"input": "test data"}

        # Act
        result = await executor.execute("mock_tool", arguments, context, chain)

        # Assert
        assert result.success is True
        assert result.result == {"output": "processed: test data"}
        assert result.retry_count == 0

        # Verify chain has both steps
        assert len(chain.steps) == 2
        assert chain.steps[0].type == StepType.TOOL_CALL
        assert chain.steps[1].type == StepType.TOOL_RESULT

        # Verify correlation IDs match
        tool_call = chain.steps[0].tool_call
        tool_result = chain.steps[1].tool_result
        assert tool_call is not None
        assert tool_result is not None
        assert tool_call.correlation_id == context.correlation_id
        assert tool_result.correlation_id == context.correlation_id

    @pytest.mark.asyncio
    async def test_execute_tool_not_found(
        self, registry: ToolRegistry, context: ToolCallContext, chain: ReasoningChain
    ) -> None:
        """Should raise ToolNotFoundError when tool does not exist."""
        # Arrange
        executor = ToolExecutor(registry)
        arguments = {"input": "test"}

        # Act & Assert
        with pytest.raises(ToolNotFoundError) as exc_info:
            await executor.execute("nonexistent_tool", arguments, context, chain)

        assert "nonexistent_tool" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_validation_error(
        self, registry: ToolRegistry, context: ToolCallContext, chain: ReasoningChain
    ) -> None:
        """Should raise ToolValidationError for invalid arguments."""
        # Arrange
        tool = MockTool()
        registry.register(tool)
        executor = ToolExecutor(registry)
        arguments = {}  # Missing required 'input' parameter

        # Act & Assert
        with pytest.raises(ToolValidationError) as exc_info:
            await executor.execute("mock_tool", arguments, context, chain)

        assert "input" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_with_retry_success_on_second_attempt(
        self, registry: ToolRegistry, context: ToolCallContext, chain: ReasoningChain
    ) -> None:
        """Should retry and succeed on second attempt."""
        # Arrange
        call_count = 0

        async def failing_then_success(ctx: ToolCallContext, args: dict[str, Any]) -> ToolResult:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("Temporary network error")
            return ToolResult(success=True, result={"output": "success"}, duration_ms=100)

        retry_config = ToolRetryConfig(
            max_retries=3, backoff_ms=10, backoff_multiplier=2.0, retryable_errors=["Connection"]
        )
        tool = MockTool(execute_fn=failing_then_success, retry_config=retry_config)
        registry.register(tool)
        executor = ToolExecutor(registry)
        arguments = {"input": "test"}

        # Act
        result = await executor.execute("mock_tool", arguments, context, chain)

        # Assert
        assert result.success is True
        assert result.retry_count == 1
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_execute_with_retry_exhausted(
        self, registry: ToolRegistry, context: ToolCallContext, chain: ReasoningChain
    ) -> None:
        """Should fail after exhausting all retries."""

        # Arrange
        async def always_fail(ctx: ToolCallContext, args: dict[str, Any]) -> ToolResult:
            raise ConnectionError("Persistent network error")

        retry_config = ToolRetryConfig(
            max_retries=2, backoff_ms=10, backoff_multiplier=2.0, retryable_errors=["Connection"]
        )
        tool = MockTool(execute_fn=always_fail, retry_config=retry_config)
        registry.register(tool)
        executor = ToolExecutor(registry)
        arguments = {"input": "test"}

        # Act
        result = await executor.execute("mock_tool", arguments, context, chain)

        # Assert
        assert result.success is False
        assert "Persistent network error" in result.error
        assert result.retry_count == 2

    @pytest.mark.asyncio
    async def test_execute_with_timeout(
        self, registry: ToolRegistry, context: ToolCallContext, chain: ReasoningChain
    ) -> None:
        """Should enforce timeout and raise ToolTimeoutError."""

        # Arrange
        async def slow_execution(ctx: ToolCallContext, args: dict[str, Any]) -> ToolResult:
            await asyncio.sleep(2.0)  # Sleep longer than timeout
            return ToolResult(success=True, result={"output": "done"}, duration_ms=2000)

        tool = MockTool(execute_fn=slow_execution, timeout_ms=1000)  # 1000ms (1s) timeout
        registry.register(tool)
        executor = ToolExecutor(registry)
        arguments = {"input": "test"}

        # Act & Assert
        with pytest.raises(ToolTimeoutError) as exc_info:
            await executor.execute("mock_tool", arguments, context, chain)

        assert "mock_tool" in str(exc_info.value)
        assert "1.0" in str(exc_info.value)  # Timeout in seconds

    @pytest.mark.asyncio
    async def test_execute_with_exponential_backoff(
        self, registry: ToolRegistry, context: ToolCallContext, chain: ReasoningChain
    ) -> None:
        """Should use exponential backoff between retries."""
        # Arrange
        call_times = []

        async def track_timing(ctx: ToolCallContext, args: dict[str, Any]) -> ToolResult:
            call_times.append(asyncio.get_event_loop().time())
            if len(call_times) <= 2:
                raise ConnectionError("Temporary error")
            return ToolResult(success=True, result={"output": "success"}, duration_ms=100)

        retry_config = ToolRetryConfig(
            max_retries=3,
            backoff_ms=100,  # 100ms initial backoff
            backoff_multiplier=2.0,
            retryable_errors=["Connection"],
        )
        tool = MockTool(execute_fn=track_timing, retry_config=retry_config)
        registry.register(tool)
        executor = ToolExecutor(registry)
        arguments = {"input": "test"}

        # Act
        result = await executor.execute("mock_tool", arguments, context, chain)

        # Assert
        assert result.success is True
        assert len(call_times) == 3

        # Verify exponential backoff timing
        # First retry: ~100ms delay (backoff_ms * 2^0)
        # Second retry: ~200ms delay (backoff_ms * 2^1)
        delay1 = call_times[1] - call_times[0]
        delay2 = call_times[2] - call_times[1]

        # Allow some tolerance for timing
        assert 0.08 < delay1 < 0.15  # ~100ms
        assert 0.18 < delay2 < 0.25  # ~200ms

    @pytest.mark.asyncio
    async def test_execute_with_rate_limiter(
        self, registry: ToolRegistry, context: ToolCallContext, chain: ReasoningChain
    ) -> None:
        """Should check rate limits before execution."""
        # Arrange
        tool = MockTool()
        registry.register(tool)

        rate_limiter = AsyncMock()
        rate_limiter.check_limit = AsyncMock()

        executor = ToolExecutor(registry, rate_limiter=rate_limiter)
        arguments = {"input": "test"}

        # Act
        await executor.execute("mock_tool", arguments, context, chain)

        # Assert
        rate_limiter.check_limit.assert_called_once_with("test-tenant-001", "mock_tool")

    @pytest.mark.asyncio
    async def test_execute_with_rate_limit_exceeded(
        self, registry: ToolRegistry, context: ToolCallContext, chain: ReasoningChain
    ) -> None:
        """Should raise RateLimitExceededError when limit is exceeded."""
        # Arrange
        tool = MockTool()
        registry.register(tool)

        rate_limiter = AsyncMock()
        rate_limiter.check_limit = AsyncMock(
            side_effect=RateLimitExceededError(
                tenant_id="test-tenant-001", limit=100, window_seconds=60
            )
        )

        executor = ToolExecutor(registry, rate_limiter=rate_limiter)
        arguments = {"input": "test"}

        # Act & Assert
        with pytest.raises(RateLimitExceededError):
            await executor.execute("mock_tool", arguments, context, chain)

    @pytest.mark.asyncio
    async def test_execute_with_cost_tracker(
        self, registry: ToolRegistry, context: ToolCallContext, chain: ReasoningChain
    ) -> None:
        """Should track costs after successful execution."""

        # Arrange
        async def execution_with_cost(ctx: ToolCallContext, args: dict[str, Any]) -> ToolResult:
            return ToolResult(
                success=True,
                result={"output": "done"},
                duration_ms=100,
                tokens_used=150,
                cost_usd=0.0025,
            )

        tool = MockTool(execute_fn=execution_with_cost)
        registry.register(tool)

        cost_tracker = AsyncMock()
        cost_tracker.track_cost = AsyncMock()

        executor = ToolExecutor(registry, cost_tracker=cost_tracker)
        arguments = {"input": "test"}

        # Act
        await executor.execute("mock_tool", arguments, context, chain)

        # Assert
        cost_tracker.track_cost.assert_called_once_with("test-task-456", "mock_tool", 0.0025, 150)

    @pytest.mark.asyncio
    async def test_execute_correlation_id_matching(
        self, registry: ToolRegistry, context: ToolCallContext, chain: ReasoningChain
    ) -> None:
        """Should use matching correlation IDs in tool_call and tool_result steps."""
        # Arrange
        tool = MockTool()
        registry.register(tool)
        executor = ToolExecutor(registry)
        arguments = {"input": "test"}

        # Act
        await executor.execute("mock_tool", arguments, context, chain)

        # Assert
        assert len(chain.steps) == 2

        tool_call_step = chain.steps[0]
        tool_result_step = chain.steps[1]

        assert tool_call_step.tool_call is not None
        assert tool_result_step.tool_result is not None
        assert tool_call_step.tool_call.correlation_id == context.correlation_id
        assert tool_result_step.tool_result.correlation_id == context.correlation_id
        assert (
            tool_call_step.tool_call.correlation_id == tool_result_step.tool_result.correlation_id
        )

    @pytest.mark.asyncio
    async def test_execute_non_retryable_error(
        self, registry: ToolRegistry, context: ToolCallContext, chain: ReasoningChain
    ) -> None:
        """Should not retry non-retryable errors."""
        # Arrange
        call_count = 0

        async def non_retryable_error(ctx: ToolCallContext, args: dict[str, Any]) -> ToolResult:
            nonlocal call_count
            call_count += 1
            raise ValueError("Invalid input - not retryable")

        retry_config = ToolRetryConfig(
            max_retries=3, backoff_ms=10, retryable_errors=["Connection", "Timeout"]
        )
        tool = MockTool(execute_fn=non_retryable_error, retry_config=retry_config)
        registry.register(tool)
        executor = ToolExecutor(registry)
        arguments = {"input": "test"}

        # Act
        result = await executor.execute("mock_tool", arguments, context, chain)

        # Assert
        assert result.success is False
        assert "Invalid input - not retryable" in result.error
        assert result.retry_count == 0
        assert call_count == 1  # Should only be called once

    @pytest.mark.asyncio
    async def test_execute_updates_chain_metrics(
        self, registry: ToolRegistry, context: ToolCallContext, chain: ReasoningChain
    ) -> None:
        """Should update chain metrics with tool execution data."""

        # Arrange
        async def execution_with_metrics(ctx: ToolCallContext, args: dict[str, Any]) -> ToolResult:
            return ToolResult(
                success=True,
                result={"output": "done"},
                duration_ms=150,
                tokens_used=100,
                cost_usd=0.002,
            )

        tool = MockTool(execute_fn=execution_with_metrics)
        registry.register(tool)
        executor = ToolExecutor(registry)
        arguments = {"input": "test"}

        # Act
        await executor.execute("mock_tool", arguments, context, chain)

        # Assert
        assert chain.metrics.total_steps == 2
        assert chain.metrics.tool_calls == 1
        assert chain.metrics.total_tokens == 100
        assert chain.metrics.total_cost == 0.002

    @pytest.mark.asyncio
    async def test_execute_without_tenant_id_skips_rate_limiter(
        self, registry: ToolRegistry, chain: ReasoningChain
    ) -> None:
        """Should skip rate limiting when tenant_id is not provided."""
        # Arrange
        tool = MockTool()
        registry.register(tool)

        rate_limiter = AsyncMock()
        rate_limiter.check_limit = AsyncMock()

        executor = ToolExecutor(registry, rate_limiter=rate_limiter)

        # Context without tenant_id
        context = ToolCallContext(
            correlation_id="test-correlation-123",
            task_id="test-task-456",
            agent_id="test-agent-789",
            tenant_id=None,  # No tenant ID
        )
        arguments = {"input": "test"}

        # Act
        await executor.execute("mock_tool", arguments, context, chain)

        # Assert
        rate_limiter.check_limit.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_default_retryable_errors(
        self, registry: ToolRegistry, context: ToolCallContext, chain: ReasoningChain
    ) -> None:
        """Should use default retryable error heuristics when none configured."""
        # Arrange
        call_count = 0

        async def connection_error(ctx: ToolCallContext, args: dict[str, Any]) -> ToolResult:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("Network timeout")
            return ToolResult(success=True, result={"output": "success"}, duration_ms=100)

        retry_config = ToolRetryConfig(
            max_retries=2, backoff_ms=10, retryable_errors=[]  # Empty list
        )
        tool = MockTool(execute_fn=connection_error, retry_config=retry_config)
        registry.register(tool)
        executor = ToolExecutor(registry)
        arguments = {"input": "test"}

        # Act
        result = await executor.execute("mock_tool", arguments, context, chain)

        # Assert
        assert result.success is True
        assert result.retry_count == 1
        assert call_count == 2  # Should have retried
