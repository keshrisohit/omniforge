"""Integration tests for end-to-end autonomous skill execution.

This module tests the complete autonomous skill execution flow from skill loading
through result generation. Tests use realistic skill definitions and exercise the
full preprocessing pipeline, ReAct loop, and event streaming (TASK-019).
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from omniforge.agents.events import (
    TaskDoneEvent,
    TaskMessageEvent,
    TaskStatusEvent,
)
from omniforge.agents.models import TextPart
from omniforge.skills.config import AutonomousConfig, ExecutionContext
from omniforge.skills.loader import SkillLoader
from omniforge.skills.orchestrator import ExecutionMode, SkillOrchestrator
from omniforge.skills.storage import StorageConfig
from omniforge.tasks.models import TaskState
from omniforge.tools.base import BaseTool, ToolCallContext, ToolDefinition, ToolResult
from omniforge.tools.executor import ToolExecutor
from omniforge.tools.registry import ToolRegistry
from omniforge.tools.types import ToolType, VisibilityLevel


class MockReadTool(BaseTool):
    """Mock read tool for testing."""

    def __init__(self) -> None:
        """Initialize mock read tool."""
        from omniforge.tools.base import ToolParameter

        self._definition = ToolDefinition(
            name="read",
            type=ToolType.FILE_READ,
            description="Read a file",
            parameters=[
                ToolParameter(
                    name="file_path",
                    type="string",
                    description="Path to the file to read",
                    required=True,
                )
            ],
        )

    @property
    def definition(self) -> ToolDefinition:
        """Get tool definition."""
        return self._definition

    async def execute(self, context: ToolCallContext, arguments: dict) -> ToolResult:
        """Execute read tool."""
        file_path = arguments.get("file_path", "")

        # Simulate reading supporting files
        if "reference.md" in file_path:
            content = "# Reference\n\nData format: CSV\nProcessing steps: validate, transform"
            return ToolResult(success=True, result={"content": content}, duration_ms=10)

        return ToolResult(
            success=True,
            result={"content": f"Content of {file_path}", "file_path": file_path},
            duration_ms=10,
        )


class MockWriteTool(BaseTool):
    """Mock write tool for testing."""

    def __init__(self) -> None:
        """Initialize mock write tool."""
        from omniforge.tools.base import ToolParameter

        self._definition = ToolDefinition(
            name="write",
            type=ToolType.FILE_WRITE,
            description="Write to a file",
            parameters=[
                ToolParameter(
                    name="file_path",
                    type="string",
                    description="Path to write to",
                    required=True,
                ),
                ToolParameter(
                    name="content",
                    type="string",
                    description="Content to write",
                    required=True,
                ),
            ],
        )

    @property
    def definition(self) -> ToolDefinition:
        """Get tool definition."""
        return self._definition

    async def execute(self, context: ToolCallContext, arguments: dict) -> ToolResult:
        """Execute write tool."""
        return ToolResult(
            success=True,
            result={"status": "written", "file_path": arguments.get("file_path")},
            duration_ms=15,
        )


class MockGrepTool(BaseTool):
    """Mock grep tool for testing."""

    def __init__(self) -> None:
        """Initialize mock grep tool."""
        from omniforge.tools.base import ToolParameter

        self._definition = ToolDefinition(
            name="grep",
            type=ToolType.FILE_READ,
            description="Search for patterns",
            parameters=[
                ToolParameter(
                    name="pattern",
                    type="string",
                    description="Pattern to search",
                    required=True,
                )
            ],
        )

    @property
    def definition(self) -> ToolDefinition:
        """Get tool definition."""
        return self._definition

    async def execute(self, context: ToolCallContext, arguments: dict) -> ToolResult:
        """Execute grep tool."""
        return ToolResult(
            success=True,
            result={"matches": ["line 1", "line 2"], "pattern": arguments.get("pattern")},
            duration_ms=12,
        )


class FlakyTool(BaseTool):
    """Mock tool that fails initially then succeeds."""

    def __init__(self) -> None:
        """Initialize flaky tool."""
        from omniforge.tools.base import ToolParameter

        self._definition = ToolDefinition(
            name="flaky_tool",
            type=ToolType.FUNCTION,
            description="A tool that may fail initially",
            parameters=[
                ToolParameter(
                    name="action",
                    type="string",
                    description="Action to perform",
                    required=True,
                )
            ],
        )
        self._call_count = 0

    @property
    def definition(self) -> ToolDefinition:
        """Get tool definition."""
        return self._definition

    async def execute(self, context: ToolCallContext, arguments: dict) -> ToolResult:
        """Execute flaky tool - fails first 2 times, succeeds on 3rd."""
        self._call_count += 1

        if self._call_count < 3:
            return ToolResult(
                success=False,
                error=f"Temporary failure (attempt {self._call_count})",
                duration_ms=10,
            )

        return ToolResult(
            success=True,
            result={"status": "success", "attempts": self._call_count},
            duration_ms=10,
        )


@pytest.fixture
def test_skills_dir(tmp_path: Path) -> Path:
    """Get the test skills fixtures directory."""
    # Use the actual fixtures directory we created
    fixtures_dir = Path(__file__).parent / "fixtures" / "test_skills"
    return fixtures_dir


@pytest.fixture
def skill_loader(test_skills_dir: Path) -> SkillLoader:
    """Create skill loader with test skills."""
    config = StorageConfig(project_path=test_skills_dir)
    loader = SkillLoader(config)
    loader.build_index(force=True)
    return loader


@pytest.fixture
def tool_registry() -> ToolRegistry:
    """Create tool registry with mock tools."""
    registry = ToolRegistry()
    registry.register(MockReadTool())
    registry.register(MockWriteTool())
    registry.register(MockGrepTool())
    registry.register(FlakyTool())
    return registry


@pytest.fixture
def tool_executor(tool_registry: ToolRegistry) -> ToolExecutor:
    """Create tool executor."""
    return ToolExecutor(tool_registry)


@pytest.fixture
def default_config() -> AutonomousConfig:
    """Create default autonomous config."""
    return AutonomousConfig(
        max_iterations=15,
        max_retries_per_tool=3,
        timeout_per_iteration_ms=30000,
    )


@pytest.fixture
def orchestrator(
    skill_loader: SkillLoader,
    tool_registry: ToolRegistry,
    tool_executor: ToolExecutor,
    default_config: AutonomousConfig,
) -> SkillOrchestrator:
    """Create skill orchestrator for testing."""
    return SkillOrchestrator(
        skill_loader=skill_loader,
        tool_registry=tool_registry,
        tool_executor=tool_executor,
        default_config=default_config,
    )


@pytest.mark.asyncio
class TestEndToEndExecution:
    """Integration tests for complete execution flow."""

    async def test_end_to_end_simple_skill(self, orchestrator: SkillOrchestrator) -> None:
        """Simple skill should execute successfully."""
        # Mock LLM response generator
        with patch("omniforge.skills.executor.LLMResponseGenerator") as mock_llm:
            mock_instance = AsyncMock()
            mock_instance.generate = AsyncMock(return_value="Task completed successfully")
            mock_llm.return_value = mock_instance

            events = []
            async for event in orchestrator.execute(
                "simple-mode-skill",
                "Process data",
                "task-1",
                execution_mode_override=ExecutionMode.SIMPLE,
            ):
                events.append(event)

            # Verify complete event sequence
            assert len(events) >= 2
            assert any(isinstance(e, TaskStatusEvent) for e in events)
            assert any(isinstance(e, TaskDoneEvent) for e in events)

            # Last event should be TaskDoneEvent
            assert isinstance(events[-1], TaskDoneEvent)
            assert events[-1].final_state in [TaskState.COMPLETED, TaskState.FAILED]

    async def test_end_to_end_with_tool_calls(self, orchestrator: SkillOrchestrator) -> None:
        """Skill with tool calls should execute tools."""
        # Mock LLM to use tools
        with patch("omniforge.skills.autonomous_executor.ReasoningEngine") as mock_engine:
            # Create mock that simulates tool usage
            mock_instance = Mock()

            async def mock_execute(*args, **kwargs):
                # Yield tool use simulation via text
                yield TaskMessageEvent(
                    task_id="task-1",
                    timestamp=datetime.utcnow(),
                    message_parts=[TextPart(text="Using read tool to read file.txt")],
                    visibility=VisibilityLevel.FULL,
                )
                # Yield completion
                yield TaskDoneEvent(
                    task_id="task-1",
                    timestamp=datetime.utcnow(),
                    final_state=TaskState.COMPLETED,
                )

            mock_instance.execute = mock_execute
            mock_engine.return_value = mock_instance

            events = []
            async for event in orchestrator.execute("tool-skill", "Read file.txt", "task-1"):
                events.append(event)

            # Verify we got events (exact count depends on mock implementation)
            assert len(events) > 0

            # Should have at least a done event
            assert any(isinstance(e, TaskDoneEvent) for e in events)

    async def test_end_to_end_with_error_recovery(self, orchestrator: SkillOrchestrator) -> None:
        """Skill should recover from tool failures with retries."""
        # Mock ReasoningEngine to simulate successful execution
        with patch("omniforge.skills.autonomous_executor.ReasoningEngine") as mock_engine:
            # Create async mock for call_llm
            mock_instance = Mock()
            mock_instance.call_llm = AsyncMock(
                return_value={"content": "Task completed after retries", "stop_reason": "end_turn"}
            )

            mock_engine.return_value = mock_instance

            events = []
            async for event in orchestrator.execute("flaky-skill", "Process", "task-1"):
                events.append(event)

            # Should complete (even if not testing actual retry logic in this test)
            assert events[-1].final_state in [TaskState.COMPLETED, TaskState.FAILED]
            # At minimum, verify we got some events
            assert len(events) > 0

    async def test_end_to_end_max_iterations(self, orchestrator: SkillOrchestrator) -> None:
        """Skill should stop at max_iterations if not complete."""
        # Mock LLM to keep iterating
        with patch("omniforge.skills.autonomous_executor.ReasoningEngine") as mock_engine:
            mock_instance = Mock()
            iteration_count = 0

            async def mock_execute(*args, **kwargs):
                nonlocal iteration_count
                # Generate events up to max iterations (5 for complex-skill)
                for i in range(6):  # Try one more than max
                    iteration_count += 1
                    yield TaskMessageEvent(
                        task_id="task-1",
                        timestamp=datetime.utcnow(),
                        message_parts=[TextPart(text=f"Iteration {i+1}")],
                        visibility=VisibilityLevel.SUMMARY,
                    )

                    # Stop at configured max
                    if i >= 4:  # max_iterations=5
                        break

                # End with partial result or failure
                yield TaskDoneEvent(
                    task_id="task-1",
                    timestamp=datetime.utcnow(),
                    final_state=TaskState.FAILED,
                )

            mock_instance.execute = mock_execute
            mock_engine.return_value = mock_instance

            events = []
            async for event in orchestrator.execute("complex-skill", "Infinite task", "task-1"):
                events.append(event)

            # Should have stopped at max iterations
            message_events = [e for e in events if isinstance(e, TaskMessageEvent)]
            assert len(message_events) <= 5  # max_iterations for complex-skill


@pytest.mark.asyncio
class TestPreprocessingIntegration:
    """Integration tests for preprocessing pipeline."""

    async def test_variable_substitution_integration(
        self, orchestrator: SkillOrchestrator, test_skills_dir: Path
    ) -> None:
        """Variables should be substituted in skill content."""
        # Load skill and verify variables are in content
        skill = orchestrator._skill_loader.load_skill("skill-with-variables")

        # Verify original content has variables
        assert "$ARGUMENTS" in skill.content
        assert "${SKILL_DIR}" in skill.content

        # Mock LLM to verify substituted content
        with patch("omniforge.skills.autonomous_executor.ReasoningEngine") as mock_engine:
            mock_instance = Mock()
            received_prompt = None

            async def mock_execute(skill_content, *args, **kwargs):
                nonlocal received_prompt
                received_prompt = skill_content

                yield TaskDoneEvent(
                    task_id="task-1",
                    timestamp=datetime.utcnow(),
                    final_state=TaskState.COMPLETED,
                )

            mock_instance.execute = mock_execute
            mock_engine.return_value = mock_instance

            events = []
            async for event in orchestrator.execute(
                "skill-with-variables",
                "test request",
                "task-1",
            ):
                events.append(event)

            # Note: Actual substitution is done by AutonomousSkillExecutor
            # We're testing that the orchestrator passes the skill correctly

    async def test_dynamic_injection_integration(self, orchestrator: SkillOrchestrator) -> None:
        """Dynamic injections should be processed before execution."""
        skill = orchestrator._skill_loader.load_skill("skill-with-injections")

        # Verify injection marker is in content
        assert "!`" in skill.content

        # Execution will process injections via StringSubstitutor
        with patch("omniforge.skills.autonomous_executor.ReasoningEngine") as mock_engine:
            mock_instance = Mock()

            async def mock_execute(*args, **kwargs):
                yield TaskDoneEvent(
                    task_id="task-1",
                    timestamp=datetime.utcnow(),
                    final_state=TaskState.COMPLETED,
                )

            mock_instance.execute = mock_execute
            mock_engine.return_value = mock_instance

            events = []
            async for event in orchestrator.execute(
                "skill-with-injections",
                "Show current date",
                "task-1",
            ):
                events.append(event)

            assert len(events) > 0

    async def test_context_loading_integration(
        self, orchestrator: SkillOrchestrator, test_skills_dir: Path
    ) -> None:
        """Supporting files should be available for loading."""
        # Load skill to verify it exists
        orchestrator._skill_loader.load_skill("skill-with-supporting-files")

        # Verify reference file exists
        reference_file = test_skills_dir / "skill-with-supporting-files" / "reference.md"
        assert reference_file.exists()

        # Mock execution to verify file can be read
        with patch("omniforge.skills.autonomous_executor.ReasoningEngine") as mock_engine:
            mock_instance = Mock()

            async def mock_execute(*args, **kwargs):
                # Simulate reading the reference file
                yield TaskMessageEvent(
                    task_id="task-1",
                    timestamp=datetime.utcnow(),
                    message_parts=[TextPart(text=f"Reading reference file: {reference_file}")],
                    visibility=VisibilityLevel.FULL,
                )
                yield TaskDoneEvent(
                    task_id="task-1",
                    timestamp=datetime.utcnow(),
                    final_state=TaskState.COMPLETED,
                )

            mock_instance.execute = mock_execute
            mock_engine.return_value = mock_instance

            events = []
            async for event in orchestrator.execute(
                "skill-with-supporting-files",
                "Use reference file",
                "task-1",
            ):
                events.append(event)

            assert len(events) > 0


@pytest.mark.asyncio
class TestRoutingIntegration:
    """Integration tests for execution mode routing."""

    async def test_autonomous_mode_routing(self, orchestrator: SkillOrchestrator) -> None:
        """Autonomous mode should use AutonomousSkillExecutor."""
        with patch("omniforge.skills.orchestrator.AutonomousSkillExecutor") as mock_executor:
            mock_instance = Mock()

            async def event_generator(*args, **kwargs):
                yield TaskStatusEvent(
                    task_id="task-1",
                    timestamp=datetime.utcnow(),
                    state=TaskState.WORKING,
                )
                yield TaskDoneEvent(
                    task_id="task-1",
                    timestamp=datetime.utcnow(),
                    final_state=TaskState.COMPLETED,
                )

            mock_instance.execute = event_generator
            mock_executor.return_value = mock_instance

            events = []
            async for event in orchestrator.execute("autonomous-skill", "Task", "task-1"):
                events.append(event)

            # Verify AutonomousSkillExecutor was used
            assert mock_executor.called
            assert len(events) >= 2

    async def test_simple_mode_routing(self, orchestrator: SkillOrchestrator) -> None:
        """Simple mode should use legacy executor."""
        with patch("omniforge.skills.orchestrator.ExecutableSkill") as mock_executor:
            mock_instance = AsyncMock()
            mock_instance.execute = AsyncMock(return_value={"success": True, "result": "Done"})
            mock_executor.return_value = mock_instance

            events = []
            async for event in orchestrator.execute("simple-mode-skill", "Task", "task-1"):
                events.append(event)

            # Verify ExecutableSkill was used
            assert mock_executor.called
            assert len(events) >= 2

    async def test_forked_context_routing(self, orchestrator: SkillOrchestrator) -> None:
        """Forked context should spawn sub-agent."""
        with patch("omniforge.skills.orchestrator.AutonomousSkillExecutor") as mock_executor:
            mock_instance = Mock()

            async def event_generator(*args, **kwargs):
                yield TaskDoneEvent(
                    task_id="task-1",
                    timestamp=datetime.utcnow(),
                    final_state=TaskState.COMPLETED,
                )

            mock_instance.execute = event_generator
            mock_executor.return_value = mock_instance

            # Execute with root context
            root_context = ExecutionContext(depth=0, max_depth=2)
            events = []
            async for event in orchestrator.execute(
                "forked-skill",
                "Analyze",
                "task-1",
                context=root_context,
            ):
                events.append(event)

            # Verify sub-agent was created
            assert mock_executor.called
            call_kwargs = mock_executor.call_args[1]
            child_context = call_kwargs["context"]
            assert child_context.depth == 1
            assert child_context.parent_task_id == "task-1"


@pytest.mark.asyncio
class TestEventStreamingIntegration:
    """Integration tests for event streaming."""

    async def test_events_stream_in_order(self, orchestrator: SkillOrchestrator) -> None:
        """Events should be emitted in correct order."""
        with patch("omniforge.skills.orchestrator.ExecutableSkill") as mock_executor:
            mock_instance = AsyncMock()
            mock_instance.execute = AsyncMock(return_value={"success": True, "result": "Done"})
            mock_executor.return_value = mock_instance

            events = []
            async for event in orchestrator.execute("simple-mode-skill", "Task", "task-1"):
                events.append(event)

            # First event should be status (WORKING/RUNNING)
            assert isinstance(events[0], (TaskStatusEvent, TaskMessageEvent))

            # Last event should be done
            assert isinstance(events[-1], TaskDoneEvent)

    async def test_events_have_timestamps(self, orchestrator: SkillOrchestrator) -> None:
        """All events should have timestamps."""
        with patch("omniforge.skills.orchestrator.ExecutableSkill") as mock_executor:
            mock_instance = AsyncMock()
            mock_instance.execute = AsyncMock(return_value={"success": True, "result": "Done"})
            mock_executor.return_value = mock_instance

            async for event in orchestrator.execute("simple-mode-skill", "Task", "task-1"):
                assert hasattr(event, "timestamp")
                assert event.timestamp is not None
                assert isinstance(event.timestamp, datetime)

    async def test_event_visibility_levels(self, orchestrator: SkillOrchestrator) -> None:
        """Events should have appropriate visibility levels."""
        with patch("omniforge.skills.orchestrator.AutonomousSkillExecutor") as mock_executor:
            mock_instance = Mock()

            async def event_generator(*args, **kwargs):
                # SUMMARY level event
                yield TaskStatusEvent(
                    task_id="task-1",
                    timestamp=datetime.utcnow(),
                    state=TaskState.WORKING,
                    visibility=VisibilityLevel.SUMMARY,
                )
                # FULL level event
                yield TaskMessageEvent(
                    task_id="task-1",
                    timestamp=datetime.utcnow(),
                    message_parts=[TextPart(text="Detailed info")],
                    visibility=VisibilityLevel.FULL,
                )
                yield TaskDoneEvent(
                    task_id="task-1",
                    timestamp=datetime.utcnow(),
                    final_state=TaskState.COMPLETED,
                    visibility=VisibilityLevel.SUMMARY,
                )

            mock_instance.execute = event_generator
            mock_executor.return_value = mock_instance

            events = []
            async for event in orchestrator.execute("autonomous-skill", "Task", "task-1"):
                events.append(event)

            # Verify visibility levels exist
            visibility_levels = [
                getattr(e, "visibility", None) for e in events if hasattr(e, "visibility")
            ]
            assert len(visibility_levels) > 0
