"""Prompt management API route handlers.

This module provides FastAPI route handlers for all prompt management operations
including CRUD, versioning, composition, experiments, and cache management.
"""

from typing import Any, Optional, Union

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field

from omniforge.api.dependencies import get_current_tenant
from omniforge.prompts.enums import MergeBehavior, PromptLayer
from omniforge.prompts.errors import (
    PromptError,
    PromptVersionNotFoundError,
)
from omniforge.prompts.sdk.manager import PromptManager

# Create router with prefix and tags
router = APIRouter(prefix="/api/v1/prompts", tags=["prompts"])

# Shared PromptManager instance for all requests
_prompt_manager = PromptManager()


# Request/Response Models


class MergePointRequest(BaseModel):
    """Request model for merge point definition."""

    name: str = Field(..., min_length=1, max_length=255, description="Merge point name")
    behavior: MergeBehavior = Field(..., description="Merge behavior (append/replace/inject)")
    required: bool = Field(False, description="Whether child layers must provide content")
    locked: bool = Field(False, description="Whether this merge point can be modified")
    description: Optional[str] = Field(None, description="Human-readable description")


class PromptCreateRequest(BaseModel):
    """Request model for creating a prompt."""

    layer: PromptLayer = Field(..., description="Hierarchical layer for the prompt")
    name: str = Field(..., min_length=1, max_length=255, description="Prompt name")
    content: str = Field(..., min_length=1, description="Prompt template content")
    scope_id: str = Field(..., description="Scope identifier (e.g., agent_id, tenant_id)")
    created_by: str = Field(..., description="ID of user creating the prompt")
    merge_points: Optional[list[dict[str, Any]]] = Field(
        None, description="List of merge point definitions"
    )
    variables_schema: Optional[dict[str, Any]] = Field(None, description="Variable schema")


class PromptUpdateRequest(BaseModel):
    """Request model for updating a prompt."""

    content: str = Field(..., min_length=1, description="New prompt content")
    change_message: str = Field(..., min_length=1, description="Description of changes")
    changed_by: str = Field(..., description="ID of user making the change")
    merge_points: Optional[list[dict[str, Any]]] = Field(None, description="Updated merge points")
    variables_schema: Optional[dict[str, Any]] = Field(None, description="Updated variable schema")


class PromptComposeRequest(BaseModel):
    """Request model for composing a prompt."""

    agent_id: str = Field(..., description="ID of the agent requesting the prompt")
    tenant_id: Optional[str] = Field(None, description="Tenant ID (optional)")
    feature_ids: Optional[Union[str, list[str]]] = Field(
        None, description="Feature ID(s) to include"
    )
    user_input: Optional[str] = Field(None, description="User input to sanitize and inject")
    variables: Optional[dict[str, Any]] = Field(None, description="Variables for rendering")
    skip_cache: bool = Field(False, description="Bypass cache and force recomposition")


class PromptValidateRequest(BaseModel):
    """Request model for validating template syntax."""

    content: str = Field(..., description="Template content to validate")


class PromptRollbackRequest(BaseModel):
    """Request model for rolling back a prompt."""

    to_version: int = Field(..., ge=1, description="Version number to rollback to")
    rolled_back_by: str = Field(..., description="ID of user performing the rollback")


class ExperimentVariantRequest(BaseModel):
    """Request model for experiment variant."""

    id: str = Field(..., description="Variant ID")
    name: str = Field(..., description="Variant name")
    prompt_version_id: str = Field(..., description="Prompt version ID for this variant")
    traffic_percentage: float = Field(..., ge=0.0, le=100.0, description="Traffic percentage")


class ExperimentCreateRequest(BaseModel):
    """Request model for creating an experiment."""

    name: str = Field(..., min_length=1, description="Experiment name")
    description: str = Field(..., description="Experiment description")
    success_metric: str = Field(..., description="Metric to optimize")
    variants: list[dict[str, Any]] = Field(..., min_length=2, description="Experiment variants")
    created_by: Optional[str] = Field(None, description="ID of user creating experiment")


class ExperimentUpdateRequest(BaseModel):
    """Request model for updating an experiment."""

    name: Optional[str] = Field(None, description="Updated experiment name")
    description: Optional[str] = Field(None, description="Updated description")


class ExperimentPromoteRequest(BaseModel):
    """Request model for promoting a variant."""

    variant_id: str = Field(..., description="ID of variant to promote")


class PromptResponse(BaseModel):
    """Response model for a prompt."""

    id: str = Field(..., description="Prompt ID")
    layer: str = Field(..., description="Prompt layer")
    scope_id: str = Field(..., description="Scope identifier")
    name: str = Field(..., description="Prompt name")
    content: str = Field(..., description="Prompt content")
    version: int = Field(..., description="Current version number")
    tenant_id: Optional[str] = Field(None, description="Tenant ID")
    merge_points: Optional[list[dict[str, Any]]] = Field(None, description="Merge points")
    variables_schema: Optional[dict[str, Any]] = Field(None, description="Variable schema")
    is_locked: bool = Field(..., description="Whether prompt is locked")
    is_active: bool = Field(..., description="Whether prompt is active")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")


class PromptVersionResponse(BaseModel):
    """Response model for a prompt version."""

    id: str = Field(..., description="Version ID")
    prompt_id: str = Field(..., description="Prompt ID")
    version_number: int = Field(..., description="Version number")
    content: str = Field(..., description="Content at this version")
    change_message: str = Field(..., description="Description of changes")
    changed_by: Optional[str] = Field(None, description="User who made the change")
    created_at: str = Field(..., description="Creation timestamp")


class ComposedPromptResponse(BaseModel):
    """Response model for a composed prompt."""

    content: str = Field(..., description="Final composed content")
    layers_used: list[str] = Field(..., description="Layers included in composition")
    cache_hit: bool = Field(..., description="Whether result was from cache")
    composition_time_ms: float = Field(..., description="Time taken to compose (ms)")


class ValidationResponse(BaseModel):
    """Response model for template validation."""

    valid: bool = Field(..., description="Whether template is valid")
    errors: list[str] = Field(default_factory=list, description="Validation errors")


class ExperimentResponse(BaseModel):
    """Response model for an experiment."""

    id: str = Field(..., description="Experiment ID")
    prompt_id: str = Field(..., description="Prompt ID")
    name: str = Field(..., description="Experiment name")
    description: str = Field(..., description="Experiment description")
    status: str = Field(..., description="Experiment status")
    success_metric: str = Field(..., description="Success metric")
    variants: list[dict[str, Any]] = Field(..., description="Experiment variants")
    created_at: str = Field(..., description="Creation timestamp")
    started_at: Optional[str] = Field(None, description="Start timestamp")
    completed_at: Optional[str] = Field(None, description="Completion timestamp")


class CacheStatsResponse(BaseModel):
    """Response model for cache statistics."""

    enabled: bool = Field(..., description="Whether cache is enabled")
    size: Optional[int] = Field(None, description="Current cache size")
    max_size: Optional[int] = Field(None, description="Maximum cache size")
    hit_count: Optional[int] = Field(None, description="Cache hits")
    miss_count: Optional[int] = Field(None, description="Cache misses")


class ErrorResponse(BaseModel):
    """Response model for errors."""

    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[dict[str, Any]] = Field(None, description="Additional error details")


# Helper Functions


def _build_prompt_response(prompt: Any) -> PromptResponse:
    """Build a PromptResponse from a Prompt model.

    Args:
        prompt: The Prompt model instance

    Returns:
        PromptResponse with all fields populated
    """
    return PromptResponse(
        id=prompt.id,
        layer=prompt.layer.value,
        scope_id=prompt.scope_id,
        name=prompt.name,
        content=prompt.content,
        version=prompt.version,
        tenant_id=prompt.tenant_id,
        merge_points=(
            [mp.model_dump() for mp in prompt.merge_points] if prompt.merge_points else None
        ),
        variables_schema=prompt.variables_schema.model_dump() if prompt.variables_schema else None,
        is_locked=prompt.is_locked,
        is_active=prompt.is_active,
        created_at=prompt.created_at.isoformat(),
        updated_at=prompt.updated_at.isoformat(),
    )


# Error Handler


def handle_prompt_error(error: PromptError) -> tuple[int, ErrorResponse]:
    """Convert PromptError to HTTP response.

    Args:
        error: The PromptError to convert

    Returns:
        Tuple of (status_code, error_response)
    """
    details = {}
    if hasattr(error, "field"):
        details["field"] = error.field
    if hasattr(error, "details"):
        details.update(error.details)

    return error.status_code, ErrorResponse(
        code=error.code, message=error.message, details=details if details else None
    )


# Prompt CRUD Endpoints


@router.post("", status_code=status.HTTP_201_CREATED, response_model=PromptResponse)
async def create_prompt(
    request: PromptCreateRequest, tenant_id: Optional[str] = Depends(get_current_tenant)
) -> PromptResponse:
    """Create a new prompt.

    Creates a prompt with the specified configuration and initial version.

    Args:
        request: Prompt creation request
        tenant_id: Current tenant ID from context

    Returns:
        Created prompt with version 1

    Raises:
        400: If validation fails
    """
    try:
        # Use tenant_id from context if available
        if tenant_id:
            _prompt_manager.tenant_id = tenant_id

        prompt = await _prompt_manager.create_prompt(
            layer=request.layer,
            name=request.name,
            content=request.content,
            scope_id=request.scope_id,
            created_by=request.created_by,
            merge_points=request.merge_points,
            variables_schema=request.variables_schema,
        )

        return _build_prompt_response(prompt)
    except PromptError as e:
        status_code, error_response = handle_prompt_error(e)
        from fastapi import HTTPException

        raise HTTPException(status_code=status_code, detail=error_response.model_dump())


@router.get("/{prompt_id}", response_model=PromptResponse)
async def get_prompt(prompt_id: str) -> PromptResponse:
    """Get a prompt by ID.

    Args:
        prompt_id: ID of the prompt to retrieve

    Returns:
        The requested prompt

    Raises:
        404: If prompt not found
    """
    try:
        prompt = await _prompt_manager.get_prompt(prompt_id)

        return _build_prompt_response(prompt)
    except PromptError as e:
        status_code, error_response = handle_prompt_error(e)
        from fastapi import HTTPException

        raise HTTPException(status_code=status_code, detail=error_response.model_dump())


@router.put("/{prompt_id}", response_model=PromptResponse)
async def update_prompt(prompt_id: str, request: PromptUpdateRequest) -> PromptResponse:
    """Update a prompt's content.

    Updates the prompt content and creates a new version.

    Args:
        prompt_id: ID of the prompt to update
        request: Update request with new content

    Returns:
        Updated prompt

    Raises:
        404: If prompt not found
        400: If validation fails
        409: If prompt is locked
    """
    try:
        prompt = await _prompt_manager.update_prompt(
            prompt_id=prompt_id,
            content=request.content,
            change_message=request.change_message,
            changed_by=request.changed_by,
            merge_points=request.merge_points,
            variables_schema=request.variables_schema,
        )

        return _build_prompt_response(prompt)
    except PromptError as e:
        status_code, error_response = handle_prompt_error(e)
        from fastapi import HTTPException

        raise HTTPException(status_code=status_code, detail=error_response.model_dump())


@router.delete("/{prompt_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_prompt(prompt_id: str) -> None:
    """Delete a prompt (soft delete).

    Args:
        prompt_id: ID of the prompt to delete

    Raises:
        404: If prompt not found
    """
    try:
        await _prompt_manager.delete_prompt(prompt_id)
    except PromptError as e:
        status_code, error_response = handle_prompt_error(e)
        from fastapi import HTTPException

        raise HTTPException(status_code=status_code, detail=error_response.model_dump())


@router.get("", response_model=list[PromptResponse])
async def list_prompts(
    tenant_id: Optional[str] = Depends(get_current_tenant),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
) -> list[PromptResponse]:
    """List prompts for a tenant.

    Args:
        tenant_id: Current tenant ID from context
        limit: Maximum number of results
        offset: Number of results to skip

    Returns:
        List of prompts
    """
    try:
        prompts = await _prompt_manager.list_prompts(
            tenant_id=tenant_id, limit=limit, offset=offset
        )

        return [_build_prompt_response(p) for p in prompts]
    except PromptError as e:
        status_code, error_response = handle_prompt_error(e)
        from fastapi import HTTPException

        raise HTTPException(status_code=status_code, detail=error_response.model_dump())


# Versioning Endpoints


@router.get("/{prompt_id}/versions", response_model=list[PromptVersionResponse])
async def list_versions(
    prompt_id: str,
    limit: int = Query(50, ge=1, le=500, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
) -> list[PromptVersionResponse]:
    """Get version history for a prompt.

    Args:
        prompt_id: ID of the prompt
        limit: Maximum number of versions
        offset: Number of versions to skip

    Returns:
        List of versions sorted by version_number descending

    Raises:
        404: If prompt not found
    """
    try:
        versions = await _prompt_manager.get_prompt_history(
            prompt_id=prompt_id, limit=limit, offset=offset
        )

        return [
            PromptVersionResponse(
                id=v.id,
                prompt_id=v.prompt_id,
                version_number=v.version_number,
                content=v.content,
                change_message=v.change_message,
                changed_by=v.changed_by,
                created_at=v.created_at.isoformat(),
            )
            for v in versions
        ]
    except PromptError as e:
        status_code, error_response = handle_prompt_error(e)
        from fastapi import HTTPException

        raise HTTPException(status_code=status_code, detail=error_response.model_dump())


@router.get("/{prompt_id}/versions/{version_number}", response_model=PromptVersionResponse)
async def get_version(prompt_id: str, version_number: int) -> PromptVersionResponse:
    """Get a specific prompt version.

    Args:
        prompt_id: ID of the prompt
        version_number: Version number to retrieve

    Returns:
        The requested version

    Raises:
        404: If prompt or version not found
    """
    try:
        versions = await _prompt_manager.get_prompt_history(prompt_id=prompt_id, limit=1000)

        # Find the specific version
        version = next((v for v in versions if v.version_number == version_number), None)
        if not version:
            raise PromptVersionNotFoundError(prompt_id, version_number)

        return PromptVersionResponse(
            id=version.id,
            prompt_id=version.prompt_id,
            version_number=version.version_number,
            content=version.content,
            change_message=version.change_message,
            changed_by=version.changed_by,
            created_at=version.created_at.isoformat(),
        )
    except PromptError as e:
        status_code, error_response = handle_prompt_error(e)
        from fastapi import HTTPException

        raise HTTPException(status_code=status_code, detail=error_response.model_dump())


@router.post("/{prompt_id}/rollback", response_model=PromptResponse)
async def rollback_prompt(prompt_id: str, request: PromptRollbackRequest) -> PromptResponse:
    """Rollback a prompt to a previous version.

    Args:
        prompt_id: ID of the prompt to rollback
        request: Rollback request with target version

    Returns:
        Updated prompt with content from target version

    Raises:
        404: If prompt or version not found
    """
    try:
        prompt = await _prompt_manager.rollback_prompt(
            prompt_id=prompt_id,
            to_version=request.to_version,
            rolled_back_by=request.rolled_back_by,
        )

        return _build_prompt_response(prompt)
    except PromptError as e:
        status_code, error_response = handle_prompt_error(e)
        from fastapi import HTTPException

        raise HTTPException(status_code=status_code, detail=error_response.model_dump())


# Composition Endpoints


@router.post("/compose", response_model=ComposedPromptResponse)
async def compose_prompt(request: PromptComposeRequest) -> ComposedPromptResponse:
    """Compose a prompt for an agent.

    Merges prompts from all layers and renders variables.

    Args:
        request: Composition request

    Returns:
        Composed prompt with metadata

    Raises:
        404: If required prompts not found
        500: If composition fails
    """
    try:
        result = await _prompt_manager.compose_prompt(
            agent_id=request.agent_id,
            tenant_id=request.tenant_id,
            feature_ids=request.feature_ids,
            user_input=request.user_input,
            variables=request.variables,
            skip_cache=request.skip_cache,
        )

        return ComposedPromptResponse(
            content=result.content,
            layers_used=[layer.value for layer in result.layers_used],
            cache_hit=result.cache_hit,
            composition_time_ms=result.composition_time_ms,
        )
    except PromptError as e:
        status_code, error_response = handle_prompt_error(e)
        from fastapi import HTTPException

        raise HTTPException(status_code=status_code, detail=error_response.model_dump())


@router.post("/preview", response_model=ComposedPromptResponse)
async def preview_prompt(request: PromptComposeRequest) -> ComposedPromptResponse:
    """Preview a composed prompt without caching.

    Same as compose but always bypasses cache.

    Args:
        request: Composition request

    Returns:
        Composed prompt with metadata
    """
    try:
        result = await _prompt_manager.compose_prompt(
            agent_id=request.agent_id,
            tenant_id=request.tenant_id,
            feature_ids=request.feature_ids,
            user_input=request.user_input,
            variables=request.variables,
            skip_cache=True,  # Always skip cache for preview
        )

        return ComposedPromptResponse(
            content=result.content,
            layers_used=[layer.value for layer in result.layers_used],
            cache_hit=result.cache_hit,
            composition_time_ms=result.composition_time_ms,
        )
    except PromptError as e:
        status_code, error_response = handle_prompt_error(e)
        from fastapi import HTTPException

        raise HTTPException(status_code=status_code, detail=error_response.model_dump())


@router.post("/validate", response_model=ValidationResponse)
async def validate_template(request: PromptValidateRequest) -> ValidationResponse:
    """Validate template syntax.

    Args:
        request: Validation request with template content

    Returns:
        Validation result with any errors
    """
    errors = _prompt_manager.validate_template(request.content)

    return ValidationResponse(valid=len(errors) == 0, errors=errors)


# Experiment Endpoints


@router.post("/{prompt_id}/experiments", status_code=status.HTTP_201_CREATED)
async def create_experiment(prompt_id: str, request: ExperimentCreateRequest) -> ExperimentResponse:
    """Create a new A/B test experiment.

    Args:
        prompt_id: ID of the prompt to experiment on
        request: Experiment creation request

    Returns:
        Created experiment in DRAFT status

    Raises:
        404: If prompt not found
        400: If validation fails
    """
    try:
        experiment = await _prompt_manager.create_experiment(
            prompt_id=prompt_id,
            name=request.name,
            description=request.description,
            success_metric=request.success_metric,
            variants=request.variants,
            created_by=request.created_by,
        )

        return ExperimentResponse(
            id=experiment.id,
            prompt_id=experiment.prompt_id,
            name=experiment.name,
            description=experiment.description,
            status=experiment.status.value,
            success_metric=experiment.success_metric,
            variants=[v.model_dump() for v in experiment.variants],
            created_at=experiment.created_at.isoformat(),
            started_at=experiment.started_at.isoformat() if experiment.started_at else None,
            completed_at=experiment.completed_at.isoformat() if experiment.completed_at else None,
        )
    except PromptError as e:
        status_code, error_response = handle_prompt_error(e)
        from fastapi import HTTPException

        raise HTTPException(status_code=status_code, detail=error_response.model_dump())


@router.get("/{prompt_id}/experiments", response_model=list[ExperimentResponse])
async def list_experiments(prompt_id: str) -> list[ExperimentResponse]:
    """List experiments for a prompt.

    Args:
        prompt_id: ID of the prompt

    Returns:
        List of experiments

    Raises:
        404: If prompt not found
    """
    try:
        # Verify prompt exists
        await _prompt_manager.get_prompt(prompt_id)

        # Get experiments from repository
        experiments = await _prompt_manager._experiment_manager.list_experiments(prompt_id)

        return [
            ExperimentResponse(
                id=e.id,
                prompt_id=e.prompt_id,
                name=e.name,
                description=e.description,
                status=e.status.value,
                success_metric=e.success_metric,
                variants=[v.model_dump() for v in e.variants],
                created_at=e.created_at.isoformat(),
                started_at=e.started_at.isoformat() if e.started_at else None,
                completed_at=e.completed_at.isoformat() if e.completed_at else None,
            )
            for e in experiments
        ]
    except PromptError as e:
        status_code, error_response = handle_prompt_error(e)
        from fastapi import HTTPException

        raise HTTPException(status_code=status_code, detail=error_response.model_dump())


@router.get("/experiments/{experiment_id}", response_model=ExperimentResponse)
async def get_experiment(experiment_id: str) -> ExperimentResponse:
    """Get an experiment by ID.

    Args:
        experiment_id: ID of the experiment

    Returns:
        The requested experiment

    Raises:
        404: If experiment not found
    """
    try:
        experiment = await _prompt_manager._experiment_manager.get_experiment(experiment_id)

        return ExperimentResponse(
            id=experiment.id,
            prompt_id=experiment.prompt_id,
            name=experiment.name,
            description=experiment.description,
            status=experiment.status.value,
            success_metric=experiment.success_metric,
            variants=[v.model_dump() for v in experiment.variants],
            created_at=experiment.created_at.isoformat(),
            started_at=experiment.started_at.isoformat() if experiment.started_at else None,
            completed_at=experiment.completed_at.isoformat() if experiment.completed_at else None,
        )
    except PromptError as e:
        status_code, error_response = handle_prompt_error(e)
        from fastapi import HTTPException

        raise HTTPException(status_code=status_code, detail=error_response.model_dump())


@router.put("/experiments/{experiment_id}", response_model=ExperimentResponse)
async def update_experiment(
    experiment_id: str, request: ExperimentUpdateRequest
) -> ExperimentResponse:
    """Update an experiment's metadata.

    Only name and description can be updated.

    Args:
        experiment_id: ID of the experiment
        request: Update request

    Returns:
        Updated experiment

    Raises:
        404: If experiment not found
    """
    try:
        experiment = await _prompt_manager._experiment_manager.get_experiment(experiment_id)

        # Update fields if provided
        if request.name is not None:
            experiment.name = request.name
        if request.description is not None:
            experiment.description = request.description

        # Save to repository
        await _prompt_manager._repository.update_experiment(experiment)

        return ExperimentResponse(
            id=experiment.id,
            prompt_id=experiment.prompt_id,
            name=experiment.name,
            description=experiment.description,
            status=experiment.status.value,
            success_metric=experiment.success_metric,
            variants=[v.model_dump() for v in experiment.variants],
            created_at=experiment.created_at.isoformat(),
            started_at=experiment.started_at.isoformat() if experiment.started_at else None,
            completed_at=experiment.completed_at.isoformat() if experiment.completed_at else None,
        )
    except PromptError as e:
        status_code, error_response = handle_prompt_error(e)
        from fastapi import HTTPException

        raise HTTPException(status_code=status_code, detail=error_response.model_dump())


@router.post("/experiments/{experiment_id}/start", response_model=ExperimentResponse)
async def start_experiment(experiment_id: str) -> ExperimentResponse:
    """Start a DRAFT or PAUSED experiment.

    Args:
        experiment_id: ID of the experiment

    Returns:
        Updated experiment with RUNNING status

    Raises:
        404: If experiment not found
        409: If experiment cannot be started
    """
    try:
        experiment = await _prompt_manager.start_experiment(experiment_id)

        return ExperimentResponse(
            id=experiment.id,
            prompt_id=experiment.prompt_id,
            name=experiment.name,
            description=experiment.description,
            status=experiment.status.value,
            success_metric=experiment.success_metric,
            variants=[v.model_dump() for v in experiment.variants],
            created_at=experiment.created_at.isoformat(),
            started_at=experiment.started_at.isoformat() if experiment.started_at else None,
            completed_at=experiment.completed_at.isoformat() if experiment.completed_at else None,
        )
    except PromptError as e:
        status_code, error_response = handle_prompt_error(e)
        from fastapi import HTTPException

        raise HTTPException(status_code=status_code, detail=error_response.model_dump())


@router.post("/experiments/{experiment_id}/stop", response_model=ExperimentResponse)
async def stop_experiment(experiment_id: str) -> ExperimentResponse:
    """Pause a RUNNING experiment.

    Args:
        experiment_id: ID of the experiment

    Returns:
        Updated experiment with PAUSED status

    Raises:
        404: If experiment not found
        409: If experiment is not RUNNING
    """
    try:
        experiment = await _prompt_manager.pause_experiment(experiment_id)

        return ExperimentResponse(
            id=experiment.id,
            prompt_id=experiment.prompt_id,
            name=experiment.name,
            description=experiment.description,
            status=experiment.status.value,
            success_metric=experiment.success_metric,
            variants=[v.model_dump() for v in experiment.variants],
            created_at=experiment.created_at.isoformat(),
            started_at=experiment.started_at.isoformat() if experiment.started_at else None,
            completed_at=experiment.completed_at.isoformat() if experiment.completed_at else None,
        )
    except PromptError as e:
        status_code, error_response = handle_prompt_error(e)
        from fastapi import HTTPException

        raise HTTPException(status_code=status_code, detail=error_response.model_dump())


@router.post("/experiments/{experiment_id}/promote", response_model=PromptResponse)
async def promote_variant(experiment_id: str, request: ExperimentPromoteRequest) -> PromptResponse:
    """Promote a winning variant to production.

    This will update the prompt to use the content from the winning variant.

    Args:
        experiment_id: ID of the experiment
        request: Request with variant ID to promote

    Returns:
        Updated prompt

    Raises:
        404: If experiment not found
        400: If variant not found
    """
    try:
        # Get experiment
        experiment = await _prompt_manager._experiment_manager.get_experiment(experiment_id)

        # Find the variant
        variant = next((v for v in experiment.variants if v.id == request.variant_id), None)
        if not variant:
            from fastapi import HTTPException

            raise HTTPException(
                status_code=400,
                detail={"code": "variant_not_found", "message": "Variant not found"},
            )

        # Get the prompt version for this variant
        # Extract version number from version_id (format: prompt_id-vN)
        version_str = variant.prompt_version_id.split("-v")[-1]
        version_number = int(version_str)

        # Rollback to this version
        prompt = await _prompt_manager.rollback_prompt(
            prompt_id=experiment.prompt_id,
            to_version=version_number,
            rolled_back_by=f"experiment_{experiment_id}_promotion",
        )

        # Complete the experiment
        results = {request.variant_id: {"promoted": True}}
        await _prompt_manager.complete_experiment(experiment_id, results)

        return _build_prompt_response(prompt)
    except PromptError as e:
        status_code, error_response = handle_prompt_error(e)
        from fastapi import HTTPException

        raise HTTPException(status_code=status_code, detail=error_response.model_dump())


# Cache Endpoints


@router.get("/cache/stats", response_model=CacheStatsResponse)
async def get_cache_stats() -> CacheStatsResponse:
    """Get cache statistics.

    Returns:
        Cache statistics including size, hits, misses
    """
    stats = _prompt_manager.get_cache_stats()

    return CacheStatsResponse(
        enabled=stats.get("enabled", False),
        size=stats.get("size"),
        max_size=stats.get("max_size"),
        hit_count=stats.get("hit_count"),
        miss_count=stats.get("miss_count"),
    )


@router.delete("/cache", status_code=status.HTTP_204_NO_CONTENT)
async def clear_cache() -> None:
    """Clear all cache entries.

    This endpoint should be restricted to admin users only.
    """
    await _prompt_manager.clear_cache()
