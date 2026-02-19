"""Agent scheduler for scheduled execution using APScheduler.

This module provides the AgentScheduler class for managing scheduled agent executions
with timezone-aware cron scheduling, database persistence, and automatic recovery.
"""

import logging
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Awaitable, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler  # type: ignore[import-untyped]
from apscheduler.triggers.cron import CronTrigger  # type: ignore[import-untyped]
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


class ScheduleConfig(BaseModel):
    """Schedule configuration for an agent.

    Attributes:
        agent_id: Unique agent identifier
        cron_expression: Cron expression for scheduling (e.g., "0 8 * * MON")
        timezone: IANA timezone identifier (default: "UTC")
        enabled: Whether schedule is active
        last_scheduled_run: Last time the schedule triggered
        next_scheduled_run: Next scheduled run time
    """

    agent_id: str = Field(..., min_length=1)
    cron_expression: str = Field(..., min_length=1)
    timezone: str = Field(default="UTC")
    enabled: bool = Field(default=True)
    last_scheduled_run: Optional[datetime] = None
    next_scheduled_run: Optional[datetime] = None

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: str) -> str:
        """Validate timezone is a valid IANA identifier."""
        import zoneinfo

        try:
            zoneinfo.ZoneInfo(v)
        except zoneinfo.ZoneInfoNotFoundError as e:
            raise ValueError(f"Invalid timezone '{v}': {e}") from e
        return v

    @field_validator("cron_expression")
    @classmethod
    def validate_cron(cls, v: str) -> str:
        """Validate cron expression is valid."""
        from croniter import croniter  # type: ignore[import-untyped]

        try:
            croniter(v)
        except (ValueError, KeyError) as e:
            raise ValueError(f"Invalid cron expression '{v}': {e}") from e
        return v


class AgentScheduler:
    """Agent scheduler using APScheduler.

    Manages scheduled execution of agents with timezone-aware cron scheduling,
    database persistence, and automatic recovery after restart.

    Example:
        >>> scheduler = AgentScheduler(execution_callback=execute_agent)
        >>> await scheduler.start()
        >>> config = ScheduleConfig(
        ...     agent_id="agent-123",
        ...     cron_expression="0 8 * * MON",
        ...     timezone="America/New_York"
        ... )
        >>> await scheduler.add_schedule(config)
        >>> await scheduler.stop()
    """

    def __init__(
        self,
        execution_callback: Callable[[str, str], Awaitable[None]],
        timezone: str = "UTC",
        misfire_grace_time: int = 3600,
    ):
        """Initialize the agent scheduler.

        Args:
            execution_callback: Async function to call when agent execution is triggered.
                Should accept (agent_id: str, triggered_by: str) as parameters.
            timezone: Default timezone for scheduler (default: "UTC")
            misfire_grace_time: Grace time in seconds for missed executions (default: 3600)
                If a scheduled run is missed by more than this time, it will be skipped.
        """
        self.execution_callback: Callable[[str, str], Awaitable[None]] = execution_callback
        self.default_timezone = timezone
        self.misfire_grace_time = misfire_grace_time

        # Initialize APScheduler with AsyncIOScheduler
        self.scheduler = AsyncIOScheduler(timezone=timezone)

        # Track active schedules
        self._active_schedules: dict[str, ScheduleConfig] = {}

    async def start(self) -> None:
        """Start the scheduler.

        This should be called during application startup.
        """
        logger.info("Starting agent scheduler")
        self.scheduler.start()
        logger.info("Agent scheduler started successfully")

    async def stop(self) -> None:
        """Stop the scheduler.

        This should be called during application shutdown.
        Waits for all running jobs to complete.
        """
        logger.info("Stopping agent scheduler")
        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)
        logger.info("Agent scheduler stopped successfully")

    async def add_schedule(self, config: ScheduleConfig) -> None:
        """Add or update a schedule for an agent.

        Args:
            config: Schedule configuration

        Raises:
            ValueError: If schedule configuration is invalid
        """
        if not config.enabled:
            logger.info(f"Schedule for agent {config.agent_id} is disabled, skipping add")
            return

        # Remove existing schedule if present
        await self.remove_schedule(config.agent_id)

        # Create job ID
        job_id = self._get_job_id(config.agent_id)

        try:
            # Create cron trigger with timezone
            trigger = CronTrigger.from_crontab(
                config.cron_expression,
                timezone=config.timezone,
            )

            # Add job to scheduler
            self.scheduler.add_job(
                self._execute_scheduled_agent,
                trigger=trigger,
                id=job_id,
                args=[config.agent_id],
                misfire_grace_time=self.misfire_grace_time,
                coalesce=False,  # Don't coalesce missed executions
                max_instances=1,  # Only one instance per agent at a time
                replace_existing=True,
            )

            # Store active schedule
            self._active_schedules[config.agent_id] = config

            # Get next run time
            job = self.scheduler.get_job(job_id)
            next_run = job.next_run_time if job else None

            logger.info(
                f"Added schedule for agent {config.agent_id}: "
                f"{config.cron_expression} ({config.timezone}). "
                f"Next run: {next_run}"
            )

        except Exception as e:
            logger.error(f"Failed to add schedule for agent {config.agent_id}: {e}")
            raise ValueError(f"Failed to add schedule: {e}") from e

    async def remove_schedule(self, agent_id: str) -> bool:
        """Remove a schedule for an agent.

        Args:
            agent_id: Agent ID

        Returns:
            True if schedule was removed, False if no schedule existed
        """
        job_id = self._get_job_id(agent_id)

        # Remove job from scheduler
        job = self.scheduler.get_job(job_id)
        job_existed = job is not None
        if job:
            job.remove()
            logger.info(f"Removed schedule for agent {agent_id}")

        # Remove from active schedules
        removed = self._active_schedules.pop(agent_id, None)

        return job_existed or removed is not None

    async def update_schedule(self, config: ScheduleConfig) -> None:
        """Update an existing schedule.

        This is equivalent to removing and re-adding the schedule.

        Args:
            config: Updated schedule configuration

        Raises:
            ValueError: If schedule configuration is invalid
        """
        logger.info(f"Updating schedule for agent {config.agent_id}")
        await self.add_schedule(config)

    def get_schedule(self, agent_id: str) -> Optional[ScheduleConfig]:
        """Get schedule configuration for an agent.

        Args:
            agent_id: Agent ID

        Returns:
            ScheduleConfig if schedule exists, None otherwise
        """
        return self._active_schedules.get(agent_id)

    def list_schedules(self) -> list[ScheduleConfig]:
        """List all active schedules.

        Returns:
            List of ScheduleConfig objects
        """
        return list(self._active_schedules.values())

    async def _execute_scheduled_agent(self, agent_id: str) -> None:
        """Execute a scheduled agent.

        This is the callback function that APScheduler calls when a schedule triggers.

        Args:
            agent_id: Agent ID to execute
        """
        logger.info(f"Executing scheduled agent: {agent_id}")

        # Update last scheduled run
        if agent_id in self._active_schedules:
            self._active_schedules[agent_id].last_scheduled_run = datetime.now(timezone.utc)

        try:
            # Call the execution callback with triggered_by='scheduler'
            await self.execution_callback(agent_id, "scheduler")
            logger.info(f"Successfully executed scheduled agent: {agent_id}")

        except Exception as e:
            # Log error but don't raise - let scheduler continue
            logger.error(f"Failed to execute scheduled agent {agent_id}: {e}", exc_info=True)

    def _get_job_id(self, agent_id: str) -> str:
        """Generate job ID from agent ID.

        Args:
            agent_id: Agent ID

        Returns:
            Job ID for APScheduler
        """
        return f"agent_{agent_id}"

    def get_next_run_time(self, agent_id: str) -> Optional[datetime]:
        """Get next scheduled run time for an agent.

        Args:
            agent_id: Agent ID

        Returns:
            Next run time if scheduled, None otherwise
        """
        job_id = self._get_job_id(agent_id)
        job = self.scheduler.get_job(job_id)
        return job.next_run_time if job else None

    def is_running(self) -> bool:
        """Check if scheduler is running.

        Returns:
            True if scheduler is running, False otherwise
        """
        return bool(self.scheduler.running)
