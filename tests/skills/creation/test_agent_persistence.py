"""Tests for SkillCreationAgent persistence integration.

This module tests the integration of session persistence into SkillCreationAgent,
including backward compatibility, session restoration, error handling, and tenant isolation.
"""

from pathlib import Path
from typing import Optional
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from omniforge.conversation.models import ConversationType
from omniforge.conversation.sqlite_repository import SQLiteConversationRepository
from omniforge.skills.creation.agent import SkillCreationAgent
from omniforge.skills.creation.models import ConversationContext, ConversationState
from omniforge.skills.storage import StorageConfig
from omniforge.storage.database import Database, DatabaseConfig


# Test helpers for working with unified conversation repository
def _session_id_to_uuid(session_id: str, tenant_id: str = "") -> UUID:
    """Convert session_id to UUID (generate UUID from session_id+tenant_id if not valid UUID).

    Args:
        session_id: Session identifier
        tenant_id: Tenant identifier (included in hash for cross-tenant uniqueness)

    Returns:
        UUID instance
    """
    try:
        return UUID(session_id) if isinstance(session_id, str) else session_id
    except ValueError:
        # If session_id is not a valid UUID, generate UUID4 from MD5 hash
        # Include tenant_id to ensure different tenants get different UUIDs for same session_id
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

    # Serialize context to state_metadata
    state_metadata = {
        "skill_name": context.skill_name,
        "skill_description": context.skill_description,
        "skill_purpose": context.skill_purpose,
        "skill_capabilities": context.skill_capabilities.model_dump()
        if context.skill_capabilities
        else None,
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

    # Check if conversation exists
    existing = await repository.get_conversation(conversation_id, tenant_id)

    if existing:
        # Update existing conversation
        await repository.update_state(
            conversation_id,
            tenant_id,
            state=context.state.value,
            state_metadata=state_metadata,
        )
    else:
        # Create new conversation with specific ID
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

    # Deserialize context from state_metadata
    from omniforge.skills.creation.models import SkillCapabilities

    data = conversation.state_metadata or {}
    context = ConversationContext(session_id=session_id)
    context.state = ConversationState(conversation.state) if conversation.state else ConversationState.IDLE
    context.skill_name = data.get("skill_name")
    context.skill_description = data.get("skill_description")
    context.skill_purpose = data.get("skill_purpose")

    # Deserialize skill_capabilities if present
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


@pytest.fixture
async def db() -> Database:
    """Create an in-memory database for testing."""
    config = DatabaseConfig(url="sqlite+aiosqlite:///:memory:")
    database = Database(config)
    await database.create_tables()
    return database


@pytest.fixture
async def repository(db: Database) -> SQLiteConversationRepository:
    """Create a unified conversation repository instance."""
    return SQLiteConversationRepository(db)


@pytest.fixture
def mock_llm_generator() -> MagicMock:
    """Create a mock LLM generator."""
    mock_gen = MagicMock()

    # Mock generate_stream to return async iterator
    async def mock_stream(prompt: str):
        # Return different responses based on prompt content
        if "pattern" in prompt.lower():
            yield '{"pattern": "simple", "confidence": 0.9}'
        elif "extract all relevant information" in prompt.lower():
            yield """{
                "examples": ["Input: PA, Output: Pro Analytics"],
                "triggers": ["writing documentation"],
                "workflow_steps": [],
                "references_topics": [],
                "scripts_needed": [],
                "extraction_notes": "Extracted 1 example and 1 trigger"
            }"""
        elif "questions" in prompt.lower():
            yield '["What examples can you provide?"]'
        elif "name" in prompt.lower() and "skill" in prompt.lower():
            yield '{"name": "test-skill"}'
        elif "description" in prompt.lower():
            yield '{"description": "A test skill for formatting."}'
        elif "body" in prompt.lower():
            yield "# Test Skill\n\nThis is a test skill body."
        else:
            yield "Test response"

    mock_gen.generate_stream = mock_stream
    return mock_gen


@pytest.fixture
def temp_storage_config(tmp_path: Path) -> StorageConfig:
    """Create temporary storage configuration."""
    project_path = tmp_path / "project" / ".omniforge" / "skills"
    project_path.mkdir(parents=True, exist_ok=True)

    return StorageConfig(
        project_path=project_path,
        personal_path=None,
        enterprise_path=None,
        plugin_paths=[],
    )


class TestAgentBackwardCompatibility:
    """Test agent works without repository (backward compatible)."""

    def test_agent_initializes_without_repository(
        self, mock_llm_generator: MagicMock, temp_storage_config: StorageConfig
    ) -> None:
        """Agent should initialize successfully without repository parameter."""
        # Act
        agent = SkillCreationAgent(
            llm_generator=mock_llm_generator,
            storage_config=temp_storage_config,
            # No conversation_repository parameter
        )

        # Assert
        assert agent.conversation_repository is None
        assert isinstance(agent.sessions, dict)
        assert len(agent.sessions) == 0

    async def test_agent_works_without_repository(
        self, mock_llm_generator: MagicMock, temp_storage_config: StorageConfig
    ) -> None:
        """Agent should work in-memory only when repository is None."""
        # Arrange
        agent = SkillCreationAgent(
            llm_generator=mock_llm_generator,
            storage_config=temp_storage_config,
            conversation_repository=None,
        )

        session_id = "test-session-1"
        tenant_id = "tenant-123"

        # Act - Get context (should create new)
        context = await agent.get_session_context(session_id, tenant_id)

        # Assert
        assert context.session_id == session_id
        assert context.state == ConversationState.IDLE
        assert session_id in agent.sessions

        # Verify context is in memory
        context2 = await agent.get_session_context(session_id, tenant_id)
        assert context2 is context  # Same object from memory


class TestSessionRestoration:
    """Test session restoration from database."""

    async def test_session_restored_from_db(
        self,
        mock_llm_generator: MagicMock,
        temp_storage_config: StorageConfig,
        repository: SQLiteConversationRepository,
    ) -> None:
        """Session should be restored from DB when not in memory."""
        # Arrange
        session_id = "test-session-restore"
        tenant_id = "tenant-123"

        # Create and save a session directly to DB
        context = ConversationContext(
            session_id=session_id,
            state=ConversationState.GATHERING_PURPOSE,
            skill_name="restored-skill",
            skill_description="Restored from DB",
        )
        await save_context_to_repository(repository, context, tenant_id)

        # Create agent with repository
        agent = SkillCreationAgent(
            llm_generator=mock_llm_generator,
            storage_config=temp_storage_config,
            conversation_repository=repository,
        )

        # Act - Get context (should load from DB)
        loaded_context = await agent.get_session_context(session_id, tenant_id)

        # Assert
        assert loaded_context.session_id == session_id
        assert loaded_context.state == ConversationState.GATHERING_PURPOSE
        assert loaded_context.skill_name == "restored-skill"
        assert loaded_context.skill_description == "Restored from DB"

        # Verify context is now in memory cache
        assert session_id in agent.sessions

    async def test_memory_cache_takes_precedence(
        self,
        mock_llm_generator: MagicMock,
        temp_storage_config: StorageConfig,
        repository: SQLiteConversationRepository,
    ) -> None:
        """Memory cache should be checked before database."""
        # Arrange
        session_id = "test-session-cache"
        tenant_id = "tenant-123"

        # Create agent with repository
        agent = SkillCreationAgent(
            llm_generator=mock_llm_generator,
            storage_config=temp_storage_config,
            conversation_repository=repository,
        )

        # Create context in memory
        memory_context = ConversationContext(
            session_id=session_id,
            state=ConversationState.GATHERING_PURPOSE,
            skill_name="memory-skill",
        )
        agent.sessions[session_id] = memory_context

        # Create different context in DB
        db_context = ConversationContext(
            session_id=session_id,
            state=ConversationState.CONFIRMING_SPEC,
            skill_name="db-skill",
        )
        await save_context_to_repository(repository,db_context, tenant_id)

        # Act - Get context (should return memory version)
        loaded_context = await agent.get_session_context(session_id, tenant_id)

        # Assert - Should get memory version, not DB version
        assert loaded_context.skill_name == "memory-skill"
        assert loaded_context.state == ConversationState.GATHERING_PURPOSE

    async def test_new_session_created_if_not_found(
        self,
        mock_llm_generator: MagicMock,
        temp_storage_config: StorageConfig,
        repository: SQLiteConversationRepository,
    ) -> None:
        """New session should be created if not found in memory or DB."""
        # Arrange
        session_id = "test-session-new"
        tenant_id = "tenant-123"

        agent = SkillCreationAgent(
            llm_generator=mock_llm_generator,
            storage_config=temp_storage_config,
            conversation_repository=repository,
        )

        # Act - Get context (should create new)
        context = await agent.get_session_context(session_id, tenant_id)

        # Assert
        assert context.session_id == session_id
        assert context.state == ConversationState.IDLE
        assert session_id in agent.sessions


class TestPersistenceErrorHandling:
    """Test persistence error handling doesn't crash agent."""

    async def test_persistence_error_logged_but_not_raised(
        self,
        mock_llm_generator: MagicMock,
        temp_storage_config: StorageConfig,
    ) -> None:
        """Persistence errors should be logged but not crash agent."""
        # Arrange
        mock_repo = MagicMock(spec=SQLiteConversationRepository)
        # Mock the unified repository methods
        mock_repo.get_conversation = AsyncMock(return_value=None)
        mock_repo.create_conversation = AsyncMock(side_effect=Exception("DB connection failed"))

        agent = SkillCreationAgent(
            llm_generator=mock_llm_generator,
            storage_config=temp_storage_config,
            conversation_repository=mock_repo,
        )

        session_id = "test-session-error"
        tenant_id = "tenant-123"
        context = ConversationContext(session_id=session_id)

        # Act - Persist with error (should not raise by default)
        try:
            await agent._persist_context(context, tenant_id, ignore_errors=False)
            assert False, "Should have raised exception"
        except Exception as e:
            assert str(e) == "DB connection failed"

    async def test_persistence_error_ignored_when_flag_set(
        self,
        mock_llm_generator: MagicMock,
        temp_storage_config: StorageConfig,
    ) -> None:
        """Persistence errors should be suppressed when ignore_errors=True."""
        # Arrange
        mock_repo = MagicMock(spec=SQLiteConversationRepository)
        # Mock the unified repository methods
        mock_repo.get_conversation = AsyncMock(return_value=None)
        mock_repo.create_conversation = AsyncMock(side_effect=Exception("DB connection failed"))

        agent = SkillCreationAgent(
            llm_generator=mock_llm_generator,
            storage_config=temp_storage_config,
            conversation_repository=mock_repo,
        )

        session_id = "test-session-error-ignored"
        tenant_id = "tenant-123"
        context = ConversationContext(session_id=session_id)

        # Act - Persist with error but ignore_errors=True (should not raise)
        await agent._persist_context(context, tenant_id, ignore_errors=True)

        # Assert - No exception raised, execution continues

    async def test_db_load_error_creates_new_session(
        self,
        mock_llm_generator: MagicMock,
        temp_storage_config: StorageConfig,
    ) -> None:
        """If DB load fails, agent should create new session and continue."""
        # Arrange
        mock_repo = MagicMock(spec=SQLiteConversationRepository)
        # Mock the unified repository methods
        mock_repo.get_conversation = AsyncMock(side_effect=Exception("DB read failed"))

        agent = SkillCreationAgent(
            llm_generator=mock_llm_generator,
            storage_config=temp_storage_config,
            conversation_repository=mock_repo,
        )

        session_id = "test-session-load-error"
        tenant_id = "tenant-123"

        # Act - Get context (DB fails, should create new)
        context = await agent.get_session_context(session_id, tenant_id)

        # Assert
        assert context.session_id == session_id
        assert context.state == ConversationState.IDLE
        assert session_id in agent.sessions


class TestTenantIsolation:
    """Test tenant isolation at agent level."""

    async def test_different_tenants_have_separate_sessions(
        self,
        mock_llm_generator: MagicMock,
        temp_storage_config: StorageConfig,
        repository: SQLiteConversationRepository,
    ) -> None:
        """Sessions should be isolated by tenant."""
        # Arrange
        session_id = "shared-session-id"
        tenant1 = "tenant-111"
        tenant2 = "tenant-222"

        agent = SkillCreationAgent(
            llm_generator=mock_llm_generator,
            storage_config=temp_storage_config,
            conversation_repository=repository,
        )

        # Create session for tenant 1
        context1 = ConversationContext(
            session_id=session_id,
            state=ConversationState.GATHERING_PURPOSE,
            skill_name="tenant1-skill",
        )
        await save_context_to_repository(repository,context1, tenant1)

        # Create session for tenant 2 with same session_id
        context2 = ConversationContext(
            session_id=session_id,
            state=ConversationState.CONFIRMING_SPEC,
            skill_name="tenant2-skill",
        )
        await save_context_to_repository(repository,context2, tenant2)

        # Act - Load for each tenant
        loaded1 = await agent.get_session_context(session_id, tenant1)
        # Clear memory to force DB reload for tenant2
        agent.sessions.clear()
        loaded2 = await agent.get_session_context(session_id, tenant2)

        # Assert - Each tenant gets their own session
        assert loaded1.skill_name == "tenant1-skill"
        assert loaded1.state == ConversationState.GATHERING_PURPOSE

        assert loaded2.skill_name == "tenant2-skill"
        assert loaded2.state == ConversationState.CONFIRMING_SPEC

    async def test_clear_session_respects_tenant_id(
        self,
        mock_llm_generator: MagicMock,
        temp_storage_config: StorageConfig,
        repository: SQLiteConversationRepository,
    ) -> None:
        """Clearing session should respect tenant isolation."""
        # Arrange
        session_id = "test-clear-session"
        tenant1 = "tenant-111"
        tenant2 = "tenant-222"

        agent = SkillCreationAgent(
            llm_generator=mock_llm_generator,
            storage_config=temp_storage_config,
            conversation_repository=repository,
        )

        # Create sessions for both tenants
        context1 = ConversationContext(session_id=session_id)
        await save_context_to_repository(repository,context1, tenant1)

        context2 = ConversationContext(session_id=session_id)
        await save_context_to_repository(repository,context2, tenant2)

        # Act - Clear session for tenant1
        await agent._clear_session(session_id, tenant1)

        # Assert - Memory is cleared for tenant1
        assert session_id not in agent.sessions  # Cleared from memory

        # To verify tenant2 is unaffected, load it
        loaded2 = await load_context_from_repository(repository, session_id, tenant2)
        assert loaded2 is not None  # Still exists


class TestContextPersistence:
    """Test context is persisted at the right times."""

    async def test_context_persisted_after_message_processing(
        self,
        mock_llm_generator: MagicMock,
        temp_storage_config: StorageConfig,
        repository: SQLiteConversationRepository,
    ) -> None:
        """Context should be persisted after processing each message."""
        # Arrange
        agent = SkillCreationAgent(
            llm_generator=mock_llm_generator,
            storage_config=temp_storage_config,
            conversation_repository=repository,
        )

        session_id = "test-persist-message"
        tenant_id = "tenant-123"

        # Act - Handle a message
        response_chunks = []
        async for chunk in agent.handle_message(
            "Create a skill for formatting product names",
            session_id,
            tenant_id,
        ):
            response_chunks.append(chunk)

        # Assert - Context should be persisted to DB
        loaded = await load_context_from_repository(repository, session_id, tenant_id)
        assert loaded is not None
        assert loaded.session_id == session_id
        # State should have progressed from IDLE
        assert loaded.state != ConversationState.IDLE

    async def test_context_persisted_on_error(
        self,
        mock_llm_generator: MagicMock,
        temp_storage_config: StorageConfig,
        repository: SQLiteConversationRepository,
    ) -> None:
        """Context should be persisted even when errors occur."""
        # Arrange
        # Make conversation manager raise an error
        agent = SkillCreationAgent(
            llm_generator=mock_llm_generator,
            storage_config=temp_storage_config,
            conversation_repository=repository,
        )

        # Mock conversation manager to raise error
        agent.conversation_manager.process_message = AsyncMock(
            side_effect=Exception("Processing failed")
        )

        session_id = "test-persist-error"
        tenant_id = "tenant-123"

        # Act - Handle message (will error but should persist)
        response_chunks = []
        async for chunk in agent.handle_message(
            "Create a skill",
            session_id,
            tenant_id,
        ):
            response_chunks.append(chunk)

        # Assert - Context should be persisted despite error
        loaded = await load_context_from_repository(repository, session_id, tenant_id)
        assert loaded is not None
        assert loaded.session_id == session_id
        # Should have transitioned to GATHERING_DETAILS for recovery
        assert loaded.state == ConversationState.GATHERING_DETAILS
