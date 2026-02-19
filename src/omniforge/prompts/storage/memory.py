"""In-memory implementation of prompt repository.

This module provides a thread-safe, in-memory storage implementation
suitable for development, testing, and lightweight deployments.
"""

import asyncio
from datetime import datetime
from typing import Optional

from omniforge.prompts.enums import ExperimentStatus, PromptLayer
from omniforge.prompts.errors import (
    ExperimentNotFoundError,
    PromptLockViolationError,
    PromptNotFoundError,
    PromptValidationError,
    PromptVersionNotFoundError,
)
from omniforge.prompts.models import Prompt, PromptExperiment, PromptVersion


class InMemoryPromptRepository:
    """Thread-safe in-memory storage for prompts, versions, and experiments.

    Uses asyncio.Lock to ensure thread safety for concurrent operations.
    Stores all data in dictionaries with UUID keys.
    """

    def __init__(self) -> None:
        """Initialize the in-memory repository with empty storage."""
        self._prompts: dict[str, Prompt] = {}
        self._versions: dict[str, PromptVersion] = {}
        self._experiments: dict[str, PromptExperiment] = {}
        self._lock = asyncio.Lock()

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
        async with self._lock:
            # Check for duplicate (layer, scope_id) combination
            for existing_prompt in self._prompts.values():
                if (
                    existing_prompt.layer == prompt.layer
                    and existing_prompt.scope_id == prompt.scope_id
                    and existing_prompt.is_active
                ):
                    raise PromptValidationError(
                        message=(
                            f"Prompt with layer '{prompt.layer}' and "
                            f"scope_id '{prompt.scope_id}' already exists"
                        ),
                        field="layer, scope_id",
                    )

            # Store the prompt
            self._prompts[prompt.id] = prompt
            return prompt

    async def get(self, prompt_id: str) -> Optional[Prompt]:
        """Retrieve a prompt by ID.

        Args:
            prompt_id: The prompt ID to retrieve

        Returns:
            The prompt if found and active, None otherwise
        """
        async with self._lock:
            prompt = self._prompts.get(prompt_id)
            if prompt and prompt.is_active:
                return prompt
            return None

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
            The prompt if found and active, None otherwise
        """
        async with self._lock:
            for prompt in self._prompts.values():
                if prompt.layer == layer and prompt.scope_id == scope_id and prompt.is_active:
                    if tenant_id is None or prompt.tenant_id == tenant_id:
                        return prompt
            return None

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
        async with self._lock:
            existing = self._prompts.get(prompt.id)
            if not existing:
                raise PromptNotFoundError(prompt.id)

            if existing.is_locked:
                raise PromptLockViolationError(
                    resource_type="prompt",
                    resource_id=prompt.id,
                )

            # Update timestamp
            prompt.updated_at = datetime.utcnow()
            self._prompts[prompt.id] = prompt
            return prompt

    async def delete(self, prompt_id: str) -> bool:
        """Soft delete a prompt by setting is_active=False.

        Args:
            prompt_id: The ID of the prompt to delete

        Returns:
            True if deleted, False if not found
        """
        async with self._lock:
            prompt = self._prompts.get(prompt_id)
            if not prompt:
                return False

            # Create a new instance with is_active=False
            # Since Pydantic models are immutable, we need to use model_copy
            updated_prompt = prompt.model_copy(update={"is_active": False})
            self._prompts[prompt_id] = updated_prompt
            return True

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
        async with self._lock:
            # Filter active prompts for tenant
            filtered = [
                p for p in self._prompts.values() if p.tenant_id == tenant_id and p.is_active
            ]

            # Sort by created_at descending
            sorted_prompts = sorted(
                filtered,
                key=lambda p: p.created_at,
                reverse=True,
            )

            # Apply pagination
            return sorted_prompts[offset : offset + limit]

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
        async with self._lock:
            # Verify parent prompt exists
            if version.prompt_id not in self._prompts:
                raise PromptNotFoundError(version.prompt_id)

            # Store the version
            self._versions[version.id] = version
            return version

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
        async with self._lock:
            for version in self._versions.values():
                if version.prompt_id == prompt_id and version.version_number == version_number:
                    return version
            return None

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
        async with self._lock:
            # Filter versions for prompt
            filtered = [v for v in self._versions.values() if v.prompt_id == prompt_id]

            # Sort by version_number descending
            sorted_versions = sorted(
                filtered,
                key=lambda v: v.version_number,
                reverse=True,
            )

            # Apply pagination
            return sorted_versions[offset : offset + limit]

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
        async with self._lock:
            # Get the prompt
            prompt = self._prompts.get(prompt_id)
            if not prompt:
                raise PromptNotFoundError(prompt_id)

            # Get the version
            version = None
            for v in self._versions.values():
                if v.prompt_id == prompt_id and v.version_number == version_number:
                    version = v
                    break

            if not version:
                raise PromptVersionNotFoundError(prompt_id, version_number)

            # Update prompt with version content
            updated_prompt = prompt.model_copy(
                update={
                    "content": version.content,
                    "merge_points": version.merge_points,
                    "variables_schema": version.variables_schema,
                    "version": version_number,
                    "updated_at": datetime.utcnow(),
                }
            )

            self._prompts[prompt_id] = updated_prompt
            return updated_prompt

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
        async with self._lock:
            # Verify parent prompt exists
            if experiment.prompt_id not in self._prompts:
                raise PromptNotFoundError(experiment.prompt_id)

            # Store the experiment
            self._experiments[experiment.id] = experiment
            return experiment

    async def get_experiment(self, experiment_id: str) -> Optional[PromptExperiment]:
        """Retrieve an experiment by ID.

        Args:
            experiment_id: The experiment ID to retrieve

        Returns:
            The experiment if found, None otherwise
        """
        async with self._lock:
            return self._experiments.get(experiment_id)

    async def get_active_experiment(self, prompt_id: str) -> Optional[PromptExperiment]:
        """Retrieve the active experiment for a prompt.

        Args:
            prompt_id: The prompt ID

        Returns:
            The active experiment if found, None otherwise
        """
        async with self._lock:
            for experiment in self._experiments.values():
                if (
                    experiment.prompt_id == prompt_id
                    and experiment.status == ExperimentStatus.RUNNING
                ):
                    return experiment
            return None

    async def update_experiment(self, experiment: PromptExperiment) -> PromptExperiment:
        """Update an existing experiment.

        Args:
            experiment: The experiment with updated data

        Returns:
            The updated experiment

        Raises:
            ExperimentNotFoundError: If experiment does not exist
        """
        async with self._lock:
            if experiment.id not in self._experiments:
                raise ExperimentNotFoundError(experiment.id)

            # Update timestamp
            experiment.updated_at = datetime.utcnow()
            self._experiments[experiment.id] = experiment
            return experiment

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
        async with self._lock:
            # Filter experiments for prompt
            filtered = [e for e in self._experiments.values() if e.prompt_id == prompt_id]

            # Apply status filter if provided
            if status is not None:
                filtered = [e for e in filtered if e.status == status]

            # Sort by created_at descending
            sorted_experiments = sorted(
                filtered,
                key=lambda e: e.created_at,
                reverse=True,
            )

            # Apply pagination
            return sorted_experiments[offset : offset + limit]
