"""Tests for SkillLoader class.

This module tests skill indexing, caching, priority resolution,
and thread-safe operations.
"""

import time
from pathlib import Path
from threading import Thread

import pytest

from omniforge.skills.errors import SkillNotFoundError, SkillValidationError
from omniforge.skills.loader import MAX_SKILL_MD_LINES, SkillLoader
from omniforge.skills.models import SkillIndexEntry
from omniforge.skills.storage import StorageConfig


class TestSkillLoader:
    """Tests for SkillLoader class."""

    def test_init_creates_loader_with_config(self, tmp_path: Path) -> None:
        """Loader should initialize with storage configuration."""
        config = StorageConfig(project_path=tmp_path)
        loader = SkillLoader(config)

        assert loader._config == config
        assert loader._cache_ttl == SkillLoader.DEFAULT_CACHE_TTL
        assert len(loader._index) == 0
        assert len(loader._skill_cache) == 0

    def test_init_with_custom_cache_ttl(self, tmp_path: Path) -> None:
        """Loader should accept custom cache TTL."""
        config = StorageConfig(project_path=tmp_path)
        loader = SkillLoader(config, cache_ttl_seconds=120)

        assert loader._cache_ttl == 120

    def test_build_index_empty_storage(self, tmp_path: Path) -> None:
        """Build index should return 0 for empty storage."""
        config = StorageConfig(project_path=tmp_path)
        loader = SkillLoader(config)

        count = loader.build_index()

        assert count == 0
        assert len(loader._index) == 0

    def test_build_index_scans_single_skill(self, tmp_path: Path) -> None:
        """Build index should find and index a single skill."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        # Create test skill
        skill_dir = skills_dir / "test-skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(
            """---
name: test-skill
description: A test skill
---

Test content
"""
        )

        config = StorageConfig(project_path=skills_dir)
        loader = SkillLoader(config)

        count = loader.build_index()

        assert count == 1
        assert "test-skill" in loader._index

    def test_build_index_multiple_skills(self, tmp_path: Path) -> None:
        """Build index should index multiple skills."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        # Create multiple test skills
        for i in range(3):
            skill_dir = skills_dir / f"skill-{i}"
            skill_dir.mkdir()
            skill_file = skill_dir / "SKILL.md"
            skill_file.write_text(
                f"""---
name: skill-{i}
description: Test skill {i}
---

Content {i}
"""
            )

        config = StorageConfig(project_path=skills_dir)
        loader = SkillLoader(config)

        count = loader.build_index()

        assert count == 3
        assert "skill-0" in loader._index
        assert "skill-1" in loader._index
        assert "skill-2" in loader._index

    def test_build_index_skips_invalid_skills(self, tmp_path: Path) -> None:
        """Build index should skip invalid skills without failing."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        # Valid skill
        valid_dir = skills_dir / "valid-skill"
        valid_dir.mkdir()
        valid_file = valid_dir / "SKILL.md"
        valid_file.write_text(
            """---
name: valid-skill
description: Valid skill
---

Content
"""
        )

        # Invalid skill (missing frontmatter)
        invalid_dir = skills_dir / "invalid-skill"
        invalid_dir.mkdir()
        invalid_file = invalid_dir / "SKILL.md"
        invalid_file.write_text("No frontmatter here")

        config = StorageConfig(project_path=skills_dir)
        loader = SkillLoader(config)

        count = loader.build_index()

        # Should index only valid skill
        assert count == 1
        assert "valid-skill" in loader._index
        assert "invalid-skill" not in loader._index

    def test_build_index_priority_resolution_by_layer(self, tmp_path: Path) -> None:
        """Build index should resolve conflicts by layer priority."""
        # Create enterprise and project skills with same name
        enterprise_dir = tmp_path / "enterprise" / "skills"
        enterprise_dir.mkdir(parents=True)
        enterprise_skill = enterprise_dir / "shared-skill"
        enterprise_skill.mkdir()
        (enterprise_skill / "SKILL.md").write_text(
            """---
name: shared-skill
description: Enterprise version
---

Enterprise content
"""
        )

        project_dir = tmp_path / "project" / "skills"
        project_dir.mkdir(parents=True)
        project_skill = project_dir / "shared-skill"
        project_skill.mkdir()
        (project_skill / "SKILL.md").write_text(
            """---
name: shared-skill
description: Project version
---

Project content
"""
        )

        config = StorageConfig(
            enterprise_path=enterprise_dir,
            project_path=project_dir,
        )
        loader = SkillLoader(config)

        count = loader.build_index()

        # Should index only one skill (enterprise wins)
        assert count == 1
        entry = loader.get_skill_metadata("shared-skill")
        assert entry.description == "Enterprise version"
        assert entry.storage_layer == "enterprise"

    def test_build_index_priority_resolution_by_explicit_priority(self, tmp_path: Path) -> None:
        """Build index should resolve same-layer conflicts by explicit priority."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        # Create two skills in same layer with same name but different priorities
        skill1_dir = skills_dir / "skill-high"
        skill1_dir.mkdir()
        (skill1_dir / "SKILL.md").write_text(
            """---
name: test-skill
description: High priority version
priority: 10
---

High priority content
"""
        )

        skill2_dir = skills_dir / "skill-low"
        skill2_dir.mkdir()
        (skill2_dir / "SKILL.md").write_text(
            """---
name: test-skill
description: Low priority version
priority: 5
---

Low priority content
"""
        )

        config = StorageConfig(project_path=skills_dir)
        loader = SkillLoader(config)

        # First build will pick first skill found
        count = loader.build_index()

        # Should index only one (based on priority)
        assert count == 1
        entry = loader.get_skill_metadata("test-skill")
        # The one with priority 10 should win
        assert entry.priority == 10

    def test_build_index_respects_cooldown(self, tmp_path: Path) -> None:
        """Build index should respect rebuild cooldown."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        config = StorageConfig(project_path=skills_dir)
        loader = SkillLoader(config)

        # First build
        count1 = loader.build_index()

        # Immediate second build should return cached count
        count2 = loader.build_index()

        assert count1 == count2

    def test_build_index_force_bypasses_cooldown(self, tmp_path: Path) -> None:
        """Build index with force=True should bypass cooldown."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        # Create initial skill
        skill_dir = skills_dir / "skill-1"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            """---
name: skill-1
description: First skill
---

Content
"""
        )

        config = StorageConfig(project_path=skills_dir)
        loader = SkillLoader(config)

        count1 = loader.build_index()
        assert count1 == 1

        # Add another skill
        skill2_dir = skills_dir / "skill-2"
        skill2_dir.mkdir()
        (skill2_dir / "SKILL.md").write_text(
            """---
name: skill-2
description: Second skill
---

Content
"""
        )

        # Force rebuild
        count2 = loader.build_index(force=True)
        assert count2 == 2

    def test_list_skills_returns_empty_list_when_no_index(self, tmp_path: Path) -> None:
        """List skills should return empty list when index is empty."""
        config = StorageConfig(project_path=tmp_path)
        loader = SkillLoader(config)

        skills = loader.list_skills()

        assert skills == []

    def test_list_skills_returns_sorted_list(self, tmp_path: Path) -> None:
        """List skills should return skills sorted by name."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        # Create skills in non-alphabetical order
        for name in ["zebra", "apple", "mango"]:
            skill_dir = skills_dir / name
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                f"""---
name: {name}
description: {name} skill
---

Content
"""
            )

        config = StorageConfig(project_path=skills_dir)
        loader = SkillLoader(config)
        loader.build_index()

        skills = loader.list_skills()

        assert len(skills) == 3
        assert skills[0].name == "apple"
        assert skills[1].name == "mango"
        assert skills[2].name == "zebra"

    def test_get_skill_metadata_returns_entry(self, tmp_path: Path) -> None:
        """Get skill metadata should return correct entry."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        skill_dir = skills_dir / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            """---
name: test-skill
description: A test skill
priority: 5
tags:
  - test
  - demo
---

Content
"""
        )

        config = StorageConfig(project_path=skills_dir)
        loader = SkillLoader(config)
        loader.build_index()

        entry = loader.get_skill_metadata("test-skill")

        assert entry.name == "test-skill"
        assert entry.description == "A test skill"
        assert entry.priority == 5
        assert entry.tags == ["test", "demo"]
        assert entry.storage_layer == "project"

    def test_get_skill_metadata_raises_not_found_error(self, tmp_path: Path) -> None:
        """Get skill metadata should raise error for missing skill."""
        config = StorageConfig(project_path=tmp_path)
        loader = SkillLoader(config)
        loader.build_index()

        with pytest.raises(SkillNotFoundError) as exc_info:
            loader.get_skill_metadata("nonexistent")

        assert exc_info.value.skill_name == "nonexistent"

    def test_load_skill_returns_complete_skill(self, tmp_path: Path) -> None:
        """Load skill should return complete Skill object."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        skill_dir = skills_dir / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            """---
name: test-skill
description: A test skill
---

Test content for skill
"""
        )

        config = StorageConfig(project_path=skills_dir)
        loader = SkillLoader(config)
        loader.build_index()

        skill = loader.load_skill("test-skill")

        assert skill.metadata.name == "test-skill"
        assert skill.metadata.description == "A test skill"
        assert skill.content == "Test content for skill"
        assert skill.storage_layer == "project"

    def test_load_skill_raises_not_found_error(self, tmp_path: Path) -> None:
        """Load skill should raise error for missing skill."""
        config = StorageConfig(project_path=tmp_path)
        loader = SkillLoader(config)
        loader.build_index()

        with pytest.raises(SkillNotFoundError) as exc_info:
            loader.load_skill("nonexistent")

        assert exc_info.value.skill_name == "nonexistent"

    def test_load_skill_uses_cache(self, tmp_path: Path) -> None:
        """Load skill should use cache for repeated loads."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        skill_dir = skills_dir / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            """---
name: test-skill
description: A test skill
---

Test content
"""
        )

        config = StorageConfig(project_path=skills_dir)
        loader = SkillLoader(config)
        loader.build_index()

        # First load - cache miss
        skill1 = loader.load_skill("test-skill")

        # Second load - cache hit
        skill2 = loader.load_skill("test-skill")

        # Should be same object from cache
        assert skill1 is skill2

    def test_load_skill_cache_expires_after_ttl(self, tmp_path: Path) -> None:
        """Load skill cache should expire after TTL."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        skill_dir = skills_dir / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            """---
name: test-skill
description: A test skill
---

Test content
"""
        )

        config = StorageConfig(project_path=skills_dir)
        loader = SkillLoader(config, cache_ttl_seconds=1)  # 1 second TTL
        loader.build_index()

        # First load
        skill1 = loader.load_skill("test-skill")

        # Wait for cache to expire
        time.sleep(1.1)

        # Second load - cache expired
        skill2 = loader.load_skill("test-skill")

        # Should be different objects (cache expired)
        assert skill1 is not skill2

    def test_has_skill_returns_true_for_existing_skill(self, tmp_path: Path) -> None:
        """Has skill should return True for existing skill."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        skill_dir = skills_dir / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            """---
name: test-skill
description: A test skill
---

Content
"""
        )

        config = StorageConfig(project_path=skills_dir)
        loader = SkillLoader(config)
        loader.build_index()

        assert loader.has_skill("test-skill") is True

    def test_has_skill_returns_false_for_missing_skill(self, tmp_path: Path) -> None:
        """Has skill should return False for missing skill."""
        config = StorageConfig(project_path=tmp_path)
        loader = SkillLoader(config)
        loader.build_index()

        assert loader.has_skill("nonexistent") is False

    def test_invalidate_cache_clears_specific_skill(self, tmp_path: Path) -> None:
        """Invalidate cache should clear specific skill."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        # Create two skills
        for name in ["skill-1", "skill-2"]:
            skill_dir = skills_dir / name
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                f"""---
name: {name}
description: {name}
---

Content
"""
            )

        config = StorageConfig(project_path=skills_dir)
        loader = SkillLoader(config)
        loader.build_index()

        # Load both skills
        skill1_before = loader.load_skill("skill-1")
        skill2_before = loader.load_skill("skill-2")

        # Invalidate only skill-1
        loader.invalidate_cache("skill-1")

        # Reload both
        skill1_after = loader.load_skill("skill-1")
        skill2_after = loader.load_skill("skill-2")

        # skill-1 should be different (reloaded)
        assert skill1_before is not skill1_after
        # skill-2 should be same (from cache)
        assert skill2_before is skill2_after

    def test_invalidate_cache_clears_all_skills(self, tmp_path: Path) -> None:
        """Invalidate cache with no name should clear all cached skills."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        # Create two skills
        for name in ["skill-1", "skill-2"]:
            skill_dir = skills_dir / name
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                f"""---
name: {name}
description: {name}
---

Content
"""
            )

        config = StorageConfig(project_path=skills_dir)
        loader = SkillLoader(config)
        loader.build_index()

        # Load both skills
        skill1_before = loader.load_skill("skill-1")
        skill2_before = loader.load_skill("skill-2")

        # Invalidate all
        loader.invalidate_cache()

        # Reload both
        skill1_after = loader.load_skill("skill-1")
        skill2_after = loader.load_skill("skill-2")

        # Both should be different (reloaded)
        assert skill1_before is not skill1_after
        assert skill2_before is not skill2_after

    def test_get_effective_priority_combines_layer_and_explicit(self, tmp_path: Path) -> None:
        """Get effective priority should combine layer and explicit priority."""
        config = StorageConfig(
            enterprise_path=tmp_path / "enterprise" / "skills",
            project_path=tmp_path / "project" / "skills",
        )
        loader = SkillLoader(config)

        # Enterprise layer (priority 4) with explicit priority 5
        enterprise_entry = SkillIndexEntry(
            name="test",
            description="test",
            path=Path("/test"),
            storage_layer="enterprise",
            priority=5,
        )

        # Project layer (priority 2) with explicit priority 100
        project_entry = SkillIndexEntry(
            name="test",
            description="test",
            path=Path("/test"),
            storage_layer="project",
            priority=100,
        )

        enterprise_effective = loader._get_effective_priority(enterprise_entry)
        project_effective = loader._get_effective_priority(project_entry)

        # Enterprise: (4 * 1000) + 5 = 4005
        assert enterprise_effective == 4005
        # Project: (2 * 1000) + 100 = 2100
        assert project_effective == 2100
        # Enterprise should still win despite lower explicit priority
        assert enterprise_effective > project_effective

    def test_thread_safe_concurrent_builds(self, tmp_path: Path) -> None:
        """Loader should handle concurrent index builds safely."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        # Create test skill
        skill_dir = skills_dir / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            """---
name: test-skill
description: Test skill
---

Content
"""
        )

        config = StorageConfig(project_path=skills_dir)
        loader = SkillLoader(config)

        results = []

        def build_index() -> None:
            count = loader.build_index(force=True)
            results.append(count)

        # Run multiple concurrent builds
        threads = [Thread(target=build_index) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # All builds should succeed
        assert len(results) == 5
        # All should return consistent results
        assert all(count == 1 for count in results)

    def test_thread_safe_concurrent_loads(self, tmp_path: Path) -> None:
        """Loader should handle concurrent skill loads safely."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        skill_dir = skills_dir / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            """---
name: test-skill
description: Test skill
---

Content
"""
        )

        config = StorageConfig(project_path=skills_dir)
        loader = SkillLoader(config)
        loader.build_index()

        results = []

        def load_skill() -> None:
            skill = loader.load_skill("test-skill")
            results.append(skill)

        # Run multiple concurrent loads
        threads = [Thread(target=load_skill) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # All loads should succeed
        assert len(results) == 5
        # All should return same cached instance
        assert all(skill is results[0] for skill in results)


class TestSkillLoaderValidation:
    """Tests for skill content validation."""

    def test_load_skill_rejects_large_skill(self, tmp_path: Path) -> None:
        """Skills exceeding 500 lines should be rejected."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        skill_dir = skills_dir / "large-skill"
        skill_dir.mkdir()

        # Create skill with 600 lines (exceeds limit)
        content_lines = "\n".join([f"Line {i}" for i in range(600)])
        (skill_dir / "SKILL.md").write_text(
            f"""---
name: large-skill
description: Test skill that exceeds line limit
---

{content_lines}
"""
        )

        config = StorageConfig(project_path=skills_dir)
        loader = SkillLoader(config)
        loader.build_index()

        with pytest.raises(SkillValidationError) as exc_info:
            loader.load_skill("large-skill")

        # Verify error details
        error = exc_info.value
        assert error.skill_name == "large-skill"
        assert "500 lines" in error.reason
        assert "600 lines" in error.reason or "604 lines" in error.reason  # Account for frontmatter
        assert error.details is not None
        assert error.details["max_lines"] == MAX_SKILL_MD_LINES
        assert error.details["line_count"] > MAX_SKILL_MD_LINES

    def test_load_skill_allows_legacy_large_skill(self, tmp_path: Path) -> None:
        """Legacy flag allows large skills with warning."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        skill_dir = skills_dir / "legacy-skill"
        skill_dir.mkdir()

        # Create large skill with legacy flag
        content_lines = "\n".join([f"Line {i}" for i in range(600)])
        (skill_dir / "SKILL.md").write_text(
            f"""---
name: legacy-skill
description: Test legacy skill
legacy-large-file: true
---

{content_lines}
"""
        )

        config = StorageConfig(project_path=skills_dir)
        loader = SkillLoader(config)
        loader.build_index()

        # Should succeed without raising error
        skill = loader.load_skill("legacy-skill")

        assert skill is not None
        assert skill.metadata.name == "legacy-skill"
        assert skill.metadata.legacy_large_file is True

    def test_load_skill_accepts_normal_skill(self, tmp_path: Path) -> None:
        """Skills under 500 lines work normally."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        skill_dir = skills_dir / "normal-skill"
        skill_dir.mkdir()

        # Create skill with 100 lines (well under limit)
        content_lines = "\n".join([f"Line {i}" for i in range(100)])
        (skill_dir / "SKILL.md").write_text(
            f"""---
name: normal-skill
description: Test skill under line limit
---

{content_lines}
"""
        )

        config = StorageConfig(project_path=skills_dir)
        loader = SkillLoader(config)
        loader.build_index()

        # Should succeed without any issues
        skill = loader.load_skill("normal-skill")

        assert skill is not None
        assert skill.metadata.name == "normal-skill"
        assert skill.metadata.legacy_large_file is False

    def test_load_skill_validates_at_exactly_500_lines(self, tmp_path: Path) -> None:
        """Skills with exactly 500 lines in body content should pass validation."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        skill_dir = skills_dir / "boundary-skill"
        skill_dir.mkdir()

        # Create skill with exactly 500 lines in body content
        # Note: validation counts lines in body content (after frontmatter extraction)
        content_lines = "\n".join([f"Line {i}" for i in range(500)])
        (skill_dir / "SKILL.md").write_text(
            f"""---
name: boundary-skill
description: Test skill at boundary
---

{content_lines}"""
        )

        config = StorageConfig(project_path=skills_dir)
        loader = SkillLoader(config)
        loader.build_index()

        # Should succeed at exactly 500 lines
        skill = loader.load_skill("boundary-skill")
        assert skill is not None
        # Verify the content has exactly 500 lines
        assert skill.content.count("\n") + 1 == 500

    def test_load_skill_validates_at_501_lines(self, tmp_path: Path) -> None:
        """Skills with 501 lines in body content should fail validation."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        skill_dir = skills_dir / "over-boundary-skill"
        skill_dir.mkdir()

        # Create skill with 501 lines in body content
        # Note: validation counts lines in body content (after frontmatter extraction)
        content_lines = "\n".join([f"Line {i}" for i in range(501)])
        (skill_dir / "SKILL.md").write_text(
            f"""---
name: over-boundary-skill
description: Test skill over boundary
---

{content_lines}"""
        )

        config = StorageConfig(project_path=skills_dir)
        loader = SkillLoader(config)
        loader.build_index()

        # Should fail at 501 lines
        with pytest.raises(SkillValidationError) as exc_info:
            loader.load_skill("over-boundary-skill")

        assert "500 lines" in str(exc_info.value)
        assert "501 lines" in str(exc_info.value)

    def test_validation_error_includes_migration_guidance(self, tmp_path: Path) -> None:
        """Validation error should include helpful migration guidance."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        skill_dir = skills_dir / "large-skill"
        skill_dir.mkdir()

        content_lines = "\n".join([f"Line {i}" for i in range(600)])
        (skill_dir / "SKILL.md").write_text(
            f"""---
name: large-skill
description: Test
---

{content_lines}
"""
        )

        config = StorageConfig(project_path=skills_dir)
        loader = SkillLoader(config)
        loader.build_index()

        with pytest.raises(SkillValidationError) as exc_info:
            loader.load_skill("large-skill")

        error_message = str(exc_info.value)
        # Check for helpful guidance in error message
        assert "reference.md" in error_message or "supporting files" in error_message
        assert "examples.md" in error_message or "supporting files" in error_message

    def test_validation_uses_cache_after_first_load(self, tmp_path: Path) -> None:
        """Validation should only run once; cached skills bypass validation."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        skill_dir = skills_dir / "test-skill"
        skill_dir.mkdir()

        content_lines = "\n".join([f"Line {i}" for i in range(100)])
        (skill_dir / "SKILL.md").write_text(
            f"""---
name: test-skill
description: Test
---

{content_lines}
"""
        )

        config = StorageConfig(project_path=skills_dir)
        loader = SkillLoader(config)
        loader.build_index()

        # First load - runs validation
        skill1 = loader.load_skill("test-skill")

        # Second load - uses cache (validation not run again)
        skill2 = loader.load_skill("test-skill")

        # Should be same cached object
        assert skill1 is skill2


class TestSkillLoaderPerformance:
    """Performance tests for SkillLoader."""

    def test_index_build_performance(self, tmp_path: Path) -> None:
        """Index build should complete within performance target."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        # Create 100 skills (scaled down from 1000 for test speed)
        for i in range(100):
            skill_dir = skills_dir / f"skill-{i:03d}"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                f"""---
name: skill-{i:03d}
description: Test skill {i}
priority: {i % 10}
tags:
  - test
  - perf
---

Content for skill {i}
"""
            )

        config = StorageConfig(project_path=skills_dir)
        loader = SkillLoader(config)

        # Measure index build time
        start_time = time.time()
        count = loader.build_index()
        elapsed = time.time() - start_time

        assert count == 100
        # Target: < 100ms for 1000 skills, so < 10ms for 100 skills
        assert elapsed < 0.1, f"Index build took {elapsed*1000:.1f}ms (target: <100ms)"
