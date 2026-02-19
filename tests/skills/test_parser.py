"""Tests for skill parser module."""

from pathlib import Path

import pytest

from omniforge.skills.errors import SkillParseError
from omniforge.skills.models import Skill, SkillIndexEntry
from omniforge.skills.parser import SkillParser


class TestSkillParser:
    """Tests for SkillParser class."""

    @pytest.fixture
    def parser(self) -> SkillParser:
        """Create a SkillParser instance."""
        return SkillParser()

    @pytest.fixture
    def temp_skill_dir(self, tmp_path: Path) -> Path:
        """Create a temporary skill directory structure."""
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        return skill_dir

    def test_parse_metadata_valid_skill(self, parser: SkillParser, temp_skill_dir: Path) -> None:
        """Should parse valid skill metadata successfully."""
        skill_file = temp_skill_dir / "SKILL.md"
        skill_file.write_text(
            """---
name: test-skill
description: A test skill
tags:
  - testing
  - example
priority: 10
---

# Test Skill

This is the skill content.
""",
            encoding="utf-8",
        )

        entry = parser.parse_metadata(skill_file, "global")

        assert isinstance(entry, SkillIndexEntry)
        assert entry.name == "test-skill"
        assert entry.description == "A test skill"
        assert entry.storage_layer == "global"
        assert entry.tags == ["testing", "example"]
        assert entry.priority == 10
        assert entry.path == skill_file.resolve()

    def test_parse_metadata_minimal_skill(self, parser: SkillParser, temp_skill_dir: Path) -> None:
        """Should parse skill with only required fields."""
        skill_file = temp_skill_dir / "SKILL.md"
        skill_file.write_text(
            """---
name: minimal-skill
description: Minimal skill
---

Content here.
""",
            encoding="utf-8",
        )

        entry = parser.parse_metadata(skill_file, "tenant-123")

        assert entry.name == "minimal-skill"
        assert entry.description == "Minimal skill"
        assert entry.storage_layer == "tenant-123"
        assert entry.tags is None
        assert entry.priority == 0

    def test_parse_metadata_missing_frontmatter(
        self, parser: SkillParser, temp_skill_dir: Path
    ) -> None:
        """Should raise error when frontmatter is missing."""
        skill_file = temp_skill_dir / "SKILL.md"
        skill_file.write_text("Just some content without frontmatter", encoding="utf-8")

        with pytest.raises(SkillParseError, match="Missing YAML frontmatter.*'---' delimiter"):
            parser.parse_metadata(skill_file, "global")

    def test_parse_metadata_invalid_yaml(self, parser: SkillParser, temp_skill_dir: Path) -> None:
        """Should raise error with line number for invalid YAML."""
        skill_file = temp_skill_dir / "SKILL.md"
        skill_file.write_text(
            """---
name: test-skill
description: "Unclosed quote
tags: [test]
---

Content
""",
            encoding="utf-8",
        )

        with pytest.raises(SkillParseError, match="Invalid YAML frontmatter"):
            parser.parse_metadata(skill_file, "global")

    def test_parse_metadata_missing_required_field(
        self, parser: SkillParser, temp_skill_dir: Path
    ) -> None:
        """Should raise error when required field is missing."""
        skill_file = temp_skill_dir / "SKILL.md"
        skill_file.write_text(
            """---
name: test-skill
---

Content
""",
            encoding="utf-8",
        )

        with pytest.raises(SkillParseError, match="Invalid metadata format"):
            parser.parse_metadata(skill_file, "global")

    def test_parse_metadata_invalid_name_format(
        self, parser: SkillParser, temp_skill_dir: Path
    ) -> None:
        """Should raise error for invalid skill name format."""
        skill_file = temp_skill_dir / "SKILL.md"
        skill_file.write_text(
            """---
name: InvalidName
description: Test
---

Content
""",
            encoding="utf-8",
        )

        with pytest.raises(SkillParseError, match="Invalid metadata format"):
            parser.parse_metadata(skill_file, "global")

    def test_parse_metadata_file_not_found(self, parser: SkillParser) -> None:
        """Should raise error for non-existent file."""
        non_existent = Path("/non/existent/SKILL.md")

        with pytest.raises(SkillParseError, match="File not found"):
            parser.parse_metadata(non_existent, "global")

    def test_parse_metadata_empty_file(self, parser: SkillParser, temp_skill_dir: Path) -> None:
        """Should raise error for empty file."""
        skill_file = temp_skill_dir / "SKILL.md"
        skill_file.write_text("", encoding="utf-8")

        with pytest.raises(SkillParseError, match="Missing YAML frontmatter"):
            parser.parse_metadata(skill_file, "global")

    def test_parse_full_valid_skill(self, parser: SkillParser, temp_skill_dir: Path) -> None:
        """Should parse complete skill with content."""
        skill_file = temp_skill_dir / "SKILL.md"
        content = """# Test Skill

This is the instruction content for the skill.

It can contain multiple paragraphs."""

        skill_file.write_text(
            f"""---
name: full-test-skill
description: Full test skill
allowed-tools:
  - tool1
  - tool2
model: gpt-4
priority: 5
---

{content}
""",
            encoding="utf-8",
        )

        skill = parser.parse_full(skill_file, "global")

        assert isinstance(skill, Skill)
        assert skill.metadata.name == "full-test-skill"
        assert skill.metadata.description == "Full test skill"
        assert skill.metadata.allowed_tools == ["tool1", "tool2"]
        assert skill.metadata.model == "gpt-4"
        assert skill.metadata.priority == 5
        assert skill.content == content.strip()
        assert skill.path == skill_file.resolve()
        assert skill.base_path == temp_skill_dir.resolve()
        assert skill.storage_layer == "global"

    def test_parse_full_with_hooks(self, parser: SkillParser, temp_skill_dir: Path) -> None:
        """Should parse skill with hook scripts."""
        skill_file = temp_skill_dir / "SKILL.md"

        # Create hook scripts
        scripts_dir = temp_skill_dir / "scripts"
        scripts_dir.mkdir()
        pre_hook = scripts_dir / "pre.sh"
        post_hook = scripts_dir / "post.py"
        pre_hook.write_text("#!/bin/bash\necho 'pre'", encoding="utf-8")
        post_hook.write_text("print('post')", encoding="utf-8")

        skill_file.write_text(
            """---
name: hook-skill
description: Skill with hooks
hooks:
  pre: scripts/pre.sh
  post: scripts/post.py
---

Content
""",
            encoding="utf-8",
        )

        skill = parser.parse_full(skill_file, "global")

        assert skill.metadata.hooks is not None
        assert skill.metadata.hooks.pre == "scripts/pre.sh"
        assert skill.metadata.hooks.post == "scripts/post.py"
        assert skill.script_paths is not None
        assert "pre" in skill.script_paths
        assert "post" in skill.script_paths
        assert skill.script_paths["pre"] == pre_hook.resolve()
        assert skill.script_paths["post"] == post_hook.resolve()

    def test_parse_full_detect_scripts_in_scripts_dir(
        self, parser: SkillParser, temp_skill_dir: Path
    ) -> None:
        """Should auto-detect script files in scripts/ directory."""
        skill_file = temp_skill_dir / "SKILL.md"
        skill_file.write_text(
            """---
name: auto-detect-skill
description: Skill with auto-detected scripts
---

Content
""",
            encoding="utf-8",
        )

        # Create scripts without hooks definition
        scripts_dir = temp_skill_dir / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "helper.py").write_text("# helper", encoding="utf-8")
        (scripts_dir / "setup.sh").write_text("#!/bin/bash", encoding="utf-8")

        skill = parser.parse_full(skill_file, "global")

        assert skill.script_paths is not None
        assert len(skill.script_paths) == 2

    def test_parse_full_detect_scripts_in_bin_dir(
        self, parser: SkillParser, temp_skill_dir: Path
    ) -> None:
        """Should auto-detect script files in bin/ directory."""
        skill_file = temp_skill_dir / "SKILL.md"
        skill_file.write_text(
            """---
name: bin-skill
description: Skill with bin scripts
---

Content
""",
            encoding="utf-8",
        )

        bin_dir = temp_skill_dir / "bin"
        bin_dir.mkdir()
        (bin_dir / "execute.rb").write_text("# ruby script", encoding="utf-8")

        skill = parser.parse_full(skill_file, "global")

        assert skill.script_paths is not None
        assert len(skill.script_paths) == 1

    def test_parse_full_detect_scripts_in_tools_dir(
        self, parser: SkillParser, temp_skill_dir: Path
    ) -> None:
        """Should auto-detect script files in tools/ directory."""
        skill_file = temp_skill_dir / "SKILL.md"
        skill_file.write_text(
            """---
name: tools-skill
description: Skill with tools scripts
---

Content
""",
            encoding="utf-8",
        )

        tools_dir = temp_skill_dir / "tools"
        tools_dir.mkdir()
        (tools_dir / "process.js").write_text("// javascript", encoding="utf-8")
        (tools_dir / "analyze.ts").write_text("// typescript", encoding="utf-8")

        skill = parser.parse_full(skill_file, "global")

        assert skill.script_paths is not None
        assert len(skill.script_paths) == 2

    def test_parse_full_detect_nested_scripts(
        self, parser: SkillParser, temp_skill_dir: Path
    ) -> None:
        """Should detect scripts in nested directories."""
        skill_file = temp_skill_dir / "SKILL.md"
        skill_file.write_text(
            """---
name: nested-skill
description: Skill with nested scripts
---

Content
""",
            encoding="utf-8",
        )

        # Create nested structure
        nested_dir = temp_skill_dir / "scripts" / "utils" / "deep"
        nested_dir.mkdir(parents=True)
        (nested_dir / "nested.py").write_text("# nested", encoding="utf-8")

        skill = parser.parse_full(skill_file, "global")

        assert skill.script_paths is not None
        assert len(skill.script_paths) == 1

    def test_parse_full_ignores_non_script_files(
        self, parser: SkillParser, temp_skill_dir: Path
    ) -> None:
        """Should ignore files without script extensions."""
        skill_file = temp_skill_dir / "SKILL.md"
        skill_file.write_text(
            """---
name: filter-skill
description: Skill with mixed files
---

Content
""",
            encoding="utf-8",
        )

        scripts_dir = temp_skill_dir / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "script.py").write_text("# script", encoding="utf-8")
        (scripts_dir / "readme.txt").write_text("not a script", encoding="utf-8")
        (scripts_dir / "config.json").write_text("{}", encoding="utf-8")
        (scripts_dir / "data.csv").write_text("col1,col2", encoding="utf-8")

        skill = parser.parse_full(skill_file, "global")

        assert skill.script_paths is not None
        assert len(skill.script_paths) == 1

    def test_parse_full_all_script_extensions(
        self, parser: SkillParser, temp_skill_dir: Path
    ) -> None:
        """Should detect all supported script extensions."""
        skill_file = temp_skill_dir / "SKILL.md"
        skill_file.write_text(
            """---
name: all-extensions-skill
description: Skill with all script types
---

Content
""",
            encoding="utf-8",
        )

        scripts_dir = temp_skill_dir / "scripts"
        scripts_dir.mkdir()

        # Create files with all supported extensions
        extensions = [".sh", ".py", ".rb", ".js", ".ts", ".pl"]
        for ext in extensions:
            (scripts_dir / f"script{ext}").write_text(f"# {ext}", encoding="utf-8")

        skill = parser.parse_full(skill_file, "global")

        assert skill.script_paths is not None
        assert len(skill.script_paths) == 6

    def test_parse_full_no_scripts(self, parser: SkillParser, temp_skill_dir: Path) -> None:
        """Should handle skills without any scripts."""
        skill_file = temp_skill_dir / "SKILL.md"
        skill_file.write_text(
            """---
name: no-scripts-skill
description: Skill without scripts
---

Content
""",
            encoding="utf-8",
        )

        skill = parser.parse_full(skill_file, "global")

        assert skill.script_paths is None or len(skill.script_paths) == 0

    def test_parse_full_hooks_not_found(self, parser: SkillParser, temp_skill_dir: Path) -> None:
        """Should handle missing hook script files gracefully."""
        skill_file = temp_skill_dir / "SKILL.md"
        skill_file.write_text(
            """---
name: missing-hooks-skill
description: Skill with missing hook files
hooks:
  pre: scripts/missing.sh
  post: scripts/also-missing.py
---

Content
""",
            encoding="utf-8",
        )

        skill = parser.parse_full(skill_file, "global")

        # Should still parse, but script_paths will be empty
        assert skill.metadata.hooks is not None
        assert skill.script_paths is None or len(skill.script_paths) == 0

    def test_parse_full_with_context_mode(self, parser: SkillParser, temp_skill_dir: Path) -> None:
        """Should parse skill with context mode setting."""
        skill_file = temp_skill_dir / "SKILL.md"
        skill_file.write_text(
            """---
name: context-skill
description: Skill with context mode
context: fork
---

Content
""",
            encoding="utf-8",
        )

        skill = parser.parse_full(skill_file, "global")

        assert skill.metadata.context.value == "fork"

    def test_parse_full_with_scope(self, parser: SkillParser, temp_skill_dir: Path) -> None:
        """Should parse skill with scope restrictions."""
        skill_file = temp_skill_dir / "SKILL.md"
        skill_file.write_text(
            """---
name: scoped-skill
description: Skill with scope
scope:
  agents:
    - agent-1
    - agent-2
  tenants:
    - tenant-123
  environments:
    - production
---

Content
""",
            encoding="utf-8",
        )

        skill = parser.parse_full(skill_file, "global")

        assert skill.metadata.scope is not None
        assert skill.metadata.scope.agents == ["agent-1", "agent-2"]
        assert skill.metadata.scope.tenants == ["tenant-123"]
        assert skill.metadata.scope.environments == ["production"]

    def test_parse_full_unicode_content(self, parser: SkillParser, temp_skill_dir: Path) -> None:
        """Should handle unicode content correctly."""
        skill_file = temp_skill_dir / "SKILL.md"
        unicode_content = "Unicode: 你好 🚀 café"
        skill_file.write_text(
            f"""---
name: unicode-skill
description: Skill with unicode
---

{unicode_content}
""",
            encoding="utf-8",
        )

        skill = parser.parse_full(skill_file, "global")

        assert unicode_content in skill.content

    def test_frontmatter_pattern(self) -> None:
        """Should match valid frontmatter patterns."""
        parser = SkillParser()

        # Valid patterns
        valid = """---
name: test
---
content"""
        assert parser.FRONTMATTER_PATTERN.match(valid)

        # Invalid - no closing delimiter
        invalid1 = """---
name: test
content"""
        assert not parser.FRONTMATTER_PATTERN.match(invalid1)

        # Invalid - doesn't start at beginning
        invalid2 = """
---
name: test
---"""
        assert not parser.FRONTMATTER_PATTERN.match(invalid2)

    def test_script_extensions_constant(self) -> None:
        """Should have correct script extensions defined."""
        parser = SkillParser()

        expected_extensions = {".sh", ".py", ".rb", ".js", ".ts", ".pl"}
        assert parser.SCRIPT_EXTENSIONS == expected_extensions

    def test_script_dirs_constant(self) -> None:
        """Should have correct script directories defined."""
        parser = SkillParser()

        expected_dirs = {"scripts", "bin", "tools"}
        assert parser.SCRIPT_DIRS == expected_dirs
