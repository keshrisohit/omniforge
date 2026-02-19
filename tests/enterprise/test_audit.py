"""Tests for audit logging system."""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from omniforge.enterprise.audit import AuditEvent, AuditLogger, EventType, Outcome
from omniforge.storage.audit_repository import AuditRepository
from omniforge.storage.database import Database, DatabaseConfig


@pytest.fixture(scope="function")
async def db():
    """Create test database for each test."""
    config = DatabaseConfig(url="sqlite+aiosqlite:///:memory:")
    database = Database(config)
    await database.create_tables()
    yield database
    await database.close()


@pytest.fixture
async def session(db):
    """Create database session."""
    async with db.session() as s:
        yield s


@pytest.fixture
def repository(session):
    """Create audit repository."""
    return AuditRepository(session)


@pytest.fixture
def logger(repository):
    """Create audit logger."""
    return AuditLogger(repository)


@pytest.mark.asyncio
async def test_audit_event_creation():
    """Test creating an audit event."""
    event = AuditEvent(
        tenant_id="tenant-1",
        user_id="user-1",
        agent_id="agent-1",
        task_id="task-1",
        event_type=EventType.TOOL_CALL,
        resource_type="tool",
        resource_id="calculator",
        action="call:calculator",
        outcome=Outcome.SUCCESS,
        metadata={"operation": "add"},
    )

    assert event.tenant_id == "tenant-1"
    assert event.event_type == EventType.TOOL_CALL
    assert event.outcome == Outcome.SUCCESS


@pytest.mark.asyncio
async def test_save_audit_event(repository):
    """Test saving an audit event."""
    event = AuditEvent(
        tenant_id="tenant-1",
        event_type=EventType.TOOL_CALL,
        action="test_action",
        outcome=Outcome.SUCCESS,
    )

    await repository.save(event)

    # Verify event was saved
    retrieved = await repository.get_by_id(event.id)
    assert retrieved is not None
    assert retrieved.tenant_id == "tenant-1"


@pytest.mark.asyncio
async def test_get_audit_event_by_id(repository):
    """Test retrieving audit event by ID."""
    event = AuditEvent(
        tenant_id="tenant-1",
        event_type=EventType.CHAIN_START,
        action="start_chain",
        outcome=Outcome.SUCCESS,
    )

    await repository.save(event)
    retrieved = await repository.get_by_id(event.id)

    assert retrieved.id == event.id
    assert retrieved.event_type == EventType.CHAIN_START


@pytest.mark.asyncio
async def test_get_nonexistent_event(repository):
    """Test retrieving nonexistent event."""
    result = await repository.get_by_id(uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_query_by_tenant(repository):
    """Test querying events by tenant."""
    # Create events for different tenants
    event1 = AuditEvent(
        tenant_id="tenant-1",
        event_type=EventType.TOOL_CALL,
        action="action1",
        outcome=Outcome.SUCCESS,
    )
    event2 = AuditEvent(
        tenant_id="tenant-1",
        event_type=EventType.TOOL_RESULT,
        action="action2",
        outcome=Outcome.SUCCESS,
    )
    event3 = AuditEvent(
        tenant_id="tenant-2",
        event_type=EventType.TOOL_CALL,
        action="action3",
        outcome=Outcome.SUCCESS,
    )

    await repository.save(event1)
    await repository.save(event2)
    await repository.save(event3)

    # Query tenant-1 events
    events = await repository.query(tenant_id="tenant-1")

    assert len(events) == 2
    assert all(e.tenant_id == "tenant-1" for e in events)


@pytest.mark.asyncio
async def test_query_by_event_type(repository):
    """Test querying events by type."""
    # Create events of different types
    event1 = AuditEvent(
        event_type=EventType.TOOL_CALL,
        action="action1",
        outcome=Outcome.SUCCESS,
    )
    event2 = AuditEvent(
        event_type=EventType.TOOL_CALL,
        action="action2",
        outcome=Outcome.SUCCESS,
    )
    event3 = AuditEvent(
        event_type=EventType.CHAIN_START,
        action="action3",
        outcome=Outcome.SUCCESS,
    )

    await repository.save(event1)
    await repository.save(event2)
    await repository.save(event3)

    # Query TOOL_CALL events
    events = await repository.query(event_type=EventType.TOOL_CALL)

    assert len(events) == 2
    assert all(e.event_type == EventType.TOOL_CALL for e in events)


@pytest.mark.asyncio
async def test_query_by_date_range(repository):
    """Test querying events by date range."""
    now = datetime.utcnow()
    yesterday = now - timedelta(days=1)
    tomorrow = now + timedelta(days=1)

    # Create event with custom timestamp
    event1 = AuditEvent(
        timestamp=yesterday,
        event_type=EventType.TOOL_CALL,
        action="old_action",
        outcome=Outcome.SUCCESS,
    )
    event2 = AuditEvent(
        timestamp=now,
        event_type=EventType.TOOL_CALL,
        action="current_action",
        outcome=Outcome.SUCCESS,
    )

    await repository.save(event1)
    await repository.save(event2)

    # Query events from today onwards
    events = await repository.query(start_time=now - timedelta(hours=1))

    assert len(events) == 1
    assert events[0].action == "current_action"


@pytest.mark.asyncio
async def test_query_pagination(repository):
    """Test pagination in event queries."""
    # Create 5 events
    for i in range(5):
        event = AuditEvent(
            tenant_id="tenant-1",
            event_type=EventType.TOOL_CALL,
            action=f"action{i}",
            outcome=Outcome.SUCCESS,
        )
        await repository.save(event)

    # Get first page
    page1 = await repository.query(tenant_id="tenant-1", limit=2, offset=0)
    assert len(page1) == 2

    # Get second page
    page2 = await repository.query(tenant_id="tenant-1", limit=2, offset=2)
    assert len(page2) == 2

    # Verify no overlap
    page1_ids = {e.id for e in page1}
    page2_ids = {e.id for e in page2}
    assert len(page1_ids & page2_ids) == 0


@pytest.mark.asyncio
async def test_count_events(repository):
    """Test counting audit events."""
    # Create events
    for i in range(3):
        event = AuditEvent(
            tenant_id="tenant-1",
            event_type=EventType.TOOL_CALL,
            action=f"action{i}",
            outcome=Outcome.SUCCESS,
        )
        await repository.save(event)

    count = await repository.count(tenant_id="tenant-1")
    assert count == 3


@pytest.mark.asyncio
async def test_log_tool_call(logger):
    """Test logging a tool call."""
    event = await logger.log_tool_call(
        tenant_id="tenant-1",
        agent_id="agent-1",
        task_id="task-1",
        tool_name="calculator",
        arguments={"a": 1, "b": 2},
        success=True,
    )

    assert event.event_type == EventType.TOOL_CALL
    assert event.resource_type == "tool"
    assert event.resource_id == "calculator"
    assert event.outcome == Outcome.SUCCESS
    assert event.metadata["tool_name"] == "calculator"


@pytest.mark.asyncio
async def test_log_tool_call_with_result(logger):
    """Test logging a tool call with result."""
    event = await logger.log_tool_call(
        tenant_id="tenant-1",
        agent_id="agent-1",
        task_id="task-1",
        tool_name="calculator",
        arguments={"a": 1, "b": 2},
        result={"answer": 3},
        success=True,
    )

    assert event.event_type == EventType.TOOL_RESULT
    assert event.metadata["result"]["answer"] == 3


@pytest.mark.asyncio
async def test_log_tool_call_redacts_sensitive(logger):
    """Test that sensitive data is redacted from tool calls."""
    event = await logger.log_tool_call(
        tenant_id="tenant-1",
        agent_id="agent-1",
        task_id="task-1",
        tool_name="api_client",
        arguments={"api_key": "secret123", "data": "public"},
        success=True,
    )

    # api_key should be redacted
    assert event.metadata["arguments"]["api_key"] == "[REDACTED]"
    # Other fields should remain
    assert event.metadata["arguments"]["data"] == "public"


@pytest.mark.asyncio
async def test_log_chain_event(logger):
    """Test logging a chain lifecycle event."""
    chain_id = uuid4()

    event = await logger.log_chain_event(
        chain_id=chain_id,
        event_type=EventType.CHAIN_START,
        tenant_id="tenant-1",
        agent_id="agent-1",
        task_id="task-1",
        success=True,
    )

    assert event.event_type == EventType.CHAIN_START
    assert event.resource_type == "chain"
    assert event.resource_id == str(chain_id)
    assert event.outcome == Outcome.SUCCESS


@pytest.mark.asyncio
async def test_log_access_granted(logger):
    """Test logging successful access."""
    event = await logger.log_access(
        tenant_id="tenant-1",
        user_id="user-1",
        resource_type="agent",
        resource_id="agent-1",
        action="read",
        granted=True,
    )

    assert event.event_type == EventType.ACCESS_GRANT
    assert event.outcome == Outcome.SUCCESS


@pytest.mark.asyncio
async def test_log_access_denied(logger):
    """Test logging denied access."""
    event = await logger.log_access(
        tenant_id="tenant-1",
        user_id="user-1",
        resource_type="agent",
        resource_id="agent-1",
        action="delete",
        granted=False,
    )

    assert event.event_type == EventType.ACCESS_DENY
    assert event.outcome == Outcome.DENIED


@pytest.mark.asyncio
async def test_log_policy_violation(logger):
    """Test logging policy violation."""
    event = await logger.log_policy_violation(
        tenant_id="tenant-1",
        agent_id="agent-1",
        task_id="task-1",
        policy_type="model_governance",
        violation_reason="Model not approved",
    )

    assert event.event_type == EventType.POLICY_VIOLATION
    assert event.resource_type == "policy"
    assert event.resource_id == "model_governance"
    assert event.outcome == Outcome.DENIED
    assert "violation_reason" in event.metadata


@pytest.mark.asyncio
async def test_audit_events_ordered_by_timestamp(repository):
    """Test that events are returned in descending timestamp order."""
    import asyncio

    event1 = AuditEvent(
        tenant_id="tenant-1",
        event_type=EventType.TOOL_CALL,
        action="action1",
        outcome=Outcome.SUCCESS,
    )
    await repository.save(event1)

    # Small delay
    await asyncio.sleep(0.01)

    event2 = AuditEvent(
        tenant_id="tenant-1",
        event_type=EventType.TOOL_CALL,
        action="action2",
        outcome=Outcome.SUCCESS,
    )
    await repository.save(event2)

    events = await repository.query(tenant_id="tenant-1")

    # Newest first
    assert events[0].action == "action2"
    assert events[1].action == "action1"


@pytest.mark.asyncio
async def test_query_by_user(repository):
    """Test querying events by user."""
    event1 = AuditEvent(
        user_id="user-1",
        event_type=EventType.TOOL_CALL,
        action="action1",
        outcome=Outcome.SUCCESS,
    )
    event2 = AuditEvent(
        user_id="user-2",
        event_type=EventType.TOOL_CALL,
        action="action2",
        outcome=Outcome.SUCCESS,
    )

    await repository.save(event1)
    await repository.save(event2)

    events = await repository.query(user_id="user-1")

    assert len(events) == 1
    assert events[0].user_id == "user-1"


@pytest.mark.asyncio
async def test_query_by_agent(repository):
    """Test querying events by agent."""
    event1 = AuditEvent(
        agent_id="agent-1",
        event_type=EventType.TOOL_CALL,
        action="action1",
        outcome=Outcome.SUCCESS,
    )
    event2 = AuditEvent(
        agent_id="agent-2",
        event_type=EventType.TOOL_CALL,
        action="action2",
        outcome=Outcome.SUCCESS,
    )

    await repository.save(event1)
    await repository.save(event2)

    events = await repository.query(agent_id="agent-1")

    assert len(events) == 1
    assert events[0].agent_id == "agent-1"


@pytest.mark.asyncio
async def test_audit_event_with_ip_and_user_agent(logger):
    """Test logging event with IP address and user agent."""
    event = await logger.log_access(
        tenant_id="tenant-1",
        user_id="user-1",
        resource_type="agent",
        resource_id="agent-1",
        action="read",
        granted=True,
        ip_address="192.168.1.1",
        user_agent="Mozilla/5.0",
    )

    assert event.ip_address == "192.168.1.1"
    assert event.user_agent == "Mozilla/5.0"


@pytest.mark.asyncio
async def test_query_combined_filters(repository):
    """Test querying with multiple filters."""
    # Create various events
    for i in range(3):
        event = AuditEvent(
            tenant_id="tenant-1",
            user_id="user-1",
            event_type=EventType.TOOL_CALL,
            action=f"action{i}",
            outcome=Outcome.SUCCESS,
        )
        await repository.save(event)

    event = AuditEvent(
        tenant_id="tenant-1",
        user_id="user-2",
        event_type=EventType.TOOL_CALL,
        action="action_other",
        outcome=Outcome.SUCCESS,
    )
    await repository.save(event)

    # Query with multiple filters
    events = await repository.query(
        tenant_id="tenant-1", user_id="user-1", event_type=EventType.TOOL_CALL
    )

    assert len(events) == 3
    assert all(e.tenant_id == "tenant-1" for e in events)
    assert all(e.user_id == "user-1" for e in events)
    assert all(e.event_type == EventType.TOOL_CALL for e in events)


@pytest.mark.asyncio
async def test_logger_custom_sensitive_fields(repository):
    """Test logger with custom sensitive fields list."""
    logger = AuditLogger(repository, sensitive_fields=["custom_secret"])

    event = await logger.log_tool_call(
        tenant_id="tenant-1",
        agent_id="agent-1",
        task_id="task-1",
        tool_name="tool",
        arguments={"custom_secret": "value", "public": "data"},
        success=True,
    )

    assert event.metadata["arguments"]["custom_secret"] == "[REDACTED]"
    assert event.metadata["arguments"]["public"] == "data"


@pytest.mark.asyncio
async def test_count_with_filters(repository):
    """Test counting events with filters."""
    # Create events
    for i in range(3):
        event = AuditEvent(
            tenant_id="tenant-1",
            event_type=EventType.TOOL_CALL,
            action=f"action{i}",
            outcome=Outcome.SUCCESS,
        )
        await repository.save(event)

    event = AuditEvent(
        tenant_id="tenant-1",
        event_type=EventType.CHAIN_START,
        action="chain_action",
        outcome=Outcome.SUCCESS,
    )
    await repository.save(event)

    # Count TOOL_CALL events
    count = await repository.count(tenant_id="tenant-1", event_type=EventType.TOOL_CALL)
    assert count == 3
