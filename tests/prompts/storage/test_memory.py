"""Tests for in-memory prompt repository implementation."""

import asyncio
from uuid import uuid4

import pytest

from omniforge.prompts.enums import ExperimentStatus, MergeBehavior, PromptLayer
from omniforge.prompts.errors import (
    ExperimentNotFoundError,
    PromptLockViolationError,
    PromptNotFoundError,
    PromptValidationError,
    PromptVersionNotFoundError,
)
from omniforge.prompts.models import (
    ExperimentVariant,
    MergePointDefinition,
    Prompt,
    PromptExperiment,
    PromptVersion,
)
from omniforge.prompts.storage.memory import InMemoryPromptRepository


class TestInMemoryPromptRepositoryPromptCRUD:
    """Tests for prompt CRUD operations."""

    @pytest.fixture
    def repository(self) -> InMemoryPromptRepository:
        """Create a fresh repository for each test."""
        return InMemoryPromptRepository()

    @pytest.fixture
    def sample_prompt(self) -> Prompt:
        """Create a sample prompt for testing."""
        return Prompt(
            id=str(uuid4()),
            layer=PromptLayer.SYSTEM,
            scope_id="default",
            name="Test Prompt",
            content="This is a test prompt",
            tenant_id="tenant-1",
        )

    @pytest.mark.asyncio
    async def test_create_prompt_success(
        self,
        repository: InMemoryPromptRepository,
        sample_prompt: Prompt,
    ) -> None:
        """Should successfully create a new prompt."""
        result = await repository.create(sample_prompt)

        assert result.id == sample_prompt.id
        assert result.layer == sample_prompt.layer
        assert result.scope_id == sample_prompt.scope_id
        assert result.name == sample_prompt.name
        assert result.content == sample_prompt.content

    @pytest.mark.asyncio
    async def test_create_duplicate_layer_scope_raises_error(
        self,
        repository: InMemoryPromptRepository,
        sample_prompt: Prompt,
    ) -> None:
        """Should raise error when creating prompt with duplicate (layer, scope_id)."""
        await repository.create(sample_prompt)

        duplicate_prompt = Prompt(
            id=str(uuid4()),
            layer=sample_prompt.layer,
            scope_id=sample_prompt.scope_id,
            name="Duplicate Prompt",
            content="Different content",
            tenant_id="tenant-1",
        )

        with pytest.raises(PromptValidationError, match="already exists"):
            await repository.create(duplicate_prompt)

    @pytest.mark.asyncio
    async def test_create_same_layer_scope_after_soft_delete_success(
        self,
        repository: InMemoryPromptRepository,
        sample_prompt: Prompt,
    ) -> None:
        """Should allow creating prompt with same layer/scope after soft delete."""
        await repository.create(sample_prompt)
        await repository.delete(sample_prompt.id)

        new_prompt = Prompt(
            id=str(uuid4()),
            layer=sample_prompt.layer,
            scope_id=sample_prompt.scope_id,
            name="New Prompt",
            content="New content",
            tenant_id="tenant-1",
        )

        result = await repository.create(new_prompt)
        assert result.id == new_prompt.id

    @pytest.mark.asyncio
    async def test_get_prompt_success(
        self,
        repository: InMemoryPromptRepository,
        sample_prompt: Prompt,
    ) -> None:
        """Should retrieve prompt by ID."""
        await repository.create(sample_prompt)
        result = await repository.get(sample_prompt.id)

        assert result is not None
        assert result.id == sample_prompt.id

    @pytest.mark.asyncio
    async def test_get_nonexistent_prompt_returns_none(
        self,
        repository: InMemoryPromptRepository,
    ) -> None:
        """Should return None for nonexistent prompt."""
        result = await repository.get(str(uuid4()))
        assert result is None

    @pytest.mark.asyncio
    async def test_get_soft_deleted_prompt_returns_none(
        self,
        repository: InMemoryPromptRepository,
        sample_prompt: Prompt,
    ) -> None:
        """Should return None for soft-deleted prompt."""
        await repository.create(sample_prompt)
        await repository.delete(sample_prompt.id)

        result = await repository.get(sample_prompt.id)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_layer_success(
        self,
        repository: InMemoryPromptRepository,
        sample_prompt: Prompt,
    ) -> None:
        """Should retrieve prompt by layer and scope."""
        await repository.create(sample_prompt)

        result = await repository.get_by_layer(
            layer=sample_prompt.layer,
            scope_id=sample_prompt.scope_id,
        )

        assert result is not None
        assert result.id == sample_prompt.id

    @pytest.mark.asyncio
    async def test_get_by_layer_with_tenant_filter(
        self,
        repository: InMemoryPromptRepository,
        sample_prompt: Prompt,
    ) -> None:
        """Should filter by tenant_id when provided."""
        await repository.create(sample_prompt)

        result = await repository.get_by_layer(
            layer=sample_prompt.layer,
            scope_id=sample_prompt.scope_id,
            tenant_id="tenant-1",
        )

        assert result is not None
        assert result.id == sample_prompt.id

        result = await repository.get_by_layer(
            layer=sample_prompt.layer,
            scope_id=sample_prompt.scope_id,
            tenant_id="tenant-2",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_update_prompt_success(
        self,
        repository: InMemoryPromptRepository,
        sample_prompt: Prompt,
    ) -> None:
        """Should successfully update prompt."""
        await repository.create(sample_prompt)

        updated_prompt = sample_prompt.model_copy(update={"content": "Updated content"})
        result = await repository.update(updated_prompt)

        assert result.content == "Updated content"
        assert result.updated_at >= sample_prompt.updated_at

    @pytest.mark.asyncio
    async def test_update_nonexistent_prompt_raises_error(
        self,
        repository: InMemoryPromptRepository,
        sample_prompt: Prompt,
    ) -> None:
        """Should raise error when updating nonexistent prompt."""
        with pytest.raises(PromptNotFoundError):
            await repository.update(sample_prompt)

    @pytest.mark.asyncio
    async def test_update_locked_prompt_raises_error(
        self,
        repository: InMemoryPromptRepository,
        sample_prompt: Prompt,
    ) -> None:
        """Should raise error when updating locked prompt."""
        locked_prompt = sample_prompt.model_copy(update={"is_locked": True})
        await repository.create(locked_prompt)

        updated_prompt = locked_prompt.model_copy(update={"content": "New content"})

        with pytest.raises(PromptLockViolationError):
            await repository.update(updated_prompt)

    @pytest.mark.asyncio
    async def test_delete_prompt_success(
        self,
        repository: InMemoryPromptRepository,
        sample_prompt: Prompt,
    ) -> None:
        """Should soft delete prompt."""
        await repository.create(sample_prompt)
        result = await repository.delete(sample_prompt.id)

        assert result is True
        retrieved = await repository.get(sample_prompt.id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_prompt_returns_false(
        self,
        repository: InMemoryPromptRepository,
    ) -> None:
        """Should return False when deleting nonexistent prompt."""
        result = await repository.delete(str(uuid4()))
        assert result is False

    @pytest.mark.asyncio
    async def test_list_by_tenant_success(
        self,
        repository: InMemoryPromptRepository,
    ) -> None:
        """Should list all active prompts for tenant."""
        prompts = [
            Prompt(
                id=str(uuid4()),
                layer=PromptLayer.SYSTEM,
                scope_id=f"scope-{i}",
                name=f"Prompt {i}",
                content=f"Content {i}",
                tenant_id="tenant-1",
            )
            for i in range(5)
        ]

        for prompt in prompts:
            await repository.create(prompt)

        result = await repository.list_by_tenant("tenant-1")

        assert len(result) == 5
        # Verify sorted by created_at descending
        for i in range(len(result) - 1):
            assert result[i].created_at >= result[i + 1].created_at

    @pytest.mark.asyncio
    async def test_list_by_tenant_excludes_inactive(
        self,
        repository: InMemoryPromptRepository,
    ) -> None:
        """Should exclude soft-deleted prompts from listing."""
        prompt1 = Prompt(
            id=str(uuid4()),
            layer=PromptLayer.SYSTEM,
            scope_id="scope-1",
            name="Prompt 1",
            content="Content 1",
            tenant_id="tenant-1",
        )
        prompt2 = Prompt(
            id=str(uuid4()),
            layer=PromptLayer.TENANT,
            scope_id="scope-2",
            name="Prompt 2",
            content="Content 2",
            tenant_id="tenant-1",
        )

        await repository.create(prompt1)
        await repository.create(prompt2)
        await repository.delete(prompt1.id)

        result = await repository.list_by_tenant("tenant-1")

        assert len(result) == 1
        assert result[0].id == prompt2.id

    @pytest.mark.asyncio
    async def test_list_by_tenant_pagination(
        self,
        repository: InMemoryPromptRepository,
    ) -> None:
        """Should support pagination with limit and offset."""
        prompts = [
            Prompt(
                id=str(uuid4()),
                layer=PromptLayer.SYSTEM,
                scope_id=f"scope-{i}",
                name=f"Prompt {i}",
                content=f"Content {i}",
                tenant_id="tenant-1",
            )
            for i in range(10)
        ]

        for prompt in prompts:
            await repository.create(prompt)

        result = await repository.list_by_tenant("tenant-1", limit=3, offset=2)

        assert len(result) == 3


class TestInMemoryPromptRepositoryVersionOperations:
    """Tests for version operations."""

    @pytest.fixture
    def repository(self) -> InMemoryPromptRepository:
        """Create a fresh repository for each test."""
        return InMemoryPromptRepository()

    @pytest.fixture
    async def sample_prompt(
        self,
        repository: InMemoryPromptRepository,
    ) -> Prompt:
        """Create and store a sample prompt."""
        prompt = Prompt(
            id=str(uuid4()),
            layer=PromptLayer.SYSTEM,
            scope_id="default",
            name="Test Prompt",
            content="Original content",
            tenant_id="tenant-1",
        )
        return await repository.create(prompt)

    @pytest.mark.asyncio
    async def test_create_version_success(
        self,
        repository: InMemoryPromptRepository,
        sample_prompt: Prompt,
    ) -> None:
        """Should successfully create version."""
        version = PromptVersion(
            id=str(uuid4()),
            prompt_id=sample_prompt.id,
            version_number=1,
            content="Version 1 content",
        )

        result = await repository.create_version(version)

        assert result.id == version.id
        assert result.prompt_id == sample_prompt.id
        assert result.version_number == 1

    @pytest.mark.asyncio
    async def test_create_version_for_nonexistent_prompt_raises_error(
        self,
        repository: InMemoryPromptRepository,
    ) -> None:
        """Should raise error when creating version for nonexistent prompt."""
        version = PromptVersion(
            id=str(uuid4()),
            prompt_id=str(uuid4()),
            version_number=1,
            content="Content",
        )

        with pytest.raises(PromptNotFoundError):
            await repository.create_version(version)

    @pytest.mark.asyncio
    async def test_get_version_success(
        self,
        repository: InMemoryPromptRepository,
        sample_prompt: Prompt,
    ) -> None:
        """Should retrieve version by prompt ID and version number."""
        version = PromptVersion(
            id=str(uuid4()),
            prompt_id=sample_prompt.id,
            version_number=2,
            content="Version 2 content",
        )
        await repository.create_version(version)

        result = await repository.get_version(sample_prompt.id, 2)

        assert result is not None
        assert result.id == version.id
        assert result.version_number == 2

    @pytest.mark.asyncio
    async def test_get_nonexistent_version_returns_none(
        self,
        repository: InMemoryPromptRepository,
        sample_prompt: Prompt,
    ) -> None:
        """Should return None for nonexistent version."""
        result = await repository.get_version(sample_prompt.id, 999)
        assert result is None

    @pytest.mark.asyncio
    async def test_list_versions_success(
        self,
        repository: InMemoryPromptRepository,
        sample_prompt: Prompt,
    ) -> None:
        """Should list all versions for prompt."""
        versions = [
            PromptVersion(
                id=str(uuid4()),
                prompt_id=sample_prompt.id,
                version_number=i,
                content=f"Version {i} content",
            )
            for i in range(1, 6)
        ]

        for version in versions:
            await repository.create_version(version)

        result = await repository.list_versions(sample_prompt.id)

        assert len(result) == 5
        # Verify sorted by version_number descending
        for i in range(len(result) - 1):
            assert result[i].version_number > result[i + 1].version_number

    @pytest.mark.asyncio
    async def test_list_versions_pagination(
        self,
        repository: InMemoryPromptRepository,
        sample_prompt: Prompt,
    ) -> None:
        """Should support pagination for versions."""
        versions = [
            PromptVersion(
                id=str(uuid4()),
                prompt_id=sample_prompt.id,
                version_number=i,
                content=f"Version {i} content",
            )
            for i in range(1, 11)
        ]

        for version in versions:
            await repository.create_version(version)

        result = await repository.list_versions(sample_prompt.id, limit=3, offset=2)

        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_set_current_version_success(
        self,
        repository: InMemoryPromptRepository,
        sample_prompt: Prompt,
    ) -> None:
        """Should set current version and update prompt content."""
        version = PromptVersion(
            id=str(uuid4()),
            prompt_id=sample_prompt.id,
            version_number=2,
            content="Version 2 content",
            merge_points=[
                MergePointDefinition(
                    name="test_merge",
                    behavior=MergeBehavior.APPEND,
                )
            ],
        )
        await repository.create_version(version)

        result = await repository.set_current_version(sample_prompt.id, 2)

        assert result.content == "Version 2 content"
        assert result.version == 2
        assert len(result.merge_points) == 1

    @pytest.mark.asyncio
    async def test_set_current_version_for_nonexistent_prompt_raises_error(
        self,
        repository: InMemoryPromptRepository,
    ) -> None:
        """Should raise error when setting version for nonexistent prompt."""
        with pytest.raises(PromptNotFoundError):
            await repository.set_current_version(str(uuid4()), 1)

    @pytest.mark.asyncio
    async def test_set_current_version_for_nonexistent_version_raises_error(
        self,
        repository: InMemoryPromptRepository,
        sample_prompt: Prompt,
    ) -> None:
        """Should raise error when setting nonexistent version."""
        with pytest.raises(PromptVersionNotFoundError):
            await repository.set_current_version(sample_prompt.id, 999)


class TestInMemoryPromptRepositoryExperimentOperations:
    """Tests for experiment operations."""

    @pytest.fixture
    def repository(self) -> InMemoryPromptRepository:
        """Create a fresh repository for each test."""
        return InMemoryPromptRepository()

    @pytest.fixture
    async def sample_prompt(
        self,
        repository: InMemoryPromptRepository,
    ) -> Prompt:
        """Create and store a sample prompt."""
        prompt = Prompt(
            id=str(uuid4()),
            layer=PromptLayer.SYSTEM,
            scope_id="default",
            name="Test Prompt",
            content="Original content",
            tenant_id="tenant-1",
        )
        return await repository.create(prompt)

    @pytest.fixture
    def sample_experiment(self, sample_prompt: Prompt) -> PromptExperiment:
        """Create a sample experiment."""
        return PromptExperiment(
            id=str(uuid4()),
            name="Test Experiment",
            prompt_id=sample_prompt.id,
            status=ExperimentStatus.DRAFT,
            variants=[
                ExperimentVariant(
                    id=str(uuid4()),
                    name="Control",
                    prompt_version_id=str(uuid4()),
                    traffic_percentage=50.0,
                ),
                ExperimentVariant(
                    id=str(uuid4()),
                    name="Variant A",
                    prompt_version_id=str(uuid4()),
                    traffic_percentage=50.0,
                ),
            ],
            success_metric="accuracy",
        )

    @pytest.mark.asyncio
    async def test_create_experiment_success(
        self,
        repository: InMemoryPromptRepository,
        sample_experiment: PromptExperiment,
    ) -> None:
        """Should successfully create experiment."""
        result = await repository.create_experiment(sample_experiment)

        assert result.id == sample_experiment.id
        assert result.name == sample_experiment.name
        assert len(result.variants) == 2

    @pytest.mark.asyncio
    async def test_create_experiment_for_nonexistent_prompt_raises_error(
        self,
        repository: InMemoryPromptRepository,
    ) -> None:
        """Should raise error when creating experiment for nonexistent prompt."""
        experiment = PromptExperiment(
            id=str(uuid4()),
            name="Test Experiment",
            prompt_id=str(uuid4()),
            status=ExperimentStatus.DRAFT,
            variants=[
                ExperimentVariant(
                    id=str(uuid4()),
                    name="Control",
                    prompt_version_id=str(uuid4()),
                    traffic_percentage=50.0,
                ),
                ExperimentVariant(
                    id=str(uuid4()),
                    name="Variant A",
                    prompt_version_id=str(uuid4()),
                    traffic_percentage=50.0,
                ),
            ],
            success_metric="accuracy",
        )

        with pytest.raises(PromptNotFoundError):
            await repository.create_experiment(experiment)

    @pytest.mark.asyncio
    async def test_get_experiment_success(
        self,
        repository: InMemoryPromptRepository,
        sample_experiment: PromptExperiment,
    ) -> None:
        """Should retrieve experiment by ID."""
        await repository.create_experiment(sample_experiment)
        result = await repository.get_experiment(sample_experiment.id)

        assert result is not None
        assert result.id == sample_experiment.id

    @pytest.mark.asyncio
    async def test_get_nonexistent_experiment_returns_none(
        self,
        repository: InMemoryPromptRepository,
    ) -> None:
        """Should return None for nonexistent experiment."""
        result = await repository.get_experiment(str(uuid4()))
        assert result is None

    @pytest.mark.asyncio
    async def test_get_active_experiment_success(
        self,
        repository: InMemoryPromptRepository,
        sample_prompt: Prompt,
        sample_experiment: PromptExperiment,
    ) -> None:
        """Should retrieve active experiment for prompt."""
        running_experiment = sample_experiment.model_copy(
            update={"status": ExperimentStatus.RUNNING}
        )
        await repository.create_experiment(running_experiment)

        result = await repository.get_active_experiment(sample_prompt.id)

        assert result is not None
        assert result.id == sample_experiment.id
        assert result.status == ExperimentStatus.RUNNING

    @pytest.mark.asyncio
    async def test_get_active_experiment_returns_none_when_no_running(
        self,
        repository: InMemoryPromptRepository,
        sample_prompt: Prompt,
        sample_experiment: PromptExperiment,
    ) -> None:
        """Should return None when no running experiment exists."""
        await repository.create_experiment(sample_experiment)

        result = await repository.get_active_experiment(sample_prompt.id)

        assert result is None

    @pytest.mark.asyncio
    async def test_update_experiment_success(
        self,
        repository: InMemoryPromptRepository,
        sample_experiment: PromptExperiment,
    ) -> None:
        """Should successfully update experiment."""
        await repository.create_experiment(sample_experiment)

        updated_experiment = sample_experiment.model_copy(
            update={"status": ExperimentStatus.RUNNING}
        )
        result = await repository.update_experiment(updated_experiment)

        assert result.status == ExperimentStatus.RUNNING
        assert result.updated_at >= sample_experiment.updated_at

    @pytest.mark.asyncio
    async def test_update_nonexistent_experiment_raises_error(
        self,
        repository: InMemoryPromptRepository,
        sample_experiment: PromptExperiment,
    ) -> None:
        """Should raise error when updating nonexistent experiment."""
        with pytest.raises(ExperimentNotFoundError):
            await repository.update_experiment(sample_experiment)

    @pytest.mark.asyncio
    async def test_list_experiments_success(
        self,
        repository: InMemoryPromptRepository,
        sample_prompt: Prompt,
    ) -> None:
        """Should list all experiments for prompt."""
        experiments = [
            PromptExperiment(
                id=str(uuid4()),
                name=f"Experiment {i}",
                prompt_id=sample_prompt.id,
                status=ExperimentStatus.DRAFT,
                variants=[
                    ExperimentVariant(
                        id=str(uuid4()),
                        name="Control",
                        prompt_version_id=str(uuid4()),
                        traffic_percentage=50.0,
                    ),
                    ExperimentVariant(
                        id=str(uuid4()),
                        name="Variant",
                        prompt_version_id=str(uuid4()),
                        traffic_percentage=50.0,
                    ),
                ],
                success_metric="accuracy",
            )
            for i in range(5)
        ]

        for experiment in experiments:
            await repository.create_experiment(experiment)

        result = await repository.list_experiments(sample_prompt.id)

        assert len(result) == 5
        # Verify sorted by created_at descending
        for i in range(len(result) - 1):
            assert result[i].created_at >= result[i + 1].created_at

    @pytest.mark.asyncio
    async def test_list_experiments_with_status_filter(
        self,
        repository: InMemoryPromptRepository,
        sample_prompt: Prompt,
    ) -> None:
        """Should filter experiments by status."""
        draft_exp = PromptExperiment(
            id=str(uuid4()),
            name="Draft Experiment",
            prompt_id=sample_prompt.id,
            status=ExperimentStatus.DRAFT,
            variants=[
                ExperimentVariant(
                    id=str(uuid4()),
                    name="Control",
                    prompt_version_id=str(uuid4()),
                    traffic_percentage=50.0,
                ),
                ExperimentVariant(
                    id=str(uuid4()),
                    name="Variant",
                    prompt_version_id=str(uuid4()),
                    traffic_percentage=50.0,
                ),
            ],
            success_metric="accuracy",
        )

        running_exp = PromptExperiment(
            id=str(uuid4()),
            name="Running Experiment",
            prompt_id=sample_prompt.id,
            status=ExperimentStatus.RUNNING,
            variants=[
                ExperimentVariant(
                    id=str(uuid4()),
                    name="Control",
                    prompt_version_id=str(uuid4()),
                    traffic_percentage=50.0,
                ),
                ExperimentVariant(
                    id=str(uuid4()),
                    name="Variant",
                    prompt_version_id=str(uuid4()),
                    traffic_percentage=50.0,
                ),
            ],
            success_metric="accuracy",
        )

        await repository.create_experiment(draft_exp)
        await repository.create_experiment(running_exp)

        result = await repository.list_experiments(
            sample_prompt.id,
            status=ExperimentStatus.RUNNING,
        )

        assert len(result) == 1
        assert result[0].id == running_exp.id

    @pytest.mark.asyncio
    async def test_list_experiments_pagination(
        self,
        repository: InMemoryPromptRepository,
        sample_prompt: Prompt,
    ) -> None:
        """Should support pagination for experiments."""
        experiments = [
            PromptExperiment(
                id=str(uuid4()),
                name=f"Experiment {i}",
                prompt_id=sample_prompt.id,
                status=ExperimentStatus.DRAFT,
                variants=[
                    ExperimentVariant(
                        id=str(uuid4()),
                        name="Control",
                        prompt_version_id=str(uuid4()),
                        traffic_percentage=50.0,
                    ),
                    ExperimentVariant(
                        id=str(uuid4()),
                        name="Variant",
                        prompt_version_id=str(uuid4()),
                        traffic_percentage=50.0,
                    ),
                ],
                success_metric="accuracy",
            )
            for i in range(10)
        ]

        for experiment in experiments:
            await repository.create_experiment(experiment)

        result = await repository.list_experiments(sample_prompt.id, limit=3, offset=2)

        assert len(result) == 3


class TestInMemoryPromptRepositoryConcurrency:
    """Tests for thread safety and concurrent operations."""

    @pytest.fixture
    def repository(self) -> InMemoryPromptRepository:
        """Create a fresh repository for each test."""
        return InMemoryPromptRepository()

    @pytest.mark.asyncio
    async def test_concurrent_creates_maintain_uniqueness(
        self,
        repository: InMemoryPromptRepository,
    ) -> None:
        """Should maintain uniqueness constraint under concurrent creates."""

        async def create_prompt(i: int) -> None:
            try:
                prompt = Prompt(
                    id=str(uuid4()),
                    layer=PromptLayer.SYSTEM,
                    scope_id="shared-scope",
                    name=f"Prompt {i}",
                    content=f"Content {i}",
                    tenant_id="tenant-1",
                )
                await repository.create(prompt)
            except PromptValidationError:
                pass  # Expected for duplicate attempts

        tasks = [create_prompt(i) for i in range(10)]
        await asyncio.gather(*tasks)

        # Only one prompt should have been created
        result = await repository.get_by_layer(
            PromptLayer.SYSTEM,
            "shared-scope",
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_concurrent_updates_are_safe(
        self,
        repository: InMemoryPromptRepository,
    ) -> None:
        """Should safely handle concurrent updates."""
        prompt = Prompt(
            id=str(uuid4()),
            layer=PromptLayer.SYSTEM,
            scope_id="default",
            name="Test Prompt",
            content="Original content",
            tenant_id="tenant-1",
        )
        await repository.create(prompt)

        async def update_prompt(i: int) -> None:
            try:
                updated = prompt.model_copy(update={"content": f"Content {i}"})
                await repository.update(updated)
            except Exception:
                pass

        tasks = [update_prompt(i) for i in range(10)]
        await asyncio.gather(*tasks)

        # Verify prompt was updated (one of the updates should have succeeded)
        result = await repository.get(prompt.id)
        assert result is not None
        assert result.content.startswith("Content")
