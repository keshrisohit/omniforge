"""Tests for autonomous skill execution configuration and state models."""

import os
from datetime import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from omniforge.skills.config import (
    AutonomousConfig,
    ExecutionContext,
    ExecutionMetrics,
    ExecutionResult,
    ExecutionState,
    PlatformAutonomousConfig,
    is_valid_duration,
    merge_configs,
    parse_duration_ms,
    validate_skill_config,
)
from omniforge.skills.models import SkillMetadata


class TestExecutionContext:
    """Tests for ExecutionContext model."""

    def test_default_initialization(self) -> None:
        """ExecutionContext should initialize with correct defaults."""
        context = ExecutionContext()

        assert context.depth == 0
        assert context.max_depth == 2
        assert context.parent_task_id is None
        assert context.root_task_id is None
        assert context.skill_chain == []

    def test_custom_initialization(self) -> None:
        """ExecutionContext should accept custom values."""
        context = ExecutionContext(
            depth=1,
            max_depth=3,
            parent_task_id="parent-123",
            root_task_id="root-456",
            skill_chain=["skill-a", "skill-b"],
        )

        assert context.depth == 1
        assert context.max_depth == 3
        assert context.parent_task_id == "parent-123"
        assert context.root_task_id == "root-456"
        assert context.skill_chain == ["skill-a", "skill-b"]

    def test_can_spawn_sub_agent_at_root(self) -> None:
        """Root context should be able to spawn sub-agent."""
        context = ExecutionContext(depth=0, max_depth=2)
        assert context.can_spawn_sub_agent() is True

    def test_can_spawn_sub_agent_at_depth_1(self) -> None:
        """Depth 1 context should be able to spawn sub-agent if max_depth is 2."""
        context = ExecutionContext(depth=1, max_depth=2)
        assert context.can_spawn_sub_agent() is True

    def test_cannot_spawn_sub_agent_at_max_depth(self) -> None:
        """Context at max depth should not be able to spawn sub-agent."""
        context = ExecutionContext(depth=2, max_depth=2)
        assert context.can_spawn_sub_agent() is False

    def test_create_child_context_increments_depth(self) -> None:
        """Creating child context should increment depth."""
        parent = ExecutionContext(depth=0, max_depth=2)
        child = parent.create_child_context("task-123")

        assert child.depth == 1
        assert child.parent_task_id == "task-123"
        assert child.max_depth == 2

    def test_create_child_context_sets_root_task_id(self) -> None:
        """Creating child context should set root_task_id if not already set."""
        parent = ExecutionContext(depth=0, max_depth=2)
        child = parent.create_child_context("task-123")

        assert child.root_task_id == "task-123"

    def test_create_child_context_preserves_root_task_id(self) -> None:
        """Creating child context should preserve existing root_task_id."""
        parent = ExecutionContext(depth=0, max_depth=2, root_task_id="root-task")
        child = parent.create_child_context("task-123")

        assert child.root_task_id == "root-task"
        assert child.parent_task_id == "task-123"

    def test_create_child_context_builds_skill_chain(self) -> None:
        """Creating child context should build skill chain."""
        parent = ExecutionContext(depth=0, max_depth=2, skill_chain=["skill-a"])
        child = parent.create_child_context("task-123", skill_name="skill-b")

        assert child.skill_chain == ["skill-a", "skill-b"]

    def test_create_child_context_skill_chain_without_skill_name(self) -> None:
        """Creating child context without skill_name should preserve chain."""
        parent = ExecutionContext(depth=0, max_depth=2, skill_chain=["skill-a"])
        child = parent.create_child_context("task-123")

        assert child.skill_chain == ["skill-a"]

    def test_create_child_context_at_max_depth_raises_error(self) -> None:
        """Creating child context at max depth should raise ValueError."""
        context = ExecutionContext(depth=2, max_depth=2, skill_chain=["skill-a", "skill-b"])

        with pytest.raises(ValueError) as exc_info:
            context.create_child_context("task-123")

        error_message = str(exc_info.value)
        assert "Maximum sub-agent depth (2) exceeded" in error_message
        assert "Cannot spawn sub-agent at depth 2" in error_message
        assert "skill-a -> skill-b" in error_message

    def test_create_grandchild_context(self) -> None:
        """Creating grandchild context should work within limits."""
        root = ExecutionContext(depth=0, max_depth=2)
        child = root.create_child_context("task-1", skill_name="skill-a")
        grandchild = child.create_child_context("task-2", skill_name="skill-b")

        assert grandchild.depth == 2
        assert grandchild.parent_task_id == "task-2"
        assert grandchild.root_task_id == "task-1"
        assert grandchild.skill_chain == ["skill-a", "skill-b"]
        assert grandchild.can_spawn_sub_agent() is False

    def test_create_great_grandchild_context_raises_error(self) -> None:
        """Creating great-grandchild context should raise ValueError."""
        root = ExecutionContext(depth=0, max_depth=2)
        child = root.create_child_context("task-1", skill_name="skill-a")
        grandchild = child.create_child_context("task-2", skill_name="skill-b")

        with pytest.raises(ValueError) as exc_info:
            grandchild.create_child_context("task-3", skill_name="skill-c")

        error_message = str(exc_info.value)
        assert "Maximum sub-agent depth (2) exceeded" in error_message

    def test_depth_validation(self) -> None:
        """ExecutionContext should reject negative depth values."""
        with pytest.raises(ValidationError) as exc_info:
            ExecutionContext(depth=-1)

        errors = exc_info.value.errors()
        assert any("greater than or equal to 0" in str(error) for error in errors)

    def test_max_depth_validation(self) -> None:
        """ExecutionContext should reject negative max_depth values."""
        with pytest.raises(ValidationError) as exc_info:
            ExecutionContext(max_depth=-1)

        errors = exc_info.value.errors()
        assert any("greater than or equal to 0" in str(error) for error in errors)

    def test_get_iteration_budget_for_child_at_root(self) -> None:
        """Root context should give child 50% of base iterations."""
        context = ExecutionContext(depth=0)
        budget = context.get_iteration_budget_for_child(base_iterations=16)
        # Child will be at depth 1: 16 // (2^1) = 8
        assert budget == 8

    def test_get_iteration_budget_for_child_at_depth_1(self) -> None:
        """Depth 1 context should give child 25% of base iterations."""
        context = ExecutionContext(depth=1)
        budget = context.get_iteration_budget_for_child(base_iterations=16)
        # Child will be at depth 2: 16 // (2^2) = 4
        assert budget == 4

    def test_get_iteration_budget_for_child_minimum(self) -> None:
        """Iteration budget should have minimum of 3."""
        context = ExecutionContext(depth=2)
        budget = context.get_iteration_budget_for_child(base_iterations=4)
        # Child would be at depth 3: 4 // (2^3) = 0, but minimum is 3
        assert budget == 3

    def test_get_iteration_budget_for_child_with_small_base(self) -> None:
        """Small base iterations should still give minimum budget."""
        context = ExecutionContext(depth=0)
        budget = context.get_iteration_budget_for_child(base_iterations=5)
        # Child at depth 1: 5 // 2 = 2, but minimum is 3
        assert budget == 3

    def test_skill_chain_is_mutable_copy(self) -> None:
        """Child context should have independent skill chain."""
        parent = ExecutionContext(skill_chain=["skill-a"])
        child = parent.create_child_context("task-123", skill_name="skill-b")

        # Modify parent chain
        parent.skill_chain.append("skill-c")

        # Child chain should not be affected
        assert child.skill_chain == ["skill-a", "skill-b"]
        assert parent.skill_chain == ["skill-a", "skill-c"]

    def test_context_at_boundary_max_depth_zero(self) -> None:
        """Context with max_depth=0 should not allow any sub-agents."""
        context = ExecutionContext(depth=0, max_depth=0)
        assert context.can_spawn_sub_agent() is False

        with pytest.raises(ValueError):
            context.create_child_context("task-123")

    def test_context_with_high_max_depth(self) -> None:
        """Context with high max_depth should work correctly."""
        context = ExecutionContext(depth=0, max_depth=5)
        assert context.can_spawn_sub_agent() is True

        # Should be able to create multiple levels
        child1 = context.create_child_context("task-1")
        assert child1.depth == 1
        assert child1.can_spawn_sub_agent() is True

        child2 = child1.create_child_context("task-2")
        assert child2.depth == 2
        assert child2.can_spawn_sub_agent() is True


class TestAutonomousConfig:
    """Tests for AutonomousConfig model."""

    def test_default_values(self) -> None:
        """AutonomousConfig should initialize with correct default values."""
        config = AutonomousConfig()

        assert config.max_iterations == 15
        assert config.max_retries_per_tool == 3
        assert config.timeout_per_iteration_ms == 30000
        assert config.early_termination is True
        assert config.model is None
        assert config.temperature == 0.0
        assert config.enable_error_recovery is True

    def test_custom_values(self) -> None:
        """AutonomousConfig should accept custom values."""
        config = AutonomousConfig(
            max_iterations=10,
            max_retries_per_tool=5,
            timeout_per_iteration_ms=60000,
            early_termination=False,
            model="gpt-4",
            temperature=0.7,
            enable_error_recovery=False,
        )

        assert config.max_iterations == 10
        assert config.max_retries_per_tool == 5
        assert config.timeout_per_iteration_ms == 60000
        assert config.early_termination is False
        assert config.model == "gpt-4"
        assert config.temperature == 0.7
        assert config.enable_error_recovery is False

    def test_max_iterations_validation_minimum(self) -> None:
        """AutonomousConfig should reject max_iterations less than 1."""
        with pytest.raises(ValidationError) as exc_info:
            AutonomousConfig(max_iterations=0)

        errors = exc_info.value.errors()
        assert any("greater than or equal to 1" in str(error) for error in errors)

    def test_max_iterations_validation_maximum(self) -> None:
        """AutonomousConfig should reject max_iterations greater than 100."""
        with pytest.raises(ValidationError) as exc_info:
            AutonomousConfig(max_iterations=101)

        errors = exc_info.value.errors()
        assert any("less than or equal to 100" in str(error) for error in errors)

    def test_max_retries_per_tool_validation_minimum(self) -> None:
        """AutonomousConfig should reject max_retries_per_tool less than 1."""
        with pytest.raises(ValidationError) as exc_info:
            AutonomousConfig(max_retries_per_tool=0)

        errors = exc_info.value.errors()
        assert any("greater than or equal to 1" in str(error) for error in errors)

    def test_max_retries_per_tool_validation_maximum(self) -> None:
        """AutonomousConfig should reject max_retries_per_tool greater than 10."""
        with pytest.raises(ValidationError) as exc_info:
            AutonomousConfig(max_retries_per_tool=11)

        errors = exc_info.value.errors()
        assert any("less than or equal to 10" in str(error) for error in errors)

    def test_timeout_per_iteration_ms_validation_minimum(self) -> None:
        """AutonomousConfig should reject timeout_per_iteration_ms less than 1000."""
        with pytest.raises(ValidationError) as exc_info:
            AutonomousConfig(timeout_per_iteration_ms=999)

        errors = exc_info.value.errors()
        assert any("greater than or equal to 1000" in str(error) for error in errors)

    def test_timeout_per_iteration_ms_validation_maximum(self) -> None:
        """AutonomousConfig should reject timeout_per_iteration_ms greater than 300000."""
        with pytest.raises(ValidationError) as exc_info:
            AutonomousConfig(timeout_per_iteration_ms=300001)

        errors = exc_info.value.errors()
        assert any("less than or equal to 300000" in str(error) for error in errors)

    def test_temperature_validation_minimum(self) -> None:
        """AutonomousConfig should reject temperature less than 0.0."""
        with pytest.raises(ValidationError) as exc_info:
            AutonomousConfig(temperature=-0.1)

        errors = exc_info.value.errors()
        assert any("greater than or equal to 0" in str(error) for error in errors)

    def test_temperature_validation_maximum(self) -> None:
        """AutonomousConfig should reject temperature greater than 2.0."""
        with pytest.raises(ValidationError) as exc_info:
            AutonomousConfig(temperature=2.1)

        errors = exc_info.value.errors()
        assert any("less than or equal to 2" in str(error) for error in errors)

    def test_boundary_values(self) -> None:
        """AutonomousConfig should accept valid boundary values."""
        config = AutonomousConfig(
            max_iterations=1,
            max_retries_per_tool=1,
            timeout_per_iteration_ms=1000,
            temperature=0.0,
        )
        assert config.max_iterations == 1
        assert config.max_retries_per_tool == 1
        assert config.timeout_per_iteration_ms == 1000
        assert config.temperature == 0.0

        config = AutonomousConfig(
            max_iterations=100,
            max_retries_per_tool=10,
            timeout_per_iteration_ms=300000,
            temperature=2.0,
        )
        assert config.max_iterations == 100
        assert config.max_retries_per_tool == 10
        assert config.timeout_per_iteration_ms == 300000
        assert config.temperature == 2.0


class TestExecutionState:
    """Tests for ExecutionState model."""

    def test_default_initialization(self) -> None:
        """ExecutionState should initialize with correct defaults."""
        state = ExecutionState()

        assert state.iteration == 0
        assert state.observations == []
        assert state.failed_approaches == {}
        assert state.loaded_files == set()
        assert state.partial_results == []
        assert state.error_count == 0
        assert isinstance(state.start_time, datetime)

    def test_custom_initialization(self) -> None:
        """ExecutionState should accept custom values."""
        start = datetime(2024, 1, 1, 12, 0, 0)
        state = ExecutionState(
            iteration=5,
            observations=[{"tool": "read", "result": "data"}],
            failed_approaches={"approach_a": 2},
            loaded_files={"file1.txt", "file2.txt"},
            partial_results=["result1", "result2"],
            error_count=3,
            start_time=start,
        )

        assert state.iteration == 5
        assert state.observations == [{"tool": "read", "result": "data"}]
        assert state.failed_approaches == {"approach_a": 2}
        assert state.loaded_files == {"file1.txt", "file2.txt"}
        assert state.partial_results == ["result1", "result2"]
        assert state.error_count == 3
        assert state.start_time == start

    def test_iteration_validation(self) -> None:
        """ExecutionState should reject negative iteration values."""
        with pytest.raises(ValidationError) as exc_info:
            ExecutionState(iteration=-1)

        errors = exc_info.value.errors()
        assert any("greater than or equal to 0" in str(error) for error in errors)

    def test_error_count_validation(self) -> None:
        """ExecutionState should reject negative error_count values."""
        with pytest.raises(ValidationError) as exc_info:
            ExecutionState(error_count=-1)

        errors = exc_info.value.errors()
        assert any("greater than or equal to 0" in str(error) for error in errors)

    def test_mutable_collections(self) -> None:
        """ExecutionState should properly handle mutable collections."""
        state1 = ExecutionState()
        state2 = ExecutionState()

        # Modify state1
        state1.observations.append({"test": "data"})
        state1.failed_approaches["test"] = 1
        state1.loaded_files.add("test.txt")
        state1.partial_results.append("test")

        # state2 should not be affected
        assert state2.observations == []
        assert state2.failed_approaches == {}
        assert state2.loaded_files == set()
        assert state2.partial_results == []

    def test_failed_approaches_tracking(self) -> None:
        """ExecutionState should track failed approaches with retry counts."""
        state = ExecutionState()

        # Add failed approaches
        state.failed_approaches["approach_a"] = 1
        state.failed_approaches["approach_b"] = 3
        state.failed_approaches["approach_a"] = 2  # Update count

        assert state.failed_approaches["approach_a"] == 2
        assert state.failed_approaches["approach_b"] == 3
        assert len(state.failed_approaches) == 2


class TestExecutionMetrics:
    """Tests for ExecutionMetrics model."""

    def test_default_initialization(self) -> None:
        """ExecutionMetrics should initialize with zero values."""
        metrics = ExecutionMetrics()

        assert metrics.total_tokens == 0
        assert metrics.prompt_tokens == 0
        assert metrics.completion_tokens == 0
        assert metrics.total_cost == 0.0
        assert metrics.duration_seconds == 0.0
        assert metrics.tool_calls_successful == 0
        assert metrics.tool_calls_failed == 0
        assert metrics.error_recoveries == 0

    def test_custom_values(self) -> None:
        """ExecutionMetrics should accept custom values."""
        metrics = ExecutionMetrics(
            total_tokens=1000,
            prompt_tokens=600,
            completion_tokens=400,
            total_cost=0.05,
            duration_seconds=12.5,
            tool_calls_successful=5,
            tool_calls_failed=2,
            error_recoveries=1,
        )

        assert metrics.total_tokens == 1000
        assert metrics.prompt_tokens == 600
        assert metrics.completion_tokens == 400
        assert metrics.total_cost == 0.05
        assert metrics.duration_seconds == 12.5
        assert metrics.tool_calls_successful == 5
        assert metrics.tool_calls_failed == 2
        assert metrics.error_recoveries == 1

    def test_negative_values_validation(self) -> None:
        """ExecutionMetrics should reject negative values for all fields."""
        # Test total_tokens
        with pytest.raises(ValidationError):
            ExecutionMetrics(total_tokens=-1)

        # Test prompt_tokens
        with pytest.raises(ValidationError):
            ExecutionMetrics(prompt_tokens=-1)

        # Test completion_tokens
        with pytest.raises(ValidationError):
            ExecutionMetrics(completion_tokens=-1)

        # Test total_cost
        with pytest.raises(ValidationError):
            ExecutionMetrics(total_cost=-0.01)

        # Test duration_seconds
        with pytest.raises(ValidationError):
            ExecutionMetrics(duration_seconds=-1.0)

        # Test tool_calls_successful
        with pytest.raises(ValidationError):
            ExecutionMetrics(tool_calls_successful=-1)

        # Test tool_calls_failed
        with pytest.raises(ValidationError):
            ExecutionMetrics(tool_calls_failed=-1)

        # Test error_recoveries
        with pytest.raises(ValidationError):
            ExecutionMetrics(error_recoveries=-1)

    def test_token_calculation(self) -> None:
        """ExecutionMetrics should allow independent token tracking."""
        metrics = ExecutionMetrics(
            prompt_tokens=300,
            completion_tokens=200,
            total_tokens=500,
        )

        assert metrics.total_tokens == 500
        assert metrics.prompt_tokens == 300
        assert metrics.completion_tokens == 200


class TestExecutionResult:
    """Tests for ExecutionResult model."""

    def test_successful_result(self) -> None:
        """ExecutionResult should represent successful execution."""
        metrics = ExecutionMetrics(
            total_tokens=500,
            total_cost=0.02,
            tool_calls_successful=3,
        )

        result = ExecutionResult(
            success=True,
            result="Task completed successfully",
            iterations_used=5,
            chain_id="chain-123",
            metrics=metrics,
        )

        assert result.success is True
        assert result.result == "Task completed successfully"
        assert result.iterations_used == 5
        assert result.chain_id == "chain-123"
        assert result.metrics.total_tokens == 500
        assert result.partial_results == []
        assert result.error is None

    def test_failed_result(self) -> None:
        """ExecutionResult should represent failed execution."""
        metrics = ExecutionMetrics(
            total_tokens=300,
            tool_calls_failed=2,
        )

        result = ExecutionResult(
            success=False,
            result="Execution incomplete",
            iterations_used=3,
            chain_id="chain-456",
            metrics=metrics,
            partial_results=["step1", "step2"],
            error="Maximum iterations exceeded",
        )

        assert result.success is False
        assert result.result == "Execution incomplete"
        assert result.iterations_used == 3
        assert result.chain_id == "chain-456"
        assert result.metrics.tool_calls_failed == 2
        assert result.partial_results == ["step1", "step2"]
        assert result.error == "Maximum iterations exceeded"

    def test_iterations_used_validation(self) -> None:
        """ExecutionResult should reject negative iterations_used."""
        metrics = ExecutionMetrics()

        with pytest.raises(ValidationError) as exc_info:
            ExecutionResult(
                success=True,
                result="test",
                iterations_used=-1,
                chain_id="chain-123",
                metrics=metrics,
            )

        errors = exc_info.value.errors()
        assert any("greater than or equal to 0" in str(error) for error in errors)

    def test_required_fields(self) -> None:
        """ExecutionResult should require all mandatory fields."""
        # Missing success
        with pytest.raises(ValidationError):
            ExecutionResult(
                result="test",
                iterations_used=1,
                chain_id="chain-123",
                metrics=ExecutionMetrics(),
            )

        # Missing result
        with pytest.raises(ValidationError):
            ExecutionResult(
                success=True,
                iterations_used=1,
                chain_id="chain-123",
                metrics=ExecutionMetrics(),
            )

        # Missing iterations_used
        with pytest.raises(ValidationError):
            ExecutionResult(
                success=True,
                result="test",
                chain_id="chain-123",
                metrics=ExecutionMetrics(),
            )

        # Missing chain_id
        with pytest.raises(ValidationError):
            ExecutionResult(
                success=True,
                result="test",
                iterations_used=1,
                metrics=ExecutionMetrics(),
            )

        # Missing metrics
        with pytest.raises(ValidationError):
            ExecutionResult(
                success=True,
                result="test",
                iterations_used=1,
                chain_id="chain-123",
            )

    def test_partial_results_with_success(self) -> None:
        """ExecutionResult should allow partial_results even on success."""
        result = ExecutionResult(
            success=True,
            result="Final result",
            iterations_used=5,
            chain_id="chain-789",
            metrics=ExecutionMetrics(),
            partial_results=["intermediate1", "intermediate2"],
        )

        assert result.success is True
        assert len(result.partial_results) == 2

    def test_json_serialization(self) -> None:
        """ExecutionResult should be JSON serializable."""
        result = ExecutionResult(
            success=True,
            result="Test result",
            iterations_used=3,
            chain_id="chain-test",
            metrics=ExecutionMetrics(total_tokens=100),
        )

        # Should be able to convert to dict (JSON-compatible)
        result_dict = result.model_dump()
        assert isinstance(result_dict, dict)
        assert result_dict["success"] is True
        assert result_dict["chain_id"] == "chain-test"


class TestPlatformAutonomousConfig:
    """Tests for PlatformAutonomousConfig model."""

    def test_default_values(self) -> None:
        """PlatformAutonomousConfig should initialize with correct defaults."""
        config = PlatformAutonomousConfig()

        assert config.default_max_iterations == 15
        assert config.default_max_retries_per_tool == 3
        assert config.default_timeout_per_iteration_ms == 30000
        assert config.enable_error_recovery is True
        assert config.default_model == "claude-sonnet-4"
        assert config.visibility_end_user == "SUMMARY"
        assert config.visibility_developer == "FULL"
        assert config.visibility_admin == "FULL"
        assert config.cost_limits_enabled is False
        assert config.max_cost_per_execution_usd == 1.0
        assert config.rate_limits_enabled is False
        assert config.max_iterations_per_minute == 100

    def test_custom_values(self) -> None:
        """PlatformAutonomousConfig should accept custom values."""
        config = PlatformAutonomousConfig(
            default_max_iterations=20,
            default_max_retries_per_tool=5,
            default_timeout_per_iteration_ms=60000,
            enable_error_recovery=False,
            default_model="claude-haiku-4",
            visibility_end_user="FULL",
            cost_limits_enabled=True,
            max_cost_per_execution_usd=2.5,
            rate_limits_enabled=True,
            max_iterations_per_minute=50,
        )

        assert config.default_max_iterations == 20
        assert config.default_max_retries_per_tool == 5
        assert config.default_timeout_per_iteration_ms == 60000
        assert config.enable_error_recovery is False
        assert config.default_model == "claude-haiku-4"
        assert config.visibility_end_user == "FULL"
        assert config.cost_limits_enabled is True
        assert config.max_cost_per_execution_usd == 2.5
        assert config.rate_limits_enabled is True
        assert config.max_iterations_per_minute == 50

    def test_from_yaml_with_valid_file(self, tmp_path: Path) -> None:
        """Should load configuration from YAML file."""
        config_file = tmp_path / "autonomous.yaml"
        config_file.write_text(
            """
autonomous:
  default_max_iterations: 20
  default_model: claude-haiku-4
  cost_limits_enabled: true
  max_cost_per_execution_usd: 2.5
"""
        )

        config = PlatformAutonomousConfig.from_yaml(str(config_file))

        assert config.default_max_iterations == 20
        assert config.default_model == "claude-haiku-4"
        assert config.cost_limits_enabled is True
        assert config.max_cost_per_execution_usd == 2.5
        # Defaults should be preserved
        assert config.default_max_retries_per_tool == 3

    def test_from_yaml_with_empty_autonomous_section(self, tmp_path: Path) -> None:
        """Should use defaults when autonomous section is empty."""
        config_file = tmp_path / "autonomous.yaml"
        config_file.write_text("autonomous: {}")

        config = PlatformAutonomousConfig.from_yaml(str(config_file))

        assert config.default_max_iterations == 15
        assert config.default_model == "claude-sonnet-4"

    def test_from_yaml_with_missing_file(self) -> None:
        """Should raise FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError) as exc_info:
            PlatformAutonomousConfig.from_yaml("/nonexistent/file.yaml")

        assert "Configuration file not found" in str(exc_info.value)

    def test_from_yaml_with_invalid_yaml(self, tmp_path: Path) -> None:
        """Should raise ValueError for invalid YAML."""
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text("invalid: yaml: content: [")

        with pytest.raises(ValueError) as exc_info:
            PlatformAutonomousConfig.from_yaml(str(config_file))

        assert "Invalid YAML format" in str(exc_info.value)

    def test_from_yaml_without_autonomous_section(self, tmp_path: Path) -> None:
        """Should use defaults when no autonomous section present."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("other_section:\n  key: value")

        config = PlatformAutonomousConfig.from_yaml(str(config_file))

        assert config.default_max_iterations == 15

    def test_from_env_with_defaults(self) -> None:
        """Should use defaults when no environment variables set."""
        # Clear any existing env vars
        env_vars = [
            "OMNIFORGE_MAX_ITERATIONS",
            "OMNIFORGE_DEFAULT_MODEL",
            "OMNIFORGE_ENABLE_ERROR_RECOVERY",
        ]
        original_values = {k: os.environ.get(k) for k in env_vars}

        try:
            for var in env_vars:
                os.environ.pop(var, None)

            config = PlatformAutonomousConfig.from_env()

            assert config.default_max_iterations == 15
            assert config.default_model == "claude-sonnet-4"
            assert config.enable_error_recovery is True
        finally:
            # Restore original values
            for k, v in original_values.items():
                if v is not None:
                    os.environ[k] = v

    def test_from_env_with_overrides(self) -> None:
        """Should override defaults with environment variables."""
        env_overrides = {
            "OMNIFORGE_MAX_ITERATIONS": "25",
            "OMNIFORGE_DEFAULT_MODEL": "claude-opus-4",
            "OMNIFORGE_ENABLE_ERROR_RECOVERY": "false",
            "OMNIFORGE_MAX_RETRIES_PER_TOOL": "5",
            "OMNIFORGE_COST_LIMITS_ENABLED": "true",
            "OMNIFORGE_MAX_COST_PER_EXECUTION_USD": "3.5",
        }

        original_values = {k: os.environ.get(k) for k in env_overrides}

        try:
            os.environ.update(env_overrides)

            config = PlatformAutonomousConfig.from_env()

            assert config.default_max_iterations == 25
            assert config.default_model == "claude-opus-4"
            assert config.enable_error_recovery is False
            assert config.default_max_retries_per_tool == 5
            assert config.cost_limits_enabled is True
            assert config.max_cost_per_execution_usd == 3.5
        finally:
            # Restore original values
            for k, v in original_values.items():
                if v is not None:
                    os.environ[k] = v
                else:
                    os.environ.pop(k, None)

    def test_from_env_with_boolean_variations(self) -> None:
        """Should handle various boolean string formats."""
        test_cases = [
            ("true", True),
            ("True", True),
            ("1", True),
            ("yes", True),
            ("false", False),
            ("False", False),
            ("0", False),
            ("no", False),
        ]

        for value, expected in test_cases:
            original = os.environ.get("OMNIFORGE_ENABLE_ERROR_RECOVERY")
            try:
                os.environ["OMNIFORGE_ENABLE_ERROR_RECOVERY"] = value
                config = PlatformAutonomousConfig.from_env()
                assert config.enable_error_recovery == expected
            finally:
                if original is not None:
                    os.environ["OMNIFORGE_ENABLE_ERROR_RECOVERY"] = original
                else:
                    os.environ.pop("OMNIFORGE_ENABLE_ERROR_RECOVERY", None)

    def test_validation_default_max_iterations(self) -> None:
        """Should validate default_max_iterations bounds."""
        with pytest.raises(ValidationError):
            PlatformAutonomousConfig(default_max_iterations=0)

        with pytest.raises(ValidationError):
            PlatformAutonomousConfig(default_max_iterations=101)

    def test_validation_max_cost_negative(self) -> None:
        """Should reject negative max_cost_per_execution_usd."""
        with pytest.raises(ValidationError):
            PlatformAutonomousConfig(max_cost_per_execution_usd=-0.1)


class TestDurationParsing:
    """Tests for parse_duration_ms and is_valid_duration functions."""

    def test_parse_duration_seconds(self) -> None:
        """Should parse seconds to milliseconds."""
        assert parse_duration_ms("30s") == 30000
        assert parse_duration_ms("1s") == 1000
        assert parse_duration_ms("0.5s") == 500

    def test_parse_duration_minutes(self) -> None:
        """Should parse minutes to milliseconds."""
        assert parse_duration_ms("1m") == 60000
        assert parse_duration_ms("2m") == 120000
        assert parse_duration_ms("0.5m") == 30000

    def test_parse_duration_milliseconds(self) -> None:
        """Should parse milliseconds."""
        assert parse_duration_ms("500ms") == 500
        assert parse_duration_ms("1000ms") == 1000
        assert parse_duration_ms("100ms") == 100

    def test_parse_duration_with_decimals(self) -> None:
        """Should handle decimal values."""
        assert parse_duration_ms("1.5s") == 1500
        assert parse_duration_ms("2.5m") == 150000
        assert parse_duration_ms("500.5ms") == 500

    def test_parse_duration_with_whitespace(self) -> None:
        """Should handle whitespace."""
        assert parse_duration_ms("30 s") == 30000
        assert parse_duration_ms(" 1m ") == 60000

    def test_parse_duration_case_insensitive(self) -> None:
        """Should be case insensitive."""
        assert parse_duration_ms("30S") == 30000
        assert parse_duration_ms("1M") == 60000
        assert parse_duration_ms("500MS") == 500

    def test_parse_duration_invalid_format(self) -> None:
        """Should return None for invalid formats."""
        assert parse_duration_ms("invalid") is None
        assert parse_duration_ms("30") is None
        assert parse_duration_ms("s30") is None
        assert parse_duration_ms("30h") is None
        assert parse_duration_ms("") is None

    def test_parse_duration_none(self) -> None:
        """Should return None for None input."""
        assert parse_duration_ms(None) is None

    def test_is_valid_duration_valid_cases(self) -> None:
        """Should return True for valid durations."""
        assert is_valid_duration("30s") is True
        assert is_valid_duration("1m") is True
        assert is_valid_duration("500ms") is True
        assert is_valid_duration("1.5s") is True

    def test_is_valid_duration_invalid_cases(self) -> None:
        """Should return False for invalid durations."""
        assert is_valid_duration("invalid") is False
        assert is_valid_duration("30") is False
        assert is_valid_duration("30h") is False


class TestValidateSkillConfig:
    """Tests for validate_skill_config function."""

    def test_validate_with_no_overrides(self) -> None:
        """Should return no warnings for skill without overrides."""
        metadata = SkillMetadata(name="test-skill", description="Test skill")
        platform = PlatformAutonomousConfig()

        warnings = validate_skill_config(metadata, platform)

        assert warnings == []

    def test_validate_max_iterations_exceeds_limit(self) -> None:
        """Should warn when max_iterations exceeds maximum."""
        # Create a mock object since Pydantic validation prevents actual invalid values
        from unittest.mock import Mock

        metadata = Mock()
        metadata.max_iterations = 200
        metadata.max_retries_per_tool = None
        metadata.timeout_per_iteration = None
        platform = PlatformAutonomousConfig()

        warnings = validate_skill_config(metadata, platform)

        assert len(warnings) == 1
        assert "max_iterations (200) exceeds maximum (100)" in warnings[0]

    def test_validate_max_iterations_below_minimum(self) -> None:
        """Should warn when max_iterations is below minimum."""
        from unittest.mock import Mock

        metadata = Mock()
        metadata.max_iterations = 0
        metadata.max_retries_per_tool = None
        metadata.timeout_per_iteration = None
        platform = PlatformAutonomousConfig()

        warnings = validate_skill_config(metadata, platform)

        assert len(warnings) == 1
        assert "max_iterations (0) must be at least 1" in warnings[0]

    def test_validate_max_retries_exceeds_limit(self) -> None:
        """Should warn when max_retries_per_tool exceeds maximum."""
        from unittest.mock import Mock

        metadata = Mock()
        metadata.max_iterations = None
        metadata.max_retries_per_tool = 15
        metadata.timeout_per_iteration = None
        platform = PlatformAutonomousConfig()

        warnings = validate_skill_config(metadata, platform)

        assert len(warnings) == 1
        assert "max_retries_per_tool (15) exceeds maximum (10)" in warnings[0]

    def test_validate_invalid_timeout_format(self) -> None:
        """Should warn when timeout format is invalid."""
        metadata = SkillMetadata(
            name="test-skill", description="Test skill", timeout_per_iteration="invalid"
        )
        platform = PlatformAutonomousConfig()

        warnings = validate_skill_config(metadata, platform)

        assert len(warnings) == 1
        assert "Invalid timeout format" in warnings[0]
        assert "Use format like '30s', '1m', '500ms'" in warnings[0]

    def test_validate_valid_timeout_format(self) -> None:
        """Should not warn for valid timeout format."""
        metadata = SkillMetadata(
            name="test-skill", description="Test skill", timeout_per_iteration="30s"
        )
        platform = PlatformAutonomousConfig()

        warnings = validate_skill_config(metadata, platform)

        assert warnings == []

    def test_validate_multiple_issues(self) -> None:
        """Should return multiple warnings for multiple issues."""
        from unittest.mock import Mock

        metadata = Mock()
        metadata.max_iterations = 200
        metadata.max_retries_per_tool = None
        metadata.timeout_per_iteration = "invalid"
        platform = PlatformAutonomousConfig()

        warnings = validate_skill_config(metadata, platform)

        assert len(warnings) == 2
        assert any("max_iterations" in w for w in warnings)
        assert any("timeout format" in w for w in warnings)

    def test_validate_with_valid_config(self) -> None:
        """Should return no warnings for valid configuration."""
        metadata = SkillMetadata(
            name="test-skill",
            description="Test skill",
            max_iterations=20,
            max_retries_per_tool=5,
            timeout_per_iteration="30s",
        )
        platform = PlatformAutonomousConfig()

        warnings = validate_skill_config(metadata, platform)

        assert warnings == []


class TestMergeConfigs:
    """Tests for merge_configs function."""

    def test_merge_with_no_skill_overrides(self) -> None:
        """Should use platform defaults when skill has no overrides."""
        platform = PlatformAutonomousConfig(
            default_max_iterations=15,
            default_max_retries_per_tool=3,
            default_model="claude-sonnet-4",
        )
        metadata = SkillMetadata(name="test-skill", description="Test skill")

        config = merge_configs(platform, metadata)

        assert config.max_iterations == 15
        assert config.max_retries_per_tool == 3
        assert config.model == "claude-sonnet-4"
        assert config.enable_error_recovery is True

    def test_merge_with_skill_overrides(self) -> None:
        """Should apply skill overrides over platform defaults."""
        platform = PlatformAutonomousConfig(
            default_max_iterations=15, default_model="claude-sonnet-4"
        )
        metadata = SkillMetadata(
            name="test-skill", description="Test skill", max_iterations=20, model="claude-opus-4"
        )

        config = merge_configs(platform, metadata)

        assert config.max_iterations == 20
        assert config.model == "claude-opus-4"

    def test_merge_with_timeout_override(self) -> None:
        """Should parse and apply timeout override."""
        platform = PlatformAutonomousConfig(default_timeout_per_iteration_ms=30000)
        metadata = SkillMetadata(
            name="test-skill", description="Test skill", timeout_per_iteration="1m"
        )

        config = merge_configs(platform, metadata)

        assert config.timeout_per_iteration_ms == 60000

    def test_merge_with_invalid_timeout(self) -> None:
        """Should use platform default for invalid timeout."""
        platform = PlatformAutonomousConfig(default_timeout_per_iteration_ms=30000)
        metadata = SkillMetadata(
            name="test-skill", description="Test skill", timeout_per_iteration="invalid"
        )

        config = merge_configs(platform, metadata)

        assert config.timeout_per_iteration_ms == 30000

    def test_merge_with_early_termination_override(self) -> None:
        """Should apply early_termination override."""
        platform = PlatformAutonomousConfig()
        metadata = SkillMetadata(
            name="test-skill", description="Test skill", early_termination=False
        )

        config = merge_configs(platform, metadata)

        assert config.early_termination is False

    def test_merge_with_all_overrides(self) -> None:
        """Should apply all skill overrides correctly."""
        platform = PlatformAutonomousConfig(
            default_max_iterations=15,
            default_max_retries_per_tool=3,
            default_timeout_per_iteration_ms=30000,
            default_model="claude-sonnet-4",
            enable_error_recovery=True,
        )
        metadata = SkillMetadata(
            name="test-skill",
            description="Test skill",
            max_iterations=25,
            max_retries_per_tool=5,
            timeout_per_iteration="45s",
            model="claude-haiku-4",
            early_termination=False,
        )

        config = merge_configs(platform, metadata)

        assert config.max_iterations == 25
        assert config.max_retries_per_tool == 5
        assert config.timeout_per_iteration_ms == 45000
        assert config.model == "claude-haiku-4"
        assert config.early_termination is False
        assert config.enable_error_recovery is True

    def test_merge_preserves_platform_error_recovery(self) -> None:
        """Should always use platform's enable_error_recovery setting."""
        platform = PlatformAutonomousConfig(enable_error_recovery=False)
        metadata = SkillMetadata(name="test-skill", description="Test skill")

        config = merge_configs(platform, metadata)

        assert config.enable_error_recovery is False
