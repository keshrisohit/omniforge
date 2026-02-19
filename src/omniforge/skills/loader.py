"""Skill loader with indexing, caching, and priority resolution.

This module provides the SkillLoader class that handles skill discovery,
indexing, caching, and loading with proper priority resolution across
storage layers.
"""

import logging
import time
from threading import RLock
from typing import Optional

from omniforge.skills.errors import SkillNotFoundError, SkillParseError, SkillValidationError
from omniforge.skills.models import Skill, SkillIndexEntry
from omniforge.skills.parser import SkillParser
from omniforge.skills.storage import SkillStorageManager, StorageConfig

logger = logging.getLogger(__name__)

# Maximum allowed lines in SKILL.md for progressive context loading
MAX_SKILL_MD_LINES = 500


class SkillLoader:
    """Loader for skill indexing, caching, and priority resolution.

    Manages skill discovery across storage layers with priority-based conflict
    resolution, caching with TTL, and thread-safe operations.

    Attributes:
        DEFAULT_CACHE_TTL: Default cache TTL in seconds (5 minutes)
        INDEX_REBUILD_COOLDOWN: Minimum seconds between index rebuilds (60s)
    """

    DEFAULT_CACHE_TTL = 300  # 5 minutes
    INDEX_REBUILD_COOLDOWN = 60  # 60 seconds

    def __init__(self, config: StorageConfig, cache_ttl_seconds: int = DEFAULT_CACHE_TTL) -> None:
        """Initialize skill loader with configuration.

        Args:
            config: Storage configuration defining layer paths
            cache_ttl_seconds: Cache TTL in seconds (default: 300)
        """
        self._config = config
        self._cache_ttl = cache_ttl_seconds
        self._storage_manager = SkillStorageManager(config)
        self._parser = SkillParser()

        # Thread-safe data structures
        self._lock = RLock()
        self._index: dict[str, SkillIndexEntry] = {}
        self._skill_cache: dict[str, tuple[Skill, float]] = {}
        self._last_index_build: float = 0.0

    def build_index(self, force: bool = False) -> int:
        """Build skill index by scanning all storage layers.

        Scans all configured storage layers for skills, parses metadata,
        and builds an index with priority-based conflict resolution.
        Includes a 60-second rebuild cooldown unless force=True.

        Args:
            force: If True, bypass rebuild cooldown and force index rebuild

        Returns:
            Number of skills indexed

        Example:
            >>> loader = SkillLoader(config)
            >>> count = loader.build_index()
            >>> print(f"Indexed {count} skills")
            Indexed 42 skills
        """
        with self._lock:
            current_time = time.time()

            # Check rebuild cooldown unless forced
            if not force:
                time_since_last_build = current_time - self._last_index_build
                if time_since_last_build < self.INDEX_REBUILD_COOLDOWN:
                    logger.debug(
                        "Skipping index rebuild (cooldown: %.1fs remaining)",
                        self.INDEX_REBUILD_COOLDOWN - time_since_last_build,
                    )
                    return len(self._index)

            # Clear existing index
            self._index.clear()

            # Track skills by name for conflict resolution
            skill_entries: dict[str, SkillIndexEntry] = {}

            # Scan all storage layers
            for storage_layer, skill_path in self._storage_manager.get_all_skill_paths():
                try:
                    # Parse metadata only (Stage 1)
                    entry = self._parser.parse_metadata(skill_path, storage_layer)

                    # Check for name conflicts
                    if entry.name in skill_entries:
                        existing = skill_entries[entry.name]

                        # Resolve conflict by effective priority
                        existing_priority = self._get_effective_priority(existing)
                        new_priority = self._get_effective_priority(entry)

                        if new_priority > existing_priority:
                            # New skill has higher priority
                            logger.debug(
                                "Skill '%s': replacing %s (priority %d) with %s (priority %d)",
                                entry.name,
                                existing.storage_layer,
                                existing_priority,
                                entry.storage_layer,
                                new_priority,
                            )
                            skill_entries[entry.name] = entry
                        else:
                            # Existing skill has higher or equal priority
                            logger.debug(
                                "Skill '%s': keeping %s (priority %d) over %s (priority %d)",
                                entry.name,
                                existing.storage_layer,
                                existing_priority,
                                entry.storage_layer,
                                new_priority,
                            )
                    else:
                        # No conflict, add to index
                        skill_entries[entry.name] = entry

                except SkillParseError as e:
                    # Log individual parse errors but don't fail entire index
                    logger.warning(
                        "Failed to parse skill at '%s': %s",
                        skill_path,
                        e.reason,
                    )
                    continue

            # Update index with resolved entries
            self._index = skill_entries
            self._last_index_build = current_time

            logger.info("Built skill index with %d skills", len(self._index))
            return len(self._index)

    def list_skills(self) -> list[SkillIndexEntry]:
        """Get sorted list of all indexed skills.

        Returns:
            List of skill index entries sorted by name

        Example:
            >>> loader = SkillLoader(config)
            >>> loader.build_index()
            >>> skills = loader.list_skills()
            >>> for skill in skills:
            ...     print(f"{skill.name}: {skill.description}")
        """
        with self._lock:
            return sorted(self._index.values(), key=lambda e: e.name)

    def get_skill_metadata(self, name: str) -> SkillIndexEntry:
        """Get skill metadata by name.

        Args:
            name: Skill name to look up

        Returns:
            SkillIndexEntry for the requested skill

        Raises:
            SkillNotFoundError: If skill is not found in index

        Example:
            >>> loader = SkillLoader(config)
            >>> loader.build_index()
            >>> metadata = loader.get_skill_metadata("debug-agent")
            >>> print(metadata.description)
        """
        with self._lock:
            if name not in self._index:
                raise SkillNotFoundError(name)
            return self._index[name]

    def load_skill(self, name: str) -> Skill:
        """Load complete skill with caching.

        Performs full skill loading (Stage 2) including content and script
        detection. Uses TTL-based caching to avoid repeated parsing.

        Args:
            name: Skill name to load

        Returns:
            Complete Skill object with metadata, content, and scripts

        Raises:
            SkillNotFoundError: If skill is not found in index

        Example:
            >>> loader = SkillLoader(config)
            >>> loader.build_index()
            >>> skill = loader.load_skill("debug-agent")
            >>> print(skill.content)
        """
        with self._lock:
            # Check if skill exists in index
            if name not in self._index:
                raise SkillNotFoundError(name)

            # Check cache
            current_time = time.time()
            if name in self._skill_cache:
                cached_skill, cached_time = self._skill_cache[name]
                age = current_time - cached_time

                if age < self._cache_ttl:
                    logger.debug("Cache hit for skill '%s' (age: %.1fs)", name, age)
                    return cached_skill
                else:
                    logger.debug("Cache expired for skill '%s' (age: %.1fs)", name, age)

            # Cache miss or expired - load skill
            entry = self._index[name]
            logger.debug("Loading skill '%s' from '%s'", name, entry.path)

            skill = self._parser.parse_full(entry.path, entry.storage_layer)

            # Validate skill content
            self._validate_skill_content(skill)

            # Cache the loaded skill
            self._skill_cache[name] = (skill, current_time)

            return skill

    def has_skill(self, name: str) -> bool:
        """Check if skill exists in index.

        Args:
            name: Skill name to check

        Returns:
            True if skill exists in index, False otherwise

        Example:
            >>> loader = SkillLoader(config)
            >>> loader.build_index()
            >>> if loader.has_skill("debug-agent"):
            ...     print("Skill exists")
        """
        with self._lock:
            return name in self._index

    def invalidate_cache(self, name: Optional[str] = None) -> None:
        """Invalidate skill cache.

        Args:
            name: Optional skill name to invalidate. If None, clears entire cache.

        Example:
            >>> loader = SkillLoader(config)
            >>> loader.invalidate_cache("debug-agent")  # Clear specific skill
            >>> loader.invalidate_cache()  # Clear all cached skills
        """
        with self._lock:
            if name is None:
                # Clear entire cache
                logger.debug("Invalidating entire skill cache")
                self._skill_cache.clear()
            elif name in self._skill_cache:
                # Clear specific skill
                logger.debug("Invalidating cache for skill '%s'", name)
                del self._skill_cache[name]

    def _validate_skill_content(self, skill: Skill) -> None:
        """Validate skill content meets requirements.

        Validates that SKILL.md content is under the 500-line limit for
        progressive context loading. Skills exceeding this limit should move
        detailed content to supporting files (reference.md, examples.md).

        Args:
            skill: Skill object to validate

        Raises:
            SkillValidationError: If skill exceeds line limit without legacy flag
        """
        # Count lines in skill content
        line_count = skill.content.count("\n") + 1

        if line_count > MAX_SKILL_MD_LINES:
            # Check for legacy override flag
            if skill.metadata.legacy_large_file:
                logger.warning(
                    "Skill '%s' SKILL.md exceeds %d lines (%d lines). "
                    "Legacy mode enabled - consider migrating to progressive loading. "
                    "Move detailed content to supporting files (reference.md, examples.md).",
                    skill.metadata.name,
                    MAX_SKILL_MD_LINES,
                    line_count,
                )
            else:
                raise SkillValidationError(
                    skill_name=skill.metadata.name,
                    reason=(
                        f"SKILL.md must be under {MAX_SKILL_MD_LINES} lines "
                        f"(found {line_count} lines). "
                        f"Move detailed content to supporting files "
                        f"(reference.md, examples.md, etc.). "
                        f"For migration guidance, see autonomous skill execution documentation."
                    ),
                    details={
                        "line_count": line_count,
                        "max_lines": MAX_SKILL_MD_LINES,
                        "skill_path": str(skill.path),
                    },
                )

    def _get_effective_priority(self, entry: SkillIndexEntry) -> int:
        """Calculate effective priority for conflict resolution.

        Combines layer priority and explicit priority into a single value
        for comparison during conflict resolution.

        Args:
            entry: Skill index entry

        Returns:
            Effective priority value (higher = higher priority)

        Example:
            >>> # Enterprise layer (priority 4) with explicit priority 5
            >>> effective = (4 * 1000) + 5  # = 4005
        """
        layer_priority = self._storage_manager.get_layer_priority(entry.storage_layer)
        return (layer_priority * 1000) + entry.priority
