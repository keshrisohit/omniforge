"""Health check endpoint for monitoring and load balancers.

This module provides comprehensive health checks for database,
scheduler, and LLM provider connectivity.
"""

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from omniforge.execution.lifecycle import get_database, get_scheduler
from omniforge.observability.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["health"])


class HealthCheckComponent(BaseModel):
    """Health status of a single component.

    Attributes:
        status: Component status (healthy, unhealthy, degraded)
        message: Optional status message or error details
    """

    status: str
    message: str | None = None


class HealthCheckResponse(BaseModel):
    """Overall health check response.

    Attributes:
        status: Overall system status (healthy, unhealthy, degraded)
        components: Status of individual components
        version: Application version
    """

    status: str
    components: dict[str, HealthCheckComponent]
    version: str = "0.1.0"


async def check_database_health() -> HealthCheckComponent:
    """Check database connectivity and health.

    Returns:
        HealthCheckComponent with database status

    Example:
        >>> component = await check_database_health()
        >>> print(component.status)
        'healthy'
    """
    try:
        database = get_database()
        if database is None:
            return HealthCheckComponent(
                status="unhealthy",
                message="Database not initialized",
            )

        # Simple query to verify database connectivity
        await database.health_check()

        return HealthCheckComponent(
            status="healthy",
            message="Database connection successful",
        )
    except Exception as e:
        logger.error("database_health_check_failed", error=str(e))
        return HealthCheckComponent(
            status="unhealthy",
            message=f"Database error: {str(e)}",
        )


async def check_scheduler_health() -> HealthCheckComponent:
    """Check scheduler status and health.

    Returns:
        HealthCheckComponent with scheduler status

    Example:
        >>> component = await check_scheduler_health()
        >>> print(component.status)
        'healthy'
    """
    try:
        scheduler = get_scheduler()
        if scheduler is None:
            return HealthCheckComponent(
                status="unhealthy",
                message="Scheduler not initialized",
            )

        # Check if scheduler is running
        if scheduler.running:
            return HealthCheckComponent(
                status="healthy",
                message="Scheduler running normally",
            )
        else:
            return HealthCheckComponent(
                status="unhealthy",
                message="Scheduler not running",
            )
    except Exception as e:
        logger.error("scheduler_health_check_failed", error=str(e))
        return HealthCheckComponent(
            status="unhealthy",
            message=f"Scheduler error: {str(e)}",
        )


async def check_llm_health() -> HealthCheckComponent:
    """Check LLM provider connectivity.

    Returns:
        HealthCheckComponent with LLM status

    Example:
        >>> component = await check_llm_health()
        >>> print(component.status)
        'healthy'
    """
    try:
        # For now, just check if LiteLLM is importable
        # In the future, we could make a lightweight API call
        import litellm  # noqa: F401

        return HealthCheckComponent(
            status="healthy",
            message="LLM provider available",
        )
    except Exception as e:
        logger.error("llm_health_check_failed", error=str(e))
        return HealthCheckComponent(
            status="degraded",
            message=f"LLM provider error: {str(e)}",
        )


@router.get("/health", response_model=HealthCheckResponse)
async def health_check() -> JSONResponse:
    """Comprehensive health check endpoint.

    Checks the health of:
    - Database connectivity
    - Scheduler status
    - LLM provider availability

    Returns:
        200 OK if all components are healthy
        503 Service Unavailable if any critical component is unhealthy

    Response Body:
        {
            "status": "healthy",
            "components": {
                "database": {"status": "healthy", "message": "..."},
                "scheduler": {"status": "healthy", "message": "..."},
                "llm": {"status": "healthy", "message": "..."}
            },
            "version": "0.1.0"
        }

    Example:
        >>> GET /health
        >>> {
        ...     "status": "healthy",
        ...     "components": {
        ...         "database": {"status": "healthy"},
        ...         "scheduler": {"status": "healthy"},
        ...         "llm": {"status": "healthy"}
        ...     }
        ... }
    """
    # Check all components
    database_health = await check_database_health()
    scheduler_health = await check_scheduler_health()
    llm_health = await check_llm_health()

    components = {
        "database": database_health,
        "scheduler": scheduler_health,
        "llm": llm_health,
    }

    # Determine overall status
    # unhealthy if any critical component is unhealthy
    # degraded if any component is degraded
    # healthy if all components are healthy
    statuses = [c.status for c in components.values()]

    if "unhealthy" in statuses:
        overall_status = "unhealthy"
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    elif "degraded" in statuses:
        overall_status = "degraded"
        status_code = status.HTTP_200_OK
    else:
        overall_status = "healthy"
        status_code = status.HTTP_200_OK

    response = HealthCheckResponse(
        status=overall_status,
        components=components,
    )

    logger.info(
        "health_check_completed",
        overall_status=overall_status,
        database=database_health.status,
        scheduler=scheduler_health.status,
        llm=llm_health.status,
    )

    return JSONResponse(
        status_code=status_code,
        content=response.model_dump(),
    )
