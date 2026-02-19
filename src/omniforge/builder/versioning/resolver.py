"""Version resolution and compatibility checking for public skills."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class VersionCompatibility(str, Enum):
    """Version compatibility levels."""

    COMPATIBLE = "compatible"  # Minor/patch version difference
    BREAKING = "breaking"  # Major version difference
    EXACT = "exact"  # Same version


@dataclass
class SemanticVersion:
    """Semantic version representation (MAJOR.MINOR.PATCH).

    Attributes:
        major: Major version (breaking changes)
        minor: Minor version (backward-compatible features)
        patch: Patch version (backward-compatible fixes)
    """

    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, version_string: str) -> "SemanticVersion":
        """Parse semantic version string.

        Args:
            version_string: Version string in format "MAJOR.MINOR.PATCH"

        Returns:
            SemanticVersion instance

        Raises:
            ValueError: If version string is invalid
        """
        try:
            parts = version_string.split(".")
            if len(parts) != 3:
                raise ValueError(
                    f"Invalid version format: {version_string}. Expected MAJOR.MINOR.PATCH"
                )

            major, minor, patch = map(int, parts)
            return cls(major=major, minor=minor, patch=patch)
        except (ValueError, AttributeError) as e:
            raise ValueError(f"Invalid semantic version '{version_string}': {e}") from e

    def __str__(self) -> str:
        """Return version as string."""
        return f"{self.major}.{self.minor}.{self.patch}"

    def __lt__(self, other: "SemanticVersion") -> bool:
        """Compare versions for less than."""
        return (self.major, self.minor, self.patch) < (
            other.major,
            other.minor,
            other.patch,
        )

    def __le__(self, other: "SemanticVersion") -> bool:
        """Compare versions for less than or equal."""
        return (self.major, self.minor, self.patch) <= (
            other.major,
            other.minor,
            other.patch,
        )

    def __gt__(self, other: "SemanticVersion") -> bool:
        """Compare versions for greater than."""
        return (self.major, self.minor, self.patch) > (
            other.major,
            other.minor,
            other.patch,
        )

    def __ge__(self, other: "SemanticVersion") -> bool:
        """Compare versions for greater than or equal."""
        return (self.major, self.minor, self.patch) >= (
            other.major,
            other.minor,
            other.patch,
        )

    def __eq__(self, other: object) -> bool:
        """Compare versions for equality."""
        if not isinstance(other, SemanticVersion):
            return False
        return (self.major, self.minor, self.patch) == (
            other.major,
            other.minor,
            other.patch,
        )


class VersionResolver:
    """Resolves and compares skill versions."""

    @staticmethod
    def resolve_latest(versions: list[str]) -> Optional[str]:
        """Find the latest version from a list of version strings.

        Args:
            versions: List of version strings

        Returns:
            Latest version string, or None if list is empty

        Raises:
            ValueError: If any version string is invalid
        """
        if not versions:
            return None

        parsed_versions = [SemanticVersion.parse(v) for v in versions]
        latest = max(parsed_versions)
        return str(latest)

    @staticmethod
    def check_compatibility(current_version: str, new_version: str) -> VersionCompatibility:
        """Check compatibility between two versions.

        Args:
            current_version: Current version string
            new_version: New version to compare

        Returns:
            VersionCompatibility level

        Raises:
            ValueError: If any version string is invalid
        """
        current = SemanticVersion.parse(current_version)
        new = SemanticVersion.parse(new_version)

        if current == new:
            return VersionCompatibility.EXACT

        if current.major != new.major:
            return VersionCompatibility.BREAKING

        return VersionCompatibility.COMPATIBLE

    @staticmethod
    def has_newer_version(current_version: str, available_versions: list[str]) -> bool:
        """Check if newer version exists for pinned skill.

        Args:
            current_version: Current pinned version
            available_versions: List of available versions

        Returns:
            True if newer version exists, False otherwise
        """
        if not available_versions:
            return False

        current = SemanticVersion.parse(current_version)
        latest_version = VersionResolver.resolve_latest(available_versions)

        if not latest_version:
            return False

        latest = SemanticVersion.parse(latest_version)
        return latest > current

    @staticmethod
    def get_version_warning(current_version: str, new_version: str) -> Optional[str]:
        """Generate warning message for version changes.

        Args:
            current_version: Current version string
            new_version: New version string

        Returns:
            Warning message if breaking change detected, None otherwise
        """
        compatibility = VersionResolver.check_compatibility(current_version, new_version)

        if compatibility == VersionCompatibility.BREAKING:
            current = SemanticVersion.parse(current_version)
            new = SemanticVersion.parse(new_version)
            return (
                f"Breaking change detected: upgrading from v{current} to v{new}. "
                f"Major version changes may include breaking changes. "
                f"Review the skill documentation before upgrading."
            )

        return None

    @staticmethod
    def filter_compatible_versions(target_version: str, available_versions: list[str]) -> list[str]:
        """Filter versions compatible with target version (same major).

        Args:
            target_version: Target version to check compatibility against
            available_versions: List of available versions

        Returns:
            List of compatible version strings
        """
        target = SemanticVersion.parse(target_version)

        compatible = []
        for version_str in available_versions:
            version = SemanticVersion.parse(version_str)
            if version.major == target.major:
                compatible.append(version_str)

        return compatible
