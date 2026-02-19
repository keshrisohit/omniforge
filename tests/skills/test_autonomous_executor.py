"""Tests for autonomous skill executor with ReAct loop.

This module tests the AutonomousSkillExecutor class, which implements the core
ReAct (Reason-Act-Observe) loop for autonomous skill execution.
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from omniforge.agents.events import (
    TaskDoneEvent,
    TaskErrorEvent,
    TaskMessageEvent,
    TaskStatusEvent,
)
from omniforge.skills.autonomous_executor import AutonomousSkillExecutor
from omniforge.skills.config import AutonomousConfig, ExecutionResult
from omniforge.skills.context_loader import ContextLoader, FileReference, LoadedContext
from omniforge.skills.models import Skill, SkillMetadata
from omniforge.skills.string_substitutor import (
    StringSubstitutor,
    SubstitutedContent,
)
from omniforge.tasks.models import TaskState
from omniforge.tools.base import ToolDefinition
from omniforge.tools.executor import ToolExecutor
from omniforge.tools.registry import ToolRegistry
from omniforge.tools.types import ToolType


@pytest.fixture
def mock_skill() -> Skill:
    """Create a mock skill for testing."""
    return Skill(
        metadata=SkillMetadata(
            name="test-skill",
            description="A test skill for unit testing",
            allowed_tools=["read", "write", "llm"],
        ),
        content="Test skill instructions.\n\nProcess the request: $ARGUMENTS",
        path=Path("/tmp/test-skill/SKILL.md"),
        base_path=Path("/tmp/test-skill"),
        storage_layer="global",
    )


@pytest.fixture
def mock_tool_registry() -> ToolRegistry:
    """Create a mock tool registry."""
    registry = Mock(spec=ToolRegistry)
    registry.list_tools.return_value = ["read", "write", "llm"]

    # Mock tool definitions
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
    def_llm = ToolDefinition(
        name="llm",
        type=ToolType.LLM,
        description="Call LLM",
        parameters=[],
    )

    registry.get_definition.side_effect = lambda name: {
        "read": def_read,
        "write": def_write,
        "llm": def_llm,
    }[name]

    return registry


@pytest.fixture
def mock_tool_executor() -> ToolExecutor:
    """Create a mock tool executor."""
    return Mock(spec=ToolExecutor)


@pytest.fixture
def mock_context_loader(mock_skill: Skill) -> Mock:
    """Create a mock context loader."""
    loader = Mock()
    loader.load_initial_context.return_value = LoadedContext(
        skill_content=mock_skill.content,
        available_files={
            "reference.md": FileReference(
                filename="reference.md",
                path=Path("/tmp/test-skill/reference.md"),
                description="Reference documentation",
                estimated_lines=100,
            )
        },
        skill_dir=Path("/tmp/test-skill"),
        line_count=10,
    )
    return loader


@pytest.fixture
def mock_string_substitutor() -> Mock:
    """Create a mock string substitutor."""
    substitutor = Mock()
    substitutor.substitute.return_value = SubstitutedContent(
        content="Test skill instructions.\n\nProcess the request: test request",
        substitutions_made=1,
        undefined_vars=[],
    )
    return substitutor


class TestAutonomousSkillExecutor:
    """Test suite for AutonomousSkillExecutor."""

    def test_init_with_defaults(
        self,
        mock_skill: Skill,
        mock_tool_registry: ToolRegistry,
        mock_tool_executor: ToolExecutor,
    ) -> None:
        """Executor should initialize with default configuration."""
        executor = AutonomousSkillExecutor(
            skill=mock_skill,
            tool_registry=mock_tool_registry,
            tool_executor=mock_tool_executor,
        )

        assert executor.skill == mock_skill
        assert executor.tool_registry == mock_tool_registry
        assert executor.tool_executor == mock_tool_executor
        assert executor.config.max_iterations == 15
        assert executor.config.temperature == 0.0
        assert executor.context_loader is not None
        assert executor.string_substitutor is not None

    def test_init_with_custom_config(
        self,
        mock_skill: Skill,
        mock_tool_registry: ToolRegistry,
        mock_tool_executor: ToolExecutor,
    ) -> None:
        """Executor should accept custom configuration."""
        config = AutonomousConfig(max_iterations=5, temperature=0.7)

        executor = AutonomousSkillExecutor(
            skill=mock_skill,
            tool_registry=mock_tool_registry,
            tool_executor=mock_tool_executor,
            config=config,
        )

        assert executor.config.max_iterations == 5
        assert executor.config.temperature == 0.7

    @pytest.mark.asyncio
    async def test_execute_returns_events(
        self,
        mock_skill: Skill,
        mock_tool_registry: ToolRegistry,
        mock_tool_executor: ToolExecutor,
        mock_context_loader: ContextLoader,
        mock_string_substitutor: StringSubstitutor,
    ) -> None:
        """Execute should yield TaskEvent instances."""
        executor = AutonomousSkillExecutor(
            skill=mock_skill,
            tool_registry=mock_tool_registry,
            tool_executor=mock_tool_executor,
            context_loader=mock_context_loader,
            string_substitutor=mock_string_substitutor,
        )

        # Mock the ReasoningEngine to return final answer immediately
        with patch("omniforge.skills.autonomous_executor.ReasoningEngine") as mock_engine_class:
            mock_engine = Mock()
            mock_engine_class.return_value = mock_engine

            # Mock LLM call to return final answer
            mock_llm_result = Mock()
            mock_llm_result.success = True
            mock_llm_result.value = {
                "content": '{"thought": "Done", "final_answer": "Task complete", "is_final": true}'
            }
            mock_engine.call_llm = AsyncMock(return_value=mock_llm_result)

            events = []
            async for event in executor.execute("test request", "task-1", "session-1"):
                events.append(event)

        # Should have at least: status, message (iteration), message (final), done
        assert len(events) >= 3
        assert any(isinstance(e, TaskStatusEvent) for e in events)
        assert any(isinstance(e, TaskMessageEvent) for e in events)
        assert any(isinstance(e, TaskDoneEvent) for e in events)

    @pytest.mark.asyncio
    async def test_execute_respects_max_iterations(
        self,
        mock_skill: Skill,
        mock_tool_registry: ToolRegistry,
        mock_tool_executor: ToolExecutor,
        mock_context_loader: ContextLoader,
        mock_string_substitutor: StringSubstitutor,
    ) -> None:
        """Execute should stop at max_iterations."""
        config = AutonomousConfig(max_iterations=3)
        executor = AutonomousSkillExecutor(
            skill=mock_skill,
            tool_registry=mock_tool_registry,
            tool_executor=mock_tool_executor,
            config=config,
            context_loader=mock_context_loader,
            string_substitutor=mock_string_substitutor,
        )

        # Mock the ReasoningEngine to never return final answer
        with patch("omniforge.skills.autonomous_executor.ReasoningEngine") as mock_engine_class:
            mock_engine = Mock()
            mock_engine_class.return_value = mock_engine

            # Mock LLM call to return action (no final answer)
            mock_llm_result = Mock()
            mock_llm_result.success = True
            content = (
                '{"thought": "Thinking", "action": "read", '
                '"action_input": {}, "is_final": false}'
            )
            mock_llm_result.value = {"content": content}
            mock_engine.call_llm = AsyncMock(return_value=mock_llm_result)

            # Mock tool call to succeed
            mock_tool_result = Mock()
            mock_tool_result.success = True
            mock_tool_result.value = {"data": "test"}
            mock_tool_result.error = None
            mock_engine.call_tool = AsyncMock(return_value=mock_tool_result)

            events = []
            async for event in executor.execute("test request", "task-1", "session-1"):
                events.append(event)

        # Should have exactly 3 iteration messages + status + error + done
        iteration_messages = [
            e
            for e in events
            if isinstance(e, TaskMessageEvent) and "Iteration" in e.message_parts[0].text
        ]
        assert len(iteration_messages) == 3

        # Should end with error and done (failed)
        assert isinstance(events[-1], TaskDoneEvent)
        assert events[-1].final_state == TaskState.FAILED

    @pytest.mark.asyncio
    async def test_execute_stops_on_final_answer(
        self,
        mock_skill: Skill,
        mock_tool_registry: ToolRegistry,
        mock_tool_executor: ToolExecutor,
        mock_context_loader: ContextLoader,
        mock_string_substitutor: StringSubstitutor,
    ) -> None:
        """Execute should stop when LLM returns final answer."""
        executor = AutonomousSkillExecutor(
            skill=mock_skill,
            tool_registry=mock_tool_registry,
            tool_executor=mock_tool_executor,
            context_loader=mock_context_loader,
            string_substitutor=mock_string_substitutor,
        )

        # Mock the ReasoningEngine to return final answer on iteration 2
        with patch("omniforge.skills.autonomous_executor.ReasoningEngine") as mock_engine_class:
            mock_engine = Mock()
            mock_engine_class.return_value = mock_engine

            call_count = 0

            async def mock_llm_call(*args, **kwargs):
                nonlocal call_count
                call_count += 1

                if call_count == 1:
                    # First iteration: return action
                    mock_result = Mock()
                    mock_result.success = True
                    content1 = (
                        '{"thought": "Need to act", "action": "read", '
                        '"action_input": {}, "is_final": false}'
                    )
                    mock_result.value = {"content": content1}
                    return mock_result
                else:
                    # Second iteration: return final answer
                    mock_result = Mock()
                    mock_result.success = True
                    content2 = (
                        '{"thought": "Done", "final_answer": "Task complete", ' '"is_final": true}'
                    )
                    mock_result.value = {"content": content2}
                    return mock_result

            mock_engine.call_llm = AsyncMock(side_effect=mock_llm_call)

            # Mock tool call to succeed
            mock_tool_result = Mock()
            mock_tool_result.success = True
            mock_tool_result.value = {"data": "test"}
            mock_tool_result.error = None
            mock_engine.call_tool = AsyncMock(return_value=mock_tool_result)

            events = []
            async for event in executor.execute("test request", "task-1", "session-1"):
                events.append(event)

        # Should have stopped early (not all iterations)
        iteration_messages = [
            e
            for e in events
            if isinstance(e, TaskMessageEvent) and "Iteration" in e.message_parts[0].text
        ]
        assert len(iteration_messages) == 2  # Stopped at iteration 2

        # Should end with completed state
        assert isinstance(events[-1], TaskDoneEvent)
        assert events[-1].final_state == TaskState.COMPLETED

    @pytest.mark.asyncio
    async def test_execute_sync_returns_result(
        self,
        mock_skill: Skill,
        mock_tool_registry: ToolRegistry,
        mock_tool_executor: ToolExecutor,
        mock_context_loader: ContextLoader,
        mock_string_substitutor: StringSubstitutor,
    ) -> None:
        """execute_sync should return ExecutionResult."""
        executor = AutonomousSkillExecutor(
            skill=mock_skill,
            tool_registry=mock_tool_registry,
            tool_executor=mock_tool_executor,
            context_loader=mock_context_loader,
            string_substitutor=mock_string_substitutor,
        )

        # Mock the ReasoningEngine to return final answer
        with patch("omniforge.skills.autonomous_executor.ReasoningEngine") as mock_engine_class:
            mock_engine = Mock()
            mock_engine_class.return_value = mock_engine

            mock_llm_result = Mock()
            mock_llm_result.success = True
            mock_llm_result.value = {
                "content": '{"thought": "Done", "final_answer": "Success!", "is_final": true}'
            }
            mock_engine.call_llm = AsyncMock(return_value=mock_llm_result)

            result = await executor.execute_sync("test request", "task-1", "session-1")

        assert isinstance(result, ExecutionResult)
        assert result.success is True
        assert "Success!" in result.result
        assert result.iterations_used >= 0
        assert result.chain_id == "task-1"

    @pytest.mark.asyncio
    async def test_execute_handles_llm_failure(
        self,
        mock_skill: Skill,
        mock_tool_registry: ToolRegistry,
        mock_tool_executor: ToolExecutor,
        mock_context_loader: ContextLoader,
        mock_string_substitutor: StringSubstitutor,
    ) -> None:
        """Execute should handle LLM call failures gracefully."""
        config = AutonomousConfig(enable_error_recovery=False)
        executor = AutonomousSkillExecutor(
            skill=mock_skill,
            tool_registry=mock_tool_registry,
            tool_executor=mock_tool_executor,
            config=config,
            context_loader=mock_context_loader,
            string_substitutor=mock_string_substitutor,
        )

        # Mock the ReasoningEngine to fail LLM call
        with patch("omniforge.skills.autonomous_executor.ReasoningEngine") as mock_engine_class:
            mock_engine = Mock()
            mock_engine_class.return_value = mock_engine

            mock_llm_result = Mock()
            mock_llm_result.success = False
            mock_llm_result.error = "LLM service unavailable"
            mock_llm_result.value = None
            mock_engine.call_llm = AsyncMock(return_value=mock_llm_result)

            events = []
            async for event in executor.execute("test request", "task-1", "session-1"):
                events.append(event)

        # Should emit error event
        error_events = [e for e in events if isinstance(e, TaskErrorEvent)]
        assert len(error_events) >= 1
        assert "LLM call failed" in error_events[0].error_message

        # Should end with failed state
        assert isinstance(events[-1], TaskDoneEvent)
        assert events[-1].final_state == TaskState.FAILED

    @pytest.mark.asyncio
    async def test_execute_handles_tool_failure(
        self,
        mock_skill: Skill,
        mock_tool_registry: ToolRegistry,
        mock_tool_executor: ToolExecutor,
        mock_context_loader: ContextLoader,
        mock_string_substitutor: StringSubstitutor,
    ) -> None:
        """Execute should handle tool execution failures gracefully."""
        executor = AutonomousSkillExecutor(
            skill=mock_skill,
            tool_registry=mock_tool_registry,
            tool_executor=mock_tool_executor,
            context_loader=mock_context_loader,
            string_substitutor=mock_string_substitutor,
        )

        # Mock the ReasoningEngine
        with patch("omniforge.skills.autonomous_executor.ReasoningEngine") as mock_engine_class:
            mock_engine = Mock()
            mock_engine_class.return_value = mock_engine

            call_count = 0

            async def mock_llm_call(*args, **kwargs):
                nonlocal call_count
                call_count += 1

                if call_count == 1:
                    # First: return action that will fail
                    mock_result = Mock()
                    mock_result.success = True
                    content1 = (
                        '{"thought": "Try tool", "action": "read", '
                        '"action_input": {}, "is_final": false}'
                    )
                    mock_result.value = {"content": content1}
                    return mock_result
                else:
                    # Then: return final answer
                    mock_result = Mock()
                    mock_result.success = True
                    content2 = (
                        '{"thought": "Done", "final_answer": "Recovered", ' '"is_final": true}'
                    )
                    mock_result.value = {"content": content2}
                    return mock_result

            mock_engine.call_llm = AsyncMock(side_effect=mock_llm_call)

            # Mock tool call to fail
            mock_tool_result = Mock()
            mock_tool_result.success = False
            mock_tool_result.error = "File not found"
            mock_tool_result.value = None
            mock_engine.call_tool = AsyncMock(return_value=mock_tool_result)

            events = []
            async for event in executor.execute("test request", "task-1", "session-1"):
                events.append(event)

        # Should continue after tool failure and complete
        assert isinstance(events[-1], TaskDoneEvent)
        assert events[-1].final_state == TaskState.COMPLETED

    @pytest.mark.asyncio
    async def test_execute_handles_timeout(
        self,
        mock_skill: Skill,
        mock_tool_registry: ToolRegistry,
        mock_tool_executor: ToolExecutor,
        mock_context_loader: ContextLoader,
        mock_string_substitutor: StringSubstitutor,
    ) -> None:
        """Execute should handle iteration timeout gracefully."""
        config = AutonomousConfig(
            timeout_per_iteration_ms=1000,  # Short timeout (minimum allowed)
            enable_error_recovery=False,
        )
        executor = AutonomousSkillExecutor(
            skill=mock_skill,
            tool_registry=mock_tool_registry,
            tool_executor=mock_tool_executor,
            config=config,
            context_loader=mock_context_loader,
            string_substitutor=mock_string_substitutor,
        )

        # Mock the ReasoningEngine with slow LLM call
        with patch("omniforge.skills.autonomous_executor.ReasoningEngine") as mock_engine_class:
            mock_engine = Mock()
            mock_engine_class.return_value = mock_engine

            async def slow_llm_call(*args, **kwargs):
                await asyncio.sleep(2)  # Longer than timeout (2 seconds)
                mock_result = Mock()
                mock_result.success = True
                mock_result.value = {"content": '{"is_final": false}'}
                return mock_result

            mock_engine.call_llm = AsyncMock(side_effect=slow_llm_call)

            events = []
            async for event in executor.execute("test request", "task-1", "session-1"):
                events.append(event)

        # Should emit timeout error
        error_events = [e for e in events if isinstance(e, TaskErrorEvent)]
        assert len(error_events) >= 1
        assert any("timeout" in e.error_message.lower() for e in error_events)

    @pytest.mark.asyncio
    async def test_preprocess_content_substitutes_variables(
        self,
        mock_skill: Skill,
        mock_tool_registry: ToolRegistry,
        mock_tool_executor: ToolExecutor,
    ) -> None:
        """Preprocess should substitute variables in skill content."""
        executor = AutonomousSkillExecutor(
            skill=mock_skill,
            tool_registry=mock_tool_registry,
            tool_executor=mock_tool_executor,
        )

        processed = await executor._preprocess_content(
            user_request="test data",
            session_id="session-123",
            tenant_id="tenant-1",
        )

        # Should have substituted $ARGUMENTS
        assert "test data" in processed
        assert "$ARGUMENTS" not in processed

    @pytest.mark.asyncio
    async def test_build_system_prompt_includes_skill_instructions(
        self,
        mock_skill: Skill,
        mock_tool_registry: ToolRegistry,
        mock_tool_executor: ToolExecutor,
        mock_context_loader: ContextLoader,
    ) -> None:
        """System prompt should include skill instructions and available tools."""
        executor = AutonomousSkillExecutor(
            skill=mock_skill,
            tool_registry=mock_tool_registry,
            tool_executor=mock_tool_executor,
            context_loader=mock_context_loader,
        )

        processed_content = "Test instructions"
        prompt = await executor._build_system_prompt(processed_content)

        # Should include skill name and description
        assert "test-skill" in prompt
        assert "Test instructions" in prompt

        # Should include allowed tools
        assert "read" in prompt
        assert "write" in prompt
        assert "llm" in prompt

        # Should include supporting files
        assert "reference.md" in prompt

        # Should include ReAct format instructions
        assert "JSON" in prompt or "json" in prompt

    @pytest.mark.asyncio
    async def test_execute_respects_allowed_tools(
        self,
        mock_skill: Skill,
        mock_tool_registry: ToolRegistry,
        mock_tool_executor: ToolExecutor,
        mock_context_loader: ContextLoader,
        mock_string_substitutor: StringSubstitutor,
    ) -> None:
        """Executor should only use allowed tools from skill metadata."""
        # Modify skill to only allow 'read'
        mock_skill.metadata.allowed_tools = ["read"]

        executor = AutonomousSkillExecutor(
            skill=mock_skill,
            tool_registry=mock_tool_registry,
            tool_executor=mock_tool_executor,
            context_loader=mock_context_loader,
            string_substitutor=mock_string_substitutor,
        )

        processed_content = "Test"
        prompt = await executor._build_system_prompt(processed_content)

        # Should only include allowed tool
        assert "read" in prompt
        # Should not include disallowed tools in the list
        assert prompt.count("write") <= 1  # May appear in general text
        assert "Use only the allowed tools: read" in prompt


class TestErrorRecoveryAndRetry:
    """Test suite for error recovery and retry logic (TASK-008)."""

    @pytest.mark.asyncio
    async def test_error_recovery_retries_tool(
        self,
        mock_skill: Skill,
        mock_tool_registry: ToolRegistry,
        mock_tool_executor: ToolExecutor,
        mock_context_loader: ContextLoader,
        mock_string_substitutor: StringSubstitutor,
    ) -> None:
        """Failed tool should be retried up to max_retries_per_tool times."""
        config = AutonomousConfig(max_retries_per_tool=2)
        executor = AutonomousSkillExecutor(
            skill=mock_skill,
            tool_registry=mock_tool_registry,
            tool_executor=mock_tool_executor,
            config=config,
            context_loader=mock_context_loader,
            string_substitutor=mock_string_substitutor,
        )

        # Mock the ReasoningEngine
        with patch("omniforge.skills.autonomous_executor.ReasoningEngine") as mock_engine_class:
            mock_engine = Mock()
            mock_engine_class.return_value = mock_engine

            call_count = 0

            async def mock_llm_call(*args, **kwargs):
                nonlocal call_count
                call_count += 1

                if call_count <= 2:
                    # First two calls: return action that will fail
                    mock_result = Mock()
                    mock_result.success = True
                    content = (
                        '{"thought": "Try tool", "action": "read", '
                        '"action_input": {}, "is_final": false}'
                    )
                    mock_result.value = {"content": content}
                    return mock_result
                else:
                    # Third call: return final answer
                    mock_result = Mock()
                    mock_result.success = True
                    content = '{"thought": "Done", "final_answer": "Success", "is_final": true}'
                    mock_result.value = {"content": content}
                    return mock_result

            mock_engine.call_llm = AsyncMock(side_effect=mock_llm_call)

            # Mock tool call to fail twice then succeed
            tool_call_count = 0

            async def mock_tool_call(*args, **kwargs):
                nonlocal tool_call_count
                tool_call_count += 1

                mock_result = Mock()
                if tool_call_count <= 2:
                    mock_result.success = False
                    mock_result.error = "Timeout"
                    mock_result.value = None
                else:
                    mock_result.success = True
                    mock_result.value = {"data": "success"}
                    mock_result.error = None
                return mock_result

            mock_engine.call_tool = AsyncMock(side_effect=mock_tool_call)

            events = []
            async for event in executor.execute("test request", "task-1", "session-1"):
                events.append(event)

        # Should have retried and eventually succeeded
        message_events = [e for e in events if isinstance(e, TaskMessageEvent)]
        observation_messages = [
            e for e in message_events if any("Observation" in part.text for part in e.message_parts)
        ]

        # Should have at least 2 retry observations
        retry_observations = [
            e
            for e in observation_messages
            if any("Retry attempt" in part.text for part in e.message_parts)
        ]
        assert len(retry_observations) >= 1

    @pytest.mark.asyncio
    async def test_error_recovery_suggests_alternative_after_max_retries(
        self,
        mock_skill: Skill,
        mock_tool_registry: ToolRegistry,
        mock_tool_executor: ToolExecutor,
        mock_context_loader: ContextLoader,
        mock_string_substitutor: StringSubstitutor,
    ) -> None:
        """After max retries, should suggest alternative approach."""
        config = AutonomousConfig(max_retries_per_tool=2)
        executor = AutonomousSkillExecutor(
            skill=mock_skill,
            tool_registry=mock_tool_registry,
            tool_executor=mock_tool_executor,
            config=config,
            context_loader=mock_context_loader,
            string_substitutor=mock_string_substitutor,
        )

        # Mock the ReasoningEngine
        with patch("omniforge.skills.autonomous_executor.ReasoningEngine") as mock_engine_class:
            mock_engine = Mock()
            mock_engine_class.return_value = mock_engine

            call_count = 0

            async def mock_llm_call(*args, **kwargs):
                nonlocal call_count
                call_count += 1

                if call_count <= 3:
                    # First three calls: keep trying same tool
                    mock_result = Mock()
                    mock_result.success = True
                    content = (
                        '{"thought": "Try tool", "action": "read", '
                        '"action_input": {}, "is_final": false}'
                    )
                    mock_result.value = {"content": content}
                    return mock_result
                else:
                    # Fourth call: return final answer
                    mock_result = Mock()
                    mock_result.success = True
                    content = (
                        '{"thought": "Give up", "final_answer": "Cannot complete", '
                        '"is_final": true}'
                    )
                    mock_result.value = {"content": content}
                    return mock_result

            mock_engine.call_llm = AsyncMock(side_effect=mock_llm_call)

            # Mock tool call to always fail
            async def mock_tool_call(*args, **kwargs):
                mock_result = Mock()
                mock_result.success = False
                mock_result.error = "Timeout error"
                mock_result.value = None
                return mock_result

            mock_engine.call_tool = AsyncMock(side_effect=mock_tool_call)

            events = []
            async for event in executor.execute("test request", "task-1", "session-1"):
                events.append(event)

        # Should suggest alternative after max retries
        message_events = [e for e in events if isinstance(e, TaskMessageEvent)]
        observation_messages = [
            e for e in message_events if any("Observation" in part.text for part in e.message_parts)
        ]

        # Should have message suggesting alternative approach
        alternative_suggestions = [
            e
            for e in observation_messages
            if any(
                "completely different" in part.text.lower() or "alternative" in part.text.lower()
                for part in e.message_parts
            )
        ]
        assert len(alternative_suggestions) >= 1

    @pytest.mark.asyncio
    async def test_partial_results_accumulated(
        self,
        mock_skill: Skill,
        mock_tool_registry: ToolRegistry,
        mock_tool_executor: ToolExecutor,
        mock_context_loader: ContextLoader,
        mock_string_substitutor: StringSubstitutor,
    ) -> None:
        """Partial results should be accumulated during execution."""
        config = AutonomousConfig(max_iterations=3)
        executor = AutonomousSkillExecutor(
            skill=mock_skill,
            tool_registry=mock_tool_registry,
            tool_executor=mock_tool_executor,
            config=config,
            context_loader=mock_context_loader,
            string_substitutor=mock_string_substitutor,
        )

        # Mock the ReasoningEngine
        with patch("omniforge.skills.autonomous_executor.ReasoningEngine") as mock_engine_class:
            mock_engine = Mock()
            mock_engine_class.return_value = mock_engine

            # Mock LLM to return actions (no final answer)
            mock_llm_result = Mock()
            mock_llm_result.success = True
            content = (
                '{"thought": "Processing", "action": "read", '
                '"action_input": {}, "is_final": false}'
            )
            mock_llm_result.value = {"content": content}
            mock_engine.call_llm = AsyncMock(return_value=mock_llm_result)

            # Mock tool call to succeed with meaningful results
            call_count = 0

            async def mock_tool_call(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                mock_result = Mock()
                mock_result.success = True
                mock_result.value = {"step": call_count, "data": f"result_{call_count}"}
                mock_result.error = None
                return mock_result

            mock_engine.call_tool = AsyncMock(side_effect=mock_tool_call)

            events = []
            async for event in executor.execute("test request", "task-1", "session-1"):
                events.append(event)

        # Should have partial results or completion message at the end
        message_events = [e for e in events if isinstance(e, TaskMessageEvent)]

        # Check for either "partial", "incomplete", or "unable to complete" messages
        completion_messages = [
            e
            for e in message_events
            if any(
                keyword in part.text.lower()
                for keyword in ["partial", "incomplete", "unable to complete"]
                for part in e.message_parts
            )
        ]

        # At minimum, should emit a message about task state when max iterations reached
        assert (
            len(completion_messages) >= 1 or len(message_events) >= 6
        )  # 3 iterations * 2 messages each

    @pytest.mark.asyncio
    async def test_partial_results_returned_in_sync_execution(
        self,
        mock_skill: Skill,
        mock_tool_registry: ToolRegistry,
        mock_tool_executor: ToolExecutor,
        mock_context_loader: ContextLoader,
        mock_string_substitutor: StringSubstitutor,
    ) -> None:
        """execute_sync should return partial results when task incomplete."""
        config = AutonomousConfig(max_iterations=2)
        executor = AutonomousSkillExecutor(
            skill=mock_skill,
            tool_registry=mock_tool_registry,
            tool_executor=mock_tool_executor,
            config=config,
            context_loader=mock_context_loader,
            string_substitutor=mock_string_substitutor,
        )

        # Mock the ReasoningEngine
        with patch("omniforge.skills.autonomous_executor.ReasoningEngine") as mock_engine_class:
            mock_engine = Mock()
            mock_engine_class.return_value = mock_engine

            # Mock LLM to never complete
            mock_llm_result = Mock()
            mock_llm_result.success = True
            content = (
                '{"thought": "Processing", "action": "read", '
                '"action_input": {}, "is_final": false}'
            )
            mock_llm_result.value = {"content": content}
            mock_engine.call_llm = AsyncMock(return_value=mock_llm_result)

            # Mock tool call to succeed
            mock_tool_result = Mock()
            mock_tool_result.success = True
            mock_tool_result.value = {"data": "meaningful result"}
            mock_tool_result.error = None
            mock_engine.call_tool = AsyncMock(return_value=mock_tool_result)

            result = await executor.execute_sync("test request", "task-1", "session-1")

        # Should have partial results or mention of partial completion
        assert result.success is False  # Did not complete fully
        assert "partial" in result.result.lower() or result.partial_results

    @pytest.mark.asyncio
    async def test_failed_approaches_tracked(
        self,
        mock_skill: Skill,
        mock_tool_registry: ToolRegistry,
        mock_tool_executor: ToolExecutor,
        mock_context_loader: ContextLoader,
        mock_string_substitutor: StringSubstitutor,
    ) -> None:
        """Failed approaches should be tracked to prevent infinite loops."""
        config = AutonomousConfig(max_retries_per_tool=2, max_iterations=5)
        executor = AutonomousSkillExecutor(
            skill=mock_skill,
            tool_registry=mock_tool_registry,
            tool_executor=mock_tool_executor,
            config=config,
            context_loader=mock_context_loader,
            string_substitutor=mock_string_substitutor,
        )

        # Mock the ReasoningEngine
        with patch("omniforge.skills.autonomous_executor.ReasoningEngine") as mock_engine_class:
            mock_engine = Mock()
            mock_engine_class.return_value = mock_engine

            call_count = 0

            async def mock_llm_call(*args, **kwargs):
                nonlocal call_count
                call_count += 1

                if call_count <= 4:
                    # Keep trying same tool with same error
                    mock_result = Mock()
                    mock_result.success = True
                    content = (
                        '{"thought": "Try again", "action": "read", '
                        '"action_input": {"file": "test.txt"}, "is_final": false}'
                    )
                    mock_result.value = {"content": content}
                    return mock_result
                else:
                    # Eventually give up
                    mock_result = Mock()
                    mock_result.success = True
                    content = (
                        '{"thought": "Cannot complete", "final_answer": "Failed", '
                        '"is_final": true}'
                    )
                    mock_result.value = {"content": content}
                    return mock_result

            mock_engine.call_llm = AsyncMock(side_effect=mock_llm_call)

            # Mock tool call to always fail with same error
            async def mock_tool_call(*args, **kwargs):
                mock_result = Mock()
                mock_result.success = False
                mock_result.error = "File not found: test.txt"
                mock_result.value = None
                return mock_result

            mock_engine.call_tool = AsyncMock(side_effect=mock_tool_call)

            events = []
            async for event in executor.execute("test request", "task-1", "session-1"):
                events.append(event)

        # Should track failed approaches and eventually suggest alternative
        message_events = [e for e in events if isinstance(e, TaskMessageEvent)]
        observation_messages = [
            e for e in message_events if any("Observation" in part.text for part in e.message_parts)
        ]

        # Should have both retry messages and alternative suggestion
        has_retry = any(
            any("Retry attempt" in part.text for part in e.message_parts)
            for e in observation_messages
        )
        has_alternative = any(
            any("completely different" in part.text.lower() for part in e.message_parts)
            for e in observation_messages
        )

        assert has_retry or has_alternative

    @pytest.mark.asyncio
    async def test_is_meaningful_result(
        self,
        mock_skill: Skill,
        mock_tool_registry: ToolRegistry,
        mock_tool_executor: ToolExecutor,
    ) -> None:
        """_is_meaningful_result should correctly identify meaningful results."""
        executor = AutonomousSkillExecutor(
            skill=mock_skill,
            tool_registry=mock_tool_registry,
            tool_executor=mock_tool_executor,
        )

        # Test meaningful string result
        result1 = Mock()
        result1.success = True
        result1.value = "This is a meaningful result with content"
        assert executor._is_meaningful_result(result1) is True

        # Test short string (not meaningful)
        result2 = Mock()
        result2.success = True
        result2.value = "short"
        assert executor._is_meaningful_result(result2) is False

        # Test meaningful dict
        result3 = Mock()
        result3.success = True
        result3.value = {"key": "value", "data": "content"}
        assert executor._is_meaningful_result(result3) is True

        # Test empty dict (not meaningful)
        result4 = Mock()
        result4.success = True
        result4.value = {}
        assert executor._is_meaningful_result(result4) is False

        # Test meaningful list
        result5 = Mock()
        result5.success = True
        result5.value = [1, 2, 3]
        assert executor._is_meaningful_result(result5) is True

        # Test empty list (not meaningful)
        result6 = Mock()
        result6.success = True
        result6.value = []
        assert executor._is_meaningful_result(result6) is False

        # Test failed result
        result7 = Mock()
        result7.success = False
        result7.value = None
        assert executor._is_meaningful_result(result7) is False

    @pytest.mark.asyncio
    async def test_summarize_result(
        self,
        mock_skill: Skill,
        mock_tool_registry: ToolRegistry,
        mock_tool_executor: ToolExecutor,
    ) -> None:
        """_summarize_result should create concise summaries."""
        executor = AutonomousSkillExecutor(
            skill=mock_skill,
            tool_registry=mock_tool_registry,
            tool_executor=mock_tool_executor,
        )

        # Test string result
        result1 = Mock()
        result1.value = "Test result content"
        summary1 = executor._summarize_result("read", result1)
        assert "read" in summary1
        assert "Test result content" in summary1

        # Test long string (truncated)
        result2 = Mock()
        result2.value = "x" * 200
        summary2 = executor._summarize_result("read", result2)
        assert "truncated" in summary2

        # Test dict result
        result3 = Mock()
        result3.value = {"key1": "val1", "key2": "val2"}
        summary3 = executor._summarize_result("fetch", result3)
        assert "fetch" in summary3
        assert "2 items" in summary3

        # Test list result
        result4 = Mock()
        result4.value = [1, 2, 3, 4, 5]
        summary4 = executor._summarize_result("query", result4)
        assert "query" in summary4
        assert "5 items" in summary4

    @pytest.mark.asyncio
    async def test_synthesize_partial_results(
        self,
        mock_skill: Skill,
        mock_tool_registry: ToolRegistry,
        mock_tool_executor: ToolExecutor,
    ) -> None:
        """_synthesize_partial_results should create readable synthesis."""
        from omniforge.skills.config import ExecutionState

        executor = AutonomousSkillExecutor(
            skill=mock_skill,
            tool_registry=mock_tool_registry,
            tool_executor=mock_tool_executor,
        )

        # Test with no partial results
        state1 = ExecutionState(error_count=3)
        synthesis1 = executor._synthesize_partial_results(state1)
        assert "Unable to complete" in synthesis1
        assert "3 errors" in synthesis1

        # Test with partial results
        state2 = ExecutionState(
            partial_results=["Step 1: Read file", "Step 2: Process data"], error_count=2
        )
        synthesis2 = executor._synthesize_partial_results(state2)
        assert "Completed 2" in synthesis2
        assert "Step 1: Read file" in synthesis2
        assert "Step 2: Process data" in synthesis2
        assert "2 errors" in synthesis2

    @pytest.mark.asyncio
    async def test_is_meaningful_result_with_other_types(
        self,
        mock_skill: Skill,
        mock_tool_registry: ToolRegistry,
        mock_tool_executor: ToolExecutor,
    ) -> None:
        """_is_meaningful_result should handle other types (not str/dict/list)."""
        executor = AutonomousSkillExecutor(
            skill=mock_skill,
            tool_registry=mock_tool_registry,
            tool_executor=mock_tool_executor,
        )

        # Test with integer
        result1 = Mock()
        result1.success = True
        result1.value = 42
        assert executor._is_meaningful_result(result1) is True

        # Test with boolean
        result2 = Mock()
        result2.success = True
        result2.value = True
        assert executor._is_meaningful_result(result2) is True

        # Test with None value
        result3 = Mock()
        result3.success = True
        result3.value = None
        assert executor._is_meaningful_result(result3) is False

    @pytest.mark.asyncio
    async def test_summarize_result_with_large_dict(
        self,
        mock_skill: Skill,
        mock_tool_registry: ToolRegistry,
        mock_tool_executor: ToolExecutor,
    ) -> None:
        """_summarize_result should truncate keys for large dicts."""
        executor = AutonomousSkillExecutor(
            skill=mock_skill,
            tool_registry=mock_tool_registry,
            tool_executor=mock_tool_executor,
        )

        # Test dict with more than 3 keys
        result = Mock()
        result.value = {"key1": "val1", "key2": "val2", "key3": "val3", "key4": "val4"}
        summary = executor._summarize_result("fetch", result)
        assert "fetch" in summary
        assert "4 items" in summary
        assert "..." in summary  # Keys should be truncated

    @pytest.mark.asyncio
    async def test_summarize_result_with_other_types(
        self,
        mock_skill: Skill,
        mock_tool_registry: ToolRegistry,
        mock_tool_executor: ToolExecutor,
    ) -> None:
        """_summarize_result should handle other types (not str/dict/list)."""
        executor = AutonomousSkillExecutor(
            skill=mock_skill,
            tool_registry=mock_tool_registry,
            tool_executor=mock_tool_executor,
        )

        # Test with integer
        result1 = Mock()
        result1.value = 12345
        summary1 = executor._summarize_result("calculate", result1)
        assert "calculate" in summary1
        assert "12345" in summary1

        # Test with custom object
        class CustomObject:
            def __str__(self):
                return "CustomObject with lots of data " + "x" * 200

        result2 = Mock()
        result2.value = CustomObject()
        summary2 = executor._summarize_result("process", result2)
        assert "process" in summary2
        # Should be truncated to 100 chars
        assert len(summary2) < 150


class TestEdgeCases:
    """Test suite for edge cases and error paths."""

    @pytest.mark.asyncio
    async def test_execute_handles_general_exception(
        self,
        mock_skill: Skill,
        mock_tool_registry: ToolRegistry,
        mock_tool_executor: ToolExecutor,
        mock_context_loader: ContextLoader,
        mock_string_substitutor: StringSubstitutor,
    ) -> None:
        """Execute should handle general exceptions in execution pipeline."""
        executor = AutonomousSkillExecutor(
            skill=mock_skill,
            tool_registry=mock_tool_registry,
            tool_executor=mock_tool_executor,
            context_loader=mock_context_loader,
            string_substitutor=mock_string_substitutor,
        )

        # Mock to raise exception during ReasoningEngine initialization
        with patch("omniforge.skills.autonomous_executor.ReasoningEngine") as mock_engine_class:
            mock_engine_class.side_effect = RuntimeError("Unexpected error")

            events = []
            async for event in executor.execute("test request", "task-1", "session-1"):
                events.append(event)

        # Should emit error event
        error_events = [e for e in events if isinstance(e, TaskErrorEvent)]
        assert len(error_events) >= 1
        assert "Unexpected error" in error_events[0].error_message

        # Should end with failed state
        assert isinstance(events[-1], TaskDoneEvent)
        assert events[-1].final_state == TaskState.FAILED

    @pytest.mark.asyncio
    async def test_execute_handles_invalid_json_response(
        self,
        mock_skill: Skill,
        mock_tool_registry: ToolRegistry,
        mock_tool_executor: ToolExecutor,
        mock_context_loader: ContextLoader,
        mock_string_substitutor: StringSubstitutor,
    ) -> None:
        """Execute should handle LLM responses that are not valid JSON."""
        executor = AutonomousSkillExecutor(
            skill=mock_skill,
            tool_registry=mock_tool_registry,
            tool_executor=mock_tool_executor,
            context_loader=mock_context_loader,
            string_substitutor=mock_string_substitutor,
        )

        # Mock the ReasoningEngine
        with patch("omniforge.skills.autonomous_executor.ReasoningEngine") as mock_engine_class:
            mock_engine = Mock()
            mock_engine_class.return_value = mock_engine

            call_count = 0

            async def mock_llm_call(*args, **kwargs):
                nonlocal call_count
                call_count += 1

                if call_count == 1:
                    # First: return invalid JSON (plain text)
                    mock_result = Mock()
                    mock_result.success = True
                    mock_result.value = {"content": "I am thinking about the problem"}
                    return mock_result
                else:
                    # Then: return valid response
                    mock_result = Mock()
                    mock_result.success = True
                    content = (
                        '{"thought": "Done", "final_answer": "Success", "is_final": true}'
                    )
                    mock_result.value = {"content": content}
                    return mock_result

            mock_engine.call_llm = AsyncMock(side_effect=mock_llm_call)

            events = []
            async for event in executor.execute("test request", "task-1", "session-1"):
                events.append(event)

        # Should emit error for invalid response
        error_events = [e for e in events if isinstance(e, TaskErrorEvent)]
        assert len(error_events) >= 1
        assert any("no action" in e.error_message.lower() for e in error_events)

    @pytest.mark.asyncio
    async def test_execute_handles_tool_exception(
        self,
        mock_skill: Skill,
        mock_tool_registry: ToolRegistry,
        mock_tool_executor: ToolExecutor,
        mock_context_loader: ContextLoader,
        mock_string_substitutor: StringSubstitutor,
    ) -> None:
        """Execute should handle exceptions raised during tool execution."""
        executor = AutonomousSkillExecutor(
            skill=mock_skill,
            tool_registry=mock_tool_registry,
            tool_executor=mock_tool_executor,
            context_loader=mock_context_loader,
            string_substitutor=mock_string_substitutor,
        )

        # Mock the ReasoningEngine
        with patch("omniforge.skills.autonomous_executor.ReasoningEngine") as mock_engine_class:
            mock_engine = Mock()
            mock_engine_class.return_value = mock_engine

            call_count = 0

            async def mock_llm_call(*args, **kwargs):
                nonlocal call_count
                call_count += 1

                if call_count == 1:
                    # First: return action that will raise exception
                    mock_result = Mock()
                    mock_result.success = True
                    content = (
                        '{"thought": "Try tool", "action": "read", '
                        '"action_input": {}, "is_final": false}'
                    )
                    mock_result.value = {"content": content}
                    return mock_result
                else:
                    # Then: return final answer
                    mock_result = Mock()
                    mock_result.success = True
                    content = '{"thought": "Done", "final_answer": "Recovered", "is_final": true}'
                    mock_result.value = {"content": content}
                    return mock_result

            mock_engine.call_llm = AsyncMock(side_effect=mock_llm_call)

            # Mock tool call to raise exception
            async def mock_tool_call(*args, **kwargs):
                raise ValueError("Tool execution failed")

            mock_engine.call_tool = AsyncMock(side_effect=mock_tool_call)

            events = []
            async for event in executor.execute("test request", "task-1", "session-1"):
                events.append(event)

        # Should emit error event for tool exception
        error_events = [e for e in events if isinstance(e, TaskErrorEvent)]
        assert len(error_events) >= 1
        assert any("Tool execution failed" in e.error_message for e in error_events)

        # Should continue and complete after exception
        assert isinstance(events[-1], TaskDoneEvent)
        assert events[-1].final_state == TaskState.COMPLETED

    @pytest.mark.asyncio
    async def test_build_system_prompt_with_tool_definition_error(
        self,
        mock_skill: Skill,
        mock_tool_registry: ToolRegistry,
        mock_tool_executor: ToolExecutor,
        mock_context_loader: ContextLoader,
    ) -> None:
        """System prompt building should handle tool definition errors gracefully."""

        # Mock tool registry to raise error for one tool
        def mock_get_definition(name):
            if name == "read":
                raise RuntimeError("Tool definition error")
            return ToolDefinition(
                name=name,
                type=ToolType.FILE_WRITE,
                description="Tool",
                parameters=[],
            )

        mock_tool_registry.get_definition.side_effect = mock_get_definition

        executor = AutonomousSkillExecutor(
            skill=mock_skill,
            tool_registry=mock_tool_registry,
            tool_executor=mock_tool_executor,
            context_loader=mock_context_loader,
        )

        processed_content = "Test instructions"
        # Should not raise exception even if tool definition fails
        prompt = await executor._build_system_prompt(processed_content)

        # Should still have prompt with other tools
        assert "test-skill" in prompt
        assert "Test instructions" in prompt

    @pytest.mark.asyncio
    async def test_preprocess_content_with_undefined_variables(
        self,
        mock_skill: Skill,
        mock_tool_registry: ToolRegistry,
        mock_tool_executor: ToolExecutor,
    ) -> None:
        """Preprocess should log warning for undefined variables."""
        # Create skill with undefined variable
        skill_with_undefined = Skill(
            metadata=SkillMetadata(
                name="test-skill",
                description="Test skill",
                allowed_tools=["read"],
            ),
            content="Test instructions with $UNDEFINED_VAR",
            path=Path("/tmp/test-skill/SKILL.md"),
            base_path=Path("/tmp/test-skill"),
            storage_layer="global",
        )

        executor = AutonomousSkillExecutor(
            skill=skill_with_undefined,
            tool_registry=mock_tool_registry,
            tool_executor=mock_tool_executor,
        )

        # This should log a warning but not raise
        processed = await executor._preprocess_content(
            user_request="test data",
            session_id="session-123",
            tenant_id="tenant-1",
        )

        # Content should still be processed
        assert "test data" in processed

    @pytest.mark.asyncio
    async def test_handle_tool_error_with_long_error_message(
        self,
        mock_skill: Skill,
        mock_tool_registry: ToolRegistry,
        mock_tool_executor: ToolExecutor,
    ) -> None:
        """_handle_tool_error should truncate very long error messages for approach tracking."""
        from omniforge.skills.config import ExecutionState

        config = AutonomousConfig(max_retries_per_tool=2)
        executor = AutonomousSkillExecutor(
            skill=mock_skill,
            tool_registry=mock_tool_registry,
            tool_executor=mock_tool_executor,
            config=config,
        )

        state = ExecutionState()

        # Create very long error message
        long_error = "x" * 500

        observation = await executor._handle_tool_error(
            tool_name="read",
            error=long_error,
            state=state,
            tool_args={},
        )

        # Should suggest retry
        assert "Retry attempt" in observation
        # Error should be included
        assert long_error in observation

    @pytest.mark.asyncio
    async def test_llm_call_with_error_recovery_disabled(
        self,
        mock_skill: Skill,
        mock_tool_registry: ToolRegistry,
        mock_tool_executor: ToolExecutor,
        mock_context_loader: ContextLoader,
        mock_string_substitutor: StringSubstitutor,
    ) -> None:
        """Execute should fail immediately when error recovery is disabled and LLM fails."""
        config = AutonomousConfig(enable_error_recovery=False)
        executor = AutonomousSkillExecutor(
            skill=mock_skill,
            tool_registry=mock_tool_registry,
            tool_executor=mock_tool_executor,
            config=config,
            context_loader=mock_context_loader,
            string_substitutor=mock_string_substitutor,
        )

        # Mock the ReasoningEngine to fail LLM call
        with patch("omniforge.skills.autonomous_executor.ReasoningEngine") as mock_engine_class:
            mock_engine = Mock()
            mock_engine_class.return_value = mock_engine

            mock_llm_result = Mock()
            mock_llm_result.success = False
            mock_llm_result.error = "LLM service unavailable"
            mock_llm_result.value = None
            mock_engine.call_llm = AsyncMock(return_value=mock_llm_result)

            events = []
            async for event in executor.execute("test request", "task-1", "session-1"):
                events.append(event)

        # Should fail immediately without retrying
        assert isinstance(events[-1], TaskDoneEvent)
        assert events[-1].final_state == TaskState.FAILED

    @pytest.mark.asyncio
    async def test_llm_failure_with_error_recovery_enabled(
        self,
        mock_skill: Skill,
        mock_tool_registry: ToolRegistry,
        mock_tool_executor: ToolExecutor,
        mock_context_loader: ContextLoader,
        mock_string_substitutor: StringSubstitutor,
    ) -> None:
        """Execute should continue after LLM failure when error recovery is enabled."""
        config = AutonomousConfig(enable_error_recovery=True, max_iterations=5)
        executor = AutonomousSkillExecutor(
            skill=mock_skill,
            tool_registry=mock_tool_registry,
            tool_executor=mock_tool_executor,
            config=config,
            context_loader=mock_context_loader,
            string_substitutor=mock_string_substitutor,
        )

        # Mock the ReasoningEngine
        with patch("omniforge.skills.autonomous_executor.ReasoningEngine") as mock_engine_class:
            mock_engine = Mock()
            mock_engine_class.return_value = mock_engine

            call_count = 0

            async def mock_llm_call(*args, **kwargs):
                nonlocal call_count
                call_count += 1

                if call_count <= 2:
                    # First two calls: fail
                    mock_result = Mock()
                    mock_result.success = False
                    mock_result.error = "LLM service temporary failure"
                    mock_result.value = None
                    return mock_result
                else:
                    # Subsequent calls: succeed
                    mock_result = Mock()
                    mock_result.success = True
                    content = (
                        '{"thought": "Done", "final_answer": "Success", "is_final": true}'
                    )
                    mock_result.value = {"content": content}
                    return mock_result

            mock_engine.call_llm = AsyncMock(side_effect=mock_llm_call)

            events = []
            async for event in executor.execute("test request", "task-1", "session-1"):
                events.append(event)

        # Should have LLM error events
        error_events = [e for e in events if isinstance(e, TaskErrorEvent)]
        assert len(error_events) >= 2
        llm_errors = [e for e in error_events if "LLM call failed" in e.error_message]
        assert len(llm_errors) >= 2

        # Should eventually complete after recovery
        assert isinstance(events[-1], TaskDoneEvent)
        assert events[-1].final_state == TaskState.COMPLETED

    @pytest.mark.asyncio
    async def test_timeout_with_error_recovery_enabled(
        self,
        mock_skill: Skill,
        mock_tool_registry: ToolRegistry,
        mock_tool_executor: ToolExecutor,
        mock_context_loader: ContextLoader,
        mock_string_substitutor: StringSubstitutor,
    ) -> None:
        """Execute should continue after timeout when error recovery is enabled."""
        config = AutonomousConfig(
            timeout_per_iteration_ms=1000,
            enable_error_recovery=True,
            max_iterations=3,
        )
        executor = AutonomousSkillExecutor(
            skill=mock_skill,
            tool_registry=mock_tool_registry,
            tool_executor=mock_tool_executor,
            config=config,
            context_loader=mock_context_loader,
            string_substitutor=mock_string_substitutor,
        )

        # Mock the ReasoningEngine
        with patch("omniforge.skills.autonomous_executor.ReasoningEngine") as mock_engine_class:
            mock_engine = Mock()
            mock_engine_class.return_value = mock_engine

            call_count = 0

            async def mock_llm_call(*args, **kwargs):
                nonlocal call_count
                call_count += 1

                if call_count == 1:
                    # First call: timeout
                    await asyncio.sleep(2)
                    mock_result = Mock()
                    mock_result.success = True
                    mock_result.value = {"content": '{"is_final": false}'}
                    return mock_result
                else:
                    # Subsequent calls: succeed quickly
                    mock_result = Mock()
                    mock_result.success = True
                    content = (
                        '{"thought": "Done", "final_answer": "Success", "is_final": true}'
                    )
                    mock_result.value = {"content": content}
                    return mock_result

            mock_engine.call_llm = AsyncMock(side_effect=mock_llm_call)

            events = []
            async for event in executor.execute("test request", "task-1", "session-1"):
                events.append(event)

        # Should have timeout error
        error_events = [e for e in events if isinstance(e, TaskErrorEvent)]
        assert len(error_events) >= 1
        timeout_errors = [e for e in error_events if "timeout" in e.error_message.lower()]
        assert len(timeout_errors) >= 1

        # Should eventually complete despite timeout
        assert isinstance(events[-1], TaskDoneEvent)


class TestModelSelection:
    """Test suite for model selection per skill (TASK-010)."""

    def test_model_from_skill_metadata(
        self,
        mock_skill: Skill,
        mock_tool_registry: ToolRegistry,
        mock_tool_executor: ToolExecutor,
    ) -> None:
        """Skill with model in metadata should use that model."""
        # Set model in skill metadata
        mock_skill.metadata.model = "haiku"

        executor = AutonomousSkillExecutor(
            skill=mock_skill,
            tool_registry=mock_tool_registry,
            tool_executor=mock_tool_executor,
        )

        assert executor._resolve_model() == "claude-haiku-4"

    def test_model_default_fallback(
        self,
        mock_skill: Skill,
        mock_tool_registry: ToolRegistry,
        mock_tool_executor: ToolExecutor,
    ) -> None:
        """Skills without model should use default."""
        # Ensure no model in metadata or config
        mock_skill.metadata.model = None

        executor = AutonomousSkillExecutor(
            skill=mock_skill,
            tool_registry=mock_tool_registry,
            tool_executor=mock_tool_executor,
        )

        assert executor._resolve_model() == "claude-sonnet-4"

    def test_model_config_override(
        self,
        mock_skill: Skill,
        mock_tool_registry: ToolRegistry,
        mock_tool_executor: ToolExecutor,
    ) -> None:
        """Config override should take precedence over skill metadata."""
        # Set different models in skill and config
        mock_skill.metadata.model = "haiku"
        config = AutonomousConfig(model="opus")

        executor = AutonomousSkillExecutor(
            skill=mock_skill,
            tool_registry=mock_tool_registry,
            tool_executor=mock_tool_executor,
            config=config,
        )

        assert executor._resolve_model() == "claude-opus-4"

    def test_model_unknown_passthrough(
        self,
        mock_skill: Skill,
        mock_tool_registry: ToolRegistry,
        mock_tool_executor: ToolExecutor,
    ) -> None:
        """Unknown model names should be used as-is for future compatibility."""
        # Set a future model name
        mock_skill.metadata.model = "claude-3-5-sonnet-20241022"

        executor = AutonomousSkillExecutor(
            skill=mock_skill,
            tool_registry=mock_tool_registry,
            tool_executor=mock_tool_executor,
        )

        assert executor._resolve_model() == "claude-3-5-sonnet-20241022"

    def test_model_case_insensitive(
        self,
        mock_skill: Skill,
        mock_tool_registry: ToolRegistry,
        mock_tool_executor: ToolExecutor,
    ) -> None:
        """Model names should be case-insensitive."""
        # Set model in different cases
        mock_skill.metadata.model = "HAIKU"

        executor = AutonomousSkillExecutor(
            skill=mock_skill,
            tool_registry=mock_tool_registry,
            tool_executor=mock_tool_executor,
        )

        assert executor._resolve_model() == "claude-haiku-4"

    def test_model_all_variants(
        self,
        mock_skill: Skill,
        mock_tool_registry: ToolRegistry,
        mock_tool_executor: ToolExecutor,
    ) -> None:
        """All model variants should map correctly."""
        test_cases = [
            ("haiku", "claude-haiku-4"),
            ("sonnet", "claude-sonnet-4"),
            ("opus", "claude-opus-4"),
            ("SONNET", "claude-sonnet-4"),  # case insensitive
        ]

        for model_hint, expected_model in test_cases:
            mock_skill.metadata.model = model_hint

            executor = AutonomousSkillExecutor(
                skill=mock_skill,
                tool_registry=mock_tool_registry,
                tool_executor=mock_tool_executor,
            )

            assert (
                executor._resolve_model() == expected_model
            ), f"Model hint '{model_hint}' should resolve to '{expected_model}'"

    @pytest.mark.asyncio
    async def test_execute_sync_tracks_model_used(
        self,
        mock_skill: Skill,
        mock_tool_registry: ToolRegistry,
        mock_tool_executor: ToolExecutor,
        mock_context_loader: ContextLoader,
        mock_string_substitutor: StringSubstitutor,
    ) -> None:
        """execute_sync should track which model was used in metrics."""
        # Set specific model
        mock_skill.metadata.model = "haiku"

        executor = AutonomousSkillExecutor(
            skill=mock_skill,
            tool_registry=mock_tool_registry,
            tool_executor=mock_tool_executor,
            context_loader=mock_context_loader,
            string_substitutor=mock_string_substitutor,
        )

        # Mock the ReasoningEngine to return final answer
        with patch("omniforge.skills.autonomous_executor.ReasoningEngine") as mock_engine_class:
            mock_engine = Mock()
            mock_engine_class.return_value = mock_engine

            mock_llm_result = Mock()
            mock_llm_result.success = True
            mock_llm_result.value = {
                "content": '{"thought": "Done", "final_answer": "Success!", "is_final": true}'
            }
            mock_engine.call_llm = AsyncMock(return_value=mock_llm_result)

            result = await executor.execute_sync("test request", "task-1", "session-1")

        # Verify model is tracked in metrics
        assert result.metrics.model_used == "claude-haiku-4"
        # Verify estimated cost is calculated
        assert result.metrics.estimated_cost_per_call > 0

    @pytest.mark.asyncio
    async def test_execute_sync_tracks_estimated_cost(
        self,
        mock_skill: Skill,
        mock_tool_registry: ToolRegistry,
        mock_tool_executor: ToolExecutor,
        mock_context_loader: ContextLoader,
        mock_string_substitutor: StringSubstitutor,
    ) -> None:
        """execute_sync should calculate estimated cost based on model."""
        # Set expensive model
        mock_skill.metadata.model = "opus"

        executor = AutonomousSkillExecutor(
            skill=mock_skill,
            tool_registry=mock_tool_registry,
            tool_executor=mock_tool_executor,
            context_loader=mock_context_loader,
            string_substitutor=mock_string_substitutor,
        )

        # Mock the ReasoningEngine to return final answer
        with patch("omniforge.skills.autonomous_executor.ReasoningEngine") as mock_engine_class:
            mock_engine = Mock()
            mock_engine_class.return_value = mock_engine

            mock_llm_result = Mock()
            mock_llm_result.success = True
            mock_llm_result.value = {
                "content": '{"thought": "Done", "final_answer": "Success!", "is_final": true}'
            }
            mock_engine.call_llm = AsyncMock(return_value=mock_llm_result)

            result = await executor.execute_sync("test request", "task-1", "session-1")

        # Verify opus costs more than haiku
        # Opus: (15 + 75) / 2 / 1M = 0.000045
        assert result.metrics.estimated_cost_per_call > 0.00004
        assert result.metrics.model_used == "claude-opus-4"


class TestConversationHistory:
    """Test suite for conversation history management."""

    @pytest.mark.asyncio
    async def test_execute_maintains_conversation_history(
        self,
        mock_skill: Skill,
        mock_tool_registry: ToolRegistry,
        mock_tool_executor: ToolExecutor,
        mock_context_loader: ContextLoader,
        mock_string_substitutor: StringSubstitutor,
    ) -> None:
        """Conversation should accumulate across iterations."""
        executor = AutonomousSkillExecutor(
            skill=mock_skill,
            tool_registry=mock_tool_registry,
            tool_executor=mock_tool_executor,
            context_loader=mock_context_loader,
            string_substitutor=mock_string_substitutor,
        )

        # Mock the ReasoningEngine
        with patch("omniforge.skills.autonomous_executor.ReasoningEngine") as mock_engine_class:
            mock_engine = Mock()
            mock_engine_class.return_value = mock_engine

            llm_call_count = 0
            conversation_sizes = []

            async def mock_llm_call(*args, **kwargs):
                nonlocal llm_call_count
                llm_call_count += 1

                # Track conversation size (messages parameter)
                messages = kwargs.get("messages", [])
                conversation_sizes.append(len(messages))

                if llm_call_count <= 2:
                    # First two calls: return actions
                    mock_result = Mock()
                    mock_result.success = True
                    content = (
                        '{"thought": "Processing", "action": "read", '
                        '"action_input": {}, "is_final": false}'
                    )
                    mock_result.value = {"content": content}
                    return mock_result
                else:
                    # Third call: return final answer
                    mock_result = Mock()
                    mock_result.success = True
                    content = '{"thought": "Done", "final_answer": "Complete", "is_final": true}'
                    mock_result.value = {"content": content}
                    return mock_result

            mock_engine.call_llm = AsyncMock(side_effect=mock_llm_call)

            # Mock tool call to succeed
            mock_tool_result = Mock()
            mock_tool_result.success = True
            mock_tool_result.value = {"data": "test"}
            mock_tool_result.error = None
            mock_engine.call_tool = AsyncMock(return_value=mock_tool_result)

            events = []
            async for event in executor.execute("test request", "task-1", "session-1"):
                events.append(event)

        # Conversation should grow with each iteration
        # Call 1: [user message with request]
        # Call 2: [user, assistant, user (observation)]
        # Call 3: [user, assistant, user, assistant, user (observation)]
        assert len(conversation_sizes) == 3
        assert conversation_sizes[0] == 1  # Initial user message
        assert conversation_sizes[1] == 3  # After first action+observation
        assert conversation_sizes[2] == 5  # After second action+observation

    @pytest.mark.asyncio
    async def test_execute_includes_json_reminder_in_conversation(
        self,
        mock_skill: Skill,
        mock_tool_registry: ToolRegistry,
        mock_tool_executor: ToolExecutor,
        mock_context_loader: ContextLoader,
        mock_string_substitutor: StringSubstitutor,
    ) -> None:
        """Initial conversation should include JSON format reminder."""
        executor = AutonomousSkillExecutor(
            skill=mock_skill,
            tool_registry=mock_tool_registry,
            tool_executor=mock_tool_executor,
            context_loader=mock_context_loader,
            string_substitutor=mock_string_substitutor,
        )

        # Mock the ReasoningEngine
        with patch("omniforge.skills.autonomous_executor.ReasoningEngine") as mock_engine_class:
            mock_engine = Mock()
            mock_engine_class.return_value = mock_engine

            initial_message = None

            async def mock_llm_call(*args, **kwargs):
                nonlocal initial_message
                messages = kwargs.get("messages", [])
                if not initial_message and messages:
                    initial_message = messages[0]["content"]

                mock_result = Mock()
                mock_result.success = True
                mock_result.value = {
                    "content": '{"thought": "Done", "final_answer": "Success", "is_final": true}'
                }
                return mock_result

            mock_engine.call_llm = AsyncMock(side_effect=mock_llm_call)

            events = []
            async for event in executor.execute("test request", "task-1", "session-1"):
                events.append(event)

        # Initial message should include JSON reminder
        assert initial_message is not None
        assert "test request" in initial_message
        assert "JSON" in initial_message or "json" in initial_message

    @pytest.mark.asyncio
    async def test_execute_truncates_large_tool_results(
        self,
        mock_skill: Skill,
        mock_tool_registry: ToolRegistry,
        mock_tool_executor: ToolExecutor,
        mock_context_loader: ContextLoader,
        mock_string_substitutor: StringSubstitutor,
    ) -> None:
        """Large tool results should be truncated in conversation context."""
        executor = AutonomousSkillExecutor(
            skill=mock_skill,
            tool_registry=mock_tool_registry,
            tool_executor=mock_tool_executor,
            context_loader=mock_context_loader,
            string_substitutor=mock_string_substitutor,
        )

        # Mock the ReasoningEngine
        with patch("omniforge.skills.autonomous_executor.ReasoningEngine") as mock_engine_class:
            mock_engine = Mock()
            mock_engine_class.return_value = mock_engine

            call_count = 0
            observations = []

            async def mock_llm_call(*args, **kwargs):
                nonlocal call_count
                call_count += 1

                # Capture observations from conversation
                messages = kwargs.get("messages", [])
                for msg in messages:
                    if msg["role"] == "user" and "Observation:" in msg["content"]:
                        observations.append(msg["content"])

                if call_count == 1:
                    # First call: return action
                    mock_result = Mock()
                    mock_result.success = True
                    content = (
                        '{"thought": "Read", "action": "read", '
                        '"action_input": {}, "is_final": false}'
                    )
                    mock_result.value = {"content": content}
                    return mock_result
                else:
                    # Second call: return final answer
                    mock_result = Mock()
                    mock_result.success = True
                    content = '{"thought": "Done", "final_answer": "Complete", "is_final": true}'
                    mock_result.value = {"content": content}
                    return mock_result

            mock_engine.call_llm = AsyncMock(side_effect=mock_llm_call)

            # Mock tool call to return very large result
            mock_tool_result = Mock()
            mock_tool_result.success = True
            mock_tool_result.value = "x" * 5000  # Very large result
            mock_tool_result.error = None
            mock_engine.call_tool = AsyncMock(return_value=mock_tool_result)

            events = []
            async for event in executor.execute("test request", "task-1", "session-1"):
                events.append(event)

        # Should have truncated the observation
        assert len(observations) > 0
        last_observation = observations[-1]
        assert "truncated" in last_observation.lower()
        # Should be much shorter than original 5000 chars
        assert len(last_observation) < 3000


class TestExecuteSyncEdgeCases:
    """Test suite for execute_sync edge cases."""

    @pytest.mark.asyncio
    async def test_execute_sync_failure_result(
        self,
        mock_skill: Skill,
        mock_tool_registry: ToolRegistry,
        mock_tool_executor: ToolExecutor,
        mock_context_loader: ContextLoader,
        mock_string_substitutor: StringSubstitutor,
    ) -> None:
        """execute_sync should return failure result when execution fails."""
        config = AutonomousConfig(max_iterations=2, enable_error_recovery=False)
        executor = AutonomousSkillExecutor(
            skill=mock_skill,
            tool_registry=mock_tool_registry,
            tool_executor=mock_tool_executor,
            config=config,
            context_loader=mock_context_loader,
            string_substitutor=mock_string_substitutor,
        )

        # Mock the ReasoningEngine to fail
        with patch("omniforge.skills.autonomous_executor.ReasoningEngine") as mock_engine_class:
            mock_engine = Mock()
            mock_engine_class.return_value = mock_engine

            mock_llm_result = Mock()
            mock_llm_result.success = False
            mock_llm_result.error = "Service unavailable"
            mock_llm_result.value = None
            mock_engine.call_llm = AsyncMock(return_value=mock_llm_result)

            result = await executor.execute_sync("test request", "task-1", "session-1")

        assert result.success is False
        assert result.error is not None
        assert "Service unavailable" in result.error

    @pytest.mark.asyncio
    async def test_execute_sync_includes_iterations(
        self,
        mock_skill: Skill,
        mock_tool_registry: ToolRegistry,
        mock_tool_executor: ToolExecutor,
        mock_context_loader: ContextLoader,
        mock_string_substitutor: StringSubstitutor,
    ) -> None:
        """execute_sync should include iterations count."""
        config = AutonomousConfig(max_iterations=5)
        executor = AutonomousSkillExecutor(
            skill=mock_skill,
            tool_registry=mock_tool_registry,
            tool_executor=mock_tool_executor,
            config=config,
            context_loader=mock_context_loader,
            string_substitutor=mock_string_substitutor,
        )

        # Mock the ReasoningEngine
        with patch("omniforge.skills.autonomous_executor.ReasoningEngine") as mock_engine_class:
            mock_engine = Mock()
            mock_engine_class.return_value = mock_engine

            call_count = 0

            async def mock_llm_call(*args, **kwargs):
                nonlocal call_count
                call_count += 1

                if call_count <= 3:
                    # First three calls: return actions
                    mock_result = Mock()
                    mock_result.success = True
                    content = (
                        '{"thought": "Processing", "action": "read", '
                        '"action_input": {}, "is_final": false}'
                    )
                    mock_result.value = {"content": content}
                    return mock_result
                else:
                    # Fourth call: return final answer
                    mock_result = Mock()
                    mock_result.success = True
                    content = '{"thought": "Done", "final_answer": "Complete", "is_final": true}'
                    mock_result.value = {"content": content}
                    return mock_result

            mock_engine.call_llm = AsyncMock(side_effect=mock_llm_call)

            # Mock tool call
            mock_tool_result = Mock()
            mock_tool_result.success = True
            mock_tool_result.value = {"data": "test"}
            mock_tool_result.error = None
            mock_engine.call_tool = AsyncMock(return_value=mock_tool_result)

            result = await executor.execute_sync("test request", "task-1", "session-1")

        # Should track iterations (3 actions were taken)
        assert result.iterations_used == 3
        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_sync_with_tool_errors(
        self,
        mock_skill: Skill,
        mock_tool_registry: ToolRegistry,
        mock_tool_executor: ToolExecutor,
        mock_context_loader: ContextLoader,
        mock_string_substitutor: StringSubstitutor,
    ) -> None:
        """execute_sync should handle and complete with tool errors."""
        config = AutonomousConfig(max_retries_per_tool=2)
        executor = AutonomousSkillExecutor(
            skill=mock_skill,
            tool_registry=mock_tool_registry,
            tool_executor=mock_tool_executor,
            config=config,
            context_loader=mock_context_loader,
            string_substitutor=mock_string_substitutor,
        )

        # Mock the ReasoningEngine
        with patch("omniforge.skills.autonomous_executor.ReasoningEngine") as mock_engine_class:
            mock_engine = Mock()
            mock_engine_class.return_value = mock_engine

            call_count = 0

            async def mock_llm_call(*args, **kwargs):
                nonlocal call_count
                call_count += 1

                if call_count <= 2:
                    # First two calls: return actions that will fail
                    mock_result = Mock()
                    mock_result.success = True
                    content = (
                        '{"thought": "Try tool", "action": "read", '
                        '"action_input": {}, "is_final": false}'
                    )
                    mock_result.value = {"content": content}
                    return mock_result
                else:
                    # Third call: return final answer
                    mock_result = Mock()
                    mock_result.success = True
                    content = '{"thought": "Done", "final_answer": "Complete", "is_final": true}'
                    mock_result.value = {"content": content}
                    return mock_result

            mock_engine.call_llm = AsyncMock(side_effect=mock_llm_call)

            # Mock tool call to always fail
            mock_tool_result = Mock()
            mock_tool_result.success = False
            mock_tool_result.error = "File not found"
            mock_tool_result.value = None
            mock_engine.call_tool = AsyncMock(return_value=mock_tool_result)

            result = await executor.execute_sync("test request", "task-1", "session-1")

        # Should still complete despite tool errors
        assert result.success is True
        assert "Complete" in result.result

    @pytest.mark.asyncio
    async def test_execute_sync_parses_partial_results_from_message(
        self,
        mock_skill: Skill,
        mock_tool_registry: ToolRegistry,
        mock_tool_executor: ToolExecutor,
        mock_context_loader: ContextLoader,
        mock_string_substitutor: StringSubstitutor,
    ) -> None:
        """execute_sync should parse partial results from synthesis messages."""
        config = AutonomousConfig(max_iterations=2)
        executor = AutonomousSkillExecutor(
            skill=mock_skill,
            tool_registry=mock_tool_registry,
            tool_executor=mock_tool_executor,
            config=config,
            context_loader=mock_context_loader,
            string_substitutor=mock_string_substitutor,
        )

        # Mock the ReasoningEngine
        with patch("omniforge.skills.autonomous_executor.ReasoningEngine") as mock_engine_class:
            mock_engine = Mock()
            mock_engine_class.return_value = mock_engine

            # Mock LLM to never complete (hit max iterations)
            mock_llm_result = Mock()
            mock_llm_result.success = True
            content = (
                '{"thought": "Processing", "action": "read", '
                '"action_input": {}, "is_final": false}'
            )
            mock_llm_result.value = {"content": content}
            mock_engine.call_llm = AsyncMock(return_value=mock_llm_result)

            # Mock tool call to succeed with meaningful result
            mock_tool_result = Mock()
            mock_tool_result.success = True
            mock_tool_result.value = {"data": "meaningful result"}
            mock_tool_result.error = None
            mock_engine.call_tool = AsyncMock(return_value=mock_tool_result)

            result = await executor.execute_sync("test request", "task-1", "session-1")

        # Should have partial results parsed
        # The synthesis message should contain "partial" or "completed"
        assert result.success is False
        # Should have the partial keyword in result
        assert "partial" in result.result.lower() or "completed" in result.result.lower()

    @pytest.mark.asyncio
    async def test_execute_sync_with_unknown_model_cost(
        self,
        mock_skill: Skill,
        mock_tool_registry: ToolRegistry,
        mock_tool_executor: ToolExecutor,
        mock_context_loader: ContextLoader,
        mock_string_substitutor: StringSubstitutor,
    ) -> None:
        """execute_sync should handle unknown model without crashing on cost calculation."""
        # Set unknown model
        mock_skill.metadata.model = "claude-future-model-xyz"

        executor = AutonomousSkillExecutor(
            skill=mock_skill,
            tool_registry=mock_tool_registry,
            tool_executor=mock_tool_executor,
            context_loader=mock_context_loader,
            string_substitutor=mock_string_substitutor,
        )

        # Mock the ReasoningEngine
        with patch("omniforge.skills.autonomous_executor.ReasoningEngine") as mock_engine_class:
            mock_engine = Mock()
            mock_engine_class.return_value = mock_engine

            mock_llm_result = Mock()
            mock_llm_result.success = True
            mock_llm_result.value = {
                "content": '{"thought": "Done", "final_answer": "Success", "is_final": true}'
            }
            mock_engine.call_llm = AsyncMock(return_value=mock_llm_result)

            result = await executor.execute_sync("test request", "task-1", "session-1")

        # Should complete successfully
        assert result.success is True
        # Model should be tracked
        assert result.metrics.model_used == "claude-future-model-xyz"
        # Cost should be 0 for unknown model
        assert result.metrics.estimated_cost_per_call == 0.0
