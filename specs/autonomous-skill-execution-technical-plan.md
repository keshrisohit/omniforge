# Technical Implementation Plan: Autonomous Skill Execution

**Version:** 1.0
**Date:** 2026-01-26
**Status:** Draft
**Author:** Technical Architecture Team

---

## Executive Summary

This technical plan details the implementation of autonomous skill execution in OmniForge, transforming skills from single-pass execution into intelligent agents that iteratively work toward task completion using the ReAct (Reason-Act-Observe) pattern. The implementation integrates deeply with existing infrastructure including `ReasoningEngine`, `ToolExecutor`, `VisibilityController`, and the `TaskEvent` streaming system.

**Key Architectural Decisions:**
- Introduce `AutonomousSkillExecutor` as the primary execution engine, replacing the current `ExecutableSkill` for autonomous mode
- Implement a modular preprocessing pipeline: `ContextLoader` -> `DynamicInjector` -> `StringSubstitutor` -> Execution
- Reuse existing `ReasoningEngine` for all tool calls and chain management
- Emit `TaskEvent` instances for streaming (no new event types)
- Support backward compatibility through execution mode routing

**Technology Stack:**
- Python 3.9+ with async/await patterns
- Pydantic for data validation and configuration models
- Existing OmniForge tools: `ToolRegistry`, `ToolExecutor`, `ReasoningChain`

---

## 1. Requirements Analysis

### 1.1 Functional Requirements (from Product Spec)

| ID | Requirement | Priority | Complexity |
|----|-------------|----------|------------|
| FR-1 | Autonomous ReAct Loop (15 iterations) | P0 | Large |
| FR-2 | Error Recovery & Retry Logic (80%+ recovery) | P0 | Large |
| FR-3 | Progressive Context Loading (on-demand file loading) | P0 | Medium |
| FR-4 | User-Facing Progressive Disclosure (FULL/SUMMARY/HIDDEN) | P0 | Medium |
| FR-5 | Sub-Agent Execution (Forked Context) | P1 | Medium |
| FR-6 | Backward Compatibility (existing skills work unchanged) | P0 | Small |
| FR-7 | Streaming Events (real-time progress) | P1 | Small |
| FR-8 | Configuration & Tuning (per-skill settings) | P2 | Small |
| FR-9 | Script Execution Support (Python/JS/Shell) | P0 | Medium |
| FR-10 | Dynamic Context Injection (`` !`command` ``) | P0 | Medium |
| FR-11 | String Substitutions ($ARGUMENTS, ${SKILL_DIR}) | P1 | Small |
| FR-12 | Model Selection per Skill | P1 | Small |

### 1.2 Non-Functional Requirements

| Category | Requirement | Target |
|----------|-------------|--------|
| Performance | Iteration overhead | <500ms per iteration |
| Performance | Total execution time | <10s for simple tasks |
| Reliability | Error recovery rate | 80%+ for common errors |
| Scalability | Concurrent skill executions | 100+ per worker |
| Security | Script execution | Sandboxed, resource-limited |
| Observability | Metrics and tracing | Full trace for debugging |

### 1.3 Integration Constraints

**MUST use existing infrastructure:**
1. `ReasoningEngine` - For tool calls, chain management, and LLM interactions
2. `ToolExecutor` - For all tool execution with retry logic
3. `VisibilityController` - For progressive disclosure filtering
4. `TaskEvent` system - For streaming updates
5. `SkillLoader` - For loading SKILL.md files
6. `ReActParser` - For parsing LLM responses in ReAct format

---

## 2. System Architecture

### 2.1 High-Level Architecture Diagram

```
+-----------------------------------------------------------------------+
|                        Skill Execution Request                         |
+-----------------------------------------------------------------------+
                                    |
                                    v
+-----------------------------------------------------------------------+
|                         SkillOrchestrator                              |
|  - Routes to appropriate executor based on execution_mode              |
|  - Manages skill lifecycle                                             |
+-----------------------------------------------------------------------+
                    |                               |
        (execution_mode: autonomous)    (execution_mode: simple)
                    |                               |
                    v                               v
+-------------------------------+      +---------------------------+
|   AutonomousSkillExecutor     |      |   ExecutableSkill         |
|   (NEW - Primary Component)   |      |   (Existing - Legacy)     |
+-------------------------------+      +---------------------------+
            |
            v
+-----------------------------------------------------------------------+
|                    Preprocessing Pipeline                              |
|  +----------------+   +------------------+   +--------------------+    |
|  | ContextLoader  |-->| DynamicInjector  |-->| StringSubstitutor  |   |
|  | (FR-3)         |   | (FR-10)          |   | (FR-11)            |   |
|  +----------------+   +------------------+   +--------------------+    |
+-----------------------------------------------------------------------+
            |
            v
+-----------------------------------------------------------------------+
|                     ReAct Execution Loop (FR-1)                        |
|  +-------------+    +-------------+    +---------------+               |
|  | Think       |--->| Act         |--->| Observe       |--+            |
|  | (LLM call)  |    | (Tool exec) |    | (Check result)|  |            |
|  +-------------+    +-------------+    +---------------+  |            |
|        ^                                      |           |            |
|        +--------------------------------------+           |            |
|                 (iteration < max_iterations)             |            |
|                                                          |            |
|        +----------------------------------<---------------+            |
|        |  (is_final OR max_iterations reached)                         |
|        v                                                               |
|  +-------------------+                                                 |
|  | Return Result     |                                                 |
|  +-------------------+                                                 |
+-----------------------------------------------------------------------+
            |
            v (events)
+-----------------------------------------------------------------------+
|                        Event Emitter (FR-7)                            |
|  - TaskStatusEvent (state changes)                                     |
|  - TaskMessageEvent (progress updates, visibility-filtered)            |
|  - TaskErrorEvent (error reporting)                                    |
|  - TaskDoneEvent (completion)                                          |
+-----------------------------------------------------------------------+
            |
            v
+-----------------------------------------------------------------------+
|                    Existing Infrastructure                             |
|  +------------------+  +---------------+  +---------------------+      |
|  | ReasoningEngine  |  | ToolExecutor  |  | VisibilityController|     |
|  +------------------+  +---------------+  +---------------------+      |
+-----------------------------------------------------------------------+
```

### 2.2 Component Interaction Flow

```
User Request
     |
     v
+------------------+
| SkillOrchestrator|
+------------------+
     |
     | 1. Load skill via SkillLoader
     v
+------------------+
| SkillLoader      |---> Skill (metadata + content)
+------------------+
     |
     | 2. Check execution_mode
     v
+-------------------------------------+
| execution_mode == "autonomous" ?    |
+-------------------------------------+
     |yes                      |no
     v                         v
+------------------------+   +-------------------+
| AutonomousSkillExecutor|   | ExecutableSkill   |
+------------------------+   | (legacy path)     |
     |                       +-------------------+
     | 3. Preprocess
     v
+------------------------+
| ContextLoader          |
| - Extract file refs    |
| - Build available list |
+------------------------+
     |
     v
+------------------------+
| DynamicInjector        |
| - Parse !`command`     |
| - Execute commands     |
| - Replace placeholders |
+------------------------+
     |
     v
+------------------------+
| StringSubstitutor      |
| - Replace $ARGUMENTS   |
| - Replace ${SKILL_DIR} |
| - Replace ${SESSION_ID}|
+------------------------+
     |
     | 4. Build System Prompt
     v
+------------------------+
| System Prompt Builder  |
| - Skill instructions   |
| - Available tools      |
| - Available files      |
| - ReAct format rules   |
+------------------------+
     |
     | 5. Execute ReAct Loop
     v
+------------------------+
| ReAct Loop             |
| for i in max_iterations|
|   - call_llm()         |
|   - parse_response()   |
|   - execute_tool()     |
|   - emit_events()      |
|   - check_complete()   |
+------------------------+
     |
     | 6. Return Result
     v
+------------------------+
| ExecutionResult        |
| - success: bool        |
| - result: str          |
| - iterations: int      |
| - metrics: dict        |
+------------------------+
```

### 2.3 Class Hierarchy

```
                    +------------------+
                    |   BaseExecutor   |  (Protocol/ABC)
                    +------------------+
                           ^
                           |
          +----------------+----------------+
          |                                 |
+------------------------+      +---------------------------+
| AutonomousSkillExecutor|      | ExecutableSkill           |
| (NEW)                  |      | (Existing - legacy mode)  |
+------------------------+      +---------------------------+
          |
          | uses
          v
+------------------------+
| ExecutionContext       |  (runtime state)
+------------------------+
          |
          | composed of
          v
+------------------------+     +------------------------+
| ContextLoader          |     | DynamicInjector        |
+------------------------+     +------------------------+
          |                              |
          | uses                         | uses
          v                              v
+------------------------+     +------------------------+
| FileReferenceParser    |     | CommandExecutor        |
+------------------------+     +------------------------+

+------------------------+     +------------------------+
| StringSubstitutor      |     | IterationTracker       |
+------------------------+     +------------------------+
```

---

## 3. Component Specifications

### 3.1 AutonomousSkillExecutor (Core Component)

**Location:** `src/omniforge/skills/autonomous_executor.py`

**Purpose:** Primary execution engine for autonomous skill execution using ReAct pattern.

```python
"""Autonomous skill executor with ReAct pattern.

This module provides the AutonomousSkillExecutor class that executes skills
autonomously using the ReAct (Reason-Act-Observe) pattern with iterative
refinement, error recovery, and progressive context loading.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, AsyncIterator, Optional
from uuid import uuid4

from omniforge.agents.cot.chain import ReasoningChain, ChainStatus
from omniforge.agents.cot.engine import ReasoningEngine, ToolCallResult
from omniforge.agents.cot.parser import ReActParser, ParsedResponse
from omniforge.agents.events import (
    TaskEvent,
    TaskStatusEvent,
    TaskMessageEvent,
    TaskDoneEvent,
    TaskErrorEvent,
)
from omniforge.skills.models import Skill, ContextMode
from omniforge.skills.context import SkillContext
from omniforge.tasks.models import TaskState
from omniforge.tools.executor import ToolExecutor
from omniforge.tools.registry import ToolRegistry


@dataclass
class AutonomousConfig:
    """Configuration for autonomous skill execution.

    Attributes:
        max_iterations: Maximum ReAct loop iterations (default: 15)
        max_retries_per_tool: Max retries per tool/approach (default: 3)
        timeout_per_iteration_ms: Timeout per iteration in ms (default: 30000)
        early_termination: Allow early termination on confidence (default: True)
        model: LLM model for reasoning (default: None, uses skill/platform default)
        temperature: LLM temperature (default: 0.0)
        enable_error_recovery: Enable automatic error recovery (default: True)
    """
    max_iterations: int = 15
    max_retries_per_tool: int = 3
    timeout_per_iteration_ms: int = 30000
    early_termination: bool = True
    model: Optional[str] = None
    temperature: float = 0.0
    enable_error_recovery: bool = True


@dataclass
class ExecutionState:
    """Tracks execution state across iterations.

    Attributes:
        iteration: Current iteration number
        observations: List of observations from tool calls
        failed_approaches: Set of failed tool/argument combinations
        loaded_files: Set of already-loaded supporting files
        partial_results: Accumulated partial results
        error_count: Number of errors encountered
        start_time: Execution start timestamp
    """
    iteration: int = 0
    observations: list[dict[str, Any]] = field(default_factory=list)
    failed_approaches: set[str] = field(default_factory=set)
    loaded_files: set[str] = field(default_factory=set)
    partial_results: list[str] = field(default_factory=list)
    error_count: int = 0
    start_time: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ExecutionResult:
    """Result of autonomous skill execution.

    Attributes:
        success: Whether execution completed successfully
        result: Final result text
        iterations_used: Number of iterations executed
        chain_id: Reasoning chain ID for debugging
        metrics: Execution metrics (tokens, cost, duration)
        partial_results: List of partial results if incomplete
        error: Error message if failed
    """
    success: bool
    result: str
    iterations_used: int
    chain_id: str
    metrics: dict[str, Any]
    partial_results: list[str] = field(default_factory=list)
    error: Optional[str] = None


class AutonomousSkillExecutor:
    """Executes skills autonomously using ReAct pattern.

    The executor:
    1. Preprocesses skill content (context injection, variable substitution)
    2. Builds system prompt with available tools and files
    3. Runs ReAct loop: Think -> Act -> Observe -> repeat
    4. Handles errors with automatic recovery and alternative approaches
    5. Emits streaming events for real-time progress updates

    Example:
        >>> executor = AutonomousSkillExecutor(
        ...     skill=skill,
        ...     tool_registry=registry,
        ...     tool_executor=tool_executor,
        ... )
        >>> async for event in executor.execute("Process data.csv"):
        ...     print(event)
    """

    def __init__(
        self,
        skill: Skill,
        tool_registry: ToolRegistry,
        tool_executor: ToolExecutor,
        config: Optional[AutonomousConfig] = None,
        context_loader: Optional["ContextLoader"] = None,
        dynamic_injector: Optional["DynamicInjector"] = None,
        string_substitutor: Optional["StringSubstitutor"] = None,
    ) -> None:
        """Initialize autonomous skill executor.

        Args:
            skill: The skill to execute
            tool_registry: Registry of available tools
            tool_executor: Executor for tool calls
            config: Optional execution configuration
            context_loader: Optional custom context loader
            dynamic_injector: Optional custom dynamic injector
            string_substitutor: Optional custom string substitutor
        """
        self._skill = skill
        self._tool_registry = tool_registry
        self._tool_executor = tool_executor
        self._config = config or self._build_config_from_skill(skill)
        self._parser = ReActParser()

        # Initialize preprocessing components
        self._context_loader = context_loader or ContextLoader(skill)
        self._dynamic_injector = dynamic_injector or DynamicInjector(
            tool_executor=tool_executor,
            allowed_tools=skill.metadata.allowed_tools,
        )
        self._string_substitutor = string_substitutor or StringSubstitutor()

    async def execute(
        self,
        user_request: str,
        task_id: str = "default",
        session_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> AsyncIterator[TaskEvent]:
        """Execute the skill autonomously and stream events.

        Args:
            user_request: User's request/task description
            task_id: Task identifier for tracking
            session_id: Optional session ID for variable substitution
            tenant_id: Optional tenant ID for multi-tenancy

        Yields:
            TaskEvent instances for streaming progress
        """
        session_id = session_id or str(uuid4())

        # Initialize execution state
        state = ExecutionState()
        chain = self._create_chain(task_id, tenant_id)
        engine = self._create_engine(chain, task_id, tenant_id)

        # Emit start event
        yield TaskStatusEvent(
            task_id=task_id,
            timestamp=datetime.utcnow(),
            state=TaskState.RUNNING,
            message=f"Starting skill: {self._skill.metadata.name}",
        )

        try:
            # Step 1: Preprocess skill content
            processed_content = await self._preprocess_content(
                user_request=user_request,
                session_id=session_id,
                task_id=task_id,
            )

            # Step 2: Build system prompt
            system_prompt = self._build_system_prompt(
                processed_content=processed_content,
                engine=engine,
            )

            # Step 3: Initialize conversation
            conversation = self._initialize_conversation(user_request)

            # Step 4: Execute ReAct loop
            final_result: Optional[str] = None

            for iteration in range(self._config.max_iterations):
                state.iteration = iteration + 1

                # Emit iteration start
                yield TaskMessageEvent(
                    task_id=task_id,
                    timestamp=datetime.utcnow(),
                    message_parts=[],
                    is_partial=True,
                )

                # Think: Get LLM decision
                llm_result = await engine.call_llm(
                    messages=conversation,
                    system=system_prompt,
                    model=self._config.model or self._skill.metadata.model,
                    temperature=self._config.temperature,
                )

                if not llm_result.success:
                    yield from self._handle_llm_error(
                        task_id=task_id,
                        error=llm_result.error or "LLM call failed",
                        state=state,
                    )
                    continue

                # Parse response
                response_text = llm_result.value.get("content", "") if llm_result.value else ""
                parsed = self._parser.parse(response_text)

                # Check for final answer
                if parsed.is_final and parsed.final_answer:
                    final_result = parsed.final_answer
                    engine.add_synthesis(
                        conclusion=f"Task completed: {final_result}",
                        sources=[llm_result.step_id],
                    )
                    break

                # Act: Execute tool if specified
                if parsed.action:
                    async for event in self._execute_action(
                        engine=engine,
                        parsed=parsed,
                        conversation=conversation,
                        state=state,
                        task_id=task_id,
                    ):
                        yield event
                else:
                    # No action and not final - add to conversation and continue
                    conversation.append({"role": "assistant", "content": response_text})
                    conversation.append({
                        "role": "user",
                        "content": "Please continue with the task. What tool should you use next?",
                    })

            # Step 5: Handle completion
            if final_result:
                yield TaskDoneEvent(
                    task_id=task_id,
                    timestamp=datetime.utcnow(),
                    final_state=TaskState.COMPLETED,
                )
            else:
                # Max iterations reached without final answer
                partial_result = self._synthesize_partial_results(state)
                yield TaskErrorEvent(
                    task_id=task_id,
                    timestamp=datetime.utcnow(),
                    error_code="MAX_ITERATIONS_REACHED",
                    error_message=f"Reached maximum iterations ({self._config.max_iterations})",
                    details={"partial_result": partial_result},
                )

        except Exception as e:
            yield TaskErrorEvent(
                task_id=task_id,
                timestamp=datetime.utcnow(),
                error_code="EXECUTION_ERROR",
                error_message=str(e),
            )
            yield TaskDoneEvent(
                task_id=task_id,
                timestamp=datetime.utcnow(),
                final_state=TaskState.FAILED,
            )

    async def execute_sync(
        self,
        user_request: str,
        task_id: str = "default",
        session_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> ExecutionResult:
        """Execute synchronously and return result (non-streaming).

        Args:
            user_request: User's request/task description
            task_id: Task identifier
            session_id: Optional session ID
            tenant_id: Optional tenant ID

        Returns:
            ExecutionResult with final outcome
        """
        final_result = ""
        iterations_used = 0
        error: Optional[str] = None

        async for event in self.execute(user_request, task_id, session_id, tenant_id):
            if isinstance(event, TaskDoneEvent):
                if event.final_state == TaskState.COMPLETED:
                    return ExecutionResult(
                        success=True,
                        result=final_result,
                        iterations_used=iterations_used,
                        chain_id="",  # TODO: Extract from chain
                        metrics={},
                    )
            elif isinstance(event, TaskErrorEvent):
                error = event.error_message

        return ExecutionResult(
            success=False,
            result=final_result,
            iterations_used=iterations_used,
            chain_id="",
            metrics={},
            error=error,
        )

    # ... (private helper methods documented below)
```

### 3.2 ContextLoader (Progressive Context Loading - FR-3)

**Location:** `src/omniforge/skills/context_loader.py`

**Purpose:** Parse SKILL.md for supporting file references and manage on-demand loading.

```python
"""Context loader for progressive skill content loading.

This module provides the ContextLoader class that extracts file references
from SKILL.md content and tracks which files have been loaded during execution.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class FileReference:
    """Reference to a supporting file in the skill directory.

    Attributes:
        filename: Name of the file (e.g., "reference.md")
        path: Absolute path to the file
        description: Description extracted from SKILL.md
        estimated_lines: Estimated line count (if mentioned)
        loaded: Whether file has been loaded
    """
    filename: str
    path: Path
    description: str
    estimated_lines: Optional[int] = None
    loaded: bool = False


@dataclass
class LoadedContext:
    """Context loaded from skill content and references.

    Attributes:
        skill_content: Processed SKILL.md content
        available_files: Map of filename -> FileReference
        skill_dir: Absolute path to skill directory
        line_count: Number of lines in SKILL.md
    """
    skill_content: str
    available_files: dict[str, FileReference]
    skill_dir: Path
    line_count: int


class ContextLoader:
    """Loads and manages skill context with progressive loading.

    Extracts references to supporting files from SKILL.md and provides
    methods for on-demand loading during execution.

    Patterns recognized:
    - "See reference.md for details"
    - "Read examples.md for usage"
    - "Check templates/report.md"
    - "(1,200 lines)" - line count hints

    Example:
        >>> loader = ContextLoader(skill)
        >>> context = loader.load_initial_context()
        >>> print(context.available_files.keys())
        dict_keys(['reference.md', 'examples.md', 'templates/report.md'])
    """

    # Patterns for extracting file references
    FILE_REFERENCE_PATTERNS = [
        # "See reference.md for details (1,200 lines)"
        re.compile(
            r"(?:see|read|check|refer to|consult)\s+[`'\"]?([a-zA-Z0-9_\-/]+\.(?:md|txt|json|yaml))[`'\"]?"
            r"(?:\s+for\s+([^(.\n]+))?"
            r"(?:\s*\((\d+(?:,\d+)?)\s*lines?\))?"
            , re.IGNORECASE
        ),
        # "- reference.md: Description"
        re.compile(
            r"^\s*[-*]\s*[`'\"]?([a-zA-Z0-9_\-/]+\.(?:md|txt|json|yaml))[`'\"]?"
            r"\s*:\s*(.+)$"
            , re.MULTILINE
        ),
        # "**reference.md**: Description"
        re.compile(
            r"\*\*([a-zA-Z0-9_\-/]+\.(?:md|txt|json|yaml))\*\*"
            r"\s*:\s*([^(\n]+)"
            r"(?:\s*\((\d+(?:,\d+)?)\s*lines?\))?"
            , re.IGNORECASE
        ),
    ]

    def __init__(self, skill: "Skill") -> None:
        """Initialize context loader for a skill.

        Args:
            skill: The skill to load context for
        """
        self._skill = skill
        self._loaded_files: set[str] = set()

    def load_initial_context(self) -> LoadedContext:
        """Load initial context from SKILL.md only.

        Returns:
            LoadedContext with skill content and available file references
        """
        # Extract file references from content
        available_files = self._extract_file_references(self._skill.content)

        # Validate files exist
        skill_dir = self._skill.base_path
        valid_files = {}
        for filename, ref in available_files.items():
            file_path = skill_dir / filename
            if file_path.exists():
                ref.path = file_path.resolve()
                valid_files[filename] = ref

        return LoadedContext(
            skill_content=self._skill.content,
            available_files=valid_files,
            skill_dir=skill_dir,
            line_count=self._skill.content.count('\n') + 1,
        )

    def mark_file_loaded(self, filename: str) -> None:
        """Mark a file as loaded (for tracking).

        Args:
            filename: Name of the file that was loaded
        """
        self._loaded_files.add(filename)

    def get_loaded_files(self) -> set[str]:
        """Get set of files that have been loaded.

        Returns:
            Set of loaded filenames
        """
        return self._loaded_files.copy()

    def _extract_file_references(self, content: str) -> dict[str, FileReference]:
        """Extract file references from skill content.

        Args:
            content: SKILL.md content

        Returns:
            Dictionary mapping filename to FileReference
        """
        references: dict[str, FileReference] = {}

        for pattern in self.FILE_REFERENCE_PATTERNS:
            for match in pattern.finditer(content):
                groups = match.groups()
                filename = groups[0]
                description = groups[1].strip() if len(groups) > 1 and groups[1] else ""

                # Parse line count if present
                lines = None
                if len(groups) > 2 and groups[2]:
                    lines = int(groups[2].replace(",", ""))

                if filename not in references:
                    references[filename] = FileReference(
                        filename=filename,
                        path=Path(filename),  # Will be resolved later
                        description=description,
                        estimated_lines=lines,
                    )

        return references

    def build_available_files_prompt(self, context: LoadedContext) -> str:
        """Build prompt section describing available files.

        Args:
            context: Loaded context with file references

        Returns:
            Formatted string for system prompt
        """
        if not context.available_files:
            return ""

        lines = ["AVAILABLE SUPPORTING FILES (load on-demand with 'read' tool):"]
        for filename, ref in sorted(context.available_files.items()):
            line = f"- {filename}"
            if ref.description:
                line += f": {ref.description}"
            if ref.estimated_lines:
                line += f" ({ref.estimated_lines:,} lines)"
            lines.append(line)

        lines.append("")
        lines.append(f"Skill directory: {context.skill_dir}")

        return "\n".join(lines)
```

### 3.3 DynamicInjector (Dynamic Context Injection - FR-10)

**Location:** `src/omniforge/skills/dynamic_injector.py`

**Purpose:** Parse and execute `` !`command` `` syntax before first iteration.

```python
"""Dynamic context injector for skill preprocessing.

This module provides the DynamicInjector class that parses and executes
command injection syntax (!`command`) in skill content before execution.
"""

import asyncio
import re
import subprocess
from dataclasses import dataclass
from typing import Any, Optional

from omniforge.tools.executor import ToolExecutor
from omniforge.tools.base import ToolCallContext


@dataclass
class InjectionResult:
    """Result of a command injection.

    Attributes:
        command: Original command
        output: Command output (or error message)
        success: Whether command executed successfully
        duration_ms: Execution duration in milliseconds
    """
    command: str
    output: str
    success: bool
    duration_ms: int


@dataclass
class InjectedContent:
    """Skill content with injections processed.

    Attributes:
        content: Processed content with placeholders replaced
        injections: List of injection results
        total_duration_ms: Total injection processing time
    """
    content: str
    injections: list[InjectionResult]
    total_duration_ms: int


class DynamicInjector:
    """Injects command output into skill content before execution.

    Parses !`command` syntax and replaces with command output:
    - Commands are validated against allowed_tools
    - Each command has a 5-second timeout
    - Output is limited to 10,000 characters
    - Failed commands show error message in content

    Example:
        >>> injector = DynamicInjector(tool_executor, allowed_tools=["Bash(gh:*)"])
        >>> result = await injector.process("PR Diff: !`gh pr diff`")
        >>> print(result.content)
        "PR Diff: [actual diff output]"
    """

    # Pattern: !`command`
    INJECTION_PATTERN = re.compile(r"!\`([^`]+)\`")

    DEFAULT_TIMEOUT_SECONDS = 5
    DEFAULT_MAX_OUTPUT_CHARS = 10_000

    def __init__(
        self,
        tool_executor: Optional[ToolExecutor] = None,
        allowed_tools: Optional[list[str]] = None,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        max_output_chars: int = DEFAULT_MAX_OUTPUT_CHARS,
    ) -> None:
        """Initialize dynamic injector.

        Args:
            tool_executor: Optional tool executor for command execution
            allowed_tools: Optional list of allowed tool patterns
            timeout_seconds: Timeout per command (default: 5)
            max_output_chars: Max output characters per command (default: 10000)
        """
        self._tool_executor = tool_executor
        self._allowed_tools = allowed_tools or []
        self._timeout_seconds = timeout_seconds
        self._max_output_chars = max_output_chars

    async def process(
        self,
        content: str,
        task_id: str = "injection",
        working_dir: Optional[str] = None,
    ) -> InjectedContent:
        """Process content and replace injection placeholders.

        Args:
            content: Skill content with !`command` placeholders
            task_id: Task ID for tracking
            working_dir: Working directory for command execution

        Returns:
            InjectedContent with processed content
        """
        injections: list[InjectionResult] = []
        total_duration = 0

        # Find all injection patterns
        matches = list(self.INJECTION_PATTERN.finditer(content))

        if not matches:
            return InjectedContent(
                content=content,
                injections=[],
                total_duration_ms=0,
            )

        # Process each injection (could be parallelized)
        replacements: dict[str, str] = {}

        for match in matches:
            full_match = match.group(0)
            command = match.group(1).strip()

            # Skip if already processed (duplicate commands)
            if full_match in replacements:
                continue

            # Validate command against allowed tools
            if not self._is_command_allowed(command):
                result = InjectionResult(
                    command=command,
                    output=f"[Command not allowed: {command}]",
                    success=False,
                    duration_ms=0,
                )
                injections.append(result)
                replacements[full_match] = result.output
                continue

            # Execute command
            result = await self._execute_command(command, working_dir)
            injections.append(result)
            total_duration += result.duration_ms

            # Truncate output if too long
            output = result.output
            if len(output) > self._max_output_chars:
                output = output[:self._max_output_chars] + f"\n... (truncated at {self._max_output_chars} chars)"

            replacements[full_match] = output

        # Replace all injections in content
        processed_content = content
        for placeholder, replacement in replacements.items():
            processed_content = processed_content.replace(placeholder, replacement)

        return InjectedContent(
            content=processed_content,
            injections=injections,
            total_duration_ms=total_duration,
        )

    async def _execute_command(
        self,
        command: str,
        working_dir: Optional[str] = None,
    ) -> InjectionResult:
        """Execute a single command with timeout.

        Args:
            command: Command to execute
            working_dir: Working directory

        Returns:
            InjectionResult with output or error
        """
        import time
        start_time = time.time()

        try:
            # Use asyncio subprocess for non-blocking execution
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_dir,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self._timeout_seconds,
                )

                duration_ms = int((time.time() - start_time) * 1000)

                if process.returncode == 0:
                    return InjectionResult(
                        command=command,
                        output=stdout.decode("utf-8", errors="replace"),
                        success=True,
                        duration_ms=duration_ms,
                    )
                else:
                    error_output = stderr.decode("utf-8", errors="replace") or stdout.decode("utf-8", errors="replace")
                    return InjectionResult(
                        command=command,
                        output=f"[Command failed: {error_output}]",
                        success=False,
                        duration_ms=duration_ms,
                    )

            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                duration_ms = int((time.time() - start_time) * 1000)
                return InjectionResult(
                    command=command,
                    output=f"[Command timed out after {self._timeout_seconds}s]",
                    success=False,
                    duration_ms=duration_ms,
                )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return InjectionResult(
                command=command,
                output=f"[Command execution error: {str(e)}]",
                success=False,
                duration_ms=duration_ms,
            )

    def _is_command_allowed(self, command: str) -> bool:
        """Check if command is allowed based on allowed_tools.

        SECURITY: This method provides defense against command injection attacks.
        It validates commands using a multi-layered approach:
        1. Deny shell operators (; && || | > < $( ` )
        2. Parse with shlex to prevent shell expansion
        3. Validate against allowed_tools whitelist
        4. Log all attempts for audit trail

        Args:
            command: Command to check

        Returns:
            True if allowed, False otherwise
        """
        import shlex
        import logging

        logger = logging.getLogger(__name__)

        # If no restrictions, allow all (use with caution!)
        if not self._allowed_tools:
            logger.warning(
                "Command injection with no allowed_tools restrictions. "
                "This is a security risk in multi-tenant environments."
            )
            return True

        # SECURITY: Disallow shell operators to prevent injection
        SHELL_OPERATORS = [';', '&&', '||', '|', '>', '<', '$(', '`', '\n']
        for operator in SHELL_OPERATORS:
            if operator in command:
                logger.security(
                    "Blocked command injection attempt with shell operator",
                    command=command,
                    operator=operator,
                    allowed_tools=self._allowed_tools,
                )
                return False

        # SECURITY: Parse with shlex to handle quotes properly
        try:
            command_parts = shlex.split(command)
        except ValueError as e:
            logger.security(
                "Blocked command injection attempt with invalid shell syntax",
                command=command,
                error=str(e),
            )
            return False

        if not command_parts:
            return False

        base_command = command_parts[0]

        # SECURITY: Validate against path traversal
        if '..' in base_command or base_command.startswith('/'):
            logger.security(
                "Blocked command injection attempt with path traversal",
                command=command,
                base_command=base_command,
            )
            return False

        for allowed in self._allowed_tools:
            # Handle Bash tool patterns
            if allowed.lower().startswith("bash"):
                # Extract pattern: Bash(pattern) or Bash
                match = re.match(r"bash\(([^)]+)\)", allowed, re.IGNORECASE)
                if match:
                    pattern = match.group(1)
                    # Pattern format: "gh:*" means commands starting with "gh"
                    if ":" in pattern:
                        allowed_prefix = pattern.split(":")[0]
                        if base_command == allowed_prefix or base_command.startswith(allowed_prefix):
                            return True
                    elif pattern == "*":
                        return True
                else:
                    # Plain "Bash" allows all bash commands
                    return True

            # Handle other tool patterns
            if allowed.lower() == base_command.lower():
                return True

        return False
```

### 3.4 StringSubstitutor (Variable Substitution - FR-11)

**Location:** `src/omniforge/skills/string_substitutor.py`

**Purpose:** Replace variables ($ARGUMENTS, ${SKILL_DIR}, etc.) before LLM execution.

```python
"""String substitutor for skill variable replacement.

This module provides the StringSubstitutor class that replaces variables
in skill content before sending to the LLM.
"""

import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class SubstitutionContext:
    """Context for variable substitution.

    Attributes:
        arguments: User-provided arguments
        session_id: Unique session identifier
        skill_dir: Absolute path to skill directory
        workspace: Current working directory
        user: Current user name
        date: Current date (YYYY-MM-DD)
        custom_vars: Additional custom variables
    """
    arguments: str = ""
    session_id: str = ""
    skill_dir: str = ""
    workspace: str = ""
    user: str = ""
    date: str = ""
    custom_vars: dict[str, str] = None

    def __post_init__(self) -> None:
        if self.custom_vars is None:
            self.custom_vars = {}


@dataclass
class SubstitutedContent:
    """Result of variable substitution.

    Attributes:
        content: Content with variables replaced
        substitutions_made: Count of substitutions
        undefined_vars: List of undefined variables found
    """
    content: str
    substitutions_made: int
    undefined_vars: list[str]


class StringSubstitutor:
    """Substitutes variables in skill content.

    Supported variables:
    - $ARGUMENTS: All arguments passed when invoking skill
    - ${CLAUDE_SESSION_ID}: Unique session identifier
    - ${SKILL_DIR}: Absolute path to skill directory
    - ${WORKSPACE}: Current working directory
    - ${USER}: Current user name
    - ${DATE}: Current date (YYYY-MM-DD)

    Example:
        >>> substitutor = StringSubstitutor()
        >>> context = SubstitutionContext(
        ...     arguments="data.csv --format json",
        ...     skill_dir="/home/user/.claude/skills/my-skill",
        ... )
        >>> result = substitutor.substitute("Process: $ARGUMENTS in ${SKILL_DIR}", context)
        >>> print(result.content)
        "Process: data.csv --format json in /home/user/.claude/skills/my-skill"
    """

    # Standard variables (order matters for replacement)
    STANDARD_VARIABLES = [
        ("${CLAUDE_SESSION_ID}", "session_id"),
        ("${SKILL_DIR}", "skill_dir"),
        ("${WORKSPACE}", "workspace"),
        ("${USER}", "user"),
        ("${DATE}", "date"),
        ("$ARGUMENTS", "arguments"),
    ]

    # Pattern for undefined variable detection
    VARIABLE_PATTERN = re.compile(r"\$\{?([A-Z][A-Z0-9_]*)\}?")

    def __init__(self) -> None:
        """Initialize string substitutor."""
        pass

    def substitute(
        self,
        content: str,
        context: SubstitutionContext,
        auto_append_arguments: bool = True,
    ) -> SubstitutedContent:
        """Substitute variables in content.

        Args:
            content: Content with variable placeholders
            context: Substitution context with values
            auto_append_arguments: If True and $ARGUMENTS not in content,
                                   append arguments at the end

        Returns:
            SubstitutedContent with processed content
        """
        substitutions = 0
        undefined_vars: list[str] = []

        # Replace standard variables
        for placeholder, attr in self.STANDARD_VARIABLES:
            value = getattr(context, attr, "")
            if placeholder in content:
                content = content.replace(placeholder, value)
                substitutions += 1

        # Replace custom variables
        if context.custom_vars:
            for var_name, value in context.custom_vars.items():
                for pattern in [f"${{{var_name}}}", f"${var_name}"]:
                    if pattern in content:
                        content = content.replace(pattern, value)
                        substitutions += 1

        # Check for undefined variables
        for match in self.VARIABLE_PATTERN.finditer(content):
            var_name = match.group(1)
            if not self._is_defined_variable(var_name, context):
                undefined_vars.append(var_name)

        # Auto-append arguments if not present
        if auto_append_arguments and "$ARGUMENTS" not in content and context.arguments:
            content += f"\n\nARGUMENTS: {context.arguments}"
            substitutions += 1

        return SubstitutedContent(
            content=content,
            substitutions_made=substitutions,
            undefined_vars=undefined_vars,
        )

    def build_context(
        self,
        arguments: str = "",
        session_id: Optional[str] = None,
        skill_dir: Optional[Path] = None,
        workspace: Optional[Path] = None,
        custom_vars: Optional[dict[str, str]] = None,
    ) -> SubstitutionContext:
        """Build substitution context with defaults.

        Args:
            arguments: User-provided arguments
            session_id: Session ID (generated if not provided)
            skill_dir: Skill directory path
            workspace: Workspace path (defaults to cwd)
            custom_vars: Additional custom variables

        Returns:
            SubstitutionContext with all values populated
        """
        from uuid import uuid4

        return SubstitutionContext(
            arguments=arguments,
            session_id=session_id or f"session-{datetime.now().strftime('%Y-%m-%d')}-{uuid4().hex[:8]}",
            skill_dir=str(skill_dir.resolve()) if skill_dir else "",
            workspace=str(workspace.resolve()) if workspace else os.getcwd(),
            user=os.environ.get("USER", os.environ.get("USERNAME", "unknown")),
            date=datetime.now().strftime("%Y-%m-%d"),
            custom_vars=custom_vars or {},
        )

    def _is_defined_variable(self, var_name: str, context: SubstitutionContext) -> bool:
        """Check if a variable is defined.

        Args:
            var_name: Variable name (without $ or {})
            context: Substitution context

        Returns:
            True if variable is defined
        """
        standard_vars = {
            "ARGUMENTS", "CLAUDE_SESSION_ID", "SKILL_DIR",
            "WORKSPACE", "USER", "DATE",
        }

        if var_name in standard_vars:
            return True

        if context.custom_vars and var_name in context.custom_vars:
            return True

        return False
```

### 3.5 SkillOrchestrator (Routing & Lifecycle Management - FR-6)

**Location:** `src/omniforge/skills/orchestrator.py`

**Purpose:** Route to appropriate executor and manage skill lifecycle.

```python
"""Skill orchestrator for routing and lifecycle management.

This module provides the SkillOrchestrator class that routes skill execution
to the appropriate executor based on execution_mode and manages the skill
lifecycle including activation, deactivation, and sub-agent spawning.
"""

from enum import Enum
from typing import AsyncIterator, Optional

from omniforge.agents.events import TaskEvent
from omniforge.skills.autonomous_executor import AutonomousSkillExecutor, AutonomousConfig
from omniforge.skills.executor import ExecutableSkill
from omniforge.skills.loader import SkillLoader
from omniforge.skills.models import Skill, ContextMode
from omniforge.tools.executor import ToolExecutor
from omniforge.tools.registry import ToolRegistry


class ExecutionMode(str, Enum):
    """Skill execution mode."""
    AUTONOMOUS = "autonomous"
    SIMPLE = "simple"


class SkillOrchestrator:
    """Orchestrates skill execution with mode-based routing.

    Routes skill execution to the appropriate executor:
    - execution_mode: autonomous -> AutonomousSkillExecutor
    - execution_mode: simple -> ExecutableSkill (legacy)

    Also manages:
    - Sub-agent spawning for forked context skills
    - Skill lifecycle (activation/deactivation)
    - Configuration merging (skill + platform defaults)

    Example:
        >>> orchestrator = SkillOrchestrator(
        ...     skill_loader=loader,
        ...     tool_registry=registry,
        ...     tool_executor=executor,
        ... )
        >>> async for event in orchestrator.execute("my-skill", "Process data"):
        ...     print(event)
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
            skill_loader: Loader for retrieving skills
            tool_registry: Registry of available tools
            tool_executor: Executor for tool calls
            default_config: Default autonomous configuration
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
    ) -> AsyncIterator[TaskEvent]:
        """Execute a skill by name.

        Args:
            skill_name: Name of the skill to execute
            user_request: User's request/task description
            task_id: Task identifier
            session_id: Optional session ID
            tenant_id: Optional tenant ID
            execution_mode_override: Optional mode override

        Yields:
            TaskEvent instances for streaming progress
        """
        # Load skill
        skill = self._skill_loader.load_skill(skill_name)

        # Determine execution mode
        mode = self._determine_execution_mode(skill, execution_mode_override)

        # Handle forked context (sub-agent)
        if skill.metadata.context == ContextMode.FORK:
            async for event in self._execute_forked(
                skill=skill,
                user_request=user_request,
                task_id=task_id,
                session_id=session_id,
                tenant_id=tenant_id,
            ):
                yield event
            return

        # Route to appropriate executor
        if mode == ExecutionMode.AUTONOMOUS:
            async for event in self._execute_autonomous(
                skill=skill,
                user_request=user_request,
                task_id=task_id,
                session_id=session_id,
                tenant_id=tenant_id,
            ):
                yield event
        else:
            async for event in self._execute_simple(
                skill=skill,
                user_request=user_request,
                task_id=task_id,
            ):
                yield event

    async def _execute_autonomous(
        self,
        skill: Skill,
        user_request: str,
        task_id: str,
        session_id: Optional[str],
        tenant_id: Optional[str],
    ) -> AsyncIterator[TaskEvent]:
        """Execute skill using autonomous executor."""
        # Build configuration
        config = self._build_config(skill)

        # Create executor
        executor = AutonomousSkillExecutor(
            skill=skill,
            tool_registry=self._tool_registry,
            tool_executor=self._tool_executor,
            config=config,
        )

        # Activate skill context in tool executor
        self._tool_executor.activate_skill(skill)

        try:
            async for event in executor.execute(
                user_request=user_request,
                task_id=task_id,
                session_id=session_id,
                tenant_id=tenant_id,
            ):
                yield event
        finally:
            # Deactivate skill context
            self._tool_executor.deactivate_skill(skill.metadata.name)

    async def _execute_simple(
        self,
        skill: Skill,
        user_request: str,
        task_id: str,
    ) -> AsyncIterator[TaskEvent]:
        """Execute skill using simple (legacy) executor."""
        from omniforge.chat.llm_generator import LLMResponseGenerator
        from datetime import datetime
        from omniforge.tasks.models import TaskState
        from omniforge.agents.events import (
            TaskStatusEvent, TaskMessageEvent, TaskDoneEvent,
        )
        from omniforge.agents.models import TextPart

        # Create legacy executor
        executor = ExecutableSkill(
            skill=skill,
            tool_registry=self._tool_registry,
        )

        yield TaskStatusEvent(
            task_id=task_id,
            timestamp=datetime.utcnow(),
            state=TaskState.RUNNING,
        )

        # Execute (non-streaming)
        result = await executor.execute(user_request, task_id)

        yield TaskMessageEvent(
            task_id=task_id,
            timestamp=datetime.utcnow(),
            message_parts=[TextPart(text=result.get("result", ""))],
        )

        final_state = TaskState.COMPLETED if result.get("success") else TaskState.FAILED
        yield TaskDoneEvent(
            task_id=task_id,
            timestamp=datetime.utcnow(),
            final_state=final_state,
        )

    async def _execute_forked(
        self,
        skill: Skill,
        user_request: str,
        task_id: str,
        session_id: Optional[str],
        tenant_id: Optional[str],
    ) -> AsyncIterator[TaskEvent]:
        """Execute skill in forked (sub-agent) context."""
        from omniforge.agents.events import TaskStatusEvent, TaskMessageEvent, TaskDoneEvent
        from omniforge.tasks.models import TaskState
        from datetime import datetime
        from omniforge.agents.models import TextPart

        yield TaskStatusEvent(
            task_id=task_id,
            timestamp=datetime.utcnow(),
            state=TaskState.RUNNING,
            message=f"Spawning sub-agent for skill: {skill.metadata.name}",
        )

        # Build sub-agent configuration
        # Sub-agents get 50% of parent's iteration budget
        parent_config = self._build_config(skill)
        sub_config = AutonomousConfig(
            max_iterations=parent_config.max_iterations // 2,
            max_retries_per_tool=parent_config.max_retries_per_tool,
            model=skill.metadata.model,
        )

        # Create sub-agent executor
        executor = AutonomousSkillExecutor(
            skill=skill,
            tool_registry=self._tool_registry,
            tool_executor=self._tool_executor,
            config=sub_config,
        )

        # Execute in isolated context
        try:
            result = await executor.execute_sync(
                user_request=user_request,
                task_id=f"{task_id}-subagent",
                session_id=session_id,
                tenant_id=tenant_id,
            )

            # Summarize result for parent
            yield TaskMessageEvent(
                task_id=task_id,
                timestamp=datetime.utcnow(),
                message_parts=[TextPart(text=f"Sub-agent completed: {result.result[:500]}")],
            )

            final_state = TaskState.COMPLETED if result.success else TaskState.FAILED
            yield TaskDoneEvent(
                task_id=task_id,
                timestamp=datetime.utcnow(),
                final_state=final_state,
            )

        except Exception as e:
            from omniforge.agents.events import TaskErrorEvent
            yield TaskErrorEvent(
                task_id=task_id,
                timestamp=datetime.utcnow(),
                error_code="SUBAGENT_ERROR",
                error_message=str(e),
            )
            yield TaskDoneEvent(
                task_id=task_id,
                timestamp=datetime.utcnow(),
                final_state=TaskState.FAILED,
            )

    def _determine_execution_mode(
        self,
        skill: Skill,
        override: Optional[ExecutionMode],
    ) -> ExecutionMode:
        """Determine execution mode for a skill.

        Args:
            skill: The skill to check
            override: Optional mode override

        Returns:
            ExecutionMode to use
        """
        if override:
            return override

        # Check skill metadata for explicit mode
        # (This would require adding execution_mode to SkillMetadata)
        # For now, default to autonomous
        return ExecutionMode.AUTONOMOUS

    def _build_config(self, skill: Skill) -> AutonomousConfig:
        """Build configuration from skill metadata and defaults.

        Args:
            skill: The skill to build config for

        Returns:
            AutonomousConfig with merged settings
        """
        # Start with defaults
        config = AutonomousConfig(
            max_iterations=self._default_config.max_iterations,
            max_retries_per_tool=self._default_config.max_retries_per_tool,
            timeout_per_iteration_ms=self._default_config.timeout_per_iteration_ms,
            early_termination=self._default_config.early_termination,
            enable_error_recovery=self._default_config.enable_error_recovery,
        )

        # Override with skill-specific settings
        # (This would read from skill metadata extensions)
        if skill.metadata.model:
            config.model = skill.metadata.model

        return config
```

---

## 4. Data Models

### 4.1 Extended SkillMetadata

Add new fields to existing `SkillMetadata` model in `src/omniforge/skills/models.py`:

```python
class SkillMetadata(BaseModel):
    """Extended skill metadata with autonomous execution fields."""

    # Existing fields...
    name: str = Field(..., min_length=1, max_length=64)
    description: str = Field(..., min_length=1, max_length=1024)
    allowed_tools: Optional[list[str]] = Field(None, alias="allowed-tools")
    model: Optional[str] = None
    context: ContextMode = ContextMode.INHERIT

    # NEW: Autonomous execution fields
    execution_mode: str = Field(
        default="autonomous",
        description="Execution mode: 'autonomous' or 'simple'",
    )
    max_iterations: Optional[int] = Field(
        None,
        alias="max-iterations",
        ge=1,
        le=100,
        description="Max ReAct iterations (default: 15)",
    )
    max_retries_per_tool: Optional[int] = Field(
        None,
        alias="max-retries-per-tool",
        ge=0,
        le=10,
        description="Max retries per tool (default: 3)",
    )
    timeout_per_iteration: Optional[str] = Field(
        None,
        alias="timeout-per-iteration",
        description="Timeout per iteration (e.g., '30s')",
    )
    early_termination: Optional[bool] = Field(
        None,
        alias="early-termination",
        description="Allow early termination on confidence",
    )
```

### 4.2 Execution Metrics

```python
@dataclass
class ExecutionMetrics:
    """Metrics tracked during autonomous execution.

    Attributes:
        iterations_used: Number of iterations executed
        total_duration_ms: Total execution time
        llm_calls: Number of LLM calls made
        tool_calls: Number of tool calls made
        successful_tool_calls: Tool calls that succeeded
        failed_tool_calls: Tool calls that failed
        retries: Total retry attempts
        tokens_used: Total tokens consumed
        cost_usd: Total cost in USD
        files_loaded: Supporting files loaded on-demand
        error_recovery_count: Errors that were recovered
    """
    iterations_used: int = 0
    total_duration_ms: int = 0
    llm_calls: int = 0
    tool_calls: int = 0
    successful_tool_calls: int = 0
    failed_tool_calls: int = 0
    retries: int = 0
    tokens_used: int = 0
    cost_usd: float = 0.0
    files_loaded: int = 0
    error_recovery_count: int = 0
```

---

## 5. Processing Pipeline

### 5.1 Execution Flow Sequence Diagram

```
User Request                    SkillOrchestrator                    Preprocessing                        ReAct Loop
     |                                |                                  |                                    |
     |--- execute(skill, request) --->|                                  |                                    |
     |                                |                                  |                                    |
     |                                |--- load_skill() ----------------->|                                    |
     |                                |<--- Skill ------------------------|                                    |
     |                                |                                  |                                    |
     |                                |--- determine_mode() ------------>|                                    |
     |                                |<--- AUTONOMOUS -------------------|                                    |
     |                                |                                  |                                    |
     |                                |--- AutonomousSkillExecutor ----->|                                    |
     |                                |                                  |                                    |
     |                                |                                  |--- ContextLoader.load_initial() -->|
     |                                |                                  |<--- LoadedContext ------------------|
     |                                |                                  |                                    |
     |                                |                                  |--- DynamicInjector.process() ----->|
     |                                |                                  |<--- InjectedContent ----------------|
     |                                |                                  |                                    |
     |                                |                                  |--- StringSubstitutor.substitute() ->|
     |                                |                                  |<--- SubstitutedContent --------------|
     |                                |                                  |                                    |
     |                                |                                  |--- build_system_prompt() --------->|
     |                                |                                  |<--- system_prompt ------------------|
     |                                |                                  |                                    |
     |                                |                                  |                    loop: iteration |
     |                                |                                  |                                    |
     |                                |                                  |                    |--- call_llm() |
     |                                |                                  |                    |<-- response --|
     |                                |                                  |                    |               |
     |                                |                                  |                    |-- parse() ---|
     |                                |                                  |                    |<-- parsed ---|
     |                                |                                  |                    |               |
     |                                |                                  |                    | if action:   |
     |                                |                                  |                    |-- call_tool()|
     |                                |                                  |                    |<-- result ---|
     |                                |                                  |                    |               |
     |                                |                                  |                    |-- observe ---|
     |                                |                                  |                    |               |
     |                                |                                  |                    | if is_final: |
     |                                |                                  |                    |-- break -----|
     |                                |                                  |                    |               |
     |                                |                                  |                    end loop       |
     |                                |                                  |                                    |
     |<--- TaskEvent (streaming) -----|<----------------------------------|<-----------------------------------|
```

### 5.2 Step-by-Step Execution Flow

**Phase 1: Initialization**
1. `SkillOrchestrator.execute()` receives skill name and user request
2. Load skill via `SkillLoader.load_skill()`
3. Determine execution mode (autonomous/simple)
4. If forked context, spawn sub-agent
5. Otherwise, route to appropriate executor

**Phase 2: Preprocessing**
1. `ContextLoader.load_initial_context()` - Extract file references
2. `DynamicInjector.process()` - Execute and replace !`command` syntax
3. `StringSubstitutor.substitute()` - Replace variables

**Phase 3: System Prompt Construction**
1. Build base prompt with skill instructions
2. Append available tools from registry
3. Append available supporting files list
4. Add ReAct format instructions

**Phase 4: ReAct Loop Execution**
```python
for iteration in range(max_iterations):
    # 1. Think - Call LLM with conversation
    llm_response = await engine.call_llm(messages, system_prompt)

    # 2. Parse - Extract action or final answer
    parsed = parser.parse(llm_response)

    # 3. Check completion
    if parsed.is_final:
        return parsed.final_answer

    # 4. Act - Execute tool
    if parsed.action:
        result = await engine.call_tool(parsed.action, parsed.action_input)

        # 5. Observe - Record result
        observation = format_observation(result)
        conversation.append(assistant_message)
        conversation.append(user_observation)

        # 6. Error recovery
        if not result.success:
            record_failed_approach(parsed.action, parsed.action_input)
```

**Phase 5: Completion**
1. If final answer found: emit success event
2. If max iterations reached: synthesize partial results
3. Update metrics
4. Deactivate skill context

---

## 6. File Organization

### 6.1 New Files to Create

```
src/omniforge/skills/
    autonomous_executor.py      # AutonomousSkillExecutor (FR-1, FR-2)
    context_loader.py           # ContextLoader (FR-3)
    dynamic_injector.py         # DynamicInjector (FR-10)
    string_substitutor.py       # StringSubstitutor (FR-11)
    orchestrator.py             # SkillOrchestrator (FR-6)
    config.py                   # AutonomousConfig, ExecutionMetrics

tests/
    skills/
        test_autonomous_executor.py
        test_context_loader.py
        test_dynamic_injector.py
        test_string_substitutor.py
        test_orchestrator.py
```

### 6.2 Files to Modify

```
src/omniforge/skills/
    models.py                   # Add execution_mode, max_iterations fields
    parser.py                   # Update to parse new metadata fields
    executor.py                 # Mark as legacy, add deprecation warning

src/omniforge/tools/
    executor.py                 # Already has activate_skill/deactivate_skill

src/omniforge/agents/cot/
    prompts.py                  # Add build_autonomous_skill_prompt()
```

### 6.3 Import Structure

```python
# In src/omniforge/skills/__init__.py
from omniforge.skills.autonomous_executor import (
    AutonomousSkillExecutor,
    AutonomousConfig,
    ExecutionState,
    ExecutionResult,
)
from omniforge.skills.context_loader import ContextLoader, LoadedContext
from omniforge.skills.dynamic_injector import DynamicInjector, InjectedContent
from omniforge.skills.string_substitutor import StringSubstitutor, SubstitutionContext
from omniforge.skills.orchestrator import SkillOrchestrator, ExecutionMode
from omniforge.skills.executor import ExecutableSkill  # Legacy

__all__ = [
    # New autonomous execution
    "AutonomousSkillExecutor",
    "AutonomousConfig",
    "ExecutionState",
    "ExecutionResult",
    "ContextLoader",
    "LoadedContext",
    "DynamicInjector",
    "InjectedContent",
    "StringSubstitutor",
    "SubstitutionContext",
    "SkillOrchestrator",
    "ExecutionMode",
    # Legacy
    "ExecutableSkill",
]
```

---

## 7. Error Handling Strategy

### 7.1 Error Categories

| Category | Examples | Recovery Strategy |
|----------|----------|-------------------|
| Tool Errors | Network timeout, file not found | Retry with backoff, try alternative tool |
| LLM Errors | Rate limit, invalid response | Retry with backoff, reduce temperature |
| Validation Errors | Invalid arguments, missing required | Log and skip, use defaults |
| Command Injection Errors | Timeout, permission denied | Replace with error message in content |
| Configuration Errors | Invalid max_iterations | Use platform defaults |

### 7.2 Error Recovery Flow

```python
async def _handle_tool_error(
    self,
    tool_name: str,
    error: str,
    state: ExecutionState,
) -> str:
    """Handle tool execution error with recovery strategy.

    Recovery strategies:
    1. Retry same tool (if retries available)
    2. Try alternative approach
    3. Record partial result
    4. Graceful degradation
    """
    approach_key = f"{tool_name}:{hash(str(error))}"

    # Check if we've tried this approach before
    retry_count = state.failed_approaches.get(approach_key, 0)

    if retry_count < self._config.max_retries_per_tool:
        # Retry same approach
        state.failed_approaches[approach_key] = retry_count + 1
        return f"Tool failed: {error}. Please retry with different parameters or try an alternative approach."

    # Max retries exceeded - suggest alternative
    state.failed_approaches.add(approach_key)
    return (
        f"Tool '{tool_name}' failed after {retry_count} attempts: {error}. "
        f"Please try a different tool or approach to accomplish this task."
    )
```

### 7.3 Graceful Degradation

```python
def _synthesize_partial_results(self, state: ExecutionState) -> str:
    """Synthesize partial results when complete solution not possible.

    Args:
        state: Current execution state

    Returns:
        Summary of partial results achieved
    """
    if not state.partial_results:
        return "Unable to complete task. No partial results available."

    return (
        f"Completed {len(state.partial_results)} of intended objectives:\n"
        + "\n".join(f"- {r}" for r in state.partial_results)
        + f"\n\nEncountered {state.error_count} errors during execution."
    )
```

---

## 8. Testing Strategy

### 8.1 Unit Tests

**test_autonomous_executor.py**
```python
import pytest
from unittest.mock import AsyncMock, MagicMock

from omniforge.skills.autonomous_executor import (
    AutonomousSkillExecutor,
    AutonomousConfig,
    ExecutionState,
)


class TestAutonomousSkillExecutor:
    """Tests for AutonomousSkillExecutor."""

    @pytest.fixture
    def mock_skill(self):
        """Create mock skill."""
        skill = MagicMock()
        skill.metadata.name = "test-skill"
        skill.metadata.description = "Test skill"
        skill.metadata.allowed_tools = ["read", "write"]
        skill.metadata.model = None
        skill.content = "Test skill instructions"
        skill.base_path = "/tmp/skills/test"
        return skill

    @pytest.fixture
    def executor(self, mock_skill):
        """Create executor with mocks."""
        return AutonomousSkillExecutor(
            skill=mock_skill,
            tool_registry=MagicMock(),
            tool_executor=MagicMock(),
        )

    async def test_execute_returns_events(self, executor):
        """Execute should yield TaskEvent instances."""
        events = []
        async for event in executor.execute("test request"):
            events.append(event)

        assert len(events) > 0
        assert events[0].type == "status"

    async def test_execute_respects_max_iterations(self, executor):
        """Execute should stop at max_iterations."""
        executor._config.max_iterations = 3

        events = []
        async for event in executor.execute("test"):
            events.append(event)

        # Should have at most max_iterations LLM calls
        # (implementation-specific assertion)

    async def test_error_recovery_retries_tool(self, executor):
        """Error recovery should retry failed tools."""
        state = ExecutionState()

        result = await executor._handle_tool_error(
            tool_name="read",
            error="File not found",
            state=state,
        )

        assert "retry" in result.lower() or "alternative" in result.lower()


class TestContextLoader:
    """Tests for ContextLoader."""

    def test_extract_file_references(self):
        """Should extract file references from content."""
        from omniforge.skills.context_loader import ContextLoader

        content = """
        See reference.md for API documentation (1,200 lines)
        Read examples.md for usage patterns
        """

        loader = ContextLoader(MagicMock())
        refs = loader._extract_file_references(content)

        assert "reference.md" in refs
        assert "examples.md" in refs
        assert refs["reference.md"].estimated_lines == 1200


class TestDynamicInjector:
    """Tests for DynamicInjector."""

    async def test_process_replaces_commands(self):
        """Should replace !`command` with output."""
        from omniforge.skills.dynamic_injector import DynamicInjector

        injector = DynamicInjector(allowed_tools=["Bash"])
        content = "Date: !`date +%Y-%m-%d`"

        result = await injector.process(content)

        assert "!`date" not in result.content
        assert result.injections[0].success

    async def test_process_handles_disallowed_commands(self):
        """Should mark disallowed commands as failed."""
        from omniforge.skills.dynamic_injector import DynamicInjector

        injector = DynamicInjector(allowed_tools=["Bash(git:*)"])
        content = "Output: !`rm -rf /`"

        result = await injector.process(content)

        assert not result.injections[0].success
        assert "not allowed" in result.content.lower()


class TestStringSubstitutor:
    """Tests for StringSubstitutor."""

    def test_substitute_arguments(self):
        """Should substitute $ARGUMENTS."""
        from omniforge.skills.string_substitutor import (
            StringSubstitutor,
            SubstitutionContext,
        )

        substitutor = StringSubstitutor()
        context = SubstitutionContext(arguments="data.csv")

        result = substitutor.substitute("Process: $ARGUMENTS", context)

        assert result.content == "Process: data.csv"
        assert result.substitutions_made == 1

    def test_auto_append_arguments(self):
        """Should auto-append arguments if not in content."""
        from omniforge.skills.string_substitutor import (
            StringSubstitutor,
            SubstitutionContext,
        )

        substitutor = StringSubstitutor()
        context = SubstitutionContext(arguments="test.txt")

        result = substitutor.substitute("Process file", context)

        assert "ARGUMENTS: test.txt" in result.content
```

### 8.2 Integration Tests

**test_autonomous_execution_integration.py**
```python
import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

from omniforge.skills.autonomous_executor import AutonomousSkillExecutor
from omniforge.skills.loader import SkillLoader
from omniforge.skills.storage import StorageConfig
from omniforge.tools.setup import get_default_tool_registry


class TestAutonomousExecutionIntegration:
    """Integration tests for autonomous skill execution."""

    @pytest.fixture
    def skill_directory(self):
        """Create temporary skill directory with test skill."""
        with TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "test-skill"
            skill_dir.mkdir()

            # Create SKILL.md
            skill_md = skill_dir / "SKILL.md"
            skill_md.write_text("""---
name: test-skill
description: Test skill for integration testing
allowed-tools:
  - read
  - write
---

# Test Skill

Process files and generate output.

See reference.md for details.
""")

            # Create reference.md
            reference_md = skill_dir / "reference.md"
            reference_md.write_text("# Reference\nAdditional documentation.")

            yield skill_dir

    async def test_end_to_end_execution(self, skill_directory):
        """Test complete skill execution flow."""
        # Setup
        config = StorageConfig(project_path=str(skill_directory.parent))
        loader = SkillLoader(config)
        loader.build_index(force=True)

        registry = get_default_tool_registry()

        skill = loader.load_skill("test-skill")

        executor = AutonomousSkillExecutor(
            skill=skill,
            tool_registry=registry,
            tool_executor=MagicMock(),  # Mock for controlled testing
        )

        # Execute
        events = []
        async for event in executor.execute("Test execution"):
            events.append(event)

        # Verify
        assert any(e.type == "status" for e in events)
        assert any(e.type == "done" for e in events)
```

### 8.3 Test Coverage Targets

| Component | Target Coverage |
|-----------|-----------------|
| AutonomousSkillExecutor | 90% |
| ContextLoader | 95% |
| DynamicInjector | 90% |
| StringSubstitutor | 95% |
| SkillOrchestrator | 85% |
| Error handling paths | 80% |

---

## 9. Migration Path

### 9.1 Backward Compatibility Guarantees

1. **Existing skills work unchanged**: Skills without new metadata fields default to autonomous mode
2. **Opt-out available**: `execution_mode: simple` reverts to legacy behavior
3. **No breaking API changes**: `ExecutableSkill` remains functional
4. **Gradual deprecation**: Legacy executor marked deprecated, not removed

### 9.2 Skill Migration Guide

**Step 1: Verify Compatibility**
```yaml
# Existing skill (works as-is with autonomous execution)
---
name: my-skill
description: My existing skill
allowed-tools:
  - read
  - write
---
```

**Step 2: Opt-in to Explicit Configuration**
```yaml
---
name: my-skill
description: My existing skill
execution-mode: autonomous  # Explicit (optional)
max-iterations: 15          # Customize iteration budget
allowed-tools:
  - read
  - write
---
```

**Step 3: Add Progressive Context Loading**
```yaml
---
name: my-skill
description: My existing skill
---

# My Skill

Quick start instructions here (keep under 500 lines).

## When You Need More Information
- **API Details**: Read reference.md for complete API specs
- **Examples**: Read examples.md for usage patterns
```

**Step 4: Add Dynamic Injection (Optional)**
```yaml
---
name: pr-reviewer
allowed-tools:
  - Bash(gh:*)
---

## Current PR State
- **Diff**: !`gh pr diff`
- **Checks**: !`gh pr checks`
```

### 9.3 Deprecation Timeline

| Phase | Timeline | Action |
|-------|----------|--------|
| Phase 1 | v1.0 | Introduce autonomous executor, legacy remains default |
| Phase 2 | v1.1 | Autonomous becomes default, legacy available |
| Phase 3 | v2.0 | Legacy executor deprecated, warning on use |
| Phase 4 | v3.0 | Legacy executor removed |

---

## 10. Risk Assessment

### 10.1 Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| ReAct loop doesn't converge | Medium | High | Max iterations, early termination, partial results |
| High LLM costs | Medium | Medium | Model selection, caching, iteration limits |
| Command injection security | Low | Critical | Whitelist validation, sandboxing, audit logging |
| Performance regression | Medium | Medium | Async execution, parallel tool calls, caching |
| Breaking existing skills | Low | High | Comprehensive testing, opt-out mechanism |

### 10.2 Operational Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Runaway iterations | Low | Medium | Strict max_iterations enforcement |
| Resource exhaustion | Low | Medium | Timeouts, rate limiting |
| Debug difficulty | Medium | Medium | Full trace logging, metrics |

### 10.3 Risk Mitigation Strategies

1. **Circuit Breaker**: Stop execution if error rate exceeds threshold
2. **Cost Budget**: Optional per-skill cost limit
3. **Audit Trail**: Complete execution history for debugging
4. **Feature Flags**: Gradual rollout capability
5. **Rollback Plan**: Quick revert to legacy executor

---

## 11. Implementation Phases

### Phase 1: Core Infrastructure (Week 1-2)

**Tasks:**
1. Create `AutonomousSkillExecutor` with basic ReAct loop
2. Implement `ContextLoader` for progressive loading
3. Implement `StringSubstitutor` for variable replacement
4. Add new metadata fields to `SkillMetadata`
5. Unit tests for all new components

**Deliverables:**
- Working autonomous executor (no error recovery)
- Context loading functional
- Variable substitution working
- 80% test coverage

### Phase 2: Error Recovery & Injection (Week 3-4)

**Tasks:**
1. Implement error recovery logic (FR-2)
2. Create `DynamicInjector` for command injection (FR-10)
3. Add retry logic with approach tracking
4. Implement partial result synthesis
5. Integration tests

**Deliverables:**
- Error recovery working (target: 80% recovery rate)
- Dynamic injection functional
- Retry logic with backoff
- End-to-end tests passing

### Phase 3: Integration & Streaming (Week 5-6)

**Tasks:**
1. Create `SkillOrchestrator` for routing (FR-6)
2. Implement streaming events (FR-7)
3. Add sub-agent support (FR-5)
4. Integrate with `VisibilityController` (FR-4)
5. Performance optimization

**Deliverables:**
- Complete routing logic
- Streaming events working
- Sub-agent execution functional
- Visibility filtering applied

### Phase 4: Polish & Documentation (Week 7-8)

**Tasks:**
1. Model selection per skill (FR-12)
2. Configuration & tuning (FR-8)
3. Script execution support (FR-9)
4. Migration documentation
5. Performance testing

**Deliverables:**
- All FRs implemented
- Migration guide complete
- Performance benchmarks
- Documentation updated

---

## 12. Success Criteria

### 12.1 Functional Criteria

- [ ] Skills iterate up to max_iterations (default: 15)
- [ ] Error recovery rate >= 80% for common errors
- [ ] Progressive context loading saves >= 40% tokens
- [ ] Backward compatibility maintained (existing skills work)
- [ ] Streaming events delivered in real-time

### 12.2 Performance Criteria

- [ ] Iteration overhead < 500ms
- [ ] Simple tasks complete in < 10s
- [ ] No memory leaks during extended execution
- [ ] Concurrent execution support (100+ skills)

### 12.3 Quality Criteria

- [ ] Test coverage >= 85%
- [ ] All type hints pass mypy
- [ ] Documentation complete
- [ ] No critical security vulnerabilities

---

## Appendix A: System Prompt Template

```python
AUTONOMOUS_SKILL_SYSTEM_PROMPT = """
You are executing the '{skill_name}' skill autonomously.

SKILL INSTRUCTIONS:
{skill_content}

{available_files_section}

AVAILABLE TOOLS:
{tool_descriptions}

EXECUTION FORMAT:
You must respond in JSON format with one of these structures:

1. When you need to call a tool:
{{
    "thought": "Your reasoning about what to do next",
    "action": "tool_name",
    "action_input": {{"arg1": "value1"}},
    "is_final": false
}}

2. When you have completed the task:
{{
    "thought": "Your final reasoning",
    "final_answer": "Your complete response to the user",
    "is_final": true
}}

RULES:
- Think step by step about how to accomplish the task
- Use tools to gather information and perform actions
- If a tool fails, try an alternative approach
- Continue until the task is complete or you cannot make progress
- Provide clear, actionable final answers

Current iteration: {iteration}/{max_iterations}
"""
```

---

## Appendix B: Event Types Reference

| Event Type | Fields | When Emitted |
|------------|--------|--------------|
| TaskStatusEvent | state, message | Start, pause, resume |
| TaskMessageEvent | message_parts, is_partial | Iteration progress |
| TaskErrorEvent | error_code, error_message, details | Error occurred |
| TaskDoneEvent | final_state | Completion (success/failure) |

---

## Appendix C: Configuration Reference

```yaml
# Platform-level defaults (config/autonomous.yaml)
autonomous:
  default_max_iterations: 15
  default_max_retries_per_tool: 3
  default_timeout_per_iteration_ms: 30000
  enable_error_recovery: true
  default_model: "claude-sonnet-4"

  visibility:
    end_user: SUMMARY
    developer: FULL
    admin: FULL

  cost_limits:
    enabled: false
    max_cost_per_execution_usd: 1.0

  rate_limits:
    enabled: false
    max_iterations_per_minute: 100
```

---

## Appendix D: Design Clarifications & Decisions

### D.1 Model Selection Strategy (FR-12)

**Question:** How should we integrate model selection with existing LLMGenerator?

**Decision:**
- Use existing `LLMResponseGenerator` class with extended constructor
- Add `model` parameter: `LLMResponseGenerator(model="claude-haiku-4")`
- Map skill frontmatter models to actual Anthropic model IDs:
  - `haiku` → `claude-haiku-4`
  - `sonnet` → `claude-sonnet-4` (current default)
  - `opus` → `claude-opus-4`
- Keep current Anthropic API integration, just parameterize the model name

**Implementation:**
```python
# In AutonomousSkillExecutor
model_map = {
    "haiku": "claude-haiku-4",
    "sonnet": "claude-sonnet-4",
    "opus": "claude-opus-4",
}
model_id = model_map.get(skill.metadata.model, "claude-sonnet-4")
llm = LLMResponseGenerator(model=model_id, temperature=0.7)
```

---

### D.2 Script Execution Sandboxing (FR-9) ⚠️ UPDATED FOR SECURITY

**Question:** Should we implement Docker sandboxing for script execution?

**UPDATED DECISION (Post-Review):**

**Critical Security Issue:** The review identified that script execution without sandboxing is a **showstopper for multi-tenant enterprise deployment**. Arbitrary code execution must be sandboxed.

**NEW APPROACH - Two-Tier Sandboxing:**

**Tier 1: Basic Sandboxing (Phase 1 - SDK & Development)**
- Subprocess isolation with resource limits
- File system restrictions (chroot/jail)
- Network restrictions (no outbound connections)
- Environment variable sanitization
- Suitable for SDK deployments and development

**Tier 2: Docker Sandboxing (Phase 1 - Production Platform)**
- Full container isolation for each script execution
- Resource limits (CPU, memory, disk, network)
- Read-only skill directory mounting
- Temporary workspace with cleanup
- **Required for enterprise/platform deployment**

**Implementation Architecture:**

```python
# src/omniforge/skills/script_executor.py
from enum import Enum
from dataclasses import dataclass
import subprocess
import docker  # pip install docker
import tempfile
import shutil

class SandboxMode(str, Enum):
    """Sandbox execution modes."""
    NONE = "none"           # No sandboxing (dev only)
    SUBPROCESS = "subprocess"  # Basic subprocess isolation
    DOCKER = "docker"       # Full Docker isolation

@dataclass
class ScriptExecutionConfig:
    """Configuration for script execution."""
    sandbox_mode: SandboxMode = SandboxMode.SUBPROCESS
    timeout_seconds: int = 30
    max_memory_mb: int = 512
    max_cpu_percent: int = 50
    allow_network: bool = False
    allow_file_write: bool = True  # In temp workspace only

class ScriptExecutor:
    """Executes scripts with configurable sandboxing."""

    def __init__(self, config: ScriptExecutionConfig):
        self.config = config
        if config.sandbox_mode == SandboxMode.DOCKER:
            self.docker_client = docker.from_env()

    async def execute_script(
        self,
        script_path: str,
        skill_dir: str,
        workspace: str,
    ) -> ScriptResult:
        """Execute a script with appropriate sandboxing."""

        # Validate script path (MUST be in skill directory)
        if not self._is_safe_path(script_path, skill_dir):
            raise SecurityError(f"Script path outside skill directory: {script_path}")

        if self.config.sandbox_mode == SandboxMode.DOCKER:
            return await self._execute_in_docker(script_path, skill_dir, workspace)
        elif self.config.sandbox_mode == SandboxMode.SUBPROCESS:
            return await self._execute_in_subprocess(script_path, skill_dir, workspace)
        else:
            return await self._execute_unsafe(script_path, workspace)

    async def _execute_in_docker(
        self,
        script_path: str,
        skill_dir: str,
        workspace: str,
    ) -> ScriptResult:
        """Execute script in Docker container (highest security)."""

        # Create temporary workspace
        temp_workspace = tempfile.mkdtemp(prefix="skill-exec-")

        try:
            # Determine image based on script type
            if script_path.endswith('.py'):
                image = "python:3.11-slim"
                cmd = ["python", "/script/script.py"]
            elif script_path.endswith('.js'):
                image = "node:18-slim"
                cmd = ["node", "/script/script.js"]
            else:
                image = "ubuntu:22.04"
                cmd = ["bash", "/script/script.sh"]

            # Run container with strict limits
            container = self.docker_client.containers.run(
                image=image,
                command=cmd,
                volumes={
                    skill_dir: {'bind': '/skill', 'mode': 'ro'},  # Read-only
                    script_path: {'bind': '/script/script.py', 'mode': 'ro'},
                    temp_workspace: {'bind': '/workspace', 'mode': 'rw'},
                },
                working_dir='/workspace',
                mem_limit=f"{self.config.max_memory_mb}m",
                cpu_period=100000,
                cpu_quota=self.config.max_cpu_percent * 1000,
                network_mode='none' if not self.config.allow_network else 'bridge',
                detach=True,
                remove=True,  # Auto-cleanup
            )

            # Wait for completion with timeout
            try:
                result = container.wait(timeout=self.config.timeout_seconds)
                logs = container.logs().decode('utf-8')

                return ScriptResult(
                    success=(result['StatusCode'] == 0),
                    output=logs,
                    exit_code=result['StatusCode'],
                )
            except docker.errors.APIError as e:
                container.kill()
                raise ScriptExecutionError(f"Docker execution failed: {e}")

        finally:
            # Cleanup temporary workspace
            shutil.rmtree(temp_workspace, ignore_errors=True)

    async def _execute_in_subprocess(
        self,
        script_path: str,
        skill_dir: str,
        workspace: str,
    ) -> ScriptResult:
        """Execute script in subprocess with resource limits (medium security)."""

        # Use resource module to limit CPU/memory
        import resource

        def set_limits():
            # Limit memory
            resource.setrlimit(
                resource.RLIMIT_AS,
                (self.config.max_memory_mb * 1024 * 1024, -1)
            )
            # Limit CPU time
            resource.setrlimit(
                resource.RLIMIT_CPU,
                (self.config.timeout_seconds, -1)
            )

        # Determine interpreter
        if script_path.endswith('.py'):
            cmd = ['python', script_path]
        elif script_path.endswith('.js'):
            cmd = ['node', script_path]
        else:
            cmd = ['bash', script_path]

        # Execute with limits
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=workspace,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            preexec_fn=set_limits,  # Apply limits before execution
        )

        try:
            stdout, _ = await asyncio.wait_for(
                process.communicate(),
                timeout=self.config.timeout_seconds
            )

            return ScriptResult(
                success=(process.returncode == 0),
                output=stdout.decode('utf-8'),
                exit_code=process.returncode,
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            raise ScriptExecutionError("Script execution timed out")

    def _is_safe_path(self, script_path: str, skill_dir: str) -> bool:
        """Validate that script is within skill directory."""
        import os
        script_abs = os.path.abspath(script_path)
        skill_abs = os.path.abspath(skill_dir)
        return script_abs.startswith(skill_abs + os.sep)
```

**Configuration (Platform Admin):**
```yaml
# config/autonomous.yaml
script_execution:
  # SDK/Development: Use subprocess sandboxing
  # Production Platform: Use Docker sandboxing
  sandbox_mode: docker  # or "subprocess" for dev

  timeout_seconds: 30
  max_memory_mb: 512
  max_cpu_percent: 50
  allow_network: false
  allow_file_write: true  # In temp workspace only

  # Docker-specific
  docker_images:
    python: "python:3.11-slim"
    node: "node:18-slim"
    shell: "ubuntu:22.04"
```

**Security Measures:**
1. ✅ Script path validation (must be in `${SKILL_DIR}/scripts/`)
2. ✅ Resource limits (CPU, memory, timeout)
3. ✅ Read-only skill directory mounting
4. ✅ Isolated temporary workspace
5. ✅ Network isolation (default: no outbound)
6. ✅ Auto-cleanup after execution
7. ✅ Audit logging of all script executions

**Deployment Recommendations:**
- **SDK Users**: Can use `subprocess` mode (simpler)
- **Platform Deployment**: **MUST use `docker` mode** (security requirement)
- **Development**: Can use `none` mode (unsafe, dev only)

**Rationale:** Security is non-negotiable for multi-tenant platforms. Docker sandboxing provides the necessary isolation for enterprise deployment.

---

### D.2.1 SKILL.md Size Limit Enforcement (FR-3) ⚠️ ADDED FOR TOKEN OPTIMIZATION

**Issue:** Progressive context loading depends on SKILL.md being kept small (<500 lines), but there's no enforcement.

**Decision:** Implement hard limit with grace period for existing skills

**Implementation:**

```python
# src/omniforge/skills/loader.py

class SkillValidationError(Exception):
    """Raised when skill validation fails."""
    pass

class SkillLoader:
    """Loads and validates skills from SKILL.md files."""

    MAX_SKILL_LINES = 500  # Hard limit for new skills

    async def load_skill(self, skill_path: Path) -> Skill:
        """Load and validate a skill."""

        skill_file = skill_path / "SKILL.md"
        if not skill_file.exists():
            raise SkillValidationError(f"SKILL.md not found: {skill_file}")

        # Read content
        content = skill_file.read_text()
        lines = content.split('\n')
        line_count = len(lines)

        # Extract metadata from frontmatter
        metadata = self._parse_frontmatter(content)

        # Enforce size limit
        is_legacy = metadata.get("legacy_large_file", False)

        if line_count > self.MAX_SKILL_LINES:
            if is_legacy:
                # Grace period for existing skills
                logger.warning(
                    f"Skill '{skill_path.name}' exceeds {self.MAX_SKILL_LINES} lines "
                    f"({line_count} lines). This skill has legacy_large_file flag. "
                    f"Please migrate content to supporting files before next major version."
                )
            else:
                # Strict enforcement for new skills
                raise SkillValidationError(
                    f"SKILL.md must be under {self.MAX_SKILL_LINES} lines "
                    f"(found {line_count} lines). Move detailed content to supporting files:\n"
                    f"  - reference.md: API documentation, detailed specs\n"
                    f"  - examples.md: Usage examples, sample code\n"
                    f"  - templates/: Templates and boilerplate\n\n"
                    f"To temporarily bypass this limit (not recommended), add to frontmatter:\n"
                    f"  legacy_large_file: true"
                )

        # Track metrics for token savings validation
        metadata["skill_file_lines"] = line_count

        return Skill(metadata=metadata, content=content, skill_dir=skill_path)
```

**Migration Path:**
```yaml
# Existing large skill (grace period)
---
name: legacy-skill
legacy_large_file: true  # Temporary bypass
---
[1200 lines of content]

# Recommended migration
---
name: legacy-skill
---
# Core instructions (450 lines)

## Supporting Files
- reference.md: Detailed API specs (500 lines)
- examples.md: Usage examples (250 lines)
```

**Token Savings Tracking:**
```python
# In ReasoningChain.metrics
class ChainMetrics(BaseModel):
    # ... existing fields

    # Token optimization metrics
    context_tokens_initial: int = 0      # SKILL.md only
    context_tokens_loaded: int = 0       # After loading supporting files
    context_tokens_total: int = 0        # Final total
    context_savings_percent: float = 0.0  # Calculated savings

    def calculate_savings(self):
        """Calculate token savings from progressive loading."""
        if self.context_tokens_total > 0:
            potential_full_load = self.context_tokens_initial + self.context_tokens_loaded
            self.context_savings_percent = (
                (potential_full_load - self.context_tokens_total) /
                potential_full_load * 100
            )
```

---

### D.2.2 Sub-Agent Depth Tracking (FR-5) ⚠️ ADDED FOR SAFETY

**Issue:** The plan mentions "2 levels max" but doesn't show explicit enforcement.

**Decision:** Add strict depth tracking to prevent recursive explosions

**Implementation:**

```python
# src/omniforge/skills/autonomous_executor.py

from dataclasses import dataclass

@dataclass
class ExecutionContext:
    """Tracks execution context for sub-agent management."""

    depth: int = 0                          # Current depth (0 = root)
    max_depth: int = 2                      # Maximum allowed depth
    parent_task_id: Optional[str] = None    # Parent task for tracing
    parent_skill_name: Optional[str] = None # Parent skill for logging
    skill_chain: list[str] = None           # Full chain: [skill-a, skill-b, skill-c]

    def __post_init__(self):
        if self.skill_chain is None:
            self.skill_chain = []

    def create_child_context(self, skill_name: str, task_id: str) -> "ExecutionContext":
        """Create context for sub-agent execution."""

        if self.depth >= self.max_depth:
            raise SkillExecutionError(
                f"Maximum sub-agent depth ({self.max_depth}) exceeded. "
                f"Skill chain: {' -> '.join(self.skill_chain + [skill_name])}"
            )

        return ExecutionContext(
            depth=self.depth + 1,
            max_depth=self.max_depth,
            parent_task_id=task_id,
            parent_skill_name=skill_name,
            skill_chain=self.skill_chain + [skill_name],
        )

class AutonomousSkillExecutor:
    """Executor with depth tracking."""

    async def execute(
        self,
        task: Task,
        skill: Skill,
        context: Optional[ExecutionContext] = None,
    ) -> TaskResult:
        """Execute skill with depth tracking."""

        # Initialize context for root execution
        if context is None:
            context = ExecutionContext()

        # Add current skill to chain
        context.skill_chain.append(skill.metadata.name)

        # Log execution depth
        logger.info(
            f"Executing skill '{skill.metadata.name}' at depth {context.depth}",
            skill_chain=" -> ".join(context.skill_chain),
        )

        # If skill has context: fork, spawn sub-agent
        if skill.metadata.context == "fork":
            return await self._execute_forked(task, skill, context)
        else:
            return await self._execute_normal(task, skill, context)

    async def _execute_forked(
        self,
        task: Task,
        skill: Skill,
        context: ExecutionContext,
    ) -> TaskResult:
        """Execute skill in forked sub-agent with depth checking."""

        # Create child context (raises if depth exceeded)
        child_context = context.create_child_context(
            skill_name=skill.metadata.name,
            task_id=task.id,
        )

        # Calculate sub-agent iteration budget (50% of parent's remaining)
        parent_budget = getattr(context, 'remaining_iterations', 15)
        child_iterations = max(1, parent_budget // 2)

        # Create sub-agent config
        sub_config = AutonomousConfig(
            max_iterations=child_iterations,
            max_depth=context.max_depth,
        )

        logger.info(
            f"Spawning sub-agent for '{skill.metadata.name}' "
            f"(depth={child_context.depth}/{context.max_depth}, "
            f"iterations={child_iterations})"
        )

        # Execute in isolated context
        sub_executor = AutonomousSkillExecutor(config=sub_config)
        return await sub_executor.execute(task, skill, child_context)
```

**Example Execution:**
```
Root Skill A (depth=0, max_iterations=15)
  └─> spawns Sub-Skill B (depth=1, max_iterations=7)
      └─> spawns Sub-Skill C (depth=2, max_iterations=3)
          └─> tries to spawn Sub-Skill D
              ❌ ERROR: Maximum sub-agent depth (2) exceeded
                 Skill chain: skill-a -> skill-b -> skill-c -> skill-d
```

---

### D.2.3 Iteration Budget Model Clarification (FR-1) ⚠️ CLARIFIED

**Issue:** Ambiguity in how iteration budgets work when skills call other skills.

**Decision:** Use **Independent Budgets** (simpler, more predictable)

**Iteration Budget Models:**

**Model 1: Independent Budgets** ✅ CHOSEN
```python
# Each skill gets its own budget, independent of caller
skill_a (max_iterations=10):
    calls skill_b (max_iterations=15)
        → skill_b executes with full 15 iterations

# Pros:
- Simple and predictable
- Skills behave consistently regardless of caller
- Easy to reason about and debug

# Cons:
- Total iterations can be high: 10 + 15 = 25
- Risk of runaway execution if skills call each other recursively
```

**Model 2: Inherited Budgets** ❌ NOT CHOSEN (too complex)
```python
# Child inherits parent's remaining budget
skill_a (max_iterations=10, used=7):
    calls skill_b (max_iterations=15)
        → skill_b gets min(15, 10-7) = 3 iterations

# Pros:
- Total iterations bounded by root budget
- Prevents runaway execution

# Cons:
- Complex: skills behave differently based on caller
- Difficult to debug: "Why did skill-b only get 3 iterations?"
- Breaking change: skill behavior depends on execution context
```

**Implementation (Independent Budgets):**
```python
class AutonomousSkillExecutor:
    async def execute(self, task: Task, skill: Skill) -> TaskResult:
        """Execute skill with independent iteration budget."""

        # Use skill's configured budget, or default
        max_iterations = skill.metadata.max_iterations or 15

        # Log for visibility
        logger.info(
            f"Starting '{skill.metadata.name}' with {max_iterations} iterations"
        )

        # Execute ReAct loop
        for iteration in range(max_iterations):
            # ... execution logic
            pass
```

**Safety Mechanism (Prevent Runaway):**
```python
# Global iteration counter to prevent infinite loops
class GlobalExecutionLimits:
    """Global limits across all skill executions."""

    MAX_TOTAL_ITERATIONS = 100  # Safety limit
    MAX_SKILL_CHAIN_LENGTH = 5  # Prevent deep nesting

    def __init__(self):
        self.total_iterations = 0
        self.skill_chain_length = 0

    def check_limits(self, skill_name: str):
        """Raise if global limits exceeded."""
        if self.total_iterations >= self.MAX_TOTAL_ITERATIONS:
            raise ExecutionError(
                f"Global iteration limit ({self.MAX_TOTAL_ITERATIONS}) exceeded"
            )

        if self.skill_chain_length >= self.MAX_SKILL_CHAIN_LENGTH:
            raise ExecutionError(
                f"Skill chain depth limit ({self.MAX_SKILL_CHAIN_LENGTH}) exceeded"
            )

# Usage
limits = GlobalExecutionLimits()
for iteration in range(max_iterations):
    limits.total_iterations += 1
    limits.check_limits(skill.metadata.name)
    # ... execute iteration
```

**Rationale:** Independent budgets are simpler and more predictable. Global limits prevent runaway execution while maintaining simplicity.

---

### D.3 Cost Tracking Integration (FR-8)

**Question:** Do we need new cost tracking or use existing infrastructure?

**Decision:**
- Check for existing `enterprise/cost_tracker.py` and integrate if available
- Otherwise, leverage existing `ReasoningChain.metrics`:
  - Already tracks: `total_tokens`, `total_cost`
  - Extend with: `cost_per_iteration`, `model_used`
- Add cost alerts at skill execution level:
  - Warn if execution cost > threshold (default: $0.50)
  - Configurable per skill: `max_cost_usd: 1.0`
- Full cost limiting/budgets can be Phase 2 (enterprise feature)

**Implementation:**
```python
# In ReasoningChain.metrics
class ChainMetrics(BaseModel):
    total_tokens: int = 0
    total_cost: float = 0.0
    cost_per_iteration: list[float] = []  # Track per iteration
    model_used: str = "claude-sonnet-4"

    def add_iteration_cost(self, tokens: int, cost: float):
        self.total_tokens += tokens
        self.total_cost += cost
        self.cost_per_iteration.append(cost)
```

---

### D.4 Sub-Agent Depth Limit (FR-5)

**Question:** Should we limit sub-agent nesting depth to prevent recursion?

**Decision:** YES
- **Maximum depth: 2 levels** (parent → child → grandchild, then stop)
- Sub-agent iteration budget: **50% of parent's remaining budget**
- Track depth in execution context:
  ```python
  @dataclass
  class SubAgentContext:
      depth: int = 0
      max_depth: int = 2
      parent_skill_name: Optional[str] = None
  ```
- Raise clear error if depth exceeded: `SubAgentDepthExceededError`

**Example:**
```
Skill A (depth=0, max_iterations=15)
  └─> spawns Skill B (depth=1, max_iterations=7)
      └─> spawns Skill C (depth=2, max_iterations=3)
          └─> tries to spawn Skill D ❌ ERROR: Max depth reached
```

**Rationale:** Prevents infinite recursion attacks and runaway costs.

---

### D.5 Backward Compatibility Default (FR-6)

**Question:** Should skills default to autonomous or simple mode?

**Decision:** Start conservative
- **Default: `execution_mode: simple` (legacy mode)**
- Requires explicit opt-in: `execution_mode: autonomous`
- After 2-3 releases and proven stability, flip default to autonomous
- Migration timeline:
  - **v1.0**: Default simple, autonomous opt-in
  - **v1.1-1.2**: Monitor adoption, fix issues
  - **v2.0**: Flip default to autonomous, simple opt-out

**Skill Behavior:**
```yaml
# No execution_mode specified → uses simple (legacy)
---
name: old-skill
description: Existing skill
---

# Explicit opt-in to autonomous
---
name: new-skill
description: New autonomous skill
execution_mode: autonomous
max_iterations: 15
---
```

**Rationale:**
- Safer rollout (don't break existing skills)
- Gives developers time to test autonomous mode
- Reduces support burden during transition

---

### D.6 Implementation Priority Adjustments

Based on clarifications, updated priority order:

**Phase 1 (Weeks 1-2) - Core Foundation:**
1. AutonomousSkillExecutor with ReAct loop (FR-1)
2. ContextLoader for progressive loading (FR-3)
3. StringSubstitutor for variables (FR-11)
4. Backward compatibility routing (FR-6)

**Phase 2 (Weeks 3-4) - Advanced Features:**
5. Error recovery & retry logic (FR-2)
6. DynamicInjector for command injection (FR-10)
7. Script execution via Bash tool (FR-9)
8. Model selection integration (FR-12)

**Phase 3 (Weeks 5-6) - Integration:**
9. Sub-agent execution with depth limits (FR-5)
10. Streaming events (FR-7)
11. User-facing progressive disclosure (FR-4)
12. Configuration & tuning (FR-8)

**Phase 4 (Weeks 7-8) - Polish:**
13. Comprehensive testing
14. Documentation
15. Migration guides
16. Performance optimization

---

### D.7 Security Hardening Summary ⚠️ POST-REVIEW UPDATES

**Review Status:** APPROVED WITH CHANGES (All critical issues addressed)
**Review Date:** 2026-01-27
**Last Updated:** 2026-01-27

This section consolidates all security improvements made after the technical architecture review.

**Critical Security Updates:**

1. **Script Execution Sandboxing (D.2)** 🔴 HIGH PRIORITY
   - ✅ Added Docker sandboxing architecture for enterprise/platform deployments
   - ✅ Subprocess isolation for SDK/development deployments
   - ✅ Resource limits (CPU: 50%, Memory: 512MB, Timeout: 30s)
   - ✅ Read-only skill directory mounting
   - ✅ Network isolation (default: disabled)
   - ✅ Automatic temporary workspace cleanup
   - **Review Finding:** "Showstopper for enterprise without this"
   - **Impact:** Prevents arbitrary code execution in multi-tenant environments

2. **Command Injection Validation Strengthening** 🟡 MEDIUM-HIGH
   - ✅ Block shell operators (; && || | > < $() ` newlines)
   - ✅ Use shlex.split() to prevent shell expansion
   - ✅ Path traversal protection (.. and absolute paths blocked)
   - ✅ Security audit logging for all injection attempts
   - **Review Finding:** "Vulnerable to shell injection attacks"
   - **Impact:** Prevents malicious command execution via !`command` syntax

3. **SKILL.md Size Limit Enforcement (D.2.1)** 🟡 MEDIUM
   - ✅ Hard 500-line limit for new skills (validation error)
   - ✅ Grace period for existing skills (legacy_large_file flag)
   - ✅ Clear migration guidance in error messages
   - ✅ Token savings metrics tracking
   - **Review Finding:** "Token savings won't materialize without enforcement"
   - **Impact:** Ensures 40% token savings claim is achieved

4. **Sub-Agent Depth Tracking (D.2.2)** 🟡 MEDIUM
   - ✅ ExecutionContext tracks depth explicitly
   - ✅ Hard limit: 2 levels maximum (parent → child → grandchild)
   - ✅ Clear error with full skill chain on violation
   - ✅ Prevents infinite recursion loops
   - **Review Finding:** "Low probability, high impact if triggered"
   - **Impact:** Prevents resource exhaustion from recursive spawning

5. **Iteration Budget Clarification (D.2.3)** 🟢 ARCHITECTURAL
   - ✅ Documented: Independent Budgets model (simpler, predictable)
   - ✅ Global safety limits (100 total iterations, 5 skill chain length)
   - ✅ Clear behavior documented for developers
   - **Review Finding:** "Ambiguity could cause bugs"
   - **Impact:** Predictable execution with bounded resource usage

**Priority Adjustments:**

| Feature | Old Priority | New Priority | Moved To | Rationale |
|---------|--------------|--------------|----------|-----------|
| FR-12 (Model Selection) | P2 | **P1** | Phase 2 | Cost optimization critical |
| Script Sandboxing | Phase 2 Optional | **Phase 1 Required** | Phase 1 | Security showstopper |
| Size Limit Enforcement | Warn-only | **Hard Limit** | Phase 1 | Token savings depends on it |
| Sub-Agent Depth | Mentioned | **Implemented** | Phase 2 | Safety requirement |

**Updated Implementation Timeline:**

```
Phase 1 (Weeks 1-2): Core + Security Hardening
├─ ReAct Loop (FR-1)
├─ Context Loader with 500-line enforcement (FR-3) ⚠️ HARDENED
├─ String Substitutor (FR-11)
├─ Backward Compatibility (FR-6)
└─ Script Executor with Docker sandboxing (FR-9) ⚠️ ADDED

Phase 2 (Weeks 3-4): Advanced Features + Validation
├─ Error Recovery (FR-2)
├─ Dynamic Injector with strengthened validation (FR-10) ⚠️ HARDENED
├─ Model Selection (FR-12) ⚠️ PROMOTED
└─ Sub-Agent with depth tracking (FR-5) ⚠️ MOVED UP

Phase 3 (Weeks 5-6): Integration
├─ Streaming Events (FR-7)
├─ Progressive Disclosure (FR-4)
└─ Configuration (FR-8)

Phase 4 (Weeks 7-8): Testing & Documentation
├─ Security testing
├─ Performance testing
├─ Migration guides
└─ Security audit documentation
```

**Security Validation Checklist (Pre-Production):**

Before deploying to production, verify:
- [ ] Docker sandboxing enabled (`sandbox_mode: docker`)
- [ ] Command injection validation logs show blocked attempts
- [ ] No skills in production use `legacy_large_file` flag
- [ ] Sub-agent depth limits tested (confirm 2-level max enforced)
- [ ] Global iteration limits tested (confirm 100-iteration safety net)
- [ ] Security audit logging captures all critical events
- [ ] Resource limits tested under load (CPU, memory, timeout)
- [ ] Network isolation verified (scripts cannot call external APIs)
- [ ] Workspace cleanup verified (no data leakage between executions)
- [ ] Token savings metrics show 35-45% reduction

**Deployment Configuration Matrix:**

| Environment | Sandbox | Size Limits | Depth | Iterations | Audit Log |
|-------------|---------|-------------|-------|------------|-----------|
| Local Dev | none | Warn | 2 | 15 | Optional |
| CI/CD | subprocess | Warn | 2 | 10 | Required |
| SDK | subprocess | Enforce | 2 | 15 | Optional |
| **Production** | **docker** | **Enforce** | **2** | **15** | **Required** |

**Security Architecture Diagram:**

```
User Request
    ↓
┌─────────────────────────────────┐
│  AutonomousSkillExecutor        │
│  - Validates execution_mode     │
│  - Enforces depth limits        │
│  - Tracks global iterations     │
└─────────────────────────────────┘
    ↓
┌─────────────────────────────────┐
│  ContextLoader                  │
│  - Enforces 500-line limit      │
│  - Validates skill structure    │
└─────────────────────────────────┘
    ↓
┌─────────────────────────────────┐
│  DynamicInjector                │
│  - Validates !`commands`        │
│  - Blocks shell operators       │
│  - Audit logs attempts          │
└─────────────────────────────────┘
    ↓
┌─────────────────────────────────┐
│  ScriptExecutor                 │
│  - Docker/subprocess sandbox    │
│  - Resource limits enforced     │
│  - Network isolated             │
│  - Path validation              │
└─────────────────────────────────┘
    ↓
    Result + Metrics
```

**Review Approval:**

- ✅ Architecture aligned with enterprise requirements
- ✅ All critical security issues addressed
- ✅ Integration strategy validated
- ✅ Implementation feasible within 8-week timeline
- ✅ **APPROVED** - Ready for task decomposition

**Next Step:** Proceed to Step 4 (Task Decomposition) with security-hardened technical plan.

---

**End of Technical Implementation Plan**
**Last Updated:** 2026-01-27 (Post-Security Review)
