"""Public skill library API endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from omniforge.api.dependencies import get_db_session
from omniforge.builder.discovery import SkillDiscoveryService
from omniforge.builder.models import PublicSkill, PublicSkillStatus
from omniforge.builder.repository import PublicSkillRepository

router = APIRouter(prefix="/skills", tags=["skills"])


class CreatePublicSkillRequest(BaseModel):
    """Request to create a new public skill."""

    id: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1, max_length=64)
    description: str = Field(..., min_length=1, max_length=1024)
    content: str = Field(..., min_length=1)
    author_id: str = Field(..., min_length=1, max_length=64)
    tags: list[str] = Field(default_factory=list)
    integrations: list[str] = Field(default_factory=list)


class SkillDiscoveryRequest(BaseModel):
    """Request for skill discovery based on context."""

    description: str = Field(..., min_length=1)
    integrations: Optional[list[str]] = None
    limit: int = Field(default=5, ge=1, le=20)


@router.post("/", response_model=PublicSkill, status_code=201)
async def create_public_skill(
    request: CreatePublicSkillRequest,
    session: AsyncSession = Depends(get_db_session),
) -> PublicSkill:
    """Create a new public skill.

    Args:
        request: Skill creation request
        session: Database session

    Returns:
        Created PublicSkill

    Raises:
        HTTPException: If skill with same name already exists
    """
    repo = PublicSkillRepository(session)

    # Check if skill with same name exists
    existing = await repo.get_by_name(request.name)
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Skill with name '{request.name}' already exists",
        )

    # Create skill with PENDING status
    skill = PublicSkill(
        id=request.id,
        name=request.name,
        description=request.description,
        content=request.content,
        author_id=request.author_id,
        tags=request.tags,
        integrations=request.integrations,
        status=PublicSkillStatus.PENDING,
    )

    created = await repo.create(skill)
    await session.commit()

    return created


@router.get("/{skill_id}", response_model=PublicSkill)
async def get_public_skill(
    skill_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> PublicSkill:
    """Get a public skill by ID.

    Args:
        skill_id: Skill ID
        session: Database session

    Returns:
        PublicSkill

    Raises:
        HTTPException: If skill not found
    """
    repo = PublicSkillRepository(session)
    skill = await repo.get_by_id(skill_id)

    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    return skill


@router.get("/", response_model=list[PublicSkill])
async def search_public_skills(
    keyword: Optional[str] = Query(None, description="Search keyword"),
    tags: Optional[list[str]] = Query(None, description="Filter by tags"),
    integration: Optional[str] = Query(None, description="Filter by integration"),
    status: str = Query("approved", description="Filter by status"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> list[PublicSkill]:
    """Search and browse public skills.

    Args:
        keyword: Search term for name/description
        tags: Filter by specific tags (OR condition)
        integration: Filter by integration type
        status: Filter by status (default: approved)
        limit: Maximum number of results
        offset: Number of results to skip
        session: Database session

    Returns:
        List of matching PublicSkill objects
    """
    repo = PublicSkillRepository(session)

    # If integration filter specified, use get_by_integration
    if integration:
        return await repo.get_by_integration(
            integration=integration,
            status=status,
            limit=limit,
        )

    # Otherwise use general search
    return await repo.search(
        keyword=keyword,
        tags=tags,
        status=status,
        limit=limit,
        offset=offset,
    )


@router.get("/popular/top", response_model=list[PublicSkill])
async def get_popular_skills(
    limit: int = Query(10, ge=1, le=50),
    session: AsyncSession = Depends(get_db_session),
) -> list[PublicSkill]:
    """Get most popular public skills.

    Args:
        limit: Maximum number of results
        session: Database session

    Returns:
        List of top skills ordered by usage_count
    """
    repo = PublicSkillRepository(session)
    return await repo.get_top_skills(limit=limit)


@router.post("/discover", response_model=list)
async def discover_skills(
    request: SkillDiscoveryRequest,
    session: AsyncSession = Depends(get_db_session),
) -> list:
    """Discover relevant skills based on conversation context.

    Args:
        request: Discovery request with description and requirements
        session: Database session

    Returns:
        List of SkillRecommendation objects
    """
    repo = PublicSkillRepository(session)
    discovery = SkillDiscoveryService(repo)

    recommendations = await discovery.discover_by_context(
        description=request.description,
        integrations=request.integrations,
        limit=request.limit,
    )

    return recommendations


@router.post("/{skill_id}/use", response_model=PublicSkill)
async def increment_skill_usage(
    skill_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> PublicSkill:
    """Increment usage count when skill is added to an agent.

    Args:
        skill_id: Skill ID
        session: Database session

    Returns:
        Updated PublicSkill

    Raises:
        HTTPException: If skill not found
    """
    repo = PublicSkillRepository(session)
    updated = await repo.increment_usage_count(skill_id)

    if not updated:
        raise HTTPException(status_code=404, detail="Skill not found")

    await session.commit()
    return updated


@router.patch("/{skill_id}/status")
async def update_skill_status(
    skill_id: str,
    status: str = Query(..., pattern="^(pending|approved|rejected|archived)$"),
    session: AsyncSession = Depends(get_db_session),
) -> PublicSkill:
    """Update skill approval status (admin only).

    Args:
        skill_id: Skill ID
        status: New status
        session: Database session

    Returns:
        Updated PublicSkill

    Raises:
        HTTPException: If skill not found
    """
    repo = PublicSkillRepository(session)
    updated = await repo.update_status(skill_id, status)

    if not updated:
        raise HTTPException(status_code=404, detail="Skill not found")

    await session.commit()
    return updated


@router.delete("/{skill_id}", status_code=204)
async def delete_public_skill(
    skill_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    """Delete a public skill.

    Args:
        skill_id: Skill ID
        session: Database session

    Raises:
        HTTPException: If skill not found
    """
    repo = PublicSkillRepository(session)
    deleted = await repo.delete(skill_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Skill not found")

    await session.commit()
