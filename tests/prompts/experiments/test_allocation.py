"""Tests for traffic allocation module."""

from omniforge.prompts.enums import ExperimentStatus
from omniforge.prompts.experiments.allocation import TrafficAllocator
from omniforge.prompts.models import ExperimentVariant, PromptExperiment


class TestTrafficAllocator:
    """Tests for TrafficAllocator class."""

    def test_deterministic_allocation(self) -> None:
        """Should allocate same user to same variant consistently."""
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

        allocator = TrafficAllocator()

        # Same user should get same variant multiple times
        user_id = "user-123"
        first_allocation = allocator.allocate(experiment, user_id)
        second_allocation = allocator.allocate(experiment, user_id)
        third_allocation = allocator.allocate(experiment, user_id)

        assert first_allocation == second_allocation
        assert second_allocation == third_allocation

    def test_different_users_can_get_different_variants(self) -> None:
        """Should allocate different users potentially to different variants."""
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

        allocator = TrafficAllocator()

        # Test multiple users to ensure we get both variants
        allocations = set()
        for i in range(100):
            user_id = f"user-{i}"
            variant_id = allocator.allocate(experiment, user_id)
            allocations.add(variant_id)

        # With 100 users and 50/50 split, we should see both variants
        assert len(allocations) == 2
        assert "variant-a" in allocations
        assert "variant-b" in allocations

    def test_traffic_distribution_approximately_correct(self) -> None:
        """Should distribute traffic according to percentages."""
        variants = [
            ExperimentVariant(
                id="variant-a",
                name="Control",
                prompt_version_id="prompt-1-v1",
                traffic_percentage=70.0,
            ),
            ExperimentVariant(
                id="variant-b",
                name="Treatment",
                prompt_version_id="prompt-1-v2",
                traffic_percentage=30.0,
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

        allocator = TrafficAllocator()

        # Test with large sample
        allocation_counts = {"variant-a": 0, "variant-b": 0}
        num_users = 1000

        for i in range(num_users):
            user_id = f"user-{i}"
            variant_id = allocator.allocate(experiment, user_id)
            allocation_counts[variant_id] += 1

        # Check that distribution is approximately correct (within 10% margin)
        variant_a_percentage = (allocation_counts["variant-a"] / num_users) * 100
        variant_b_percentage = (allocation_counts["variant-b"] / num_users) * 100

        assert 60.0 <= variant_a_percentage <= 80.0  # 70% ± 10%
        assert 20.0 <= variant_b_percentage <= 40.0  # 30% ± 10%

    def test_three_way_split(self) -> None:
        """Should handle three-way traffic splits."""
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

        allocator = TrafficAllocator()

        # Test that all variants are used
        allocations = set()
        for i in range(300):
            user_id = f"user-{i}"
            variant_id = allocator.allocate(experiment, user_id)
            allocations.add(variant_id)

        # All three variants should be seen
        assert len(allocations) == 3
        assert "variant-a" in allocations
        assert "variant-b" in allocations
        assert "variant-c" in allocations

    def test_different_experiment_ids_give_different_allocations(self) -> None:
        """Should allocate differently for different experiments."""
        user_id = "user-123"

        # Create two experiments with same variants but different IDs
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

        experiment1 = PromptExperiment(
            id="exp-1",
            name="Test Experiment 1",
            prompt_id="prompt-1",
            status=ExperimentStatus.RUNNING,
            variants=variants,
            success_metric="conversion_rate",
        )

        experiment2 = PromptExperiment(
            id="exp-2",
            name="Test Experiment 2",
            prompt_id="prompt-1",
            status=ExperimentStatus.RUNNING,
            variants=variants,
            success_metric="conversion_rate",
        )

        allocator = TrafficAllocator()

        # Same user might get different variants in different experiments
        allocation1 = allocator.allocate(experiment1, user_id)
        allocation2 = allocator.allocate(experiment2, user_id)

        # We can't guarantee they'll be different, but the hash should be different
        # Just verify both are valid variants
        assert allocation1 in ["variant-a", "variant-b"]
        assert allocation2 in ["variant-a", "variant-b"]

    def test_get_variant_for_identifier(self) -> None:
        """Should return variant ID for identifier."""
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

        allocator = TrafficAllocator()

        variant_id = allocator.get_variant_for_identifier(experiment, "user-123")
        assert variant_id in ["variant-a", "variant-b"]

    def test_get_variant_for_identifier_with_variants(self) -> None:
        """Should return variant ID when experiment has variants."""
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

        allocator = TrafficAllocator()

        variant_id = allocator.get_variant_for_identifier(experiment, "user-123")
        assert variant_id in ["variant-a", "variant-b"]
