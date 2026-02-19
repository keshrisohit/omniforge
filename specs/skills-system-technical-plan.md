# Agent Skills System - Technical Implementation Plan

**Created**: 2026-01-13
**Updated**: 2026-01-13
**Version**: 1.1
**Status**: Ready for Task Decomposition
**Author**: Technical Architect

**Review Status**: APPROVED WITH CHANGES - All critical and high-priority issues addressed

**Changes from v1.0:**
- Added Multi-LLM Compatibility Strategy section (addresses CRITICAL-1)
- Added Script Execution Enforcement Mechanism section (addresses CRITICAL-2)
- Added Enhanced Tool Restriction Security section (addresses CRITICAL-3)
- Fixed storage layer detection to use explicit parameters (addresses HIGH-1)

---

## Executive Summary

This technical plan details the implementation of the Agent Skills System for OmniForge, enabling agents to discover and execute specialized capabilities defined in SKILL.md files. The system follows Claude Code's progressive disclosure pattern, where skills are presented through the SkillTool description rather than the system prompt, achieving zero context cost until skill invocation.

**Key Technical Decisions:**
1. **SkillTool as Progressive Disclosure Vehicle**: Skills list embedded in SkillTool's dynamically-generated description
2. **SkillLoader with Caching**: Directory scanning with parsed metadata cache for sub-100ms discovery
3. **Pydantic Models**: `Skill` and `SkillMetadata` models for type-safe YAML parsing
4. **Four-Layer Storage**: Enterprise > Personal > Project > Plugin with clear override semantics
5. **Tool Restriction at Executor Level**: Enforcement in `ToolExecutor` via `ExecutionContext.active_skill`
6. **Rename Strategy**: Existing `SkillTool` becomes `FunctionTool` with deprecation aliases

**Architecture Approach**: Minimal new components, maximum reuse of existing tool infrastructure. The skills system integrates as a new tool type alongside existing tools, not a parallel system.

---

## Requirements Analysis

### Functional Requirements (from Spec)

| ID | Requirement | Implementation Component |
|----|-------------|-------------------------|
| FR-1 | Load SKILL.md files from directories | `SkillLoader.scan_directory()` |
| FR-2 | Parse YAML frontmatter with validation | `SkillParser.parse()` |
| FR-3 | Four-layer storage hierarchy | `SkillStorageManager` |
| FR-4 | Progressive disclosure (3-stage loading) | `SkillTool.definition` (dynamic) |
| FR-5 | Tool restrictions (allowed-tools) | `ToolExecutor` + `ExecutionContext` |
| FR-6 | Path resolution for agents | `base_path` in ToolResult |
| FR-7 | Script execution without loading | Documentation in system prompt |
| FR-8 | Skill activation/deactivation | `SkillContext` context manager |
| FR-9 | Rename existing SkillTool | `FunctionTool` with aliases |

### Non-Functional Requirements

| ID | Requirement | Target | Validation |
|----|-------------|--------|------------|
| NFR-1 | Discovery latency | < 100ms for 1000 skills | Benchmark test |
| NFR-2 | Activation latency | < 50ms | Unit test timing |
| NFR-3 | Memory overhead | < 10MB for 1000 skills | Memory profiling |
| NFR-4 | Index size | ~1KB per skill | Measurement |
| NFR-5 | Type safety | 100% mypy compliance | CI check |
| NFR-6 | Test coverage | > 80% | pytest-cov |

---

## Constraints and Assumptions

### Technical Constraints

1. **Python 3.9+**: Must use built-in generics (`list[str]` not `List[str]`)
2. **Line length**: 100 characters (Black/Ruff enforced)
3. **Strict typing**: mypy with `disallow_untyped_defs = true`
4. **Existing tool interface**: Must implement `BaseTool` from `tools/base.py`
5. **Pydantic v2**: Use v2 patterns (already in codebase)

### Assumptions

1. File system access is available for skill directories
2. YAML frontmatter follows Hugo/Jekyll convention (`---` delimiters)
3. Single active skill at a time (multi-skill is out of scope)
4. Skills are trusted code (enterprise security is enforcement layer)
5. Existing `SkillTool` (Python functions) can be renamed without breaking external APIs

### Dependencies

- **pyyaml** or **ruamel.yaml**: YAML parsing (recommend `pyyaml` for simplicity)
- **python-frontmatter**: YAML frontmatter extraction (optional, can implement inline)
- **watchdog** (optional): File system watching for hot reload

---

## System Architecture

### High-Level Component Diagram

```
                                    +-----------------------+
                                    |    Agent System       |
                                    |   (CoT Engine, etc)   |
                                    +-----------+-----------+
                                                |
                                                | invokes
                                                v
+---------------------------+       +-----------------------+
|    SkillStorageManager    |       |      ToolExecutor     |
|---------------------------|       |-----------------------|
| - enterprise_path         |<----->| - registry            |
| - personal_path           |       | - active_skill_ctx    |<----+
| - project_path            |       | - rate_limiter        |     |
| - plugin_paths            |       +-----------+-----------+     |
+------------+--------------+                   |                 |
             |                                  | executes        |
             | loads from                       v                 |
             v                      +-----------------------+     |
+---------------------------+       |      SkillTool        |     |
|       SkillLoader         |       |-----------------------|     |
|---------------------------|       | - skill_loader        |     |
| - storage_manager         |       | - skill_cache         |     |
| - skill_index: dict       |------>| - active_skills       |     |
| - last_scan: datetime     |       | + definition (dynamic)|     |
+------------+--------------+       | + execute()           |     |
             |                      +-----------+-----------+     |
             | parses                           |                 |
             v                                  | returns         |
+---------------------------+                   v                 |
|       SkillParser         |       +-----------------------+     |
|---------------------------|       |      ToolResult       |     |
| + parse(path) -> Skill    |       | - skill_name          |     |
| + parse_frontmatter()     |       | - base_path           |     |
| + validate_metadata()     |       | - content             |     |
+---------------------------+       +-----------------------+     |
                                                                  |
+---------------------------+                                     |
|       SkillContext        |-------------------------------------+
|---------------------------|   restricts tools
| - original_tools          |
| - restricted_tools        |
| - skill: Skill            |
| + __enter__()             |
| + __exit__()              |
+---------------------------+
```

### Data Flow

```
1. Agent Initialization
   +---------+     +----------------+     +--------------+
   | Agent   |---->| SkillLoader    |---->| Storage Mgr  |
   | Init    |     | .load_index()  |     | .scan_all()  |
   +---------+     +----------------+     +--------------+
                          |
                          v
                   +----------------+
                   | Skill Index    |  (in-memory cache)
                   | name -> meta   |
                   +----------------+

2. Skill Discovery (Stage 1 - Tool Definition)
   +---------+     +----------------+     +--------------+
   | LLM     |<----| SkillTool      |<----| Skill Index  |
   | prompt  |     | .definition    |     | (metadata)   |
   +---------+     +----------------+     +--------------+
                          |
                          v
                   +------------------+
                   | <available_skills>
                   | "name": desc     |
                   +------------------+

3. Skill Activation (Stage 2 - Tool Execution)
   +---------+     +----------------+     +--------------+
   | LLM     |---->| SkillTool      |---->| SkillLoader  |
   | invoke  |     | .execute()     |     | .load_full() |
   +---------+     +----------------+     +--------------+
                          |
                          v
                   +------------------+
                   | ToolResult       |
                   | - skill_name     |
                   | - base_path      |
                   | - content (md)   |
                   +------------------+

4. Tool Restriction (During Skill Execution)
   +---------+     +----------------+     +--------------+
   | LLM     |---->| ToolExecutor   |---->| SkillContext |
   | tool    |     | .execute()     |     | .check_tool()|
   | call    |     +----------------+     +--------------+
   +---------+            |
                          v
                   +------------------+
                   | if tool not in   |
                   | allowed-tools:   |
                   |   return error   |
                   +------------------+
```

---

## Technology Stack

### Core Dependencies

| Component | Library | Version | Rationale |
|-----------|---------|---------|-----------|
| YAML Parsing | PyYAML | 6.0+ | Standard, well-tested, already in ecosystem |
| Data Models | Pydantic | 2.0+ | Already used in codebase, excellent validation |
| Path Handling | pathlib | stdlib | Python 3.9+ standard library |
| Async I/O | asyncio | stdlib | Consistent with existing tool pattern |
| Caching | functools.lru_cache | stdlib | Simple, effective for skill index |

### Optional Dependencies (Future)

| Component | Library | Use Case |
|-----------|---------|----------|
| File Watching | watchdog | Hot reload of skills |
| Frontmatter | python-frontmatter | Alternative to manual parsing |
| Schema Validation | jsonschema | Extended YAML validation |

---

## Component Specifications

### 1. Skill Data Model (`src/omniforge/skills/models.py`)

```python
"""Data models for the Agent Skills System."""

from enum import Enum
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class ContextMode(str, Enum):
    """Context mode for skill execution."""
    INHERIT = "inherit"
    FORK = "fork"


class SkillHooks(BaseModel):
    """Pre and post execution hooks for skills."""

    pre: Optional[str] = Field(
        default=None,
        description="Script to run before skill execution (relative path)"
    )
    post: Optional[str] = Field(
        default=None,
        description="Script to run after skill execution (relative path)"
    )


class SkillScope(BaseModel):
    """Scoping configuration for skill availability."""

    agents: Optional[list[str]] = Field(
        default=None,
        description="List of agent types this skill is available to"
    )
    tenants: Optional[list[str]] = Field(
        default=None,
        description="List of tenant IDs this skill is available to"
    )
    environments: Optional[list[str]] = Field(
        default=None,
        description="List of environments where skill is available"
    )


class SkillMetadata(BaseModel):
    """YAML frontmatter metadata from SKILL.md.

    This represents the parsed frontmatter section of a SKILL.md file.
    Used for Stage 1 (discovery) loading with minimal memory footprint.
    """

    name: str = Field(
        description="Unique skill identifier (kebab-case)"
    )
    description: str = Field(
        description="One-line description for discovery matching"
    )
    allowed_tools: Optional[list[str]] = Field(
        default=None,
        alias="allowed-tools",
        description="Tool allowlist (if omitted, all tools available)"
    )
    model: Optional[str] = Field(
        default=None,
        description="Preferred LLM model for this skill"
    )
    context: ContextMode = Field(
        default=ContextMode.INHERIT,
        description="Context mode: inherit or fork"
    )
    agent: Optional[str] = Field(
        default=None,
        description="Specific agent type to spawn (requires context: fork)"
    )
    hooks: Optional[SkillHooks] = Field(
        default=None,
        description="Pre/post execution hooks"
    )
    priority: int = Field(
        default=0,
        description="Override priority (higher wins in conflicts)"
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Categorization tags for organization"
    )
    scope: Optional[SkillScope] = Field(
        default=None,
        description="Scoping configuration for availability"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate skill name follows kebab-case convention."""
        import re
        if not re.match(r"^[a-z][a-z0-9-]*$", v):
            raise ValueError(
                f"Skill name '{v}' must be kebab-case "
                "(lowercase letters, numbers, hyphens, starting with letter)"
            )
        return v

    class Config:
        populate_by_name = True  # Allow both 'allowed_tools' and 'allowed-tools'


class Skill(BaseModel):
    """Complete skill definition including content.

    This represents a fully loaded skill with both metadata and content.
    Used for Stage 2 (activation) loading.
    """

    metadata: SkillMetadata = Field(
        description="Parsed YAML frontmatter"
    )
    content: str = Field(
        description="Full SKILL.md content (after frontmatter)"
    )
    path: Path = Field(
        description="Absolute path to SKILL.md file"
    )
    base_path: Path = Field(
        description="Absolute path to skill directory"
    )
    storage_layer: str = Field(
        description="Storage layer: enterprise, personal, project, or plugin"
    )

    @property
    def name(self) -> str:
        """Convenience accessor for skill name."""
        return self.metadata.name

    @property
    def description(self) -> str:
        """Convenience accessor for skill description."""
        return self.metadata.description

    @property
    def allowed_tools(self) -> Optional[list[str]]:
        """Convenience accessor for allowed tools."""
        return self.metadata.allowed_tools


class SkillIndexEntry(BaseModel):
    """Lightweight index entry for skill discovery.

    Minimal data structure for Stage 1 loading.
    Full Skill is loaded on-demand via path.
    """

    name: str
    description: str
    path: Path
    storage_layer: str
    priority: int = 0
    tags: list[str] = Field(default_factory=list)
```

### 2. Skill Parser (`src/omniforge/skills/parser.py`)

```python
"""YAML frontmatter parser for SKILL.md files."""

import re
from pathlib import Path
from typing import Optional, Tuple

import yaml
from pydantic import ValidationError

from omniforge.skills.models import Skill, SkillMetadata, SkillIndexEntry
from omniforge.skills.errors import SkillParseError


class SkillParser:
    """Parser for SKILL.md files with YAML frontmatter.

    Supports Hugo/Jekyll-style frontmatter:
    ```
    ---
    name: my-skill
    description: Skill description
    ---

    # Skill Content
    ...
    ```
    """

    # Regex pattern for YAML frontmatter
    FRONTMATTER_PATTERN = re.compile(
        r"^---\s*\n(.*?)\n---\s*\n(.*)$",
        re.DOTALL
    )

    def parse_metadata(self, path: Path, storage_layer: str) -> SkillIndexEntry:
        """Parse only the frontmatter for index building (Stage 1).

        Args:
            path: Path to SKILL.md file
            storage_layer: Explicit storage layer (enterprise, personal, project, plugin)

        Returns:
            SkillIndexEntry with minimal metadata

        Raises:
            SkillParseError: If parsing fails
        """
        content = self._read_file(path)
        frontmatter_str, _ = self._extract_frontmatter(content, path)

        try:
            frontmatter_data = yaml.safe_load(frontmatter_str)
            metadata = SkillMetadata.model_validate(frontmatter_data)

            return SkillIndexEntry(
                name=metadata.name,
                description=metadata.description,
                path=path,
                storage_layer=storage_layer,  # Use explicit parameter
                priority=metadata.priority,
                tags=metadata.tags,
            )
        except yaml.YAMLError as e:
            raise SkillParseError(
                f"Invalid YAML in frontmatter of {path}: {e}",
                path=path,
            )
        except ValidationError as e:
            raise SkillParseError(
                f"Invalid skill metadata in {path}: {e}",
                path=path,
            )

    def parse_full(self, path: Path, storage_layer: str) -> Skill:
        """Parse complete SKILL.md file (Stage 2).

        Args:
            path: Path to SKILL.md file
            storage_layer: Explicit storage layer (enterprise, personal, project, plugin)

        Returns:
            Complete Skill with metadata and content

        Raises:
            SkillParseError: If parsing fails
        """
        content = self._read_file(path)
        frontmatter_str, body = self._extract_frontmatter(content, path)

        try:
            frontmatter_data = yaml.safe_load(frontmatter_str)
            metadata = SkillMetadata.model_validate(frontmatter_data)

            return Skill(
                metadata=metadata,
                content=body.strip(),
                path=path,
                base_path=path.parent,
                storage_layer=storage_layer,  # Use explicit parameter
            )
        except yaml.YAMLError as e:
            raise SkillParseError(
                f"Invalid YAML in frontmatter of {path}: {e}",
                path=path,
            )
        except ValidationError as e:
            raise SkillParseError(
                f"Invalid skill metadata in {path}: {e}",
                path=path,
            )

    def _read_file(self, path: Path) -> str:
        """Read file content with UTF-8 encoding."""
        try:
            return path.read_text(encoding="utf-8")
        except OSError as e:
            raise SkillParseError(
                f"Failed to read skill file {path}: {e}",
                path=path,
            )

    def _extract_frontmatter(
        self, content: str, path: Path
    ) -> Tuple[str, str]:
        """Extract frontmatter and body from content.

        Returns:
            Tuple of (frontmatter_yaml, body_content)
        """
        match = self.FRONTMATTER_PATTERN.match(content)
        if not match:
            raise SkillParseError(
                f"No valid YAML frontmatter found in {path}. "
                "Expected format: ---\\n<yaml>\\n---\\n<content>",
                path=path,
            )
        return match.group(1), match.group(2)

    # NOTE: Storage layer is now passed explicitly as a parameter to parse methods
    # instead of being inferred from path. This avoids fragile path-based heuristics
    # that break with symlinks, network mounts, or non-standard directory structures.
```

### 3. Skill Storage Manager (`src/omniforge/skills/storage.py`)

```python
"""Storage layer management for skills hierarchy."""

import os
from pathlib import Path
from typing import Iterator, Optional

from pydantic import BaseModel, Field


class StorageConfig(BaseModel):
    """Configuration for skill storage locations."""

    enterprise_path: Optional[Path] = Field(
        default=None,
        description="Path to enterprise skills (highest priority)"
    )
    personal_path: Optional[Path] = Field(
        default=None,
        description="Path to personal skills"
    )
    project_path: Optional[Path] = Field(
        default=None,
        description="Path to project skills"
    )
    plugin_paths: list[Path] = Field(
        default_factory=list,
        description="Paths to plugin skill directories"
    )

    @classmethod
    def from_environment(cls, project_root: Optional[Path] = None) -> "StorageConfig":
        """Create config from environment and defaults.

        Args:
            project_root: Optional project root path

        Returns:
            StorageConfig with resolved paths
        """
        home = Path.home()

        return cls(
            enterprise_path=home / ".omniforge" / "enterprise" / "skills",
            personal_path=home / ".omniforge" / "skills",
            project_path=project_root / ".omniforge" / "skills" if project_root else None,
            plugin_paths=[],  # Populated by plugin manager
        )


class SkillStorageManager:
    """Manager for skill storage hierarchy.

    Implements the four-layer storage hierarchy:
    1. Enterprise (~/.omniforge/enterprise/skills/) - Highest priority
    2. Personal (~/.omniforge/skills/)
    3. Project (.omniforge/skills/ in project root)
    4. Plugin (installed packages) - Lowest priority
    """

    # Storage layers in priority order (highest first)
    LAYER_ORDER = ["enterprise", "personal", "project", "plugin"]

    def __init__(self, config: StorageConfig) -> None:
        """Initialize storage manager.

        Args:
            config: Storage configuration with paths
        """
        self.config = config

    def get_all_skill_paths(self) -> Iterator[tuple[str, Path]]:
        """Iterate over all SKILL.md files in priority order.

        Yields:
            Tuples of (storage_layer, skill_path)
        """
        # Enterprise layer
        if self.config.enterprise_path and self.config.enterprise_path.exists():
            yield from self._scan_directory("enterprise", self.config.enterprise_path)

        # Personal layer
        if self.config.personal_path and self.config.personal_path.exists():
            yield from self._scan_directory("personal", self.config.personal_path)

        # Project layer
        if self.config.project_path and self.config.project_path.exists():
            yield from self._scan_directory("project", self.config.project_path)

        # Plugin layers
        for plugin_path in self.config.plugin_paths:
            if plugin_path.exists():
                yield from self._scan_directory("plugin", plugin_path)

    def _scan_directory(
        self, layer: str, base_path: Path
    ) -> Iterator[tuple[str, Path]]:
        """Scan a directory for SKILL.md files.

        Args:
            layer: Storage layer name
            base_path: Directory to scan

        Yields:
            Tuples of (layer, skill_md_path)
        """
        for skill_dir in base_path.iterdir():
            if not skill_dir.is_dir():
                continue

            skill_file = skill_dir / "SKILL.md"
            if skill_file.exists():
                yield (layer, skill_file)

    def get_layer_priority(self, layer: str) -> int:
        """Get priority value for a storage layer.

        Higher values = higher priority.
        """
        try:
            # Reverse index so enterprise (index 0) has highest priority
            return len(self.LAYER_ORDER) - self.LAYER_ORDER.index(layer)
        except ValueError:
            return 0
```

### 4. Skill Loader (`src/omniforge/skills/loader.py`)

```python
"""Skill loader with caching and index management."""

import threading
import time
from pathlib import Path
from typing import Dict, Optional

from omniforge.skills.models import Skill, SkillIndexEntry
from omniforge.skills.parser import SkillParser
from omniforge.skills.storage import SkillStorageManager, StorageConfig
from omniforge.skills.errors import SkillNotFoundError


class SkillLoader:
    """Loader for skills with caching and priority resolution.

    Provides:
    - Index building from storage hierarchy
    - Priority-based skill resolution (Enterprise > Personal > Project > Plugin)
    - Caching of parsed skills
    - Thread-safe operations

    Example:
        >>> config = StorageConfig.from_environment(project_root)
        >>> loader = SkillLoader(config)
        >>> loader.build_index()  # Scans all storage layers
        >>>
        >>> # Stage 1: Get skill list for tool description
        >>> skills = loader.list_skills()
        >>>
        >>> # Stage 2: Load full skill on demand
        >>> skill = loader.load_skill("kubernetes-deploy")
    """

    def __init__(
        self,
        config: Optional[StorageConfig] = None,
        cache_ttl_seconds: int = 300,
    ) -> None:
        """Initialize skill loader.

        Args:
            config: Storage configuration (uses defaults if None)
            cache_ttl_seconds: Cache TTL for skill content (default: 5 min)
        """
        self.config = config or StorageConfig.from_environment()
        self.storage = SkillStorageManager(self.config)
        self.parser = SkillParser()

        self._cache_ttl = cache_ttl_seconds
        self._index: Dict[str, SkillIndexEntry] = {}
        self._skill_cache: Dict[str, tuple[Skill, float]] = {}
        self._lock = threading.RLock()
        self._last_index_time: Optional[float] = None

    def build_index(self, force: bool = False) -> int:
        """Build or rebuild the skill index from all storage layers.

        Args:
            force: Force rebuild even if recently built

        Returns:
            Number of skills indexed
        """
        with self._lock:
            # Skip if recently indexed and not forced
            if not force and self._last_index_time:
                if time.time() - self._last_index_time < 60:  # 1 minute cooldown
                    return len(self._index)

            new_index: Dict[str, SkillIndexEntry] = {}

            for layer, skill_path in self.storage.get_all_skill_paths():
                try:
                    # Pass storage layer explicitly to parser (no path-based heuristics)
                    entry = self.parser.parse_metadata(skill_path, storage_layer=layer)

                    # Handle conflicts: higher priority wins
                    if entry.name in new_index:
                        existing = new_index[entry.name]
                        existing_priority = self._get_effective_priority(existing)
                        new_priority = self._get_effective_priority(entry)

                        if new_priority > existing_priority:
                            new_index[entry.name] = entry
                        # else: keep existing (higher priority)
                    else:
                        new_index[entry.name] = entry

                except Exception as e:
                    # Log but don't fail on individual skill parse errors
                    # TODO: Add logging
                    pass

            self._index = new_index
            self._last_index_time = time.time()
            return len(self._index)

    def list_skills(self) -> list[SkillIndexEntry]:
        """List all available skills (Stage 1 data only).

        Returns:
            List of skill index entries sorted by name
        """
        with self._lock:
            return sorted(
                self._index.values(),
                key=lambda s: s.name
            )

    def get_skill_metadata(self, name: str) -> SkillIndexEntry:
        """Get skill metadata by name.

        Args:
            name: Skill name (kebab-case)

        Returns:
            SkillIndexEntry for the skill

        Raises:
            SkillNotFoundError: If skill not found
        """
        with self._lock:
            if name not in self._index:
                raise SkillNotFoundError(name)
            return self._index[name]

    def load_skill(self, name: str) -> Skill:
        """Load complete skill content (Stage 2).

        Args:
            name: Skill name (kebab-case)

        Returns:
            Complete Skill with metadata and content

        Raises:
            SkillNotFoundError: If skill not found
        """
        with self._lock:
            if name not in self._index:
                raise SkillNotFoundError(name)

            entry = self._index[name]

            # Check cache
            if name in self._skill_cache:
                skill, cached_at = self._skill_cache[name]
                if time.time() - cached_at < self._cache_ttl:
                    return skill

            # Load and cache (pass storage_layer explicitly)
            skill = self.parser.parse_full(entry.path, storage_layer=entry.storage_layer)
            self._skill_cache[name] = (skill, time.time())

            return skill

    def has_skill(self, name: str) -> bool:
        """Check if a skill exists in the index."""
        with self._lock:
            return name in self._index

    def invalidate_cache(self, name: Optional[str] = None) -> None:
        """Invalidate skill cache.

        Args:
            name: Specific skill to invalidate, or None for all
        """
        with self._lock:
            if name:
                self._skill_cache.pop(name, None)
            else:
                self._skill_cache.clear()

    def _get_effective_priority(self, entry: SkillIndexEntry) -> int:
        """Calculate effective priority (storage layer + explicit priority)."""
        layer_priority = self.storage.get_layer_priority(entry.storage_layer)
        return (layer_priority * 1000) + entry.priority
```

### 5. Skill Errors (`src/omniforge/skills/errors.py`)

```python
"""Exception hierarchy for skill-related errors."""

from pathlib import Path
from typing import Any, Optional


class SkillError(Exception):
    """Base exception for all skill-related errors."""

    error_code: str = "SKILL_ERROR"

    def __init__(self, message: str, **context: Any) -> None:
        super().__init__(message)
        self.message = message
        self.context = context

    def __str__(self) -> str:
        if not self.context:
            return f"[{self.error_code}] {self.message}"
        context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
        return f"[{self.error_code}] {self.message} ({context_str})"


class SkillNotFoundError(SkillError):
    """Raised when a requested skill is not found."""

    error_code = "SKILL_NOT_FOUND"

    def __init__(self, skill_name: str, **context: Any) -> None:
        message = f"Skill '{skill_name}' not found"
        super().__init__(message, skill_name=skill_name, **context)


class SkillParseError(SkillError):
    """Raised when SKILL.md parsing fails."""

    error_code = "SKILL_PARSE_ERROR"

    def __init__(
        self,
        message: str,
        path: Optional[Path] = None,
        **context: Any
    ) -> None:
        super().__init__(message, path=str(path) if path else None, **context)


class SkillToolNotAllowedError(SkillError):
    """Raised when a tool is not allowed by active skill."""

    error_code = "SKILL_TOOL_NOT_ALLOWED"

    def __init__(
        self,
        tool_name: str,
        skill_name: str,
        allowed_tools: list[str],
        **context: Any
    ) -> None:
        message = (
            f"Tool '{tool_name}' not allowed by skill '{skill_name}'. "
            f"Allowed tools: {', '.join(allowed_tools)}"
        )
        super().__init__(
            message,
            tool_name=tool_name,
            skill_name=skill_name,
            allowed_tools=allowed_tools,
            **context
        )


class SkillActivationError(SkillError):
    """Raised when skill activation fails."""

    error_code = "SKILL_ACTIVATION_ERROR"

    def __init__(
        self,
        skill_name: str,
        reason: str,
        **context: Any
    ) -> None:
        message = f"Failed to activate skill '{skill_name}': {reason}"
        super().__init__(message, skill_name=skill_name, reason=reason, **context)
```

### 6. Skill Context (Tool Restriction) (`src/omniforge/skills/context.py`)

```python
"""Skill execution context for tool restriction enforcement."""

from typing import TYPE_CHECKING, Optional, Set

from omniforge.skills.models import Skill
from omniforge.skills.errors import SkillToolNotAllowedError

if TYPE_CHECKING:
    from omniforge.tools.registry import ToolRegistry


class SkillContext:
    """Context manager for skill-based tool restrictions.

    When a skill is active, this context restricts which tools
    the agent can use based on the skill's allowed-tools list.

    Example:
        >>> skill = loader.load_skill("kubernetes-deploy")
        >>> with SkillContext(skill, tool_registry) as ctx:
        ...     # Only Bash, Read, Write, Glob available
        ...     ctx.check_tool_allowed("bash")  # OK
        ...     ctx.check_tool_allowed("llm")   # Raises SkillToolNotAllowedError
    """

    def __init__(
        self,
        skill: Skill,
        registry: "ToolRegistry",
    ) -> None:
        """Initialize skill context.

        Args:
            skill: Active skill with restrictions
            registry: Tool registry to restrict
        """
        self.skill = skill
        self.registry = registry
        self._original_tools: Optional[Set[str]] = None
        self._allowed_tools: Optional[Set[str]] = None

    def __enter__(self) -> "SkillContext":
        """Enter skill context and apply restrictions."""
        if self.skill.allowed_tools:
            # Normalize tool names to lowercase for comparison
            self._allowed_tools = {
                t.lower() for t in self.skill.allowed_tools
            }
        else:
            # No restrictions - all tools allowed
            self._allowed_tools = None

        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Exit skill context and restore original tools."""
        self._allowed_tools = None
        return False  # Don't suppress exceptions

    def check_tool_allowed(self, tool_name: str) -> None:
        """Check if a tool is allowed by the active skill.

        Args:
            tool_name: Name of tool to check

        Raises:
            SkillToolNotAllowedError: If tool not allowed
        """
        if self._allowed_tools is None:
            # No restrictions active
            return

        if tool_name.lower() not in self._allowed_tools:
            raise SkillToolNotAllowedError(
                tool_name=tool_name,
                skill_name=self.skill.name,
                allowed_tools=list(self._allowed_tools),
            )

    @property
    def is_restricted(self) -> bool:
        """Check if tool restrictions are active."""
        return self._allowed_tools is not None

    @property
    def allowed_tool_names(self) -> Optional[Set[str]]:
        """Get set of allowed tool names (None if unrestricted)."""
        return self._allowed_tools
```

### 7. SkillTool Implementation (`src/omniforge/skills/tool.py`)

```python
"""SkillTool for loading agent skills from SKILL.md files."""

import time
from typing import Any, Optional

from omniforge.tools.base import (
    BaseTool,
    ParameterType,
    ToolCallContext,
    ToolDefinition,
    ToolParameter,
    ToolResult,
)
from omniforge.tools.types import ToolType
from omniforge.skills.loader import SkillLoader
from omniforge.skills.storage import StorageConfig
from omniforge.skills.errors import SkillNotFoundError


class SkillTool(BaseTool):
    """Tool for invoking agent skills from SKILL.md files.

    This tool implements progressive disclosure as per the Claude Code pattern:

    1. **Stage 1 (Discovery)**: Skills list is embedded in the tool description
       dynamically generated from the skill index. Zero context cost.

    2. **Stage 2 (Activation)**: When invoked, returns full SKILL.md content
       with base_path for reference doc resolution.

    3. **Stage 3 (Reference)**: Agent uses Read/Bash tools with base_path
       to access docs and execute scripts.

    Example:
        >>> loader = SkillLoader(config)
        >>> loader.build_index()
        >>> tool = SkillTool(loader)
        >>>
        >>> # Tool description contains available skills
        >>> print(tool.definition.description)  # Shows <available_skills>
        >>>
        >>> # Invoke skill
        >>> result = await tool.execute(
        ...     arguments={"skill_name": "kubernetes-deploy"},
        ...     context=context
        ... )
        >>> print(result.result["content"])  # Full SKILL.md content
    """

    def __init__(
        self,
        skill_loader: SkillLoader,
        timeout_ms: int = 30000,
    ) -> None:
        """Initialize SkillTool.

        Args:
            skill_loader: Loader with built index
            timeout_ms: Timeout for skill loading
        """
        self._loader = skill_loader
        self._timeout_ms = timeout_ms

    @property
    def definition(self) -> ToolDefinition:
        """Get tool definition with dynamic skill list.

        The description is regenerated each time to reflect
        the current skill index. This enables hot reload.
        """
        return ToolDefinition(
            name="skill",
            type=ToolType.SKILL,
            description=self._build_description(),
            parameters=[
                ToolParameter(
                    name="skill_name",
                    type=ParameterType.STRING,
                    description="Name of the skill to invoke (from available_skills)",
                    required=True,
                ),
                ToolParameter(
                    name="args",
                    type=ParameterType.STRING,
                    description="Optional arguments to pass to the skill",
                    required=False,
                ),
            ],
            timeout_ms=self._timeout_ms,
        )

    def _build_description(self) -> str:
        """Build tool description with available skills list."""
        skills = self._loader.list_skills()

        # Build skills list in Claude Code format
        if skills:
            skills_section = "\n".join(
                f'"{s.name}": {s.description}'
                for s in skills
            )
        else:
            skills_section = "(No skills currently available)"

        return f'''Execute specialized skills within the conversation.

When users request task execution or you identify a relevant capability, invoke this tool with the skill name.

## How to Invoke Skills

Use the tool with the skill name:
- skill_name: "commit-message" - basic invocation
- skill_name: "code-review", args: "pr-123" - with arguments

## Available Skills

The following skills are available:

<available_skills>
{skills_section}
</available_skills>

## Important Requirements

- IMMEDIATELY invoke this tool as your first action when a skill is relevant
- NEVER just announce a skill without calling the tool
- Only use skills listed in <available_skills> above
- Don't invoke already-running skills
- Don't use this tool for built-in CLI commands

## What Happens When You Invoke

When you invoke a skill:
1. You receive the skill's base_path and full content
2. Follow the skill's instructions precisely
3. The skill may include tool restrictions (allowed-tools)
4. Use base_path to resolve relative paths in the skill content'''

    async def execute(
        self,
        arguments: dict[str, Any],
        context: ToolCallContext,
    ) -> ToolResult:
        """Execute skill invocation (Stage 2 loading).

        Args:
            arguments: Tool arguments with skill_name and optional args
            context: Execution context

        Returns:
            ToolResult with skill content, base_path, and metadata
        """
        start_time = time.time()

        # Extract arguments
        skill_name = arguments.get("skill_name", "").strip()
        skill_args = arguments.get("args", "")

        # Validate skill name
        if not skill_name:
            return ToolResult(
                success=False,
                error="skill_name is required",
                duration_ms=int((time.time() - start_time) * 1000),
            )

        try:
            # Load full skill (Stage 2)
            skill = self._loader.load_skill(skill_name)

            duration_ms = int((time.time() - start_time) * 1000)

            # Return skill content with base_path for navigation
            return ToolResult(
                success=True,
                result={
                    "skill_name": skill.name,
                    "base_path": str(skill.base_path),
                    "content": skill.content,
                    "allowed_tools": skill.allowed_tools,
                    "args": skill_args,
                },
                duration_ms=duration_ms,
            )

        except SkillNotFoundError as e:
            duration_ms = int((time.time() - start_time) * 1000)

            # Suggest similar skills
            available = [s.name for s in self._loader.list_skills()]
            suggestion = self._find_similar(skill_name, available)

            error_msg = f"Skill '{skill_name}' not found."
            if suggestion:
                error_msg += f" Did you mean '{suggestion}'?"

            return ToolResult(
                success=False,
                error=error_msg,
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return ToolResult(
                success=False,
                error=f"Failed to load skill: {str(e)}",
                duration_ms=duration_ms,
            )

    def _find_similar(
        self, name: str, available: list[str], threshold: float = 0.6
    ) -> Optional[str]:
        """Find similar skill name using basic string matching."""
        name_lower = name.lower()

        for skill in available:
            skill_lower = skill.lower()
            # Simple substring matching
            if name_lower in skill_lower or skill_lower in name_lower:
                return skill

        return None
```

---

## Integration Points

### 1. System Prompt Injection

Add skill navigation instructions to the agent's system prompt in `src/omniforge/agents/cot/prompts.py`:

```python
SKILL_NAVIGATION_INSTRUCTIONS = '''
## Skill Navigation Instructions

When a skill is loaded, you receive:
- skill_name: The skill identifier
- base_path: Full path to the skill directory
- content: The SKILL.md markdown content

### Loading Reference Documents

When you see markdown links in the skill content:
```
For advanced features, see [reference.md](reference.md)
```

**Action**: Use the Read tool with: `{base_path}/reference.md`
- Resolve relative paths using the base_path
- Load content only when you need the information

### Executing Scripts

When you see bash code blocks with commands:
```
Run the validation script:
```bash
python scripts/validate.py input.txt
```
```

**Action**: Use the Bash tool with the command, resolving paths:
- Command: `python {base_path}/scripts/validate.py input.txt`
- **IMPORTANT**: Execute the script, don't load its contents into context
- Only the script's output will be visible to you

### Path Resolution Rules

- Relative paths (e.g., `reference.md`) -> `{base_path}/{relative_path}`
- Absolute paths (e.g., `/etc/config`) -> Use as-is
- URLs (e.g., `https://...`) -> Use as-is
'''


def build_react_system_prompt(tools: list[ToolDefinition]) -> str:
    """Build complete ReAct system prompt with tool and skill navigation."""
    # ... existing code ...

    # Add skill navigation section
    prompt += "\n\n" + SKILL_NAVIGATION_INSTRUCTIONS

    return prompt
```

### 2. Tool Executor Integration

Modify `ToolExecutor` in `src/omniforge/tools/executor.py` to enforce skill restrictions:

```python
class ToolExecutor:
    """Tool executor with skill-aware tool restriction."""

    def __init__(
        self,
        registry: ToolRegistry,
        rate_limiter: Optional[RateLimiter] = None,
        cost_tracker: Optional[CostTracker] = None,
    ) -> None:
        self._registry = registry
        self._rate_limiter = rate_limiter
        self._cost_tracker = cost_tracker
        self._active_skill_context: Optional[SkillContext] = None

    def set_active_skill(self, context: Optional[SkillContext]) -> None:
        """Set active skill context for tool restriction."""
        self._active_skill_context = context

    async def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        context: ToolCallContext,
        chain: ReasoningChain,
    ) -> ToolResult:
        """Execute tool with skill restriction check."""
        # Check skill restrictions first
        if self._active_skill_context:
            try:
                self._active_skill_context.check_tool_allowed(tool_name)
            except SkillToolNotAllowedError as e:
                # Return error result without executing
                return ToolResult(
                    success=False,
                    error=str(e),
                    duration_ms=0,
                )

        # ... rest of existing execute logic ...
```

### 3. FunctionTool Rename Strategy

**Phase 1: Add Aliases (Non-breaking)**

```python
# src/omniforge/tools/builtin/function.py (new file)
"""Function invocation tool (renamed from SkillTool)."""

# Re-export with new names
from omniforge.tools.builtin.skill import (
    SkillDefinition as FunctionDefinition,
    SkillRegistry as FunctionRegistry,
    SkillTool as FunctionTool,
    skill as function,
)

__all__ = [
    "FunctionDefinition",
    "FunctionRegistry",
    "FunctionTool",
    "function",
]
```

```python
# src/omniforge/tools/builtin/skill.py - Add deprecation warnings
import warnings

class SkillTool(BaseTool):
    """DEPRECATED: Use FunctionTool instead.

    This class has been renamed to FunctionTool to distinguish
    internal Python functions from external SKILL.md skills.
    """

    def __init__(self, *args, **kwargs):
        warnings.warn(
            "SkillTool is deprecated, use FunctionTool instead",
            DeprecationWarning,
            stacklevel=2
        )
        super().__init__(*args, **kwargs)
```

**Phase 2: Update Imports (v2.0)**

- Update `builtin/__init__.py` to export new names
- Update all internal usages to use `FunctionTool`
- Keep deprecated aliases for one minor version

**Phase 3: Remove Deprecated Names (v3.0)**

- Remove `SkillTool`, `SkillRegistry`, `SkillDefinition` from `skill.py`
- Remove the deprecated module entirely

---

## Multi-LLM Compatibility Strategy

### Problem Statement

The product specification requires the skills system to work with multiple LLMs (Claude, GPT-4, Gemini, etc.), not just Claude. While Claude can implicitly understand path resolution patterns from context, other LLMs require **explicit instructions** with concrete examples.

**Risk**: Skills work perfectly with Claude but fail with GPT-4 because the agent doesn't understand how to resolve `{base_path}/reference.md` into an absolute path.

### Solution: Enhanced System Prompt Instructions

**1. Explicit Path Resolution Examples**

Add concrete examples to the system prompt showing exact path construction:

```python
MULTI_LLM_PATH_RESOLUTION = '''
## Path Resolution for Skills

When working with skills, you receive a `base_path` in the ToolResult. Use it to resolve all relative paths:

**Example 1: Loading Reference Documents**
```
ToolResult: {
  "skill_name": "kubernetes-deploy",
  "base_path": "/home/user/.claude/skills/kubernetes-deploy",
  "content": "See [advanced.md](advanced.md) for details"
}
```

Action: Use Read tool with path: `/home/user/.claude/skills/kubernetes-deploy/advanced.md`

Construction: `{base_path}/{relative_path}` = `/home/user/.claude/skills/kubernetes-deploy/advanced.md`

**Example 2: Executing Scripts**
```
ToolResult: {
  "skill_name": "pdf-processing",
  "base_path": "/project/.claude/skills/pdf-processing",
  "content": "Run: ```bash\\npython scripts/extract.py input.pdf\\n```"
}
```

Action: Use Bash tool with command: `cd /project/.claude/skills/pdf-processing && python scripts/extract.py input.pdf`

Construction: `cd {base_path} && {command}`

**Example 3: Nested Paths**
```
For path: `docs/api/reference.md` in skill at `/skills/my-skill`
Read tool argument: `/skills/my-skill/docs/api/reference.md`
```

**Path Resolution Rules (in order of precedence):**
1. Absolute paths (start with `/` or drive letter) → Use as-is
2. URLs (start with `http://` or `https://`) → Use as-is
3. Relative paths → Prepend `{base_path}/`
'''
```

**2. Script Execution Patterns**

Add explicit guidance on executing scripts without loading content:

```python
SCRIPT_EXECUTION_INSTRUCTIONS = '''
## Script Execution (CRITICAL for Context Efficiency)

**NEVER load script contents with Read tool**. Always execute via Bash.

✅ CORRECT: Execute script
```
Bash tool: "cd /skills/my-skill && python scripts/validate.py data.csv"
```

❌ WRONG: Read script contents
```
Read tool: "/skills/my-skill/scripts/validate.py"  # Wastes 5000+ tokens!
```

**Why**: Script files can be 500+ lines. Executing them consumes only ~100 tokens (for output), while reading them wastes 5000+ tokens for content you don't need.

**Detection**: If you see bash code blocks or references to `/scripts/` directory, ALWAYS execute, NEVER read.
'''
```

**3. Tool Calling Format Examples**

Add concrete examples of tool invocation structure:

```python
TOOL_CALLING_EXAMPLES = '''
## Tool Calling Format for Skills

When a skill instructs you to use a tool, format your request exactly like this:

**Read Tool Example:**
```json
{
  "tool": "Read",
  "arguments": {
    "file_path": "/absolute/path/to/file.md"
  }
}
```

**Bash Tool Example:**
```json
{
  "tool": "Bash",
  "arguments": {
    "command": "cd /skill/base/path && python script.py"
  }
}
```

**Skill Tool Example (invoking another skill):**
```json
{
  "tool": "Skill",
  "arguments": {
    "skill_name": "kubernetes-deploy"
  }
}
```
'''
```

### Multi-LLM Testing Requirements

**Phase 1 (Foundation) Testing:**

Before proceeding to Phase 2, validate that skill navigation works correctly across:

1. **Claude Opus 4.5** (reference implementation)
   - Test: Load skill, read reference doc, execute script
   - Success criteria: Correctly resolves all paths without errors

2. **GPT-4 Turbo** (primary alternative)
   - Test: Same skill navigation flow as Claude
   - Success criteria: Correctly resolves paths with system prompt guidance
   - Focus: Validate path construction patterns work without implicit understanding

3. **Gemini 1.5 Pro** (secondary alternative)
   - Test: Same skill navigation flow
   - Success criteria: Correctly resolves paths and executes scripts
   - Focus: Validate tool calling format compatibility

**Test Cases:**

```python
# tests/skills/test_multi_llm_compatibility.py
import pytest
from omniforge.skills import SkillLoader, SkillTool
from omniforge.llm import LLMClient


@pytest.mark.parametrize("model", [
    "claude-opus-4-5-20251101",
    "gpt-4-turbo-2024-04-09",
    "gemini-1.5-pro-latest",
])
async def test_skill_navigation_cross_llm(model: str, skill_directory):
    """Test that skill navigation works across different LLMs."""
    # Setup skill system
    loader = SkillLoader(skill_directory)
    skill_tool = SkillTool(loader)

    # Create agent with specific LLM
    agent = create_agent(model=model, tools=[skill_tool, ReadTool(), BashTool()])

    # Task: Load skill, read reference doc, execute script
    result = await agent.execute(
        "Use the pdf-processing skill to extract text from sample.pdf"
    )

    # Verify agent correctly:
    # 1. Invoked SkillTool with skill_name="pdf-processing"
    # 2. Read reference docs using base_path
    # 3. Executed script without reading script file
    # 4. Completed task successfully

    assert result.success
    assert_used_tool(result, "Skill", arguments={"skill_name": "pdf-processing"})
    assert_did_not_read_script_files(result)  # Critical check
    assert_executed_script_via_bash(result)   # Critical check
```

### Monitoring and Validation

**Production Monitoring:**

Track skill execution patterns to detect multi-LLM compatibility issues:

```python
# Metrics to track:
- skill_path_resolution_failures (by LLM model)
- script_read_attempts (anti-pattern detection)
- tool_restriction_violations (by LLM model)
- average_tokens_per_skill_execution (by LLM model)
```

**Success Criteria:**

- All supported LLMs achieve < 5% path resolution error rate
- Zero instances of agents reading script files instead of executing
- Token consumption within 20% across different LLMs for same task

---

## Script Execution Enforcement Mechanism

### Problem Statement

The current design states "scripts are executed, never loaded" but provides no enforcement. An agent could use Read tool on script files, wasting thousands of tokens and defeating the purpose of the script execution model.

**Risk**: An agent reads a 500-line `scripts/deploy.sh` (consuming 5000+ tokens) instead of executing it (consuming ~100 tokens for output).

### Solution: Script Path Detection and Enforcement

**1. Track Script Paths in Skill Model**

Update the `Skill` model to explicitly track script files:

```python
# src/omniforge/skills/models.py

class Skill(BaseModel):
    """Complete skill definition including content."""

    metadata: SkillMetadata
    content: str
    path: Path
    base_path: Path
    storage_layer: str
    script_paths: list[Path] = Field(
        default_factory=list,
        description="List of executable script files in this skill"
    )

    @property
    def is_script_file(self, file_path: Path) -> bool:
        """Check if a path is a script file in this skill."""
        abs_path = file_path.resolve()
        return any(
            abs_path == script_path.resolve()
            for script_path in self.script_paths
        )
```

**2. Auto-Detect Scripts During Parsing**

Update `SkillParser` to identify script files:

```python
# src/omniforge/skills/parser.py

class SkillParser:
    """Parser for SKILL.md files with YAML frontmatter."""

    SCRIPT_EXTENSIONS = {".sh", ".py", ".rb", ".js", ".ts", ".pl"}
    SCRIPT_DIRS = {"scripts", "bin", "tools"}

    def parse_full(self, path: Path) -> Skill:
        """Parse complete SKILL.md file with script detection."""
        # ... existing parsing logic ...

        # Detect script files
        script_paths = self._detect_script_files(path.parent)

        return Skill(
            metadata=metadata,
            content=body.strip(),
            path=path,
            base_path=path.parent,
            storage_layer=self._determine_storage_layer(path),
            script_paths=script_paths,
        )

    def _detect_script_files(self, base_path: Path) -> list[Path]:
        """Detect executable script files in skill directory."""
        script_files = []

        # Check common script directories
        for script_dir in self.SCRIPT_DIRS:
            dir_path = base_path / script_dir
            if dir_path.is_dir():
                for file_path in dir_path.rglob("*"):
                    if file_path.suffix in self.SCRIPT_EXTENSIONS:
                        script_files.append(file_path)

        return script_files
```

**3. Enforce in SkillContext**

Update `SkillContext` to intercept Read tool calls on scripts:

```python
# src/omniforge/skills/context.py

class SkillContext:
    """Context manager with script execution enforcement."""

    def __init__(
        self,
        skill: Skill,
        executor: "ToolExecutor",  # Need reference to executor
    ) -> None:
        self.skill = skill
        self.executor = executor
        self._original_tools: Optional[Set[str]] = None
        self._allowed_tools: Optional[Set[str]] = None

    def check_tool_arguments(
        self,
        tool_name: str,
        arguments: dict[str, Any]
    ) -> None:
        """Validate tool arguments against skill rules.

        Raises:
            SkillScriptReadError: If attempting to read a script file
        """
        # Check if Read tool is being used on a script file
        if tool_name.lower() == "read":
            file_path = arguments.get("file_path")
            if file_path:
                path_obj = Path(file_path)

                # Check if this is a script file in the active skill
                if self.skill.is_script_file(path_obj):
                    raise SkillScriptReadError(
                        f"Cannot read script file '{file_path}' during skill execution. "
                        f"Script files must be EXECUTED via Bash tool, not read. "
                        f"Use: Bash tool with command 'cd {self.skill.base_path} && ...'"
                    )
```

**4. Update ToolExecutor Integration**

Modify executor to check arguments before execution:

```python
# src/omniforge/tools/executor.py

class ToolExecutor:
    """Tool executor with skill-aware enforcement."""

    async def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        context: ToolCallContext,
        chain: ReasoningChain,
    ) -> ToolResult:
        """Execute tool with skill restriction and argument checks."""
        # Check skill restrictions
        if self._active_skill_context:
            try:
                # Check if tool is allowed
                self._active_skill_context.check_tool_allowed(tool_name)

                # Check if arguments violate skill rules (e.g., reading scripts)
                self._active_skill_context.check_tool_arguments(tool_name, arguments)

            except (SkillToolNotAllowedError, SkillScriptReadError) as e:
                # Return error result without executing
                return ToolResult(
                    success=False,
                    error=str(e),
                    duration_ms=0,
                )

        # ... rest of existing execute logic ...
```

**5. Add Clear Error Messages**

Create helpful error messages that guide agents to correct behavior:

```python
# src/omniforge/skills/errors.py

class SkillScriptReadError(SkillError):
    """Raised when agent attempts to read a script file instead of executing it."""

    def __init__(self, message: str, script_path: Path, skill_name: str):
        super().__init__(message)
        self.script_path = script_path
        self.skill_name = skill_name

    def __str__(self) -> str:
        return (
            f"{self.message}\n\n"
            f"Script: {self.script_path}\n"
            f"Skill: {self.skill_name}\n\n"
            f"✅ CORRECT: Use Bash tool to execute the script\n"
            f"❌ WRONG: Use Read tool to load script contents\n\n"
            f"Scripts are designed to be executed, not read. This saves context tokens."
        )
```

### Testing

Add tests to verify enforcement:

```python
# tests/skills/test_script_enforcement.py

def test_read_script_file_blocked(skill_loader, skill_context):
    """Test that reading script files is blocked during skill execution."""
    skill = skill_loader.load_skill("pdf-processing")

    with skill_context(skill):
        # Attempt to read a script file
        with pytest.raises(SkillScriptReadError) as exc:
            read_tool.execute(
                arguments={"file_path": str(skill.base_path / "scripts" / "extract.py")},
                context=tool_context,
            )

        assert "must be EXECUTED via Bash tool" in str(exc.value)
        assert "extract.py" in str(exc.value)

def test_execute_script_allowed(skill_loader, skill_context):
    """Test that executing scripts via Bash is allowed."""
    skill = skill_loader.load_skill("pdf-processing")

    with skill_context(skill):
        # Execute script via Bash
        result = bash_tool.execute(
            arguments={
                "command": f"cd {skill.base_path} && python scripts/extract.py test.pdf"
            },
            context=tool_context,
        )

        assert result.success  # Should work fine
```

### Monitoring

Track anti-pattern attempts:

```python
# Metrics:
- script_read_attempts_blocked (count)
- script_read_attempts_by_llm_model (breakdown)
- script_execution_success_rate (%)
```

---

## Enhanced Tool Restriction Security

### Problem Statement

The current `SkillContext` uses Python's context manager (`__enter__`/`__exit__`) to manage tool restrictions. However, this approach has a critical security flaw: if an exception occurs or the agent manipulates conversation flow, tool restrictions might not persist throughout the entire skill execution lifecycle.

**Risk**: An agent could invoke a skill with tool restrictions, trigger an exception, and then use unrestricted tools while still nominally "executing" the skill.

### Solution: Persistent Skill Context with Stack-Based Tracking

**1. Executor-Level Skill Stack**

Replace context manager with persistent state in the executor:

```python
# src/omniforge/tools/executor.py

class ToolExecutor:
    """Tool executor with persistent skill context stack."""

    def __init__(
        self,
        registry: ToolRegistry,
        rate_limiter: Optional[RateLimiter] = None,
        cost_tracker: Optional[CostTracker] = None,
    ) -> None:
        self._registry = registry
        self._rate_limiter = rate_limiter
        self._cost_tracker = cost_tracker
        self._skill_stack: list[Skill] = []  # Stack of active skills
        self._skill_contexts: dict[str, SkillContext] = {}  # skill_name -> context

    @property
    def active_skill(self) -> Optional[Skill]:
        """Get currently active skill (top of stack)."""
        return self._skill_stack[-1] if self._skill_stack else None

    def activate_skill(self, skill: Skill) -> None:
        """Activate a skill with tool restrictions.

        Args:
            skill: Skill to activate

        Raises:
            SkillError: If skill is already active
        """
        if skill.name in self._skill_contexts:
            raise SkillError(f"Skill '{skill.name}' is already active")

        # Create context and push to stack
        context = SkillContext(skill=skill, executor=self)
        self._skill_stack.append(skill)
        self._skill_contexts[skill.name] = context

        # Log activation for audit
        logger.info(
            f"Activated skill '{skill.name}' with restrictions: "
            f"{skill.allowed_tools or 'all tools allowed'}"
        )

    def deactivate_skill(self, skill_name: str) -> None:
        """Deactivate a skill and remove restrictions.

        Args:
            skill_name: Name of skill to deactivate

        Raises:
            SkillError: If skill is not active or not at top of stack
        """
        if not self._skill_stack:
            raise SkillError("No active skills to deactivate")

        # Enforce stack discipline - can only deactivate top of stack
        if self._skill_stack[-1].name != skill_name:
            raise SkillError(
                f"Cannot deactivate '{skill_name}' - "
                f"'{self._skill_stack[-1].name}' must be deactivated first"
            )

        # Pop from stack and remove context
        self._skill_stack.pop()
        context = self._skill_contexts.pop(skill_name)

        # Log deactivation for audit
        logger.info(f"Deactivated skill '{skill_name}'")

    async def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        context: ToolCallContext,
        chain: ReasoningChain,
    ) -> ToolResult:
        """Execute tool with skill restriction checks."""
        start_time = time.time()

        # Check skill restrictions if any skill is active
        if self.active_skill:
            skill_context = self._skill_contexts[self.active_skill.name]

            try:
                # Validate tool is allowed
                skill_context.check_tool_allowed(tool_name)

                # Validate arguments (e.g., no reading scripts)
                skill_context.check_tool_arguments(tool_name, arguments)

            except (SkillToolNotAllowedError, SkillScriptReadError) as e:
                # Log violation attempt
                logger.warning(
                    f"Tool restriction violated in skill '{self.active_skill.name}': "
                    f"Attempted to use '{tool_name}' but not allowed. "
                    f"Error: {e}"
                )

                return ToolResult(
                    success=False,
                    error=str(e),
                    duration_ms=int((time.time() - start_time) * 1000),
                )

        # ... rest of existing execute logic ...

        # Log tool execution during skill context
        if self.active_skill:
            logger.debug(
                f"Executed '{tool_name}' in skill '{self.active_skill.name}' context"
            )
```

**2. Update SkillTool to Use Explicit Activation**

Modify `SkillTool` to explicitly activate/deactivate skills:

```python
# src/omniforge/skills/tool.py

class SkillTool(BaseTool):
    """Tool for loading and activating agent skills."""

    def __init__(
        self,
        skill_loader: SkillLoader,
        tool_executor: ToolExecutor,
    ) -> None:
        self._skill_loader = skill_loader
        self._executor = tool_executor
        self._active_skills: dict[str, Skill] = {}  # Track loaded skills

    async def execute(
        self, arguments: dict[str, Any], context: ToolCallContext
    ) -> ToolResult:
        """Execute skill loading and activation."""
        start_time = time.time()

        skill_name = arguments.get("skill_name", "").strip()
        action = arguments.get("action", "activate")  # activate | deactivate

        if not skill_name:
            return ToolResult(
                success=False,
                error="skill_name is required",
                duration_ms=int((time.time() - start_time) * 1000),
            )

        try:
            if action == "activate":
                # Load skill if not already loaded
                if skill_name not in self._active_skills:
                    skill = self._skill_loader.load_skill(skill_name)
                    self._active_skills[skill_name] = skill
                else:
                    skill = self._active_skills[skill_name]

                # Activate skill in executor
                self._executor.activate_skill(skill)

                # Return skill content
                return ToolResult(
                    success=True,
                    result={
                        "skill_name": skill.name,
                        "base_path": str(skill.base_path),
                        "content": skill.content,
                        "allowed_tools": skill.allowed_tools,
                        "status": "activated",
                    },
                    duration_ms=int((time.time() - start_time) * 1000),
                )

            elif action == "deactivate":
                # Deactivate skill in executor
                self._executor.deactivate_skill(skill_name)

                # Remove from active skills
                self._active_skills.pop(skill_name, None)

                return ToolResult(
                    success=True,
                    result={
                        "skill_name": skill_name,
                        "status": "deactivated",
                    },
                    duration_ms=int((time.time() - start_time) * 1000),
                )

            else:
                return ToolResult(
                    success=False,
                    error=f"Unknown action '{action}'. Use 'activate' or 'deactivate'.",
                    duration_ms=int((time.time() - start_time) * 1000),
                )

        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Skill {action} failed: {str(e)}",
                duration_ms=int((time.time() - start_time) * 1000),
            )
```

**3. Add Automatic Deactivation on Task Completion**

Ensure skills are deactivated when tasks complete:

```python
# src/omniforge/orchestration/task_executor.py

class TaskExecutor:
    """Task executor with automatic skill cleanup."""

    async def execute_task(
        self,
        task: Task,
        agent: Agent,
        context: ExecutionContext,
    ) -> TaskResult:
        """Execute task with automatic skill deactivation."""
        try:
            # Execute task
            result = await agent.execute(task, context)

            return result

        finally:
            # Deactivate all skills on task completion
            while agent.tool_executor.active_skill:
                skill_name = agent.tool_executor.active_skill.name
                agent.tool_executor.deactivate_skill(skill_name)
                logger.info(
                    f"Auto-deactivated skill '{skill_name}' on task completion"
                )
```

**4. Add Audit Logging**

Track all skill activations and deactivations:

```python
# Audit log format:
{
  "timestamp": "2026-01-13T10:30:00Z",
  "event": "skill_activated",
  "skill_name": "kubernetes-deploy",
  "agent_id": "agent-123",
  "task_id": "task-456",
  "tenant_id": "tenant-789",
  "allowed_tools": ["Bash", "Read", "Write"],
  "correlation_id": "corr-abc"
}

{
  "timestamp": "2026-01-13T10:30:45Z",
  "event": "tool_execution_in_skill",
  "skill_name": "kubernetes-deploy",
  "tool_name": "Bash",
  "tool_allowed": true,
  "correlation_id": "corr-abc"
}

{
  "timestamp": "2026-01-13T10:31:00Z",
  "event": "tool_restriction_violated",
  "skill_name": "kubernetes-deploy",
  "tool_name": "LLM",
  "tool_allowed": false,
  "error": "Tool 'LLM' not in allowed-tools list",
  "correlation_id": "corr-abc"
}

{
  "timestamp": "2026-01-13T10:32:00Z",
  "event": "skill_deactivated",
  "skill_name": "kubernetes-deploy",
  "duration_seconds": 120,
  "correlation_id": "corr-abc"
}
```

### Testing

Add comprehensive security tests:

```python
# tests/skills/test_tool_restriction_security.py

async def test_skill_restriction_survives_exception(executor, skill_tool):
    """Test that tool restrictions persist even if exception occurs."""
    skill = await skill_tool.execute(
        arguments={"skill_name": "kubernetes-deploy", "action": "activate"},
        context=test_context,
    )

    assert executor.active_skill.name == "kubernetes-deploy"
    assert executor.active_skill.allowed_tools == ["Bash", "Read", "Write"]

    # Simulate exception during tool execution
    with pytest.raises(ValueError):
        await executor.execute(
            tool_name="Bash",
            arguments={"command": "invalid command that raises exception"},
            context=test_context,
            chain=test_chain,
        )

    # Verify skill restrictions still active
    assert executor.active_skill.name == "kubernetes-deploy"

    # Verify restricted tool still blocked
    result = await executor.execute(
        tool_name="LLM",  # Not in allowed-tools
        arguments={"prompt": "test"},
        context=test_context,
        chain=test_chain,
    )

    assert not result.success
    assert "not in allowed-tools" in result.error

async def test_nested_skill_activation_blocked(executor, skill_tool):
    """Test that nested skill activation is properly handled."""
    # Activate first skill
    await skill_tool.execute(
        arguments={"skill_name": "skill-a", "action": "activate"},
        context=test_context,
    )

    # Attempt to activate second skill (should work - stack-based)
    await skill_tool.execute(
        arguments={"skill_name": "skill-b", "action": "activate"},
        context=test_context,
    )

    # Verify stack order
    assert executor.active_skill.name == "skill-b"
    assert len(executor._skill_stack) == 2

    # Must deactivate in reverse order
    with pytest.raises(SkillError, match="must be deactivated first"):
        executor.deactivate_skill("skill-a")  # Cannot skip skill-b

    # Deactivate correctly
    executor.deactivate_skill("skill-b")
    assert executor.active_skill.name == "skill-a"

    executor.deactivate_skill("skill-a")
    assert executor.active_skill is None

async def test_auto_deactivation_on_task_completion(task_executor):
    """Test that skills are auto-deactivated when task completes."""
    task = Task(id="test-task", description="Test task")
    agent = create_agent_with_skills()

    # Activate skill during task execution
    await agent.invoke_tool(
        "Skill",
        {"skill_name": "kubernetes-deploy", "action": "activate"}
    )

    # Complete task
    result = await task_executor.execute_task(task, agent, execution_context)

    # Verify skill was auto-deactivated
    assert agent.tool_executor.active_skill is None
    assert len(agent.tool_executor._skill_stack) == 0
```

### Security Benefits

1. **Exception-Safe**: Tool restrictions persist even if exceptions occur
2. **Stack-Based**: Supports nested skill contexts with proper lifecycle management
3. **Audit Trail**: Every skill activation, tool execution, and violation is logged
4. **Explicit Deactivation**: Skills must be explicitly deactivated, preventing lingering restrictions
5. **Automatic Cleanup**: Task completion auto-deactivates all skills
6. **Enforcement at Executor**: Single point of enforcement, cannot be bypassed

---

## Testing Strategy

### Unit Tests

```
tests/skills/
  __init__.py
  test_models.py         # Skill, SkillMetadata, SkillIndexEntry
  test_parser.py         # SkillParser (frontmatter extraction, validation)
  test_storage.py        # SkillStorageManager (path scanning, priorities)
  test_loader.py         # SkillLoader (indexing, caching, loading)
  test_context.py        # SkillContext (tool restrictions)
  test_tool.py           # SkillTool (execute, description generation)
  test_errors.py         # Custom exceptions
  conftest.py            # Shared fixtures (temp skill directories, etc.)
```

### Test Fixtures

```python
# tests/skills/conftest.py
import pytest
from pathlib import Path
import tempfile


@pytest.fixture
def skill_directory(tmp_path: Path) -> Path:
    """Create a temporary skill directory structure."""
    # Enterprise skill
    enterprise = tmp_path / ".omniforge" / "enterprise" / "skills" / "deploy"
    enterprise.mkdir(parents=True)
    (enterprise / "SKILL.md").write_text('''---
name: deploy
description: Deploy applications to production
allowed-tools:
  - Bash
  - Read
---

# Deploy Skill

Instructions for deployment...
''')

    # Project skill (lower priority, same name)
    project = tmp_path / ".omniforge" / "skills" / "deploy"
    project.mkdir(parents=True)
    (project / "SKILL.md").write_text('''---
name: deploy
description: Project-specific deployment
---

# Project Deploy

Overridden by enterprise...
''')

    return tmp_path


@pytest.fixture
def skill_loader(skill_directory: Path) -> SkillLoader:
    """Create skill loader with test configuration."""
    config = StorageConfig(
        enterprise_path=skill_directory / ".omniforge" / "enterprise" / "skills",
        project_path=skill_directory / ".omniforge" / "skills",
    )
    loader = SkillLoader(config)
    loader.build_index()
    return loader
```

### Key Test Cases

1. **Parser Tests**
   - Valid YAML frontmatter extraction
   - Invalid YAML handling
   - Missing frontmatter detection
   - All metadata fields parsed correctly
   - Kebab-case name validation

2. **Storage Tests**
   - Directory scanning finds SKILL.md files
   - Ignores non-directory entries
   - Handles missing directories gracefully
   - Layer priority ordering

3. **Loader Tests**
   - Index building from multiple layers
   - Priority resolution (enterprise > project)
   - Skill caching and TTL expiration
   - Thread safety of index operations
   - Not found errors

4. **Context Tests**
   - Tool restriction enforcement
   - Case-insensitive tool matching
   - No restrictions when allowed_tools is None
   - Context manager cleanup

5. **Tool Tests**
   - Dynamic description generation
   - Successful skill loading
   - Not found with suggestions
   - Base path in result

### Integration Tests

```python
# tests/integration/test_skill_execution.py
"""Integration tests for skill execution flow."""

@pytest.mark.asyncio
async def test_skill_tool_restriction_enforcement():
    """Test that tool restrictions are enforced during skill execution."""
    # Setup: Create skill with restricted tools
    # Execute: Try to use disallowed tool
    # Assert: SkillToolNotAllowedError raised
```

### Performance Benchmarks

```python
# tests/benchmarks/test_skill_performance.py
"""Performance benchmarks for skill system."""

def test_index_build_performance(benchmark, large_skill_directory):
    """Benchmark: Index 1000 skills in < 100ms."""
    loader = SkillLoader(config)
    result = benchmark(loader.build_index)
    assert result < 0.1  # 100ms


def test_skill_load_performance(benchmark, skill_loader):
    """Benchmark: Load skill in < 50ms."""
    result = benchmark(lambda: skill_loader.load_skill("test-skill"))
    assert result < 0.05  # 50ms
```

---

## Migration/Deployment Approach

### Phase 1: Foundation (Week 1-2)

1. **Create skills module structure**
   ```
   src/omniforge/skills/
     __init__.py
     models.py
     errors.py
     parser.py
     storage.py
     loader.py
   ```

2. **Implement core models and parser**
   - Skill, SkillMetadata, SkillIndexEntry models
   - SkillParser with frontmatter extraction
   - Unit tests for all models

3. **Implement storage manager**
   - StorageConfig for path configuration
   - Directory scanning
   - Layer priority

### Phase 2: Loader and Caching (Week 2-3)

1. **Implement SkillLoader**
   - Index building from storage
   - Priority-based resolution
   - Skill caching with TTL
   - Thread safety

2. **Add tests**
   - Loader unit tests
   - Integration tests with filesystem

### Phase 3: SkillTool (Week 3-4)

1. **Implement SkillTool**
   - Dynamic description with skills list
   - Execute for skill loading
   - Error handling with suggestions

2. **Implement SkillContext**
   - Tool restriction enforcement
   - Context manager pattern

3. **Integration with ToolExecutor**
   - Add active_skill_context
   - Restriction checking

### Phase 4: Rename and Integration (Week 4-5)

1. **Rename existing SkillTool -> FunctionTool**
   - Create function.py with new names
   - Add deprecation warnings
   - Update __init__.py exports

2. **System prompt integration**
   - Add skill navigation instructions
   - Update prompts.py

3. **Full integration testing**

### Phase 5: Documentation and Release (Week 5)

1. **Documentation**
   - API documentation
   - Usage examples
   - Migration guide for SkillTool -> FunctionTool

2. **Final testing**
   - Performance benchmarks
   - Edge case testing

---

## Trade-offs and Alternatives

### Alternative 1: Skills in System Prompt

**Approach**: Embed all skill instructions directly in system prompt.

| Aspect | System Prompt Approach | Tool Description Approach (Chosen) |
|--------|----------------------|-----------------------------------|
| Context Cost | High (scales with skills) | Low (fixed overhead) |
| Discovery | LLM sees all skills always | LLM sees list in tool desc |
| Activation | No explicit step | Explicit tool invocation |
| Observability | Hard to track | Clear tool call/result |
| Flexibility | Static at init | Dynamic, hot-reloadable |

**Decision**: Tool description approach chosen for context efficiency and observability.

### Alternative 2: Plugin-Based Storage Only

**Approach**: No hierarchy, all skills are plugins.

| Aspect | Plugin Only | Four-Layer Hierarchy (Chosen) |
|--------|------------|------------------------------|
| Simplicity | Simpler | More complex |
| Enterprise Control | Limited | Full override capability |
| Personal Customization | No | Yes |
| Project Portability | Good | Good |

**Decision**: Four-layer hierarchy chosen for enterprise governance requirements.

### Alternative 3: Inline Tool Restriction Check

**Approach**: Each tool checks restrictions itself.

| Aspect | Inline Checks | Executor-Level (Chosen) |
|--------|--------------|------------------------|
| Implementation | Per-tool code | Centralized |
| Bypass Risk | Higher | Lower |
| Maintainability | Distributed | Single location |
| Performance | Multiple checks | Single check |

**Decision**: Executor-level enforcement chosen for security and maintainability.

### Alternative 4: YAML-Only Skills (No Markdown Body)

**Approach**: All skill content in YAML.

| Aspect | YAML-Only | Markdown Body (Chosen) |
|--------|-----------|----------------------|
| Authoring | Harder (YAML escaping) | Natural (Markdown) |
| Readability | Lower | Higher |
| Tooling | Less common | VSCode, etc. support |
| Content Size | YAML bloat | Clean separation |

**Decision**: Markdown body chosen for author experience and Claude Code compatibility.

---

## Risk Assessment

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| YAML parsing edge cases | Medium | Low | Comprehensive parser tests |
| Path resolution bugs (Windows) | Medium | Medium | Path normalization, platform tests |
| Cache invalidation issues | Low | Medium | TTL-based expiration, manual invalidate |
| Thread safety in loader | Low | High | RLock usage, concurrent tests |
| Large index memory usage | Low | Medium | Monitor in benchmarks, pagination if needed |

### Integration Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| SkillTool rename breaks users | Medium | Medium | Deprecation period, clear migration guide |
| Tool restriction bypass | Low | High | Executor-level enforcement |
| System prompt size explosion | Low | Medium | Keep instructions minimal |

### Operational Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Skill file corruption | Low | Low | Graceful error handling, skip bad skills |
| Storage layer misconfiguration | Medium | Low | Clear defaults, validation |
| Hot reload race conditions | Low | Low | Thread-safe index updates |

---

## Implementation Phases Summary

```
Week 1-2: Foundation
  - Skills module structure
  - Models and parser
  - Storage manager
  - Unit tests

Week 2-3: Loader
  - SkillLoader implementation
  - Caching with TTL
  - Thread safety
  - Integration tests

Week 3-4: SkillTool
  - SkillTool implementation
  - SkillContext for restrictions
  - ToolExecutor integration
  - Full tests

Week 4-5: Rename + Integration
  - FunctionTool rename
  - System prompt update
  - Integration testing
  - Documentation

Week 5+: Polish
  - Performance benchmarks
  - Edge case fixes
  - Release prep
```

---

## Appendix A: Module Structure

```
src/omniforge/skills/
  __init__.py           # Public API exports
  models.py             # Pydantic models (Skill, SkillMetadata, etc.)
  errors.py             # Exception hierarchy
  parser.py             # YAML frontmatter parser
  storage.py            # Storage layer management
  loader.py             # Skill loader with caching
  context.py            # SkillContext for tool restrictions
  tool.py               # SkillTool implementation

src/omniforge/tools/builtin/
  function.py           # NEW: FunctionTool (renamed from skill.py)
  skill.py              # MODIFIED: Deprecation aliases only
```

---

## Appendix B: API Reference Summary

### Public Classes

- `Skill` - Complete skill with metadata and content
- `SkillMetadata` - YAML frontmatter fields
- `SkillLoader` - Index and load skills
- `SkillTool` - Tool for skill invocation
- `SkillContext` - Tool restriction context manager
- `StorageConfig` - Storage path configuration

### Public Functions

- `StorageConfig.from_environment()` - Create config from defaults

### Exceptions

- `SkillError` - Base exception
- `SkillNotFoundError` - Skill not in index
- `SkillParseError` - SKILL.md parsing failed
- `SkillToolNotAllowedError` - Tool restricted by skill

---

## Appendix C: SKILL.md Specification

```yaml
---
# Required fields
name: string           # Kebab-case identifier
description: string    # One-line description

# Optional fields
allowed-tools:         # Tool allowlist
  - Bash
  - Read
  - Write
model: string          # Preferred LLM model
context: inherit|fork  # Context mode (default: inherit)
agent: string          # Agent type for fork mode
hooks:
  pre: string          # Pre-execution script path
  post: string         # Post-execution script path
priority: number       # Override priority (default: 0)
tags:                  # Categorization tags
  - deployment
  - kubernetes
scope:                 # Availability restrictions
  agents: [string]
  tenants: [string]
  environments: [string]
---

# Skill content in Markdown

Instructions for the agent...
```
