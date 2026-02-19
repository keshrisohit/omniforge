"""Traffic allocation for A/B test experiments.

This module provides deterministic variant selection based on user identifiers,
ensuring consistent assignment of users to experiment variants.
"""

import hashlib
from typing import Optional

from omniforge.prompts.models import PromptExperiment


class TrafficAllocator:
    """Allocates traffic across experiment variants using consistent hashing.

    The allocator uses SHA-256 hashing to deterministically assign users to variants
    based on their identifier and the experiment ID. This ensures that the same user
    always sees the same variant for a given experiment.
    """

    def allocate(self, experiment: PromptExperiment, identifier: str) -> str:
        """Allocate a user to a variant based on consistent hashing.

        The allocation works as follows:
        1. Create a hash from experiment_id + identifier
        2. Convert hash to a percentage (0-100)
        3. Map the percentage to a variant based on traffic allocation

        Args:
            experiment: The experiment to allocate for
            identifier: User or tenant identifier for consistent assignment

        Returns:
            The variant ID the user should see

        Example:
            >>> allocator = TrafficAllocator()
            >>> variant_id = allocator.allocate(experiment, "user-123")
        """
        # Create deterministic hash from experiment ID and identifier
        hash_input = f"{experiment.id}:{identifier}".encode("utf-8")
        hash_digest = hashlib.sha256(hash_input).hexdigest()

        # Convert first 8 hex characters to integer and normalize to 0-100 range
        hash_int = int(hash_digest[:8], 16)
        percentage = (hash_int % 10000) / 100.0  # 0.00 to 99.99

        # Map percentage to variant based on traffic allocation
        cumulative = 0.0
        for variant in experiment.variants:
            cumulative += variant.traffic_percentage
            if percentage < cumulative:
                return variant.id

        # Fallback to last variant (should not happen if percentages sum to 100)
        return experiment.variants[-1].id

    def get_variant_for_identifier(
        self, experiment: PromptExperiment, identifier: str
    ) -> Optional[str]:
        """Get the variant ID for a given identifier.

        This is an alias for allocate() with clearer naming.

        Args:
            experiment: The experiment to check
            identifier: User or tenant identifier

        Returns:
            The variant ID or None if experiment has no variants
        """
        if not experiment.variants:
            return None
        return self.allocate(experiment, identifier)
