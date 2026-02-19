"""Experiment manager for A/B testing prompt variations.

This module provides the main interface for creating, managing, and running
A/B test experiments on prompts.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from omniforge.prompts.enums import ExperimentStatus
from omniforge.prompts.errors import (
    ExperimentNotFoundError,
    ExperimentStateError,
    PromptNotFoundError,
    PromptValidationError,
)
from omniforge.prompts.experiments.allocation import TrafficAllocator
from omniforge.prompts.models import (
    ExperimentVariant,
    Prompt,
    PromptExperiment,
)
from omniforge.prompts.storage.repository import PromptRepository


@dataclass
class VariantSelection:
    """Result of variant selection for an experiment.

    Attributes:
        experiment_id: The experiment ID
        variant_id: The selected variant ID
        variant_name: Human-readable variant name
        prompt_version_id: The prompt version to use
    """

    experiment_id: str
    variant_id: str
    variant_name: str
    prompt_version_id: str


class ExperimentManager:
    """Manages A/B test experiments for prompt optimization.

    The manager handles the complete lifecycle of experiments from creation
    through analysis and promotion of winning variants.
    """

    def __init__(self, repository: PromptRepository) -> None:
        """Initialize the experiment manager.

        Args:
            repository: The prompt repository for data persistence
        """
        self.repository = repository
        self.allocator = TrafficAllocator()

    async def create_experiment(
        self,
        prompt_id: str,
        name: str,
        description: str,
        success_metric: str,
        variants: list[ExperimentVariant],
        created_by: Optional[str] = None,
    ) -> PromptExperiment:
        """Create a new A/B test experiment.

        Args:
            prompt_id: ID of the prompt to experiment on
            name: Human-readable experiment name
            description: Detailed description of the experiment
            success_metric: Name of the metric to optimize
            variants: List of experiment variants (must be at least 2)
            created_by: Optional ID of user creating the experiment

        Returns:
            The created experiment

        Raises:
            PromptNotFoundError: If prompt does not exist
            PromptValidationError: If variants don't sum to 100% or other validation fails
        """
        # Validate prompt exists
        prompt = await self.repository.get(prompt_id)
        if not prompt:
            raise PromptNotFoundError(prompt_id)

        # Validate variant count
        if len(variants) < 2:
            raise PromptValidationError(
                "Experiment must have at least 2 variants",
                field="variants",
            )

        # Validate traffic allocation sums to 100%
        total_traffic = sum(v.traffic_percentage for v in variants)
        if abs(total_traffic - 100.0) > 0.01:
            raise PromptValidationError(
                f"Variant traffic percentages must sum to 100%, got {total_traffic}",
                field="variants",
            )

        # Generate experiment ID
        experiment_id = f"exp-{prompt_id}-{datetime.utcnow().timestamp()}"

        # Create experiment in DRAFT status
        experiment = PromptExperiment(
            id=experiment_id,
            name=name,
            description=description,
            prompt_id=prompt_id,
            status=ExperimentStatus.DRAFT,
            variants=variants,
            success_metric=success_metric,
            created_by=created_by,
        )

        return await self.repository.create_experiment(experiment)

    async def get_experiment(self, experiment_id: str) -> PromptExperiment:
        """Get an experiment by ID.

        Args:
            experiment_id: ID of the experiment to retrieve

        Returns:
            The experiment

        Raises:
            ExperimentNotFoundError: If experiment does not exist
        """
        experiment = await self.repository.get_experiment(experiment_id)
        if not experiment:
            raise ExperimentNotFoundError(experiment_id)
        return experiment

    async def list_experiments(self, prompt_id: str) -> list[PromptExperiment]:
        """List all experiments for a prompt.

        Args:
            prompt_id: ID of the prompt

        Returns:
            List of experiments for the prompt

        Raises:
            PromptNotFoundError: If prompt does not exist
        """
        # Verify prompt exists
        prompt = await self.repository.get(prompt_id)
        if not prompt:
            raise PromptNotFoundError(prompt_id)

        return await self.repository.list_experiments(prompt_id)

    async def start_experiment(self, experiment_id: str) -> PromptExperiment:
        """Start a DRAFT or PAUSED experiment.

        Args:
            experiment_id: ID of the experiment to start

        Returns:
            The updated experiment with RUNNING status

        Raises:
            ExperimentNotFoundError: If experiment does not exist
            ExperimentStateError: If experiment is not in DRAFT or PAUSED state
            ExperimentStateError: If another experiment is already running for this prompt
        """
        experiment = await self.repository.get_experiment(experiment_id)
        if not experiment:
            raise ExperimentNotFoundError(experiment_id)

        # Verify experiment is in valid state for starting
        if experiment.status not in [ExperimentStatus.DRAFT, ExperimentStatus.PAUSED]:
            raise ExperimentStateError(
                experiment_id=experiment_id,
                current_state=experiment.status.value,
                operation="start",
            )

        # Check no other RUNNING experiment exists for this prompt
        active_experiment = await self.repository.get_active_experiment(experiment.prompt_id)
        if active_experiment and active_experiment.id != experiment_id:
            raise ExperimentStateError(
                experiment_id=experiment_id,
                current_state=experiment.status.value,
                operation="start",
            )

        # Update experiment status and start time
        experiment.status = ExperimentStatus.RUNNING
        if experiment.start_time is None:
            experiment.start_time = datetime.utcnow()
        experiment.updated_at = datetime.utcnow()

        return await self.repository.update_experiment(experiment)

    async def pause_experiment(self, experiment_id: str) -> PromptExperiment:
        """Pause a RUNNING experiment.

        Args:
            experiment_id: ID of the experiment to pause

        Returns:
            The updated experiment with PAUSED status

        Raises:
            ExperimentNotFoundError: If experiment does not exist
            ExperimentStateError: If experiment is not RUNNING
        """
        experiment = await self.repository.get_experiment(experiment_id)
        if not experiment:
            raise ExperimentNotFoundError(experiment_id)

        # Verify experiment is running
        if experiment.status != ExperimentStatus.RUNNING:
            raise ExperimentStateError(
                experiment_id=experiment_id,
                current_state=experiment.status.value,
                operation="pause",
            )

        # Update experiment status
        experiment.status = ExperimentStatus.PAUSED
        experiment.updated_at = datetime.utcnow()

        return await self.repository.update_experiment(experiment)

    async def complete_experiment(
        self, experiment_id: str, results: dict[str, Any]
    ) -> PromptExperiment:
        """Complete an experiment and store results.

        Args:
            experiment_id: ID of the experiment to complete
            results: Statistical results to store

        Returns:
            The updated experiment with COMPLETED status

        Raises:
            ExperimentNotFoundError: If experiment does not exist
        """
        experiment = await self.repository.get_experiment(experiment_id)
        if not experiment:
            raise ExperimentNotFoundError(experiment_id)

        # Update experiment status and store results
        experiment.status = ExperimentStatus.COMPLETED
        experiment.end_time = datetime.utcnow()
        experiment.updated_at = datetime.utcnow()

        # Store results in variant metrics
        for variant in experiment.variants:
            if variant.id in results:
                if variant.metrics is None:
                    variant.metrics = {}
                variant.metrics.update({"final_result": results[variant.id]})

        return await self.repository.update_experiment(experiment)

    async def cancel_experiment(self, experiment_id: str) -> PromptExperiment:
        """Cancel an experiment.

        Args:
            experiment_id: ID of the experiment to cancel

        Returns:
            The updated experiment with CANCELLED status

        Raises:
            ExperimentNotFoundError: If experiment does not exist
        """
        experiment = await self.repository.get_experiment(experiment_id)
        if not experiment:
            raise ExperimentNotFoundError(experiment_id)

        # Update experiment status
        experiment.status = ExperimentStatus.CANCELLED
        experiment.end_time = datetime.utcnow()
        experiment.updated_at = datetime.utcnow()

        return await self.repository.update_experiment(experiment)

    async def select_variant(self, prompt_id: str, tenant_id: str) -> Optional[VariantSelection]:
        """Select a variant for a user based on active experiments.

        Uses consistent hashing to ensure the same tenant always gets the same variant
        for a given experiment.

        Args:
            prompt_id: The prompt ID to check for experiments
            tenant_id: Tenant identifier for consistent assignment

        Returns:
            VariantSelection if an active experiment exists, None otherwise
        """
        # Check for active experiment on this prompt
        experiment = await self.repository.get_active_experiment(prompt_id)
        if not experiment:
            return None

        # Allocate tenant to a variant
        variant_id = self.allocator.allocate(experiment, tenant_id)

        # Find the variant details
        variant = next((v for v in experiment.variants if v.id == variant_id), None)
        if not variant:
            return None

        return VariantSelection(
            experiment_id=experiment.id,
            variant_id=variant.id,
            variant_name=variant.name,
            prompt_version_id=variant.prompt_version_id,
        )

    async def promote_variant(
        self, experiment_id: str, variant_id: str, promoted_by: str
    ) -> Prompt:
        """Promote a variant's prompt version as the current version.

        This completes the experiment and sets the winning variant's version
        as the current version of the prompt.

        Args:
            experiment_id: ID of the experiment
            variant_id: ID of the variant to promote
            promoted_by: ID of user performing the promotion

        Returns:
            The updated prompt with the new current version

        Raises:
            ExperimentNotFoundError: If experiment does not exist
            PromptValidationError: If variant does not exist in experiment
        """
        experiment = await self.repository.get_experiment(experiment_id)
        if not experiment:
            raise ExperimentNotFoundError(experiment_id)

        # Find the variant
        variant = next((v for v in experiment.variants if v.id == variant_id), None)
        if not variant:
            raise PromptValidationError(
                f"Variant '{variant_id}' not found in experiment",
                field="variant_id",
            )

        # Extract version number from prompt_version_id
        # Assuming format: "prompt_id-v{version_number}"
        version_str = variant.prompt_version_id.split("-v")[-1]
        try:
            version_number = int(version_str)
        except ValueError:
            raise PromptValidationError(
                f"Invalid prompt_version_id format: {variant.prompt_version_id}",
                field="prompt_version_id",
            )

        # Set the variant's version as current
        prompt = await self.repository.set_current_version(experiment.prompt_id, version_number)

        # Complete the experiment
        await self.complete_experiment(
            experiment_id,
            {"promoted_variant": variant_id, "promoted_by": promoted_by},
        )

        return prompt
