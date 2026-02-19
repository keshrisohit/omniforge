"""Tests for reasoning-specific SSE events."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from omniforge.agents.cot.chain import ChainMetrics, ReasoningStep, StepType, ThinkingInfo
from omniforge.agents.cot.events import (
    ChainCompletedEvent,
    ChainFailedEvent,
    ChainStartedEvent,
    ReasoningStepEvent,
)


class TestChainStartedEvent:
    """Tests for ChainStartedEvent model."""

    def test_create_chain_started_event_with_valid_data(self) -> None:
        """ChainStartedEvent should initialize with valid data."""
        now = datetime.now(timezone.utc)
        event = ChainStartedEvent(
            task_id="task-123",
            timestamp=now,
            chain_id="chain-abc",
        )

        assert event.type == "chain_started"
        assert event.task_id == "task-123"
        assert event.timestamp == now
        assert event.chain_id == "chain-abc"

    def test_chain_started_event_type_is_literal(self) -> None:
        """ChainStartedEvent type field should always be 'chain_started'."""
        event = ChainStartedEvent(
            task_id="task-456",
            timestamp=datetime.now(timezone.utc),
            chain_id="chain-def",
        )

        assert event.type == "chain_started"

    def test_chain_started_event_requires_task_id(self) -> None:
        """ChainStartedEvent should require task_id."""
        with pytest.raises(ValidationError):
            ChainStartedEvent(
                timestamp=datetime.now(timezone.utc),
                chain_id="chain-xyz",
            )

    def test_chain_started_event_requires_chain_id(self) -> None:
        """ChainStartedEvent should require chain_id."""
        with pytest.raises(ValidationError):
            ChainStartedEvent(
                task_id="task-789",
                timestamp=datetime.now(timezone.utc),
            )

    def test_chain_started_event_serializes_to_json(self) -> None:
        """ChainStartedEvent should serialize to JSON correctly."""
        event = ChainStartedEvent(
            task_id="task-001",
            timestamp=datetime.now(timezone.utc),
            chain_id="chain-001",
        )

        json_data = event.model_dump(mode="json")

        assert json_data["type"] == "chain_started"
        assert json_data["task_id"] == "task-001"
        assert json_data["chain_id"] == "chain-001"
        assert "timestamp" in json_data

    def test_chain_started_event_deserializes_from_json(self) -> None:
        """ChainStartedEvent should deserialize from JSON correctly."""
        now = datetime.now(timezone.utc)
        json_data = {
            "task_id": "task-002",
            "timestamp": now.isoformat(),
            "chain_id": "chain-002",
        }

        event = ChainStartedEvent.model_validate(json_data)

        assert event.task_id == "task-002"
        assert event.chain_id == "chain-002"
        assert event.type == "chain_started"


class TestReasoningStepEvent:
    """Tests for ReasoningStepEvent model."""

    def test_create_reasoning_step_event_with_valid_data(self) -> None:
        """ReasoningStepEvent should initialize with valid data."""
        now = datetime.now(timezone.utc)
        step = ReasoningStep(
            step_number=0,
            type=StepType.THINKING,
            thinking=ThinkingInfo(content="Analyzing the problem..."),
        )

        event = ReasoningStepEvent(
            task_id="task-123",
            timestamp=now,
            chain_id="chain-abc",
            step=step,
        )

        assert event.type == "reasoning_step"
        assert event.task_id == "task-123"
        assert event.timestamp == now
        assert event.chain_id == "chain-abc"
        assert event.step.type == StepType.THINKING

    def test_reasoning_step_event_type_is_literal(self) -> None:
        """ReasoningStepEvent type field should always be 'reasoning_step'."""
        step = ReasoningStep(
            step_number=1,
            type=StepType.SYNTHESIS,
            synthesis={"content": "Final answer", "sources": []},
        )

        event = ReasoningStepEvent(
            task_id="task-456",
            timestamp=datetime.now(timezone.utc),
            chain_id="chain-def",
            step=step,
        )

        assert event.type == "reasoning_step"

    def test_reasoning_step_event_requires_step(self) -> None:
        """ReasoningStepEvent should require step."""
        with pytest.raises(ValidationError):
            ReasoningStepEvent(
                task_id="task-789",
                timestamp=datetime.now(timezone.utc),
                chain_id="chain-xyz",
            )

    def test_reasoning_step_event_serializes_to_json(self) -> None:
        """ReasoningStepEvent should serialize to JSON correctly."""
        step = ReasoningStep(
            step_number=0,
            type=StepType.THINKING,
            thinking=ThinkingInfo(content="Test thinking", confidence=0.95),
            tokens_used=100,
            cost=0.001,
        )

        event = ReasoningStepEvent(
            task_id="task-001",
            timestamp=datetime.now(timezone.utc),
            chain_id="chain-001",
            step=step,
        )

        json_data = event.model_dump(mode="json")

        assert json_data["type"] == "reasoning_step"
        assert json_data["task_id"] == "task-001"
        assert json_data["chain_id"] == "chain-001"
        assert json_data["step"]["type"] == "thinking"
        assert json_data["step"]["thinking"]["content"] == "Test thinking"
        assert json_data["step"]["tokens_used"] == 100

    def test_reasoning_step_event_deserializes_from_json(self) -> None:
        """ReasoningStepEvent should deserialize from JSON correctly."""
        now = datetime.now(timezone.utc)
        step_id = uuid4()
        json_data = {
            "task_id": "task-002",
            "timestamp": now.isoformat(),
            "chain_id": "chain-002",
            "step": {
                "id": str(step_id),
                "step_number": 0,
                "type": "thinking",
                "timestamp": now.isoformat(),
                "thinking": {"content": "Deserialized thinking"},
                "tokens_used": 50,
                "cost": 0.0005,
            },
        }

        event = ReasoningStepEvent.model_validate(json_data)

        assert event.task_id == "task-002"
        assert event.chain_id == "chain-002"
        assert event.step.type == StepType.THINKING
        assert event.step.thinking is not None
        assert event.step.thinking.content == "Deserialized thinking"


class TestChainCompletedEvent:
    """Tests for ChainCompletedEvent model."""

    def test_create_chain_completed_event_with_valid_data(self) -> None:
        """ChainCompletedEvent should initialize with valid data."""
        now = datetime.now(timezone.utc)
        metrics = ChainMetrics(
            total_steps=10,
            llm_calls=5,
            tool_calls=3,
            total_tokens=1000,
            total_cost=0.05,
        )

        event = ChainCompletedEvent(
            task_id="task-123",
            timestamp=now,
            chain_id="chain-abc",
            metrics=metrics,
        )

        assert event.type == "chain_completed"
        assert event.task_id == "task-123"
        assert event.timestamp == now
        assert event.chain_id == "chain-abc"
        assert event.metrics.total_steps == 10
        assert event.metrics.total_tokens == 1000

    def test_chain_completed_event_type_is_literal(self) -> None:
        """ChainCompletedEvent type field should always be 'chain_completed'."""
        metrics = ChainMetrics()

        event = ChainCompletedEvent(
            task_id="task-456",
            timestamp=datetime.now(timezone.utc),
            chain_id="chain-def",
            metrics=metrics,
        )

        assert event.type == "chain_completed"

    def test_chain_completed_event_requires_metrics(self) -> None:
        """ChainCompletedEvent should require metrics."""
        with pytest.raises(ValidationError):
            ChainCompletedEvent(
                task_id="task-789",
                timestamp=datetime.now(timezone.utc),
                chain_id="chain-xyz",
            )

    def test_chain_completed_event_with_empty_metrics(self) -> None:
        """ChainCompletedEvent should accept empty metrics."""
        metrics = ChainMetrics()

        event = ChainCompletedEvent(
            task_id="task-001",
            timestamp=datetime.now(timezone.utc),
            chain_id="chain-001",
            metrics=metrics,
        )

        assert event.metrics.total_steps == 0
        assert event.metrics.llm_calls == 0
        assert event.metrics.tool_calls == 0
        assert event.metrics.total_tokens == 0
        assert event.metrics.total_cost == 0.0

    def test_chain_completed_event_serializes_to_json(self) -> None:
        """ChainCompletedEvent should serialize to JSON correctly."""
        metrics = ChainMetrics(
            total_steps=15,
            llm_calls=8,
            tool_calls=5,
            total_tokens=2000,
            total_cost=0.1,
        )

        event = ChainCompletedEvent(
            task_id="task-002",
            timestamp=datetime.now(timezone.utc),
            chain_id="chain-002",
            metrics=metrics,
        )

        json_data = event.model_dump(mode="json")

        assert json_data["type"] == "chain_completed"
        assert json_data["task_id"] == "task-002"
        assert json_data["chain_id"] == "chain-002"
        assert json_data["metrics"]["total_steps"] == 15
        assert json_data["metrics"]["llm_calls"] == 8
        assert json_data["metrics"]["total_cost"] == 0.1

    def test_chain_completed_event_deserializes_from_json(self) -> None:
        """ChainCompletedEvent should deserialize from JSON correctly."""
        now = datetime.now(timezone.utc)
        json_data = {
            "task_id": "task-003",
            "timestamp": now.isoformat(),
            "chain_id": "chain-003",
            "metrics": {
                "total_steps": 20,
                "llm_calls": 10,
                "tool_calls": 8,
                "total_tokens": 3000,
                "total_cost": 0.15,
            },
        }

        event = ChainCompletedEvent.model_validate(json_data)

        assert event.task_id == "task-003"
        assert event.chain_id == "chain-003"
        assert event.metrics.total_steps == 20
        assert event.metrics.llm_calls == 10


class TestChainFailedEvent:
    """Tests for ChainFailedEvent model."""

    def test_create_chain_failed_event_with_valid_data(self) -> None:
        """ChainFailedEvent should initialize with valid data."""
        now = datetime.now(timezone.utc)
        event = ChainFailedEvent(
            task_id="task-123",
            timestamp=now,
            chain_id="chain-abc",
            error_code="CHAIN_ERROR_001",
            error_message="Chain execution failed due to timeout",
        )

        assert event.type == "chain_failed"
        assert event.task_id == "task-123"
        assert event.timestamp == now
        assert event.chain_id == "chain-abc"
        assert event.error_code == "CHAIN_ERROR_001"
        assert event.error_message == "Chain execution failed due to timeout"

    def test_chain_failed_event_type_is_literal(self) -> None:
        """ChainFailedEvent type field should always be 'chain_failed'."""
        event = ChainFailedEvent(
            task_id="task-456",
            timestamp=datetime.now(timezone.utc),
            chain_id="chain-def",
            error_code="ERR002",
            error_message="Test error",
        )

        assert event.type == "chain_failed"

    def test_chain_failed_event_requires_error_code(self) -> None:
        """ChainFailedEvent should require error_code."""
        with pytest.raises(ValidationError):
            ChainFailedEvent(
                task_id="task-789",
                timestamp=datetime.now(timezone.utc),
                chain_id="chain-xyz",
                error_message="Missing error code",
            )

    def test_chain_failed_event_requires_error_message(self) -> None:
        """ChainFailedEvent should require error_message."""
        with pytest.raises(ValidationError):
            ChainFailedEvent(
                task_id="task-999",
                timestamp=datetime.now(timezone.utc),
                chain_id="chain-999",
                error_code="ERR003",
            )

    def test_chain_failed_event_serializes_to_json(self) -> None:
        """ChainFailedEvent should serialize to JSON correctly."""
        event = ChainFailedEvent(
            task_id="task-001",
            timestamp=datetime.now(timezone.utc),
            chain_id="chain-001",
            error_code="TIMEOUT",
            error_message="Operation timed out after 30 seconds",
        )

        json_data = event.model_dump(mode="json")

        assert json_data["type"] == "chain_failed"
        assert json_data["task_id"] == "task-001"
        assert json_data["chain_id"] == "chain-001"
        assert json_data["error_code"] == "TIMEOUT"
        assert json_data["error_message"] == "Operation timed out after 30 seconds"

    def test_chain_failed_event_deserializes_from_json(self) -> None:
        """ChainFailedEvent should deserialize from JSON correctly."""
        now = datetime.now(timezone.utc)
        json_data = {
            "task_id": "task-002",
            "timestamp": now.isoformat(),
            "chain_id": "chain-002",
            "error_code": "TOOL_FAILURE",
            "error_message": "Tool execution failed unexpectedly",
        }

        event = ChainFailedEvent.model_validate(json_data)

        assert event.task_id == "task-002"
        assert event.chain_id == "chain-002"
        assert event.error_code == "TOOL_FAILURE"
        assert event.error_message == "Tool execution failed unexpectedly"


class TestEventJsonSerialization:
    """Tests for JSON serialization of all event types."""

    def test_all_events_serialize_and_deserialize_correctly(self) -> None:
        """All event types should round-trip through JSON serialization."""
        now = datetime.now(timezone.utc)

        # Chain started
        started = ChainStartedEvent(
            task_id="task-001",
            timestamp=now,
            chain_id="chain-001",
        )
        started_json = started.model_dump(mode="json")
        started_restored = ChainStartedEvent.model_validate(started_json)
        assert started_restored.chain_id == started.chain_id

        # Reasoning step
        step_event = ReasoningStepEvent(
            task_id="task-001",
            timestamp=now,
            chain_id="chain-001",
            step=ReasoningStep(
                step_number=0,
                type=StepType.THINKING,
                thinking=ThinkingInfo(content="Test"),
            ),
        )
        step_json = step_event.model_dump(mode="json")
        step_restored = ReasoningStepEvent.model_validate(step_json)
        assert step_restored.step.type == StepType.THINKING

        # Chain completed
        completed = ChainCompletedEvent(
            task_id="task-001",
            timestamp=now,
            chain_id="chain-001",
            metrics=ChainMetrics(total_steps=5),
        )
        completed_json = completed.model_dump(mode="json")
        completed_restored = ChainCompletedEvent.model_validate(completed_json)
        assert completed_restored.metrics.total_steps == 5

        # Chain failed
        failed = ChainFailedEvent(
            task_id="task-001",
            timestamp=now,
            chain_id="chain-001",
            error_code="ERR",
            error_message="Failed",
        )
        failed_json = failed.model_dump(mode="json")
        failed_restored = ChainFailedEvent.model_validate(failed_json)
        assert failed_restored.error_code == "ERR"

    def test_event_type_discriminator_works(self) -> None:
        """Event type field should enable discriminated union pattern."""
        events = [
            ChainStartedEvent(
                task_id="task-001",
                timestamp=datetime.now(timezone.utc),
                chain_id="chain-001",
            ),
            ReasoningStepEvent(
                task_id="task-001",
                timestamp=datetime.now(timezone.utc),
                chain_id="chain-001",
                step=ReasoningStep(
                    step_number=0,
                    type=StepType.THINKING,
                    thinking=ThinkingInfo(content="Test"),
                ),
            ),
            ChainCompletedEvent(
                task_id="task-001",
                timestamp=datetime.now(timezone.utc),
                chain_id="chain-001",
                metrics=ChainMetrics(),
            ),
            ChainFailedEvent(
                task_id="task-001",
                timestamp=datetime.now(timezone.utc),
                chain_id="chain-001",
                error_code="ERR",
                error_message="Failed",
            ),
        ]

        types = [event.type for event in events]

        assert types == [
            "chain_started",
            "reasoning_step",
            "chain_completed",
            "chain_failed",
        ]
