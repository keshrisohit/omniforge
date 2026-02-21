"""Tests for ReadContextTool and WriteContextTool."""

import pytest

from omniforge.memory.working import AgentContextStore
from omniforge.tools.base import ToolCallContext
from omniforge.tools.builtin.context import ReadContextTool, WriteContextTool


def make_context(
    task_id: str = "task-1",
    trace_id: str | None = "trace-1",
) -> ToolCallContext:
    return ToolCallContext(
        correlation_id="corr-1",
        task_id=task_id,
        agent_id="agent-1",
        trace_id=trace_id,
    )


@pytest.fixture(autouse=True)
def isolated_store(monkeypatch: pytest.MonkeyPatch) -> AgentContextStore:
    """Give each test its own AgentContextStore so they don't share state."""
    store = AgentContextStore()
    import omniforge.memory.working as wm
    import omniforge.tools.builtin.context as ctx_mod

    monkeypatch.setattr(wm, "_default_store", store)
    return store


class TestWriteContextTool:
    """Tests for WriteContextTool."""

    @pytest.fixture
    def tool(self) -> WriteContextTool:
        return WriteContextTool()

    @pytest.mark.asyncio
    async def test_write_succeeds(self, tool: WriteContextTool) -> None:
        ctx = make_context()
        result = await tool.execute(ctx, {"key": "output", "value": {"x": 1}})
        assert result.success
        assert result.result["key"] == "output"
        assert result.result["trace_id"] == "trace-1"

    @pytest.mark.asyncio
    async def test_write_missing_key_fails(self, tool: WriteContextTool) -> None:
        ctx = make_context()
        result = await tool.execute(ctx, {"key": "", "value": 42})
        assert not result.success
        assert "key" in result.error.lower()

    @pytest.mark.asyncio
    async def test_write_missing_value_fails(self, tool: WriteContextTool) -> None:
        ctx = make_context()
        result = await tool.execute(ctx, {"key": "output"})
        assert not result.success
        assert "value" in result.error.lower()

    @pytest.mark.asyncio
    async def test_write_fallback_to_task_id_when_no_trace(
        self, tool: WriteContextTool, isolated_store: AgentContextStore
    ) -> None:
        ctx = make_context(task_id="task-99", trace_id=None)
        result = await tool.execute(ctx, {"key": "data", "value": "hello"})
        assert result.success
        # Falls back to task_id as namespace
        assert isolated_store.get("task-99", "data") == "hello"

    @pytest.mark.asyncio
    async def test_write_non_serialisable_fails(self, tool: WriteContextTool) -> None:
        ctx = make_context()
        result = await tool.execute(ctx, {"key": "bad", "value": object()})
        assert not result.success

    @pytest.mark.asyncio
    async def test_definition_name(self, tool: WriteContextTool) -> None:
        assert tool.definition.name == "write_context"


class TestReadContextTool:
    """Tests for ReadContextTool."""

    @pytest.fixture
    def tool(self) -> ReadContextTool:
        return ReadContextTool()

    @pytest.mark.asyncio
    async def test_read_returns_written_value(
        self, tool: ReadContextTool, isolated_store: AgentContextStore
    ) -> None:
        isolated_store.set("trace-1", "result", {"answer": 42})
        ctx = make_context()
        result = await tool.execute(ctx, {"key": "result"})
        assert result.success
        assert result.result["value"] == {"answer": 42}
        assert result.result["found"] is True

    @pytest.mark.asyncio
    async def test_read_missing_key_returns_not_found(self, tool: ReadContextTool) -> None:
        ctx = make_context()
        result = await tool.execute(ctx, {"key": "nonexistent"})
        assert result.success  # not an error — just missing
        assert result.result["value"] is None
        assert result.result["found"] is False

    @pytest.mark.asyncio
    async def test_read_missing_key_arg_fails(self, tool: ReadContextTool) -> None:
        ctx = make_context()
        result = await tool.execute(ctx, {"key": ""})
        assert not result.success
        assert "key" in result.error.lower()

    @pytest.mark.asyncio
    async def test_read_fallback_to_task_id_when_no_trace(
        self, tool: ReadContextTool, isolated_store: AgentContextStore
    ) -> None:
        isolated_store.set("task-42", "data", "hi")
        ctx = make_context(task_id="task-42", trace_id=None)
        result = await tool.execute(ctx, {"key": "data"})
        assert result.success
        assert result.result["value"] == "hi"

    @pytest.mark.asyncio
    async def test_definition_name(self, tool: ReadContextTool) -> None:
        assert tool.definition.name == "read_context"


class TestWriteReadRoundtrip:
    """Integration: write then read."""

    @pytest.mark.asyncio
    async def test_write_then_read(self, isolated_store: AgentContextStore) -> None:
        writer = WriteContextTool()
        reader = ReadContextTool()
        ctx = make_context()

        write_result = await writer.execute(ctx, {"key": "pipeline_output", "value": [1, 2, 3]})
        assert write_result.success

        read_result = await reader.execute(ctx, {"key": "pipeline_output"})
        assert read_result.success
        assert read_result.result["value"] == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_different_traces_isolated(
        self, isolated_store: AgentContextStore
    ) -> None:
        writer = WriteContextTool()
        reader = ReadContextTool()

        ctx_a = make_context(trace_id="trace-A")
        ctx_b = make_context(trace_id="trace-B")

        await writer.execute(ctx_a, {"key": "shared", "value": "A-value"})
        await writer.execute(ctx_b, {"key": "shared", "value": "B-value"})

        res_a = await reader.execute(ctx_a, {"key": "shared"})
        res_b = await reader.execute(ctx_b, {"key": "shared"})

        assert res_a.result["value"] == "A-value"
        assert res_b.result["value"] == "B-value"
