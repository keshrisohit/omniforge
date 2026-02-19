"""Progressive context loader for skill supporting files.

This module provides the ContextLoader class that parses SKILL.md for supporting
file references and manages on-demand loading. Extracts references like "See reference.md
for details (1,200 lines)" and builds a list of available files for the system prompt.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from omniforge.skills.models import Skill


@dataclass
class FileReference:
    """Reference to a supporting file in a skill directory.

    Attributes:
        filename: Name of the file (e.g., "reference.md")
        path: Absolute path to the file
        description: Description extracted from SKILL.md
        estimated_lines: Line count if mentioned (e.g., 1200 from "(1,200 lines)")
        loaded: Whether file has been loaded during execution
    """

    filename: str
    path: Path
    description: str
    estimated_lines: Optional[int] = None
    loaded: bool = False


@dataclass
class LoadedContext:
    """Context loaded from a skill.

    Attributes:
        skill_content: SKILL.md content (markdown body without frontmatter)
        available_files: Map of filename -> FileReference for supporting files
        skill_dir: Absolute path to skill directory
        line_count: Number of lines in SKILL.md content
    """

    skill_content: str
    available_files: dict[str, FileReference] = field(default_factory=dict)
    skill_dir: Path = field(default_factory=Path)
    line_count: int = 0


class ContextLoader:
    """Loader for progressive context loading of skill supporting files.

    Parses SKILL.md for references to supporting files and manages on-demand loading.
    Only SKILL.md content is loaded initially; supporting files are loaded on-demand
    via the `read` tool during execution.

    Supported file reference patterns:
        1. "See reference.md for API documentation (1,200 lines)"
        2. "- reference.md: Description"
        3. "**reference.md**: Description (300 lines)"
        4. "Read examples.md for usage patterns"
        5. "Check templates/report.md"

    Attributes:
        FILE_PATTERN: Regex pattern for file reference matching
        LINE_COUNT_PATTERN: Regex pattern for extracting line counts
        SUPPORTED_EXTENSIONS: File extensions to recognize as supporting files
    """

    # Regex patterns for extracting file references
    FILE_PATTERN = re.compile(
        r"(?:see|read|check|refer\s+to|reference|load|include)\s+"
        r"[`'\"]?([a-zA-Z0-9_\-/]+\.(?:md|txt|json|yaml|yml))[`'\"]?",
        re.IGNORECASE,
    )

    # Pattern for list items with file references
    LIST_PATTERN = re.compile(
        r"^[\s]*[-*]\s+[`'\"]?([a-zA-Z0-9_\-/]+\.(?:md|txt|json|yaml|yml))[`'\"]?\s*:\s*(.+)$",
        re.MULTILINE,
    )

    # Pattern for bold markdown file references
    BOLD_PATTERN = re.compile(
        r"\*\*[`'\"]?([a-zA-Z0-9_\-/]+\.(?:md|txt|json|yaml|yml))[`'\"]?\*\*\s*:\s*(.+?)(?:\n|$)",
    )

    # Pattern for extracting line counts from descriptions
    LINE_COUNT_PATTERN = re.compile(r"\(([0-9,]+)\s+lines?\)")

    # Supported file extensions
    SUPPORTED_EXTENSIONS = {".md", ".txt", ".json", ".yaml", ".yml"}

    def __init__(self, skill: Skill) -> None:
        """Initialize context loader for a skill.

        Args:
            skill: The skill to load context for
        """
        self._skill = skill
        self._loaded_files: set[str] = set()

    def load_initial_context(self) -> LoadedContext:
        """Load initial context with SKILL.md content and available file references.

        Parses SKILL.md content to extract references to supporting files,
        validates that referenced files exist, and builds a context object
        with metadata about available files.

        Returns:
            LoadedContext with skill content and available file references
        """
        # Get skill content and metadata
        skill_content = self._skill.content
        skill_dir = self._skill.base_path
        line_count = len(skill_content.splitlines())

        # Extract file references from content
        file_refs = self._extract_file_references(skill_content, skill_dir)

        return LoadedContext(
            skill_content=skill_content,
            available_files=file_refs,
            skill_dir=skill_dir,
            line_count=line_count,
        )

    def mark_file_loaded(self, filename: str) -> None:
        """Mark a file as loaded during execution.

        Args:
            filename: Name of the file that was loaded
        """
        self._loaded_files.add(filename)

    def get_loaded_files(self) -> set[str]:
        """Get set of files that have been loaded.

        Returns:
            Set of filenames that have been loaded
        """
        return self._loaded_files.copy()

    def build_available_files_prompt(self, context: LoadedContext) -> str:
        """Build formatted prompt section for available supporting files.

        Creates a formatted section that can be included in the system prompt
        to inform the agent about available supporting files.

        Args:
            context: The loaded context with available files

        Returns:
            Formatted string for system prompt
        """
        if not context.available_files:
            return ""

        lines = [
            "## AVAILABLE SUPPORTING FILES",
            "",
            "The following supporting files are available in the skill directory.",
            "Use the `read` tool to load them on-demand when needed:",
            "",
        ]

        # Sort files by filename for consistent output
        sorted_files = sorted(context.available_files.items())

        for filename, file_ref in sorted_files:
            line_info = ""
            if file_ref.estimated_lines:
                # Format with thousands separator
                line_info = f" (~{file_ref.estimated_lines:,} lines)"

            lines.append(f"- **{filename}**{line_info}")
            lines.append(f"  Path: `{file_ref.path}`")
            lines.append(f"  Description: {file_ref.description}")
            lines.append("")

        return "\n".join(lines)

    def _extract_file_references(self, content: str, skill_dir: Path) -> dict[str, FileReference]:
        """Extract file references from SKILL.md content.

        Scans content for various file reference patterns and builds
        FileReference objects for files that exist in the skill directory.

        Args:
            content: SKILL.md content to parse
            skill_dir: Skill directory path for resolving file paths

        Returns:
            Dictionary mapping filename to FileReference
        """
        file_refs: dict[str, FileReference] = {}

        # Pattern 1: List items "- reference.md: Description"
        for match in self.LIST_PATTERN.finditer(content):
            filename = match.group(1)
            description = match.group(2).strip()
            self._add_file_reference(file_refs, filename, description, skill_dir)

        # Pattern 2: Bold references "**reference.md**: Description"
        for match in self.BOLD_PATTERN.finditer(content):
            filename = match.group(1)
            description = match.group(2).strip()
            self._add_file_reference(file_refs, filename, description, skill_dir)

        # Pattern 3: Inline references "See reference.md for details"
        for match in self.FILE_PATTERN.finditer(content):
            filename = match.group(1)

            # Skip if already found with better description
            if filename in file_refs:
                continue

            # Extract surrounding context as description (up to 100 chars)
            start = max(0, match.start() - 50)
            end = min(len(content), match.end() + 50)
            context_snippet = content[start:end].strip()

            # Clean up description
            description = self._clean_description(context_snippet)

            self._add_file_reference(file_refs, filename, description, skill_dir)

        return file_refs

    def _add_file_reference(
        self,
        file_refs: dict[str, FileReference],
        filename: str,
        description: str,
        skill_dir: Path,
    ) -> None:
        """Add a file reference if the file exists and is not already added.

        Args:
            file_refs: Dictionary to add reference to
            filename: Name of the file (may include subdirectory path)
            description: Description of the file
            skill_dir: Skill directory for resolving paths
        """
        # Skip if already added
        if filename in file_refs:
            return

        # Resolve file path
        file_path = skill_dir / filename

        # Only add if file exists
        if not file_path.exists():
            return

        # Check if extension is supported
        if file_path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            return

        # Extract line count if mentioned
        estimated_lines = self._extract_line_count(description)

        # Create file reference
        file_refs[filename] = FileReference(
            filename=filename,
            path=file_path.resolve(),
            description=self._clean_description(description),
            estimated_lines=estimated_lines,
            loaded=False,
        )

    def _extract_line_count(self, text: str) -> Optional[int]:
        """Extract line count from description text.

        Parses patterns like "(1,200 lines)" or "(300 lines)" and converts
        to integer.

        Args:
            text: Text to extract line count from

        Returns:
            Line count as integer, or None if not found
        """
        match = self.LINE_COUNT_PATTERN.search(text)
        if match:
            # Remove commas and convert to int
            count_str = match.group(1).replace(",", "")
            try:
                return int(count_str)
            except ValueError:
                return None
        return None

    def _clean_description(self, text: str) -> str:
        """Clean up description text.

        Removes excess whitespace, newlines, and truncates to reasonable length.

        Args:
            text: Raw description text

        Returns:
            Cleaned description
        """
        # Replace multiple whitespace/newlines with single space
        cleaned = re.sub(r"\s+", " ", text)

        # Remove line count from description to avoid duplication
        cleaned = self.LINE_COUNT_PATTERN.sub("", cleaned)

        # Truncate to 200 characters
        if len(cleaned) > 200:
            cleaned = cleaned[:197] + "..."

        return cleaned.strip()
