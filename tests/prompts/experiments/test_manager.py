"""Tests for experiment manager module."""

import pytest

from omniforge.prompts.enums import ExperimentStatus, PromptLayer
from omniforge.prompts.errors import (
    ExperimentNotFoundError,
    ExperimentStateError,
    PromptNotFoundError,
    PromptValidationError,
)
from omniforge.prompts.experiments.manager import ExperimentManager, VariantSelection
from omniforge.prompts.models import ExperimentVariant, Prompt, PromptVersion
from omniforge.prompts.storage.memory import InMemoryPromptRepository


class TestExperimentManager:
    """Tests for ExperimentManager class."""

    @pytest.fixture
    def repository(self) -> InMemoryPromptRepository:
        """Create an in-memory repository for testing."""
        return InMemoryPromptRepository()

    @pytest.fixture
    def manager(self, repository: InMemoryPromptRepository) -> ExperimentManager:
        """Create an experiment manager instance."""
        return ExperimentManager(repository)

    @pytest.fixture
    async def sample_prompt(self, repository: InMemoryPromptRepository) -> Prompt:
        """Create a sample prompt for testing."""
        prompt = Prompt(
            id="prompt-1",
            layer=PromptLayer.SYSTEM,
            scope_id="global",
            name="Test Prompt",
            content="You are a helpful assistant.",
            tenant_id="tenant-1",
        )
        return await repository.create(prompt)

    @pytest.mark.asyncio
    async def test_create_experiment(
        self,
        manager: ExperimentManager,
        sample_prompt: Prompt,
    ) -> None:
        """Should create a new experiment successfully."""
        variants = [
            ExperimentVariant(
                id="variant-a",
                name="Control",
                prompt_version_id="prompt-1-v1",
                traffic_percentage=50.0,
            ),
            ExperimentVariant(
                id="variant-b",
                name="Treatment",
                prompt_version_id="prompt-1-v2",
                traffic_percentage=50.0,
            ),
        ]

        experiment = await manager.create_experiment(
            prompt_id=sample_prompt.id,
            name="My First Experiment",
            description="Testing prompt variations",
            success_metric="conversion_rate",
            variants=variants,
            created_by="user-123",
        )

        assert experiment.name == "My First Experiment"
        assert experiment.description == "Testing prompt variations"
        assert experiment.prompt_id == sample_prompt.id
        assert experiment.status == ExperimentStatus.DRAFT
        assert len(experiment.variants) == 2
        assert experiment.success_metric == "conversion_rate"
        assert experiment.created_by == "user-123"

    @pytest.mark.asyncio
    async def test_create_experiment_prompt_not_found(self, manager: ExperimentManager) -> None:
        """Should raise error when prompt does not exist."""
        variants = [
            ExperimentVariant(
                id="variant-a",
                name="Control",
                prompt_version_id="prompt-1-v1",
                traffic_percentage=50.0,
            ),
            ExperimentVariant(
                id="variant-b",
                name="Treatment",
                prompt_version_id="prompt-1-v2",
                traffic_percentage=50.0,
            ),
        ]

        with pytest.raises(PromptNotFoundError):
            await manager.create_experiment(
                prompt_id="nonexistent",
                name="Test",
                description="Test",
                success_metric="conversion_rate",
                variants=variants,
            )

    @pytest.mark.asyncio
    async def test_create_experiment_insufficient_variants(
        self,
        manager: ExperimentManager,
        sample_prompt: Prompt,
    ) -> None:
        """Should raise error when fewer than 2 variants."""
        variants = [
            ExperimentVariant(
                id="variant-a",
                name="Control",
                prompt_version_id="prompt-1-v1",
                traffic_percentage=100.0,
            ),
        ]

        with pytest.raises(PromptValidationError, match="at least 2 variants"):
            await manager.create_experiment(
                prompt_id=sample_prompt.id,
                name="Test",
                description="Test",
                success_metric="conversion_rate",
                variants=variants,
            )

    @pytest.mark.asyncio
    async def test_create_experiment_invalid_traffic_allocation(
        self,
        manager: ExperimentManager,
        sample_prompt: Prompt,
    ) -> None:
        """Should raise error when traffic doesn't sum to 100%."""
        variants = [
            ExperimentVariant(
                id="variant-a",
                name="Control",
                prompt_version_id="prompt-1-v1",
                traffic_percentage=40.0,
            ),
            ExperimentVariant(
                id="variant-b",
                name="Treatment",
                prompt_version_id="prompt-1-v2",
                traffic_percentage=50.0,
            ),
        ]

        with pytest.raises(PromptValidationError, match="sum to 100%"):
            await manager.create_experiment(
                prompt_id=sample_prompt.id,
                name="Test",
                description="Test",
                success_metric="conversion_rate",
                variants=variants,
            )

    @pytest.mark.asyncio
    async def test_start_experiment(
        self,
        manager: ExperimentManager,
        sample_prompt: Prompt,
    ) -> None:
        """Should start a DRAFT experiment."""
        variants = [
            ExperimentVariant(
                id="variant-a",
                name="Control",
                prompt_version_id="prompt-1-v1",
                traffic_percentage=50.0,
            ),
            ExperimentVariant(
                id="variant-b",
                name="Treatment",
                prompt_version_id="prompt-1-v2",
                traffic_percentage=50.0,
            ),
        ]

        experiment = await manager.create_experiment(
            prompt_id=sample_prompt.id,
            name="Test",
            description="Test",
            success_metric="conversion_rate",
            variants=variants,
        )

        started_experiment = await manager.start_experiment(experiment.id)

        assert started_experiment.status == ExperimentStatus.RUNNING
        assert started_experiment.start_time is not None

    @pytest.mark.asyncio
    async def test_start_experiment_not_found(self, manager: ExperimentManager) -> None:
        """Should raise error when experiment does not exist."""
        with pytest.raises(ExperimentNotFoundError):
            await manager.start_experiment("nonexistent")

    @pytest.mark.asyncio
    async def test_start_experiment_invalid_state(
        self,
        manager: ExperimentManager,
        sample_prompt: Prompt,
    ) -> None:
        """Should raise error when experiment is not in DRAFT or PAUSED state."""
        variants = [
            ExperimentVariant(
                id="variant-a",
                name="Control",
                prompt_version_id="prompt-1-v1",
                traffic_percentage=50.0,
            ),
            ExperimentVariant(
                id="variant-b",
                name="Treatment",
                prompt_version_id="prompt-1-v2",
                traffic_percentage=50.0,
            ),
        ]

        experiment = await manager.create_experiment(
            prompt_id=sample_prompt.id,
            name="Test",
            description="Test",
            success_metric="conversion_rate",
            variants=variants,
        )

        # Start and complete the experiment
        await manager.start_experiment(experiment.id)
        await manager.complete_experiment(experiment.id, {})

        # Try to start again
        with pytest.raises(ExperimentStateError):
            await manager.start_experiment(experiment.id)

    @pytest.mark.asyncio
    async def test_pause_experiment(
        self,
        manager: ExperimentManager,
        sample_prompt: Prompt,
    ) -> None:
        """Should pause a RUNNING experiment."""
        variants = [
            ExperimentVariant(
                id="variant-a",
                name="Control",
                prompt_version_id="prompt-1-v1",
                traffic_percentage=50.0,
            ),
            ExperimentVariant(
                id="variant-b",
                name="Treatment",
                prompt_version_id="prompt-1-v2",
                traffic_percentage=50.0,
            ),
        ]

        experiment = await manager.create_experiment(
            prompt_id=sample_prompt.id,
            name="Test",
            description="Test",
            success_metric="conversion_rate",
            variants=variants,
        )

        await manager.start_experiment(experiment.id)
        paused_experiment = await manager.pause_experiment(experiment.id)

        assert paused_experiment.status == ExperimentStatus.PAUSED

    @pytest.mark.asyncio
    async def test_pause_experiment_invalid_state(
        self,
        manager: ExperimentManager,
        sample_prompt: Prompt,
    ) -> None:
        """Should raise error when experiment is not RUNNING."""
        variants = [
            ExperimentVariant(
                id="variant-a",
                name="Control",
                prompt_version_id="prompt-1-v1",
                traffic_percentage=50.0,
            ),
            ExperimentVariant(
                id="variant-b",
                name="Treatment",
                prompt_version_id="prompt-1-v2",
                traffic_percentage=50.0,
            ),
        ]

        experiment = await manager.create_experiment(
            prompt_id=sample_prompt.id,
            name="Test",
            description="Test",
            success_metric="conversion_rate",
            variants=variants,
        )

        # Try to pause a DRAFT experiment
        with pytest.raises(ExperimentStateError):
            await manager.pause_experiment(experiment.id)

    @pytest.mark.asyncio
    async def test_complete_experiment(
        self,
        manager: ExperimentManager,
        sample_prompt: Prompt,
    ) -> None:
        """Should complete an experiment and store results."""
        variants = [
            ExperimentVariant(
                id="variant-a",
                name="Control",
                prompt_version_id="prompt-1-v1",
                traffic_percentage=50.0,
            ),
            ExperimentVariant(
                id="variant-b",
                name="Treatment",
                prompt_version_id="prompt-1-v2",
                traffic_percentage=50.0,
            ),
        ]

        experiment = await manager.create_experiment(
            prompt_id=sample_prompt.id,
            name="Test",
            description="Test",
            success_metric="conversion_rate",
            variants=variants,
        )

        results = {"variant-a": 0.42, "variant-b": 0.58}
        completed_experiment = await manager.complete_experiment(experiment.id, results)

        assert completed_experiment.status == ExperimentStatus.COMPLETED
        assert completed_experiment.end_time is not None

    @pytest.mark.asyncio
    async def test_cancel_experiment(
        self,
        manager: ExperimentManager,
        sample_prompt: Prompt,
    ) -> None:
        """Should cancel an experiment."""
        variants = [
            ExperimentVariant(
                id="variant-a",
                name="Control",
                prompt_version_id="prompt-1-v1",
                traffic_percentage=50.0,
            ),
            ExperimentVariant(
                id="variant-b",
                name="Treatment",
                prompt_version_id="prompt-1-v2",
                traffic_percentage=50.0,
            ),
        ]

        experiment = await manager.create_experiment(
            prompt_id=sample_prompt.id,
            name="Test",
            description="Test",
            success_metric="conversion_rate",
            variants=variants,
        )

        cancelled_experiment = await manager.cancel_experiment(experiment.id)

        assert cancelled_experiment.status == ExperimentStatus.CANCELLED
        assert cancelled_experiment.end_time is not None

    @pytest.mark.asyncio
    async def test_select_variant_with_active_experiment(
        self,
        manager: ExperimentManager,
        sample_prompt: Prompt,
    ) -> None:
        """Should select a variant when experiment is running."""
        variants = [
            ExperimentVariant(
                id="variant-a",
                name="Control",
                prompt_version_id="prompt-1-v1",
                traffic_percentage=50.0,
            ),
            ExperimentVariant(
                id="variant-b",
                name="Treatment",
                prompt_version_id="prompt-1-v2",
                traffic_percentage=50.0,
            ),
        ]

        experiment = await manager.create_experiment(
            prompt_id=sample_prompt.id,
            name="Test",
            description="Test",
            success_metric="conversion_rate",
            variants=variants,
        )

        await manager.start_experiment(experiment.id)

        selection = await manager.select_variant(sample_prompt.id, "tenant-123")

        assert selection is not None
        assert isinstance(selection, VariantSelection)
        assert selection.experiment_id == experiment.id
        assert selection.variant_id in ["variant-a", "variant-b"]
        assert selection.prompt_version_id in ["prompt-1-v1", "prompt-1-v2"]

    @pytest.mark.asyncio
    async def test_select_variant_deterministic(
        self,
        manager: ExperimentManager,
        sample_prompt: Prompt,
    ) -> None:
        """Should select same variant for same tenant consistently."""
        variants = [
            ExperimentVariant(
                id="variant-a",
                name="Control",
                prompt_version_id="prompt-1-v1",
                traffic_percentage=50.0,
            ),
            ExperimentVariant(
                id="variant-b",
                name="Treatment",
                prompt_version_id="prompt-1-v2",
                traffic_percentage=50.0,
            ),
        ]

        experiment = await manager.create_experiment(
            prompt_id=sample_prompt.id,
            name="Test",
            description="Test",
            success_metric="conversion_rate",
            variants=variants,
        )

        await manager.start_experiment(experiment.id)

        tenant_id = "tenant-123"
        selection1 = await manager.select_variant(sample_prompt.id, tenant_id)
        selection2 = await manager.select_variant(sample_prompt.id, tenant_id)
        selection3 = await manager.select_variant(sample_prompt.id, tenant_id)

        assert selection1 is not None
        assert selection2 is not None
        assert selection3 is not None
        assert selection1.variant_id == selection2.variant_id
        assert selection2.variant_id == selection3.variant_id

    @pytest.mark.asyncio
    async def test_select_variant_no_active_experiment(
        self,
        manager: ExperimentManager,
        sample_prompt: Prompt,
    ) -> None:
        """Should return None when no active experiment exists."""
        selection = await manager.select_variant(sample_prompt.id, "tenant-123")
        assert selection is None

    @pytest.mark.asyncio
    async def test_promote_variant(
        self,
        manager: ExperimentManager,
        repository: InMemoryPromptRepository,
        sample_prompt: Prompt,
    ) -> None:
        """Should promote a variant's version as current."""
        # Create versions first
        version1 = PromptVersion(
            id="prompt-1-v1",
            prompt_id=sample_prompt.id,
            version_number=1,
            content="Version 1 content",
        )
        version2 = PromptVersion(
            id="prompt-1-v2",
            prompt_id=sample_prompt.id,
            version_number=2,
            content="Version 2 content",
        )

        await repository.create_version(version1)
        await repository.create_version(version2)

        variants = [
            ExperimentVariant(
                id="variant-a",
                name="Control",
                prompt_version_id="prompt-1-v1",
                traffic_percentage=50.0,
            ),
            ExperimentVariant(
                id="variant-b",
                name="Treatment",
                prompt_version_id="prompt-1-v2",
                traffic_percentage=50.0,
            ),
        ]

        experiment = await manager.create_experiment(
            prompt_id=sample_prompt.id,
            name="Test",
            description="Test",
            success_metric="conversion_rate",
            variants=variants,
        )

        # Promote variant-b
        promoted_prompt = await manager.promote_variant(experiment.id, "variant-b", "user-123")

        assert promoted_prompt.version == 2
        assert promoted_prompt.content == "Version 2 content"

        # Experiment should be completed
        completed_experiment = await repository.get_experiment(experiment.id)
        assert completed_experiment is not None
        assert completed_experiment.status == ExperimentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_promote_variant_not_found(
        self,
        manager: ExperimentManager,
        sample_prompt: Prompt,
    ) -> None:
        """Should raise error when variant does not exist."""
        variants = [
            ExperimentVariant(
                id="variant-a",
                name="Control",
                prompt_version_id="prompt-1-v1",
                traffic_percentage=50.0,
            ),
            ExperimentVariant(
                id="variant-b",
                name="Treatment",
                prompt_version_id="prompt-1-v2",
                traffic_percentage=50.0,
            ),
        ]

        experiment = await manager.create_experiment(
            prompt_id=sample_prompt.id,
            name="Test",
            description="Test",
            success_metric="conversion_rate",
            variants=variants,
        )

        with pytest.raises(PromptValidationError, match="not found in experiment"):
            await manager.promote_variant(experiment.id, "nonexistent", "user-123")
