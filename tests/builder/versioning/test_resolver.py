"""Tests for version resolution and compatibility checking."""

import pytest

from omniforge.builder.versioning import (
    SemanticVersion,
    VersionCompatibility,
    VersionResolver,
)


class TestSemanticVersion:
    """Tests for SemanticVersion class."""

    def test_parse_valid_version(self) -> None:
        """SemanticVersion should parse valid version strings."""
        version = SemanticVersion.parse("1.2.3")

        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3

    def test_parse_invalid_format_raises_error(self) -> None:
        """SemanticVersion should raise error for invalid format."""
        with pytest.raises(ValueError, match="Invalid version format"):
            SemanticVersion.parse("1.2")

        with pytest.raises(ValueError, match="Invalid version format"):
            SemanticVersion.parse("1.2.3.4")

    def test_parse_non_numeric_raises_error(self) -> None:
        """SemanticVersion should raise error for non-numeric parts."""
        with pytest.raises(ValueError, match="Invalid semantic version"):
            SemanticVersion.parse("1.2.x")

    def test_string_representation(self) -> None:
        """SemanticVersion should convert to string correctly."""
        version = SemanticVersion(major=1, minor=2, patch=3)

        assert str(version) == "1.2.3"

    def test_version_comparison_less_than(self) -> None:
        """SemanticVersion should compare versions correctly for less than."""
        v1 = SemanticVersion(1, 0, 0)
        v2 = SemanticVersion(2, 0, 0)
        v3 = SemanticVersion(1, 1, 0)
        v4 = SemanticVersion(1, 0, 1)

        assert v1 < v2
        assert v1 < v3
        assert v1 < v4
        assert not v2 < v1

    def test_version_comparison_greater_than(self) -> None:
        """SemanticVersion should compare versions correctly for greater than."""
        v1 = SemanticVersion(2, 0, 0)
        v2 = SemanticVersion(1, 0, 0)

        assert v1 > v2
        assert not v2 > v1

    def test_version_equality(self) -> None:
        """SemanticVersion should check equality correctly."""
        v1 = SemanticVersion(1, 2, 3)
        v2 = SemanticVersion(1, 2, 3)
        v3 = SemanticVersion(1, 2, 4)

        assert v1 == v2
        assert not v1 == v3

    def test_version_comparison_operators(self) -> None:
        """SemanticVersion should support all comparison operators."""
        v1 = SemanticVersion(1, 0, 0)
        v2 = SemanticVersion(2, 0, 0)
        v3 = SemanticVersion(1, 0, 0)

        assert v1 <= v2
        assert v1 <= v3
        assert v2 >= v1
        assert v1 >= v3


class TestVersionResolver:
    """Tests for VersionResolver class."""

    def test_resolve_latest_from_versions(self) -> None:
        """VersionResolver should find latest version from list."""
        versions = ["1.0.0", "2.1.0", "1.5.3", "2.0.0"]

        latest = VersionResolver.resolve_latest(versions)

        assert latest == "2.1.0"

    def test_resolve_latest_empty_list(self) -> None:
        """VersionResolver should return None for empty list."""
        latest = VersionResolver.resolve_latest([])

        assert latest is None

    def test_resolve_latest_single_version(self) -> None:
        """VersionResolver should return single version."""
        latest = VersionResolver.resolve_latest(["1.0.0"])

        assert latest == "1.0.0"

    def test_check_compatibility_exact(self) -> None:
        """VersionResolver should detect exact version match."""
        compatibility = VersionResolver.check_compatibility("1.2.3", "1.2.3")

        assert compatibility == VersionCompatibility.EXACT

    def test_check_compatibility_compatible(self) -> None:
        """VersionResolver should detect compatible versions (same major)."""
        compatibility1 = VersionResolver.check_compatibility("1.0.0", "1.1.0")
        compatibility2 = VersionResolver.check_compatibility("1.0.0", "1.0.1")

        assert compatibility1 == VersionCompatibility.COMPATIBLE
        assert compatibility2 == VersionCompatibility.COMPATIBLE

    def test_check_compatibility_breaking(self) -> None:
        """VersionResolver should detect breaking changes (different major)."""
        compatibility = VersionResolver.check_compatibility("1.0.0", "2.0.0")

        assert compatibility == VersionCompatibility.BREAKING

    def test_has_newer_version_true(self) -> None:
        """VersionResolver should detect newer versions."""
        has_newer = VersionResolver.has_newer_version(
            "1.0.0", ["1.0.0", "1.1.0", "2.0.0"]
        )

        assert has_newer is True

    def test_has_newer_version_false(self) -> None:
        """VersionResolver should return False when on latest version."""
        has_newer = VersionResolver.has_newer_version(
            "2.0.0", ["1.0.0", "1.1.0", "2.0.0"]
        )

        assert has_newer is False

    def test_has_newer_version_empty_list(self) -> None:
        """VersionResolver should return False for empty available versions."""
        has_newer = VersionResolver.has_newer_version("1.0.0", [])

        assert has_newer is False

    def test_get_version_warning_breaking_change(self) -> None:
        """VersionResolver should generate warning for breaking changes."""
        warning = VersionResolver.get_version_warning("1.0.0", "2.0.0")

        assert warning is not None
        assert "Breaking change detected" in warning
        assert "v1.0.0" in warning
        assert "v2.0.0" in warning

    def test_get_version_warning_compatible_change(self) -> None:
        """VersionResolver should not generate warning for compatible changes."""
        warning1 = VersionResolver.get_version_warning("1.0.0", "1.1.0")
        warning2 = VersionResolver.get_version_warning("1.0.0", "1.0.1")

        assert warning1 is None
        assert warning2 is None

    def test_get_version_warning_exact_match(self) -> None:
        """VersionResolver should not generate warning for exact match."""
        warning = VersionResolver.get_version_warning("1.0.0", "1.0.0")

        assert warning is None

    def test_filter_compatible_versions(self) -> None:
        """VersionResolver should filter compatible versions (same major)."""
        versions = ["1.0.0", "1.1.0", "1.2.0", "2.0.0", "2.1.0", "3.0.0"]

        compatible = VersionResolver.filter_compatible_versions("1.5.0", versions)

        assert compatible == ["1.0.0", "1.1.0", "1.2.0"]
        assert "2.0.0" not in compatible
        assert "3.0.0" not in compatible

    def test_filter_compatible_versions_no_matches(self) -> None:
        """VersionResolver should return empty list when no compatible versions."""
        versions = ["1.0.0", "2.0.0", "3.0.0"]

        compatible = VersionResolver.filter_compatible_versions("4.0.0", versions)

        assert compatible == []

    def test_version_ordering_complex(self) -> None:
        """VersionResolver should correctly order complex version lists."""
        versions = ["1.0.0", "1.10.0", "1.2.0", "2.0.0", "1.9.9"]

        latest = VersionResolver.resolve_latest(versions)

        assert latest == "2.0.0"

    def test_parse_version_with_leading_zeros(self) -> None:
        """SemanticVersion should handle versions with leading zeros."""
        version = SemanticVersion.parse("1.0.0")

        assert version.major == 1
        assert version.minor == 0
        assert version.patch == 0
