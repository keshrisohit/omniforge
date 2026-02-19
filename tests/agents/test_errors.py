"""Tests for agent error classes."""

import pytest

from omniforge.agents.errors import (
    AgentError,
    AgentNotFoundError,
    AgentProcessingError,
    SkillNotFoundError,
    TaskNotFoundError,
    TaskStateError,
)


class TestAgentError:
    """Tests for AgentError base class."""

    def test_create_agent_error_with_all_fields(self) -> None:
        """Should create error with message, code, and status code."""
        error = AgentError(message="Something went wrong", code="generic_error", status_code=500)

        assert error.message == "Something went wrong"
        assert error.code == "generic_error"
        assert error.status_code == 500
        assert str(error) == "Something went wrong"

    def test_agent_error_inherits_from_exception(self) -> None:
        """Should be instance of Exception."""
        error = AgentError(message="Test", code="test", status_code=500)
        assert isinstance(error, Exception)

    def test_agent_error_can_be_raised_and_caught(self) -> None:
        """Should be raisable and catchable."""
        with pytest.raises(AgentError) as exc_info:
            raise AgentError(message="Test error", code="test", status_code=500)

        assert exc_info.value.message == "Test error"
        assert exc_info.value.code == "test"


class TestAgentNotFoundError:
    """Tests for AgentNotFoundError."""

    def test_create_agent_not_found_error(self) -> None:
        """Should create error with agent ID."""
        error = AgentNotFoundError(agent_id="agent-123")

        assert error.message == "Agent 'agent-123' not found"
        assert error.code == "agent_not_found"
        assert error.status_code == 404
        assert error.agent_id == "agent-123"

    def test_agent_not_found_error_inherits_from_agent_error(self) -> None:
        """Should be instance of AgentError."""
        error = AgentNotFoundError(agent_id="agent-123")
        assert isinstance(error, AgentError)

    def test_agent_not_found_error_can_be_caught_as_agent_error(self) -> None:
        """Should be catchable as AgentError."""
        with pytest.raises(AgentError) as exc_info:
            raise AgentNotFoundError(agent_id="agent-123")

        assert exc_info.value.status_code == 404

    def test_agent_not_found_error_with_uuid(self) -> None:
        """Should handle UUID-style agent IDs."""
        error = AgentNotFoundError(agent_id="550e8400-e29b-41d4-a716-446655440000")

        assert "550e8400-e29b-41d4-a716-446655440000" in error.message
        assert error.agent_id == "550e8400-e29b-41d4-a716-446655440000"


class TestTaskNotFoundError:
    """Tests for TaskNotFoundError."""

    def test_create_task_not_found_error(self) -> None:
        """Should create error with task ID."""
        error = TaskNotFoundError(task_id="task-456")

        assert error.message == "Task 'task-456' not found"
        assert error.code == "task_not_found"
        assert error.status_code == 404
        assert error.task_id == "task-456"

    def test_task_not_found_error_inherits_from_agent_error(self) -> None:
        """Should be instance of AgentError."""
        error = TaskNotFoundError(task_id="task-456")
        assert isinstance(error, AgentError)

    def test_task_not_found_error_with_special_characters(self) -> None:
        """Should handle task IDs with special characters."""
        error = TaskNotFoundError(task_id="task:run-analysis#1")

        assert "task:run-analysis#1" in error.message
        assert error.task_id == "task:run-analysis#1"


class TestTaskStateError:
    """Tests for TaskStateError."""

    def test_create_task_state_error(self) -> None:
        """Should create error with task ID, state, and operation."""
        error = TaskStateError(task_id="task-789", current_state="completed", operation="cancel")

        assert error.message == ("Cannot perform 'cancel' on task 'task-789' in state 'completed'")
        assert error.code == "task_state_error"
        assert error.status_code == 409
        assert error.task_id == "task-789"
        assert error.current_state == "completed"
        assert error.operation == "cancel"

    def test_task_state_error_inherits_from_agent_error(self) -> None:
        """Should be instance of AgentError."""
        error = TaskStateError(task_id="task-1", current_state="running", operation="start")
        assert isinstance(error, AgentError)

    def test_task_state_error_with_different_states(self) -> None:
        """Should handle various task states."""
        states = ["pending", "running", "paused", "completed", "failed", "cancelled"]

        for state in states:
            error = TaskStateError(task_id="task-1", current_state=state, operation="delete")
            assert state in error.message
            assert error.current_state == state

    def test_task_state_error_with_different_operations(self) -> None:
        """Should handle various operations."""
        operations = ["start", "pause", "resume", "cancel", "restart"]

        for operation in operations:
            error = TaskStateError(task_id="task-1", current_state="completed", operation=operation)
            assert operation in error.message
            assert error.operation == operation


class TestSkillNotFoundError:
    """Tests for SkillNotFoundError."""

    def test_create_skill_not_found_error_without_agent_id(self) -> None:
        """Should create error with skill name only."""
        error = SkillNotFoundError(skill_name="code-analysis")

        assert error.message == "Skill 'code-analysis' not found"
        assert error.code == "skill_not_found"
        assert error.status_code == 404
        assert error.skill_name == "code-analysis"
        assert error.agent_id is None

    def test_create_skill_not_found_error_with_agent_id(self) -> None:
        """Should create error with skill name and agent ID."""
        error = SkillNotFoundError(skill_name="code-analysis", agent_id="agent-123")

        assert error.message == "Skill 'code-analysis' not found in agent 'agent-123'"
        assert error.code == "skill_not_found"
        assert error.status_code == 404
        assert error.skill_name == "code-analysis"
        assert error.agent_id == "agent-123"

    def test_skill_not_found_error_inherits_from_agent_error(self) -> None:
        """Should be instance of AgentError."""
        error = SkillNotFoundError(skill_name="test")
        assert isinstance(error, AgentError)

    def test_skill_not_found_error_with_hyphenated_name(self) -> None:
        """Should handle skill names with hyphens."""
        error = SkillNotFoundError(skill_name="analyze-code-quality", agent_id="agent-1")

        assert "analyze-code-quality" in error.message
        assert error.skill_name == "analyze-code-quality"


class TestAgentProcessingError:
    """Tests for AgentProcessingError."""

    def test_create_agent_processing_error_without_agent_id(self) -> None:
        """Should create error with message only."""
        error = AgentProcessingError(message="Failed to process task")

        assert error.message == "Failed to process task"
        assert error.code == "agent_processing_error"
        assert error.status_code == 500
        assert error.agent_id is None

    def test_create_agent_processing_error_with_agent_id(self) -> None:
        """Should create error with message and agent ID."""
        error = AgentProcessingError(message="Failed to process task", agent_id="agent-123")

        assert error.message == "Agent 'agent-123': Failed to process task"
        assert error.code == "agent_processing_error"
        assert error.status_code == 500
        assert error.agent_id == "agent-123"

    def test_agent_processing_error_inherits_from_agent_error(self) -> None:
        """Should be instance of AgentError."""
        error = AgentProcessingError(message="Test")
        assert isinstance(error, AgentError)

    def test_agent_processing_error_with_detailed_message(self) -> None:
        """Should preserve detailed error messages."""
        detailed_msg = "Task execution failed: Invalid input format at line 42"
        error = AgentProcessingError(message=detailed_msg, agent_id="agent-456")

        assert detailed_msg in error.message
        assert error.agent_id == "agent-456"


class TestErrorHierarchy:
    """Tests for error hierarchy and inheritance."""

    def test_all_errors_inherit_from_agent_error(self) -> None:
        """All specific errors should inherit from AgentError."""
        errors = [
            AgentNotFoundError(agent_id="test"),
            TaskNotFoundError(task_id="test"),
            TaskStateError(task_id="test", current_state="running", operation="cancel"),
            SkillNotFoundError(skill_name="test"),
            AgentProcessingError(message="test"),
        ]

        for error in errors:
            assert isinstance(error, AgentError)
            assert isinstance(error, Exception)

    def test_all_errors_have_required_attributes(self) -> None:
        """All errors should have message, code, and status_code."""
        errors = [
            AgentNotFoundError(agent_id="test"),
            TaskNotFoundError(task_id="test"),
            TaskStateError(task_id="test", current_state="running", operation="cancel"),
            SkillNotFoundError(skill_name="test"),
            AgentProcessingError(message="test"),
        ]

        for error in errors:
            assert hasattr(error, "message")
            assert hasattr(error, "code")
            assert hasattr(error, "status_code")
            assert isinstance(error.message, str)
            assert isinstance(error.code, str)
            assert isinstance(error.status_code, int)

    def test_error_codes_are_snake_case(self) -> None:
        """All error codes should be in snake_case format."""
        errors = [
            AgentNotFoundError(agent_id="test"),
            TaskNotFoundError(task_id="test"),
            TaskStateError(task_id="test", current_state="running", operation="cancel"),
            SkillNotFoundError(skill_name="test"),
            AgentProcessingError(message="test"),
        ]

        for error in errors:
            # Check that code is lowercase and uses underscores
            assert error.code == error.code.lower()
            assert " " not in error.code
            assert "-" not in error.code

    def test_http_status_codes_are_appropriate(self) -> None:
        """HTTP status codes should be appropriate for error types."""
        # 404 errors
        not_found_errors = [
            AgentNotFoundError(agent_id="test"),
            TaskNotFoundError(task_id="test"),
            SkillNotFoundError(skill_name="test"),
        ]
        for error in not_found_errors:
            assert error.status_code == 404

        # 409 error
        conflict_error = TaskStateError(task_id="test", current_state="running", operation="cancel")
        assert conflict_error.status_code == 409

        # 500 error
        server_error = AgentProcessingError(message="test")
        assert server_error.status_code == 500

    def test_catch_specific_error_type(self) -> None:
        """Should be able to catch specific error types."""
        with pytest.raises(AgentNotFoundError) as exc_info:
            raise AgentNotFoundError(agent_id="agent-123")

        assert exc_info.value.agent_id == "agent-123"

    def test_catch_as_base_agent_error(self) -> None:
        """Should be able to catch all agent errors as AgentError."""
        errors = [
            AgentNotFoundError(agent_id="test"),
            TaskNotFoundError(task_id="test"),
            TaskStateError(task_id="test", current_state="running", operation="cancel"),
            SkillNotFoundError(skill_name="test"),
            AgentProcessingError(message="test"),
        ]

        for error in errors:
            with pytest.raises(AgentError):
                raise error
