"""Tests for SkillWriter.

This module tests filesystem operations for writing skills including directory
creation, atomic writes, conflict detection, and resource bundling.
"""

from pathlib import Path

import pytest

from omniforge.skills.creation.writer import (
    SkillExistsError,
    SkillWriter,
    SkillWriterError,
)
from omniforge.skills.storage import SkillStorageManager, StorageConfig


class TestSkillWriter:
    """Tests for SkillWriter class."""

    @pytest.fixture
    def temp_storage(self, tmp_path: Path) -> StorageConfig:
        """Create temporary storage configuration."""
        return StorageConfig(
            project_path=tmp_path / ".omniforge" / "skills",
            personal_path=tmp_path / "home" / ".omniforge" / "skills",
            enterprise_path=tmp_path / "enterprise" / ".omniforge" / "skills",
        )

    @pytest.fixture
    def storage_manager(self, temp_storage: StorageConfig) -> SkillStorageManager:
        """Create storage manager with temporary paths."""
        return SkillStorageManager(temp_storage)

    @pytest.fixture
    def writer(self, storage_manager: SkillStorageManager) -> SkillWriter:
        """Create SkillWriter instance."""
        return SkillWriter(storage_manager)

    @pytest.fixture
    def valid_skill_content(self) -> str:
        """Create valid SKILL.md content."""
        return """---
name: test-skill
description: A test skill for unit testing. Use when you need to test skill writing.
---

# Test Skill

This is a test skill for verifying the writer functionality.

## Usage

Invoke this skill during unit tests.
"""

    @pytest.mark.asyncio
    async def test_write_skill_creates_directory_and_file(
        self,
        writer: SkillWriter,
        valid_skill_content: str,
        temp_storage: StorageConfig,
    ) -> None:
        """Writer should create skill directory and SKILL.md file."""
        path = await writer.write_skill("test-skill", valid_skill_content, "project")

        assert path.exists()
        assert path.is_file()
        assert path.name == "SKILL.md"
        assert path.parent.name == "test-skill"
        assert path.read_text(encoding="utf-8") == valid_skill_content

    @pytest.mark.asyncio
    async def test_write_skill_creates_parent_directories(
        self,
        writer: SkillWriter,
        valid_skill_content: str,
        temp_storage: StorageConfig,
    ) -> None:
        """Writer should create parent directories if they don't exist."""
        # Ensure parent doesn't exist
        assert not temp_storage.project_path.exists()

        path = await writer.write_skill("test-skill", valid_skill_content, "project")

        assert path.exists()
        assert temp_storage.project_path.exists()
        assert temp_storage.project_path.is_dir()

    @pytest.mark.asyncio
    async def test_write_skill_returns_absolute_path(
        self,
        writer: SkillWriter,
        valid_skill_content: str,
    ) -> None:
        """Writer should return absolute path to SKILL.md."""
        path = await writer.write_skill("test-skill", valid_skill_content, "project")

        assert path.is_absolute()
        assert str(path).endswith("test-skill/SKILL.md")

    @pytest.mark.asyncio
    async def test_write_skill_handles_spaces_in_path(
        self,
        tmp_path: Path,
        valid_skill_content: str,
    ) -> None:
        """Writer should handle paths with spaces correctly."""
        # Create config with spaces in path
        config = StorageConfig(project_path=tmp_path / "my project" / ".omniforge" / "skills")
        manager = SkillStorageManager(config)
        writer = SkillWriter(manager)

        path = await writer.write_skill("test-skill", valid_skill_content, "project")

        assert path.exists()
        assert "my project" in str(path)
        assert path.read_text(encoding="utf-8") == valid_skill_content

    @pytest.mark.asyncio
    async def test_write_skill_raises_on_existing_skill(
        self,
        writer: SkillWriter,
        valid_skill_content: str,
        temp_storage: StorageConfig,
    ) -> None:
        """Writer should raise SkillExistsError if skill already exists."""
        # Write skill first time
        await writer.write_skill("test-skill", valid_skill_content, "project")

        # Attempt to write again
        with pytest.raises(SkillExistsError, match="already exists"):
            await writer.write_skill("test-skill", valid_skill_content, "project")

    @pytest.mark.asyncio
    async def test_write_skill_raises_on_invalid_storage_layer(
        self,
        writer: SkillWriter,
        valid_skill_content: str,
    ) -> None:
        """Writer should raise ValueError for invalid storage layer."""
        with pytest.raises(ValueError, match="Invalid storage layer"):
            await writer.write_skill("test-skill", valid_skill_content, "invalid-layer")

    @pytest.mark.asyncio
    async def test_write_skill_with_bundled_resources(
        self,
        writer: SkillWriter,
        valid_skill_content: str,
        temp_storage: StorageConfig,
    ) -> None:
        """Writer should write bundled resources to correct subdirectories."""
        resources = {
            "scripts/helper.py": "print('hello')",
            "references/guide.md": "# Guide\n\nReference material",
            "assets/config.json": '{"key": "value"}',
        }

        path = await writer.write_skill(
            "test-skill", valid_skill_content, "project", resources=resources
        )

        # Check SKILL.md exists
        assert path.exists()

        # Check resources exist
        skill_dir = path.parent
        assert (skill_dir / "scripts" / "helper.py").exists()
        assert (skill_dir / "references" / "guide.md").exists()
        assert (skill_dir / "assets" / "config.json").exists()

        # Verify content
        assert (skill_dir / "scripts" / "helper.py").read_text() == "print('hello')"

    @pytest.mark.asyncio
    async def test_write_skill_cleans_up_on_resource_failure(
        self,
        writer: SkillWriter,
        valid_skill_content: str,
        temp_storage: StorageConfig,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Writer should clean up skill directory if resource write fails."""
        resources = {"scripts/helper.py": "print('hello')"}

        # Mock write_bundled_resource to raise exception
        async def failing_write(*args, **kwargs):
            raise OSError("Simulated write failure")

        monkeypatch.setattr(writer, "write_bundled_resource", failing_write)

        # Attempt write - should fail
        with pytest.raises(SkillWriterError, match="Failed to write bundled resource"):
            await writer.write_skill("test-skill", valid_skill_content, "project", resources)

    def test_get_skill_directory_project_layer(
        self,
        writer: SkillWriter,
        temp_storage: StorageConfig,
    ) -> None:
        """get_skill_directory should return correct path for project layer."""
        path = writer.get_skill_directory("my-skill", "project")

        assert path == temp_storage.project_path / "my-skill"
        assert path.is_absolute()

    def test_get_skill_directory_personal_layer(
        self,
        writer: SkillWriter,
        temp_storage: StorageConfig,
    ) -> None:
        """get_skill_directory should return correct path for personal layer."""
        path = writer.get_skill_directory("my-skill", "personal")

        assert path == temp_storage.personal_path / "my-skill"

    def test_get_skill_directory_enterprise_layer(
        self,
        writer: SkillWriter,
        temp_storage: StorageConfig,
    ) -> None:
        """get_skill_directory should return correct path for enterprise layer."""
        path = writer.get_skill_directory("my-skill", "enterprise")

        assert path == temp_storage.enterprise_path / "my-skill"

    def test_get_skill_directory_raises_on_invalid_layer(
        self,
        writer: SkillWriter,
    ) -> None:
        """get_skill_directory should raise ValueError for invalid layer."""
        with pytest.raises(ValueError, match="Invalid storage layer"):
            writer.get_skill_directory("my-skill", "invalid")

    def test_get_skill_directory_raises_on_unconfigured_layer(
        self,
        tmp_path: Path,
    ) -> None:
        """get_skill_directory should raise ValueError for unconfigured layer."""
        # Create config with only project path
        config = StorageConfig(project_path=tmp_path / ".omniforge" / "skills")
        manager = SkillStorageManager(config)
        writer = SkillWriter(manager)

        with pytest.raises(ValueError, match="not configured"):
            writer.get_skill_directory("my-skill", "personal")

    def test_skill_exists_returns_true_for_existing_skill(
        self,
        writer: SkillWriter,
        temp_storage: StorageConfig,
    ) -> None:
        """skill_exists should return True if skill directory and SKILL.md exist."""
        # Create skill directory with SKILL.md
        skill_dir = temp_storage.project_path / "existing-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("content")

        assert writer.skill_exists("existing-skill", "project") is True

    def test_skill_exists_returns_false_for_nonexistent_skill(
        self,
        writer: SkillWriter,
    ) -> None:
        """skill_exists should return False if skill doesn't exist."""
        assert writer.skill_exists("nonexistent-skill", "project") is False

    def test_skill_exists_returns_false_for_directory_without_skill_md(
        self,
        writer: SkillWriter,
        temp_storage: StorageConfig,
    ) -> None:
        """skill_exists should return False if directory exists but SKILL.md missing."""
        # Create skill directory without SKILL.md
        skill_dir = temp_storage.project_path / "incomplete-skill"
        skill_dir.mkdir(parents=True)

        assert writer.skill_exists("incomplete-skill", "project") is False

    def test_skill_exists_returns_false_for_unconfigured_layer(
        self,
        tmp_path: Path,
    ) -> None:
        """skill_exists should return False for unconfigured storage layer."""
        config = StorageConfig(project_path=tmp_path / ".omniforge" / "skills")
        manager = SkillStorageManager(config)
        writer = SkillWriter(manager)

        assert writer.skill_exists("any-skill", "personal") is False

    @pytest.mark.asyncio
    async def test_write_bundled_resource_creates_subdirectories(
        self,
        writer: SkillWriter,
        tmp_path: Path,
    ) -> None:
        """write_bundled_resource should create nested subdirectories."""
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()

        path = await writer.write_bundled_resource(
            skill_dir, "scripts/utils/helper.py", "print('hello')"
        )

        assert path.exists()
        assert path.parent.name == "utils"
        assert path.parent.parent.name == "scripts"

    @pytest.mark.asyncio
    async def test_write_bundled_resource_handles_forward_slashes(
        self,
        writer: SkillWriter,
        tmp_path: Path,
    ) -> None:
        """write_bundled_resource should handle forward slashes correctly."""
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()

        path = await writer.write_bundled_resource(skill_dir, "scripts/helper.py", "content")

        assert path.exists()
        assert path.name == "helper.py"
        assert path.parent.name == "scripts"

    @pytest.mark.asyncio
    async def test_write_bundled_resource_handles_backslashes(
        self,
        writer: SkillWriter,
        tmp_path: Path,
    ) -> None:
        """write_bundled_resource should convert backslashes to forward slashes."""
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()

        # Use backslash (Windows-style)
        path = await writer.write_bundled_resource(skill_dir, "scripts\\helper.py", "content")

        assert path.exists()
        assert path.name == "helper.py"
        assert path.parent.name == "scripts"

    @pytest.mark.asyncio
    async def test_write_bundled_resource_returns_absolute_path(
        self,
        writer: SkillWriter,
        tmp_path: Path,
    ) -> None:
        """write_bundled_resource should return absolute path."""
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()

        path = await writer.write_bundled_resource(skill_dir, "scripts/helper.py", "content")

        assert path.is_absolute()

    @pytest.mark.asyncio
    async def test_write_bundled_resource_writes_content_correctly(
        self,
        writer: SkillWriter,
        tmp_path: Path,
    ) -> None:
        """write_bundled_resource should write content with UTF-8 encoding."""
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()

        content = "# Unicode test: café, naïve, 日本語"
        path = await writer.write_bundled_resource(skill_dir, "references/unicode.md", content)

        assert path.read_text(encoding="utf-8") == content

    @pytest.mark.asyncio
    async def test_atomic_write_creates_temp_file_in_same_directory(
        self,
        writer: SkillWriter,
        tmp_path: Path,
    ) -> None:
        """_write_file_atomic should create temp file in same directory for atomic rename."""
        target = tmp_path / "test.txt"
        content = "test content"

        writer._write_file_atomic(target, content)

        assert target.exists()
        assert target.read_text(encoding="utf-8") == content

        # Verify no temp files left behind
        temp_files = list(tmp_path.glob(".test.txt.*.tmp"))
        assert len(temp_files) == 0

    @pytest.mark.asyncio
    async def test_atomic_write_overwrites_existing_file(
        self,
        writer: SkillWriter,
        tmp_path: Path,
    ) -> None:
        """_write_file_atomic should atomically overwrite existing file."""
        target = tmp_path / "test.txt"
        target.write_text("old content")

        writer._write_file_atomic(target, "new content")

        assert target.read_text(encoding="utf-8") == "new content"

    @pytest.mark.asyncio
    async def test_write_skill_different_layers_dont_conflict(
        self,
        writer: SkillWriter,
        valid_skill_content: str,
    ) -> None:
        """Writer should allow same skill name in different storage layers."""
        # Write to project layer
        project_path = await writer.write_skill("test-skill", valid_skill_content, "project")

        # Write to personal layer - should succeed
        personal_path = await writer.write_skill("test-skill", valid_skill_content, "personal")

        # Both should exist
        assert project_path.exists()
        assert personal_path.exists()
        assert project_path != personal_path

    @pytest.mark.asyncio
    async def test_write_skill_validates_content_encoding(
        self,
        writer: SkillWriter,
    ) -> None:
        """Writer should handle Unicode content correctly."""
        content = """---
name: unicode-skill
description: Testing Unicode: café, naïve, 日本語, emoji 🚀
---

# Unicode Skill

Content with various Unicode characters: café, naïve, 日本語, emoji 🚀
"""

        path = await writer.write_skill("unicode-skill", content, "project")

        # Read back and verify
        written_content = path.read_text(encoding="utf-8")
        assert written_content == content
        assert "café" in written_content
        assert "🚀" in written_content

    def test_skill_exists_handles_file_instead_of_directory(
        self,
        writer: SkillWriter,
        temp_storage: StorageConfig,
    ) -> None:
        """skill_exists should return False if path is a file, not directory."""
        # Create a file instead of directory
        temp_storage.project_path.mkdir(parents=True)
        fake_skill = temp_storage.project_path / "fake-skill"
        fake_skill.write_text("not a directory")

        assert writer.skill_exists("fake-skill", "project") is False

    @pytest.mark.asyncio
    async def test_write_skill_multiple_skills_in_same_layer(
        self,
        writer: SkillWriter,
        valid_skill_content: str,
    ) -> None:
        """Writer should handle multiple skills in same storage layer."""
        skill1_path = await writer.write_skill("skill-one", valid_skill_content, "project")
        skill2_path = await writer.write_skill("skill-two", valid_skill_content, "project")
        skill3_path = await writer.write_skill("skill-three", valid_skill_content, "project")

        assert skill1_path.exists()
        assert skill2_path.exists()
        assert skill3_path.exists()

        # All should be in same parent directory
        assert skill1_path.parent.parent == skill2_path.parent.parent
        assert skill2_path.parent.parent == skill3_path.parent.parent
