"""Tests for cost record persistence."""

from datetime import date, datetime, timedelta

import pytest

from omniforge.enterprise.cost_tracker import CostRecord
from omniforge.storage.cost_repository import CostRecordRepository, ModelUsageRepository
from omniforge.storage.database import Database, DatabaseConfig


@pytest.fixture
async def database():
    """Create in-memory database for testing."""
    config = DatabaseConfig(url="sqlite+aiosqlite:///:memory:")
    db = Database(config)
    await db.create_tables()
    yield db
    await db.close()


@pytest.fixture
async def cost_repo(database):
    """Create cost record repository."""
    async with database.session() as session:
        yield CostRecordRepository(session)


@pytest.fixture
async def usage_repo(database):
    """Create model usage repository."""
    async with database.session() as session:
        yield ModelUsageRepository(session)


@pytest.mark.asyncio
async def test_database_initialization():
    """Test database initialization."""
    config = DatabaseConfig(url="sqlite+aiosqlite:///:memory:")
    db = Database(config)
    await db.create_tables()

    assert db.config == config
    assert db.is_async is True

    await db.close()


@pytest.mark.asyncio
async def test_save_cost_record(database):
    """Test saving a cost record."""
    async with database.session() as session:
        repo = CostRecordRepository(session)

        record = CostRecord(
            tenant_id="tenant-1",
            task_id="task-1",
            chain_id="chain-1",
            step_id="step-1",
            tool_name="llm",
            cost_usd=0.5,
            tokens=100,
            model="gpt-4",
        )

        await repo.save(record)
        await session.commit()

    # Verify saved
    async with database.session() as session:
        repo = CostRecordRepository(session)
        records = await repo.get_by_task("task-1")

        assert len(records) == 1
        assert records[0].tenant_id == "tenant-1"
        assert records[0].task_id == "task-1"
        assert records[0].cost_usd == 0.5
        assert records[0].tokens == 100
        assert records[0].model == "gpt-4"


@pytest.mark.asyncio
async def test_save_multiple_cost_records(database):
    """Test saving multiple cost records."""
    async with database.session() as session:
        repo = CostRecordRepository(session)

        for i in range(5):
            record = CostRecord(
                tenant_id="tenant-1",
                task_id="task-1",
                chain_id="chain-1",
                step_id=f"step-{i}",
                tool_name="llm",
                cost_usd=0.1 * (i + 1),
                tokens=100 * (i + 1),
            )
            await repo.save(record)

        await session.commit()

    # Verify all saved
    async with database.session() as session:
        repo = CostRecordRepository(session)
        records = await repo.get_by_task("task-1")

        assert len(records) == 5
        assert sum(r.cost_usd for r in records) == pytest.approx(1.5)
        assert sum(r.tokens for r in records) == 1500


@pytest.mark.asyncio
async def test_get_by_task_empty(database):
    """Test getting records for non-existent task."""
    async with database.session() as session:
        repo = CostRecordRepository(session)
        records = await repo.get_by_task("nonexistent")

        assert len(records) == 0


@pytest.mark.asyncio
async def test_get_by_tenant_date_range(database):
    """Test getting records by tenant and date range."""
    now = datetime.utcnow()
    yesterday = now - timedelta(days=1)
    tomorrow = now + timedelta(days=1)

    async with database.session() as session:
        repo = CostRecordRepository(session)

        # Record from yesterday
        record1 = CostRecord(
            tenant_id="tenant-1",
            task_id="task-1",
            chain_id="chain-1",
            step_id="step-1",
            tool_name="llm",
            cost_usd=0.5,
            tokens=100,
            created_at=yesterday,
        )
        await repo.save(record1)

        # Record from today
        record2 = CostRecord(
            tenant_id="tenant-1",
            task_id="task-2",
            chain_id="chain-1",
            step_id="step-1",
            tool_name="llm",
            cost_usd=0.3,
            tokens=60,
            created_at=now,
        )
        await repo.save(record2)

        # Record from different tenant
        record3 = CostRecord(
            tenant_id="tenant-2",
            task_id="task-3",
            chain_id="chain-1",
            step_id="step-1",
            tool_name="llm",
            cost_usd=0.2,
            tokens=40,
            created_at=now,
        )
        await repo.save(record3)

        await session.commit()

    # Query tenant-1 for today only
    async with database.session() as session:
        repo = CostRecordRepository(session)
        records = await repo.get_by_tenant_date_range(
            "tenant-1", now - timedelta(hours=1), tomorrow
        )

        assert len(records) == 1
        assert records[0].task_id == "task-2"

    # Query tenant-1 for all dates
    async with database.session() as session:
        repo = CostRecordRepository(session)
        records = await repo.get_by_tenant_date_range(
            "tenant-1", yesterday - timedelta(days=1), tomorrow
        )

        assert len(records) == 2


@pytest.mark.asyncio
async def test_get_tenant_totals(database):
    """Test getting aggregated totals for a tenant."""
    async with database.session() as session:
        repo = CostRecordRepository(session)

        # Add records for tenant-1
        for i in range(3):
            record = CostRecord(
                tenant_id="tenant-1",
                task_id=f"task-{i}",
                chain_id="chain-1",
                step_id="step-1",
                tool_name="llm",
                cost_usd=0.5,
                tokens=100,
            )
            await repo.save(record)

        # Add record for tenant-2
        record = CostRecord(
            tenant_id="tenant-2",
            task_id="task-3",
            chain_id="chain-1",
            step_id="step-1",
            tool_name="llm",
            cost_usd=0.2,
            tokens=40,
        )
        await repo.save(record)

        await session.commit()

    # Get totals for tenant-1
    async with database.session() as session:
        repo = CostRecordRepository(session)
        totals = await repo.get_tenant_totals("tenant-1")

        assert totals["total_cost_usd"] == pytest.approx(1.5)
        assert totals["total_tokens"] == 300
        assert totals["record_count"] == 3


@pytest.mark.asyncio
async def test_get_tenant_totals_with_date_range(database):
    """Test getting tenant totals with date filtering."""
    now = datetime.utcnow()
    yesterday = now - timedelta(days=1)

    async with database.session() as session:
        repo = CostRecordRepository(session)

        # Record from yesterday
        record1 = CostRecord(
            tenant_id="tenant-1",
            task_id="task-1",
            chain_id="chain-1",
            step_id="step-1",
            tool_name="llm",
            cost_usd=0.5,
            tokens=100,
            created_at=yesterday,
        )
        await repo.save(record1)

        # Record from today
        record2 = CostRecord(
            tenant_id="tenant-1",
            task_id="task-2",
            chain_id="chain-1",
            step_id="step-1",
            tool_name="llm",
            cost_usd=0.3,
            tokens=60,
            created_at=now,
        )
        await repo.save(record2)

        await session.commit()

    # Get totals for today only
    async with database.session() as session:
        repo = CostRecordRepository(session)
        totals = await repo.get_tenant_totals(
            "tenant-1", start_date=now - timedelta(hours=1)
        )

        assert totals["total_cost_usd"] == pytest.approx(0.3)
        assert totals["total_tokens"] == 60
        assert totals["record_count"] == 1


@pytest.mark.asyncio
async def test_get_tenant_totals_empty(database):
    """Test getting totals for tenant with no records."""
    async with database.session() as session:
        repo = CostRecordRepository(session)
        totals = await repo.get_tenant_totals("nonexistent")

        assert totals["total_cost_usd"] == 0.0
        assert totals["total_tokens"] == 0
        assert totals["record_count"] == 0


@pytest.mark.asyncio
async def test_update_model_usage_new(database):
    """Test updating model usage creates new record."""
    today = date.today()

    async with database.session() as session:
        repo = ModelUsageRepository(session)

        await repo.update_usage(
            tenant_id="tenant-1",
            model="gpt-4",
            usage_date=today,
            call_count=5,
            input_tokens=1000,
            output_tokens=500,
            cost_usd=0.5,
        )

        await session.commit()

    # Verify created
    async with database.session() as session:
        repo = ModelUsageRepository(session)
        usage = await repo.get_tenant_usage("tenant-1", today, today)

        assert len(usage) == 1
        assert usage[0]["model"] == "gpt-4"
        assert usage[0]["call_count"] == 5
        assert usage[0]["input_tokens"] == 1000
        assert usage[0]["output_tokens"] == 500
        assert usage[0]["total_cost_usd"] == pytest.approx(0.5)


@pytest.mark.asyncio
async def test_update_model_usage_existing(database):
    """Test updating model usage updates existing record."""
    today = date.today()

    async with database.session() as session:
        repo = ModelUsageRepository(session)

        # First update
        await repo.update_usage(
            tenant_id="tenant-1",
            model="gpt-4",
            usage_date=today,
            call_count=5,
            input_tokens=1000,
            output_tokens=500,
            cost_usd=0.5,
        )

        await session.commit()

    # Second update (should accumulate)
    async with database.session() as session:
        repo = ModelUsageRepository(session)

        await repo.update_usage(
            tenant_id="tenant-1",
            model="gpt-4",
            usage_date=today,
            call_count=3,
            input_tokens=600,
            output_tokens=300,
            cost_usd=0.3,
        )

        await session.commit()

    # Verify accumulated
    async with database.session() as session:
        repo = ModelUsageRepository(session)
        usage = await repo.get_tenant_usage("tenant-1", today, today)

        assert len(usage) == 1
        assert usage[0]["call_count"] == 8  # 5 + 3
        assert usage[0]["input_tokens"] == 1600  # 1000 + 600
        assert usage[0]["output_tokens"] == 800  # 500 + 300
        assert usage[0]["total_cost_usd"] == pytest.approx(0.8)  # 0.5 + 0.3


@pytest.mark.asyncio
async def test_get_tenant_usage_multiple_models(database):
    """Test getting usage for multiple models."""
    today = date.today()

    async with database.session() as session:
        repo = ModelUsageRepository(session)

        # Add usage for multiple models
        await repo.update_usage(
            "tenant-1", "gpt-4", today, 5, 1000, 500, 0.5
        )
        await repo.update_usage(
            "tenant-1", "gpt-3.5", today, 10, 2000, 1000, 0.2
        )

        await session.commit()

    # Verify both models returned
    async with database.session() as session:
        repo = ModelUsageRepository(session)
        usage = await repo.get_tenant_usage("tenant-1", today, today)

        assert len(usage) == 2
        models = {u["model"] for u in usage}
        assert models == {"gpt-4", "gpt-3.5"}


@pytest.mark.asyncio
async def test_get_tenant_usage_date_range(database):
    """Test getting usage for a date range."""
    today = date.today()
    yesterday = today - timedelta(days=1)

    async with database.session() as session:
        repo = ModelUsageRepository(session)

        # Add usage for yesterday
        await repo.update_usage(
            "tenant-1", "gpt-4", yesterday, 5, 1000, 500, 0.5
        )

        # Add usage for today
        await repo.update_usage(
            "tenant-1", "gpt-4", today, 3, 600, 300, 0.3
        )

        await session.commit()

    # Query for today only
    async with database.session() as session:
        repo = ModelUsageRepository(session)
        usage = await repo.get_tenant_usage("tenant-1", today, today)

        assert len(usage) == 1
        assert usage[0]["call_count"] == 3

    # Query for both days
    async with database.session() as session:
        repo = ModelUsageRepository(session)
        usage = await repo.get_tenant_usage("tenant-1", yesterday, today)

        assert len(usage) == 2


@pytest.mark.asyncio
async def test_get_model_totals(database):
    """Test getting aggregated totals per model."""
    today = date.today()
    yesterday = today - timedelta(days=1)

    async with database.session() as session:
        repo = ModelUsageRepository(session)

        # Add usage for gpt-4 across 2 days
        await repo.update_usage(
            "tenant-1", "gpt-4", yesterday, 5, 1000, 500, 0.5
        )
        await repo.update_usage(
            "tenant-1", "gpt-4", today, 3, 600, 300, 0.3
        )

        # Add usage for gpt-3.5
        await repo.update_usage(
            "tenant-1", "gpt-3.5", today, 10, 2000, 1000, 0.2
        )

        await session.commit()

    # Get model totals
    async with database.session() as session:
        repo = ModelUsageRepository(session)
        totals = await repo.get_model_totals("tenant-1")

        assert "gpt-4" in totals
        assert totals["gpt-4"]["call_count"] == 8  # 5 + 3
        assert totals["gpt-4"]["input_tokens"] == 1600  # 1000 + 600
        assert totals["gpt-4"]["output_tokens"] == 800  # 500 + 300
        assert totals["gpt-4"]["total_cost_usd"] == pytest.approx(0.8)

        assert "gpt-3.5" in totals
        assert totals["gpt-3.5"]["call_count"] == 10


@pytest.mark.asyncio
async def test_get_model_totals_with_date_range(database):
    """Test getting model totals with date filtering."""
    today = date.today()
    yesterday = today - timedelta(days=1)

    async with database.session() as session:
        repo = ModelUsageRepository(session)

        # Add usage for yesterday
        await repo.update_usage(
            "tenant-1", "gpt-4", yesterday, 5, 1000, 500, 0.5
        )

        # Add usage for today
        await repo.update_usage(
            "tenant-1", "gpt-4", today, 3, 600, 300, 0.3
        )

        await session.commit()

    # Get totals for today only
    async with database.session() as session:
        repo = ModelUsageRepository(session)
        totals = await repo.get_model_totals("tenant-1", start_date=today)

        assert totals["gpt-4"]["call_count"] == 3
        assert totals["gpt-4"]["total_cost_usd"] == pytest.approx(0.3)


@pytest.mark.asyncio
async def test_tenant_isolation(database):
    """Test that tenant data is properly isolated."""
    today = date.today()

    async with database.session() as session:
        repo = ModelUsageRepository(session)

        # Add usage for tenant-1
        await repo.update_usage(
            "tenant-1", "gpt-4", today, 5, 1000, 500, 0.5
        )

        # Add usage for tenant-2
        await repo.update_usage(
            "tenant-2", "gpt-4", today, 3, 600, 300, 0.3
        )

        await session.commit()

    # Verify tenant-1 only sees their data
    async with database.session() as session:
        repo = ModelUsageRepository(session)
        usage = await repo.get_tenant_usage("tenant-1", today, today)

        assert len(usage) == 1
        assert usage[0]["call_count"] == 5

    # Verify tenant-2 only sees their data
    async with database.session() as session:
        repo = ModelUsageRepository(session)
        usage = await repo.get_tenant_usage("tenant-2", today, today)

        assert len(usage) == 1
        assert usage[0]["call_count"] == 3
