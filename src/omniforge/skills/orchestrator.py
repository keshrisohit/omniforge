"""Skill orchestrator for routing execution to appropriate executors.

This module provides the SkillOrchestrator class that routes skill execution
to the appropriate executor based on execution mode and context configuration.
It supports:
- Autonomous execution via AutonomousSkillExecutor (ReAct loop)
- Sub-agent spawning for forked context mode

Note: The legacy "simple" execution mode using ExecutableSkill has been deprecated.
All skills now use AutonomousSkillExecutor for consistent, spec-compliant execution.
"""

import logging
from enum import Enum
from typing import AsyncIterator, Optional

from omniforge.agents.events import TaskDoneEvent, TaskEvent, TaskMessageEvent, TaskStatusEvent
from omniforge.agents.models import TextPart
from omniforge.skills.autonomous_executor import AutonomousSkillExecutor
from omniforge.skills.config import AutonomousConfig, ExecutionContext
from omniforge.skills.loader import SkillLoader
from omniforge.skills.models import ContextMode, Skill
from omniforge.tasks.models import TaskState
from omniforge.tools.executor import ToolExecutor
from omniforge.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class ExecutionMode(str, Enum):
    """Execution mode for skill routing.

    Attributes:
        AUTONOMOUS: Use AutonomousSkillExecutor with ReAct loop (default and only mode)

    Note: SIMPLE mode has been deprecated. All skills now use autonomous execution.
    """

    AUTONOMOUS = "autonomous"


class SkillOrchestrator:
    """Orchestrator for routing skill execution to appropriate executors.

    This class is the main entry point for skill execution. It:
    1. Loads skills via SkillLoader
    2. Determines execution mode (autonomous vs simple)
    3. Handles forked context (sub-agent spawning)
    4. Routes to appropriate executor
    5. Manages skill context activation/deactivation

    Attributes:
        skill_loader: Loader for discovering and loading skills
        tool_registry: Registry of available tools
        tool_executor: Executor for running tools
        default_config: Default configuration for autonomous execution
    """

    def __init__(
        self,
        skill_loader: SkillLoader,
        tool_registry: ToolRegistry,
        tool_executor: ToolExecutor,
        default_config: Optional[AutonomousConfig] = None,
    ) -> None:
        """Initialize skill orchestrator.

        Args:
            skill_loader: Loader for discovering and loading skills
            tool_registry: Registry of available tools
            tool_executor: Executor for running tools
            default_config: Optional default configuration for autonomous execution
        """
        self._skill_loader = skill_loader
        self._tool_registry = tool_registry
        self._tool_executor = tool_executor
        self._default_config = default_config or AutonomousConfig()

    async def execute(
        self,
        skill_name: str,
        user_request: str,
        task_id: str = "default",
        session_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        execution_mode_override: Optional[ExecutionMode] = None,
        context: Optional[ExecutionContext] = None,
    ) -> AsyncIterator[TaskEvent]:
        """Execute a skill by name.

        Main entry point for skill execution. Routes to appropriate executor
        based on execution mode and context configuration.

        Args:
            skill_name: Name of the skill to execute
            user_request: User's request/task description
            task_id: Unique task identifier (default: "default")
            session_id: Optional session identifier for this execution
            tenant_id: Optional tenant identifier for multi-tenancy
            execution_mode_override: Optional override for execution mode
            context: Optional execution context for depth tracking

        Yields:
            TaskEvent instances for progress updates

        Raises:
            SkillNotFoundError: If skill is not found in the skill loader

        Example:
            >>> orchestrator = SkillOrchestrator(loader, registry, executor)
            >>> async for event in orchestrator.execute("data-processor", "Process file.csv"):
            ...     if isinstance(event, TaskMessageEvent):
            ...         print(f"Progress: {event.message_parts[0].text}")
        """
        # Default values
        session_id = session_id or f"session-{task_id}"
        context = context or ExecutionContext()

        # Step 1: Load skill via SkillLoader
        logger.info(f"Loading skill '{skill_name}' for task '{task_id}'")
        skill = self._skill_loader.load_skill(skill_name)

        # Step 2: Determine execution mode
        execution_mode = self._determine_execution_mode(skill, execution_mode_override)
        logger.info(
            f"Executing skill '{skill_name}' in {execution_mode.value} mode "
            f"(depth: {context.depth})"
        )

        # Step 3: Handle forked context (sub-agent spawning)
        if skill.metadata.context == ContextMode.FORK:
            async for event in self._execute_forked(
                skill=skill,
                user_request=user_request,
                task_id=task_id,
                session_id=session_id,
                tenant_id=tenant_id,
                context=context,
                execution_mode=execution_mode,
            ):
                yield event
            return

        # Step 4: Execute using AutonomousSkillExecutor (all skills use autonomous mode)
        async for event in self._execute_autonomous(
            skill=skill,
            user_request=user_request,
            task_id=task_id,
            session_id=session_id,
            tenant_id=tenant_id,
            context=context,
        ):
            yield event

    def _determine_execution_mode(
        self,
        skill: Skill,
        override: Optional[ExecutionMode],
    ) -> ExecutionMode:
        """Determine execution mode for a skill.

        Note: All skills now use AUTONOMOUS mode. Legacy "simple" mode has been deprecated.

        Args:
            skill: Skill to execute
            override: Optional execution mode override (deprecated, always returns AUTONOMOUS)

        Returns:
            ExecutionMode.AUTONOMOUS (always)
        """
        # Log deprecation warning if override or non-autonomous mode is specified
        if override and override != ExecutionMode.AUTONOMOUS:
            logger.warning(
                f"Execution mode override '{override}' is deprecated. "
                f"All skills now use AUTONOMOUS mode."
            )

        mode = skill.metadata.execution_mode or "autonomous"
        if mode.lower() != "autonomous":
            logger.warning(
                f"Skill '{skill.metadata.name}' specifies execution_mode='{mode}'. "
                f"Simple mode is deprecated. Using AUTONOMOUS mode."
            )

        return ExecutionMode.AUTONOMOUS

    async def _execute_autonomous(
        self,
        skill: Skill,
        user_request: str,
        task_id: str,
        session_id: str,
        tenant_id: Optional[str],
        context: ExecutionContext,
        config: Optional[AutonomousConfig] = None,
    ) -> AsyncIterator[TaskEvent]:
        """Execute skill using AutonomousSkillExecutor.

        Builds configuration from skill metadata and platform defaults,
        activates skill context, and executes with ReAct loop.

        Args:
            skill: Skill to execute
            user_request: User's request/task description
            task_id: Task identifier
            session_id: Session identifier
            tenant_id: Optional tenant identifier
            context: Execution context for depth tracking
            config: Optional pre-built configuration (for forked execution)

        Yields:
            TaskEvent instances from AutonomousSkillExecutor
        """
        # Build configuration from skill metadata + platform defaults if not provided
        if config is None:
            config = self._build_config(skill)

        # Create autonomous executor
        executor = AutonomousSkillExecutor(
            skill=skill,
            tool_registry=self._tool_registry,
            tool_executor=self._tool_executor,
            config=config,
            context=context,
        )

        # Activate skill context in tool executor
        self._tool_executor.activate_skill(skill)

        try:
            # Execute with streaming events
            async for event in executor.execute(
                user_request=user_request,
                task_id=task_id,
                session_id=session_id,
                tenant_id=tenant_id,
            ):
                yield event
        finally:
            # Always deactivate skill context
            self._tool_executor.deactivate_skill(skill.metadata.name)

    async def _execute_forked(
        self,
        skill: Skill,
        user_request: str,
        task_id: str,
        session_id: str,
        tenant_id: Optional[str],
        context: ExecutionContext,
        execution_mode: ExecutionMode,
    ) -> AsyncIterator[TaskEvent]:
        """Execute skill in forked (sub-agent) context.

        Spawns a sub-agent with its own execution context and reduced budget.

        Args:
            skill: Skill to execute
            user_request: User's request/task description
            task_id: Task identifier
            session_id: Session identifier
            tenant_id: Optional tenant identifier
            context: Current execution context
            execution_mode: Execution mode for the sub-agent

        Yields:
            TaskEvent instances for sub-agent execution
        """
        from datetime import datetime

        # Step 1: Check depth limit
        if not context.can_spawn_sub_agent():
            error_msg = (
                f"Cannot spawn sub-agent: maximum depth ({context.max_depth}) reached. "
                f"Current depth: {context.depth}"
            )
            logger.warning(error_msg)

            yield TaskMessageEvent(
                task_id=task_id,
                timestamp=datetime.utcnow(),
                message_parts=[TextPart(text=error_msg)],
            )
            yield TaskDoneEvent(
                task_id=task_id,
                timestamp=datetime.utcnow(),
                final_state=TaskState.FAILED,
            )
            return

        # Step 2: Create child context
        child_context = context.create_child_context(
            task_id=task_id,
            skill_name=skill.metadata.name,
        )

        logger.info(
            f"Spawning sub-agent for skill '{skill.metadata.name}' "
            f"(depth: {child_context.depth}, parent: {task_id})"
        )

        # Step 3: Build sub-agent config with reduced budget
        child_config = self._build_config(skill)
        if execution_mode == ExecutionMode.AUTONOMOUS:
            # Reduce iteration budget for sub-agents
            base_iterations = child_config.max_iterations
            reduced_iterations = context.get_iteration_budget_for_child(base_iterations)
            child_config.max_iterations = reduced_iterations

            logger.debug(
                f"Sub-agent iteration budget: {reduced_iterations} "
                f"(reduced from {base_iterations})"
            )

        # Step 4: Execute with child context
        # Use same routing logic but with child context and reduced config
        if execution_mode == ExecutionMode.AUTONOMOUS:
            async for event in self._execute_autonomous(
                skill=skill,
                user_request=user_request,
                task_id=task_id,
                session_id=session_id,
                tenant_id=tenant_id,
                context=child_context,
                config=child_config,
            ):
                yield event
        else:
            async for event in self._execute_simple(
                skill=skill,
                user_request=user_request,
                task_id=task_id,
            ):
                yield event

    def _build_config(self, skill: Skill) -> AutonomousConfig:
        """Build autonomous config from skill metadata and platform defaults.

        Merges skill-specific configuration with platform defaults, with
        skill metadata taking precedence.

        Args:
            skill: Skill with metadata configuration

        Returns:
            Merged AutonomousConfig
        """
        # Start with platform defaults
        config = AutonomousConfig(
            max_iterations=self._default_config.max_iterations,
            max_retries_per_tool=self._default_config.max_retries_per_tool,
            timeout_per_iteration_ms=self._default_config.timeout_per_iteration_ms,
            early_termination=self._default_config.early_termination,
            model=self._default_config.model,
            temperature=self._default_config.temperature,
            enable_error_recovery=self._default_config.enable_error_recovery,
        )

        # Override with skill metadata (if present)
        if skill.metadata.max_iterations is not None:
            config.max_iterations = skill.metadata.max_iterations

        if skill.metadata.max_retries_per_tool is not None:
            config.max_retries_per_tool = skill.metadata.max_retries_per_tool

        if skill.metadata.timeout_per_iteration is not None:
            # Parse timeout string (e.g., "30s" -> 30000ms)
            timeout_str = skill.metadata.timeout_per_iteration
            timeout_ms = self._parse_timeout(timeout_str)
            if timeout_ms:
                config.timeout_per_iteration_ms = timeout_ms

        if skill.metadata.early_termination is not None:
            config.early_termination = skill.metadata.early_termination

        if skill.metadata.model is not None:
            config.model = skill.metadata.model

        return config

    def _parse_timeout(self, timeout_str: str) -> Optional[int]:
        """Parse timeout string to milliseconds.

        Args:
            timeout_str: Timeout string (e.g., "30s", "5m", "30000ms")

        Returns:
            Timeout in milliseconds, or None if parsing fails
        """
        timeout_str = timeout_str.strip().lower()

        try:
            # Parse milliseconds first (e.g., "30000ms")
            if timeout_str.endswith("ms"):
                return int(timeout_str[:-2])

            # Parse seconds (e.g., "30s")
            if timeout_str.endswith("s"):
                seconds = int(timeout_str[:-1])
                return seconds * 1000

            # Parse minutes (e.g., "5m")
            if timeout_str.endswith("m"):
                minutes = int(timeout_str[:-1])
                return minutes * 60 * 1000

            # Default: assume seconds
            return int(timeout_str) * 1000

        except (ValueError, IndexError):
            logger.warning(f"Invalid timeout format: {timeout_str}")
            return None
