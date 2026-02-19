"""Version manager for prompt lifecycle operations.

This module provides the VersionManager class for managing prompt version
lifecycle including creation, retrieval, listing, and rollback operations.
"""

import logging
import uuid
from datetime import datetime

from omniforge.prompts.errors import PromptNotFoundError, PromptVersionNotFoundError
from omniforge.prompts.models import Prompt, PromptVersion
from omniforge.prompts.storage.repository import PromptRepository

logger = logging.getLogger(__name__)


class VersionManager:
    """Manager for prompt version lifecycle operations.

    Handles creating new versions when prompts are updated, retrieving version
    history, and rolling back to previous versions. Ensures version immutability
    and maintains audit trail.

    Attributes:
        _repository: Storage repository for prompts and versions
    """

    def __init__(self, repository: PromptRepository) -> None:
        """Initialize the version manager.

        Args:
            repository: Storage repository for prompts and versions
        """
        self._repository = repository

    async def create_initial_version(self, prompt: Prompt, created_by: str) -> PromptVersion:
        """Create version 1 for a new prompt.

        This should be called when a prompt is first created to establish
        the initial version baseline.

        Args:
            prompt: The newly created prompt
            created_by: ID of the user creating the initial version

        Returns:
            The created initial version (version 1)

        Raises:
            PromptNotFoundError: If the prompt does not exist in the repository
        """
        version = PromptVersion(
            id=self._generate_version_id(),
            prompt_id=prompt.id,
            version_number=1,
            content=prompt.content,
            merge_points=prompt.merge_points.copy(),
            variables_schema=(
                prompt.variables_schema.model_copy(deep=True) if prompt.variables_schema else None
            ),
            change_message="Initial version",
            created_by=created_by,
            created_at=datetime.utcnow(),
        )

        created_version = await self._repository.create_version(version)
        logger.info(
            f"Created initial version for prompt {prompt.id}: "
            f"version={created_version.version_number}"
        )
        return created_version

    async def create_version(
        self, prompt: Prompt, change_message: str, changed_by: str
    ) -> PromptVersion:
        """Create a new version for an updated prompt.

        Gets the next version number and creates a new immutable snapshot
        of the prompt's current state.

        Args:
            prompt: The prompt with updated content
            change_message: Description of what changed in this version
            changed_by: ID of the user making the change

        Returns:
            The newly created version

        Raises:
            PromptNotFoundError: If the prompt does not exist
        """
        # Get current versions to determine next version number
        existing_versions = await self._repository.list_versions(
            prompt_id=prompt.id, limit=1, offset=0
        )

        # Calculate next version number
        next_version_number = 1
        if existing_versions:
            next_version_number = existing_versions[0].version_number + 1

        # Create new version snapshot
        version = PromptVersion(
            id=self._generate_version_id(),
            prompt_id=prompt.id,
            version_number=next_version_number,
            content=prompt.content,
            merge_points=prompt.merge_points.copy(),
            variables_schema=(
                prompt.variables_schema.model_copy(deep=True) if prompt.variables_schema else None
            ),
            change_message=change_message,
            created_by=changed_by,
            created_at=datetime.utcnow(),
        )

        created_version = await self._repository.create_version(version)
        logger.info(
            f"Created version {created_version.version_number} for prompt "
            f"{prompt.id}: {change_message}"
        )
        return created_version

    async def get_version(self, prompt_id: str, version_number: int) -> PromptVersion:
        """Retrieve a specific version of a prompt.

        Args:
            prompt_id: ID of the parent prompt
            version_number: Version number to retrieve

        Returns:
            The requested version

        Raises:
            PromptVersionNotFoundError: If the version does not exist
        """
        version = await self._repository.get_version(prompt_id, version_number)
        if not version:
            raise PromptVersionNotFoundError(prompt_id, version_number)

        logger.debug(f"Retrieved version {version_number} for prompt {prompt_id}")
        return version

    async def list_versions(
        self, prompt_id: str, limit: int = 50, offset: int = 0
    ) -> list[PromptVersion]:
        """List all versions for a prompt.

        Returns versions sorted by version number in descending order
        (newest first).

        Args:
            prompt_id: ID of the parent prompt
            limit: Maximum number of versions to return (default: 50)
            offset: Number of versions to skip for pagination (default: 0)

        Returns:
            List of versions sorted by version_number descending
        """
        versions = await self._repository.list_versions(
            prompt_id=prompt_id, limit=limit, offset=offset
        )

        logger.debug(
            f"Listed {len(versions)} versions for prompt {prompt_id} "
            f"(limit={limit}, offset={offset})"
        )
        return versions

    async def rollback(self, prompt_id: str, to_version: int, rolled_back_by: str) -> Prompt:
        """Rollback a prompt to a previous version.

        This operation:
        1. Verifies the target version exists
        2. Updates the prompt to use the target version's content
        3. Creates a new version documenting the rollback
        4. Returns the updated prompt

        Args:
            prompt_id: ID of the prompt to rollback
            to_version: Version number to rollback to
            rolled_back_by: ID of the user performing the rollback

        Returns:
            The updated prompt with content from the target version

        Raises:
            PromptNotFoundError: If the prompt does not exist
            PromptVersionNotFoundError: If the target version does not exist
        """
        # Verify prompt exists
        prompt = await self._repository.get(prompt_id)
        if not prompt:
            raise PromptNotFoundError(prompt_id)

        # Verify target version exists
        target_version = await self._repository.get_version(prompt_id, to_version)
        if not target_version:
            raise PromptVersionNotFoundError(prompt_id, to_version)

        # Update prompt content from target version
        prompt.content = target_version.content
        prompt.merge_points = target_version.merge_points.copy()
        prompt.variables_schema = (
            target_version.variables_schema.model_copy(deep=True)
            if target_version.variables_schema
            else None
        )
        prompt.updated_at = datetime.utcnow()

        # Save the updated prompt
        updated_prompt = await self._repository.update(prompt)

        # Create a new version documenting the rollback
        rollback_message = f"Rolled back to version {to_version}"
        await self.create_version(
            prompt=updated_prompt,
            change_message=rollback_message,
            changed_by=rolled_back_by,
        )

        logger.info(
            f"Rolled back prompt {prompt_id} to version {to_version} " f"by user {rolled_back_by}"
        )
        return updated_prompt

    async def get_current_version(self, prompt_id: str) -> PromptVersion:
        """Get the currently active version for a prompt.

        Retrieves the most recent version from the version history.

        Args:
            prompt_id: ID of the parent prompt

        Returns:
            The current (most recent) version

        Raises:
            PromptVersionNotFoundError: If no versions exist for the prompt
        """
        versions = await self._repository.list_versions(prompt_id=prompt_id, limit=1, offset=0)

        if not versions:
            raise PromptVersionNotFoundError(prompt_id, 1)

        logger.debug(
            f"Retrieved current version {versions[0].version_number} " f"for prompt {prompt_id}"
        )
        return versions[0]

    @staticmethod
    def _generate_version_id() -> str:
        """Generate a unique ID for a version.

        Returns:
            A unique version ID
        """
        return f"ver_{uuid.uuid4().hex}"
