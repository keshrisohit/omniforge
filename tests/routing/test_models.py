"""Tests for routing models."""

import pytest

from omniforge.routing.models import ActionType, RoutingDecision


class TestActionType:
    """Tests for ActionType enum."""

    def test_action_type_values(self) -> None:
        """ActionType should have all expected values."""
        assert ActionType.CREATE_AGENT.value == "create_agent"
        assert ActionType.CREATE_SKILL.value == "create_skill"
        assert ActionType.EXECUTE_TASK.value == "execute_task"
        assert ActionType.UPDATE_AGENT.value == "update_agent"
        assert ActionType.QUERY_INFO.value == "query_info"
        assert ActionType.MANAGE_PLATFORM.value == "manage_platform"
        assert ActionType.UNKNOWN.value == "unknown"

    def test_action_type_is_string_enum(self) -> None:
        """ActionType should be a string enum."""
        assert isinstance(ActionType.CREATE_AGENT, str)
        assert ActionType.CREATE_AGENT == "create_agent"

    def test_action_type_iteration(self) -> None:
        """ActionType should be iterable."""
        action_types = list(ActionType)
        assert len(action_types) == 7
        assert ActionType.CREATE_AGENT in action_types
        assert ActionType.UNKNOWN in action_types

    def test_action_type_from_string(self) -> None:
        """ActionType should be creatable from string values."""
        assert ActionType("create_agent") == ActionType.CREATE_AGENT
        assert ActionType("execute_task") == ActionType.EXECUTE_TASK
        assert ActionType("unknown") == ActionType.UNKNOWN

    def test_action_type_invalid_value_raises_error(self) -> None:
        """ActionType should raise error for invalid values."""
        with pytest.raises(ValueError):
            ActionType("invalid_action")


class TestRoutingDecision:
    """Tests for RoutingDecision dataclass."""

    def test_routing_decision_creation_minimal(self) -> None:
        """RoutingDecision should be created with minimal required fields."""
        decision = RoutingDecision(
            action_type=ActionType.CREATE_AGENT,
            confidence=0.95,
        )

        assert decision.action_type == ActionType.CREATE_AGENT
        assert decision.confidence == 0.95
        assert decision.target_agent_id is None
        assert decision.reasoning == ""
        assert decision.entities == {}

    def test_routing_decision_creation_full(self) -> None:
        """RoutingDecision should be created with all fields."""
        entities = {"agent_name": "test-agent", "purpose": "testing"}
        decision = RoutingDecision(
            action_type=ActionType.EXECUTE_TASK,
            confidence=0.87,
            target_agent_id="agent-123",
            reasoning="High confidence match based on keywords",
            entities=entities,
        )

        assert decision.action_type == ActionType.EXECUTE_TASK
        assert decision.confidence == 0.87
        assert decision.target_agent_id == "agent-123"
        assert decision.reasoning == "High confidence match based on keywords"
        assert decision.entities == entities

    def test_routing_decision_entities_default_empty_dict(self) -> None:
        """RoutingDecision entities should default to empty dict."""
        decision = RoutingDecision(
            action_type=ActionType.QUERY_INFO,
            confidence=0.75,
        )

        assert decision.entities == {}
        assert isinstance(decision.entities, dict)

    def test_routing_decision_entities_mutable(self) -> None:
        """RoutingDecision entities should be mutable."""
        decision = RoutingDecision(
            action_type=ActionType.CREATE_SKILL,
            confidence=0.90,
        )

        decision.entities["skill_name"] = "data-processor"
        decision.entities["tools"] = ["python", "pandas"]

        assert decision.entities["skill_name"] == "data-processor"
        assert decision.entities["tools"] == ["python", "pandas"]

    def test_routing_decision_confidence_range(self) -> None:
        """RoutingDecision should accept various confidence values."""
        low_confidence = RoutingDecision(
            action_type=ActionType.UNKNOWN,
            confidence=0.0,
        )
        mid_confidence = RoutingDecision(
            action_type=ActionType.QUERY_INFO,
            confidence=0.5,
        )
        high_confidence = RoutingDecision(
            action_type=ActionType.CREATE_AGENT,
            confidence=1.0,
        )

        assert low_confidence.confidence == 0.0
        assert mid_confidence.confidence == 0.5
        assert high_confidence.confidence == 1.0

    def test_routing_decision_with_different_action_types(self) -> None:
        """RoutingDecision should work with all ActionType values."""
        for action_type in ActionType:
            decision = RoutingDecision(
                action_type=action_type,
                confidence=0.8,
            )
            assert decision.action_type == action_type

    def test_routing_decision_equality(self) -> None:
        """RoutingDecision instances with same values should be equal."""
        decision1 = RoutingDecision(
            action_type=ActionType.CREATE_AGENT,
            confidence=0.95,
            target_agent_id="agent-1",
            reasoning="Test",
            entities={"key": "value"},
        )
        decision2 = RoutingDecision(
            action_type=ActionType.CREATE_AGENT,
            confidence=0.95,
            target_agent_id="agent-1",
            reasoning="Test",
            entities={"key": "value"},
        )

        assert decision1 == decision2

    def test_routing_decision_inequality(self) -> None:
        """RoutingDecision instances with different values should not be equal."""
        decision1 = RoutingDecision(
            action_type=ActionType.CREATE_AGENT,
            confidence=0.95,
        )
        decision2 = RoutingDecision(
            action_type=ActionType.CREATE_SKILL,
            confidence=0.95,
        )

        assert decision1 != decision2

    def test_routing_decision_repr(self) -> None:
        """RoutingDecision should have a readable string representation."""
        decision = RoutingDecision(
            action_type=ActionType.EXECUTE_TASK,
            confidence=0.85,
            reasoning="Test reasoning",
        )

        repr_str = repr(decision)
        assert "RoutingDecision" in repr_str
        assert "EXECUTE_TASK" in repr_str
        assert "0.85" in repr_str
