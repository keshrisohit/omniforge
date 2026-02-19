"""Skill writer for filesystem operations.

This module handles writing skills to the filesystem with proper directory structure,
atomic writes, and storage layer resolution following official Anthropic Agent Skills format.
"""

import tempfile
from pathlib import Path
from typing import Optional

from omniforge.skills.storage import SkillStorageManager


class SkillWriterError(Exception):
    """Base exception for skill writer errors."""

    pass


class SkillExistsError(SkillWriterError):
    """Raised when attempting to write a skill that already exists."""

    pass


class StoragePermissionError(SkillWriterError):
    """Raised when lacking permissions to write to storage layer."""

    pass


class SkillWriter:
    """Write skills to filesystem following official structure.

    Handles filesystem operations for saving skills with proper directory structure,
    atomic writes, and conflict detection. Supports the 4-layer skill storage hierarchy.

    Official directory structure created:
        skill-name/
        |-- SKILL.md (required)
        |-- scripts/     (optional)
        |-- references/  (optional)
        +-- assets/      (optional)

    Attributes:
        storage_manager: Manager for storage layer path resolution
    """

    def __init__(self, storage_manager: SkillStorageManager) -> None:
        """Initialize the skill writer.

        Args:
            storage_manager: Storage manager for layer path resolution
        """
        self.storage_manager = storage_manager

    async def write_skill(
        self,
        skill_name: str,
        content: str,
        storage_layer: str,
        resources: Optional[dict[str, str]] = None,
    ) -> Path:
        """Write skill to storage layer with atomic operations.

        Creates the official directory structure and writes SKILL.md atomically
        using a temporary file approach to ensure data consistency.

        Args:
            skill_name: Skill identifier in kebab-case
            content: Complete SKILL.md content (frontmatter + body)
            storage_layer: Target storage layer (project, personal, enterprise)
            resources: Optional dict of resource_path -> content for bundled resources

        Returns:
            Absolute path to the written SKILL.md file

        Raises:
            SkillExistsError: If skill already exists in the storage layer
            StoragePermissionError: If lacking write permissions
            SkillWriterError: If write operation fails
            ValueError: If storage_layer is invalid
        """
        # Validate storage layer
        if storage_layer not in ["project", "personal", "enterprise"]:
            raise ValueError(
                f"Invalid storage layer '{storage_layer}'. "
                "Must be one of: project, personal, enterprise"
            )

        # Check for existing skill
        if self.skill_exists(skill_name, storage_layer):
            raise SkillExistsError(
                f"Skill '{skill_name}' already exists in {storage_layer} layer. "
                "Choose a different name or delete the existing skill."
            )

        # Get target directory
        skill_dir = self.get_skill_directory(skill_name, storage_layer)

        # Check write permissions by trying to create the parent directory
        try:
            skill_dir.mkdir(parents=True, exist_ok=False)
        except PermissionError as e:
            raise StoragePermissionError(
                f"Permission denied: cannot write to {storage_layer} layer at {skill_dir.parent}"
            ) from e
        except OSError as e:
            raise SkillWriterError(f"Failed to create skill directory: {e}") from e

        # Write SKILL.md atomically
        skill_md_path = skill_dir / "SKILL.md"
        try:
            self._write_file_atomic(skill_md_path, content)
        except Exception as e:
            # Clean up partial directory on failure
            if skill_dir.exists():
                try:
                    skill_dir.rmdir()
                except OSError:
                    pass  # Best effort cleanup
            raise SkillWriterError(f"Failed to write SKILL.md: {e}") from e

        # Write bundled resources if provided
        if resources:
            for resource_path, resource_content in resources.items():
                try:
                    await self.write_bundled_resource(skill_dir, resource_path, resource_content)
                except Exception as e:
                    raise SkillWriterError(
                        f"Failed to write bundled resource '{resource_path}': {e}"
                    ) from e

        return skill_md_path

    def get_skill_directory(self, skill_name: str, storage_layer: str) -> Path:
        """Get target directory for skill in specified storage layer.

        Resolves the absolute path where the skill directory should be created
        based on the storage layer configuration.

        Args:
            skill_name: Skill identifier in kebab-case
            storage_layer: Target storage layer (project, personal, enterprise)

        Returns:
            Absolute path to skill directory

        Raises:
            ValueError: If storage_layer is invalid or not configured

        Example:
            >>> writer.get_skill_directory("my-skill", "project")
            Path("/path/to/project/.omniforge/skills/my-skill")
        """
        # Get base path for layer from storage manager config
        config = self.storage_manager._config

        if storage_layer == "project":
            base_path = config.project_path
        elif storage_layer == "personal":
            base_path = config.personal_path
        elif storage_layer == "enterprise":
            base_path = config.enterprise_path
        else:
            raise ValueError(
                f"Invalid storage layer '{storage_layer}'. "
                "Must be one of: project, personal, enterprise"
            )

        if base_path is None:
            raise ValueError(f"Storage layer '{storage_layer}' is not configured")

        # Return absolute path to skill directory
        return base_path / skill_name

    def skill_exists(self, skill_name: str, storage_layer: str) -> bool:
        """Check if skill already exists in specified storage layer.

        A skill is considered to exist if a directory with the skill name exists
        and contains a SKILL.md file.

        Args:
            skill_name: Skill identifier in kebab-case
            storage_layer: Target storage layer (project, personal, enterprise)

        Returns:
            True if skill exists, False otherwise

        Example:
            >>> writer.skill_exists("my-skill", "project")
            False
        """
        try:
            skill_dir = self.get_skill_directory(skill_name, storage_layer)
        except ValueError:
            # Storage layer not configured, skill doesn't exist
            return False

        # Check if directory exists and contains SKILL.md
        skill_md = skill_dir / "SKILL.md"
        return skill_md.exists() and skill_md.is_file()

    async def write_bundled_resource(
        self,
        skill_dir: Path,
        resource_path: str,
        content: str,
    ) -> Path:
        """Write bundled resource file to skill directory.

        Creates subdirectories as needed and writes the resource content
        atomically. Supports scripts/, references/, and assets/ subdirectories
        per official Anthropic format.

        Args:
            skill_dir: Absolute path to skill directory
            resource_path: Relative path within skill directory (e.g., "scripts/process.py")
            content: Resource file content

        Returns:
            Absolute path to written resource file

        Raises:
            SkillWriterError: If write operation fails

        Example:
            >>> await writer.write_bundled_resource(
            ...     Path("/path/to/skill"),
            ...     "scripts/helper.py",
            ...     "print('hello')"
            ... )
            Path("/path/to/skill/scripts/helper.py")
        """
        # Ensure forward slashes per official spec
        resource_path = resource_path.replace("\\", "/")

        # Construct full path
        full_path = skill_dir / resource_path

        # Create parent directories
        try:
            full_path.parent.mkdir(parents=True, exist_ok=True)
        except PermissionError as e:
            raise StoragePermissionError(
                f"Permission denied: cannot create directory {full_path.parent}"
            ) from e
        except OSError as e:
            raise SkillWriterError(f"Failed to create resource directory: {e}") from e

        # Write file atomically
        try:
            self._write_file_atomic(full_path, content)
        except Exception as e:
            raise SkillWriterError(f"Failed to write resource file: {e}") from e

        return full_path

    def _write_file_atomic(self, target_path: Path, content: str) -> None:
        """Write file atomically using temp file + rename.

        This ensures that the file is either fully written or not present at all,
        avoiding partial writes in case of failures.

        Args:
            target_path: Target file path
            content: File content to write

        Raises:
            OSError: If write or rename operation fails
        """
        # Create temp file in same directory as target for atomic rename
        temp_fd = None
        temp_path = None

        try:
            # Create temporary file in same directory
            temp_fd = tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=target_path.parent,
                delete=False,
                prefix=f".{target_path.name}.",
                suffix=".tmp",
            )
            temp_path = Path(temp_fd.name)

            # Write content to temp file
            temp_fd.write(content)
            temp_fd.flush()

            # Close file descriptor
            temp_fd.close()
            temp_fd = None

            # Atomically rename temp file to target
            temp_path.replace(target_path)
            temp_path = None  # Rename succeeded

        finally:
            # Clean up temp file if still exists
            if temp_fd is not None:
                try:
                    temp_fd.close()
                except OSError:
                    pass

            if temp_path is not None and temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass  # Best effort cleanup
