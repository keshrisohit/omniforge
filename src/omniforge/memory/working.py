"""Working memory for active agent chains.

AgentContextStore is a singleton in-process key-value store scoped by
trace_id. Agents use it to share structured data within one request chain
without embedding everything in task description strings.

Usage:
    store = get_context_store()
    store.set(trace_id, "research_output", {...})
    value = store.get(trace_id, "research_output")
    store.clear(trace_id)  # called when the chain completes
"""

from typing import Any, Optional

from omniforge.memory.backends.in_memory import InMemoryBackend

_default_store: Optional["AgentContextStore"] = None


class AgentContextStore:
    """In-memory working-memory store scoped by trace_id.

    One global instance is shared across all agents in the same process.
    Each request chain (identified by trace_id) has an isolated namespace
    so concurrent requests never bleed into each other.
    """

    def __init__(self) -> None:
        self._backend = InMemoryBackend()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set(self, trace_id: str, key: str, value: Any) -> None:
        """Write *value* under *key* for the given trace.

        Args:
            trace_id: The trace that scopes this write.
            key: Slot name (e.g. "research_output").
            value: Any JSON-serialisable value (max 1 MB).

        Raises:
            ValueError: If value is not JSON-serialisable or exceeds 1 MB.
        """
        self._backend.set(trace_id, key, value)

    def get(self, trace_id: str, key: str) -> Optional[Any]:
        """Read the value stored under *key* for the given trace.

        Args:
            trace_id: The trace that scopes this read.
            key: Slot name to look up.

        Returns:
            The stored value, or None if the key does not exist.
        """
        return self._backend.get(trace_id, key)

    def list_keys(self, trace_id: str) -> list[str]:
        """Return all key names present for the given trace.

        Args:
            trace_id: The trace to inspect.

        Returns:
            List of key names (may be empty).
        """
        return self._backend.list_keys(trace_id)

    def clear(self, trace_id: str) -> None:
        """Delete all entries for the given trace (call on chain completion).

        Args:
            trace_id: The trace whose entries should be purged.
        """
        self._backend.clear(trace_id)


def get_context_store() -> AgentContextStore:
    """Return the process-wide AgentContextStore singleton."""
    global _default_store
    if _default_store is None:
        _default_store = AgentContextStore()
    return _default_store
