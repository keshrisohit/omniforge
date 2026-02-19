"""Tests for SkillOrchestrator routing logic."""

from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from omniforge.agents.events import TaskDoneEvent, TaskMessageEvent, TaskStatusEvent
from omniforge.agents.models import TextPart
from omniforge.skills.config import AutonomousConfig, ExecutionContext
from omniforge.skills.models import ContextMode, Skill, SkillMetadata
from omniforge.skills.orchestrator import ExecutionMode, SkillOrchestrator
from omniforge.tasks.models import TaskState


@pytest.fixture
def mock_skill_loader() -> MagicMock:
    """Create mock skill loader."""
    loader = MagicMock()
    return loader


@pytest.fixture
def mock_tool_registry() -> MagicMock:
    """Create mock tool registry."""
    registry = MagicMock()
    registry.list_tools = MagicMock(return_value=["read", "write", "bash"])
    return registry


@pytest.fixture
def mock_tool_executor() -> MagicMock:
    """Create mock tool executor."""
    executor = MagicMock()
    executor.activate_skill = MagicMock()
    executor.deactivate_skill = MagicMock()
    return executor


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
    mock_skill_loader: MagicMock,
    mock_tool_registry: MagicMock,
    mock_tool_executor: MagicMock,
    default_config: AutonomousConfig,
) -> SkillOrchestrator:
    """Create skill orchestrator for testing."""
    return SkillOrchestrator(
        skill_loader=mock_skill_loader,
        tool_registry=mock_tool_registry,
        tool_executor=mock_tool_executor,
        default_config=default_config,
    )


def create_test_skill(
    name: str = "test-skill",
    execution_mode: str | None = "autonomous",
    context: ContextMode = ContextMode.INHERIT,
    max_iterations: int | None = None,
) -> Skill:
    """Create a test skill for testing."""
    # Build metadata kwargs
    metadata_kwargs = {
        "name": name,
        "description": "Test skill",
        "context": context,
    }

    # Add optional fields only if not None
    if execution_mode is not None:
        metadata_kwargs["execution_mode"] = execution_mode
    if max_iterations is not None:
        metadata_kwargs["max_iterations"] = max_iterations

    metadata = SkillMetadata(**metadata_kwargs)
    return Skill(
        metadata=metadata,
        content="Test skill instructions",
        path=Path(f"/test/{name}/SKILL.md"),
        base_path=Path(f"/test/{name}"),
        storage_layer="test",
    )


class TestExecutionModeDetermination:
    """Tests for execution mode determination logic."""

    def test_determine_mode_with_override(self, orchestrator: SkillOrchestrator) -> None:
        """Override should take precedence over skill metadata."""
        skill = create_test_skill(execution_mode="autonomous")
        mode = orchestrator._determine_execution_mode(skill, ExecutionMode.SIMPLE)

        assert mode == ExecutionMode.SIMPLE

    def test_determine_mode_from_skill_metadata(self, orchestrator: SkillOrchestrator) -> None:
        """Should use skill metadata when no override."""
        skill = create_test_skill(execution_mode="simple")
        mode = orchestrator._determine_execution_mode(skill, None)

        assert mode == ExecutionMode.SIMPLE

    def test_determine_mode_defaults_to_autonomous(self, orchestrator: SkillOrchestrator) -> None:
        """Should default to autonomous when metadata is None."""
        skill = create_test_skill(execution_mode=None)
        mode = orchestrator._determine_execution_mode(skill, None)

        assert mode == ExecutionMode.AUTONOMOUS

    def test_determine_mode_handles_invalid_mode(self, orchestrator: SkillOrchestrator) -> None:
        """Should default to autonomous for invalid mode."""
        skill = create_test_skill(execution_mode="invalid-mode")
        mode = orchestrator._determine_execution_mode(skill, None)

        assert mode == ExecutionMode.AUTONOMOUS


class TestConfigurationBuilding:
    """Tests for configuration merging logic."""

    def test_build_config_uses_platform_defaults(self, orchestrator: SkillOrchestrator) -> None:
        """Should use platform defaults when skill metadata is empty."""
        skill = create_test_skill()
        config = orchestrator._build_config(skill)

        assert config.max_iterations == 15
        assert config.max_retries_per_tool == 3
        assert config.timeout_per_iteration_ms == 30000

    def test_build_config_skill_metadata_overrides(self, orchestrator: SkillOrchestrator) -> None:
        """Skill metadata should override platform defaults."""
        skill = create_test_skill(max_iterations=20)
        config = orchestrator._build_config(skill)

        assert config.max_iterations == 20
        assert config.max_retries_per_tool == 3  # Still uses default

    def test_parse_timeout_seconds(self, orchestrator: SkillOrchestrator) -> None:
        """Should parse timeout in seconds."""
        assert orchestrator._parse_timeout("30s") == 30000
        assert orchestrator._parse_timeout("5s") == 5000

    def test_parse_timeout_minutes(self, orchestrator: SkillOrchestrator) -> None:
        """Should parse timeout in minutes."""
        assert orchestrator._parse_timeout("1m") == 60000
        assert orchestrator._parse_timeout("5m") == 300000

    def test_parse_timeout_milliseconds(self, orchestrator: SkillOrchestrator) -> None:
        """Should parse timeout in milliseconds."""
        assert orchestrator._parse_timeout("30000ms") == 30000

    def test_parse_timeout_invalid(self, orchestrator: SkillOrchestrator) -> None:
        """Should return None for invalid timeout."""
        assert orchestrator._parse_timeout("invalid") is None
        assert orchestrator._parse_timeout("") is None


@pytest.mark.asyncio
class TestAutonomousExecution:
    """Tests for autonomous execution path."""

    async def test_routes_to_autonomous_executor(
        self,
        orchestrator: SkillOrchestrator,
        mock_skill_loader: MagicMock,
        mock_tool_executor: MagicMock,
    ) -> None:
        """Autonomous mode should use AutonomousSkillExecutor."""
        skill = create_test_skill(execution_mode="autonomous")
        mock_skill_loader.load_skill = MagicMock(return_value=skill)

        # Mock AutonomousSkillExecutor to return test events
        with patch("omniforge.skills.orchestrator.AutonomousSkillExecutor") as mock_executor:
            # Create async generator for events
            async def event_generator(*args, **kwargs):
                yield TaskStatusEvent(
                    task_id="task-1", timestamp=datetime.utcnow(), state=TaskState.WORKING
                )
                yield TaskMessageEvent(
                    task_id="task-1",
                    timestamp=datetime.utcnow(),
                    message_parts=[TextPart(text="Processing...")],
                )
                yield TaskDoneEvent(
                    task_id="task-1", timestamp=datetime.utcnow(), final_state=TaskState.COMPLETED
                )

            mock_instance = MagicMock()
            mock_instance.execute = event_generator
            mock_executor.return_value = mock_instance

            # Execute skill
            events = []
            async for event in orchestrator.execute("test-skill", "Process data", "task-1"):
                events.append(event)

            # Verify events
            assert len(events) == 3
            assert isinstance(events[0], TaskStatusEvent)
            assert isinstance(events[1], TaskMessageEvent)
            assert isinstance(events[2], TaskDoneEvent)

            # Verify skill context was activated and deactivated
            mock_tool_executor.activate_skill.assert_called_once_with(skill)
            mock_tool_executor.deactivate_skill.assert_called_once_with("test-skill")

    async def test_autonomous_deactivates_on_error(
        self,
        orchestrator: SkillOrchestrator,
        mock_skill_loader: MagicMock,
        mock_tool_executor: MagicMock,
    ) -> None:
        """Should deactivate skill context even on error."""
        skill = create_test_skill(execution_mode="autonomous")
        mock_skill_loader.load_skill = MagicMock(return_value=skill)

        # Mock executor that raises error
        with patch("omniforge.skills.orchestrator.AutonomousSkillExecutor") as mock_executor:

            async def failing_generator(*args, **kwargs):
                yield TaskStatusEvent(
                    task_id="task-1", timestamp=datetime.utcnow(), state=TaskState.WORKING
                )
                raise RuntimeError("Test error")

            mock_instance = MagicMock()
            mock_instance.execute = failing_generator
            mock_executor.return_value = mock_instance

            # Execute and expect error propagation
            with pytest.raises(RuntimeError):
                async for event in orchestrator.execute("test-skill", "Process data", "task-1"):
                    pass

            # Verify skill was deactivated despite error
            mock_tool_executor.activate_skill.assert_called_once_with(skill)
            mock_tool_executor.deactivate_skill.assert_called_once_with("test-skill")


@pytest.mark.asyncio
class TestSimpleExecution:
    """Tests for simple execution path."""

    async def test_routes_to_simple_executor(
        self,
        orchestrator: SkillOrchestrator,
        mock_skill_loader: MagicMock,
    ) -> None:
        """Simple mode should use ExecutableSkill."""
        skill = create_test_skill(execution_mode="simple")
        mock_skill_loader.load_skill = MagicMock(return_value=skill)

        # Mock ExecutableSkill
        with patch("omniforge.skills.orchestrator.ExecutableSkill") as mock_executor:
            mock_instance = AsyncMock()
            mock_instance.execute = AsyncMock(
                return_value={"success": True, "result": "Task completed"}
            )
            mock_executor.return_value = mock_instance

            # Execute skill
            events = []
            async for event in orchestrator.execute(
                "test-skill", "Process data", "task-1", execution_mode_override=ExecutionMode.SIMPLE
            ):
                events.append(event)

            # Verify events
            assert len(events) == 3
            assert isinstance(events[0], TaskStatusEvent)
            assert isinstance(events[1], TaskMessageEvent)
            assert isinstance(events[2], TaskDoneEvent)
            assert events[2].final_state == TaskState.COMPLETED

    async def test_simple_execution_handles_failure(
        self,
        orchestrator: SkillOrchestrator,
        mock_skill_loader: MagicMock,
    ) -> None:
        """Should handle simple execution failures gracefully."""
        skill = create_test_skill(execution_mode="simple")
        mock_skill_loader.load_skill = MagicMock(return_value=skill)

        # Mock ExecutableSkill that returns failure
        with patch("omniforge.skills.orchestrator.ExecutableSkill") as mock_executor:
            mock_instance = AsyncMock()
            mock_instance.execute = AsyncMock(
                return_value={"success": False, "result": "Task failed"}
            )
            mock_executor.return_value = mock_instance

            # Execute skill
            events = []
            async for event in orchestrator.execute("test-skill", "Process data", "task-1"):
                events.append(event)

            # Verify failed state
            assert events[-1].final_state == TaskState.FAILED

    async def test_simple_execution_handles_exception(
        self,
        orchestrator: SkillOrchestrator,
        mock_skill_loader: MagicMock,
    ) -> None:
        """Should handle exceptions in simple execution."""
        skill = create_test_skill(execution_mode="simple")
        mock_skill_loader.load_skill = MagicMock(return_value=skill)

        # Mock ExecutableSkill that raises exception
        with patch("omniforge.skills.orchestrator.ExecutableSkill") as mock_executor:
            mock_instance = AsyncMock()
            mock_instance.execute = AsyncMock(side_effect=RuntimeError("Test error"))
            mock_executor.return_value = mock_instance

            # Execute skill
            events = []
            async for event in orchestrator.execute("test-skill", "Process data", "task-1"):
                events.append(event)

            # Verify error handling
            assert len(events) == 3
            assert isinstance(events[1], TaskMessageEvent)
            assert "Execution failed" in events[1].message_parts[0].text
            assert events[-1].final_state == TaskState.FAILED


@pytest.mark.asyncio
class TestForkedContextExecution:
    """Tests for forked context (sub-agent) execution."""

    async def test_forked_context_spawns_sub_agent(
        self,
        orchestrator: SkillOrchestrator,
        mock_skill_loader: MagicMock,
    ) -> None:
        """Skills with context: fork should spawn sub-agent."""
        skill = create_test_skill(context=ContextMode.FORK, execution_mode="autonomous")
        mock_skill_loader.load_skill = MagicMock(return_value=skill)

        # Mock AutonomousSkillExecutor
        with patch("omniforge.skills.orchestrator.AutonomousSkillExecutor") as mock_executor:

            async def event_generator(*args, **kwargs):
                yield TaskDoneEvent(
                    task_id="task-1", timestamp=datetime.utcnow(), final_state=TaskState.COMPLETED
                )

            mock_instance = MagicMock()
            mock_instance.execute = event_generator
            mock_executor.return_value = mock_instance

            # Execute with root context
            root_context = ExecutionContext(depth=0, max_depth=2)
            events = []
            async for event in orchestrator.execute(
                "test-skill", "Process data", "task-1", context=root_context
            ):
                events.append(event)

            # Verify sub-agent was created with reduced budget
            assert mock_executor.called
            call_kwargs = mock_executor.call_args[1]
            child_context = call_kwargs["context"]
            assert child_context.depth == 1
            assert child_context.parent_task_id == "task-1"

    async def test_forked_context_respects_depth_limit(
        self,
        orchestrator: SkillOrchestrator,
        mock_skill_loader: MagicMock,
    ) -> None:
        """Should fail when max depth is exceeded."""
        skill = create_test_skill(context=ContextMode.FORK)
        mock_skill_loader.load_skill = MagicMock(return_value=skill)

        # Create context at max depth
        max_depth_context = ExecutionContext(depth=2, max_depth=2)

        # Execute and expect failure
        events = []
        async for event in orchestrator.execute(
            "test-skill", "Process data", "task-1", context=max_depth_context
        ):
            events.append(event)

        # Verify error message and failed state
        assert len(events) == 2
        assert isinstance(events[0], TaskMessageEvent)
        assert "maximum depth" in events[0].message_parts[0].text.lower()
        assert events[-1].final_state == TaskState.FAILED

    async def test_forked_context_reduces_iteration_budget(
        self,
        orchestrator: SkillOrchestrator,
        mock_skill_loader: MagicMock,
    ) -> None:
        """Sub-agents should have reduced iteration budget."""
        skill = create_test_skill(
            context=ContextMode.FORK, execution_mode="autonomous", max_iterations=20
        )
        mock_skill_loader.load_skill = MagicMock(return_value=skill)

        # Mock AutonomousSkillExecutor
        with patch("omniforge.skills.orchestrator.AutonomousSkillExecutor") as mock_executor:

            async def event_generator(*args, **kwargs):
                yield TaskDoneEvent(
                    task_id="task-1", timestamp=datetime.utcnow(), final_state=TaskState.COMPLETED
                )

            mock_instance = MagicMock()
            mock_instance.execute = event_generator
            mock_executor.return_value = mock_instance

            # Execute with root context
            root_context = ExecutionContext(depth=0, max_depth=2)
            events = []
            async for event in orchestrator.execute(
                "test-skill", "Process data", "task-1", context=root_context
            ):
                events.append(event)

            # Verify reduced iteration budget (20 / 2 = 10)
            call_kwargs = mock_executor.call_args[1]
            config = call_kwargs["config"]
            assert config.max_iterations == 10


@pytest.mark.asyncio
class TestExecutionModeOverride:
    """Tests for execution mode override functionality."""

    async def test_execution_mode_override_works(
        self,
        orchestrator: SkillOrchestrator,
        mock_skill_loader: MagicMock,
    ) -> None:
        """Override should force specific execution mode."""
        # Create autonomous skill
        skill = create_test_skill(execution_mode="autonomous")
        mock_skill_loader.load_skill = MagicMock(return_value=skill)

        # Mock ExecutableSkill (simple mode)
        with patch("omniforge.skills.orchestrator.ExecutableSkill") as mock_executor:
            mock_instance = AsyncMock()
            mock_instance.execute = AsyncMock(
                return_value={"success": True, "result": "Task completed"}
            )
            mock_executor.return_value = mock_instance

            # Execute with SIMPLE override
            events = []
            async for event in orchestrator.execute(
                "test-skill",
                "Process data",
                "task-1",
                execution_mode_override=ExecutionMode.SIMPLE,
            ):
                events.append(event)

            # Verify simple executor was used despite autonomous metadata
            mock_executor.assert_called_once()


@pytest.mark.asyncio
class TestIntegration:
    """Integration tests for complete orchestration flow."""

    async def test_complete_autonomous_flow(
        self,
        orchestrator: SkillOrchestrator,
        mock_skill_loader: MagicMock,
        mock_tool_executor: MagicMock,
    ) -> None:
        """Test complete flow with autonomous execution."""
        skill = create_test_skill(execution_mode="autonomous", max_iterations=10)
        mock_skill_loader.load_skill = MagicMock(return_value=skill)

        with patch("omniforge.skills.orchestrator.AutonomousSkillExecutor") as mock_executor:

            async def event_generator(*args, **kwargs):
                yield TaskStatusEvent(
                    task_id="task-1", timestamp=datetime.utcnow(), state=TaskState.WORKING
                )
                yield TaskMessageEvent(
                    task_id="task-1",
                    timestamp=datetime.utcnow(),
                    message_parts=[TextPart(text="Step 1")],
                )
                yield TaskMessageEvent(
                    task_id="task-1",
                    timestamp=datetime.utcnow(),
                    message_parts=[TextPart(text="Step 2")],
                )
                yield TaskDoneEvent(
                    task_id="task-1", timestamp=datetime.utcnow(), final_state=TaskState.COMPLETED
                )

            mock_instance = MagicMock()
            mock_instance.execute = event_generator
            mock_executor.return_value = mock_instance

            # Execute
            events = []
            async for event in orchestrator.execute(
                skill_name="test-skill",
                user_request="Process my data",
                task_id="task-1",
                session_id="session-1",
                tenant_id="tenant-1",
            ):
                events.append(event)

            # Verify complete flow
            assert len(events) == 4
            assert mock_tool_executor.activate_skill.called
            assert mock_tool_executor.deactivate_skill.called

            # Verify config was built correctly
            call_kwargs = mock_executor.call_args[1]
            config = call_kwargs["config"]
            assert config.max_iterations == 10
