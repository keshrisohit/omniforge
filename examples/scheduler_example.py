"""Example demonstrating AgentScheduler usage.

This example shows how to:
1. Create an AgentScheduler with a custom execution callback
2. Add schedules with cron expressions
3. Handle schedule execution
4. Manage scheduler lifecycle
"""

import asyncio
import logging
from datetime import datetime, timezone

from omniforge.execution.scheduler import AgentScheduler, ScheduleConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Execution tracking
executions = []


async def execute_agent(agent_id: str, triggered_by: str) -> None:
    """Custom execution callback.

    This function is called by the scheduler when an agent is triggered.

    Args:
        agent_id: Agent ID to execute
        triggered_by: Trigger source (e.g., "scheduler")
    """
    timestamp = datetime.now(timezone.utc)
    logger.info(f"Executing agent {agent_id} (triggered by: {triggered_by}) at {timestamp}")

    # Track execution
    executions.append({"agent_id": agent_id, "triggered_by": triggered_by, "timestamp": timestamp})

    # Simulate agent execution
    await asyncio.sleep(0.1)

    logger.info(f"Agent {agent_id} execution completed")


async def main() -> None:
    """Main example demonstrating scheduler usage."""
    logger.info("Starting scheduler example")

    # Create scheduler with execution callback
    scheduler = AgentScheduler(
        execution_callback=execute_agent, timezone="UTC", misfire_grace_time=3600
    )

    # Start scheduler
    await scheduler.start()
    logger.info("Scheduler started")

    # Add schedules
    # Note: These are example cron expressions for demonstration
    # In real usage, these would be realistic schedules

    # Schedule 1: Agent that would run every minute (for demo purposes)
    # In production, this might be "0 8 * * *" (daily at 8am)
    config1 = ScheduleConfig(
        agent_id="agent-daily-report",
        cron_expression="* * * * *",  # Every minute (demo only)
        timezone="UTC",
    )

    # Schedule 2: Agent that would run every minute (for demo purposes)
    # In production, this might be "0 */6 * * *" (every 6 hours)
    config2 = ScheduleConfig(
        agent_id="agent-sync-data",
        cron_expression="* * * * *",  # Every minute (demo only)
        timezone="America/New_York",
    )

    await scheduler.add_schedule(config1)
    await scheduler.add_schedule(config2)

    # List all schedules
    schedules = scheduler.list_schedules()
    logger.info(f"Active schedules: {len(schedules)}")
    for schedule in schedules:
        next_run = scheduler.get_next_run_time(schedule.agent_id)
        logger.info(f"  - {schedule.agent_id}: {schedule.cron_expression} (next: {next_run})")

    # Wait for a few seconds to see schedules execute
    logger.info("Waiting 5 seconds to observe scheduled executions...")
    await asyncio.sleep(5)

    # Show execution history
    logger.info(f"\nExecution history ({len(executions)} executions):")
    for execution in executions:
        logger.info(
            f"  - {execution['agent_id']} at {execution['timestamp']} "
            f"(triggered by: {execution['triggered_by']})"
        )

    # Update a schedule
    logger.info("\nUpdating schedule for agent-daily-report...")
    config1_updated = ScheduleConfig(
        agent_id="agent-daily-report",
        cron_expression="*/2 * * * *",  # Every 2 minutes
        timezone="UTC",
    )
    await scheduler.update_schedule(config1_updated)

    # Remove a schedule
    logger.info("Removing schedule for agent-sync-data...")
    removed = await scheduler.remove_schedule("agent-sync-data")
    logger.info(f"Schedule removed: {removed}")

    # List schedules after modifications
    schedules = scheduler.list_schedules()
    logger.info(f"\nActive schedules after modifications: {len(schedules)}")
    for schedule in schedules:
        next_run = scheduler.get_next_run_time(schedule.agent_id)
        logger.info(f"  - {schedule.agent_id}: {schedule.cron_expression} (next: {next_run})")

    # Stop scheduler
    logger.info("\nStopping scheduler...")
    await scheduler.stop()
    logger.info("Scheduler stopped")

    # Final execution count
    logger.info(f"\nTotal executions: {len(executions)}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Example interrupted by user")
