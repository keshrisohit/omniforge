"""Tests for artifact storage tools.

Tests StoreArtifactTool, FetchArtifactTool, and register_artifact_tools.
Covers: definition checks, store/fetch roundtrip, tenant isolation,
input validation, and integration with MasterAgent.
"""

import json

import pytest

# Import agents.models FIRST to resolve circular import chain before storage.memory
from omniforge.agents.models import ArtifactType  # noqa: F401
from omniforge.storage.memory import InMemoryArtifactRepository
from omniforge.tools.base import ToolCallContext
from omniforge.tools.builtin.artifact import (
    FetchArtifactTool,
    StoreArtifactTool,
    register_artifact_tools,
)
from omniforge.tools.registry import ToolRegistry
from omniforge.tools.types import ToolType

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def store() -> InMemoryArtifactRepository:
    return InMemoryArtifactRepository()


@pytest.fixture
def ctx() -> ToolCallContext:
    return ToolCallContext(
        correlation_id="corr-1",
        task_id="task-1",
        agent_id="master-agent",
        tenant_id="tenant-abc",
    )


@pytest.fixture
def ctx_no_tenant() -> ToolCallContext:
    return ToolCallContext(
        correlation_id="corr-2",
        task_id="task-2",
        agent_id="master-agent",
        tenant_id=None,
    )


@pytest.fixture
def other_tenant_ctx() -> ToolCallContext:
    return ToolCallContext(
        correlation_id="corr-3",
        task_id="task-3",
        agent_id="other-agent",
        tenant_id="tenant-xyz",
    )


# ---------------------------------------------------------------------------
# StoreArtifactTool — definition checks
# ---------------------------------------------------------------------------


class TestStoreArtifactToolDefinition:
    """Tests that StoreArtifactTool definition is correctly configured."""

    def test_name(self, store: InMemoryArtifactRepository) -> None:
        tool = StoreArtifactTool(store)
        assert tool.definition.name == "store_artifact"

    def test_type(self, store: InMemoryArtifactRepository) -> None:
        tool = StoreArtifactTool(store)
        assert tool.definition.type == ToolType.FUNCTION

    def test_description_non_empty(self, store: InMemoryArtifactRepository) -> None:
        tool = StoreArtifactTool(store)
        assert len(tool.definition.description) > 10

    def test_required_params_present(self, store: InMemoryArtifactRepository) -> None:
        tool = StoreArtifactTool(store)
        param_names = [p.name for p in tool.definition.parameters]
        assert "type" in param_names
        assert "title" in param_names
        assert "content" in param_names

    def test_optional_params_present(self, store: InMemoryArtifactRepository) -> None:
        tool = StoreArtifactTool(store)
        param_names = [p.name for p in tool.definition.parameters]
        assert "metadata" in param_names
        assert "mime_type" in param_names

    def test_required_flags(self, store: InMemoryArtifactRepository) -> None:
        tool = StoreArtifactTool(store)
        required = {p.name for p in tool.definition.parameters if p.required}
        assert required == {"type", "title", "content"}

    def test_optional_flags(self, store: InMemoryArtifactRepository) -> None:
        tool = StoreArtifactTool(store)
        optional = {p.name for p in tool.definition.parameters if not p.required}
        assert "metadata" in optional
        assert "mime_type" in optional


# ---------------------------------------------------------------------------
# StoreArtifactTool — successful stores
# ---------------------------------------------------------------------------


class TestStoreArtifactToolExecution:
    """Execution tests for StoreArtifactTool."""

    @pytest.mark.asyncio
    async def test_store_string_content(
        self, store: InMemoryArtifactRepository, ctx: ToolCallContext
    ) -> None:
        tool = StoreArtifactTool(store)
        result = await tool.execute(
            ctx,
            {"type": "document", "title": "My Report", "content": "Hello world"},
        )
        assert result.success is True
        assert "artifact_id" in result.result
        assert result.result["artifact_id"]

    @pytest.mark.asyncio
    async def test_store_dict_content_as_json_string(
        self, store: InMemoryArtifactRepository, ctx: ToolCallContext
    ) -> None:
        tool = StoreArtifactTool(store)
        payload = json.dumps({"key": "value", "count": 42})
        result = await tool.execute(
            ctx,
            {"type": "structured", "title": "Config", "content": payload},
        )
        assert result.success is True
        assert result.result["type"] == "structured"

    @pytest.mark.asyncio
    async def test_store_list_content_as_json_string(
        self, store: InMemoryArtifactRepository, ctx: ToolCallContext
    ) -> None:
        tool = StoreArtifactTool(store)
        payload = json.dumps([1, 2, 3])
        result = await tool.execute(
            ctx,
            {"type": "dataset", "title": "Numbers", "content": payload},
        )
        assert result.success is True

    @pytest.mark.asyncio
    async def test_store_code_type(
        self, store: InMemoryArtifactRepository, ctx: ToolCallContext
    ) -> None:
        tool = StoreArtifactTool(store)
        result = await tool.execute(
            ctx,
            {"type": "code", "title": "Script", "content": "print('hello')"},
        )
        assert result.success is True
        assert result.result["type"] == "code"

    @pytest.mark.asyncio
    async def test_store_uses_context_tenant_id(
        self, store: InMemoryArtifactRepository, ctx: ToolCallContext
    ) -> None:
        tool = StoreArtifactTool(store)
        result = await tool.execute(
            ctx,
            {"type": "document", "title": "Test", "content": "data"},
        )
        assert result.success is True
        artifact_id = result.result["artifact_id"]
        # Verify stored under correct tenant
        artifact = await store.fetch(artifact_id, "tenant-abc")
        assert artifact is not None
        assert artifact.tenant_id == "tenant-abc"

    @pytest.mark.asyncio
    async def test_store_sets_created_by_agent_id(
        self, store: InMemoryArtifactRepository, ctx: ToolCallContext
    ) -> None:
        tool = StoreArtifactTool(store)
        result = await tool.execute(
            ctx,
            {"type": "document", "title": "Test", "content": "data"},
        )
        assert result.success is True
        artifact_id = result.result["artifact_id"]
        artifact = await store.fetch(artifact_id, "tenant-abc")
        assert artifact is not None
        assert artifact.created_by_agent_id == "master-agent"

    @pytest.mark.asyncio
    async def test_store_with_metadata(
        self, store: InMemoryArtifactRepository, ctx: ToolCallContext
    ) -> None:
        tool = StoreArtifactTool(store)
        metadata = json.dumps({"source": "skill-x", "version": 1})
        result = await tool.execute(
            ctx,
            {
                "type": "document",
                "title": "With Meta",
                "content": "content",
                "metadata": metadata,
            },
        )
        assert result.success is True

    @pytest.mark.asyncio
    async def test_store_with_mime_type(
        self, store: InMemoryArtifactRepository, ctx: ToolCallContext
    ) -> None:
        tool = StoreArtifactTool(store)
        result = await tool.execute(
            ctx,
            {
                "type": "document",
                "title": "JSON Doc",
                "content": "{}",
                "mime_type": "application/json",
            },
        )
        assert result.success is True

    @pytest.mark.asyncio
    async def test_result_contains_title(
        self, store: InMemoryArtifactRepository, ctx: ToolCallContext
    ) -> None:
        tool = StoreArtifactTool(store)
        result = await tool.execute(
            ctx,
            {"type": "document", "title": "My Doc", "content": "data"},
        )
        assert result.success is True
        assert result.result["title"] == "My Doc"


# ---------------------------------------------------------------------------
# StoreArtifactTool — validation errors
# ---------------------------------------------------------------------------


class TestStoreArtifactToolValidation:
    """Input validation tests for StoreArtifactTool."""

    @pytest.mark.asyncio
    async def test_missing_tenant_id(
        self, store: InMemoryArtifactRepository, ctx_no_tenant: ToolCallContext
    ) -> None:
        tool = StoreArtifactTool(store)
        result = await tool.execute(
            ctx_no_tenant,
            {"type": "document", "title": "Test", "content": "data"},
        )
        assert result.success is False
        assert "tenant_id" in result.error.lower()

    @pytest.mark.asyncio
    async def test_invalid_artifact_type(
        self, store: InMemoryArtifactRepository, ctx: ToolCallContext
    ) -> None:
        tool = StoreArtifactTool(store)
        result = await tool.execute(
            ctx,
            {"type": "invalid_type", "title": "Test", "content": "data"},
        )
        assert result.success is False
        assert "invalid" in result.error.lower() or "type" in result.error.lower()

    @pytest.mark.asyncio
    async def test_empty_title(
        self, store: InMemoryArtifactRepository, ctx: ToolCallContext
    ) -> None:
        tool = StoreArtifactTool(store)
        result = await tool.execute(
            ctx,
            {"type": "document", "title": "", "content": "data"},
        )
        assert result.success is False
        assert "title" in result.error.lower()

    @pytest.mark.asyncio
    async def test_missing_content(
        self, store: InMemoryArtifactRepository, ctx: ToolCallContext
    ) -> None:
        tool = StoreArtifactTool(store)
        result = await tool.execute(
            ctx,
            {"type": "document", "title": "Test"},
        )
        assert result.success is False
        assert "content" in result.error.lower()

    @pytest.mark.asyncio
    async def test_title_too_long(
        self, store: InMemoryArtifactRepository, ctx: ToolCallContext
    ) -> None:
        tool = StoreArtifactTool(store)
        result = await tool.execute(
            ctx,
            {"type": "document", "title": "x" * 501, "content": "data"},
        )
        assert result.success is False
        assert "500" in result.error or "title" in result.error.lower()

    @pytest.mark.asyncio
    async def test_invalid_metadata_json(
        self, store: InMemoryArtifactRepository, ctx: ToolCallContext
    ) -> None:
        tool = StoreArtifactTool(store)
        result = await tool.execute(
            ctx,
            {"type": "document", "title": "Test", "content": "data", "metadata": "not-json"},
        )
        assert result.success is False
        assert "metadata" in result.error.lower()

    @pytest.mark.asyncio
    async def test_metadata_as_array_rejected(
        self, store: InMemoryArtifactRepository, ctx: ToolCallContext
    ) -> None:
        tool = StoreArtifactTool(store)
        result = await tool.execute(
            ctx,
            {
                "type": "document",
                "title": "Test",
                "content": "data",
                "metadata": json.dumps([1, 2, 3]),
            },
        )
        assert result.success is False
        assert "metadata" in result.error.lower()


# ---------------------------------------------------------------------------
# FetchArtifactTool — definition checks
# ---------------------------------------------------------------------------


class TestFetchArtifactToolDefinition:
    """Tests that FetchArtifactTool definition is correctly configured."""

    def test_name(self, store: InMemoryArtifactRepository) -> None:
        tool = FetchArtifactTool(store)
        assert tool.definition.name == "fetch_artifact"

    def test_type(self, store: InMemoryArtifactRepository) -> None:
        tool = FetchArtifactTool(store)
        assert tool.definition.type == ToolType.FUNCTION

    def test_has_artifact_id_param(self, store: InMemoryArtifactRepository) -> None:
        tool = FetchArtifactTool(store)
        param_names = [p.name for p in tool.definition.parameters]
        assert "artifact_id" in param_names

    def test_artifact_id_is_required(self, store: InMemoryArtifactRepository) -> None:
        tool = FetchArtifactTool(store)
        required = {p.name for p in tool.definition.parameters if p.required}
        assert "artifact_id" in required


# ---------------------------------------------------------------------------
# FetchArtifactTool — execution
# ---------------------------------------------------------------------------


class TestFetchArtifactToolExecution:
    """Execution tests for FetchArtifactTool."""

    @pytest.mark.asyncio
    async def test_fetch_stored_artifact(
        self, store: InMemoryArtifactRepository, ctx: ToolCallContext
    ) -> None:
        store_tool = StoreArtifactTool(store)
        fetch_tool = FetchArtifactTool(store)

        store_result = await store_tool.execute(
            ctx,
            {"type": "document", "title": "My Doc", "content": "Hello"},
        )
        assert store_result.success is True
        artifact_id = store_result.result["artifact_id"]

        fetch_result = await fetch_tool.execute(ctx, {"artifact_id": artifact_id})
        assert fetch_result.success is True
        assert fetch_result.result["artifact_id"] == artifact_id
        assert fetch_result.result["title"] == "My Doc"
        assert fetch_result.result["type"] == "document"

    @pytest.mark.asyncio
    async def test_fetch_returns_content(
        self, store: InMemoryArtifactRepository, ctx: ToolCallContext
    ) -> None:
        store_tool = StoreArtifactTool(store)
        fetch_tool = FetchArtifactTool(store)

        store_result = await store_tool.execute(
            ctx,
            {"type": "document", "title": "Test", "content": "my content"},
        )
        artifact_id = store_result.result["artifact_id"]

        fetch_result = await fetch_tool.execute(ctx, {"artifact_id": artifact_id})
        assert fetch_result.success is True
        assert fetch_result.result["content"] == "my content"

    @pytest.mark.asyncio
    async def test_fetch_cross_tenant_returns_not_found(
        self,
        store: InMemoryArtifactRepository,
        ctx: ToolCallContext,
        other_tenant_ctx: ToolCallContext,
    ) -> None:
        store_tool = StoreArtifactTool(store)
        fetch_tool = FetchArtifactTool(store)

        store_result = await store_tool.execute(
            ctx,
            {"type": "document", "title": "Secret", "content": "sensitive"},
        )
        artifact_id = store_result.result["artifact_id"]

        # Attempt fetch from a different tenant
        fetch_result = await fetch_tool.execute(other_tenant_ctx, {"artifact_id": artifact_id})
        assert fetch_result.success is False
        assert "not found" in fetch_result.error.lower()

    @pytest.mark.asyncio
    async def test_fetch_nonexistent_returns_error(
        self, store: InMemoryArtifactRepository, ctx: ToolCallContext
    ) -> None:
        tool = FetchArtifactTool(store)
        result = await tool.execute(ctx, {"artifact_id": "does-not-exist"})
        assert result.success is False
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_fetch_missing_artifact_id(
        self, store: InMemoryArtifactRepository, ctx: ToolCallContext
    ) -> None:
        tool = FetchArtifactTool(store)
        result = await tool.execute(ctx, {})
        assert result.success is False
        assert "artifact_id" in result.error.lower()

    @pytest.mark.asyncio
    async def test_fetch_missing_tenant_id(
        self, store: InMemoryArtifactRepository, ctx_no_tenant: ToolCallContext
    ) -> None:
        tool = FetchArtifactTool(store)
        result = await tool.execute(ctx_no_tenant, {"artifact_id": "some-id"})
        assert result.success is False
        assert "tenant_id" in result.error.lower()

    @pytest.mark.asyncio
    async def test_fetch_returns_agent_id(
        self, store: InMemoryArtifactRepository, ctx: ToolCallContext
    ) -> None:
        store_tool = StoreArtifactTool(store)
        fetch_tool = FetchArtifactTool(store)

        store_result = await store_tool.execute(
            ctx,
            {"type": "document", "title": "Test", "content": "data"},
        )
        artifact_id = store_result.result["artifact_id"]

        fetch_result = await fetch_tool.execute(ctx, {"artifact_id": artifact_id})
        assert fetch_result.success is True
        assert fetch_result.result["created_by_agent_id"] == "master-agent"


# ---------------------------------------------------------------------------
# register_artifact_tools
# ---------------------------------------------------------------------------


class TestRegisterArtifactTools:
    """Tests for the register_artifact_tools factory function."""

    def test_both_tools_registered(self, store: InMemoryArtifactRepository) -> None:
        registry = ToolRegistry()
        register_artifact_tools(registry, store)
        tool_names = registry.list_tools()
        assert "store_artifact" in tool_names
        assert "fetch_artifact" in tool_names

    def test_idempotent_call_raises_on_double_register(
        self, store: InMemoryArtifactRepository
    ) -> None:
        registry = ToolRegistry()
        register_artifact_tools(registry, store)
        # Second registration should raise (ToolRegistry prevents duplicates)
        with pytest.raises(Exception):
            register_artifact_tools(registry, store)


# ---------------------------------------------------------------------------
# Integration: store-then-fetch roundtrip
# ---------------------------------------------------------------------------


class TestArtifactToolIntegration:
    """Integration tests for the store-then-fetch workflow."""

    @pytest.mark.asyncio
    async def test_store_fetch_structured_roundtrip(
        self, store: InMemoryArtifactRepository, ctx: ToolCallContext
    ) -> None:
        store_tool = StoreArtifactTool(store)
        fetch_tool = FetchArtifactTool(store)

        data = {"rows": [1, 2, 3], "count": 3}
        store_result = await store_tool.execute(
            ctx,
            {
                "type": "structured",
                "title": "Analysis Result",
                "content": json.dumps(data),
                "mime_type": "application/json",
            },
        )
        assert store_result.success is True
        artifact_id = store_result.result["artifact_id"]

        fetch_result = await fetch_tool.execute(ctx, {"artifact_id": artifact_id})
        assert fetch_result.success is True
        assert fetch_result.result["content"] == data
        assert fetch_result.result["type"] == "structured"
        assert fetch_result.result["title"] == "Analysis Result"

    @pytest.mark.asyncio
    async def test_cross_tenant_isolation_integration(
        self,
        store: InMemoryArtifactRepository,
        ctx: ToolCallContext,
        other_tenant_ctx: ToolCallContext,
    ) -> None:
        """Storing in tenant-abc is invisible from tenant-xyz."""
        store_tool = StoreArtifactTool(store)
        fetch_tool = FetchArtifactTool(store)

        store_result = await store_tool.execute(
            ctx,
            {"type": "code", "title": "Private Code", "content": "secret()"},
        )
        assert store_result.success is True
        artifact_id = store_result.result["artifact_id"]

        # tenant-xyz cannot see tenant-abc's artifact
        fetch_result = await fetch_tool.execute(other_tenant_ctx, {"artifact_id": artifact_id})
        assert fetch_result.success is False

        # tenant-abc can still see its own artifact
        fetch_result_own = await fetch_tool.execute(ctx, {"artifact_id": artifact_id})
        assert fetch_result_own.success is True

    @pytest.mark.asyncio
    async def test_multiple_artifacts_same_tenant(
        self, store: InMemoryArtifactRepository, ctx: ToolCallContext
    ) -> None:
        store_tool = StoreArtifactTool(store)
        fetch_tool = FetchArtifactTool(store)

        r1 = await store_tool.execute(
            ctx, {"type": "document", "title": "Doc 1", "content": "content 1"}
        )
        r2 = await store_tool.execute(
            ctx, {"type": "document", "title": "Doc 2", "content": "content 2"}
        )
        assert r1.success and r2.success
        assert r1.result["artifact_id"] != r2.result["artifact_id"]

        f1 = await fetch_tool.execute(ctx, {"artifact_id": r1.result["artifact_id"]})
        f2 = await fetch_tool.execute(ctx, {"artifact_id": r2.result["artifact_id"]})
        assert f1.result["title"] == "Doc 1"
        assert f2.result["title"] == "Doc 2"


# ---------------------------------------------------------------------------
# MasterAgent integration
# ---------------------------------------------------------------------------


class TestMasterAgentArtifactIntegration:
    """Tests that MasterAgent registers artifact tools when store is provided."""

    def test_artifact_tools_registered_when_store_provided(
        self, store: InMemoryArtifactRepository
    ) -> None:
        from omniforge.agents.master_agent import MasterAgent

        agent = MasterAgent(artifact_store=store)
        tool_names = agent._tool_registry.list_tools()
        assert "store_artifact" in tool_names
        assert "fetch_artifact" in tool_names

    def test_artifact_tools_absent_without_store(self) -> None:
        from omniforge.agents.master_agent import MasterAgent

        agent = MasterAgent()
        tool_names = agent._tool_registry.list_tools()
        assert "store_artifact" not in tool_names
        assert "fetch_artifact" not in tool_names
