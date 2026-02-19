"""Repository for cost record persistence.

This module provides database repositories for storing and querying cost records
and aggregated model usage statistics.
"""

from datetime import date, datetime
from typing import Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from omniforge.enterprise.cost_tracker import CostRecord
from omniforge.storage.models import CostRecordModel, ModelUsageModel


class CostRecordRepository:
    """Repository for cost record persistence.

    Provides async methods for storing and querying cost records with
    efficient indexing and tenant isolation.

    Example:
        >>> repo = CostRecordRepository(session)
        >>> record = CostRecord(...)
        >>> await repo.save(record)
        >>> records = await repo.get_by_task("task-1")
    """

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def save(self, cost_record: CostRecord) -> None:
        """Save a cost record to the database.

        Args:
            cost_record: Cost record to save
        """
        model = CostRecordModel(
            tenant_id=cost_record.tenant_id,
            task_id=cost_record.task_id,
            chain_id=cost_record.chain_id,
            step_id=cost_record.step_id,
            tool_name=cost_record.tool_name,
            cost_usd=cost_record.cost_usd,
            tokens=cost_record.tokens,
            model=cost_record.model,
            created_at=cost_record.created_at,
        )
        self.session.add(model)
        await self.session.flush()

    async def get_by_task(self, task_id: str) -> List[CostRecord]:
        """Get all cost records for a task.

        Args:
            task_id: Task identifier

        Returns:
            List of cost records for the task
        """
        stmt = select(CostRecordModel).where(CostRecordModel.task_id == task_id).order_by(CostRecordModel.created_at)
        result = await self.session.execute(stmt)
        models = result.scalars().all()

        return [
            CostRecord(
                tenant_id=model.tenant_id,
                task_id=model.task_id,
                chain_id=model.chain_id,
                step_id=model.step_id,
                tool_name=model.tool_name,
                cost_usd=model.cost_usd,
                tokens=model.tokens,
                model=model.model,
                created_at=model.created_at,
            )
            for model in models
        ]

    async def get_by_tenant_date_range(
        self, tenant_id: str, start_date: datetime, end_date: datetime
    ) -> List[CostRecord]:
        """Get cost records for a tenant within a date range.

        Args:
            tenant_id: Tenant identifier
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)

        Returns:
            List of cost records within the date range
        """
        stmt = (
            select(CostRecordModel)
            .where(
                CostRecordModel.tenant_id == tenant_id,
                CostRecordModel.created_at >= start_date,
                CostRecordModel.created_at <= end_date,
            )
            .order_by(CostRecordModel.created_at)
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()

        return [
            CostRecord(
                tenant_id=model.tenant_id,
                task_id=model.task_id,
                chain_id=model.chain_id,
                step_id=model.step_id,
                tool_name=model.tool_name,
                cost_usd=model.cost_usd,
                tokens=model.tokens,
                model=model.model,
                created_at=model.created_at,
            )
            for model in models
        ]

    async def get_tenant_totals(
        self, tenant_id: str, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
    ) -> Dict[str, float]:
        """Get aggregated totals for a tenant.

        Args:
            tenant_id: Tenant identifier
            start_date: Optional start of date range
            end_date: Optional end of date range

        Returns:
            Dictionary with total_cost_usd, total_tokens, and record_count
        """
        stmt = select(
            func.sum(CostRecordModel.cost_usd).label("total_cost"),
            func.sum(CostRecordModel.tokens).label("total_tokens"),
            func.count(CostRecordModel.id).label("record_count"),
        ).where(CostRecordModel.tenant_id == tenant_id)

        if start_date:
            stmt = stmt.where(CostRecordModel.created_at >= start_date)
        if end_date:
            stmt = stmt.where(CostRecordModel.created_at <= end_date)

        result = await self.session.execute(stmt)
        row = result.one()

        return {
            "total_cost_usd": float(row.total_cost or 0.0),
            "total_tokens": int(row.total_tokens or 0),
            "record_count": int(row.record_count or 0),
        }


class ModelUsageRepository:
    """Repository for aggregated model usage statistics.

    Provides async methods for updating and querying daily usage aggregations
    per tenant and model.

    Example:
        >>> repo = ModelUsageRepository(session)
        >>> await repo.update_usage("tenant-1", "gpt-4", date.today(), 10, 1000, 500, 0.5)
        >>> usage = await repo.get_tenant_usage("tenant-1", date.today(), date.today())
    """

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def update_usage(
        self,
        tenant_id: str,
        model: str,
        usage_date: date,
        call_count: int,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
    ) -> None:
        """Update usage statistics for a tenant/model/date.

        Creates a new record or updates existing one (upsert).

        Args:
            tenant_id: Tenant identifier
            model: Model name
            usage_date: Date for aggregation
            call_count: Number of calls to add
            input_tokens: Input tokens to add
            output_tokens: Output tokens to add
            cost_usd: Cost to add
        """
        # Try to get existing record
        stmt = select(ModelUsageModel).where(
            ModelUsageModel.tenant_id == tenant_id,
            ModelUsageModel.model == model,
            ModelUsageModel.date == usage_date,
        )
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing record
            existing.call_count += call_count
            existing.input_tokens += input_tokens
            existing.output_tokens += output_tokens
            existing.total_cost_usd += cost_usd
        else:
            # Create new record
            usage = ModelUsageModel(
                tenant_id=tenant_id,
                model=model,
                date=usage_date,
                call_count=call_count,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_cost_usd=cost_usd,
            )
            self.session.add(usage)

        await self.session.flush()

    async def get_tenant_usage(
        self, tenant_id: str, start_date: date, end_date: date
    ) -> List[Dict[str, any]]:
        """Get usage statistics for a tenant within a date range.

        Args:
            tenant_id: Tenant identifier
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)

        Returns:
            List of usage records with model, date, and metrics
        """
        stmt = (
            select(ModelUsageModel)
            .where(
                ModelUsageModel.tenant_id == tenant_id,
                ModelUsageModel.date >= start_date,
                ModelUsageModel.date <= end_date,
            )
            .order_by(ModelUsageModel.date, ModelUsageModel.model)
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()

        return [
            {
                "model": model.model,
                "date": model.date,
                "call_count": model.call_count,
                "input_tokens": model.input_tokens,
                "output_tokens": model.output_tokens,
                "total_cost_usd": model.total_cost_usd,
            }
            for model in models
        ]

    async def get_model_totals(
        self, tenant_id: str, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> Dict[str, Dict[str, float]]:
        """Get aggregated totals per model for a tenant.

        Args:
            tenant_id: Tenant identifier
            start_date: Optional start of date range
            end_date: Optional end of date range

        Returns:
            Dictionary mapping model names to their aggregate metrics
        """
        stmt = (
            select(
                ModelUsageModel.model,
                func.sum(ModelUsageModel.call_count).label("total_calls"),
                func.sum(ModelUsageModel.input_tokens).label("total_input"),
                func.sum(ModelUsageModel.output_tokens).label("total_output"),
                func.sum(ModelUsageModel.total_cost_usd).label("total_cost"),
            )
            .where(ModelUsageModel.tenant_id == tenant_id)
            .group_by(ModelUsageModel.model)
        )

        if start_date:
            stmt = stmt.where(ModelUsageModel.date >= start_date)
        if end_date:
            stmt = stmt.where(ModelUsageModel.date <= end_date)

        result = await self.session.execute(stmt)
        rows = result.all()

        return {
            row.model: {
                "call_count": int(row.total_calls or 0),
                "input_tokens": int(row.total_input or 0),
                "output_tokens": int(row.total_output or 0),
                "total_cost_usd": float(row.total_cost or 0.0),
            }
            for row in rows
        }
