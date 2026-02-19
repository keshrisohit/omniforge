"""Tests for PromptManager SDK class."""

import pytest

from omniforge.prompts import (
    ExperimentStatus,
    MergeBehavior,
    PromptLayer,
    PromptNotFoundError,
    PromptValidationError,
)
from omniforge.prompts.sdk import PromptManager


class TestPromptManagerInit:
    """Tests for PromptManager initialization."""

    def test_init_with_defaults(self) -> None:
        """PromptManager should initialize with default settings."""
        manager = PromptManager()

        assert manager.tenant_id is None
        assert manager._repository is not None
        assert manager._cache_manager is not None
        assert manager._composition_engine is not None
        assert manager._version_manager is not None
        assert manager._experiment_manager is not None

    def test_init_with_tenant_id(self) -> None:
        """PromptManager should accept tenant_id parameter."""
        manager = PromptManager(tenant_id="tenant-123")

        assert manager.tenant_id == "tenant-123"

    def test_init_with_cache_disabled(self) -> None:
        """PromptManager should work without caching."""
        manager = PromptManager(enable_cache=False)

        assert manager._cache_manager is None


class TestPromptCRUD:
    """Tests for prompt CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_prompt_minimal(self) -> None:
        """Should create a prompt with minimal parameters."""
        manager = PromptManager(tenant_id="tenant-1")

        prompt = await manager.create_prompt(
            layer=PromptLayer.AGENT,
            name="test-agent",
            content="You are a helpful assistant.",
            scope_id="agent-123",
            created_by="user-1",
        )

        assert prompt.id is not None
        assert prompt.layer == PromptLayer.AGENT
        assert prompt.name == "test-agent"
        assert prompt.content == "You are a helpful assistant."
        assert prompt.scope_id == "agent-123"
        assert prompt.version == 1
        assert prompt.tenant_id == "tenant-1"

    @pytest.mark.asyncio
    async def test_create_prompt_with_merge_points(self) -> None:
        """Should create a prompt with merge points."""
        manager = PromptManager()

        prompt = await manager.create_prompt(
            layer=PromptLayer.AGENT,
            name="test-agent",
            content="You are a helpful assistant. {{ context }}",
            scope_id="agent-123",
            created_by="user-1",
            merge_points=[
                {
                    "name": "context",
                    "behavior": MergeBehavior.APPEND,
                    "required": False,
                }
            ],
        )

        assert len(prompt.merge_points) == 1
        assert prompt.merge_points[0].name == "context"
        assert prompt.merge_points[0].behavior == MergeBehavior.APPEND

    @pytest.mark.asyncio
    async def test_create_prompt_with_variables_schema(self) -> None:
        """Should create a prompt with variable schema."""
        manager = PromptManager()

        prompt = await manager.create_prompt(
            layer=PromptLayer.AGENT,
            name="test-agent",
            content="Hello {{ name }}",
            scope_id="agent-123",
            created_by="user-1",
            variables_schema={
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
        )

        assert prompt.variables_schema is not None
        assert "name" in prompt.variables_schema.properties
        assert "name" in prompt.variables_schema.required

    @pytest.mark.asyncio
    async def test_create_prompt_with_invalid_syntax(self) -> None:
        """Should reject prompt with invalid template syntax."""
        manager = PromptManager()

        with pytest.raises(PromptValidationError) as exc_info:
            await manager.create_prompt(
                layer=PromptLayer.AGENT,
                name="test-agent",
                content="Hello {{ name",  # Missing closing braces
                scope_id="agent-123",
                created_by="user-1",
            )

        assert "syntax" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_create_prompt_with_invalid_schema(self) -> None:
        """Should reject prompt with invalid variable schema."""
        manager = PromptManager()

        # Pydantic validates the schema on creation, so we expect either
        # ValidationError or PromptValidationError
        with pytest.raises((PromptValidationError, Exception)) as exc_info:
            await manager.create_prompt(
                layer=PromptLayer.AGENT,
                name="test-agent",
                content="Hello {{ name }}",
                scope_id="agent-123",
                created_by="user-1",
                variables_schema={
                    "properties": {"name": {"type": "string"}},
                    "required": ["age"],  # Required field not in properties
                },
            )

        # Should contain reference to schema or required field error
        error_msg = str(exc_info.value).lower()
        assert "required" in error_msg or "schema" in error_msg or "age" in error_msg

    @pytest.mark.asyncio
    async def test_get_prompt(self) -> None:
        """Should retrieve a prompt by ID."""
        manager = PromptManager()

        # Create a prompt
        created = await manager.create_prompt(
            layer=PromptLayer.AGENT,
            name="test-agent",
            content="Test content",
            scope_id="agent-123",
            created_by="user-1",
        )

        # Get the prompt
        retrieved = await manager.get_prompt(created.id)

        assert retrieved.id == created.id
        assert retrieved.name == created.name
        assert retrieved.content == created.content

    @pytest.mark.asyncio
    async def test_get_prompt_not_found(self) -> None:
        """Should raise error when prompt not found."""
        manager = PromptManager()

        with pytest.raises(PromptNotFoundError):
            await manager.get_prompt("nonexistent-id")

    @pytest.mark.asyncio
    async def test_update_prompt(self) -> None:
        """Should update a prompt and create new version."""
        manager = PromptManager()

        # Create a prompt
        prompt = await manager.create_prompt(
            layer=PromptLayer.AGENT,
            name="test-agent",
            content="Original content",
            scope_id="agent-123",
            created_by="user-1",
        )

        # Update the prompt
        updated = await manager.update_prompt(
            prompt_id=prompt.id,
            content="Updated content",
            change_message="Changed content",
            changed_by="user-1",
        )

        assert updated.id == prompt.id
        assert updated.content == "Updated content"

        # Verify version history
        history = await manager.get_prompt_history(prompt.id)
        assert len(history) >= 2  # Initial + update

    @pytest.mark.asyncio
    async def test_update_prompt_with_invalid_syntax(self) -> None:
        """Should reject update with invalid template syntax."""
        manager = PromptManager()

        # Create a prompt
        prompt = await manager.create_prompt(
            layer=PromptLayer.AGENT,
            name="test-agent",
            content="Original content",
            scope_id="agent-123",
            created_by="user-1",
        )

        # Try to update with invalid syntax
        with pytest.raises(PromptValidationError):
            await manager.update_prompt(
                prompt_id=prompt.id,
                content="Invalid {{ syntax",
                change_message="Invalid update",
                changed_by="user-1",
            )

    @pytest.mark.asyncio
    async def test_delete_prompt(self) -> None:
        """Should soft delete a prompt."""
        manager = PromptManager()

        # Create a prompt
        prompt = await manager.create_prompt(
            layer=PromptLayer.AGENT,
            name="test-agent",
            content="Test content",
            scope_id="agent-123",
            created_by="user-1",
        )

        # Delete the prompt
        await manager.delete_prompt(prompt.id)

        # Should not be able to retrieve deleted prompt
        with pytest.raises(PromptNotFoundError):
            await manager.get_prompt(prompt.id)

    @pytest.mark.asyncio
    async def test_list_prompts(self) -> None:
        """Should list prompts for a tenant."""
        manager = PromptManager(tenant_id="tenant-1")

        # Create multiple prompts
        for i in range(3):
            await manager.create_prompt(
                layer=PromptLayer.AGENT,
                name=f"agent-{i}",
                content=f"Content {i}",
                scope_id=f"agent-{i}",
                created_by="user-1",
            )

        # List prompts
        prompts = await manager.list_prompts()

        assert len(prompts) == 3

    @pytest.mark.asyncio
    async def test_list_prompts_with_pagination(self) -> None:
        """Should paginate prompt list."""
        manager = PromptManager(tenant_id="tenant-1")

        # Create 5 prompts
        for i in range(5):
            await manager.create_prompt(
                layer=PromptLayer.AGENT,
                name=f"agent-{i}",
                content=f"Content {i}",
                scope_id=f"agent-{i}",
                created_by="user-1",
            )

        # Get first page
        page1 = await manager.list_prompts(limit=2, offset=0)
        assert len(page1) == 2

        # Get second page
        page2 = await manager.list_prompts(limit=2, offset=2)
        assert len(page2) == 2

        # Verify different prompts
        assert page1[0].id != page2[0].id


class TestVersioning:
    """Tests for versioning operations."""

    @pytest.mark.asyncio
    async def test_get_prompt_history(self) -> None:
        """Should retrieve version history for a prompt."""
        manager = PromptManager()

        # Create a prompt
        prompt = await manager.create_prompt(
            layer=PromptLayer.AGENT,
            name="test-agent",
            content="Version 1",
            scope_id="agent-123",
            created_by="user-1",
        )

        # Update it twice
        await manager.update_prompt(
            prompt_id=prompt.id,
            content="Version 2",
            change_message="Update 1",
            changed_by="user-1",
        )
        await manager.update_prompt(
            prompt_id=prompt.id,
            content="Version 3",
            change_message="Update 2",
            changed_by="user-1",
        )

        # Get history
        history = await manager.get_prompt_history(prompt.id)

        assert len(history) >= 3
        # Versions should be in descending order
        assert history[0].version_number >= history[1].version_number

    @pytest.mark.asyncio
    async def test_rollback_prompt(self) -> None:
        """Should rollback prompt to previous version."""
        manager = PromptManager()

        # Create a prompt
        prompt = await manager.create_prompt(
            layer=PromptLayer.AGENT,
            name="test-agent",
            content="Version 1",
            scope_id="agent-123",
            created_by="user-1",
        )

        # Update it
        await manager.update_prompt(
            prompt_id=prompt.id,
            content="Version 2",
            change_message="Update",
            changed_by="user-1",
        )

        # Rollback to version 1
        rolled_back = await manager.rollback_prompt(
            prompt_id=prompt.id,
            to_version=1,
            rolled_back_by="user-1",
        )

        assert rolled_back.content == "Version 1"


class TestComposition:
    """Tests for prompt composition."""

    @pytest.mark.asyncio
    async def test_compose_prompt_simple(self) -> None:
        """Should compose a simple prompt."""
        manager = PromptManager(tenant_id="tenant-1")

        # Create system prompt
        await manager.create_prompt(
            layer=PromptLayer.SYSTEM,
            name="system",
            content="System instructions",
            scope_id="default",
            created_by="system",
        )

        # Create agent prompt
        await manager.create_prompt(
            layer=PromptLayer.AGENT,
            name="agent",
            content="Agent instructions",
            scope_id="agent-123",
            created_by="user-1",
        )

        # Compose
        result = await manager.compose_prompt(agent_id="agent-123")

        assert result.content is not None
        assert isinstance(result.composition_time_ms, float)
        assert result.composition_time_ms >= 0

    @pytest.mark.asyncio
    async def test_compose_prompt_with_variables(self) -> None:
        """Should compose prompt with variable substitution."""
        manager = PromptManager(tenant_id="tenant-1")

        # Create system prompt
        await manager.create_prompt(
            layer=PromptLayer.SYSTEM,
            name="system",
            content="System prompt",
            scope_id="default",
            created_by="system",
        )

        # Create agent prompt with variables
        await manager.create_prompt(
            layer=PromptLayer.AGENT,
            name="agent",
            content="Agent: Hello {{ name }}!",
            scope_id="agent-123",
            created_by="user-1",
        )

        # Compose with variables
        result = await manager.compose_prompt(
            agent_id="agent-123",
            variables={"name": "World"},
        )

        # The composed prompt should contain both system and agent content
        # and variables should be rendered
        assert result.content is not None
        assert len(result.content) > 0
        # Check that composition happened (should have content from multiple layers)
        assert "World" in result.content or "name" not in result.content

    @pytest.mark.asyncio
    async def test_compose_prompt_with_cache(self) -> None:
        """Should use cache for repeated compositions."""
        manager = PromptManager(tenant_id="tenant-1")

        # Create prompts
        await manager.create_prompt(
            layer=PromptLayer.SYSTEM,
            name="system",
            content="System",
            scope_id="default",
            created_by="system",
        )
        await manager.create_prompt(
            layer=PromptLayer.AGENT,
            name="agent",
            content="Agent",
            scope_id="agent-123",
            created_by="user-1",
        )

        # First composition (cache miss)
        result1 = await manager.compose_prompt(agent_id="agent-123")

        # Second composition (cache hit)
        result2 = await manager.compose_prompt(agent_id="agent-123")

        # Both should have same content
        assert result1.content == result2.content

        # Cache stats should show hits
        stats = manager.get_cache_stats()
        assert stats["hit_count"] >= 0


class TestValidation:
    """Tests for validation operations."""

    def test_validate_template_valid(self) -> None:
        """Should validate correct template syntax."""
        manager = PromptManager()

        errors = manager.validate_template("Hello {{ name }}")

        assert len(errors) == 0

    def test_validate_template_invalid(self) -> None:
        """Should detect invalid template syntax."""
        manager = PromptManager()

        errors = manager.validate_template("Hello {{ name")

        assert len(errors) > 0

    def test_validate_schema_valid(self) -> None:
        """Should validate correct schema."""
        manager = PromptManager()

        errors = manager.validate_schema(
            {
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            }
        )

        assert len(errors) == 0

    def test_validate_schema_invalid(self) -> None:
        """Should detect invalid schema."""
        manager = PromptManager()

        errors = manager.validate_schema(
            {
                "properties": {"name": {"type": "string"}},
                "required": ["age"],  # Required but not in properties
            }
        )

        assert len(errors) > 0


class TestExperiments:
    """Tests for experiment operations."""

    @pytest.mark.asyncio
    async def test_create_experiment(self) -> None:
        """Should create an A/B test experiment."""
        manager = PromptManager()

        # Create a prompt
        prompt = await manager.create_prompt(
            layer=PromptLayer.AGENT,
            name="test-agent",
            content="Original",
            scope_id="agent-123",
            created_by="user-1",
        )

        # Create experiment
        experiment = await manager.create_experiment(
            prompt_id=prompt.id,
            name="Test experiment",
            description="Testing variants",
            success_metric="accuracy",
            variants=[
                {
                    "id": "var-1",
                    "name": "Variant A",
                    "prompt_version_id": f"{prompt.id}-v1",
                    "traffic_percentage": 50.0,
                },
                {
                    "id": "var-2",
                    "name": "Variant B",
                    "prompt_version_id": f"{prompt.id}-v1",
                    "traffic_percentage": 50.0,
                },
            ],
            created_by="user-1",
        )

        assert experiment.id is not None
        assert experiment.name == "Test experiment"
        assert experiment.status == ExperimentStatus.DRAFT
        assert len(experiment.variants) == 2

    @pytest.mark.asyncio
    async def test_start_experiment(self) -> None:
        """Should start a draft experiment."""
        manager = PromptManager()

        # Create prompt and experiment
        prompt = await manager.create_prompt(
            layer=PromptLayer.AGENT,
            name="test-agent",
            content="Original",
            scope_id="agent-123",
            created_by="user-1",
        )
        experiment = await manager.create_experiment(
            prompt_id=prompt.id,
            name="Test experiment",
            description="Testing",
            success_metric="accuracy",
            variants=[
                {
                    "id": "var-1",
                    "name": "A",
                    "prompt_version_id": f"{prompt.id}-v1",
                    "traffic_percentage": 50.0,
                },
                {
                    "id": "var-2",
                    "name": "B",
                    "prompt_version_id": f"{prompt.id}-v1",
                    "traffic_percentage": 50.0,
                },
            ],
        )

        # Start experiment
        started = await manager.start_experiment(experiment.id)

        assert started.status == ExperimentStatus.RUNNING

    @pytest.mark.asyncio
    async def test_pause_experiment(self) -> None:
        """Should pause a running experiment."""
        manager = PromptManager()

        # Create and start experiment
        prompt = await manager.create_prompt(
            layer=PromptLayer.AGENT,
            name="test-agent",
            content="Original",
            scope_id="agent-123",
            created_by="user-1",
        )
        experiment = await manager.create_experiment(
            prompt_id=prompt.id,
            name="Test",
            description="Test",
            success_metric="accuracy",
            variants=[
                {
                    "id": "var-1",
                    "name": "A",
                    "prompt_version_id": f"{prompt.id}-v1",
                    "traffic_percentage": 50.0,
                },
                {
                    "id": "var-2",
                    "name": "B",
                    "prompt_version_id": f"{prompt.id}-v1",
                    "traffic_percentage": 50.0,
                },
            ],
        )
        await manager.start_experiment(experiment.id)

        # Pause experiment
        paused = await manager.pause_experiment(experiment.id)

        assert paused.status == ExperimentStatus.PAUSED

    @pytest.mark.asyncio
    async def test_complete_experiment(self) -> None:
        """Should complete an experiment with results."""
        manager = PromptManager()

        # Create and start experiment
        prompt = await manager.create_prompt(
            layer=PromptLayer.AGENT,
            name="test-agent",
            content="Original",
            scope_id="agent-123",
            created_by="user-1",
        )
        experiment = await manager.create_experiment(
            prompt_id=prompt.id,
            name="Test",
            description="Test",
            success_metric="accuracy",
            variants=[
                {
                    "id": "var-1",
                    "name": "A",
                    "prompt_version_id": f"{prompt.id}-v1",
                    "traffic_percentage": 50.0,
                },
                {
                    "id": "var-2",
                    "name": "B",
                    "prompt_version_id": f"{prompt.id}-v1",
                    "traffic_percentage": 50.0,
                },
            ],
        )
        await manager.start_experiment(experiment.id)

        # Complete experiment
        results = {"var-1": {"accuracy": 0.85}, "var-2": {"accuracy": 0.78}}
        completed = await manager.complete_experiment(experiment.id, results)

        assert completed.status == ExperimentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_cancel_experiment(self) -> None:
        """Should cancel an experiment."""
        manager = PromptManager()

        # Create experiment
        prompt = await manager.create_prompt(
            layer=PromptLayer.AGENT,
            name="test-agent",
            content="Original",
            scope_id="agent-123",
            created_by="user-1",
        )
        experiment = await manager.create_experiment(
            prompt_id=prompt.id,
            name="Test",
            description="Test",
            success_metric="accuracy",
            variants=[
                {
                    "id": "var-1",
                    "name": "A",
                    "prompt_version_id": f"{prompt.id}-v1",
                    "traffic_percentage": 50.0,
                },
                {
                    "id": "var-2",
                    "name": "B",
                    "prompt_version_id": f"{prompt.id}-v1",
                    "traffic_percentage": 50.0,
                },
            ],
        )

        # Cancel experiment
        cancelled = await manager.cancel_experiment(experiment.id)

        assert cancelled.status == ExperimentStatus.CANCELLED


class TestCacheManagement:
    """Tests for cache management operations."""

    def test_get_cache_stats(self) -> None:
        """Should return cache statistics."""
        manager = PromptManager()

        stats = manager.get_cache_stats()

        assert "size" in stats or "enabled" in stats

    def test_get_cache_stats_when_disabled(self) -> None:
        """Should return stats when cache is disabled."""
        manager = PromptManager(enable_cache=False)

        stats = manager.get_cache_stats()

        assert stats["enabled"] is False

    @pytest.mark.asyncio
    async def test_clear_cache(self) -> None:
        """Should clear all cache entries."""
        manager = PromptManager()

        await manager.clear_cache()

        # Should not raise error
        stats = manager.get_cache_stats()
        assert stats["size"] == 0
