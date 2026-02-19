"""Chain management API route handlers.

This module provides FastAPI route handlers for accessing reasoning chains,
with visibility filtering based on user roles.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from omniforge.agents.cot.chain import ChainStatus, ReasoningChain, ReasoningStep
from omniforge.agents.cot.visibility import VisibilityConfiguration, VisibilityController
from omniforge.api.dependencies import get_current_tenant, get_user_role, require_permission
from omniforge.security.rbac import Permission, Role
from omniforge.storage.chain_repository import ChainRepository
from omniforge.storage.database import Database, DatabaseConfig

# Create router
router = APIRouter(prefix="/api/v1", tags=["chains"])

# Shared database instance
# TODO: Replace with dependency injection in production
_database: Optional[Database] = None


def get_database() -> Database:
    """Get or create database instance.

    Returns:
        Database instance
    """
    global _database
    if _database is None:
        config = DatabaseConfig(url="sqlite+aiosqlite:///:memory:")
        _database = Database(config)
    return _database


async def get_chain_repository() -> ChainRepository:
    """Dependency for getting chain repository.

    Returns:
        Chain repository instance
    """
    db = get_database()
    async with db.session() as session:
        yield ChainRepository(session)


def get_visibility_controller() -> VisibilityController:
    """Dependency for getting visibility controller.

    Returns:
        Visibility controller instance
    """
    config = VisibilityConfiguration()
    return VisibilityController(config)


# Response Models


class ChainMetadataResponse(BaseModel):
    """Chain metadata in response."""

    total_steps: int
    llm_calls: int
    tool_calls: int
    total_tokens: int
    total_cost: float


class ChainResponse(BaseModel):
    """Full chain response with steps."""

    id: UUID
    task_id: str
    agent_id: str
    status: ChainStatus
    started_at: datetime
    completed_at: Optional[datetime]
    metrics: ChainMetadataResponse
    child_chain_ids: list[str]
    tenant_id: Optional[str]
    steps: list[dict]  # Serialized steps


class ChainSummaryResponse(BaseModel):
    """Chain summary without steps."""

    id: UUID
    task_id: str
    agent_id: str
    status: ChainStatus
    started_at: datetime
    completed_at: Optional[datetime]
    metrics: ChainMetadataResponse
    tenant_id: Optional[str]


class ChainListResponse(BaseModel):
    """Paginated list of chains."""

    chains: list[ChainSummaryResponse]
    total: int
    limit: int
    offset: int


class StepListResponse(BaseModel):
    """Paginated list of steps."""

    steps: list[dict]  # Serialized steps
    total: int
    limit: int
    offset: int


# Route Handlers


@router.get(
    "/chains/{chain_id}",
    response_model=ChainResponse,
    dependencies=[Depends(require_permission(Permission.CHAIN_READ))],
)
async def get_chain(
    chain_id: UUID,
    repository: ChainRepository = Depends(get_chain_repository),
    visibility: VisibilityController = Depends(get_visibility_controller),
    user_role: Optional[Role] = Depends(get_user_role),
    tenant_id: Optional[str] = Depends(get_current_tenant),
) -> ChainResponse:
    """Get a reasoning chain by ID with visibility filtering.

    Args:
        chain_id: Chain identifier
        repository: Chain repository
        visibility: Visibility controller
        user_role: Authenticated user role
        tenant_id: Current tenant ID

    Returns:
        Chain with filtered steps based on user role

    Raises:
        HTTPException: 404 if chain not found, 403 if access denied
    """
    # Retrieve chain
    chain = await repository.get_by_id(chain_id)

    if not chain:
        raise HTTPException(status_code=404, detail="Chain not found")

    # Check tenant access
    if tenant_id and chain.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to chain")

    # Apply visibility filtering
    filtered_chain = visibility.filter_chain(chain, user_role)

    return ChainResponse(
        id=filtered_chain.id,
        task_id=filtered_chain.task_id,
        agent_id=filtered_chain.agent_id,
        status=filtered_chain.status,
        started_at=filtered_chain.started_at,
        completed_at=filtered_chain.completed_at,
        metrics=ChainMetadataResponse(**filtered_chain.metrics.model_dump()),
        child_chain_ids=filtered_chain.child_chain_ids,
        tenant_id=filtered_chain.tenant_id,
        steps=[step.model_dump() for step in filtered_chain.steps],
    )


@router.get(
    "/tasks/{task_id}/chains",
    response_model=list[ChainSummaryResponse],
    dependencies=[Depends(require_permission(Permission.CHAIN_READ))],
)
async def get_task_chains(
    task_id: str,
    repository: ChainRepository = Depends(get_chain_repository),
    tenant_id: Optional[str] = Depends(get_current_tenant),
) -> list[ChainSummaryResponse]:
    """Get all chains for a specific task.

    Args:
        task_id: Task identifier
        repository: Chain repository
        tenant_id: Current tenant ID

    Returns:
        List of chains for the task

    Raises:
        HTTPException: 404 if no chains found
    """
    chains = await repository.get_by_task(task_id)

    if not chains:
        raise HTTPException(status_code=404, detail="No chains found for task")

    # Filter by tenant if applicable
    if tenant_id:
        chains = [c for c in chains if c.tenant_id == tenant_id]

    return [
        ChainSummaryResponse(
            id=chain.id,
            task_id=chain.task_id,
            agent_id=chain.agent_id,
            status=chain.status,
            started_at=chain.started_at,
            completed_at=chain.completed_at,
            metrics=ChainMetadataResponse(**chain.metrics.model_dump()),
            tenant_id=chain.tenant_id,
        )
        for chain in chains
    ]


@router.get(
    "/chains/{chain_id}/steps",
    response_model=StepListResponse,
    dependencies=[Depends(require_permission(Permission.CHAIN_READ))],
)
async def get_chain_steps(
    chain_id: UUID,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    repository: ChainRepository = Depends(get_chain_repository),
    visibility: VisibilityController = Depends(get_visibility_controller),
    user_role: Optional[Role] = Depends(get_user_role),
    tenant_id: Optional[str] = Depends(get_current_tenant),
) -> StepListResponse:
    """Get paginated steps for a chain.

    Args:
        chain_id: Chain identifier
        limit: Maximum number of steps to return
        offset: Number of steps to skip
        repository: Chain repository
        visibility: Visibility controller
        user_role: Authenticated user role
        tenant_id: Current tenant ID

    Returns:
        Paginated list of steps

    Raises:
        HTTPException: 404 if chain not found, 403 if access denied
    """
    # Retrieve chain
    chain = await repository.get_by_id(chain_id)

    if not chain:
        raise HTTPException(status_code=404, detail="Chain not found")

    # Check tenant access
    if tenant_id and chain.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to chain")

    # Apply visibility filtering
    filtered_chain = visibility.filter_chain(chain, user_role)

    # Apply pagination
    total = len(filtered_chain.steps)
    paginated_steps = filtered_chain.steps[offset : offset + limit]

    return StepListResponse(
        steps=[step.model_dump() for step in paginated_steps],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/tenants/{tenant_id}/chains",
    response_model=ChainListResponse,
    dependencies=[Depends(require_permission(Permission.CHAIN_READ))],
)
async def list_tenant_chains(
    tenant_id: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    status: Optional[ChainStatus] = Query(None),
    repository: ChainRepository = Depends(get_chain_repository),
    current_tenant: Optional[str] = Depends(get_current_tenant),
) -> ChainListResponse:
    """List chains for a tenant with filtering and pagination.

    Args:
        tenant_id: Tenant identifier
        limit: Maximum number of chains to return
        offset: Number of chains to skip
        status: Optional status filter
        repository: Chain repository
        current_tenant: Current tenant ID from auth

    Returns:
        Paginated list of chains

    Raises:
        HTTPException: 403 if accessing different tenant
    """
    # Verify tenant access
    if current_tenant and current_tenant != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to tenant chains")

    # Retrieve chains
    chains = await repository.list_by_tenant(tenant_id, limit=limit, offset=offset)

    # Apply status filter if provided
    if status:
        chains = [c for c in chains if c.status == status]

    # Count total (would need separate query in production)
    # For now, return the limited set
    total = len(chains)

    return ChainListResponse(
        chains=[
            ChainSummaryResponse(
                id=chain.id,
                task_id=chain.task_id,
                agent_id=chain.agent_id,
                status=chain.status,
                started_at=chain.started_at,
                completed_at=chain.completed_at,
                metrics=ChainMetadataResponse(**chain.metrics.model_dump()),
                tenant_id=chain.tenant_id,
            )
            for chain in chains
        ],
        total=total,
        limit=limit,
        offset=offset,
    )
