"""Skill file parser for YAML frontmatter and script detection.

This module provides functionality to parse SKILL.md files with YAML frontmatter,
extract metadata, and detect associated script files in the skill directory.
"""

import re
from pathlib import Path
from typing import Optional

import yaml

from omniforge.skills.errors import SkillParseError
from omniforge.skills.models import Skill, SkillIndexEntry, SkillMetadata


class SkillParser:
    """Parser for skill files with YAML frontmatter.

    This parser handles both lightweight metadata parsing for indexing (Stage 1)
    and full skill parsing with script detection (Stage 2).

    Attributes:
        FRONTMATTER_PATTERN: Regex pattern for matching YAML frontmatter
        SCRIPT_EXTENSIONS: Set of supported script file extensions
        SCRIPT_DIRS: Set of directories to scan for script files
    """

    FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.MULTILINE | re.DOTALL)
    SCRIPT_EXTENSIONS = {".sh", ".py", ".rb", ".js", ".ts", ".pl"}
    SCRIPT_DIRS = {"scripts", "bin", "tools"}

    def parse_metadata(self, path: Path, storage_layer: str) -> SkillIndexEntry:
        """Parse only frontmatter for skill indexing (Stage 1).

        This method extracts minimal metadata needed for skill discovery and
        listing without loading full content or detecting scripts.

        Args:
            path: Path to skill file (SKILL.md)
            storage_layer: Storage layer identifier (e.g., "global", "tenant-123")

        Returns:
            SkillIndexEntry with name, description, path, and optional metadata

        Raises:
            SkillParseError: If file cannot be read or frontmatter is invalid
        """
        content = self._read_file(path)
        frontmatter_yaml, _ = self._extract_frontmatter(content, path)

        try:
            metadata_dict = yaml.safe_load(frontmatter_yaml)
            if not isinstance(metadata_dict, dict):
                raise SkillParseError(
                    str(path),
                    "Frontmatter must be a YAML dictionary",
                )

            # Validate required fields for metadata
            metadata = SkillMetadata(**metadata_dict)

        except yaml.YAMLError as e:
            line_number = getattr(e, "problem_mark", None)
            line_num = line_number.line + 1 if line_number else None
            raise SkillParseError(
                str(path),
                f"Invalid YAML frontmatter: {e}",
                line_num,
            ) from e
        except (TypeError, ValueError) as e:
            raise SkillParseError(
                str(path),
                f"Invalid metadata format: {e}",
            ) from e

        return SkillIndexEntry(
            name=metadata.name,
            description=metadata.description,
            path=path.resolve(),
            storage_layer=storage_layer,
            tags=metadata.tags,
            priority=metadata.priority,
        )

    def parse_full(self, path: Path, storage_layer: str) -> Skill:
        """Parse complete SKILL.md file (Stage 2).

        This method extracts both metadata and body content, and detects any
        script files in the skill directory.

        Args:
            path: Path to skill file (SKILL.md)
            storage_layer: Storage layer identifier (e.g., "global", "tenant-123")

        Returns:
            Complete Skill with metadata, content, and script paths

        Raises:
            SkillParseError: If file cannot be read or frontmatter is invalid
        """
        content = self._read_file(path)
        frontmatter_yaml, body = self._extract_frontmatter(content, path)

        try:
            metadata_dict = yaml.safe_load(frontmatter_yaml)
            if not isinstance(metadata_dict, dict):
                raise SkillParseError(
                    str(path),
                    "Frontmatter must be a YAML dictionary",
                )

            metadata = SkillMetadata(**metadata_dict)

        except yaml.YAMLError as e:
            line_number = getattr(e, "problem_mark", None)
            line_num = line_number.line + 1 if line_number else None
            raise SkillParseError(
                str(path),
                f"Invalid YAML frontmatter: {e}",
                line_num,
            ) from e
        except (TypeError, ValueError) as e:
            raise SkillParseError(
                str(path),
                f"Invalid metadata format: {e}",
            ) from e

        # Detect script files in skill directory
        base_path = path.parent
        script_files = self._detect_script_files(base_path)

        # Build script paths mapping if hooks are defined
        script_paths: Optional[dict[str, Path]] = None
        if metadata.hooks:
            script_paths = {}
            if metadata.hooks.pre:
                pre_path = base_path / metadata.hooks.pre
                if pre_path.exists():
                    script_paths["pre"] = pre_path.resolve()
            if metadata.hooks.post:
                post_path = base_path / metadata.hooks.post
                if post_path.exists():
                    script_paths["post"] = post_path.resolve()

        # If no hooks defined but scripts found, include all detected scripts
        if not script_paths and script_files:
            script_paths = {f"script_{i}": p for i, p in enumerate(script_files)}

        return Skill(
            metadata=metadata,
            content=body.strip(),
            path=path.resolve(),
            base_path=base_path.resolve(),
            storage_layer=storage_layer,
            script_paths=script_paths,
        )

    def _read_file(self, path: Path) -> str:
        """Read file content with UTF-8 encoding.

        Args:
            path: Path to file to read

        Returns:
            File content as string

        Raises:
            SkillParseError: If file cannot be read
        """
        try:
            return path.read_text(encoding="utf-8")
        except FileNotFoundError:
            raise SkillParseError(
                str(path),
                "File not found",
            )
        except UnicodeDecodeError as e:
            raise SkillParseError(
                str(path),
                f"File encoding error: {e}",
            ) from e
        except OSError as e:
            raise SkillParseError(
                str(path),
                f"Failed to read file: {e}",
            ) from e

    def _extract_frontmatter(self, content: str, path: Path) -> tuple[str, str]:
        """Extract YAML frontmatter from content.

        Args:
            content: File content
            path: Path to file (for error messages)

        Returns:
            Tuple of (frontmatter_yaml, body_content)

        Raises:
            SkillParseError: If frontmatter is missing or malformed
        """
        match = self.FRONTMATTER_PATTERN.match(content)
        if not match:
            raise SkillParseError(
                str(path),
                "Missing YAML frontmatter. File must start with '---' delimiter.",
            )

        frontmatter_yaml = match.group(1)
        body = content[match.end() :]

        return frontmatter_yaml, body

    def _detect_script_files(self, base_path: Path) -> list[Path]:
        """Detect script files in skill directory.

        Scans SCRIPT_DIRS for files with SCRIPT_EXTENSIONS.

        Args:
            base_path: Base directory to scan

        Returns:
            List of absolute paths to detected script files
        """
        script_files: list[Path] = []

        for script_dir in self.SCRIPT_DIRS:
            dir_path = base_path / script_dir
            if not dir_path.exists() or not dir_path.is_dir():
                continue

            # Use rglob to support nested directories
            for ext in self.SCRIPT_EXTENSIONS:
                for script_path in dir_path.rglob(f"*{ext}"):
                    if script_path.is_file():
                        script_files.append(script_path.resolve())

        return sorted(script_files)
