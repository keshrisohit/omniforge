"""Storage layer management for the 4-layer skill hierarchy.

This module implements the storage configuration and management system that
handles skill discovery across enterprise, personal, project, and plugin layers.
"""

from pathlib import Path
from typing import Iterator, Optional

from pydantic import BaseModel, ConfigDict


class StorageConfig(BaseModel):
    """Configuration for skill storage locations.

    Defines the directory paths for each storage layer in the skill hierarchy.

    Attributes:
        enterprise_path: Optional path to enterprise-wide skills
        personal_path: Optional path to user's personal skills
        project_path: Optional path to project-specific skills
        plugin_paths: List of paths to plugin-provided skills
    """

    enterprise_path: Optional[Path] = None
    personal_path: Optional[Path] = None
    project_path: Optional[Path] = None
    plugin_paths: list[Path] = []

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @classmethod
    def from_environment(cls, project_root: Optional[Path] = None) -> "StorageConfig":
        """Create storage configuration with default environment paths.

        Creates a default configuration using standard .omniforge directory
        locations for each storage layer.

        Args:
            project_root: Optional project root directory for project-level skills.
                         If None, project_path will not be set.

        Returns:
            StorageConfig with default paths configured
        """
        home = Path.home()

        return cls(
            enterprise_path=home / ".omniforge" / "enterprise" / "skills",
            personal_path=home / ".omniforge" / "skills",
            project_path=project_root / ".omniforge" / "skills" if project_root else None,
            plugin_paths=[],
        )


class SkillStorageManager:
    """Manages skill discovery across the 4-layer storage hierarchy.

    Handles scanning and enumeration of skills from enterprise, personal,
    project, and plugin storage layers with proper precedence ordering.

    Attributes:
        LAYER_ORDER: Class constant defining layer priority order
    """

    LAYER_ORDER = ["enterprise", "personal", "project", "plugin"]

    def __init__(self, config: StorageConfig) -> None:
        """Initialize storage manager with configuration.

        Args:
            config: Storage configuration defining layer paths
        """
        self._config = config

    def get_all_skill_paths(self) -> Iterator[tuple[str, Path]]:
        """Get all skill paths across all layers in priority order.

        Scans all configured storage layers for SKILL.md files and yields
        them in priority order (enterprise -> personal -> project -> plugin).

        Yields:
            Tuple of (storage_layer, skill_path) where:
                - storage_layer: Layer identifier ("enterprise", "personal", etc.)
                - skill_path: Absolute path to the SKILL.md file

        Example:
            >>> manager = SkillStorageManager(config)
            >>> for layer, path in manager.get_all_skill_paths():
            ...     print(f"{layer}: {path}")
            enterprise: /home/user/.omniforge/enterprise/skills/debug-agent/SKILL.md
            personal: /home/user/.omniforge/skills/my-skill/SKILL.md
        """
        # Enterprise layer
        if self._config.enterprise_path:
            yield from self._scan_directory("enterprise", self._config.enterprise_path)

        # Personal layer
        if self._config.personal_path:
            yield from self._scan_directory("personal", self._config.personal_path)

        # Project layer
        if self._config.project_path:
            yield from self._scan_directory("project", self._config.project_path)

        # Plugin layers
        for plugin_path in self._config.plugin_paths:
            yield from self._scan_directory("plugin", plugin_path)

    def _scan_directory(self, layer: str, base_path: Path) -> Iterator[tuple[str, Path]]:
        """Scan a directory for SKILL.md files in immediate subdirectories.

        Looks for SKILL.md files only in the immediate subdirectories of the
        base path (not recursive). Silently skips if the directory doesn't exist.

        Args:
            layer: Storage layer identifier
            base_path: Base directory path to scan

        Yields:
            Tuple of (storage_layer, skill_path) for each found SKILL.md file

        Example:
            Given directory structure:
                /base/
                  skill-a/SKILL.md
                  skill-b/SKILL.md
                  skill-c/nested/SKILL.md  # NOT included (not immediate)

            Will yield:
                ("layer", Path("/base/skill-a/SKILL.md"))
                ("layer", Path("/base/skill-b/SKILL.md"))
        """
        # Skip if directory doesn't exist
        if not base_path.exists() or not base_path.is_dir():
            return

        # Scan immediate subdirectories for SKILL.md
        for item in base_path.iterdir():
            if item.is_dir():
                skill_file = item / "SKILL.md"
                if skill_file.exists() and skill_file.is_file():
                    yield (layer, skill_file)

    def get_layer_priority(self, layer: str) -> int:
        """Get the priority value for a storage layer.

        Returns a numeric priority where higher values indicate higher precedence.
        Enterprise layer has highest priority, plugin has lowest.

        Args:
            layer: Storage layer identifier

        Returns:
            Priority value (4 for enterprise, 3 for personal, 2 for project, 1 for plugin)

        Raises:
            ValueError: If layer is not a valid layer identifier

        Example:
            >>> manager.get_layer_priority("enterprise")
            4
            >>> manager.get_layer_priority("plugin")
            1
        """
        if layer not in self.LAYER_ORDER:
            raise ValueError(
                f"Invalid layer '{layer}'. Must be one of: {', '.join(self.LAYER_ORDER)}"
            )

        # Return priority (higher number = higher priority)
        return len(self.LAYER_ORDER) - self.LAYER_ORDER.index(layer)
