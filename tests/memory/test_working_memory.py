"""Tests for the working memory module (AgentContextStore + InMemoryBackend)."""

import pytest

from omniforge.memory.backends.in_memory import InMemoryBackend
from omniforge.memory.working import AgentContextStore, get_context_store


class TestInMemoryBackend:
    """Unit tests for InMemoryBackend."""

    def setup_method(self) -> None:
        self.backend = InMemoryBackend()

    def test_set_and_get_returns_stored_value(self) -> None:
        self.backend.set("trace-1", "key", {"hello": "world"})
        assert self.backend.get("trace-1", "key") == {"hello": "world"}

    def test_get_missing_key_returns_none(self) -> None:
        assert self.backend.get("trace-1", "nonexistent") is None

    def test_get_missing_namespace_returns_none(self) -> None:
        assert self.backend.get("no-such-trace", "key") is None

    def test_set_overwrites_existing_value(self) -> None:
        self.backend.set("trace-1", "key", "first")
        self.backend.set("trace-1", "key", "second")
        assert self.backend.get("trace-1", "key") == "second"

    def test_namespaces_are_isolated(self) -> None:
        self.backend.set("trace-A", "key", "A-value")
        self.backend.set("trace-B", "key", "B-value")
        assert self.backend.get("trace-A", "key") == "A-value"
        assert self.backend.get("trace-B", "key") == "B-value"

    def test_list_keys_returns_all_keys(self) -> None:
        self.backend.set("trace-1", "alpha", 1)
        self.backend.set("trace-1", "beta", 2)
        keys = self.backend.list_keys("trace-1")
        assert set(keys) == {"alpha", "beta"}

    def test_list_keys_empty_namespace(self) -> None:
        assert self.backend.list_keys("trace-99") == []

    def test_clear_removes_namespace(self) -> None:
        self.backend.set("trace-1", "key", "value")
        self.backend.clear("trace-1")
        assert self.backend.get("trace-1", "key") is None
        assert self.backend.list_keys("trace-1") == []

    def test_clear_nonexistent_namespace_is_noop(self) -> None:
        self.backend.clear("trace-never-existed")  # should not raise

    def test_rejects_non_json_serialisable_value(self) -> None:
        with pytest.raises(ValueError, match="JSON-serialisable"):
            self.backend.set("trace-1", "key", object())

    def test_rejects_value_exceeding_size_limit(self) -> None:
        huge = "x" * (1024 * 1024 + 10)
        with pytest.raises(ValueError, match="1 MB"):
            self.backend.set("trace-1", "key", huge)

    def test_accepts_various_json_types(self) -> None:
        cases = [
            ("string_key", "hello"),
            ("int_key", 42),
            ("list_key", [1, 2, 3]),
            ("dict_key", {"a": 1}),
            ("bool_key", True),
            ("null_key", None),
        ]
        for key, val in cases:
            self.backend.set("trace-1", key, val)
            assert self.backend.get("trace-1", key) == val


class TestAgentContextStore:
    """Unit tests for AgentContextStore."""

    def setup_method(self) -> None:
        self.store = AgentContextStore()

    def test_set_and_get(self) -> None:
        self.store.set("t1", "output", {"result": 42})
        assert self.store.get("t1", "output") == {"result": 42}

    def test_get_missing_returns_none(self) -> None:
        assert self.store.get("t1", "missing") is None

    def test_list_keys(self) -> None:
        self.store.set("t1", "a", 1)
        self.store.set("t1", "b", 2)
        assert set(self.store.list_keys("t1")) == {"a", "b"}

    def test_clear_removes_all_keys(self) -> None:
        self.store.set("t1", "a", 1)
        self.store.clear("t1")
        assert self.store.get("t1", "a") is None

    def test_traces_do_not_interfere(self) -> None:
        self.store.set("trace-A", "shared", "A")
        self.store.set("trace-B", "shared", "B")
        assert self.store.get("trace-A", "shared") == "A"
        assert self.store.get("trace-B", "shared") == "B"

    def test_clear_only_removes_own_trace(self) -> None:
        self.store.set("trace-A", "key", "A")
        self.store.set("trace-B", "key", "B")
        self.store.clear("trace-A")
        assert self.store.get("trace-A", "key") is None
        assert self.store.get("trace-B", "key") == "B"


class TestGetContextStore:
    """Tests for get_context_store() singleton."""

    def test_returns_same_instance(self) -> None:
        a = get_context_store()
        b = get_context_store()
        assert a is b

    def test_returns_agent_context_store(self) -> None:
        assert isinstance(get_context_store(), AgentContextStore)
