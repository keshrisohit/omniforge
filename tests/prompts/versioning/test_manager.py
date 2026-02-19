"""Tests for VersionManager class.

This module tests version lifecycle operations including creation,
retrieval, listing, and rollback.
"""

import pytest

from omniforge.prompts.enums import PromptLayer
from omniforge.prompts.errors import PromptNotFoundError, PromptVersionNotFoundError
from omniforge.prompts.models import Prompt, VariableSchema
from omniforge.prompts.storage.memory import InMemoryPromptRepository
from omniforge.prompts.versioning.manager import VersionManager


@pytest.fixture
def repository() -> InMemoryPromptRepository:
    """Create an in-memory repository for testing."""
    return InMemoryPromptRepository()


@pytest.fixture
def version_manager(repository: InMemoryPromptRepository) -> VersionManager:
    """Create a version manager instance."""
    return VersionManager(repository=repository)


@pytest.fixture
async def sample_prompt(repository: InMemoryPromptRepository) -> Prompt:
    """Create a sample prompt for testing."""
    prompt = Prompt(
        id="prompt_001",
        layer=PromptLayer.AGENT,
        scope_id="agent_123",
        name="Test Prompt",
        content="Hello, world!",
        tenant_id="tenant_001",
    )
    return await repository.create(prompt)


class TestCreateInitialVersion:
    """Tests for create_initial_version method."""

    async def test_create_initial_version_success(
        self,
        version_manager: VersionManager,
        sample_prompt: Prompt,
    ) -> None:
        """Initial version should be created with version_number=1."""
        version = await version_manager.create_initial_version(
            prompt=sample_prompt,
            created_by="user_001",
        )

        assert version.prompt_id == sample_prompt.id
        assert version.version_number == 1
        assert version.content == sample_prompt.content
        assert version.change_message == "Initial version"
        assert version.created_by == "user_001"
        assert version.id.startswith("ver_")

    async def test_create_initial_version_copies_merge_points(
        self,
        version_manager: VersionManager,
        repository: InMemoryPromptRepository,
    ) -> None:
        """Initial version should deep copy merge points."""
        from omniforge.prompts.enums import MergeBehavior
        from omniforge.prompts.models import MergePointDefinition

        prompt = Prompt(
            id="prompt_002",
            layer=PromptLayer.TENANT,
            scope_id="tenant_001",
            name="Prompt with Merge Points",
            content="Content with {{merge_here}}",
            merge_points=[
                MergePointDefinition(
                    name="merge_here",
                    behavior=MergeBehavior.INJECT,
                    required=True,
                )
            ],
        )
        prompt = await repository.create(prompt)

        version = await version_manager.create_initial_version(
            prompt=prompt,
            created_by="user_001",
        )

        assert len(version.merge_points) == 1
        assert version.merge_points[0].name == "merge_here"
        assert version.merge_points[0].behavior == MergeBehavior.INJECT

    async def test_create_initial_version_copies_variable_schema(
        self,
        version_manager: VersionManager,
        repository: InMemoryPromptRepository,
    ) -> None:
        """Initial version should deep copy variable schema."""
        prompt = Prompt(
            id="prompt_003",
            layer=PromptLayer.USER,
            scope_id="user_001",
            name="Prompt with Variables",
            content="Hello {{name}}!",
            variables_schema=VariableSchema(
                properties={"name": {"type": "string"}},
                required=["name"],
            ),
        )
        prompt = await repository.create(prompt)

        version = await version_manager.create_initial_version(
            prompt=prompt,
            created_by="user_001",
        )

        assert version.variables_schema is not None
        assert "name" in version.variables_schema.properties
        assert "name" in version.variables_schema.required


class TestCreateVersion:
    """Tests for create_version method."""

    async def test_create_version_increments_version_number(
        self,
        version_manager: VersionManager,
        sample_prompt: Prompt,
    ) -> None:
        """Version number should auto-increment."""
        # Create initial version
        await version_manager.create_initial_version(
            prompt=sample_prompt,
            created_by="user_001",
        )

        # Create second version
        sample_prompt.content = "Updated content"
        version = await version_manager.create_version(
            prompt=sample_prompt,
            change_message="Updated prompt content",
            changed_by="user_002",
        )

        assert version.version_number == 2
        assert version.content == "Updated content"
        assert version.change_message == "Updated prompt content"
        assert version.created_by == "user_002"

    async def test_create_version_multiple_updates(
        self,
        version_manager: VersionManager,
        sample_prompt: Prompt,
    ) -> None:
        """Multiple versions should increment correctly."""
        await version_manager.create_initial_version(
            prompt=sample_prompt,
            created_by="user_001",
        )

        # Create versions 2, 3, 4
        for i in range(2, 5):
            sample_prompt.content = f"Version {i} content"
            version = await version_manager.create_version(
                prompt=sample_prompt,
                change_message=f"Update {i}",
                changed_by=f"user_{i}",
            )
            assert version.version_number == i

    async def test_create_version_without_initial_version(
        self,
        version_manager: VersionManager,
        sample_prompt: Prompt,
    ) -> None:
        """Creating version without initial version should start at 1."""
        version = await version_manager.create_version(
            prompt=sample_prompt,
            change_message="First version",
            changed_by="user_001",
        )

        assert version.version_number == 1


class TestGetVersion:
    """Tests for get_version method."""

    async def test_get_version_success(
        self,
        version_manager: VersionManager,
        sample_prompt: Prompt,
    ) -> None:
        """Should retrieve existing version."""
        created_version = await version_manager.create_initial_version(
            prompt=sample_prompt,
            created_by="user_001",
        )

        retrieved_version = await version_manager.get_version(
            prompt_id=sample_prompt.id,
            version_number=1,
        )

        assert retrieved_version.id == created_version.id
        assert retrieved_version.version_number == 1
        assert retrieved_version.content == sample_prompt.content

    async def test_get_version_not_found(
        self,
        version_manager: VersionManager,
        sample_prompt: Prompt,
    ) -> None:
        """Should raise error when version does not exist."""
        await version_manager.create_initial_version(
            prompt=sample_prompt,
            created_by="user_001",
        )

        with pytest.raises(PromptVersionNotFoundError) as exc_info:
            await version_manager.get_version(
                prompt_id=sample_prompt.id,
                version_number=999,
            )

        assert exc_info.value.prompt_id == sample_prompt.id
        assert exc_info.value.version_number == 999


class TestListVersions:
    """Tests for list_versions method."""

    async def test_list_versions_empty(
        self,
        version_manager: VersionManager,
        sample_prompt: Prompt,
    ) -> None:
        """Should return empty list when no versions exist."""
        versions = await version_manager.list_versions(prompt_id=sample_prompt.id)

        assert versions == []

    async def test_list_versions_single_version(
        self,
        version_manager: VersionManager,
        sample_prompt: Prompt,
    ) -> None:
        """Should return single version in list."""
        await version_manager.create_initial_version(
            prompt=sample_prompt,
            created_by="user_001",
        )

        versions = await version_manager.list_versions(prompt_id=sample_prompt.id)

        assert len(versions) == 1
        assert versions[0].version_number == 1

    async def test_list_versions_descending_order(
        self,
        version_manager: VersionManager,
        sample_prompt: Prompt,
    ) -> None:
        """Should return versions in descending order (newest first)."""
        await version_manager.create_initial_version(
            prompt=sample_prompt,
            created_by="user_001",
        )

        # Create versions 2, 3, 4
        for i in range(2, 5):
            sample_prompt.content = f"Version {i}"
            await version_manager.create_version(
                prompt=sample_prompt,
                change_message=f"Update {i}",
                changed_by="user_001",
            )

        versions = await version_manager.list_versions(prompt_id=sample_prompt.id)

        assert len(versions) == 4
        assert versions[0].version_number == 4
        assert versions[1].version_number == 3
        assert versions[2].version_number == 2
        assert versions[3].version_number == 1

    async def test_list_versions_with_limit(
        self,
        version_manager: VersionManager,
        sample_prompt: Prompt,
    ) -> None:
        """Should respect limit parameter."""
        await version_manager.create_initial_version(
            prompt=sample_prompt,
            created_by="user_001",
        )

        for i in range(2, 6):
            sample_prompt.content = f"Version {i}"
            await version_manager.create_version(
                prompt=sample_prompt,
                change_message=f"Update {i}",
                changed_by="user_001",
            )

        versions = await version_manager.list_versions(
            prompt_id=sample_prompt.id,
            limit=2,
        )

        assert len(versions) == 2
        assert versions[0].version_number == 5
        assert versions[1].version_number == 4

    async def test_list_versions_with_offset(
        self,
        version_manager: VersionManager,
        sample_prompt: Prompt,
    ) -> None:
        """Should respect offset parameter for pagination."""
        await version_manager.create_initial_version(
            prompt=sample_prompt,
            created_by="user_001",
        )

        for i in range(2, 6):
            sample_prompt.content = f"Version {i}"
            await version_manager.create_version(
                prompt=sample_prompt,
                change_message=f"Update {i}",
                changed_by="user_001",
            )

        versions = await version_manager.list_versions(
            prompt_id=sample_prompt.id,
            limit=2,
            offset=2,
        )

        assert len(versions) == 2
        assert versions[0].version_number == 3
        assert versions[1].version_number == 2


class TestRollback:
    """Tests for rollback method."""

    async def test_rollback_success(
        self,
        version_manager: VersionManager,
        sample_prompt: Prompt,
        repository: InMemoryPromptRepository,
    ) -> None:
        """Should successfully rollback to previous version."""
        # Create version 1
        await version_manager.create_initial_version(
            prompt=sample_prompt,
            created_by="user_001",
        )

        # Create version 2
        sample_prompt.content = "Updated content"
        await version_manager.create_version(
            prompt=sample_prompt,
            change_message="Updated",
            changed_by="user_001",
        )

        # Rollback to version 1
        updated_prompt = await version_manager.rollback(
            prompt_id=sample_prompt.id,
            to_version=1,
            rolled_back_by="user_002",
        )

        assert updated_prompt.content == "Hello, world!"

        # Verify rollback created a new version
        versions = await version_manager.list_versions(prompt_id=sample_prompt.id)
        assert len(versions) == 3
        assert versions[0].version_number == 3
        assert versions[0].change_message == "Rolled back to version 1"
        assert versions[0].created_by == "user_002"

    async def test_rollback_restores_merge_points(
        self,
        version_manager: VersionManager,
        repository: InMemoryPromptRepository,
    ) -> None:
        """Rollback should restore merge points from target version."""
        from omniforge.prompts.enums import MergeBehavior
        from omniforge.prompts.models import MergePointDefinition

        # Create prompt with merge points
        prompt = Prompt(
            id="prompt_rollback",
            layer=PromptLayer.TENANT,
            scope_id="tenant_001",
            name="Test Rollback",
            content="Content {{merge1}}",
            merge_points=[
                MergePointDefinition(
                    name="merge1",
                    behavior=MergeBehavior.INJECT,
                )
            ],
        )
        prompt = await repository.create(prompt)

        # Create version 1
        await version_manager.create_initial_version(
            prompt=prompt,
            created_by="user_001",
        )

        # Update and create version 2
        prompt.merge_points = [
            MergePointDefinition(
                name="merge2",
                behavior=MergeBehavior.APPEND,
            )
        ]
        await repository.update(prompt)
        await version_manager.create_version(
            prompt=prompt,
            change_message="Changed merge points",
            changed_by="user_001",
        )

        # Rollback to version 1
        updated_prompt = await version_manager.rollback(
            prompt_id=prompt.id,
            to_version=1,
            rolled_back_by="user_001",
        )

        assert len(updated_prompt.merge_points) == 1
        assert updated_prompt.merge_points[0].name == "merge1"

    async def test_rollback_restores_variable_schema(
        self,
        version_manager: VersionManager,
        repository: InMemoryPromptRepository,
    ) -> None:
        """Rollback should restore variable schema from target version."""
        # Create prompt with variable schema
        prompt = Prompt(
            id="prompt_vars",
            layer=PromptLayer.USER,
            scope_id="user_001",
            name="Test Variables",
            content="Hello {{name}}!",
            variables_schema=VariableSchema(
                properties={"name": {"type": "string"}},
                required=["name"],
            ),
        )
        prompt = await repository.create(prompt)

        # Create version 1
        await version_manager.create_initial_version(
            prompt=prompt,
            created_by="user_001",
        )

        # Update schema and create version 2
        prompt.variables_schema = VariableSchema(
            properties={"email": {"type": "string"}},
            required=["email"],
        )
        await repository.update(prompt)
        await version_manager.create_version(
            prompt=prompt,
            change_message="Changed variables",
            changed_by="user_001",
        )

        # Rollback to version 1
        updated_prompt = await version_manager.rollback(
            prompt_id=prompt.id,
            to_version=1,
            rolled_back_by="user_001",
        )

        assert updated_prompt.variables_schema is not None
        assert "name" in updated_prompt.variables_schema.properties
        assert "name" in updated_prompt.variables_schema.required

    async def test_rollback_prompt_not_found(
        self,
        version_manager: VersionManager,
    ) -> None:
        """Should raise error when prompt does not exist."""
        with pytest.raises(PromptNotFoundError) as exc_info:
            await version_manager.rollback(
                prompt_id="nonexistent",
                to_version=1,
                rolled_back_by="user_001",
            )

        assert exc_info.value.prompt_id == "nonexistent"

    async def test_rollback_version_not_found(
        self,
        version_manager: VersionManager,
        sample_prompt: Prompt,
    ) -> None:
        """Should raise error when target version does not exist."""
        await version_manager.create_initial_version(
            prompt=sample_prompt,
            created_by="user_001",
        )

        with pytest.raises(PromptVersionNotFoundError) as exc_info:
            await version_manager.rollback(
                prompt_id=sample_prompt.id,
                to_version=999,
                rolled_back_by="user_001",
            )

        assert exc_info.value.prompt_id == sample_prompt.id
        assert exc_info.value.version_number == 999


class TestGetCurrentVersion:
    """Tests for get_current_version method."""

    async def test_get_current_version_success(
        self,
        version_manager: VersionManager,
        sample_prompt: Prompt,
    ) -> None:
        """Should return the most recent version."""
        await version_manager.create_initial_version(
            prompt=sample_prompt,
            created_by="user_001",
        )

        sample_prompt.content = "Updated"
        await version_manager.create_version(
            prompt=sample_prompt,
            change_message="Update",
            changed_by="user_001",
        )

        current_version = await version_manager.get_current_version(prompt_id=sample_prompt.id)

        assert current_version.version_number == 2
        assert current_version.content == "Updated"

    async def test_get_current_version_no_versions(
        self,
        version_manager: VersionManager,
        sample_prompt: Prompt,
    ) -> None:
        """Should raise error when no versions exist."""
        with pytest.raises(PromptVersionNotFoundError) as exc_info:
            await version_manager.get_current_version(prompt_id=sample_prompt.id)

        assert exc_info.value.prompt_id == sample_prompt.id
        assert exc_info.value.version_number == 1


class TestVersionImmutability:
    """Tests to verify that versions are immutable."""

    async def test_version_content_not_modified_after_creation(
        self,
        version_manager: VersionManager,
        sample_prompt: Prompt,
    ) -> None:
        """Version content should remain unchanged after prompt updates."""
        # Create initial version
        v1 = await version_manager.create_initial_version(
            prompt=sample_prompt,
            created_by="user_001",
        )

        # Update prompt and create new version
        sample_prompt.content = "Modified content"
        await version_manager.create_version(
            prompt=sample_prompt,
            change_message="Modified",
            changed_by="user_001",
        )

        # Verify version 1 still has original content
        v1_retrieved = await version_manager.get_version(
            prompt_id=sample_prompt.id,
            version_number=1,
        )

        assert v1_retrieved.content == "Hello, world!"
        assert v1_retrieved.content == v1.content

    async def test_version_history_preserved_after_rollback(
        self,
        version_manager: VersionManager,
        sample_prompt: Prompt,
    ) -> None:
        """Version history should be preserved after rollback."""
        # Create versions 1, 2, 3
        await version_manager.create_initial_version(
            prompt=sample_prompt,
            created_by="user_001",
        )

        sample_prompt.content = "Version 2"
        await version_manager.create_version(
            prompt=sample_prompt,
            change_message="v2",
            changed_by="user_001",
        )

        sample_prompt.content = "Version 3"
        await version_manager.create_version(
            prompt=sample_prompt,
            change_message="v3",
            changed_by="user_001",
        )

        # Rollback to version 1
        await version_manager.rollback(
            prompt_id=sample_prompt.id,
            to_version=1,
            rolled_back_by="user_001",
        )

        # All original versions should still exist
        versions = await version_manager.list_versions(prompt_id=sample_prompt.id)
        assert len(versions) == 4  # v1, v2, v3, rollback
        assert versions[3].version_number == 1
        assert versions[3].content == "Hello, world!"
        assert versions[2].version_number == 2
        assert versions[2].content == "Version 2"
        assert versions[1].version_number == 3
        assert versions[1].content == "Version 3"
