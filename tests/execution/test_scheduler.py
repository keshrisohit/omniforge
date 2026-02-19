"""Unit tests for AgentScheduler."""

import asyncio
from datetime import datetime, timezone

import pytest

# Import directly from module to avoid circular imports
from omniforge.execution.scheduler import AgentScheduler, ScheduleConfig


class TestScheduleConfig:
    """Tests for ScheduleConfig model."""

    def test_create_schedule_config_with_valid_data(self) -> None:
        """ScheduleConfig should initialize with valid data."""
        config = ScheduleConfig(
            agent_id="agent-123",
            cron_expression="0 8 * * MON",
            timezone="America/New_York",
        )

        assert config.agent_id == "agent-123"
        assert config.cron_expression == "0 8 * * MON"
        assert config.timezone == "America/New_York"
        assert config.enabled is True

    def test_schedule_config_defaults_to_utc(self) -> None:
        """ScheduleConfig should default timezone to UTC."""
        config = ScheduleConfig(
            agent_id="agent-123",
            cron_expression="0 8 * * *",
        )

        assert config.timezone == "UTC"

    def test_schedule_config_validates_invalid_timezone(self) -> None:
        """ScheduleConfig should reject invalid timezone."""
        with pytest.raises(ValueError, match="Invalid timezone"):
            ScheduleConfig(
                agent_id="agent-123",
                cron_expression="0 8 * * *",
                timezone="Invalid/Timezone",
            )

    def test_schedule_config_validates_invalid_cron(self) -> None:
        """ScheduleConfig should reject invalid cron expression."""
        with pytest.raises(ValueError, match="Invalid cron expression"):
            ScheduleConfig(
                agent_id="agent-123",
                cron_expression="invalid cron",
                timezone="UTC",
            )

    def test_schedule_config_accepts_standard_cron_expressions(self) -> None:
        """ScheduleConfig should accept standard cron expressions."""
        expressions = [
            "0 8 * * *",  # Daily at 8am
            "0 8 * * MON",  # Mondays at 8am
            "*/15 * * * *",  # Every 15 minutes
            "0 0 1 * *",  # First day of month
            "0 0 * * 0",  # Sundays at midnight
        ]

        for expr in expressions:
            config = ScheduleConfig(
                agent_id="agent-123",
                cron_expression=expr,
            )
            assert config.cron_expression == expr


class TestAgentScheduler:
    """Tests for AgentScheduler."""

    @pytest.fixture
    async def execution_log(self) -> list[tuple[str, str]]:
        """Fixture for tracking execution calls."""
        return []

    @pytest.fixture
    async def execution_callback(
        self, execution_log: list[tuple[str, str]]
    ) -> callable:
        """Fixture for execution callback."""

        async def callback(agent_id: str, triggered_by: str) -> None:
            execution_log.append((agent_id, triggered_by))

        return callback

    @pytest.fixture
    async def scheduler(self, execution_callback: callable) -> AgentScheduler:
        """Fixture for AgentScheduler."""
        return AgentScheduler(
            execution_callback=execution_callback,
            timezone="UTC",
        )

    async def test_scheduler_starts_and_stops(self, scheduler: AgentScheduler) -> None:
        """Scheduler should start and stop successfully."""
        assert not scheduler.is_running()

        await scheduler.start()
        assert scheduler.is_running()

        await scheduler.stop()
        # APScheduler shutdown may take a moment to complete
        await asyncio.sleep(0.1)
        assert not scheduler.is_running()

    async def test_add_schedule_creates_job(self, scheduler: AgentScheduler) -> None:
        """Adding a schedule should create an APScheduler job."""
        await scheduler.start()

        config = ScheduleConfig(
            agent_id="agent-123",
            cron_expression="0 8 * * *",
            timezone="UTC",
        )

        await scheduler.add_schedule(config)

        # Verify job was created
        job = scheduler.scheduler.get_job("agent_agent-123")
        assert job is not None
        assert job.id == "agent_agent-123"

        await scheduler.stop()

    async def test_add_schedule_stores_config(self, scheduler: AgentScheduler) -> None:
        """Adding a schedule should store the config."""
        await scheduler.start()

        config = ScheduleConfig(
            agent_id="agent-123",
            cron_expression="0 8 * * *",
        )

        await scheduler.add_schedule(config)

        # Verify config is stored
        stored_config = scheduler.get_schedule("agent-123")
        assert stored_config is not None
        assert stored_config.agent_id == "agent-123"
        assert stored_config.cron_expression == "0 8 * * *"

        await scheduler.stop()

    async def test_remove_schedule_removes_job(self, scheduler: AgentScheduler) -> None:
        """Removing a schedule should remove the APScheduler job."""
        await scheduler.start()

        config = ScheduleConfig(
            agent_id="agent-123",
            cron_expression="0 8 * * *",
        )

        await scheduler.add_schedule(config)
        removed = await scheduler.remove_schedule("agent-123")

        assert removed is True

        # Verify job was removed
        job = scheduler.scheduler.get_job("agent_agent-123")
        assert job is None

        # Verify config was removed
        stored_config = scheduler.get_schedule("agent-123")
        assert stored_config is None

        await scheduler.stop()

    async def test_remove_schedule_returns_false_if_not_exists(
        self, scheduler: AgentScheduler
    ) -> None:
        """Removing non-existent schedule should return False."""
        await scheduler.start()

        removed = await scheduler.remove_schedule("nonexistent")
        assert removed is False

        await scheduler.stop()

    async def test_update_schedule_replaces_existing(
        self, scheduler: AgentScheduler
    ) -> None:
        """Updating a schedule should replace the existing one."""
        await scheduler.start()

        # Add initial schedule
        config1 = ScheduleConfig(
            agent_id="agent-123",
            cron_expression="0 8 * * *",
        )
        await scheduler.add_schedule(config1)

        # Update schedule
        config2 = ScheduleConfig(
            agent_id="agent-123",
            cron_expression="0 9 * * *",
        )
        await scheduler.update_schedule(config2)

        # Verify schedule was updated
        stored_config = scheduler.get_schedule("agent-123")
        assert stored_config is not None
        assert stored_config.cron_expression == "0 9 * * *"

        await scheduler.stop()

    async def test_list_schedules_returns_all_active(
        self, scheduler: AgentScheduler
    ) -> None:
        """list_schedules should return all active schedules."""
        await scheduler.start()

        config1 = ScheduleConfig(agent_id="agent-1", cron_expression="0 8 * * *")
        config2 = ScheduleConfig(agent_id="agent-2", cron_expression="0 9 * * *")
        config3 = ScheduleConfig(agent_id="agent-3", cron_expression="0 10 * * *")

        await scheduler.add_schedule(config1)
        await scheduler.add_schedule(config2)
        await scheduler.add_schedule(config3)

        schedules = scheduler.list_schedules()
        assert len(schedules) == 3

        agent_ids = {s.agent_id for s in schedules}
        assert agent_ids == {"agent-1", "agent-2", "agent-3"}

        await scheduler.stop()

    async def test_get_next_run_time_returns_datetime(
        self, scheduler: AgentScheduler
    ) -> None:
        """get_next_run_time should return next scheduled run."""
        await scheduler.start()

        config = ScheduleConfig(
            agent_id="agent-123",
            cron_expression="0 8 * * *",
        )
        await scheduler.add_schedule(config)

        next_run = scheduler.get_next_run_time("agent-123")
        assert next_run is not None
        assert isinstance(next_run, datetime)

        await scheduler.stop()

    async def test_disabled_schedule_not_added(
        self, scheduler: AgentScheduler
    ) -> None:
        """Disabled schedule should not be added to scheduler."""
        await scheduler.start()

        config = ScheduleConfig(
            agent_id="agent-123",
            cron_expression="0 8 * * *",
            enabled=False,
        )

        await scheduler.add_schedule(config)

        # Verify job was not created
        job = scheduler.scheduler.get_job("agent_agent-123")
        assert job is None

        # Verify config was not stored
        stored_config = scheduler.get_schedule("agent-123")
        assert stored_config is None

        await scheduler.stop()

    async def test_scheduled_execution_calls_callback(
        self,
        scheduler: AgentScheduler,
        execution_log: list[tuple[str, str]],
    ) -> None:
        """Scheduled execution should call the execution callback."""
        await scheduler.start()

        # Add schedule that runs every second
        config = ScheduleConfig(
            agent_id="agent-123",
            cron_expression="* * * * * *",  # Every second (with seconds support)
        )

        # Manually trigger execution to test callback
        await scheduler._execute_scheduled_agent("agent-123")

        # Verify callback was called
        assert len(execution_log) == 1
        assert execution_log[0] == ("agent-123", "scheduler")

        await scheduler.stop()

    async def test_execution_callback_error_logged_not_raised(
        self,
        scheduler: AgentScheduler,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Execution errors should be logged but not raised."""

        async def failing_callback(agent_id: str, triggered_by: str) -> None:
            raise RuntimeError("Execution failed")

        failing_scheduler = AgentScheduler(
            execution_callback=failing_callback,
            timezone="UTC",
        )

        await failing_scheduler.start()

        # Execute scheduled agent
        await failing_scheduler._execute_scheduled_agent("agent-123")

        # Verify error was logged but didn't raise
        assert "Failed to execute scheduled agent" in caplog.text

        await failing_scheduler.stop()

    async def test_timezone_aware_scheduling(self, scheduler: AgentScheduler) -> None:
        """Schedules should respect timezone configuration."""
        await scheduler.start()

        config = ScheduleConfig(
            agent_id="agent-123",
            cron_expression="0 8 * * *",
            timezone="America/New_York",
        )

        await scheduler.add_schedule(config)

        # Verify job has correct timezone
        job = scheduler.scheduler.get_job("agent_agent-123")
        assert job is not None
        # Note: APScheduler stores timezone in the trigger
        assert str(job.trigger.timezone) == "America/New_York"

        await scheduler.stop()

    async def test_job_id_format(self, scheduler: AgentScheduler) -> None:
        """Job IDs should follow agent_{agent_id} format."""
        job_id = scheduler._get_job_id("agent-123")
        assert job_id == "agent_agent-123"

        job_id = scheduler._get_job_id("abc-def-ghi")
        assert job_id == "agent_abc-def-ghi"
