"""Tool execution with retry logic, timeout enforcement, and chain integration.

This module provides the ToolExecutor class that handles unified tool execution
with support for retries, timeouts, rate limiting, cost tracking, and integration
with the reasoning chain.
"""

import asyncio
import logging
import re
import time
from typing import Any, Optional, Protocol

from omniforge.agents.cot.chain import (
    ReasoningStep,
    StepType,
    ToolCallInfo,
    ToolResultInfo,
    VisibilityConfig,
)
from omniforge.core.protocols import ChainRecorder
from omniforge.skills.context import SkillContext
from omniforge.skills.errors import SkillActivationError, SkillError
from omniforge.skills.models import Skill
from omniforge.tools.base import BaseTool, ToolCallContext, ToolResult
from omniforge.tools.errors import (
    ToolTimeoutError,
)
from omniforge.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class RateLimiter(Protocol):
    """Protocol for rate limiting implementation."""

    async def check_limit(self, tenant_id: str, tool_name: str) -> None:
        """Check if rate limit allows execution.

        Args:
            tenant_id: Tenant making the request
            tool_name: Tool being executed

        Raises:
            RateLimitExceededError: If rate limit is exceeded
        """
        ...


class CostTracker(Protocol):
    """Protocol for cost tracking implementation."""

    async def track_cost(
        self, task_id: str, tool_name: str, cost_usd: float, tokens_used: int
    ) -> None:
        """Track cost and token usage for a tool execution.

        Args:
            task_id: Task ID for tracking
            tool_name: Tool that was executed
            cost_usd: Cost in USD
            tokens_used: Number of tokens consumed
        """
        ...


class ToolExecutor:
    """Unified executor for tool execution with retry, timeout, and chain integration.

    The executor handles:
    - Tool retrieval from registry
    - Argument validation
    - Rate limiting (optional)
    - Retry logic with exponential backoff
    - Timeout enforcement
    - Cost tracking (optional)
    - Reasoning chain integration with correlation IDs
    """

    def __init__(
        self,
        registry: ToolRegistry,
        rate_limiter: Optional[RateLimiter] = None,
        cost_tracker: Optional[CostTracker] = None,
        backend: Optional[Any] = None,
    ) -> None:
        """Initialize the tool executor.

        Args:
            registry: Tool registry for retrieving tools
            rate_limiter: Optional rate limiter for request throttling
            cost_tracker: Optional cost tracker for monitoring expenses
            backend: Execution backend (defaults to InProcessBackend)
        """
        from omniforge.execution import InProcessBackend

        self._registry = registry
        self._rate_limiter = rate_limiter
        self._cost_tracker = cost_tracker
        self._backend = backend or InProcessBackend()
        self._skill_stack: list[Skill] = []
        self._skill_contexts: dict[str, SkillContext] = {}

    @property
    def active_skill(self) -> Optional[Skill]:
        """Get the currently active skill from top of stack.

        Returns:
            The active skill if one exists, None otherwise
        """
        return self._skill_stack[-1] if self._skill_stack else None

    def activate_skill(self, skill: Skill) -> None:
        """Activate a skill and push it onto the execution stack.

        Creates a SkillContext for the skill and enforces restrictions during
        tool execution. The activation is exception-safe - restrictions will
        persist even if tool execution fails.

        Args:
            skill: The skill to activate

        Raises:
            SkillActivationError: If skill is already active
        """
        skill_name = skill.metadata.name

        # Check if skill is already active
        if skill_name in self._skill_contexts:
            raise SkillActivationError(
                skill_name=skill_name, reason="Skill is already active in the stack"
            )

        # Create skill context with executor reference
        skill_context = SkillContext(skill, executor=self)

        # Enter the context to set up allowed tools
        skill_context.__enter__()

        # Push to stack and register in contexts
        self._skill_stack.append(skill)
        self._skill_contexts[skill_name] = skill_context

        # Audit logging
        logger.info(
            f"Skill activated: {skill_name}",
            extra={
                "skill_name": skill_name,
                "stack_depth": len(self._skill_stack),
                "allowed_tools": skill.metadata.allowed_tools,
            },
        )

    def deactivate_skill(self, skill_name: str) -> None:
        """Deactivate a skill and remove it from the execution stack.

        Enforces LIFO (Last In, First Out) stack discipline - can only deactivate
        the skill at the top of the stack.

        Args:
            skill_name: Name of the skill to deactivate

        Raises:
            SkillError: If skill is not active or not at top of stack
        """
        # Check if skill is active
        if skill_name not in self._skill_contexts:
            raise SkillError(
                message=f"Cannot deactivate skill '{skill_name}': not active",
                error_code="skill_not_active",
                context={"skill_name": skill_name},
            )

        # Enforce stack discipline - can only deactivate top skill
        if not self._skill_stack or self._skill_stack[-1].metadata.name != skill_name:
            current_top = self._skill_stack[-1].metadata.name if self._skill_stack else None
            raise SkillError(
                message=(
                    f"Cannot deactivate skill '{skill_name}': not at top of stack. "
                    f"Current top: {current_top}"
                ),
                error_code="skill_stack_violation",
                context={"skill_name": skill_name, "stack_top": current_top},
            )

        # Get context and exit it
        skill_context = self._skill_contexts[skill_name]
        skill_context.__exit__(None, None, None)

        # Remove from stack and contexts
        self._skill_stack.pop()
        del self._skill_contexts[skill_name]

        # Audit logging
        logger.info(
            f"Skill deactivated: {skill_name}",
            extra={"skill_name": skill_name, "stack_depth": len(self._skill_stack)},
        )

    async def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        context: ToolCallContext,
        chain: ChainRecorder,
    ) -> ToolResult:
        """Execute a tool with full retry and chain integration.

        Args:
            tool_name: Name of the tool to execute
            arguments: Arguments to pass to the tool
            context: Execution context with task/agent/tenant info
            chain: Chain recorder to record steps in

        Returns:
            ToolResult containing execution outcome and metadata

        Raises:
            ToolNotFoundError: If tool is not found in registry
            ToolValidationError: If argument validation fails
            RateLimitExceededError: If rate limit is exceeded
            ToolTimeoutError: If execution exceeds timeout
            ToolExecutionError: If execution fails after retries
        """
        # Retrieve tool from registry
        tool = self._registry.get(tool_name)

        # Validate arguments
        tool.validate_arguments(arguments)

        # Check skill restrictions if active skill exists
        if self.active_skill:
            skill_context = self._skill_contexts[self.active_skill.metadata.name]
            try:
                # Check if tool is allowed
                skill_context.check_tool_allowed(tool_name)
                # Check tool arguments
                skill_context.check_tool_arguments(tool_name, arguments)
            except SkillError as e:
                # Return error result instead of executing
                logger.warning(
                    f"Skill restriction blocked tool execution: {e.message}",
                    extra={
                        "skill_name": self.active_skill.metadata.name,
                        "tool_name": tool_name,
                        "error_code": e.error_code,
                    },
                )
                return ToolResult(
                    success=False,
                    error=e.message,
                    duration_ms=0,
                    retry_count=0,
                )

        # Check rate limits if limiter is configured
        if self._rate_limiter and context.tenant_id:
            await self._rate_limiter.check_limit(context.tenant_id, tool_name)

        # Create tool_call step and add to chain
        tool_call_step = ReasoningStep(
            step_number=0,  # Will be updated by chain.add_step
            type=StepType.TOOL_CALL,
            tool_call=ToolCallInfo(
                tool_name=tool_name,
                tool_type=tool.definition.type,
                parameters=arguments,
                correlation_id=context.correlation_id,
            ),
            visibility=VisibilityConfig(level=tool.definition.visibility.default_level),
        )
        chain.add_step(tool_call_step)

        # Execute tool with retries via backend
        async def _run() -> ToolResult:
            return await self._execute_with_retries(tool, arguments, context)

        result = await self._backend.run_activity(
            _run,
            activity_name=tool_name,
            timeout_ms=tool.definition.timeout_ms,
            max_retries=tool.definition.retry_config.max_retries,
        )

        # Track cost if tracker is configured
        if self._cost_tracker:
            await self._cost_tracker.track_cost(
                context.task_id, tool_name, result.cost_usd, result.tokens_used
            )

        # Create tool_result step with matching correlation_id
        tool_result_step = ReasoningStep(
            step_number=0,  # Will be updated by chain.add_step
            type=StepType.TOOL_RESULT,
            tool_result=ToolResultInfo(
                correlation_id=context.correlation_id,
                success=result.success,
                result=result.result,
                error=result.error,
            ),
            tokens_used=result.tokens_used,
            cost=result.cost_usd,
            visibility=VisibilityConfig(level=tool.definition.visibility.default_level),
        )
        chain.add_step(tool_result_step)

        return result

    async def _execute_with_retries(
        self, tool: BaseTool, arguments: dict[str, Any], context: ToolCallContext
    ) -> ToolResult:
        """Execute tool with retry logic and exponential backoff.

        Args:
            tool: Tool instance to execute
            arguments: Validated arguments for the tool
            context: Execution context

        Returns:
            ToolResult with retries_used count and duration_ms

        Raises:
            ToolTimeoutError: If execution exceeds timeout
            ToolExecutionError: If execution fails after all retries
        """
        retry_config = tool.definition.retry_config
        timeout_seconds = tool.definition.timeout_ms / 1000.0
        last_error: Optional[Exception] = None
        retries_used = 0

        for attempt in range(retry_config.max_retries + 1):
            start_time = time.time()

            try:
                # Execute with timeout enforcement
                result = await asyncio.wait_for(
                    tool.execute(context, arguments), timeout=timeout_seconds
                )

                # Calculate duration
                duration_ms = int((time.time() - start_time) * 1000)

                # Update result with retry count and ensure duration is set
                result.retry_count = retries_used
                if result.duration_ms == 0:
                    result.duration_ms = duration_ms

                return result

            except asyncio.TimeoutError:
                # Timeout is not retryable
                duration_ms = int((time.time() - start_time) * 1000)
                raise ToolTimeoutError(
                    tool_name=tool.definition.name,
                    timeout_seconds=timeout_seconds,
                    duration_ms=duration_ms,
                )

            except Exception as e:
                last_error = e
                error_type = type(e).__name__

                # Check if error is retryable
                is_retryable = self._is_retryable_error(error_type, retry_config)

                if not is_retryable or attempt >= retry_config.max_retries:
                    # No more retries, return error result
                    duration_ms = int((time.time() - start_time) * 1000)
                    return ToolResult(
                        success=False,
                        error=str(e),
                        duration_ms=duration_ms,
                        retry_count=retries_used,
                    )

                # Increment retry counter
                retries_used += 1

                # Check if this is a rate limit error and extract wait time
                rate_limit_wait = self._extract_rate_limit_wait_time(str(e))

                # Calculate backoff delay
                if rate_limit_wait is not None:
                    # Use the rate limit suggested wait time + small buffer
                    backoff_seconds = rate_limit_wait + 0.5

                    # Reduce max_tokens for LLM tool if rate limited
                    if tool.definition.name == "llm" and "max_tokens" in arguments:
                        original_max_tokens = arguments["max_tokens"]
                        # Reduce by 30% for next retry
                        arguments["max_tokens"] = int(original_max_tokens * 0.7)
                else:
                    # Standard exponential backoff
                    backoff_seconds = (
                        retry_config.backoff_ms * (retry_config.backoff_multiplier**attempt)
                    ) / 1000.0

                # Wait before retrying
                await asyncio.sleep(backoff_seconds)

        # Should not reach here, but handle it gracefully
        duration_ms = int((time.time() - start_time) * 1000)
        error_msg = str(last_error) if last_error else "Unknown error"
        return ToolResult(
            success=False, error=error_msg, duration_ms=duration_ms, retry_count=retries_used
        )

    def _is_retryable_error(self, error_type: str, retry_config: Any) -> bool:
        """Check if an error type is retryable based on configuration.

        Args:
            error_type: Type name of the error
            retry_config: Retry configuration with retryable_errors list

        Returns:
            True if the error should trigger a retry, False otherwise
        """
        # If no retryable errors configured, use default heuristic
        if not retry_config.retryable_errors:
            # Common retryable error patterns
            retryable_patterns = [
                "Timeout",
                "Connection",
                "Network",
                "Temporary",
                "Throttle",
                "RateLimit",
                "ServiceUnavailable",
            ]
            return any(pattern.lower() in error_type.lower() for pattern in retryable_patterns)

        # Check against configured retryable errors
        for pattern in retry_config.retryable_errors:
            if pattern.lower() in error_type.lower():
                return True

        return False

    def _extract_rate_limit_wait_time(self, error_message: str) -> Optional[float]:
        """Extract wait time from rate limit error messages.

        Parses error messages from providers like Groq, OpenAI, etc. to extract
        the suggested wait time before retrying.

        Args:
            error_message: The error message string

        Returns:
            Wait time in seconds, or None if not found

        Examples:
            >>> _extract_rate_limit_wait_time("Please try again in 21s")
            21.0
            >>> _extract_rate_limit_wait_time("Please try again in 810ms")
            0.81
        """
        import re

        # Try to find wait time in seconds (e.g., "21s", "21.5s")
        match = re.search(r"try again in (\d+(?:\.\d+)?)s(?!\w)", error_message)
        if match:
            return float(match.group(1))

        # Try to find wait time in milliseconds (e.g., "810ms")
        match = re.search(r"try again in (\d+(?:\.\d+)?)ms", error_message)
        if match:
            return float(match.group(1)) / 1000.0

        # Try to find wait time in minutes (e.g., "2m", "1.5m")
        match = re.search(r"try again in (\d+(?:\.\d+)?)m(?!\w)", error_message)
        if match:
            return float(match.group(1)) * 60.0

        return None

