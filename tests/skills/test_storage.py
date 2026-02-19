"""Tests for skill storage management.

This module tests the storage configuration and management system for the
4-layer skill hierarchy.
"""

from pathlib import Path

import pytest

from omniforge.skills.storage import SkillStorageManager, StorageConfig


class TestStorageConfig:
    """Tests for StorageConfig model."""

    def test_create_empty_config(self) -> None:
        """StorageConfig should initialize with all None/empty values."""
        config = StorageConfig()

        assert config.enterprise_path is None
        assert config.personal_path is None
        assert config.project_path is None
        assert config.plugin_paths == []

    def test_create_config_with_paths(self) -> None:
        """StorageConfig should accept path values."""
        enterprise = Path("/enterprise/skills")
        personal = Path("/personal/skills")
        project = Path("/project/skills")
        plugins = [Path("/plugin1"), Path("/plugin2")]

        config = StorageConfig(
            enterprise_path=enterprise,
            personal_path=personal,
            project_path=project,
            plugin_paths=plugins,
        )

        assert config.enterprise_path == enterprise
        assert config.personal_path == personal
        assert config.project_path == project
        assert config.plugin_paths == plugins

    def test_from_environment_without_project(self) -> None:
        """from_environment should create config with default paths when no project root."""
        config = StorageConfig.from_environment()

        home = Path.home()
        assert config.enterprise_path == home / ".omniforge" / "enterprise" / "skills"
        assert config.personal_path == home / ".omniforge" / "skills"
        assert config.project_path is None
        assert config.plugin_paths == []

    def test_from_environment_with_project(self, tmp_path: Path) -> None:
        """from_environment should include project path when project root provided."""
        project_root = tmp_path / "my-project"

        config = StorageConfig.from_environment(project_root=project_root)

        home = Path.home()
        assert config.enterprise_path == home / ".omniforge" / "enterprise" / "skills"
        assert config.personal_path == home / ".omniforge" / "skills"
        assert config.project_path == project_root / ".omniforge" / "skills"
        assert config.plugin_paths == []


class TestSkillStorageManager:
    """Tests for SkillStorageManager class."""

    def test_layer_order_constant(self) -> None:
        """LAYER_ORDER should define correct priority sequence."""
        assert SkillStorageManager.LAYER_ORDER == ["enterprise", "personal", "project", "plugin"]

    def test_get_layer_priority_enterprise(self) -> None:
        """get_layer_priority should return 4 for enterprise layer."""
        config = StorageConfig()
        manager = SkillStorageManager(config)

        assert manager.get_layer_priority("enterprise") == 4

    def test_get_layer_priority_personal(self) -> None:
        """get_layer_priority should return 3 for personal layer."""
        config = StorageConfig()
        manager = SkillStorageManager(config)

        assert manager.get_layer_priority("personal") == 3

    def test_get_layer_priority_project(self) -> None:
        """get_layer_priority should return 2 for project layer."""
        config = StorageConfig()
        manager = SkillStorageManager(config)

        assert manager.get_layer_priority("project") == 2

    def test_get_layer_priority_plugin(self) -> None:
        """get_layer_priority should return 1 for plugin layer."""
        config = StorageConfig()
        manager = SkillStorageManager(config)

        assert manager.get_layer_priority("plugin") == 1

    def test_get_layer_priority_invalid_layer(self) -> None:
        """get_layer_priority should raise ValueError for invalid layer."""
        config = StorageConfig()
        manager = SkillStorageManager(config)

        with pytest.raises(ValueError, match="Invalid layer 'invalid'"):
            manager.get_layer_priority("invalid")

    def test_get_all_skill_paths_empty_config(self) -> None:
        """get_all_skill_paths should return empty iterator with empty config."""
        config = StorageConfig()
        manager = SkillStorageManager(config)

        paths = list(manager.get_all_skill_paths())
        assert paths == []

    def test_get_all_skill_paths_nonexistent_directories(self, tmp_path: Path) -> None:
        """get_all_skill_paths should skip nonexistent directories without errors."""
        config = StorageConfig(
            enterprise_path=tmp_path / "nonexistent1",
            personal_path=tmp_path / "nonexistent2",
            project_path=tmp_path / "nonexistent3",
        )
        manager = SkillStorageManager(config)

        paths = list(manager.get_all_skill_paths())
        assert paths == []

    def test_get_all_skill_paths_single_layer(self, tmp_path: Path) -> None:
        """get_all_skill_paths should find skills in single configured layer."""
        enterprise_path = tmp_path / "enterprise"
        enterprise_path.mkdir()

        # Create skill directory with SKILL.md
        skill_dir = enterprise_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# My Skill")

        config = StorageConfig(enterprise_path=enterprise_path)
        manager = SkillStorageManager(config)

        paths = list(manager.get_all_skill_paths())
        assert len(paths) == 1
        assert paths[0][0] == "enterprise"
        assert paths[0][1] == skill_dir / "SKILL.md"

    def test_get_all_skill_paths_multiple_skills_same_layer(self, tmp_path: Path) -> None:
        """get_all_skill_paths should find multiple skills in same layer."""
        personal_path = tmp_path / "personal"
        personal_path.mkdir()

        # Create multiple skill directories
        skill1 = personal_path / "skill-one"
        skill1.mkdir()
        (skill1 / "SKILL.md").write_text("# Skill One")

        skill2 = personal_path / "skill-two"
        skill2.mkdir()
        (skill2 / "SKILL.md").write_text("# Skill Two")

        config = StorageConfig(personal_path=personal_path)
        manager = SkillStorageManager(config)

        paths = list(manager.get_all_skill_paths())
        assert len(paths) == 2

        layers = [layer for layer, _ in paths]
        assert all(layer == "personal" for layer in layers)

        skill_names = {path.parent.name for _, path in paths}
        assert skill_names == {"skill-one", "skill-two"}

    def test_get_all_skill_paths_all_layers(self, tmp_path: Path) -> None:
        """get_all_skill_paths should find skills across all layers in priority order."""
        # Create all layer directories
        enterprise_path = tmp_path / "enterprise"
        personal_path = tmp_path / "personal"
        project_path = tmp_path / "project"
        plugin_path = tmp_path / "plugin"

        for path in [enterprise_path, personal_path, project_path, plugin_path]:
            path.mkdir()

        # Create one skill per layer
        for base_path, skill_name in [
            (enterprise_path, "enterprise-skill"),
            (personal_path, "personal-skill"),
            (project_path, "project-skill"),
            (plugin_path, "plugin-skill"),
        ]:
            skill_dir = base_path / skill_name
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(f"# {skill_name}")

        config = StorageConfig(
            enterprise_path=enterprise_path,
            personal_path=personal_path,
            project_path=project_path,
            plugin_paths=[plugin_path],
        )
        manager = SkillStorageManager(config)

        paths = list(manager.get_all_skill_paths())
        assert len(paths) == 4

        # Verify priority order
        layers = [layer for layer, _ in paths]
        assert layers == ["enterprise", "personal", "project", "plugin"]

    def test_get_all_skill_paths_multiple_plugin_paths(self, tmp_path: Path) -> None:
        """get_all_skill_paths should scan all plugin paths."""
        plugin1 = tmp_path / "plugin1"
        plugin2 = tmp_path / "plugin2"

        for path in [plugin1, plugin2]:
            path.mkdir()

        # Create skills in each plugin directory
        skill1 = plugin1 / "plugin-skill-1"
        skill1.mkdir()
        (skill1 / "SKILL.md").write_text("# Plugin Skill 1")

        skill2 = plugin2 / "plugin-skill-2"
        skill2.mkdir()
        (skill2 / "SKILL.md").write_text("# Plugin Skill 2")

        config = StorageConfig(plugin_paths=[plugin1, plugin2])
        manager = SkillStorageManager(config)

        paths = list(manager.get_all_skill_paths())
        assert len(paths) == 2

        layers = [layer for layer, _ in paths]
        assert all(layer == "plugin" for layer in layers)

        skill_names = {path.parent.name for _, path in paths}
        assert skill_names == {"plugin-skill-1", "plugin-skill-2"}

    def test_get_all_skill_paths_skips_directories_without_skill_md(self, tmp_path: Path) -> None:
        """get_all_skill_paths should skip directories without SKILL.md."""
        personal_path = tmp_path / "personal"
        personal_path.mkdir()

        # Create directory without SKILL.md
        empty_dir = personal_path / "empty-skill"
        empty_dir.mkdir()

        # Create directory with SKILL.md
        valid_dir = personal_path / "valid-skill"
        valid_dir.mkdir()
        (valid_dir / "SKILL.md").write_text("# Valid Skill")

        config = StorageConfig(personal_path=personal_path)
        manager = SkillStorageManager(config)

        paths = list(manager.get_all_skill_paths())
        assert len(paths) == 1
        assert paths[0][1] == valid_dir / "SKILL.md"

    def test_get_all_skill_paths_skips_files_in_base_directory(self, tmp_path: Path) -> None:
        """get_all_skill_paths should ignore files in base directory."""
        personal_path = tmp_path / "personal"
        personal_path.mkdir()

        # Create SKILL.md in base directory (should be ignored)
        (personal_path / "SKILL.md").write_text("# Base Skill")

        # Create valid skill directory
        valid_dir = personal_path / "valid-skill"
        valid_dir.mkdir()
        (valid_dir / "SKILL.md").write_text("# Valid Skill")

        config = StorageConfig(personal_path=personal_path)
        manager = SkillStorageManager(config)

        paths = list(manager.get_all_skill_paths())
        assert len(paths) == 1
        assert paths[0][1] == valid_dir / "SKILL.md"

    def test_get_all_skill_paths_not_recursive(self, tmp_path: Path) -> None:
        """get_all_skill_paths should only scan immediate subdirectories."""
        personal_path = tmp_path / "personal"
        personal_path.mkdir()

        # Create nested skill (should be ignored)
        nested_dir = personal_path / "category" / "nested-skill"
        nested_dir.mkdir(parents=True)
        (nested_dir / "SKILL.md").write_text("# Nested Skill")

        # Create immediate skill (should be found)
        immediate_dir = personal_path / "immediate-skill"
        immediate_dir.mkdir()
        (immediate_dir / "SKILL.md").write_text("# Immediate Skill")

        config = StorageConfig(personal_path=personal_path)
        manager = SkillStorageManager(config)

        paths = list(manager.get_all_skill_paths())
        assert len(paths) == 1
        assert paths[0][1] == immediate_dir / "SKILL.md"

    def test_scan_directory_with_mixed_content(self, tmp_path: Path) -> None:
        """_scan_directory should handle directories with mixed content."""
        base_path = tmp_path / "mixed"
        base_path.mkdir()

        # Create various types of content
        # Valid skill directory
        valid_skill = base_path / "valid-skill"
        valid_skill.mkdir()
        (valid_skill / "SKILL.md").write_text("# Valid")

        # Directory without SKILL.md
        no_skill = base_path / "no-skill"
        no_skill.mkdir()

        # Regular file
        (base_path / "readme.txt").write_text("readme")

        # Directory with other files
        other_files = base_path / "other-files"
        other_files.mkdir()
        (other_files / "other.md").write_text("# Other")

        config = StorageConfig(personal_path=base_path)
        manager = SkillStorageManager(config)

        paths = list(manager.get_all_skill_paths())
        assert len(paths) == 1
        assert paths[0][1] == valid_skill / "SKILL.md"
