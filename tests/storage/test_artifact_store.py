"""Tests for InMemoryArtifactRepository."""

import pytest

from omniforge.agents.models import Artifact, ArtifactType
from omniforge.storage.memory import InMemoryArtifactRepository


def make_artifact(
    tenant_id: str = "tenant-a",
    artifact_id: str | None = None,
    title: str = "Test Artifact",
    inline_content: str = "content",
) -> Artifact:
    """Create a minimal valid Artifact for testing."""
    return Artifact(
        id=artifact_id,
        type=ArtifactType.DOCUMENT,
        title=title,
        inline_content=inline_content,
        tenant_id=tenant_id,
    )


class TestInMemoryArtifactRepositoryStore:
    """Tests for store() method."""

    @pytest.fixture
    def repo(self) -> InMemoryArtifactRepository:
        return InMemoryArtifactRepository()

    @pytest.mark.asyncio
    async def test_store_generates_uuid_when_id_is_none(
        self, repo: InMemoryArtifactRepository
    ) -> None:
        """store() should generate a non-empty UUID when artifact.id is None."""
        artifact = make_artifact(artifact_id=None)
        returned_id = await repo.store(artifact)

        assert returned_id
        assert len(returned_id) > 0

    @pytest.mark.asyncio
    async def test_store_uses_existing_id(self, repo: InMemoryArtifactRepository) -> None:
        """store() should use the artifact's existing ID when set."""
        artifact = make_artifact(artifact_id="my-fixed-id")
        returned_id = await repo.store(artifact)

        assert returned_id == "my-fixed-id"

    @pytest.mark.asyncio
    async def test_store_sets_id_on_stored_copy(self, repo: InMemoryArtifactRepository) -> None:
        """store() should persist the artifact with the returned ID set."""
        artifact = make_artifact(artifact_id=None)
        returned_id = await repo.store(artifact)

        fetched = await repo.fetch(returned_id, artifact.tenant_id)
        assert fetched is not None
        assert fetched.id == returned_id

    @pytest.mark.asyncio
    async def test_store_upserts_on_duplicate_id(self, repo: InMemoryArtifactRepository) -> None:
        """store() should overwrite an existing artifact with same ID and tenant."""
        artifact_v1 = make_artifact(artifact_id="dup-id", title="Version 1")
        await repo.store(artifact_v1)

        artifact_v2 = make_artifact(artifact_id="dup-id", title="Version 2")
        await repo.store(artifact_v2)

        fetched = await repo.fetch("dup-id", "tenant-a")
        assert fetched is not None
        assert fetched.title == "Version 2"

    @pytest.mark.asyncio
    async def test_store_returns_different_ids_for_different_artifacts(
        self, repo: InMemoryArtifactRepository
    ) -> None:
        """store() should return distinct UUIDs for each artifact without an ID."""
        id1 = await repo.store(make_artifact(artifact_id=None))
        id2 = await repo.store(make_artifact(artifact_id=None))

        assert id1 != id2


class TestInMemoryArtifactRepositoryFetch:
    """Tests for fetch() method."""

    @pytest.fixture
    def repo(self) -> InMemoryArtifactRepository:
        return InMemoryArtifactRepository()

    @pytest.mark.asyncio
    async def test_fetch_returns_stored_artifact(self, repo: InMemoryArtifactRepository) -> None:
        """fetch() should return the artifact that was previously stored."""
        artifact = make_artifact(artifact_id="fetch-me", tenant_id="tenant-a")
        await repo.store(artifact)

        fetched = await repo.fetch("fetch-me", "tenant-a")
        assert fetched is not None
        assert fetched.id == "fetch-me"
        assert fetched.tenant_id == "tenant-a"

    @pytest.mark.asyncio
    async def test_fetch_returns_none_for_missing_id(
        self, repo: InMemoryArtifactRepository
    ) -> None:
        """fetch() should return None when the artifact ID does not exist."""
        result = await repo.fetch("nonexistent", "tenant-a")
        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_returns_none_for_wrong_tenant(
        self, repo: InMemoryArtifactRepository
    ) -> None:
        """fetch() must return None when the artifact exists but belongs to a different tenant.

        This is the critical tenant isolation check — cross-tenant access must be
        indistinguishable from not-found to prevent information leakage.
        """
        artifact = make_artifact(artifact_id="secret-id", tenant_id="tenant-a")
        await repo.store(artifact)

        result = await repo.fetch("secret-id", "tenant-b")
        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_returns_deep_copy(self, repo: InMemoryArtifactRepository) -> None:
        """fetch() should return a deep copy — mutating it must not affect stored state."""
        artifact = make_artifact(artifact_id="copy-test", inline_content="original")
        await repo.store(artifact)

        fetched = await repo.fetch("copy-test", "tenant-a")
        assert fetched is not None

        # Mutate the returned copy
        fetched.inline_content = "mutated"

        # Stored state must be unchanged
        fetched_again = await repo.fetch("copy-test", "tenant-a")
        assert fetched_again is not None
        assert fetched_again.inline_content == "original"


class TestInMemoryArtifactRepositoryDelete:
    """Tests for delete() method."""

    @pytest.fixture
    def repo(self) -> InMemoryArtifactRepository:
        return InMemoryArtifactRepository()

    @pytest.mark.asyncio
    async def test_delete_removes_artifact(self, repo: InMemoryArtifactRepository) -> None:
        """delete() should remove the artifact so subsequent fetch returns None."""
        artifact = make_artifact(artifact_id="delete-me", tenant_id="tenant-a")
        await repo.store(artifact)

        await repo.delete("delete-me", "tenant-a")

        result = await repo.fetch("delete-me", "tenant-a")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_raises_for_missing_id(self, repo: InMemoryArtifactRepository) -> None:
        """delete() should raise ValueError when the artifact ID does not exist."""
        with pytest.raises(ValueError, match="nonexistent"):
            await repo.delete("nonexistent", "tenant-a")

    @pytest.mark.asyncio
    async def test_delete_raises_for_wrong_tenant(self, repo: InMemoryArtifactRepository) -> None:
        """delete() should raise ValueError when the artifact belongs to a different tenant."""
        artifact = make_artifact(artifact_id="owned-by-a", tenant_id="tenant-a")
        await repo.store(artifact)

        with pytest.raises(ValueError, match="owned-by-a"):
            await repo.delete("owned-by-a", "tenant-b")

        # The artifact must still exist in the correct tenant
        still_there = await repo.fetch("owned-by-a", "tenant-a")
        assert still_there is not None


class TestInMemoryArtifactRepositoryTenantIsolation:
    """Cross-cutting tenant isolation tests."""

    @pytest.fixture
    def repo(self) -> InMemoryArtifactRepository:
        return InMemoryArtifactRepository()

    @pytest.mark.asyncio
    async def test_two_tenants_same_id_no_collision(self, repo: InMemoryArtifactRepository) -> None:
        """Two tenants can store artifacts with the same ID without overwriting each other."""
        artifact_a = make_artifact(artifact_id="shared-id", tenant_id="tenant-a", title="Tenant A")
        artifact_b = make_artifact(artifact_id="shared-id", tenant_id="tenant-b", title="Tenant B")

        await repo.store(artifact_a)
        await repo.store(artifact_b)

        fetched_a = await repo.fetch("shared-id", "tenant-a")
        fetched_b = await repo.fetch("shared-id", "tenant-b")

        assert fetched_a is not None
        assert fetched_b is not None
        assert fetched_a.title == "Tenant A"
        assert fetched_b.title == "Tenant B"

    @pytest.mark.asyncio
    async def test_delete_one_tenant_does_not_affect_other(
        self, repo: InMemoryArtifactRepository
    ) -> None:
        """Deleting an artifact for one tenant must not affect the other tenant's artifact."""
        await repo.store(make_artifact(artifact_id="shared-id", tenant_id="tenant-a"))
        await repo.store(make_artifact(artifact_id="shared-id", tenant_id="tenant-b"))

        await repo.delete("shared-id", "tenant-a")

        assert await repo.fetch("shared-id", "tenant-a") is None
        assert await repo.fetch("shared-id", "tenant-b") is not None
