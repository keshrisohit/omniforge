"""Tests for prompt management enums."""

from omniforge.prompts.enums import (
    ExperimentStatus,
    MergeBehavior,
    PromptLayer,
    ValidationSeverity,
)


class TestPromptLayer:
    """Tests for PromptLayer enum."""

    def test_all_layers_defined(self) -> None:
        """All expected prompt layers should be defined."""
        assert PromptLayer.SYSTEM == "system"
        assert PromptLayer.TENANT == "tenant"
        assert PromptLayer.FEATURE == "feature"
        assert PromptLayer.AGENT == "agent"
        assert PromptLayer.USER == "user"

    def test_layer_count(self) -> None:
        """Should have exactly 5 layers."""
        assert len(PromptLayer) == 5

    def test_layers_are_strings(self) -> None:
        """All layer values should be strings."""
        for layer in PromptLayer:
            assert isinstance(layer.value, str)


class TestMergeBehavior:
    """Tests for MergeBehavior enum."""

    def test_all_behaviors_defined(self) -> None:
        """All expected merge behaviors should be defined."""
        assert MergeBehavior.APPEND == "append"
        assert MergeBehavior.PREPEND == "prepend"
        assert MergeBehavior.REPLACE == "replace"
        assert MergeBehavior.INJECT == "inject"

    def test_behavior_count(self) -> None:
        """Should have exactly 4 merge behaviors."""
        assert len(MergeBehavior) == 4

    def test_behaviors_are_strings(self) -> None:
        """All behavior values should be strings."""
        for behavior in MergeBehavior:
            assert isinstance(behavior.value, str)


class TestExperimentStatus:
    """Tests for ExperimentStatus enum."""

    def test_all_statuses_defined(self) -> None:
        """All expected experiment statuses should be defined."""
        assert ExperimentStatus.DRAFT == "draft"
        assert ExperimentStatus.RUNNING == "running"
        assert ExperimentStatus.PAUSED == "paused"
        assert ExperimentStatus.COMPLETED == "completed"
        assert ExperimentStatus.CANCELLED == "cancelled"

    def test_status_count(self) -> None:
        """Should have exactly 5 statuses."""
        assert len(ExperimentStatus) == 5

    def test_statuses_are_strings(self) -> None:
        """All status values should be strings."""
        for status in ExperimentStatus:
            assert isinstance(status.value, str)


class TestValidationSeverity:
    """Tests for ValidationSeverity enum."""

    def test_all_severities_defined(self) -> None:
        """All expected validation severities should be defined."""
        assert ValidationSeverity.ERROR == "error"
        assert ValidationSeverity.WARNING == "warning"
        assert ValidationSeverity.INFO == "info"

    def test_severity_count(self) -> None:
        """Should have exactly 3 severities."""
        assert len(ValidationSeverity) == 3

    def test_severities_are_strings(self) -> None:
        """All severity values should be strings."""
        for severity in ValidationSeverity:
            assert isinstance(severity.value, str)
