"""Tests for progressive context loader.

This module tests the ContextLoader class for parsing SKILL.md file references
and managing progressive context loading.
"""

from pathlib import Path
from unittest.mock import Mock

from omniforge.skills.context_loader import ContextLoader, FileReference, LoadedContext
from omniforge.skills.models import Skill, SkillMetadata


class TestFileReference:
    """Tests for FileReference dataclass."""

    def test_create_file_reference(self) -> None:
        """FileReference should initialize with all attributes."""
        ref = FileReference(
            filename="reference.md",
            path=Path("/path/to/reference.md"),
            description="API documentation",
            estimated_lines=1200,
            loaded=False,
        )

        assert ref.filename == "reference.md"
        assert ref.path == Path("/path/to/reference.md")
        assert ref.description == "API documentation"
        assert ref.estimated_lines == 1200
        assert ref.loaded is False

    def test_file_reference_defaults(self) -> None:
        """FileReference should have sensible defaults."""
        ref = FileReference(
            filename="reference.md",
            path=Path("/path/to/reference.md"),
            description="API documentation",
        )

        assert ref.estimated_lines is None
        assert ref.loaded is False


class TestLoadedContext:
    """Tests for LoadedContext dataclass."""

    def test_create_loaded_context(self) -> None:
        """LoadedContext should initialize with all attributes."""
        context = LoadedContext(
            skill_content="Test content",
            available_files={"ref.md": Mock()},
            skill_dir=Path("/skill/dir"),
            line_count=10,
        )

        assert context.skill_content == "Test content"
        assert len(context.available_files) == 1
        assert context.skill_dir == Path("/skill/dir")
        assert context.line_count == 10

    def test_loaded_context_defaults(self) -> None:
        """LoadedContext should have sensible defaults."""
        context = LoadedContext(skill_content="Test content")

        assert context.available_files == {}
        assert context.skill_dir == Path()
        assert context.line_count == 0


class TestContextLoader:
    """Tests for ContextLoader class."""

    def _create_mock_skill(self, content: str, skill_dir: Path) -> Skill:
        """Create a mock skill for testing.

        Args:
            content: SKILL.md content
            skill_dir: Skill directory path

        Returns:
            Mock Skill object
        """
        metadata = SkillMetadata(
            name="test-skill",
            description="Test skill",
        )

        return Skill(
            metadata=metadata,
            content=content,
            path=skill_dir / "SKILL.md",
            base_path=skill_dir,
            storage_layer="test",
            script_paths=None,
        )

    def test_extract_list_pattern(self, tmp_path: Path) -> None:
        """Should extract file references from list pattern."""
        # Create supporting file
        (tmp_path / "reference.md").write_text("API docs")

        content = """
        Supporting files:
        - reference.md: API documentation (1,200 lines)
        - examples.md: Usage examples
        """

        skill = self._create_mock_skill(content, tmp_path)
        loader = ContextLoader(skill)
        refs = loader._extract_file_references(content, tmp_path)

        assert "reference.md" in refs
        assert refs["reference.md"].filename == "reference.md"
        assert refs["reference.md"].description == "API documentation"
        assert refs["reference.md"].estimated_lines == 1200

    def test_extract_bold_pattern(self, tmp_path: Path) -> None:
        """Should extract file references from bold markdown pattern."""
        # Create supporting file
        (tmp_path / "reference.md").write_text("API docs")

        content = """
        **reference.md**: Complete API reference (300 lines)
        **examples.md**: Usage patterns and examples
        """

        skill = self._create_mock_skill(content, tmp_path)
        loader = ContextLoader(skill)
        refs = loader._extract_file_references(content, tmp_path)

        assert "reference.md" in refs
        assert refs["reference.md"].description == "Complete API reference"
        assert refs["reference.md"].estimated_lines == 300

    def test_extract_inline_pattern(self, tmp_path: Path) -> None:
        """Should extract file references from inline text patterns."""
        # Create supporting files
        (tmp_path / "reference.md").write_text("API docs")
        (tmp_path / "examples.md").write_text("Examples")

        content = """
        See reference.md for API documentation.
        Read examples.md for usage patterns.
        Check guidelines.txt for best practices.
        """

        skill = self._create_mock_skill(content, tmp_path)
        loader = ContextLoader(skill)
        refs = loader._extract_file_references(content, tmp_path)

        assert "reference.md" in refs
        assert "examples.md" in refs
        assert len(refs["reference.md"].description) > 0

    def test_extract_nested_path(self, tmp_path: Path) -> None:
        """Should extract file references with nested paths."""
        # Create nested directory structure
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        (templates_dir / "report.md").write_text("Report template")

        content = """
        Check templates/report.md for report format.
        """

        skill = self._create_mock_skill(content, tmp_path)
        loader = ContextLoader(skill)
        refs = loader._extract_file_references(content, tmp_path)

        assert "templates/report.md" in refs
        assert refs["templates/report.md"].path.exists()

    def test_validate_files_exist(self, tmp_path: Path) -> None:
        """Should only include files that actually exist."""
        # Create only one file
        (tmp_path / "reference.md").write_text("API docs")

        content = """
        - reference.md: API documentation
        - missing.md: This file does not exist
        - nonexistent.txt: Also missing
        """

        skill = self._create_mock_skill(content, tmp_path)
        loader = ContextLoader(skill)
        refs = loader._extract_file_references(content, tmp_path)

        # Only reference.md should be included
        assert "reference.md" in refs
        assert "missing.md" not in refs
        assert "nonexistent.txt" not in refs

    def test_load_initial_context(self, tmp_path: Path) -> None:
        """Should load initial context with skill content and file references."""
        # Create supporting files
        (tmp_path / "reference.md").write_text("API docs")
        (tmp_path / "examples.md").write_text("Examples")

        content = """# Test Skill

This is a test skill.

Supporting files:
- reference.md: API documentation (1,200 lines)
- examples.md: Usage examples
"""

        skill = self._create_mock_skill(content, tmp_path)
        loader = ContextLoader(skill)
        context = loader.load_initial_context()

        assert isinstance(context, LoadedContext)
        assert context.skill_content == content
        assert context.skill_dir == tmp_path
        assert context.line_count == len(content.splitlines())
        assert "reference.md" in context.available_files
        assert "examples.md" in context.available_files

    def test_mark_file_loaded(self, tmp_path: Path) -> None:
        """Should track which files have been loaded."""
        skill = self._create_mock_skill("", tmp_path)
        loader = ContextLoader(skill)

        loader.mark_file_loaded("reference.md")
        loader.mark_file_loaded("examples.md")

        loaded = loader.get_loaded_files()
        assert "reference.md" in loaded
        assert "examples.md" in loaded
        assert len(loaded) == 2

    def test_get_loaded_files_returns_copy(self, tmp_path: Path) -> None:
        """Should return a copy of loaded files set."""
        skill = self._create_mock_skill("", tmp_path)
        loader = ContextLoader(skill)

        loader.mark_file_loaded("reference.md")
        loaded1 = loader.get_loaded_files()
        loaded2 = loader.get_loaded_files()

        # Modifying one should not affect the other
        loaded1.add("examples.md")
        assert "examples.md" not in loaded2

    def test_build_available_files_prompt(self, tmp_path: Path) -> None:
        """Should build formatted prompt section for available files."""
        # Create supporting files
        (tmp_path / "reference.md").write_text("API docs")
        (tmp_path / "examples.md").write_text("Examples")

        content = """
        - reference.md: API documentation (1,200 lines)
        - examples.md: Usage examples
        """

        skill = self._create_mock_skill(content, tmp_path)
        loader = ContextLoader(skill)
        context = loader.load_initial_context()
        prompt = loader.build_available_files_prompt(context)

        assert "AVAILABLE SUPPORTING FILES" in prompt
        assert "reference.md" in prompt
        assert "examples.md" in prompt
        assert "API documentation" in prompt
        assert "1,200 lines" in prompt
        assert str(tmp_path / "reference.md") in prompt

    def test_build_available_files_prompt_empty(self, tmp_path: Path) -> None:
        """Should return empty string when no files available."""
        skill = self._create_mock_skill("No file references here", tmp_path)
        loader = ContextLoader(skill)
        context = loader.load_initial_context()
        prompt = loader.build_available_files_prompt(context)

        assert prompt == ""

    def test_extract_line_count(self, tmp_path: Path) -> None:
        """Should extract line counts from various formats."""
        skill = self._create_mock_skill("", tmp_path)
        loader = ContextLoader(skill)

        # Test with comma separator
        assert loader._extract_line_count("(1,200 lines)") == 1200

        # Test without comma
        assert loader._extract_line_count("(300 lines)") == 300

        # Test singular form
        assert loader._extract_line_count("(1 line)") == 1

        # Test no match
        assert loader._extract_line_count("No line count here") is None

    def test_clean_description(self, tmp_path: Path) -> None:
        """Should clean up description text."""
        skill = self._create_mock_skill("", tmp_path)
        loader = ContextLoader(skill)

        # Test whitespace normalization
        desc = loader._clean_description("Multiple   spaces\n and\nlines")
        assert desc == "Multiple spaces and lines"

        # Test line count removal
        desc = loader._clean_description("API docs (1,200 lines)")
        assert desc == "API docs"

        # Test truncation
        long_text = "x" * 250
        desc = loader._clean_description(long_text)
        assert len(desc) == 200
        assert desc.endswith("...")

    def test_supported_extensions(self, tmp_path: Path) -> None:
        """Should recognize all supported file extensions."""
        # Create files with different extensions
        (tmp_path / "file.md").write_text("markdown")
        (tmp_path / "file.txt").write_text("text")
        (tmp_path / "file.json").write_text("{}")
        (tmp_path / "file.yaml").write_text("key: value")
        (tmp_path / "file.yml").write_text("key: value")
        (tmp_path / "file.unsupported").write_text("not supported")

        content = """
        - file.md: Markdown
        - file.txt: Text
        - file.json: JSON
        - file.yaml: YAML
        - file.yml: YML
        - file.unsupported: Unsupported
        """

        skill = self._create_mock_skill(content, tmp_path)
        loader = ContextLoader(skill)
        refs = loader._extract_file_references(content, tmp_path)

        assert "file.md" in refs
        assert "file.txt" in refs
        assert "file.json" in refs
        assert "file.yaml" in refs
        assert "file.yml" in refs
        assert "file.unsupported" not in refs

    def test_case_insensitive_patterns(self, tmp_path: Path) -> None:
        """Should match file references case-insensitively."""
        (tmp_path / "reference.md").write_text("API docs")

        content = """
        SEE reference.md for API documentation.
        READ reference.md for more details.
        Check reference.md before proceeding.
        """

        skill = self._create_mock_skill(content, tmp_path)
        loader = ContextLoader(skill)
        refs = loader._extract_file_references(content, tmp_path)

        # Should find the file at least once
        assert "reference.md" in refs

    def test_duplicate_references_ignored(self, tmp_path: Path) -> None:
        """Should not add duplicate file references."""
        (tmp_path / "reference.md").write_text("API docs")

        content = """
        - reference.md: API documentation
        See reference.md for details.
        **reference.md**: Complete reference
        """

        skill = self._create_mock_skill(content, tmp_path)
        loader = ContextLoader(skill)
        refs = loader._extract_file_references(content, tmp_path)

        # Should only have one entry
        assert len([r for r in refs if r == "reference.md"]) == 1

    def test_multiline_skill_content(self, tmp_path: Path) -> None:
        """Should correctly count lines in multi-line content."""
        content = """Line 1
Line 2
Line 3
Line 4
Line 5"""

        skill = self._create_mock_skill(content, tmp_path)
        loader = ContextLoader(skill)
        context = loader.load_initial_context()

        assert context.line_count == 5

    def test_context_loader_with_real_skill_structure(self, tmp_path: Path) -> None:
        """Should work with realistic skill directory structure."""
        # Create realistic skill structure
        (tmp_path / "reference.md").write_text("# API Reference\n\nAPI details here")
        (tmp_path / "examples.md").write_text("# Examples\n\nExample usage")

        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        (templates_dir / "report.md").write_text("# Report Template")

        content = """# Data Processor Skill

Process and analyze data from various sources.

## Supporting Files

- reference.md: Complete API reference (50 lines)
- examples.md: Usage examples and patterns

For report formatting, check templates/report.md.
"""

        skill = self._create_mock_skill(content, tmp_path)
        loader = ContextLoader(skill)
        context = loader.load_initial_context()

        # Should find all three files
        assert len(context.available_files) == 3
        assert "reference.md" in context.available_files
        assert "examples.md" in context.available_files
        assert "templates/report.md" in context.available_files

        # Build prompt and verify content
        prompt = loader.build_available_files_prompt(context)
        assert "AVAILABLE SUPPORTING FILES" in prompt
        assert "reference.md" in prompt
        assert "50 lines" in prompt

    def test_quoted_filenames(self, tmp_path: Path) -> None:
        """Should handle filenames in quotes or backticks."""
        (tmp_path / "reference.md").write_text("API docs")

        content = """
        See `reference.md` for details.
        Check 'reference.md' for info.
        Read "reference.md" for docs.
        """

        skill = self._create_mock_skill(content, tmp_path)
        loader = ContextLoader(skill)
        refs = loader._extract_file_references(content, tmp_path)

        assert "reference.md" in refs

    def test_invalid_line_count_format(self, tmp_path: Path) -> None:
        """Should handle invalid line count gracefully."""
        skill = self._create_mock_skill("", tmp_path)
        loader = ContextLoader(skill)

        # Test with non-numeric value
        assert loader._extract_line_count("(invalid lines)") is None

        # Test with malformed format
        assert loader._extract_line_count("(abc,def lines)") is None

    def test_unsupported_file_extension(self, tmp_path: Path) -> None:
        """Should skip files with unsupported extensions."""
        # Create file with unsupported extension
        (tmp_path / "file.exe").write_text("Binary content")
        (tmp_path / "file.bin").write_text("Binary content")

        content = """
        - file.exe: Executable file
        - file.bin: Binary file
        """

        skill = self._create_mock_skill(content, tmp_path)
        loader = ContextLoader(skill)
        refs = loader._extract_file_references(content, tmp_path)

        # Should not include unsupported extensions
        assert "file.exe" not in refs
        assert "file.bin" not in refs
