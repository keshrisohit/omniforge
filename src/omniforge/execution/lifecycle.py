"""FastAPI lifecycle hooks for agent scheduler.

This module provides lifecycle management for the AgentScheduler, including
startup and shutdown hooks, schedule persistence, and automatic recovery.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from fastapi import FastAPI

from omniforge.builder.repository import AgentConfigRepository
from omniforge.execution.scheduler import AgentScheduler, ScheduleConfig
from omniforge.storage.database import Database

logger = logging.getLogger(__name__)

# Global scheduler instance
_scheduler: Optional[AgentScheduler] = None
_database: Optional[Database] = None


async def execute_scheduled_agent(agent_id: str, triggered_by: str) -> None:
    """Execute a scheduled agent.

    This is the callback function that the scheduler calls when a schedule triggers.
    It creates a database session and executes the agent.

    Args:
        agent_id: Agent ID to execute
        triggered_by: Trigger source (should be "scheduler")
    """
    logger.info(f"Executing agent {agent_id} (triggered by: {triggered_by})")

    if not _database:
        logger.error("Database not initialized, cannot execute agent")
        return

    try:
        # Log execution trigger
        # In a real implementation, this would create a database session and:
        # 1. Retrieve agent config with tenant_id using AgentConfigRepository(session)
        # 2. Create AgentExecution record
        # 3. Execute agent skills
        # 4. Update execution status
        logger.info(
            f"Agent {agent_id} scheduled execution triggered. "
            f"Execution tracking would be implemented here."
        )

        # TODO: Implement actual agent execution logic with database session

    except Exception as e:
        logger.error(f"Failed to execute scheduled agent {agent_id}: {e}", exc_info=True)
        raise


async def load_schedules_from_database(
    scheduler: AgentScheduler,
    database: Database,
) -> int:
    """Load and restore schedules from database.

    Loads all active scheduled agents from the database and registers them
    with the scheduler.

    Args:
        scheduler: AgentScheduler instance
        database: Database instance

    Returns:
        Number of schedules loaded
    """
    logger.info("Loading schedules from database")
    loaded_count = 0

    try:
        async with database.session() as session:
            # Get all scheduled agents using the repository method
            repo = AgentConfigRepository(session)

            # Get all active scheduled agents
            scheduled_agents = await repo.list_scheduled_agents()

            logger.info(f"Found {len(scheduled_agents)} scheduled agents in database")

            # Add schedule for each agent
            for agent in scheduled_agents:
                if not agent.id or not agent.schedule:
                    logger.warning(f"Skipping agent {agent.name}: missing id or schedule")
                    continue

                try:
                    config = ScheduleConfig(
                        agent_id=agent.id,
                        cron_expression=agent.schedule,
                        timezone="UTC",  # TODO: Support per-agent timezone
                        enabled=True,
                    )

                    await scheduler.add_schedule(config)
                    loaded_count += 1
                    logger.info(f"Loaded schedule for agent {agent.id}: {agent.schedule}")

                except Exception as e:
                    logger.error(
                        f"Failed to load schedule for agent {agent.id}: {e}",
                        exc_info=True,
                    )
                    # Continue loading other schedules

    except Exception as e:
        logger.error(f"Failed to load schedules from database: {e}", exc_info=True)
        # Don't raise - allow scheduler to start even if loading fails

    logger.info(f"Loaded {loaded_count} schedules from database")
    return loaded_count


async def startup_scheduler(database: Database) -> AgentScheduler:
    """Start the agent scheduler.

    This should be called during FastAPI application startup.

    Args:
        database: Database instance for schedule persistence

    Returns:
        Started AgentScheduler instance
    """
    global _scheduler, _database

    logger.info("Starting agent scheduler")

    # Create scheduler instance
    _scheduler = AgentScheduler(
        execution_callback=execute_scheduled_agent,
        timezone="UTC",
        misfire_grace_time=3600,
    )

    # Store database reference
    _database = database

    # Start scheduler
    await _scheduler.start()

    # Load schedules from database
    await load_schedules_from_database(_scheduler, database)

    logger.info("Agent scheduler startup complete")
    return _scheduler


async def shutdown_scheduler() -> None:
    """Shutdown the agent scheduler.

    This should be called during FastAPI application shutdown.
    """
    global _scheduler

    if not _scheduler:
        logger.warning("Scheduler not initialized, skipping shutdown")
        return

    logger.info("Shutting down agent scheduler")
    await _scheduler.stop()
    _scheduler = None

    logger.info("Agent scheduler shutdown complete")


def get_scheduler() -> Optional[AgentScheduler]:
    """Get the global scheduler instance.

    Returns:
        AgentScheduler instance if initialized, None otherwise
    """
    return _scheduler


def get_database() -> Optional[Database]:
    """Get the global database instance.

    Returns:
        Database instance if initialized, None otherwise
    """
    return _database


@asynccontextmanager
async def scheduler_lifespan(
    app: FastAPI,
    database: Database,
) -> AsyncGenerator[None, None]:
    """Lifespan context manager for agent scheduler.

    This can be used with FastAPI's lifespan parameter to manage scheduler
    startup and shutdown.

    Example:
        >>> from functools import partial
        >>> db = Database(DatabaseConfig())
        >>> app = FastAPI(lifespan=partial(scheduler_lifespan, database=db))

    Args:
        app: FastAPI application instance
        database: Database instance

    Yields:
        None during application runtime
    """
    # Startup
    logger.info("FastAPI lifespan: Starting scheduler")
    await startup_scheduler(database)

    try:
        yield
    finally:
        # Shutdown
        logger.info("FastAPI lifespan: Stopping scheduler")
        await shutdown_scheduler()
