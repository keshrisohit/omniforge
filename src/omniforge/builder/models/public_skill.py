"""Public skill library models."""

import re
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class PublicSkillStatus(str, Enum):
    """Public skill approval status."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class PublicSkill(BaseModel):
    """Public skill library entry.

    Represents a community-contributed skill available for reuse.
    Skills are stored as SKILL.md content and can be discovered through
    search, tags, and integration filters.

    Attributes:
        id: Unique skill identifier (kebab-case)
        name: Human-readable skill name (kebab-case, matches id)
        version: Semantic version (e.g., "1.0.0", "2.1.3")
        description: What the skill does (max 1024 chars)
        content: Complete SKILL.md file content
        author_id: User ID who contributed the skill
        tags: Categorization tags for discovery
        integrations: Integration types this skill uses (e.g., ["notion", "slack"])
        usage_count: Number of times skill has been added to agents
        rating_avg: Average user rating (0.0-5.0)
        status: Approval status (pending/approved/rejected/archived)
        created_at: When the skill was submitted
    """

    id: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1, max_length=64)
    version: str = Field(..., min_length=1, max_length=20)
    description: str = Field(..., min_length=1, max_length=1024)
    content: str = Field(..., min_length=1)
    author_id: str = Field(..., min_length=1, max_length=64)
    tags: list[str] = Field(default_factory=list)
    integrations: list[str] = Field(default_factory=list)
    usage_count: int = Field(default=0, ge=0)
    rating_avg: float = Field(default=0.0, ge=0.0, le=5.0)
    status: PublicSkillStatus = Field(default=PublicSkillStatus.PENDING)
    created_at: Optional[datetime] = None

    @field_validator("name", "id")
    @classmethod
    def validate_kebab_case(cls, v: str) -> str:
        """Validate name/id follows kebab-case naming."""
        if not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError(f"Must be kebab-case alphanumeric with hyphens: {v}")
        return v

    @field_validator("version")
    @classmethod
    def validate_semantic_version(cls, v: str) -> str:
        """Validate version follows semantic versioning (MAJOR.MINOR.PATCH)."""
        semver_pattern = r"^\d+\.\d+\.\d+$"
        if not re.match(semver_pattern, v):
            raise ValueError(f"Version must follow semantic versioning (MAJOR.MINOR.PATCH): {v}")
        return v

    @field_validator("tags", "integrations")
    @classmethod
    def validate_lists_lowercase(cls, v: list[str]) -> list[str]:
        """Normalize tags and integrations to lowercase."""
        return [item.lower() for item in v]

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "id": "notion-weekly-report",
                "name": "notion-weekly-report",
                "version": "1.0.0",
                "description": "Generates weekly summary from Notion database",
                "content": "---\nname: notion-weekly-report\n...",
                "author_id": "user-123",
                "tags": ["reporting", "notion", "weekly"],
                "integrations": ["notion"],
                "usage_count": 42,
                "rating_avg": 4.5,
                "status": "approved",
            }
        }
