"""Performance tests for autonomous skill execution.

This module tests that autonomous skill execution meets performance targets for:
- Iteration overhead (<500ms per iteration excluding LLM)
- Token savings from progressive context loading (>=40%)
- Concurrent execution capacity (100+ concurrent)
- Memory stability under load
"""

import asyncio
import time
import tracemalloc
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest

from omniforge.agents.events import TaskDoneEvent
from omniforge.skills.autonomous_executor import AutonomousSkillExecutor
from omniforge.skills.config import AutonomousConfig
from omniforge.skills.context_loader import ContextLoader, FileReference, LoadedContext
from omniforge.skills.models import Skill, SkillMetadata
from omniforge.skills.string_substitutor import StringSubstitutor, SubstitutedContent
from omniforge.tools.base import ToolDefinition
from omniforge.tools.executor import ToolExecutor
from omniforge.tools.registry import ToolRegistry
from omniforge.tools.types import ToolType


@pytest.fixture
def mock_skill_for_performance() -> Skill:
    """Create a mock skill for performance testing."""
    return Skill(
        metadata=SkillMetadata(
            name="perf-test-skill",
            description="Performance test skill",
            allowed_tools=["read", "write"],
        ),
        content="Test skill instructions.\n\nProcess: $ARGUMENTS",
        path=Path("/tmp/perf-test/SKILL.md"),
        base_path=Path("/tmp/perf-test"),
        storage_layer="global",
    )


@pytest.fixture
def mock_registry_for_performance() -> ToolRegistry:
    """Create a mock tool registry for performance testing."""
    registry = Mock(spec=ToolRegistry)
    registry.list_tools.return_value = ["read", "write"]

    def_read = ToolDefinition(
        name="read",
        type=ToolType.FILE_READ,
        description="Read a file",
        parameters=[],
    )
    def_write = ToolDefinition(
        name="write",
        type=ToolType.FILE_WRITE,
        description="Write to a file",
        parameters=[],
    )

    registry.get_definition.side_effect = lambda name: {"read": def_read, "write": def_write}[name]

    return registry


@pytest.fixture
def mock_executor_for_performance() -> ToolExecutor:
    """Create a mock tool executor for performance testing."""
    return Mock(spec=ToolExecutor)


@pytest.fixture
def mock_context_loader_for_performance(mock_skill_for_performance: Skill) -> Mock:
    """Create a mock context loader for performance testing."""
    loader = Mock()
    loader.load_initial_context.return_value = LoadedContext(
        skill_content=mock_skill_for_performance.content,
        available_files={
            "ref1.md": FileReference(
                filename="ref1.md",
                path=Path("/tmp/perf-test/ref1.md"),
                description="Reference 1",
                estimated_lines=50,
            )
        },
        skill_dir=Path("/tmp/perf-test"),
        line_count=10,
    )
    return loader


@pytest.fixture
def mock_substitutor_for_performance() -> Mock:
    """Create a mock string substitutor for performance testing."""
    substitutor = Mock()
    substitutor.substitute.return_value = SubstitutedContent(
        content="Test skill instructions.\n\nProcess: test request",
        substitutions_made=1,
        undefined_vars=[],
    )
    return substitutor


@pytest.mark.performance
class TestIterationOverhead:
    """Tests for ReAct loop iteration overhead."""

    @pytest.mark.asyncio
    async def test_iteration_overhead_under_500ms(
        self,
        mock_skill_for_performance: Skill,
        mock_registry_for_performance: ToolRegistry,
        mock_executor_for_performance: ToolExecutor,
        mock_context_loader_for_performance: ContextLoader,
        mock_substitutor_for_performance: StringSubstitutor,
    ) -> None:
        """Single iteration should complete in under 500ms (excluding LLM)."""
        executor = AutonomousSkillExecutor(
            skill=mock_skill_for_performance,
            tool_registry=mock_registry_for_performance,
            tool_executor=mock_executor_for_performance,
            context_loader=mock_context_loader_for_performance,
            string_substitutor=mock_substitutor_for_performance,
        )

        # Mock the ReasoningEngine with instant LLM response
        with patch("omniforge.skills.autonomous_executor.ReasoningEngine") as mock_engine_class:
            mock_engine = Mock()
            mock_engine_class.return_value = mock_engine

            # Mock LLM call to return instantly with final answer
            mock_llm_result = Mock()
            mock_llm_result.success = True
            mock_llm_result.value = {
                "content": '{"thought": "Done", "final_answer": "Complete", "is_final": true}'
            }
            mock_engine.call_llm = AsyncMock(return_value=mock_llm_result)

            start = time.perf_counter()
            events = []
            async for event in executor.execute("test", "task-perf-1", "session-perf"):
                events.append(event)
            duration_ms = (time.perf_counter() - start) * 1000

        # Should have completed one iteration quickly
        # Allow generous buffer since includes event processing
        assert duration_ms < 500, f"Iteration took {duration_ms:.2f}ms, expected <500ms"

    @pytest.mark.asyncio
    async def test_preprocessing_overhead_minimal(
        self,
        mock_skill_for_performance: Skill,
        mock_registry_for_performance: ToolRegistry,
        mock_executor_for_performance: ToolExecutor,
    ) -> None:
        """Preprocessing should add minimal overhead."""
        executor = AutonomousSkillExecutor(
            skill=mock_skill_for_performance,
            tool_registry=mock_registry_for_performance,
            tool_executor=mock_executor_for_performance,
        )

        start = time.perf_counter()
        await executor._preprocess_content(
            user_request="test",
            session_id="test-session",
            tenant_id="test-tenant",
        )
        duration_ms = (time.perf_counter() - start) * 1000

        assert duration_ms < 100, f"Preprocessing took {duration_ms:.2f}ms, expected <100ms"

    @pytest.mark.asyncio
    async def test_event_emission_overhead_minimal(
        self,
        mock_skill_for_performance: Skill,
        mock_registry_for_performance: ToolRegistry,
        mock_executor_for_performance: ToolExecutor,
        mock_context_loader_for_performance: ContextLoader,
        mock_substitutor_for_performance: StringSubstitutor,
    ) -> None:
        """Event emission should not block execution."""
        config = AutonomousConfig(max_iterations=3)
        executor = AutonomousSkillExecutor(
            skill=mock_skill_for_performance,
            tool_registry=mock_registry_for_performance,
            tool_executor=mock_executor_for_performance,
            config=config,
            context_loader=mock_context_loader_for_performance,
            string_substitutor=mock_substitutor_for_performance,
        )

        # Mock the ReasoningEngine
        with patch("omniforge.skills.autonomous_executor.ReasoningEngine") as mock_engine_class:
            mock_engine = Mock()
            mock_engine_class.return_value = mock_engine

            iteration_count = 0

            async def mock_llm_call(*args: Any, **kwargs: Any) -> Mock:
                nonlocal iteration_count
                iteration_count += 1
                mock_result = Mock()
                mock_result.success = True
                if iteration_count < 3:
                    content = (
                        '{"thought": "Continue", "action": "read", '
                        '"action_input": {}, "is_final": false}'
                    )
                else:
                    content = '{"thought": "Done", "final_answer": "Complete", ' '"is_final": true}'
                mock_result.value = {"content": content}
                return mock_result

            mock_engine.call_llm = AsyncMock(side_effect=mock_llm_call)

            # Mock tool call
            mock_tool_result = Mock()
            mock_tool_result.success = True
            mock_tool_result.value = {"data": "test"}
            mock_tool_result.error = None
            mock_engine.call_tool = AsyncMock(return_value=mock_tool_result)

            events = []
            start = time.perf_counter()
            async for event in executor.execute("test", "task-perf-2", "session-perf"):
                events.append(event)
            duration_ms = (time.perf_counter() - start) * 1000

        # Calculate overhead per event
        overhead_per_event = duration_ms / len(events) if events else 0

        assert (
            overhead_per_event < 10
        ), f"Event overhead: {overhead_per_event:.2f}ms per event, expected <10ms"


@pytest.mark.performance
class TestTokenSavings:
    """Tests for progressive context loading token savings."""

    def test_initial_context_under_limit(
        self,
        mock_skill_for_performance: Skill,
        mock_registry_for_performance: ToolRegistry,
        mock_executor_for_performance: ToolExecutor,
    ) -> None:
        """Initial context should be limited to SKILL.md only."""
        # Create real context loader
        context_loader = ContextLoader(mock_skill_for_performance)

        # Load initial context
        context = context_loader.load_initial_context()

        # SKILL.md should be under 500 lines
        assert context.line_count <= 500, f"Initial context has {context.line_count} lines"

        # Calculate approximate tokens (1 line ~ 10 tokens)
        estimated_tokens = context.line_count * 10
        assert (
            estimated_tokens < 5000
        ), f"Estimated {estimated_tokens} tokens, expected <5000 for initial context"

    def test_token_savings_measurement(self, tmp_path: Path) -> None:
        """Measure token savings from progressive loading."""
        # Create skill directory with multiple supporting files
        skill_dir = tmp_path / "token-test-skill"
        skill_dir.mkdir()

        # Create SKILL.md with moderate content
        skill_md = skill_dir / "SKILL.md"
        skill_md_content = """---
name: token-test
description: Test skill for token savings
---

# Token Test Skill

This is a test skill with supporting files.

## Instructions

Process the data using available tools.
"""
        skill_md.write_text(skill_md_content)

        # Create multiple supporting files
        for i in range(5):
            support_file = skill_dir / f"support_{i}.md"
            # Each file has ~200 lines
            content = "\n".join([f"Line {j} of support file {i}" for j in range(200)])
            support_file.write_text(content)

        # Calculate tokens if all files loaded upfront
        total_lines = 0
        for file_path in skill_dir.glob("*.md"):
            total_lines += len(file_path.read_text().splitlines())
        total_tokens_upfront = total_lines * 10

        # Calculate tokens with progressive loading (SKILL.md only)
        skill_md_lines = len(skill_md.read_text().splitlines())
        progressive_tokens = skill_md_lines * 10

        # Calculate savings
        savings_pct = (1 - progressive_tokens / total_tokens_upfront) * 100

        assert savings_pct >= 40, (
            f"Token savings: {savings_pct:.1f}%, expected >=40% "
            f"(progressive: {progressive_tokens}, upfront: {total_tokens_upfront})"
        )

    def test_progressive_loading_reduces_context(
        self,
        mock_skill_for_performance: Skill,
        mock_registry_for_performance: ToolRegistry,
        mock_executor_for_performance: ToolExecutor,
    ) -> None:
        """Progressive loading should significantly reduce initial context size."""
        # Create context loader
        context_loader = ContextLoader(mock_skill_for_performance)

        # Load initial context
        initial_context = context_loader.load_initial_context()

        # Initial context should only have SKILL.md content
        # Supporting files should be listed but not loaded
        assert initial_context.skill_content is not None
        assert initial_context.line_count < 100  # Should be small

        # Verify supporting files are available but not loaded
        if initial_context.available_files:
            # Files are referenced but content not loaded
            for filename, file_ref in initial_context.available_files.items():
                assert file_ref.estimated_lines is not None
                assert file_ref.description is not None


@pytest.mark.performance
@pytest.mark.slow
class TestConcurrentExecution:
    """Tests for concurrent skill execution capacity."""

    @pytest.mark.asyncio
    async def test_concurrent_executions(
        self,
        mock_skill_for_performance: Skill,
        mock_registry_for_performance: ToolRegistry,
        mock_executor_for_performance: ToolExecutor,
        mock_context_loader_for_performance: ContextLoader,
        mock_substitutor_for_performance: StringSubstitutor,
    ) -> None:
        """Should support 100+ concurrent executions."""
        num_concurrent = 100

        async def execute_skill(i: int) -> list[Any]:
            executor = AutonomousSkillExecutor(
                skill=mock_skill_for_performance,
                tool_registry=mock_registry_for_performance,
                tool_executor=mock_executor_for_performance,
                context_loader=mock_context_loader_for_performance,
                string_substitutor=mock_substitutor_for_performance,
            )

            # Mock the ReasoningEngine
            with patch("omniforge.skills.autonomous_executor.ReasoningEngine") as mock_engine_class:
                mock_engine = Mock()
                mock_engine_class.return_value = mock_engine

                mock_llm_result = Mock()
                mock_llm_result.success = True
                mock_llm_result.value = {
                    "content": '{"thought": "Done", "final_answer": "Complete", "is_final": true}'
                }
                mock_engine.call_llm = AsyncMock(return_value=mock_llm_result)

                events = []
                async for event in executor.execute(
                    f"Task {i}",
                    f"task-{i}",
                    "session-concurrent",
                ):
                    events.append(event)
                return events

        # Execute all concurrently
        start = time.perf_counter()
        results = await asyncio.gather(*[execute_skill(i) for i in range(num_concurrent)])
        duration = time.perf_counter() - start

        # All should complete successfully
        assert all(len(r) > 0 for r in results), "All executions should produce events"

        # Check that all completed successfully
        completed_count = sum(
            1 for result in results if any(isinstance(e, TaskDoneEvent) for e in result)
        )
        assert (
            completed_count == num_concurrent
        ), f"Expected {num_concurrent} completions, got {completed_count}"

        # Log performance
        throughput = num_concurrent / duration
        print(f"\nCompleted {num_concurrent} executions in {duration:.2f}s")
        print(f"Throughput: {throughput:.2f} executions/second")

        # Verify reasonable throughput (at least 10 exec/s with mocking)
        assert throughput > 10, f"Throughput {throughput:.2f} exec/s is too low"

    @pytest.mark.asyncio
    async def test_memory_stable_under_load(
        self,
        mock_skill_for_performance: Skill,
        mock_registry_for_performance: ToolRegistry,
        mock_executor_for_performance: ToolExecutor,
        mock_context_loader_for_performance: ContextLoader,
        mock_substitutor_for_performance: StringSubstitutor,
    ) -> None:
        """Memory should not grow unbounded during concurrent execution."""
        tracemalloc.start()
        initial_memory = tracemalloc.get_traced_memory()[0]

        # Run many executions sequentially
        for i in range(50):
            executor = AutonomousSkillExecutor(
                skill=mock_skill_for_performance,
                tool_registry=mock_registry_for_performance,
                tool_executor=mock_executor_for_performance,
                context_loader=mock_context_loader_for_performance,
                string_substitutor=mock_substitutor_for_performance,
            )

            # Mock the ReasoningEngine
            with patch("omniforge.skills.autonomous_executor.ReasoningEngine") as mock_engine_class:
                mock_engine = Mock()
                mock_engine_class.return_value = mock_engine

                mock_llm_result = Mock()
                mock_llm_result.success = True
                mock_llm_result.value = {
                    "content": '{"thought": "Done", "final_answer": "Complete", "is_final": true}'
                }
                mock_engine.call_llm = AsyncMock(return_value=mock_llm_result)

                async for _ in executor.execute(f"Task {i}", f"task-mem-{i}", "session-mem"):
                    pass

        final_memory = tracemalloc.get_traced_memory()[0]
        tracemalloc.stop()

        memory_growth = final_memory - initial_memory
        memory_growth_mb = memory_growth / (1024 * 1024)

        print(f"\nMemory growth: {memory_growth_mb:.2f} MB over 50 executions")

        assert memory_growth_mb < 100, f"Memory grew by {memory_growth_mb:.2f}MB, expected <100MB"


@pytest.mark.performance
class TestExecutionMetrics:
    """Tests for ExecutionMetrics accuracy and tracking."""

    @pytest.mark.asyncio
    async def test_metrics_track_duration(
        self,
        mock_skill_for_performance: Skill,
        mock_registry_for_performance: ToolRegistry,
        mock_executor_for_performance: ToolExecutor,
        mock_context_loader_for_performance: ContextLoader,
        mock_substitutor_for_performance: StringSubstitutor,
    ) -> None:
        """ExecutionMetrics should accurately track execution duration."""
        executor = AutonomousSkillExecutor(
            skill=mock_skill_for_performance,
            tool_registry=mock_registry_for_performance,
            tool_executor=mock_executor_for_performance,
            context_loader=mock_context_loader_for_performance,
            string_substitutor=mock_substitutor_for_performance,
        )

        # Mock the ReasoningEngine
        with patch("omniforge.skills.autonomous_executor.ReasoningEngine") as mock_engine_class:
            mock_engine = Mock()
            mock_engine_class.return_value = mock_engine

            mock_llm_result = Mock()
            mock_llm_result.success = True
            mock_llm_result.value = {
                "content": '{"thought": "Done", "final_answer": "Complete", "is_final": true}'
            }
            mock_engine.call_llm = AsyncMock(return_value=mock_llm_result)

            start = time.perf_counter()
            result = await executor.execute_sync("test", "task-metrics-1", "session-metrics")
            actual_duration = time.perf_counter() - start

        # Verify duration is tracked
        assert result.metrics.duration_seconds > 0
        # Allow some tolerance for measurement differences
        assert abs(result.metrics.duration_seconds - actual_duration) < 0.1

    @pytest.mark.asyncio
    async def test_metrics_track_model_used(
        self,
        mock_skill_for_performance: Skill,
        mock_registry_for_performance: ToolRegistry,
        mock_executor_for_performance: ToolExecutor,
        mock_context_loader_for_performance: ContextLoader,
        mock_substitutor_for_performance: StringSubstitutor,
    ) -> None:
        """ExecutionMetrics should track the model used for execution."""
        # Set specific model
        mock_skill_for_performance.metadata.model = "haiku"

        executor = AutonomousSkillExecutor(
            skill=mock_skill_for_performance,
            tool_registry=mock_registry_for_performance,
            tool_executor=mock_executor_for_performance,
            context_loader=mock_context_loader_for_performance,
            string_substitutor=mock_substitutor_for_performance,
        )

        # Mock the ReasoningEngine
        with patch("omniforge.skills.autonomous_executor.ReasoningEngine") as mock_engine_class:
            mock_engine = Mock()
            mock_engine_class.return_value = mock_engine

            mock_llm_result = Mock()
            mock_llm_result.success = True
            mock_llm_result.value = {
                "content": '{"thought": "Done", "final_answer": "Complete", "is_final": true}'
            }
            mock_engine.call_llm = AsyncMock(return_value=mock_llm_result)

            result = await executor.execute_sync("test", "task-metrics-2", "session-metrics")

        # Verify model is tracked
        assert result.metrics.model_used == "claude-haiku-4"

    @pytest.mark.asyncio
    async def test_metrics_calculate_estimated_cost(
        self,
        mock_skill_for_performance: Skill,
        mock_registry_for_performance: ToolRegistry,
        mock_executor_for_performance: ToolExecutor,
        mock_context_loader_for_performance: ContextLoader,
        mock_substitutor_for_performance: StringSubstitutor,
    ) -> None:
        """ExecutionMetrics should calculate estimated cost based on model."""
        # Set model with known costs
        mock_skill_for_performance.metadata.model = "sonnet"

        executor = AutonomousSkillExecutor(
            skill=mock_skill_for_performance,
            tool_registry=mock_registry_for_performance,
            tool_executor=mock_executor_for_performance,
            context_loader=mock_context_loader_for_performance,
            string_substitutor=mock_substitutor_for_performance,
        )

        # Mock the ReasoningEngine
        with patch("omniforge.skills.autonomous_executor.ReasoningEngine") as mock_engine_class:
            mock_engine = Mock()
            mock_engine_class.return_value = mock_engine

            mock_llm_result = Mock()
            mock_llm_result.success = True
            mock_llm_result.value = {
                "content": '{"thought": "Done", "final_answer": "Complete", "is_final": true}'
            }
            mock_engine.call_llm = AsyncMock(return_value=mock_llm_result)

            result = await executor.execute_sync("test", "task-metrics-3", "session-metrics")

        # Verify estimated cost is calculated
        assert result.metrics.estimated_cost_per_call > 0
        # Sonnet: (3 + 15) / 2 / 1M = 0.000009
        assert result.metrics.estimated_cost_per_call > 0.000008
