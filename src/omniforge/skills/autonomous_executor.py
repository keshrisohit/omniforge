"""Autonomous skill executor with ReAct loop pattern.

This module provides the AutonomousSkillExecutor class - the primary execution engine
for autonomous skill execution. It implements the ReAct (Reason-Act-Observe) pattern
with iterative refinement, allowing skills to think, call tools, observe results,
and repeat until task completion.

The executor orchestrates:
- Preprocessing pipeline (context loading, injection, substitution)
- System prompt building with skill instructions and available tools
- ReAct loop execution with LLM reasoning and tool calls
- Event streaming for real-time progress updates
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, AsyncIterator, Optional

from omniforge.agents.cot.chain import ReasoningChain
from omniforge.agents.cot.engine import ReasoningEngine
from omniforge.agents.cot.parser import ReActParser
from omniforge.agents.cot.prompts import build_react_system_prompt
from omniforge.agents.events import (
    TaskDoneEvent,
    TaskErrorEvent,
    TaskEvent,
    TaskMessageEvent,
    TaskStatusEvent,
)
from omniforge.agents.models import TextPart
from omniforge.skills.config import (
    AutonomousConfig,
    ExecutionContext,
    ExecutionMetrics,
    ExecutionResult,
    ExecutionState,
)
from omniforge.skills.context_loader import ContextLoader
from omniforge.skills.models import Skill
from omniforge.skills.string_substitutor import StringSubstitutor, SubstitutionContext
from omniforge.tasks.models import TaskState
from omniforge.tools.executor import ToolExecutor
from omniforge.tools.registry import ToolRegistry
from omniforge.tools.types import VisibilityLevel

logger = logging.getLogger(__name__)

# Model mapping from simple names to Anthropic model IDs
MODEL_MAP = {
    "haiku": "claude-haiku-4",
    "sonnet": "claude-sonnet-4",
    "opus": "claude-opus-4",
}

def _get_default_model() -> str:
    """Get default model from environment or return fallback."""
    from omniforge.llm.config import load_config_from_env
    try:
        config = load_config_from_env()
        return config.default_model
    except Exception:
        # Fallback to OpenRouter (litellm-compatible model ID)
        return "openrouter/arcee-ai/trinity-large-preview:free"

# Model costs for tracking (approximate, per 1M tokens)
MODEL_COSTS = {
    "claude-haiku-4": {"input": 0.25, "output": 1.25},
    "claude-sonnet-4": {"input": 3.0, "output": 15.0},
    "claude-opus-4": {"input": 15.0, "output": 75.0},
}


class AutonomousSkillExecutor:
    """Autonomous skill executor implementing the ReAct loop pattern.

    This class is the core execution engine for autonomous skills. It orchestrates
    the preprocessing pipeline, builds system prompts, runs the ReAct loop,
    and emits streaming events for real-time progress visibility.

    The ReAct loop follows this pattern:
    1. Reason: LLM analyzes current state and decides on action
    2. Act: Execute the chosen tool with appropriate arguments
    3. Observe: Capture tool output and add to conversation context
    4. Repeat until task complete or max iterations reached

    Attributes:
        skill: The skill definition with instructions and metadata
        tool_registry: Registry of available tools
        tool_executor: Executor for running tools
        config: Execution configuration parameters
        context: Execution context for depth tracking
        context_loader: Optional loader for supporting files
        string_substitutor: Optional substitutor for variable replacement
    """

    def __init__(
        self,
        skill: Skill,
        tool_registry: ToolRegistry,
        tool_executor: ToolExecutor,
        config: Optional[AutonomousConfig] = None,
        context: Optional[ExecutionContext] = None,
        context_loader: Optional[ContextLoader] = None,
        string_substitutor: Optional[StringSubstitutor] = None,
    ) -> None:
        """Initialize autonomous skill executor.

        Args:
            skill: Skill definition with instructions and metadata
            tool_registry: Registry of available tools
            tool_executor: Executor for running tools
            config: Optional execution configuration (uses defaults if not provided)
            context: Optional execution context for depth tracking (uses defaults if not provided)
            context_loader: Optional loader for supporting files
            string_substitutor: Optional substitutor for variable replacement
        """
        self.skill = skill
        self.tool_registry = tool_registry
        self.tool_executor = tool_executor
        self.config = config or AutonomousConfig()
        self.context = context or ExecutionContext()
        self.context_loader = context_loader or ContextLoader(skill)
        self.string_substitutor = string_substitutor or StringSubstitutor()
        self._parser = ReActParser()

    def _resolve_model(self) -> str:
        """Resolve LLM model to use for this skill.

        Priority: config override > skill metadata > environment default

        Returns:
            Resolved model ID (e.g., "openrouter/arcee-ai/trinity-large-preview:free")
        """
        # Priority: config override > skill metadata > environment default
        if self.config.model:
            return self._resolve_model_name(self.config.model)

        if self.skill.metadata.model:
            return self._resolve_model_name(self.skill.metadata.model)

        return _get_default_model()

    def _resolve_model_name(self, model_hint: str) -> str:
        """Map model hint to actual model ID.

        Args:
            model_hint: Model hint (e.g., "haiku", "sonnet", or full ID)

        Returns:
            Actual model ID. If hint is in MODEL_MAP, returns mapped value.
            Otherwise returns the hint as-is for future compatibility.
        """
        return MODEL_MAP.get(model_hint.lower(), model_hint)

    async def execute(
        self,
        user_request: str,
        task_id: str,
        session_id: str,
        tenant_id: Optional[str] = None,
    ) -> AsyncIterator[TaskEvent]:
        """Execute skill autonomously with streaming events.

        This is the main entry point for autonomous execution. It runs the complete
        ReAct loop and yields TaskEvent instances for real-time progress updates.

        Args:
            user_request: User's request/task description
            task_id: Unique task identifier
            session_id: Session identifier for this execution
            tenant_id: Optional tenant identifier for multi-tenancy

        Yields:
            TaskEvent instances (status, message, error, done) throughout execution

        Example:
            >>> executor = AutonomousSkillExecutor(skill, registry, tool_executor)
            >>> async for event in executor.execute("Process data.csv", "task-123", "session-1"):
            ...     if isinstance(event, TaskMessageEvent):
            ...         print(f"Progress: {event.message_parts[0].text}")
            ...     elif isinstance(event, TaskDoneEvent):
            ...         print(f"Completed with state: {event.final_state}")
        """
        # Emit starting event
        yield TaskStatusEvent(
            task_id=task_id,
            timestamp=datetime.utcnow(),
            state=TaskState.WORKING,
            message="Starting autonomous skill execution",
            visibility=VisibilityLevel.SUMMARY,
        )

        # Initialize execution state
        state = ExecutionState(start_time=datetime.utcnow())

        try:
            # Step 1: Preprocess content
            processed_content = await self._preprocess_content(user_request, session_id, tenant_id)

            # Step 2: Build system prompt
            system_prompt = await self._build_system_prompt(processed_content)

            # Step 3: Initialize reasoning engine
            chain = ReasoningChain(
                task_id=task_id,
                agent_id=f"skill-{self.skill.metadata.name}",
            )

            task_dict = {
                "id": task_id,
                "agent_id": f"skill-{self.skill.metadata.name}",
                "tenant_id": tenant_id,
                "chain_id": str(chain.id),
            }

            engine = ReasoningEngine(
                chain=chain,
                executor=self.tool_executor,
                task=task_dict,
                default_llm_model=self._resolve_model(),
            )

            # Step 4: Execute ReAct loop
            async for event in self._execute_react_loop(
                user_request=user_request,
                system_prompt=system_prompt,
                engine=engine,
                state=state,
                task_id=task_id,
            ):
                yield event

        except Exception as e:
            logger.exception(f"Error in autonomous execution: {e}")

            # Emit error event
            yield TaskErrorEvent(
                task_id=task_id,
                timestamp=datetime.utcnow(),
                error_code="EXECUTION_ERROR",
                error_message=f"Autonomous execution failed: {str(e)}",
                details={"skill": self.skill.metadata.name},
                visibility=VisibilityLevel.SUMMARY,
            )

            # Emit done event with failed state
            yield TaskDoneEvent(
                task_id=task_id,
                timestamp=datetime.utcnow(),
                final_state=TaskState.FAILED,
            )

    async def execute_sync(
        self,
        user_request: str,
        task_id: str,
        session_id: str,
        tenant_id: Optional[str] = None,
    ) -> ExecutionResult:
        """Execute skill and return final result (non-streaming).

        Convenience wrapper around execute() that collects all events and returns
        a single ExecutionResult with the final outcome and metrics.

        Args:
            user_request: User's request/task description
            task_id: Unique task identifier
            session_id: Session identifier for this execution
            tenant_id: Optional tenant identifier for multi-tenancy

        Returns:
            ExecutionResult with success status, result text, and metrics

        Example:
            >>> executor = AutonomousSkillExecutor(skill, registry, tool_executor)
            >>> result = await executor.execute_sync("Process data.csv", "task-123", "session-1")
            >>> if result.success:
            ...     print(f"Result: {result.result}")
            ... else:
            ...     print(f"Error: {result.error}")
        """
        events = []
        final_result = ""
        error_message: Optional[str] = None
        success = False
        iterations_used = 0
        partial_results: list[str] = []
        start_time = datetime.utcnow()

        # Collect all events
        async for event in self.execute(user_request, task_id, session_id, tenant_id):
            events.append(event)

            # Extract final result from message events
            if isinstance(event, TaskMessageEvent):
                for part in event.message_parts:
                    if isinstance(part, TextPart):
                        final_result += part.text

            # Track errors
            elif isinstance(event, TaskErrorEvent):
                error_message = event.error_message

            # Check final state
            elif isinstance(event, TaskDoneEvent):
                success = event.final_state == TaskState.COMPLETED

        # Build metrics from events
        metrics = ExecutionMetrics()
        # Track model used for execution
        resolved_model = self._resolve_model()
        metrics.model_used = resolved_model

        # Calculate estimated cost per call
        from omniforge.skills.autonomous_executor import MODEL_COSTS

        if resolved_model in MODEL_COSTS:
            # Average of input and output costs (rough estimate)
            costs = MODEL_COSTS[resolved_model]
            metrics.estimated_cost_per_call = (costs["input"] + costs["output"]) / 2 / 1_000_000

        tool_calls_successful = 0
        tool_calls_failed = 0
        error_recoveries = 0

        for event in events:
            if isinstance(event, TaskMessageEvent):
                # Count action messages as iterations
                for part in event.message_parts:
                    if isinstance(part, TextPart) and "Action:" in part.text:
                        iterations_used += 1
            elif isinstance(event, TaskErrorEvent):
                if "retry" in event.error_message.lower():
                    error_recoveries += 1

        # Update metrics with counts
        metrics.tool_calls_successful = tool_calls_successful
        metrics.tool_calls_failed = tool_calls_failed
        metrics.error_recoveries = error_recoveries

        # Calculate duration
        duration = (datetime.utcnow() - start_time).total_seconds()
        metrics.duration_seconds = duration

        # Extract partial results from final message if present
        if "partial" in final_result.lower() or "completed" in final_result.lower():
            # Parse partial results from synthesis message
            lines = final_result.split("\n")
            for line in lines:
                if line.strip().startswith("- "):
                    partial_results.append(line.strip()[2:])

        return ExecutionResult(
            success=success,
            result=final_result,
            iterations_used=iterations_used,
            chain_id=task_id,
            metrics=metrics,
            partial_results=partial_results,
            error=error_message,
        )

    async def _preprocess_content(
        self,
        user_request: str,
        session_id: str,
        tenant_id: Optional[str] = None,
    ) -> str:
        """Preprocess skill content with substitution.

        Applies string substitution to replace variables in the skill content
        before execution. Variables like $ARGUMENTS, ${SKILL_DIR}, etc. are replaced.

        Args:
            user_request: User's request (becomes $ARGUMENTS)
            session_id: Session identifier
            tenant_id: Optional tenant identifier

        Returns:
            Preprocessed skill content with variables replaced
        """
        # Build substitution context
        context = SubstitutionContext(
            arguments=user_request,
            session_id=session_id,
            skill_dir=str(self.skill.base_path),
            workspace=str(self.skill.base_path),
            user=tenant_id or "default",
            date=datetime.utcnow().strftime("%Y-%m-%d"),
        )

        # Substitute variables
        result = self.string_substitutor.substitute(
            content=self.skill.content,
            context=context,
            auto_append_arguments=True,
        )

        if result.undefined_vars:
            logger.warning(f"Undefined variables in skill content: {result.undefined_vars}")

        return result.content

    async def _build_system_prompt(self, processed_content: str) -> str:
        """Build system prompt with skill instructions and available tools.

        Creates a comprehensive system prompt that includes:
        - Skill instructions (processed content)
        - Available tools from registry
        - Available supporting files from context loader
        - ReAct format instructions

        Args:
            processed_content: Preprocessed skill content

        Returns:
            Complete system prompt for LLM
        """
        from omniforge.prompts import get_default_registry

        # Get available tools (respect allowed_tools if specified)
        available_tool_names = list(self.tool_registry.list_tools())
        if self.skill.metadata.allowed_tools:
            available_tool_names = [
                t for t in available_tool_names if t in self.skill.metadata.allowed_tools
            ]

        # Get tool definitions
        tool_definitions = []
        for tool_name in available_tool_names:
            try:
                definition = self.tool_registry.get_definition(tool_name)
                tool_definitions.append(definition)
            except Exception as e:
                logger.warning(f"Could not get definition for tool {tool_name}: {e}")

        # Build base ReAct prompt with tools
        base_prompt = build_react_system_prompt(tool_definitions)

        # Get available supporting files from context loader
        context = self.context_loader.load_initial_context()
        available_files_section = ""
        if context.available_files:
            files_list = []
            for filename, file_ref in context.available_files.items():
                line_info = (
                    f" (~{file_ref.estimated_lines} lines)" if file_ref.estimated_lines else ""
                )
                files_list.append(f"- {filename}{line_info}: {file_ref.description}")
            available_files_section = "\n\n**Available Supporting Files:**\n" + "\n".join(
                files_list
            )

        # Use skill_wrapper template from registry
        registry = get_default_registry()
        full_prompt = registry.render(
            "skill_wrapper",
            skill_name=self.skill.metadata.name,
            skill_description=self.skill.metadata.description,
            skill_content=processed_content,
            available_files_section=available_files_section,
            base_react_prompt=base_prompt,
            allowed_tools=", ".join(available_tool_names),
        )

        return full_prompt

    async def _execute_react_loop(
        self,
        user_request: str,
        system_prompt: str,
        engine: ReasoningEngine,
        state: ExecutionState,
        task_id: str,
    ) -> AsyncIterator[TaskEvent]:
        """Execute the core ReAct loop with iterative refinement.

        Implements the Reason-Act-Observe pattern:
        1. Reason: LLM analyzes state and decides action
        2. Act: Execute tool with arguments
        3. Observe: Add result to conversation
        4. Repeat until complete or max iterations

        Args:
            user_request: User's original request
            system_prompt: Complete system prompt with instructions
            engine: Reasoning engine for LLM and tool calls
            state: Execution state tracker
            task_id: Task identifier

        Yields:
            TaskEvent instances for progress updates
        """
        # Initialize conversation with user request and JSON reminder
        json_reminder = "IMPORTANT: Respond with valid JSON only as specified in the system prompt."
        conversation: list[dict[str, str]] = [
            {"role": "user", "content": f"{user_request}\n\n{json_reminder}"}
        ]

        # Execute ReAct loop
        for iteration in range(self.config.max_iterations):
            state.iteration = iteration

            # Emit iteration progress
            iteration_msg = (
                f"Iteration {iteration + 1}/{self.config.max_iterations}: Analyzing next step"
            )
            yield TaskMessageEvent(
                task_id=task_id,
                timestamp=datetime.utcnow(),
                message_parts=[TextPart(text=iteration_msg)],
                is_partial=True,
                visibility=VisibilityLevel.FULL,
            )

            try:
                # Apply timeout per iteration
                async with asyncio.timeout(self.config.timeout_per_iteration_ms / 1000):  # type: ignore[attr-defined]
                    # Get LLM decision
                    llm_result = await engine.call_llm(
                        messages=conversation,
                        system=system_prompt,
                        model=self._resolve_model(),
                        temperature=self.config.temperature,
                    )

                # Check if LLM call succeeded
                if not llm_result.success or not llm_result.value:
                    error_msg = f"LLM call failed: {llm_result.error}"
                    logger.error(error_msg)

                    yield TaskErrorEvent(
                        task_id=task_id,
                        timestamp=datetime.utcnow(),
                        error_code="LLM_CALL_FAILED",
                        error_message=error_msg,
                        visibility=VisibilityLevel.SUMMARY,
                    )

                    state.error_count += 1

                    # Continue or fail based on config
                    if not self.config.enable_error_recovery:
                        yield TaskDoneEvent(
                            task_id=task_id,
                            timestamp=datetime.utcnow(),
                            final_state=TaskState.FAILED,
                        )
                        return

                    continue

                # Extract LLM response
                llm_response = llm_result.value.get("content", "")

                # Parse response for action or final answer
                parsed = self._parser.parse(llm_response)

                # Log thought if present
                if parsed.thought:
                    yield TaskMessageEvent(
                        task_id=task_id,
                        timestamp=datetime.utcnow(),
                        message_parts=[TextPart(text=f"Thought: {parsed.thought}")],
                        is_partial=True,
                        visibility=VisibilityLevel.FULL,
                    )

                # Check for final answer
                if parsed.is_final:
                    # Use final_answer if provided, otherwise use a default message
                    final_message = parsed.final_answer or "Task completed."
                    yield TaskMessageEvent(
                        task_id=task_id,
                        timestamp=datetime.utcnow(),
                        message_parts=[TextPart(text=f"Final answer: {final_message}")],
                        is_partial=False,
                        visibility=VisibilityLevel.SUMMARY,
                    )

                    yield TaskDoneEvent(
                        task_id=task_id,
                        timestamp=datetime.utcnow(),
                        final_state=TaskState.COMPLETED,
                    )
                    return

                # Must have an action if not final
                if not parsed.action:
                    error_msg = f"LLM response has no action or final answer: {llm_response[:200]}"
                    logger.warning(error_msg)

                    yield TaskErrorEvent(
                        task_id=task_id,
                        timestamp=datetime.utcnow(),
                        error_code="INVALID_RESPONSE",
                        error_message=error_msg,
                        visibility=VisibilityLevel.SUMMARY,
                    )

                    state.error_count += 1
                    continue

                # Execute tool action
                yield TaskMessageEvent(
                    task_id=task_id,
                    timestamp=datetime.utcnow(),
                    message_parts=[TextPart(text=f"Action: {parsed.action}")],
                    is_partial=True,
                    visibility=VisibilityLevel.SUMMARY,
                )

                try:
                    tool_result = await engine.call_tool(
                        tool_name=parsed.action,
                        arguments=parsed.action_input or {},
                    )

                    # Format observation
                    if tool_result.success:
                        result_value = tool_result.value
                        # Truncate large results for context efficiency
                        result_str = str(result_value)
                        if len(result_str) > 2000:
                            result_str = result_str[:2000] + "...(truncated)"
                        observation = f"Observation: {result_str}"

                        # Track successful tool call
                        state.observations.append(
                            {
                                "tool": parsed.action,
                                "result": result_value,
                                "success": True,
                            }
                        )

                        # Record meaningful partial result
                        if self._is_meaningful_result(tool_result):
                            partial_result = self._summarize_result(
                                tool_name=parsed.action, result=tool_result
                            )
                            state.partial_results.append(partial_result)
                            logger.info(f"Recorded partial result: {partial_result}")
                    else:
                        # Handle tool error with recovery strategy
                        observation = await self._handle_tool_error(
                            tool_name=parsed.action,
                            error=tool_result.error or "Unknown error",
                            state=state,
                            tool_args=parsed.action_input or {},
                        )
                        state.error_count += 1

                        # Track failed tool call
                        state.observations.append(
                            {
                                "tool": parsed.action,
                                "error": tool_result.error,
                                "success": False,
                            }
                        )

                except Exception as e:
                    # Handle exception with recovery strategy
                    observation = await self._handle_tool_error(
                        tool_name=parsed.action,
                        error=str(e),
                        state=state,
                        tool_args=parsed.action_input or {},
                    )
                    state.error_count += 1

                    logger.exception(f"Tool execution error: {e}")

                    yield TaskErrorEvent(
                        task_id=task_id,
                        timestamp=datetime.utcnow(),
                        error_code="TOOL_EXECUTION_ERROR",
                        error_message=str(e),
                        visibility=VisibilityLevel.SUMMARY,
                    )

                # Emit observation event for visibility
                yield TaskMessageEvent(
                    task_id=task_id,
                    timestamp=datetime.utcnow(),
                    message_parts=[TextPart(text=observation)],
                    is_partial=True,
                    visibility=VisibilityLevel.FULL,
                )

                # Add to conversation
                conversation.append({"role": "assistant", "content": llm_response})
                conversation.append({"role": "user", "content": observation})

            except asyncio.TimeoutError:
                error_msg = f"Iteration timeout after {self.config.timeout_per_iteration_ms}ms"
                logger.warning(error_msg)

                yield TaskErrorEvent(
                    task_id=task_id,
                    timestamp=datetime.utcnow(),
                    error_code="ITERATION_TIMEOUT",
                    error_message=error_msg,
                    visibility=VisibilityLevel.SUMMARY,
                )

                state.error_count += 1

                if not self.config.enable_error_recovery:
                    yield TaskDoneEvent(
                        task_id=task_id,
                        timestamp=datetime.utcnow(),
                        final_state=TaskState.FAILED,
                    )
                    return

        # Max iterations reached without final answer - return partial results
        error_msg = (
            f"Reached maximum iterations ({self.config.max_iterations}) "
            f"without producing final answer"
        )
        logger.warning(error_msg)

        yield TaskErrorEvent(
            task_id=task_id,
            timestamp=datetime.utcnow(),
            error_code="MAX_ITERATIONS_REACHED",
            error_message=error_msg,
            visibility=VisibilityLevel.SUMMARY,
        )

        # Synthesize partial results if available
        if state.partial_results:
            partial_synthesis = self._synthesize_partial_results(state)
            yield TaskMessageEvent(
                task_id=task_id,
                timestamp=datetime.utcnow(),
                message_parts=[TextPart(text=partial_synthesis)],
                is_partial=False,
                visibility=VisibilityLevel.SUMMARY,
            )

        yield TaskDoneEvent(
            task_id=task_id,
            timestamp=datetime.utcnow(),
            final_state=TaskState.FAILED,
        )

    async def _handle_tool_error(
        self,
        tool_name: str,
        error: str,
        state: ExecutionState,
        tool_args: dict,
    ) -> str:
        """Handle tool execution error with recovery strategy.

        Implements intelligent error recovery:
        1. Track failed approaches to avoid infinite loops
        2. Retry up to max_retries_per_tool times
        3. Suggest alternative approaches after max retries

        Args:
            tool_name: Name of the tool that failed
            error: Error message from tool execution
            state: Current execution state
            tool_args: Arguments passed to the tool

        Returns:
            Observation message for conversation context
        """
        # Create approach key for tracking (tool name + error hash)
        # Use first 100 chars of error to group similar errors
        error_sample = error[:100] if len(error) > 100 else error
        approach_key = f"{tool_name}:{hash(error_sample)}"

        # Check retry count for this approach
        retry_count = state.failed_approaches.get(approach_key, 0)

        if retry_count < self.config.max_retries_per_tool:
            # Increment retry counter
            state.failed_approaches[approach_key] = retry_count + 1

            logger.info(
                f"Tool '{tool_name}' failed (attempt {retry_count + 1}/"
                f"{self.config.max_retries_per_tool}): {error[:200]}"
            )

            # Suggest retry with different parameters or approach
            return (
                f"Observation: Tool '{tool_name}' failed: {error}\n"
                f"Retry attempt {retry_count + 1}/{self.config.max_retries_per_tool}. "
                f"Please retry with different parameters or try an alternative approach."
            )

        # Max retries exceeded - must try completely different approach
        logger.warning(
            f"Tool '{tool_name}' failed after {retry_count} attempts. "
            f"Suggesting alternative approach."
        )

        return (
            f"Observation: Tool '{tool_name}' failed after {retry_count} attempts: {error}\n"
            f"This approach is not working. Please try a completely different "
            f"tool or method to accomplish this task."
        )

    def _is_meaningful_result(self, tool_result: Any) -> bool:
        """Check if tool result contains meaningful data worth tracking.

        Args:
            tool_result: Result from tool execution

        Returns:
            True if result is meaningful, False otherwise
        """
        if not tool_result.success or not tool_result.value:
            return False

        # Check if result has substantive content
        result_value = tool_result.value

        # Handle different result types
        if isinstance(result_value, str):
            # Non-empty strings with meaningful content
            return len(result_value.strip()) > 10

        if isinstance(result_value, dict):
            # Dicts with actual data (not just metadata)
            return bool(result_value)

        if isinstance(result_value, list):
            # Non-empty lists
            return len(result_value) > 0

        # For other types, consider them meaningful if present
        return True

    def _summarize_result(self, tool_name: str, result: Any) -> str:
        """Summarize a tool result for partial results tracking.

        Args:
            tool_name: Name of the tool that produced the result
            result: Tool result to summarize

        Returns:
            Human-readable summary of the result
        """
        result_value = result.value

        # Summarize based on type
        if isinstance(result_value, str):
            # Truncate long strings
            max_len = 100
            if len(result_value) > max_len:
                return f"{tool_name}: {result_value[:max_len]}... (truncated)"
            return f"{tool_name}: {result_value}"

        if isinstance(result_value, dict):
            # Summarize dict size and keys
            keys = list(result_value.keys())[:3]
            keys_str = ", ".join(keys)
            if len(result_value) > 3:
                keys_str += "..."
            return f"{tool_name}: Retrieved {len(result_value)} items ({keys_str})"

        if isinstance(result_value, list):
            # Summarize list size
            return f"{tool_name}: Retrieved {len(result_value)} items"

        # Generic summary
        return f"{tool_name}: {str(result_value)[:100]}"

    def _synthesize_partial_results(self, state: ExecutionState) -> str:
        """Synthesize partial results when complete solution not possible.

        Args:
            state: Current execution state with partial results

        Returns:
            Human-readable synthesis of partial results
        """
        if not state.partial_results:
            return (
                "Unable to complete task. No partial results available.\n"
                f"Encountered {state.error_count} errors during execution."
            )

        # Build partial results summary
        results_text = "\n".join(f"  - {r}" for r in state.partial_results)

        return (
            f"Task incomplete. Completed {len(state.partial_results)} "
            f"of intended objectives:\n{results_text}\n\n"
            f"Encountered {state.error_count} errors during execution."
        )
