"""Statistical analysis for A/B test experiments.

This module provides statistical analysis capabilities for experiment results,
including significance testing and recommendations.
"""

import math
from dataclasses import dataclass
from typing import Optional, Union

from omniforge.prompts.models import PromptExperiment


@dataclass
class VariantStats:
    """Statistics for a single experiment variant.

    Attributes:
        variant_id: The variant identifier
        variant_name: Human-readable variant name
        sample_size: Number of observations
        mean: Average value of the success metric
        std_dev: Standard deviation of the metric
        conversion_rate: Optional conversion rate (for binary metrics)
    """

    variant_id: str
    variant_name: str
    sample_size: int
    mean: float
    std_dev: float
    conversion_rate: Optional[float] = None


@dataclass
class AnalysisResult:
    """Result of experiment statistical analysis.

    Attributes:
        variant_stats: Dictionary mapping variant IDs to their statistics
        winner: Optional variant ID of the winning variant
        is_significant: Whether results are statistically significant
        confidence_level: Confidence level of the results (0-1)
        p_value: Optional p-value from significance test
        sample_size_sufficient: Whether sample size is adequate
        recommendation: Human-readable recommendation
    """

    variant_stats: dict[str, VariantStats]
    winner: Optional[str]
    is_significant: bool
    confidence_level: float
    p_value: Optional[float] = None
    sample_size_sufficient: bool = True
    recommendation: str = ""


class ExperimentAnalyzer:
    """Analyzes A/B test experiment results for statistical significance.

    The analyzer computes basic statistics per variant and determines whether
    results are statistically significant using simple heuristics.
    """

    # Minimum sample size per variant for reliable results
    MIN_SAMPLE_SIZE = 100

    # Significance threshold (p-value)
    SIGNIFICANCE_THRESHOLD = 0.05

    def analyze(
        self,
        experiment: PromptExperiment,
        metrics: dict[str, dict[str, Union[int, float, list[float]]]],
    ) -> AnalysisResult:
        """Analyze experiment results and determine statistical significance.

        Args:
            experiment: The experiment to analyze
            metrics: Dictionary mapping variant IDs to their metric data.
                Each variant's data should contain:
                - 'sample_size': Number of observations
                - 'mean': Average value of success metric
                - 'std_dev': Standard deviation (optional, calculated if values provided)
                - 'values': List of individual values (optional, for computing stats)
                - 'conversion_rate': For binary metrics (optional)

        Returns:
            AnalysisResult with statistical analysis and recommendations

        Example:
            >>> analyzer = ExperimentAnalyzer()
            >>> metrics = {
            ...     "variant-1": {"sample_size": 150, "mean": 0.45, "std_dev": 0.1},
            ...     "variant-2": {"sample_size": 145, "mean": 0.52, "std_dev": 0.09}
            ... }
            >>> result = analyzer.analyze(experiment, metrics)
        """
        # Compute statistics for each variant
        variant_stats = self._compute_variant_stats(experiment, metrics)

        # Check if sample sizes are sufficient
        sample_size_sufficient = all(
            stats.sample_size >= self.MIN_SAMPLE_SIZE for stats in variant_stats.values()
        )

        # Find the best performing variant
        winner = self._find_winner(variant_stats)

        # Compute statistical significance
        is_significant, p_value = self._compute_significance(variant_stats)

        # Determine confidence level
        confidence_level = 1.0 - (p_value if p_value is not None else 1.0)

        # Generate recommendation
        recommendation = self._generate_recommendation(
            variant_stats, winner, is_significant, sample_size_sufficient
        )

        return AnalysisResult(
            variant_stats=variant_stats,
            winner=winner if is_significant else None,
            is_significant=is_significant,
            confidence_level=confidence_level,
            p_value=p_value,
            sample_size_sufficient=sample_size_sufficient,
            recommendation=recommendation,
        )

    def _compute_variant_stats(
        self,
        experiment: PromptExperiment,
        metrics: dict[str, dict[str, Union[int, float, list[float]]]],
    ) -> dict[str, VariantStats]:
        """Compute statistics for each variant.

        Args:
            experiment: The experiment being analyzed
            metrics: Raw metrics data per variant

        Returns:
            Dictionary mapping variant IDs to their computed statistics
        """
        variant_stats = {}

        for variant in experiment.variants:
            variant_id = variant.id
            variant_metrics = metrics.get(variant_id, {})

            # Extract or compute statistics
            sample_size_val = variant_metrics.get("sample_size", 0)
            sample_size = int(sample_size_val) if isinstance(sample_size_val, (int, float)) else 0

            mean_val = variant_metrics.get("mean", 0.0)
            mean = float(mean_val) if isinstance(mean_val, (int, float)) else 0.0

            # Compute std_dev from values if not provided
            if "std_dev" in variant_metrics:
                std_dev_val = variant_metrics["std_dev"]
                std_dev = float(std_dev_val) if isinstance(std_dev_val, (int, float)) else 0.0
            elif "values" in variant_metrics:
                values = variant_metrics["values"]
                if isinstance(values, list) and values:
                    std_dev = self._compute_std_dev(values, mean)
                else:
                    std_dev = 0.0
            else:
                std_dev = 0.0

            conversion_rate_val = variant_metrics.get("conversion_rate")
            conversion_rate: Optional[float] = None
            if conversion_rate_val is not None and isinstance(conversion_rate_val, (int, float)):
                conversion_rate = float(conversion_rate_val)

            variant_stats[variant_id] = VariantStats(
                variant_id=variant_id,
                variant_name=variant.name,
                sample_size=sample_size,
                mean=mean,
                std_dev=std_dev,
                conversion_rate=conversion_rate,
            )

        return variant_stats

    def _compute_std_dev(self, values: list[float], mean: float) -> float:
        """Compute standard deviation from a list of values.

        Args:
            values: List of metric values
            mean: Pre-computed mean

        Returns:
            Standard deviation
        """
        if not values or len(values) < 2:
            return 0.0

        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return math.sqrt(variance)

    def _find_winner(self, variant_stats: dict[str, VariantStats]) -> Optional[str]:
        """Find the variant with the highest mean.

        Args:
            variant_stats: Statistics for all variants

        Returns:
            Variant ID of the winner, or None if no variants
        """
        if not variant_stats:
            return None

        return max(variant_stats.items(), key=lambda x: x[1].mean)[0]

    def _compute_significance(
        self, variant_stats: dict[str, VariantStats]
    ) -> tuple[bool, Optional[float]]:
        """Compute whether results are statistically significant.

        Uses a simplified two-sample t-test for comparing means.

        Args:
            variant_stats: Statistics for all variants

        Returns:
            Tuple of (is_significant, p_value)
        """
        if len(variant_stats) < 2:
            return False, None

        # For simplicity, compare the top 2 variants
        sorted_variants = sorted(variant_stats.values(), key=lambda x: x.mean, reverse=True)
        variant_a = sorted_variants[0]
        variant_b = sorted_variants[1]

        # Check minimum sample sizes
        if (
            variant_a.sample_size < self.MIN_SAMPLE_SIZE
            or variant_b.sample_size < self.MIN_SAMPLE_SIZE
        ):
            return False, None

        # Compute t-statistic for two-sample t-test
        try:
            p_value = self._two_sample_t_test(variant_a, variant_b)
            is_significant = p_value < self.SIGNIFICANCE_THRESHOLD
            return is_significant, p_value
        except (ValueError, ZeroDivisionError):
            return False, None

    def _two_sample_t_test(self, variant_a: VariantStats, variant_b: VariantStats) -> float:
        """Perform a two-sample t-test.

        This is a simplified implementation using Welch's t-test approximation.

        Args:
            variant_a: Statistics for first variant
            variant_b: Statistics for second variant

        Returns:
            Approximate p-value

        Raises:
            ValueError: If standard errors are zero
        """
        # Calculate standard errors
        se_a = variant_a.std_dev / math.sqrt(variant_a.sample_size)
        se_b = variant_b.std_dev / math.sqrt(variant_b.sample_size)

        # Calculate pooled standard error
        pooled_se = math.sqrt(se_a**2 + se_b**2)

        if pooled_se == 0:
            raise ValueError("Pooled standard error is zero")

        # Calculate t-statistic
        t_stat = abs(variant_a.mean - variant_b.mean) / pooled_se

        # Degrees of freedom (Welch-Satterthwaite approximation)
        df = (se_a**2 + se_b**2) ** 2 / (
            se_a**4 / (variant_a.sample_size - 1) + se_b**4 / (variant_b.sample_size - 1)
        )

        # Approximate p-value using normal distribution for large samples
        # For df > 30, t-distribution approximates normal distribution
        if df > 30:
            p_value = 2 * (1 - self._normal_cdf(t_stat))
        else:
            # Conservative estimate for small samples
            p_value = 2 * (1 - self._normal_cdf(t_stat * 0.9))

        return max(0.0, min(1.0, p_value))

    def _normal_cdf(self, x: float) -> float:
        """Approximate cumulative distribution function for standard normal.

        Uses error function approximation.

        Args:
            x: Value to compute CDF for

        Returns:
            Approximate CDF value
        """
        return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

    def _generate_recommendation(
        self,
        variant_stats: dict[str, VariantStats],
        winner: Optional[str],
        is_significant: bool,
        sample_size_sufficient: bool,
    ) -> str:
        """Generate a human-readable recommendation.

        Args:
            variant_stats: Statistics for all variants
            winner: ID of winning variant
            is_significant: Whether results are statistically significant
            sample_size_sufficient: Whether sample sizes are adequate

        Returns:
            Recommendation text
        """
        if not sample_size_sufficient:
            return (
                f"Continue experiment to reach minimum sample size of "
                f"{self.MIN_SAMPLE_SIZE} per variant for reliable results."
            )

        if not winner:
            return "No clear winner identified. Continue experiment or analyze metrics."

        winner_stats = variant_stats[winner]

        if is_significant:
            return (
                f"Statistically significant results detected. "
                f"Variant '{winner_stats.variant_name}' (mean: {winner_stats.mean:.4f}) "
                f"is the clear winner. Consider promoting this variant."
            )
        else:
            return (
                f"Variant '{winner_stats.variant_name}' shows best performance "
                f"(mean: {winner_stats.mean:.4f}), but results are not statistically "
                f"significant. Continue experiment to gather more data."
            )
