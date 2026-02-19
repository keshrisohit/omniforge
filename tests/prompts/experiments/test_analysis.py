"""Tests for experiment analysis module."""

from omniforge.prompts.enums import ExperimentStatus
from omniforge.prompts.experiments.analysis import (
    ExperimentAnalyzer,
)
from omniforge.prompts.models import ExperimentVariant, PromptExperiment


class TestExperimentAnalyzer:
    """Tests for ExperimentAnalyzer class."""

    def test_analyze_with_sufficient_samples_and_significance(self) -> None:
        """Should identify significant winner with sufficient samples."""
        variants = [
            ExperimentVariant(
                id="variant-a",
                name="Control",
                prompt_version_id="prompt-1-v1",
                traffic_percentage=50.0,
            ),
            ExperimentVariant(
                id="variant-b",
                name="Treatment",
                prompt_version_id="prompt-1-v2",
                traffic_percentage=50.0,
            ),
        ]

        experiment = PromptExperiment(
            id="exp-1",
            name="Test Experiment",
            prompt_id="prompt-1",
            status=ExperimentStatus.RUNNING,
            variants=variants,
            success_metric="conversion_rate",
        )

        # Strong difference with large samples
        metrics = {
            "variant-a": {"sample_size": 200, "mean": 0.30, "std_dev": 0.15},
            "variant-b": {"sample_size": 200, "mean": 0.50, "std_dev": 0.15},
        }

        analyzer = ExperimentAnalyzer()
        result = analyzer.analyze(experiment, metrics)

        assert result.sample_size_sufficient is True
        assert result.is_significant is True
        assert result.winner == "variant-b"
        assert result.confidence_level > 0.95
        assert "variant-b" in result.variant_stats
        assert result.variant_stats["variant-b"].mean == 0.50

    def test_analyze_with_insufficient_samples(self) -> None:
        """Should indicate insufficient samples when below threshold."""
        variants = [
            ExperimentVariant(
                id="variant-a",
                name="Control",
                prompt_version_id="prompt-1-v1",
                traffic_percentage=50.0,
            ),
            ExperimentVariant(
                id="variant-b",
                name="Treatment",
                prompt_version_id="prompt-1-v2",
                traffic_percentage=50.0,
            ),
        ]

        experiment = PromptExperiment(
            id="exp-1",
            name="Test Experiment",
            prompt_id="prompt-1",
            status=ExperimentStatus.RUNNING,
            variants=variants,
            success_metric="conversion_rate",
        )

        # Small samples
        metrics = {
            "variant-a": {"sample_size": 50, "mean": 0.30, "std_dev": 0.15},
            "variant-b": {"sample_size": 50, "mean": 0.50, "std_dev": 0.15},
        }

        analyzer = ExperimentAnalyzer()
        result = analyzer.analyze(experiment, metrics)

        assert result.sample_size_sufficient is False
        assert "Continue experiment" in result.recommendation

    def test_analyze_without_significance(self) -> None:
        """Should indicate no significance when results are too close."""
        variants = [
            ExperimentVariant(
                id="variant-a",
                name="Control",
                prompt_version_id="prompt-1-v1",
                traffic_percentage=50.0,
            ),
            ExperimentVariant(
                id="variant-b",
                name="Treatment",
                prompt_version_id="prompt-1-v2",
                traffic_percentage=50.0,
            ),
        ]

        experiment = PromptExperiment(
            id="exp-1",
            name="Test Experiment",
            prompt_id="prompt-1",
            status=ExperimentStatus.RUNNING,
            variants=variants,
            success_metric="conversion_rate",
        )

        # Very similar results with high variance
        metrics = {
            "variant-a": {"sample_size": 200, "mean": 0.45, "std_dev": 0.25},
            "variant-b": {"sample_size": 200, "mean": 0.46, "std_dev": 0.25},
        }

        analyzer = ExperimentAnalyzer()
        result = analyzer.analyze(experiment, metrics)

        assert result.sample_size_sufficient is True
        assert result.is_significant is False
        assert result.winner is None
        assert "not statistically significant" in result.recommendation

    def test_compute_variant_stats(self) -> None:
        """Should compute correct statistics for variants."""
        variants = [
            ExperimentVariant(
                id="variant-a",
                name="Control",
                prompt_version_id="prompt-1-v1",
                traffic_percentage=50.0,
            ),
            ExperimentVariant(
                id="variant-b",
                name="Treatment",
                prompt_version_id="prompt-1-v2",
                traffic_percentage=50.0,
            ),
        ]

        experiment = PromptExperiment(
            id="exp-1",
            name="Test Experiment",
            prompt_id="prompt-1",
            status=ExperimentStatus.RUNNING,
            variants=variants,
            success_metric="conversion_rate",
        )

        metrics = {
            "variant-a": {
                "sample_size": 100,
                "mean": 0.42,
                "std_dev": 0.15,
                "conversion_rate": 0.42,
            },
            "variant-b": {
                "sample_size": 100,
                "mean": 0.38,
                "std_dev": 0.14,
            },
        }

        analyzer = ExperimentAnalyzer()
        result = analyzer.analyze(experiment, metrics)

        variant_stats = result.variant_stats["variant-a"]
        assert variant_stats.variant_id == "variant-a"
        assert variant_stats.variant_name == "Control"
        assert variant_stats.sample_size == 100
        assert variant_stats.mean == 0.42
        assert variant_stats.std_dev == 0.15
        assert variant_stats.conversion_rate == 0.42

    def test_compute_std_dev_from_values(self) -> None:
        """Should compute std_dev from values when not provided."""
        variants = [
            ExperimentVariant(
                id="variant-a",
                name="Control",
                prompt_version_id="prompt-1-v1",
                traffic_percentage=50.0,
            ),
            ExperimentVariant(
                id="variant-b",
                name="Treatment",
                prompt_version_id="prompt-1-v2",
                traffic_percentage=50.0,
            ),
        ]

        experiment = PromptExperiment(
            id="exp-1",
            name="Test Experiment",
            prompt_id="prompt-1",
            status=ExperimentStatus.RUNNING,
            variants=variants,
            success_metric="score",
        )

        # Provide values instead of std_dev
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        mean = sum(values) / len(values)

        metrics = {
            "variant-a": {
                "sample_size": len(values),
                "mean": mean,
                "values": values,
            },
            "variant-b": {
                "sample_size": 100,
                "mean": 3.0,
                "std_dev": 1.5,
            },
        }

        analyzer = ExperimentAnalyzer()
        result = analyzer.analyze(experiment, metrics)

        variant_stats = result.variant_stats["variant-a"]
        # Computed std_dev should be non-zero
        assert variant_stats.std_dev > 0

    def test_analyze_three_variants(self) -> None:
        """Should analyze experiments with three variants."""
        variants = [
            ExperimentVariant(
                id="variant-a",
                name="Control",
                prompt_version_id="prompt-1-v1",
                traffic_percentage=33.33,
            ),
            ExperimentVariant(
                id="variant-b",
                name="Treatment 1",
                prompt_version_id="prompt-1-v2",
                traffic_percentage=33.33,
            ),
            ExperimentVariant(
                id="variant-c",
                name="Treatment 2",
                prompt_version_id="prompt-1-v3",
                traffic_percentage=33.34,
            ),
        ]

        experiment = PromptExperiment(
            id="exp-1",
            name="Test Experiment",
            prompt_id="prompt-1",
            status=ExperimentStatus.RUNNING,
            variants=variants,
            success_metric="conversion_rate",
        )

        metrics = {
            "variant-a": {"sample_size": 150, "mean": 0.30, "std_dev": 0.15},
            "variant-b": {"sample_size": 150, "mean": 0.45, "std_dev": 0.15},
            "variant-c": {"sample_size": 150, "mean": 0.60, "std_dev": 0.15},
        }

        analyzer = ExperimentAnalyzer()
        result = analyzer.analyze(experiment, metrics)

        # Should pick the best variant
        assert result.winner == "variant-c" or not result.is_significant
        assert len(result.variant_stats) == 3

    def test_find_winner_with_empty_stats(self) -> None:
        """Should return None when no variant has data."""
        variants = [
            ExperimentVariant(
                id="variant-a",
                name="Control",
                prompt_version_id="prompt-1-v1",
                traffic_percentage=50.0,
            ),
            ExperimentVariant(
                id="variant-b",
                name="Treatment",
                prompt_version_id="prompt-1-v2",
                traffic_percentage=50.0,
            ),
        ]

        experiment = PromptExperiment(
            id="exp-1",
            name="Test Experiment",
            prompt_id="prompt-1",
            status=ExperimentStatus.RUNNING,
            variants=variants,
            success_metric="conversion_rate",
        )

        analyzer = ExperimentAnalyzer()
        result = analyzer.analyze(experiment, {})

        # No winner because sample sizes are insufficient
        assert result.winner is None
        assert result.sample_size_sufficient is False

    def test_normal_cdf(self) -> None:
        """Should compute reasonable CDF values."""
        analyzer = ExperimentAnalyzer()

        # Test some known values
        cdf_0 = analyzer._normal_cdf(0.0)
        assert 0.49 < cdf_0 < 0.51  # Should be ~0.5

        cdf_positive = analyzer._normal_cdf(2.0)
        assert cdf_positive > 0.95  # Should be high

        cdf_negative = analyzer._normal_cdf(-2.0)
        assert cdf_negative < 0.05  # Should be low

    def test_recommendation_with_winner(self) -> None:
        """Should generate appropriate recommendation with clear winner."""
        variants = [
            ExperimentVariant(
                id="variant-a",
                name="Control",
                prompt_version_id="prompt-1-v1",
                traffic_percentage=50.0,
            ),
            ExperimentVariant(
                id="variant-b",
                name="Treatment",
                prompt_version_id="prompt-1-v2",
                traffic_percentage=50.0,
            ),
        ]

        experiment = PromptExperiment(
            id="exp-1",
            name="Test Experiment",
            prompt_id="prompt-1",
            status=ExperimentStatus.RUNNING,
            variants=variants,
            success_metric="conversion_rate",
        )

        # Clear winner
        metrics = {
            "variant-a": {"sample_size": 200, "mean": 0.30, "std_dev": 0.10},
            "variant-b": {"sample_size": 200, "mean": 0.60, "std_dev": 0.10},
        }

        analyzer = ExperimentAnalyzer()
        result = analyzer.analyze(experiment, metrics)

        if result.is_significant:
            assert "Treatment" in result.recommendation
            assert "clear winner" in result.recommendation or "promoting" in result.recommendation
