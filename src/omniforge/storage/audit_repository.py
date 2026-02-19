"""Repository for audit event persistence.

This module provides append-only storage for audit events with
efficient querying by tenant, date range, and event type.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from omniforge.enterprise.audit import AuditEvent, EventType, Outcome
from omniforge.storage.models import AuditEventModel


class AuditRepository:
    """Repository for managing audit event persistence.

    Provides append-only storage with no update or delete operations
    to maintain immutable audit trails.

    Example:
        >>> repo = AuditRepository(session)
        >>> await repo.save(audit_event)
        >>> events = await repo.query(tenant_id="tenant-1")
    """

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def save(self, event: AuditEvent) -> None:
        """Save an audit event (append-only).

        Args:
            event: Audit event to persist
        """
        model = AuditEventModel(
            id=str(event.id),
            timestamp=event.timestamp,
            tenant_id=event.tenant_id,
            user_id=event.user_id,
            agent_id=event.agent_id,
            task_id=event.task_id,
            event_type=event.event_type.value,
            resource_type=event.resource_type,
            resource_id=event.resource_id,
            action=event.action,
            outcome=event.outcome.value,
            event_metadata=event.metadata,
            ip_address=event.ip_address,
            user_agent=event.user_agent,
        )

        self.session.add(model)
        await self.session.flush()

    async def get_by_id(self, event_id: UUID) -> Optional[AuditEvent]:
        """Retrieve an audit event by ID.

        Args:
            event_id: Event identifier

        Returns:
            Audit event if found, None otherwise
        """
        stmt = select(AuditEventModel).where(AuditEventModel.id == str(event_id))
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            return None

        return self._model_to_event(model)

    async def query(
        self,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        event_type: Optional[EventType] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditEvent]:
        """Query audit events with filters.

        Args:
            tenant_id: Filter by tenant
            user_id: Filter by user
            agent_id: Filter by agent
            event_type: Filter by event type
            start_time: Filter events after this time
            end_time: Filter events before this time
            limit: Maximum number of events to return
            offset: Number of events to skip

        Returns:
            List of matching audit events
        """
        stmt = select(AuditEventModel)

        # Apply filters
        if tenant_id:
            stmt = stmt.where(AuditEventModel.tenant_id == tenant_id)
        if user_id:
            stmt = stmt.where(AuditEventModel.user_id == user_id)
        if agent_id:
            stmt = stmt.where(AuditEventModel.agent_id == agent_id)
        if event_type:
            stmt = stmt.where(AuditEventModel.event_type == event_type.value)
        if start_time:
            stmt = stmt.where(AuditEventModel.timestamp >= start_time)
        if end_time:
            stmt = stmt.where(AuditEventModel.timestamp <= end_time)

        # Order by timestamp descending (newest first)
        stmt = stmt.order_by(AuditEventModel.timestamp.desc())

        # Apply pagination
        stmt = stmt.limit(limit).offset(offset)

        result = await self.session.execute(stmt)
        models = result.scalars().all()

        return [self._model_to_event(model) for model in models]

    async def count(
        self,
        tenant_id: Optional[str] = None,
        event_type: Optional[EventType] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> int:
        """Count audit events matching filters.

        Args:
            tenant_id: Filter by tenant
            event_type: Filter by event type
            start_time: Filter events after this time
            end_time: Filter events before this time

        Returns:
            Count of matching events
        """
        from sqlalchemy import func

        stmt = select(func.count(AuditEventModel.id))

        # Apply filters
        if tenant_id:
            stmt = stmt.where(AuditEventModel.tenant_id == tenant_id)
        if event_type:
            stmt = stmt.where(AuditEventModel.event_type == event_type.value)
        if start_time:
            stmt = stmt.where(AuditEventModel.timestamp >= start_time)
        if end_time:
            stmt = stmt.where(AuditEventModel.timestamp <= end_time)

        result = await self.session.execute(stmt)
        return result.scalar_one()

    def _model_to_event(self, model: AuditEventModel) -> AuditEvent:
        """Convert ORM model to domain event.

        Args:
            model: ORM audit event model

        Returns:
            Audit event
        """
        return AuditEvent(
            id=UUID(model.id),
            timestamp=model.timestamp,
            tenant_id=model.tenant_id,
            user_id=model.user_id,
            agent_id=model.agent_id,
            task_id=model.task_id,
            event_type=EventType(model.event_type),
            resource_type=model.resource_type,
            resource_id=model.resource_id,
            action=model.action,
            outcome=Outcome(model.outcome),
            metadata=model.event_metadata,
            ip_address=model.ip_address,
            user_agent=model.user_agent,
        )
