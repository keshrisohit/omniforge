"""Audit logging for compliance and investigation.

This module provides audit logging for agent operations, tool calls,
and access events for compliance and security monitoring.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Types of audit events."""

    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    CHAIN_START = "chain_start"
    CHAIN_COMPLETE = "chain_complete"
    CHAIN_FAIL = "chain_fail"
    ACCESS_GRANT = "access_grant"
    ACCESS_DENY = "access_deny"
    POLICY_VIOLATION = "policy_violation"


class Outcome(str, Enum):
    """Outcome of an audited operation."""

    SUCCESS = "success"
    FAILURE = "failure"
    DENIED = "denied"


class AuditEvent(BaseModel):
    """An auditable event in the system.

    Attributes:
        id: Unique event identifier
        timestamp: When the event occurred
        tenant_id: Tenant identifier
        user_id: User who initiated the action
        agent_id: Agent involved in the action
        task_id: Task being executed
        event_type: Type of event
        resource_type: Type of resource accessed
        resource_id: Identifier of the resource
        action: Action performed
        outcome: Result of the action
        metadata: Additional context (JSON-serializable)
        ip_address: Client IP address
        user_agent: Client user agent
    """

    id: UUID = Field(default_factory=uuid4, description="Unique event identifier")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Event timestamp"
    )

    # Identifiers
    tenant_id: Optional[str] = Field(None, description="Tenant identifier")
    user_id: Optional[str] = Field(None, description="User identifier")
    agent_id: Optional[str] = Field(None, description="Agent identifier")
    task_id: Optional[str] = Field(None, description="Task identifier")

    # Event details
    event_type: EventType = Field(description="Event type")
    resource_type: Optional[str] = Field(None, description="Resource type")
    resource_id: Optional[str] = Field(None, description="Resource identifier")
    action: str = Field(description="Action performed")
    outcome: Outcome = Field(description="Action outcome")

    # Additional context
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional context"
    )
    ip_address: Optional[str] = Field(None, description="Client IP address")
    user_agent: Optional[str] = Field(None, description="Client user agent")


class AuditLogger:
    """Logger for audit events.

    Provides methods to log various types of audit events with automatic
    sensitive data redaction.

    Example:
        >>> logger = AuditLogger(repository, sensitive_fields=["password", "api_key"])
        >>> await logger.log_tool_call(
        ...     tenant_id="tenant-1",
        ...     tool_name="calculator",
        ...     arguments={"a": 1, "b": 2},
        ...     result={"answer": 3}
        ... )
    """

    def __init__(
        self,
        repository: Any,  # AuditRepository
        sensitive_fields: Optional[list[str]] = None,
    ):
        """Initialize audit logger.

        Args:
            repository: Audit repository for persistence
            sensitive_fields: Fields to redact from logs
        """
        self.repository = repository
        self.sensitive_fields = sensitive_fields or [
            "password",
            "api_key",
            "token",
            "secret",
            "credential",
        ]

    async def log_tool_call(
        self,
        tenant_id: Optional[str],
        agent_id: Optional[str],
        task_id: Optional[str],
        tool_name: str,
        arguments: dict[str, Any],
        result: Optional[dict[str, Any]] = None,
        success: bool = True,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> AuditEvent:
        """Log a tool call event.

        Args:
            tenant_id: Tenant identifier
            agent_id: Agent identifier
            task_id: Task identifier
            tool_name: Name of the tool called
            arguments: Tool arguments
            result: Tool result (if completed)
            success: Whether the call succeeded
            user_id: User identifier
            ip_address: Client IP address

        Returns:
            Created audit event
        """
        # Redact sensitive data
        safe_arguments = self._redact_sensitive(arguments)
        safe_result = self._redact_sensitive(result) if result else None

        event = AuditEvent(
            tenant_id=tenant_id,
            user_id=user_id,
            agent_id=agent_id,
            task_id=task_id,
            event_type=EventType.TOOL_CALL if not result else EventType.TOOL_RESULT,
            resource_type="tool",
            resource_id=tool_name,
            action=f"call:{tool_name}",
            outcome=Outcome.SUCCESS if success else Outcome.FAILURE,
            metadata={
                "tool_name": tool_name,
                "arguments": safe_arguments,
                "result": safe_result,
            },
            ip_address=ip_address,
        )

        await self.repository.save(event)
        return event

    async def log_chain_event(
        self,
        chain_id: UUID,
        event_type: EventType,
        tenant_id: Optional[str],
        agent_id: Optional[str],
        task_id: Optional[str],
        success: bool = True,
        metadata: Optional[dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ) -> AuditEvent:
        """Log a chain lifecycle event.

        Args:
            chain_id: Chain identifier
            event_type: Type of chain event
            tenant_id: Tenant identifier
            agent_id: Agent identifier
            task_id: Task identifier
            success: Whether the operation succeeded
            metadata: Additional context
            user_id: User identifier

        Returns:
            Created audit event
        """
        event = AuditEvent(
            tenant_id=tenant_id,
            user_id=user_id,
            agent_id=agent_id,
            task_id=task_id,
            event_type=event_type,
            resource_type="chain",
            resource_id=str(chain_id),
            action=f"chain:{event_type.value}",
            outcome=Outcome.SUCCESS if success else Outcome.FAILURE,
            metadata=self._redact_sensitive(metadata or {}),
        )

        await self.repository.save(event)
        return event

    async def log_access(
        self,
        tenant_id: Optional[str],
        user_id: str,
        resource_type: str,
        resource_id: str,
        action: str,
        granted: bool,
        metadata: Optional[dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditEvent:
        """Log an access control event.

        Args:
            tenant_id: Tenant identifier
            user_id: User identifier
            resource_type: Type of resource accessed
            resource_id: Resource identifier
            action: Action attempted
            granted: Whether access was granted
            metadata: Additional context
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            Created audit event
        """
        event = AuditEvent(
            tenant_id=tenant_id,
            user_id=user_id,
            event_type=EventType.ACCESS_GRANT if granted else EventType.ACCESS_DENY,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            outcome=Outcome.SUCCESS if granted else Outcome.DENIED,
            metadata=metadata or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )

        await self.repository.save(event)
        return event

    async def log_policy_violation(
        self,
        tenant_id: Optional[str],
        agent_id: Optional[str],
        task_id: Optional[str],
        policy_type: str,
        violation_reason: str,
        metadata: Optional[dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ) -> AuditEvent:
        """Log a policy violation event.

        Args:
            tenant_id: Tenant identifier
            agent_id: Agent identifier
            task_id: Task identifier
            policy_type: Type of policy violated
            violation_reason: Reason for violation
            metadata: Additional context
            user_id: User identifier

        Returns:
            Created audit event
        """
        event = AuditEvent(
            tenant_id=tenant_id,
            user_id=user_id,
            agent_id=agent_id,
            task_id=task_id,
            event_type=EventType.POLICY_VIOLATION,
            resource_type="policy",
            resource_id=policy_type,
            action="violate",
            outcome=Outcome.DENIED,
            metadata={
                "policy_type": policy_type,
                "violation_reason": violation_reason,
                **(metadata or {}),
            },
        )

        await self.repository.save(event)
        return event

    def _redact_sensitive(self, data: Optional[dict[str, Any]]) -> dict[str, Any]:
        """Redact sensitive fields from data.

        Args:
            data: Data to redact

        Returns:
            Redacted data
        """
        if data is None:
            return {}

        from omniforge.agents.cot.visibility import redact_sensitive_fields

        return redact_sensitive_fields(data, self.sensitive_fields)
