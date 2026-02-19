"""End-to-end integration tests for conversation persistence.

This module verifies the complete persistence workflow including:
- Full conversation flow with cache clearing (simulating restarts)
- Error recovery with context preservation
- Multi-tenant isolation
- Cleanup job integration

All tests use a real in-memory SQLite database for realistic behavior.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest

from omniforge.conversation.models import ConversationType
from omniforge.conversation.orm import ConversationModel
from omniforge.conversation.sqlite_repository import SQLiteConversationRepository
from omniforge.skills.creation.agent import SkillCreationAgent
from omniforge.skills.creation.models import (
    ConversationContext,
    ConversationState,
    SkillCapabilities,
)
from omniforge.storage.database import Database, DatabaseConfig


# Helper functions for working with unified conversation repository
def _session_id_to_uuid(session_id: str, tenant_id: str = "") -> UUID:
    """Convert session_id to UUID (generate UUID from session_id+tenant_id if not valid UUID)."""
    try:
        return UUID(session_id) if isinstance(session_id, str) else session_id
    except ValueError:
        import hashlib

        combined = f"{tenant_id}:{session_id}"
        return UUID(bytes=hashlib.md5(combined.encode()).digest(), version=4)


async def save_context_to_repository(
    repository: SQLiteConversationRepository,
    context: ConversationContext,
    tenant_id: str,
) -> None:
    """Helper to save ConversationContext to unified repository."""
    conversation_id = _session_id_to_uuid(context.session_id, tenant_id)

    state_metadata = {
        "skill_name": context.skill_name,
        "skill_description": context.skill_description,
        "skill_purpose": context.skill_purpose,
        "skill_capabilities": (
            context.skill_capabilities.model_dump() if context.skill_capabilities else None
        ),
        "examples": context.examples,
        "triggers": context.triggers,
        "storage_layer": context.storage_layer,
        "generated_content": context.generated_content,
        "generated_resources": context.generated_resources,
        "validation_errors": context.validation_errors,
        "validation_attempts": context.validation_attempts,
        "validation_progress": context.validation_progress,
        "max_validation_retries": context.max_validation_retries,
    }

    existing = await repository.get_conversation(conversation_id, tenant_id)

    if existing:
        await repository.update_state(
            conversation_id,
            tenant_id,
            state=context.state.value,
            state_metadata=state_metadata,
        )
    else:
        await repository.create_conversation(
            tenant_id=tenant_id,
            user_id=tenant_id,
            title=context.skill_name or "Skill Creation Session",
            conversation_type=ConversationType.SKILL_CREATION,
            state=context.state.value,
            state_metadata=state_metadata,
            conversation_id=conversation_id,
        )


async def load_context_from_repository(
    repository: SQLiteConversationRepository,
    session_id: str,
    tenant_id: str,
) -> Optional[ConversationContext]:
    """Helper to load ConversationContext from unified repository."""
    conversation_id = _session_id_to_uuid(session_id, tenant_id)

    conversation = await repository.get_conversation(conversation_id, tenant_id)
    if not conversation:
        return None

    data = conversation.state_metadata or {}
    context = ConversationContext(session_id=session_id)
    context.state = (
        ConversationState(conversation.state) if conversation.state else ConversationState.IDLE
    )
    context.skill_name = data.get("skill_name")
    context.skill_description = data.get("skill_description")
    context.skill_purpose = data.get("skill_purpose")

    capabilities_data = data.get("skill_capabilities")
    if capabilities_data:
        context.skill_capabilities = SkillCapabilities(**capabilities_data)

    context.examples = data.get("examples", [])
    context.triggers = data.get("triggers", [])
    context.storage_layer = data.get("storage_layer")
    context.generated_content = data.get("generated_content")
    context.generated_resources = data.get("generated_resources", {})
    context.validation_errors = data.get("validation_errors", [])
    context.validation_attempts = data.get("validation_attempts", 0)
    context.validation_progress = data.get("validation_progress", {})
    context.max_validation_retries = data.get("max_validation_retries", 3)

    return context


class TestFullConversationFlow:
    """Test complete conversation lifecycle with persistence and restoration."""

    @pytest.mark.asyncio
    async def test_full_skill_creation_with_restart(
        self, agent_with_persistence: SkillCreationAgent
    ) -> None:
        """Verify full conversation flow with simulated restart."""
        session_id = "integration-full-flow"
        tenant_id = "tenant-integration"

        # Step 1: Start conversation
        messages = []
        async for chunk in agent_with_persistence.handle_message(
            "Create a calculator skill",
            session_id=session_id,
            tenant_id=tenant_id,
        ):
            messages.append(chunk)

        assert len(messages) > 0

        # Verify context persisted
        context = await agent_with_persistence.get_session_context(session_id, tenant_id)
        assert context.session_id == session_id
        assert len(context.message_history) > 0
        original_message_count = len(context.message_history)

        # Step 2: Continue conversation
        messages2 = []
        async for chunk in agent_with_persistence.handle_message(
            "It should support basic arithmetic operations",
            session_id=session_id,
            tenant_id=tenant_id,
        ):
            messages2.append(chunk)

        assert len(messages2) > 0

        # Verify message history grew
        context = await agent_with_persistence.get_session_context(session_id, tenant_id)
        assert len(context.message_history) > original_message_count

        # Step 3: Simulate restart - clear in-memory cache
        agent_with_persistence.sessions.clear()
        assert session_id not in agent_with_persistence.sessions

        # Step 4: Resume conversation - should restore from database
        messages3 = []
        async for chunk in agent_with_persistence.handle_message(
            "Add multiplication and division",
            session_id=session_id,
            tenant_id=tenant_id,
        ):
            messages3.append(chunk)

        assert len(messages3) > 0

        # Verify full context was restored
        restored_context = await agent_with_persistence.get_session_context(session_id, tenant_id)
        assert restored_context.session_id == session_id
        assert len(restored_context.message_history) >= 6  # At least 3 exchanges

        # Verify session now in memory again
        assert session_id in agent_with_persistence.sessions

    @pytest.mark.asyncio
    async def test_multiple_sessions_in_parallel(
        self, agent_with_persistence: SkillCreationAgent
    ) -> None:
        """Verify multiple concurrent sessions are isolated and persisted correctly."""
        tenant_id = "tenant-parallel"
        session_ids = [f"parallel-session-{i}" for i in range(3)]

        # Start multiple conversations concurrently
        async def start_conversation(session_id: str) -> None:
            chunks = []
            async for chunk in agent_with_persistence.handle_message(
                f"Create a skill for session {session_id}",
                session_id=session_id,
                tenant_id=tenant_id,
            ):
                chunks.append(chunk)
            assert len(chunks) > 0

        await asyncio.gather(*[start_conversation(sid) for sid in session_ids])

        # Verify all sessions persisted with correct isolation
        for session_id in session_ids:
            context = await agent_with_persistence.get_session_context(session_id, tenant_id)
            assert context.session_id == session_id
            assert len(context.message_history) > 0

            # Verify the message is specific to this session
            user_message = context.message_history[0]["content"]
            assert session_id in user_message


class TestErrorRecovery:
    """Test error handling and context preservation during failures."""

    @pytest.mark.asyncio
    async def test_error_recovery_preserves_context(
        self, agent_with_persistence: SkillCreationAgent
    ) -> None:
        """Verify context is persisted even when errors occur during processing."""
        session_id = "integration-error-recovery"
        tenant_id = "tenant-error"

        # Start normal conversation
        messages = []
        async for chunk in agent_with_persistence.handle_message(
            "Create a logging utility skill",
            session_id=session_id,
            tenant_id=tenant_id,
        ):
            messages.append(chunk)

        assert len(messages) > 0

        # Get context before error
        context_before = await agent_with_persistence.get_session_context(session_id, tenant_id)
        message_count_before = len(context_before.message_history)

        # Simulate an error by mocking the LLM generator to raise an exception
        with patch.object(
            agent_with_persistence.llm_generator,
            "generate",
            side_effect=RuntimeError("Simulated LLM error"),
        ):
            # This should fail but not crash
            error_messages = []
            try:
                async for chunk in agent_with_persistence.handle_message(
                    "Add error handling",
                    session_id=session_id,
                    tenant_id=tenant_id,
                ):
                    error_messages.append(chunk)
            except RuntimeError:
                pass  # Expected error

        # Verify context was persisted despite error (or at least not lost)
        context_after = await agent_with_persistence.get_session_context(session_id, tenant_id)

        # Context should still exist with history preserved
        assert context_after.session_id == session_id
        assert len(context_after.message_history) >= message_count_before

        # Continue conversation after error - should work normally
        recovery_messages = []
        async for chunk in agent_with_persistence.handle_message(
            "Make it production ready",
            session_id=session_id,
            tenant_id=tenant_id,
        ):
            recovery_messages.append(chunk)

        assert len(recovery_messages) > 0

        # Verify full history preserved through error
        final_context = await agent_with_persistence.get_session_context(session_id, tenant_id)
        assert len(final_context.message_history) > message_count_before


class TestMultiTenantIsolation:
    """Test tenant isolation in persistence layer."""

    @pytest.mark.asyncio
    async def test_tenant_isolation_end_to_end(
        self, agent_with_persistence: SkillCreationAgent
    ) -> None:
        """Verify complete isolation between tenants in full workflow."""
        # Use different session IDs but same logical session name
        session_id_1 = "tenant-alpha-session"
        session_id_2 = "tenant-beta-session"
        tenant_1 = "tenant-alpha"
        tenant_2 = "tenant-beta"

        # Create session for tenant 1
        async for chunk in agent_with_persistence.handle_message(
            "Create a data pipeline skill",
            session_id=session_id_1,
            tenant_id=tenant_1,
        ):
            pass

        # Create session for tenant 2
        async for chunk in agent_with_persistence.handle_message(
            "Create a reporting skill",
            session_id=session_id_2,
            tenant_id=tenant_2,
        ):
            pass

        # Clear cache to force DB load
        agent_with_persistence.sessions.clear()

        # Load contexts - should be completely isolated
        context_1 = await agent_with_persistence.get_session_context(session_id_1, tenant_1)
        context_2 = await agent_with_persistence.get_session_context(session_id_2, tenant_2)

        # Verify isolation
        assert context_1.session_id == session_id_1
        assert context_2.session_id == session_id_2

        # Verify different conversation content
        msg_1 = context_1.message_history[0]["content"]
        msg_2 = context_2.message_history[0]["content"]
        assert "data pipeline" in msg_1.lower()
        assert "reporting" in msg_2.lower()
        assert msg_1 != msg_2

        # Modify tenant 1's context
        agent_with_persistence.sessions.clear()  # Clear before modifying
        async for chunk in agent_with_persistence.handle_message(
            "Add ETL capabilities",
            session_id=session_id_1,
            tenant_id=tenant_1,
        ):
            pass

        # Verify tenant 2 unaffected
        agent_with_persistence.sessions.clear()
        context_1_after = await agent_with_persistence.get_session_context(session_id_1, tenant_1)
        context_2_after = await agent_with_persistence.get_session_context(session_id_2, tenant_2)

        # Tenant 1 should have more messages now
        assert len(context_1_after.message_history) > len(context_1.message_history)

        # Tenant 2 should remain unchanged
        assert len(context_2_after.message_history) == len(context_2.message_history)

    @pytest.mark.asyncio
    @pytest.mark.skip(
        reason="Cleanup method not yet implemented in unified conversation repository"
    )
    async def test_tenant_isolation_in_cleanup(
        self, repository: SQLiteConversationRepository, db: Database
    ) -> None:
        """Verify cleanup operations respect tenant boundaries."""
        tenant_1 = "tenant-cleanup-1"
        tenant_2 = "tenant-cleanup-2"

        # Create old completed sessions for both tenants
        old_date = datetime.utcnow() - timedelta(days=95)

        for i in range(3):
            context = ConversationContext(session_id=f"old-session-{i}")
            context.state = ConversationState.COMPLETED
            await save_context_to_repository(repository, context, tenant_1)

        for i in range(2):
            context = ConversationContext(session_id=f"old-session-{i}")
            context.state = ConversationState.COMPLETED
            await save_context_to_repository(repository, context, tenant_2)

        # Manually update timestamps to be old
        async with db.session() as session:
            from sqlalchemy import update

            await session.execute(
                update(ConversationModel)
                .where(ConversationModel.tenant_id == tenant_1)
                .values(updated_at=old_date, status="completed")
            )
            await session.execute(
                update(ConversationModel)
                .where(ConversationModel.tenant_id == tenant_2)
                .values(updated_at=old_date, status="completed")
            )
            await session.flush()

        # Run cleanup for tenant_1 only
        deleted = await repository.cleanup_old_sessions(
            completed_retention_days=90,
            abandoned_retention_days=30,
            tenant_id=tenant_1,
        )

        assert deleted == 3

        # Verify tenant_2 sessions still exist
        tenant_2_sessions = await repository.list_by_tenant(tenant_2, status="completed")
        assert len(tenant_2_sessions) == 2


@pytest.mark.skip(
    reason="Cleanup functionality not yet implemented in unified conversation repository"
)
class TestCleanupIntegration:
    """Test cleanup job integration with real workflow."""

    @pytest.mark.asyncio
    async def test_cleanup_job_lifecycle(self, repository: SQLiteConversationRepository) -> None:
        """Verify cleanup job can be started, runs, and stops cleanly."""
        # Create cleaner with short interval for testing
        cleaner = SkillCreationSessionCleaner(repository, cleanup_interval_seconds=1)

        # Start cleaner
        await cleaner.start()
        assert cleaner._running

        # Wait for at least one cleanup cycle
        await asyncio.sleep(1.5)

        # Stop cleaner
        await cleaner.stop()
        assert not cleaner._running

        # Should be safe to stop multiple times
        await cleaner.stop()

    @pytest.mark.asyncio
    async def test_cleanup_removes_old_sessions(
        self, repository: SQLiteConversationRepository, db: Database
    ) -> None:
        """Verify cleanup job actually removes old sessions."""
        tenant_id = "tenant-cleanup-integration"

        # Create a mix of sessions:
        # 1. Recent active session (should not be cleaned)
        recent_context = ConversationContext(session_id="recent-session")
        await save_context_to_repository(repository, recent_context, tenant_id)

        # 2. Old completed session (should be deleted)
        old_completed = ConversationContext(session_id="old-completed")
        old_completed.state = ConversationState.COMPLETED
        await save_context_to_repository(repository, old_completed, tenant_id)

        # 3. Old abandoned session (should be deleted)
        old_abandoned = ConversationContext(session_id="old-abandoned")
        await save_context_to_repository(repository, old_abandoned, tenant_id)

        # Manually update timestamps to be old
        async with db.session() as session:
            from sqlalchemy import update

            # Update completed session to 95 days old
            await session.execute(
                update(ConversationModel)
                .where(ConversationModel.session_id == "old-completed")
                .values(
                    updated_at=datetime.utcnow() - timedelta(days=95),
                    status="completed",
                )
            )

            # Update abandoned session to 35 days old and mark as abandoned
            await session.execute(
                update(ConversationModel)
                .where(ConversationModel.session_id == "old-abandoned")
                .values(
                    updated_at=datetime.utcnow() - timedelta(days=35),
                    status="abandoned",
                )
            )

            await session.flush()

        # Run cleanup manually
        cleaner = SkillCreationSessionCleaner(repository)
        await cleaner._run_cleanup()

        # Verify results
        recent = await load_context_from_repository(repository, "recent-session", tenant_id)
        old_completed_after = await load_context_from_repository(
            repository, "old-completed", tenant_id
        )
        old_abandoned_after = await load_context_from_repository(
            repository, "old-abandoned", tenant_id
        )

        assert recent is not None  # Should still exist
        assert old_completed_after is None  # Should be deleted
        assert old_abandoned_after is None  # Should be deleted


# Fixtures


@pytest.fixture
async def db() -> Database:
    """Create test database."""
    config = DatabaseConfig(url="sqlite+aiosqlite:///:memory:")
    database = Database(config)
    await database.create_tables()
    return database


@pytest.fixture
async def repository(db: Database) -> SQLiteConversationRepository:
    """Create repository fixture."""
    return SQLiteConversationRepository(db)


@pytest.fixture
async def agent_with_persistence(
    repository: SQLiteConversationRepository,
) -> SkillCreationAgent:
    """Create agent with persistence enabled."""
    # Mock LLM generator for faster tests
    mock_llm = AsyncMock()
    mock_llm.generate = AsyncMock(
        return_value=AsyncMock(__aiter__=lambda self: iter(["Test response"]))
    )

    agent = SkillCreationAgent(
        llm_generator=mock_llm,
        conversation_repository=repository,
    )
    return agent
