"""Tests for prompt management models."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from omniforge.prompts.enums import (
    ExperimentStatus,
    MergeBehavior,
    PromptLayer,
)
from omniforge.prompts.models import (
    ComposedPrompt,
    ExperimentVariant,
    MergePointDefinition,
    Prompt,
    PromptExperiment,
    PromptVersion,
    VariableSchema,
)


class TestMergePointDefinition:
    """Tests for MergePointDefinition model."""

    def test_valid_merge_point(self) -> None:
        """Should create merge point with valid data."""
        merge_point = MergePointDefinition(
            name="header",
            behavior=MergeBehavior.APPEND,
            required=True,
            locked=False,
            description="Header merge point",
        )

        assert merge_point.name == "header"
        assert merge_point.behavior == MergeBehavior.APPEND
        assert merge_point.required is True
        assert merge_point.locked is False
        assert merge_point.description == "Header merge point"

    def test_defaults(self) -> None:
        """Should use default values when not provided."""
        merge_point = MergePointDefinition(
            name="footer",
            behavior=MergeBehavior.PREPEND,
        )

        assert merge_point.required is False
        assert merge_point.locked is False
        assert merge_point.description is None

    def test_name_with_underscores(self) -> None:
        """Should accept names with underscores."""
        merge_point = MergePointDefinition(
            name="merge_point_name",
            behavior=MergeBehavior.INJECT,
        )
        assert merge_point.name == "merge_point_name"

    def test_name_with_hyphens(self) -> None:
        """Should accept names with hyphens."""
        merge_point = MergePointDefinition(
            name="merge-point-name",
            behavior=MergeBehavior.REPLACE,
        )
        assert merge_point.name == "merge-point-name"

    def test_invalid_name_with_special_chars(self) -> None:
        """Should reject names with invalid special characters."""
        with pytest.raises(ValidationError, match="alphanumeric"):
            MergePointDefinition(
                name="invalid@name",
                behavior=MergeBehavior.APPEND,
            )

    def test_empty_name(self) -> None:
        """Should reject empty name."""
        with pytest.raises(ValidationError):
            MergePointDefinition(
                name="",
                behavior=MergeBehavior.APPEND,
            )


class TestVariableSchema:
    """Tests for VariableSchema model."""

    def test_valid_schema(self) -> None:
        """Should create variable schema with valid data."""
        schema = VariableSchema(
            properties={
                "user_name": {"type": "string"},
                "age": {"type": "integer"},
            },
            required=["user_name"],
        )

        assert "user_name" in schema.properties
        assert "age" in schema.properties
        assert schema.required == ["user_name"]

    def test_empty_schema(self) -> None:
        """Should create empty schema with defaults."""
        schema = VariableSchema()

        assert schema.properties == {}
        assert schema.required == []

    def test_required_variable_not_in_properties(self) -> None:
        """Should reject required variable not defined in properties."""
        with pytest.raises(ValidationError, match="must be defined in properties"):
            VariableSchema(
                properties={"user_name": {"type": "string"}},
                required=["user_name", "age"],
            )


class TestPrompt:
    """Tests for Prompt model."""

    def test_valid_prompt(self) -> None:
        """Should create prompt with valid data."""
        prompt = Prompt(
            id="prompt-123",
            layer=PromptLayer.AGENT,
            scope_id="agent-456",
            name="Test Prompt",
            content="Hello, {user_name}!",
            tenant_id="tenant-789",
        )

        assert prompt.id == "prompt-123"
        assert prompt.layer == PromptLayer.AGENT
        assert prompt.scope_id == "agent-456"
        assert prompt.name == "Test Prompt"
        assert prompt.content == "Hello, {user_name}!"
        assert prompt.tenant_id == "tenant-789"

    def test_defaults(self) -> None:
        """Should use default values when not provided."""
        prompt = Prompt(
            id="prompt-123",
            layer=PromptLayer.SYSTEM,
            scope_id="global",
            name="System Prompt",
            content="You are a helpful assistant.",
        )

        assert prompt.merge_points == []
        assert prompt.variables_schema is None
        assert prompt.parent_prompt_id is None
        assert prompt.is_locked is False
        assert prompt.tenant_id is None
        assert prompt.version == 1
        assert isinstance(prompt.created_at, datetime)
        assert isinstance(prompt.updated_at, datetime)

    def test_empty_content_rejected(self) -> None:
        """Should reject empty content."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            Prompt(
                id="prompt-123",
                layer=PromptLayer.USER,
                scope_id="user-789",
                name="Empty Prompt",
                content="",
            )

    def test_whitespace_only_content_rejected(self) -> None:
        """Should reject whitespace-only content."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            Prompt(
                id="prompt-123",
                layer=PromptLayer.USER,
                scope_id="user-789",
                name="Whitespace Prompt",
                content="   \n\t  ",
            )

    def test_duplicate_merge_point_names_rejected(self) -> None:
        """Should reject duplicate merge point names."""
        with pytest.raises(ValidationError, match="Duplicate merge point names"):
            Prompt(
                id="prompt-123",
                layer=PromptLayer.FEATURE,
                scope_id="feature-abc",
                name="Duplicate Merge Points",
                content="Content with merge points",
                merge_points=[
                    MergePointDefinition(name="header", behavior=MergeBehavior.APPEND),
                    MergePointDefinition(name="header", behavior=MergeBehavior.PREPEND),
                ],
            )

    def test_unique_merge_points_accepted(self) -> None:
        """Should accept unique merge point names."""
        prompt = Prompt(
            id="prompt-123",
            layer=PromptLayer.FEATURE,
            scope_id="feature-abc",
            name="Multiple Merge Points",
            content="Content with merge points",
            merge_points=[
                MergePointDefinition(name="header", behavior=MergeBehavior.APPEND),
                MergePointDefinition(name="footer", behavior=MergeBehavior.PREPEND),
            ],
        )

        assert len(prompt.merge_points) == 2


class TestPromptVersion:
    """Tests for PromptVersion model."""

    def test_valid_version(self) -> None:
        """Should create prompt version with valid data."""
        version = PromptVersion(
            id="version-123",
            prompt_id="prompt-456",
            version_number=5,
            content="Version 5 content",
            change_message="Updated greeting",
            created_by="user-789",
        )

        assert version.id == "version-123"
        assert version.prompt_id == "prompt-456"
        assert version.version_number == 5
        assert version.content == "Version 5 content"
        assert version.change_message == "Updated greeting"
        assert version.created_by == "user-789"

    def test_defaults(self) -> None:
        """Should use default values when not provided."""
        version = PromptVersion(
            id="version-123",
            prompt_id="prompt-456",
            version_number=1,
            content="Initial version",
        )

        assert version.merge_points == []
        assert version.variables_schema is None
        assert version.change_message is None
        assert version.created_by is None
        assert isinstance(version.created_at, datetime)

    def test_version_number_must_be_positive(self) -> None:
        """Should reject version number less than 1."""
        with pytest.raises(ValidationError):
            PromptVersion(
                id="version-123",
                prompt_id="prompt-456",
                version_number=0,
                content="Invalid version",
            )

    def test_empty_content_rejected(self) -> None:
        """Should reject empty content."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            PromptVersion(
                id="version-123",
                prompt_id="prompt-456",
                version_number=1,
                content="",
            )


class TestExperimentVariant:
    """Tests for ExperimentVariant model."""

    def test_valid_variant(self) -> None:
        """Should create experiment variant with valid data."""
        variant = ExperimentVariant(
            id="variant-123",
            name="Control",
            prompt_version_id="version-456",
            traffic_percentage=50.0,
            metrics={"click_rate": 0.15, "conversion": 100},
        )

        assert variant.id == "variant-123"
        assert variant.name == "Control"
        assert variant.prompt_version_id == "version-456"
        assert variant.traffic_percentage == 50.0
        assert variant.metrics == {"click_rate": 0.15, "conversion": 100}

    def test_traffic_percentage_boundaries(self) -> None:
        """Should accept traffic percentage between 0 and 100."""
        variant_zero = ExperimentVariant(
            id="variant-1",
            name="Zero Traffic",
            prompt_version_id="version-1",
            traffic_percentage=0.0,
        )
        assert variant_zero.traffic_percentage == 0.0

        variant_hundred = ExperimentVariant(
            id="variant-2",
            name="Full Traffic",
            prompt_version_id="version-2",
            traffic_percentage=100.0,
        )
        assert variant_hundred.traffic_percentage == 100.0

    def test_traffic_percentage_below_zero_rejected(self) -> None:
        """Should reject traffic percentage below 0."""
        with pytest.raises(ValidationError):
            ExperimentVariant(
                id="variant-1",
                name="Invalid",
                prompt_version_id="version-1",
                traffic_percentage=-1.0,
            )

    def test_traffic_percentage_above_hundred_rejected(self) -> None:
        """Should reject traffic percentage above 100."""
        with pytest.raises(ValidationError):
            ExperimentVariant(
                id="variant-1",
                name="Invalid",
                prompt_version_id="version-1",
                traffic_percentage=101.0,
            )

    def test_traffic_percentage_two_decimals_accepted(self) -> None:
        """Should accept traffic percentage with 2 decimal places."""
        variant = ExperimentVariant(
            id="variant-1",
            name="Precise",
            prompt_version_id="version-1",
            traffic_percentage=33.33,
        )
        assert variant.traffic_percentage == 33.33

    def test_traffic_percentage_more_decimals_rejected(self) -> None:
        """Should reject traffic percentage with more than 2 decimal places."""
        with pytest.raises(ValidationError, match="at most 2 decimal places"):
            ExperimentVariant(
                id="variant-1",
                name="Too Precise",
                prompt_version_id="version-1",
                traffic_percentage=33.333,
            )


class TestPromptExperiment:
    """Tests for PromptExperiment model."""

    def test_valid_experiment(self) -> None:
        """Should create experiment with valid data."""
        experiment = PromptExperiment(
            id="exp-123",
            name="A/B Test",
            description="Testing new prompt",
            prompt_id="prompt-456",
            status=ExperimentStatus.RUNNING,
            variants=[
                ExperimentVariant(
                    id="var-1",
                    name="Control",
                    prompt_version_id="v1",
                    traffic_percentage=50.0,
                ),
                ExperimentVariant(
                    id="var-2",
                    name="Treatment",
                    prompt_version_id="v2",
                    traffic_percentage=50.0,
                ),
            ],
            success_metric="conversion_rate",
        )

        assert experiment.id == "exp-123"
        assert experiment.name == "A/B Test"
        assert experiment.description == "Testing new prompt"
        assert experiment.prompt_id == "prompt-456"
        assert experiment.status == ExperimentStatus.RUNNING
        assert len(experiment.variants) == 2
        assert experiment.success_metric == "conversion_rate"

    def test_traffic_allocation_must_sum_to_100(self) -> None:
        """Should require variants traffic to sum to 100%."""
        with pytest.raises(ValidationError, match="must sum to 100"):
            PromptExperiment(
                id="exp-123",
                name="Invalid",
                prompt_id="prompt-456",
                status=ExperimentStatus.DRAFT,
                variants=[
                    ExperimentVariant(
                        id="var-1",
                        name="Control",
                        prompt_version_id="v1",
                        traffic_percentage=30.0,
                    ),
                    ExperimentVariant(
                        id="var-2",
                        name="Treatment",
                        prompt_version_id="v2",
                        traffic_percentage=30.0,
                    ),
                ],
                success_metric="clicks",
            )

    def test_traffic_allocation_floating_point_tolerance(self) -> None:
        """Should allow small floating point errors in traffic sum."""
        # This should not raise even though technically 99.99 != 100.0
        experiment = PromptExperiment(
            id="exp-123",
            name="Float Precision",
            prompt_id="prompt-456",
            status=ExperimentStatus.DRAFT,
            variants=[
                ExperimentVariant(
                    id="var-1",
                    name="A",
                    prompt_version_id="v1",
                    traffic_percentage=33.33,
                ),
                ExperimentVariant(
                    id="var-2",
                    name="B",
                    prompt_version_id="v2",
                    traffic_percentage=33.33,
                ),
                ExperimentVariant(
                    id="var-3",
                    name="C",
                    prompt_version_id="v3",
                    traffic_percentage=33.34,
                ),
            ],
            success_metric="engagement",
        )
        assert len(experiment.variants) == 3

    def test_minimum_two_variants_required(self) -> None:
        """Should require at least 2 variants."""
        with pytest.raises(ValidationError):
            PromptExperiment(
                id="exp-123",
                name="Single Variant",
                prompt_id="prompt-456",
                status=ExperimentStatus.DRAFT,
                variants=[
                    ExperimentVariant(
                        id="var-1",
                        name="Only One",
                        prompt_version_id="v1",
                        traffic_percentage=100.0,
                    ),
                ],
                success_metric="clicks",
            )

    def test_duplicate_variant_names_rejected(self) -> None:
        """Should reject duplicate variant names."""
        with pytest.raises(ValidationError, match="Duplicate variant names"):
            PromptExperiment(
                id="exp-123",
                name="Duplicate Names",
                prompt_id="prompt-456",
                status=ExperimentStatus.DRAFT,
                variants=[
                    ExperimentVariant(
                        id="var-1",
                        name="Control",
                        prompt_version_id="v1",
                        traffic_percentage=50.0,
                    ),
                    ExperimentVariant(
                        id="var-2",
                        name="Control",
                        prompt_version_id="v2",
                        traffic_percentage=50.0,
                    ),
                ],
                success_metric="clicks",
            )

    def test_unique_variant_names_accepted(self) -> None:
        """Should accept unique variant names."""
        experiment = PromptExperiment(
            id="exp-123",
            name="Unique Names",
            prompt_id="prompt-456",
            status=ExperimentStatus.DRAFT,
            variants=[
                ExperimentVariant(
                    id="var-1",
                    name="Control",
                    prompt_version_id="v1",
                    traffic_percentage=50.0,
                ),
                ExperimentVariant(
                    id="var-2",
                    name="Treatment",
                    prompt_version_id="v2",
                    traffic_percentage=50.0,
                ),
            ],
            success_metric="clicks",
        )
        assert len(experiment.variants) == 2


class TestComposedPrompt:
    """Tests for ComposedPrompt model."""

    def test_valid_composed_prompt(self) -> None:
        """Should create composed prompt with valid data."""
        composed = ComposedPrompt(
            content="Final composed content",
            layer_versions={
                "system": 1,
                "tenant": 2,
                "agent": 5,
            },
            cache_key="cache-key-123",
            composition_time_ms=15.5,
        )

        assert composed.content == "Final composed content"
        assert composed.layer_versions == {"system": 1, "tenant": 2, "agent": 5}
        assert composed.cache_key == "cache-key-123"
        assert composed.composition_time_ms == 15.5

    def test_defaults(self) -> None:
        """Should use default values when not provided."""
        composed = ComposedPrompt(
            content="Content",
            composition_time_ms=10.0,
        )

        assert composed.layer_versions == {}
        assert composed.cache_key is None
        assert isinstance(composed.composed_at, datetime)

    def test_empty_content_rejected(self) -> None:
        """Should reject empty content."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            ComposedPrompt(
                content="",
                composition_time_ms=10.0,
            )

    def test_whitespace_only_content_rejected(self) -> None:
        """Should reject whitespace-only content."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            ComposedPrompt(
                content="   \n\t  ",
                composition_time_ms=10.0,
            )

    def test_negative_composition_time_rejected(self) -> None:
        """Should reject negative composition time."""
        with pytest.raises(ValidationError):
            ComposedPrompt(
                content="Valid content",
                composition_time_ms=-5.0,
            )

    def test_zero_composition_time_accepted(self) -> None:
        """Should accept zero composition time."""
        composed = ComposedPrompt(
            content="Instant composition",
            composition_time_ms=0.0,
        )
        assert composed.composition_time_ms == 0.0
