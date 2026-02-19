"""Repository protocol for prompt storage operations.

This module defines the abstract interface that all prompt storage
implementations must follow.
"""

from typing import Optional, Protocol

from omniforge.prompts.enums import ExperimentStatus, PromptLayer
from omniforge.prompts.models import Prompt, PromptExperiment, PromptVersion


class PromptRepository(Protocol):
    """Protocol defining storage operations for prompts, versions, and experiments.

    All methods are async to support various storage backends (SQL, NoSQL, etc.).
    Implementations must ensure thread-safety for concurrent operations.
    """

    # Prompt CRUD Operations
    async def create(self, prompt: Prompt) -> Prompt:
        """Create a new prompt.

        Args:
            prompt: The prompt to create

        Returns:
            The created prompt

        Raises:
            PromptValidationError: If (layer, scope_id) combination already exists
        """
        ...

    async def get(self, prompt_id: str) -> Optional[Prompt]:
        """Retrieve a prompt by ID.

        Args:
            prompt_id: The prompt ID to retrieve

        Returns:
            The prompt if found, None otherwise
        """
        ...

    async def get_by_layer(
        self,
        layer: PromptLayer,
        scope_id: str,
        tenant_id: Optional[str] = None,
    ) -> Optional[Prompt]:
        """Retrieve a prompt by layer and scope.

        Args:
            layer: The prompt layer
            scope_id: The scope identifier
            tenant_id: Optional tenant ID for filtering

        Returns:
            The prompt if found, None otherwise
        """
        ...

    async def update(self, prompt: Prompt) -> Prompt:
        """Update an existing prompt.

        Args:
            prompt: The prompt with updated data

        Returns:
            The updated prompt

        Raises:
            PromptNotFoundError: If prompt does not exist
            PromptLockViolationError: If prompt is locked
        """
        ...

    async def delete(self, prompt_id: str) -> bool:
        """Soft delete a prompt by setting is_active=False.

        Args:
            prompt_id: The ID of the prompt to delete

        Returns:
            True if deleted, False if not found
        """
        ...

    async def list_by_tenant(
        self,
        tenant_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Prompt]:
        """List all active prompts for a tenant.

        Args:
            tenant_id: The tenant ID to filter by
            limit: Maximum number of results to return
            offset: Number of results to skip

        Returns:
            List of prompts, sorted by created_at descending
        """
        ...

    # Version Operations
    async def create_version(self, version: PromptVersion) -> PromptVersion:
        """Create a new prompt version.

        Args:
            version: The version to create

        Returns:
            The created version

        Raises:
            PromptNotFoundError: If parent prompt does not exist
        """
        ...

    async def get_version(
        self,
        prompt_id: str,
        version_number: int,
    ) -> Optional[PromptVersion]:
        """Retrieve a specific prompt version.

        Args:
            prompt_id: The parent prompt ID
            version_number: The version number to retrieve

        Returns:
            The version if found, None otherwise
        """
        ...

    async def list_versions(
        self,
        prompt_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PromptVersion]:
        """List all versions for a prompt.

        Args:
            prompt_id: The parent prompt ID
            limit: Maximum number of results to return
            offset: Number of results to skip

        Returns:
            List of versions, sorted by version_number descending
        """
        ...

    async def set_current_version(
        self,
        prompt_id: str,
        version_number: int,
    ) -> Prompt:
        """Set the current version of a prompt.

        Updates the prompt to reflect the content from the specified version.

        Args:
            prompt_id: The prompt ID
            version_number: The version number to set as current

        Returns:
            The updated prompt

        Raises:
            PromptNotFoundError: If prompt does not exist
            PromptVersionNotFoundError: If version does not exist
        """
        ...

    # Experiment Operations
    async def create_experiment(self, experiment: PromptExperiment) -> PromptExperiment:
        """Create a new A/B test experiment.

        Args:
            experiment: The experiment to create

        Returns:
            The created experiment

        Raises:
            PromptNotFoundError: If prompt does not exist
        """
        ...

    async def get_experiment(self, experiment_id: str) -> Optional[PromptExperiment]:
        """Retrieve an experiment by ID.

        Args:
            experiment_id: The experiment ID to retrieve

        Returns:
            The experiment if found, None otherwise
        """
        ...

    async def get_active_experiment(self, prompt_id: str) -> Optional[PromptExperiment]:
        """Retrieve the active experiment for a prompt.

        Args:
            prompt_id: The prompt ID

        Returns:
            The active experiment if found, None otherwise
        """
        ...

    async def update_experiment(self, experiment: PromptExperiment) -> PromptExperiment:
        """Update an existing experiment.

        Args:
            experiment: The experiment with updated data

        Returns:
            The updated experiment

        Raises:
            ExperimentNotFoundError: If experiment does not exist
        """
        ...

    async def list_experiments(
        self,
        prompt_id: str,
        status: Optional[ExperimentStatus] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PromptExperiment]:
        """List experiments for a prompt.

        Args:
            prompt_id: The prompt ID
            status: Optional status filter
            limit: Maximum number of results to return
            offset: Number of results to skip

        Returns:
            List of experiments, sorted by created_at descending
        """
        ...
