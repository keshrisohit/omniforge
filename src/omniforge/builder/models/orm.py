"""SQLAlchemy ORM models for database persistence."""

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from omniforge.storage.base_model import Base


class AgentConfigModel(Base):
    """SQLAlchemy model for agent_configs table.

    Stores agent configuration including trigger settings, skills, and integrations.
    """

    __tablename__ = "agent_configs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="draft",
        index=True,
    )
    trigger: Mapped[str] = mapped_column(String(20), nullable=False, default="on_demand")
    schedule: Mapped[str | None] = mapped_column(String(100), nullable=True)
    skills_json: Mapped[str] = mapped_column(Text, nullable=False)
    integrations_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    sharing_level: Mapped[str] = mapped_column(String(20), nullable=False, default="private")
    created_by: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    executions: Mapped[list["AgentExecutionModel"]] = relationship(
        back_populates="agent",
        cascade="all, delete-orphan",
    )

    # Indexes
    __table_args__ = (
        Index("idx_agent_tenant_status", "tenant_id", "status"),
        Index("idx_agent_trigger", "trigger"),
        Index("idx_agent_created_by", "created_by"),
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert ORM model to dictionary.

        Returns:
            Dictionary representation including parsed JSON fields
        """
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "trigger": self.trigger,
            "schedule": self.schedule,
            "skills": json.loads(self.skills_json),
            "integrations": json.loads(self.integrations_json),
            "sharing_level": self.sharing_level,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class CredentialModel(Base):
    """SQLAlchemy model for credentials table.

    Stores encrypted OAuth tokens and API credentials.
    """

    __tablename__ = "credentials"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    integration_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    integration_name: Mapped[str] = mapped_column(String(200), nullable=False)
    encrypted_credentials: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Indexes
    __table_args__ = (Index("idx_credential_tenant_type", "tenant_id", "integration_type"),)

    def to_dict(self) -> dict[str, Any]:
        """Convert ORM model to dictionary (excluding encrypted credentials).

        Returns:
            Dictionary representation without sensitive data
        """
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "integration_type": self.integration_type,
            "integration_name": self.integration_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_used_at": (self.last_used_at.isoformat() if self.last_used_at else None),
        }


class AgentExecutionModel(Base):
    """SQLAlchemy model for agent_executions table.

    Tracks agent execution history with timing, status, and outputs.
    """

    __tablename__ = "agent_executions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("agent_configs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    trigger_type: Mapped[str] = mapped_column(String(20), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    skill_executions_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")

    # Relationships
    agent: Mapped[AgentConfigModel] = relationship(back_populates="executions")

    # Indexes
    __table_args__ = (
        Index("idx_execution_agent_status", "agent_id", "status"),
        Index("idx_execution_tenant_started", "tenant_id", "started_at"),
        Index("idx_execution_status", "status"),
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert ORM model to dictionary.

        Returns:
            Dictionary representation including parsed JSON fields
        """
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "tenant_id": self.tenant_id,
            "status": self.status,
            "trigger_type": self.trigger_type,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (self.completed_at.isoformat() if self.completed_at else None),
            "duration_ms": self.duration_ms,
            "output": json.loads(self.output_json) if self.output_json else None,
            "error": self.error,
            "skill_executions": json.loads(self.skill_executions_json),
            "metadata": json.loads(self.metadata_json),
        }


class PublicSkillModel(Base):
    """SQLAlchemy model for public_skills table.

    Stores community-contributed skills available for discovery and reuse.
    Multiple versions of the same skill can be stored with UNIQUE(name, version).
    """

    __tablename__ = "public_skills"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(1024), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    author_id: Mapped[str] = mapped_column(String(64), nullable=False)
    tags_json: Mapped[str] = mapped_column(JSON, nullable=False, default="[]")
    integrations_json: Mapped[str] = mapped_column(JSON, nullable=False, default="[]")
    usage_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rating_avg: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Indexes and Constraints
    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_public_skills_name_version"),
        Index("idx_public_skills_name", "name"),
        Index("idx_public_skills_version", "version"),
        Index("idx_public_skills_usage", "usage_count"),
        Index("idx_public_skills_status", "status"),
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert ORM model to dictionary.

        Returns:
            Dictionary representation including parsed JSON fields
        """
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "content": self.content,
            "author_id": self.author_id,
            "tags": (
                json.loads(self.tags_json) if isinstance(self.tags_json, str) else self.tags_json
            ),
            "integrations": (
                json.loads(self.integrations_json)
                if isinstance(self.integrations_json, str)
                else self.integrations_json
            ),
            "usage_count": self.usage_count,
            "rating_avg": self.rating_avg,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
