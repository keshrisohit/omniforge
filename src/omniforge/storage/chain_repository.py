"""Repository for reasoning chain persistence.

This module provides the repository interface for storing and retrieving
reasoning chains and their steps.
"""

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from omniforge.agents.cot.chain import ReasoningChain, ReasoningStep
from omniforge.storage.models import ReasoningChainModel, ReasoningStepModel


class ChainRepository:
    """Repository for managing reasoning chain persistence.

    Handles conversion between Pydantic domain models and SQLAlchemy
    ORM models, providing async CRUD operations.

    Example:
        >>> repo = ChainRepository(session)
        >>> await repo.save(chain)
        >>> retrieved = await repo.get_by_id(chain.id)
    """

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def save(self, chain: ReasoningChain) -> None:
        """Persist a reasoning chain with all its steps.

        Args:
            chain: Reasoning chain to persist
        """
        # Convert Pydantic chain to ORM model
        chain_model = ReasoningChainModel(
            id=str(chain.id),
            task_id=chain.task_id,
            agent_id=chain.agent_id,
            status=chain.status.value,
            started_at=chain.started_at,
            completed_at=chain.completed_at,
            metrics=chain.metrics.model_dump(),
            child_chain_ids=chain.child_chain_ids,
            tenant_id=chain.tenant_id,
        )

        # Convert steps to ORM models
        for step in chain.steps:
            step_model = self._step_to_model(step, str(chain.id))
            chain_model.steps.append(step_model)

        # Merge or add to session
        self.session.add(chain_model)
        await self.session.flush()

    async def get_by_id(self, chain_id: UUID) -> Optional[ReasoningChain]:
        """Retrieve a chain by its ID.

        Args:
            chain_id: Chain identifier

        Returns:
            Reasoning chain if found, None otherwise
        """
        # Query with eager loading of steps
        stmt = (
            select(ReasoningChainModel)
            .where(ReasoningChainModel.id == str(chain_id))
            .options(selectinload(ReasoningChainModel.steps))
        )
        result = await self.session.execute(stmt)
        chain_model = result.scalar_one_or_none()

        if not chain_model:
            return None

        return self._model_to_chain(chain_model)

    async def get_by_task(self, task_id: str) -> list[ReasoningChain]:
        """Retrieve all chains for a task.

        Args:
            task_id: Task identifier

        Returns:
            List of reasoning chains for the task
        """
        stmt = (
            select(ReasoningChainModel)
            .where(ReasoningChainModel.task_id == task_id)
            .options(selectinload(ReasoningChainModel.steps))
            .order_by(ReasoningChainModel.started_at)
        )
        result = await self.session.execute(stmt)
        chain_models = result.scalars().all()

        return [self._model_to_chain(model) for model in chain_models]

    async def list_by_tenant(
        self, tenant_id: str, limit: int = 100, offset: int = 0
    ) -> list[ReasoningChain]:
        """List chains for a tenant with pagination.

        Args:
            tenant_id: Tenant identifier
            limit: Maximum number of chains to return
            offset: Number of chains to skip

        Returns:
            List of reasoning chains for the tenant
        """
        stmt = (
            select(ReasoningChainModel)
            .where(ReasoningChainModel.tenant_id == tenant_id)
            .options(selectinload(ReasoningChainModel.steps))
            .order_by(ReasoningChainModel.started_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        chain_models = result.scalars().all()

        return [self._model_to_chain(model) for model in chain_models]

    async def delete(self, chain_id: UUID) -> bool:
        """Delete a chain and all its steps.

        Args:
            chain_id: Chain identifier

        Returns:
            True if chain was deleted, False if not found
        """
        stmt = select(ReasoningChainModel).where(ReasoningChainModel.id == str(chain_id))
        result = await self.session.execute(stmt)
        chain_model = result.scalar_one_or_none()

        if not chain_model:
            return False

        await self.session.delete(chain_model)
        await self.session.flush()
        return True

    def _step_to_model(self, step: ReasoningStep, chain_id: str) -> ReasoningStepModel:
        """Convert Pydantic step to ORM model.

        Args:
            step: Reasoning step
            chain_id: Parent chain ID

        Returns:
            ORM step model
        """
        return ReasoningStepModel(
            id=str(step.id),
            chain_id=chain_id,
            step_number=step.step_number,
            type=step.type.value,
            timestamp=step.timestamp,
            parent_step_id=str(step.parent_step_id) if step.parent_step_id else None,
            visibility=step.visibility.model_dump(),
            thinking=step.thinking.model_dump() if step.thinking else None,
            tool_call=step.tool_call.model_dump() if step.tool_call else None,
            tool_result=step.tool_result.model_dump() if step.tool_result else None,
            synthesis=step.synthesis.model_dump() if step.synthesis else None,
            tokens_used=step.tokens_used,
            cost=step.cost,
        )

    def _model_to_chain(self, model: ReasoningChainModel) -> ReasoningChain:
        """Convert ORM model to Pydantic chain.

        Args:
            model: ORM chain model

        Returns:
            Reasoning chain
        """
        from omniforge.agents.cot.chain import (
            ChainMetrics,
            ChainStatus,
            StepType,
            SynthesisInfo,
            ThinkingInfo,
            ToolCallInfo,
            ToolResultInfo,
            VisibilityConfig,
        )

        # Reconstruct chain
        chain = ReasoningChain(
            id=UUID(model.id),
            task_id=model.task_id,
            agent_id=model.agent_id,
            status=ChainStatus(model.status),
            started_at=model.started_at,
            completed_at=model.completed_at,
            metrics=ChainMetrics(**model.metrics),
            child_chain_ids=model.child_chain_ids,
            tenant_id=model.tenant_id,
            steps=[],  # Add steps separately
        )

        # Reconstruct steps (already ordered by step_number due to relationship)
        for step_model in model.steps:
            step = ReasoningStep(
                id=UUID(step_model.id),
                step_number=step_model.step_number,
                type=StepType(step_model.type),
                timestamp=step_model.timestamp,
                parent_step_id=UUID(step_model.parent_step_id) if step_model.parent_step_id else None,
                visibility=VisibilityConfig(**step_model.visibility),
                thinking=ThinkingInfo(**step_model.thinking) if step_model.thinking else None,
                tool_call=ToolCallInfo(**step_model.tool_call) if step_model.tool_call else None,
                tool_result=(
                    ToolResultInfo(**step_model.tool_result) if step_model.tool_result else None
                ),
                synthesis=(
                    SynthesisInfo(**step_model.synthesis) if step_model.synthesis else None
                ),
                tokens_used=step_model.tokens_used,
                cost=step_model.cost,
            )
            chain.steps.append(step)

        return chain
