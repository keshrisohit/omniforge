"""FastAPI application factory for OmniForge Chat API.

This module provides the application factory pattern for creating
configured FastAPI instances with all necessary middleware, routes,
and error handlers.
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

from omniforge.api.middleware.correlation import CorrelationIdMiddleware
from omniforge.api.middleware.error_handler import setup_error_handlers
from omniforge.api.middleware.tenant import TenantMiddleware
from omniforge.api.routes.agents import router as agents_router
from omniforge.api.routes.builder_agents import router as builder_agents_router
from omniforge.api.routes.chains import router as chains_router
from omniforge.api.routes.chat import router as chat_router
from omniforge.api.routes.conversation import router as conversation_router
from omniforge.api.routes.health import router as health_router
from omniforge.api.routes.oauth import router as oauth_router
from omniforge.api.routes.prompts import router as prompts_router
from omniforge.api.routes.tasks import router as tasks_router
from omniforge.execution.lifecycle import shutdown_scheduler, startup_scheduler
from omniforge.observability.logging import setup_logging
from omniforge.observability.metrics import get_metrics_collector
from omniforge.storage.database import Database, DatabaseConfig

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifespan events.

    Handles startup and shutdown of the agent scheduler.

    Args:
        app: FastAPI application instance

    Yields:
        None during application runtime
    """
    # Setup structured logging
    log_level = os.getenv("LOG_LEVEL", "INFO")
    json_logs = os.getenv("JSON_LOGS", "true").lower() == "true"
    setup_logging(log_level=log_level, json_logs=json_logs)

    # Startup: Initialize database and scheduler
    logger.info("Application startup: Initializing database and scheduler")

    # Get database URL from environment or use default
    db_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./omniforge.db")
    database = Database(DatabaseConfig(url=db_url))

    # Create tables if they don't exist
    await database.create_tables()

    # Start scheduler
    await startup_scheduler(database)

    logger.info("Application startup complete")

    try:
        yield
    finally:
        # Shutdown: Stop scheduler and close database
        logger.info("Application shutdown: Stopping scheduler and closing database")
        await shutdown_scheduler()
        await database.close()
        logger.info("Application shutdown complete")


def create_app() -> FastAPI:
    """Create and configure a FastAPI application instance.

    This factory function creates a FastAPI application with:
    - CORS middleware configured for development
    - Error handling middleware for consistent error responses
    - Chat API routes mounted at /api/v1
    - Health check endpoint for monitoring
    - Agent scheduler with automatic startup/shutdown

    Returns:
        Configured FastAPI application instance

    Examples:
        >>> app = create_app()
        >>> # Use with uvicorn
        >>> # uvicorn omniforge.api.app:app --reload
    """
    # Create FastAPI application with lifespan manager
    app = FastAPI(
        title="OmniForge Chat API",
        version="0.1.0",
        description="Enterprise-grade chat API with streaming support",
        lifespan=lifespan,
    )

    # Add CORS middleware for development
    # TODO: Configure allowed origins for production deployment
    app.add_middleware(
        CORSMiddleware,  # type: ignore[arg-type]
        allow_origins=["*"],  # Allow all origins in development
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add correlation ID middleware for request tracing
    app.add_middleware(CorrelationIdMiddleware)  # type: ignore[arg-type]

    # Add tenant middleware for multi-tenancy support
    app.add_middleware(TenantMiddleware)  # type: ignore[arg-type]

    # Setup error handlers
    setup_error_handlers(app)

    # Include routers
    app.include_router(agents_router)
    app.include_router(tasks_router)
    app.include_router(chains_router)
    app.include_router(chat_router)
    app.include_router(prompts_router)
    app.include_router(conversation_router)
    app.include_router(builder_agents_router)
    app.include_router(oauth_router)
    app.include_router(health_router)

    # Prometheus metrics endpoint
    @app.get("/metrics")
    async def metrics() -> Response:
        """Prometheus metrics endpoint.

        Returns:
            Metrics in Prometheus exposition format

        Examples:
            >>> GET /metrics
            >>> # HELP agent_executions_total Total number of agent executions
            >>> # TYPE agent_executions_total counter
            >>> agent_executions_total{status="success",agent_id="agent-1"} 42.0
        """
        metrics_collector = get_metrics_collector()
        metrics_data = metrics_collector.generate_metrics()
        return Response(
            content=metrics_data,
            media_type="text/plain; version=0.0.4; charset=utf-8",
        )

    return app


# Module-level app instance for uvicorn
app = create_app()
