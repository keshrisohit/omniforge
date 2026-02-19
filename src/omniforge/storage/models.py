"""SQLAlchemy ORM models for persistence.

This module defines database models for cost tracking, usage reporting,
reasoning chain persistence, and other persistent data.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    LargeBinary,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from omniforge.storage.base_model import Base


class CostRecordModel(Base):
    """ORM model for cost records.

    Stores individual cost events from tool executions with full traceability
    for billing, usage analytics, and cost control.

    Attributes:
        id: Unique identifier (UUID)
        tenant_id: Tenant identifier (indexed)
        task_id: Task identifier (indexed)
        chain_id: Chain of thought identifier
        step_id: Step identifier within the chain
        tool_name: Name of the tool that incurred the cost
        cost_usd: Cost in USD
        tokens: Number of tokens consumed
        model: Model name (for LLM calls)
        created_at: Timestamp when cost was recorded
    """

    __tablename__ = "cost_records"

    # Primary key
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Identifiers (indexed for queries)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    task_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    chain_id: Mapped[str] = mapped_column(String(255), nullable=False)
    step_id: Mapped[str] = mapped_column(String(255), nullable=False)

    # Cost details
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False)
    cost_usd: Mapped[float] = mapped_column(Float, nullable=False)
    tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    model: Mapped[str] = mapped_column(String(100), nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Composite indexes for common query patterns
    __table_args__ = (
        Index("idx_tenant_created", "tenant_id", "created_at"),
        Index("idx_task_created", "task_id", "created_at"),
        Index("idx_tenant_task", "tenant_id", "task_id"),
    )


class ModelUsageModel(Base):
    """ORM model for aggregated model usage reporting.

    Stores daily aggregated usage statistics per tenant and model for
    efficient reporting and analytics.

    Attributes:
        id: Unique identifier (UUID)
        tenant_id: Tenant identifier
        model: Model name
        date: Date for aggregation
        call_count: Number of calls made
        input_tokens: Total input tokens
        output_tokens: Total output tokens
        total_cost_usd: Total cost in USD
    """

    __tablename__ = "model_usage"

    # Primary key
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Identifiers
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    date: Mapped[datetime] = mapped_column(Date, nullable=False)

    # Usage metrics
    call_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Unique constraint: one row per tenant/model/date
    __table_args__ = (
        UniqueConstraint("tenant_id", "model", "date", name="uq_tenant_model_date"),
        Index("idx_tenant_date", "tenant_id", "date"),
    )


class ReasoningChainModel(Base):
    """ORM model for reasoning chains.

    Stores reasoning chains for audit trails, debugging, and replay functionality.
    Each chain represents a complete reasoning process for a task.

    Attributes:
        id: Unique identifier (UUID)
        task_id: Task identifier (indexed)
        agent_id: Agent identifier (indexed)
        status: Chain execution status
        started_at: When chain execution started
        completed_at: When chain execution completed
        metrics: Aggregated chain metrics (JSON)
        child_chain_ids: List of child chain IDs for sub-agent delegation (JSON)
        tenant_id: Tenant identifier (indexed)
        steps: Related reasoning steps (relationship)
    """

    __tablename__ = "reasoning_chains"

    # Primary key
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # Identifiers (indexed for queries)
    task_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    agent_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=True, index=True)

    # Status and timing
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # Metrics and relationships (stored as JSON)
    metrics: Mapped[dict] = mapped_column(JSON, nullable=False)
    child_chain_ids: Mapped[list] = mapped_column(JSON, nullable=False)

    # Relationship to steps (cascade delete)
    steps: Mapped[list["ReasoningStepModel"]] = relationship(
        "ReasoningStepModel",
        back_populates="chain",
        cascade="all, delete-orphan",
        order_by="ReasoningStepModel.step_number",
    )

    # Composite indexes for common query patterns
    __table_args__ = (
        Index("idx_chain_tenant_task", "tenant_id", "task_id"),
        Index("idx_chain_tenant_started", "tenant_id", "started_at"),
        Index("idx_chain_task_started", "task_id", "started_at"),
    )


class ReasoningStepModel(Base):
    """ORM model for reasoning steps.

    Stores individual steps within a reasoning chain. Steps are ordered
    sequentially and contain type-specific information in JSON fields.

    Attributes:
        id: Unique identifier (UUID)
        chain_id: Foreign key to reasoning chain (cascade delete)
        step_number: Sequential step number within chain
        type: Step type (thinking, tool_call, tool_result, synthesis)
        timestamp: When step was created
        parent_step_id: Optional parent step ID for nested operations
        visibility: Visibility configuration (JSON)
        thinking: Thinking step info (JSON)
        tool_call: Tool call step info (JSON)
        tool_result: Tool result step info (JSON)
        synthesis: Synthesis step info (JSON)
        tokens_used: Tokens consumed in this step
        cost: Cost of this step in USD
        chain: Related reasoning chain (relationship)
    """

    __tablename__ = "reasoning_steps"

    # Primary key
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # Foreign key to chain (cascade delete)
    chain_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("reasoning_chains.id", ondelete="CASCADE"), nullable=False
    )

    # Step metadata
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    parent_step_id: Mapped[str] = mapped_column(String(36), nullable=True)

    # Visibility configuration
    visibility: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Type-specific info (stored as JSON)
    thinking: Mapped[dict] = mapped_column(JSON, nullable=True)
    tool_call: Mapped[dict] = mapped_column(JSON, nullable=True)
    tool_result: Mapped[dict] = mapped_column(JSON, nullable=True)
    synthesis: Mapped[dict] = mapped_column(JSON, nullable=True)

    # Token and cost tracking
    tokens_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Relationship to chain
    chain: Mapped["ReasoningChainModel"] = relationship(
        "ReasoningChainModel", back_populates="steps"
    )

    # Composite indexes for queries
    __table_args__ = (
        Index("idx_chain_step", "chain_id", "step_number"),
        Index("idx_chain_timestamp", "chain_id", "timestamp"),
    )


class AuditEventModel(Base):
    """ORM model for audit events.

    Stores immutable audit logs for compliance and security monitoring.
    Events are append-only and never modified or deleted.

    Attributes:
        id: Unique identifier (UUID)
        timestamp: When event occurred (indexed)
        tenant_id: Tenant identifier (indexed)
        user_id: User identifier
        agent_id: Agent identifier
        task_id: Task identifier
        event_type: Type of event
        resource_type: Type of resource accessed
        resource_id: Resource identifier
        action: Action performed
        outcome: Action outcome (success/failure/denied)
        metadata: Additional context (JSON)
        ip_address: Client IP address
        user_agent: Client user agent
    """

    __tablename__ = "audit_events"

    # Primary key
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # Timestamp (heavily indexed for queries)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)

    # Identifiers (indexed for filtering)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=True, index=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=True, index=True)
    agent_id: Mapped[str] = mapped_column(String(255), nullable=True)
    task_id: Mapped[str] = mapped_column(String(255), nullable=True)

    # Event details
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=True)
    resource_id: Mapped[str] = mapped_column(String(255), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    outcome: Mapped[str] = mapped_column(String(20), nullable=False)

    # Context
    event_metadata: Mapped[dict] = mapped_column(JSON, nullable=False)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str] = mapped_column(String(500), nullable=True)

    # Composite indexes for common query patterns
    __table_args__ = (
        Index("idx_audit_tenant_timestamp", "tenant_id", "timestamp"),
        Index("idx_audit_event_timestamp", "event_type", "timestamp"),
        Index("idx_audit_user_timestamp", "user_id", "timestamp"),
        Index("idx_audit_agent_timestamp", "agent_id", "timestamp"),
    )


class OAuthStateModel(Base):
    """ORM model for OAuth state tracking.

    Stores OAuth state for CSRF protection during OAuth flows.
    State records are short-lived and cleaned up after completion.

    Attributes:
        state: Unique state identifier (primary key)
        user_id: User identifier
        tenant_id: Tenant identifier
        integration_id: Integration identifier (e.g., "notion")
        session_id: Session identifier for callback routing
        created_at: State creation timestamp
        expires_at: State expiration timestamp
    """

    __tablename__ = "oauth_states"

    # Primary key (the state itself)
    state: Mapped[str] = mapped_column(String(255), primary_key=True)

    # Identifiers
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    integration_id: Mapped[str] = mapped_column(String(100), nullable=False)
    session_id: Mapped[str] = mapped_column(String(255), nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Index for cleanup queries
    __table_args__ = (Index("idx_oauth_state_expires", "expires_at"),)


class OAuthCredentialModel(Base):
    """ORM model for OAuth credentials.

    Stores encrypted OAuth tokens with metadata. Supports token refresh
    and workspace discovery for integrations like Notion.

    Attributes:
        id: Unique credential identifier (UUID)
        user_id: User identifier (indexed)
        tenant_id: Tenant identifier (indexed)
        integration_id: Integration identifier (e.g., "notion")
        workspace_id: External workspace/team identifier
        workspace_name: Human-readable workspace name
        access_token_encrypted: Encrypted access token (bytes)
        refresh_token_encrypted: Encrypted refresh token (bytes, optional)
        token_type: Token type (usually "Bearer")
        expires_at: Token expiration timestamp
        scopes: List of granted OAuth scopes (JSON)
        created_at: Credential creation timestamp
        updated_at: Last update timestamp (for refresh)
    """

    __tablename__ = "oauth_credentials"

    # Primary key
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # Identifiers (indexed for queries)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    integration_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Workspace info
    workspace_id: Mapped[str] = mapped_column(String(255), nullable=True)
    workspace_name: Mapped[str] = mapped_column(String(255), nullable=True)

    # Encrypted tokens (stored as binary)
    access_token_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    refresh_token_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=True)

    # Token metadata
    token_type: Mapped[str] = mapped_column(String(50), nullable=False, default="Bearer")
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    scopes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Composite indexes for common query patterns
    __table_args__ = (
        Index("idx_oauth_cred_user_tenant", "user_id", "tenant_id"),
        Index("idx_oauth_cred_integration", "integration_id", "user_id"),
    )
