"""In-memory storage backend — default for Phase 2.

Scoped by namespace (trace_id). Not durable across process restarts.
Phase 3 will add a persistent backend.
"""

from typing import Any, Optional

from omniforge.memory.backends.base import StorageBackend
from omniforge.memory.types import MemoryEntry

_MAX_VALUE_BYTES = 1 * 1024 * 1024  # 1 MB per entry cap


class InMemoryBackend(StorageBackend):
    """Thread-safe-enough in-memory backend backed by a plain dict.

    Not designed for concurrent writes from threads — but asyncio is
    single-threaded so this is safe for all in-process agent calls.
    """

    def __init__(self) -> None:
        # namespace → {key: MemoryEntry}
        self._store: dict[str, dict[str, MemoryEntry]] = {}

    def set(self, namespace: str, key: str, value: Any) -> None:
        import json

        # Enforce entry size limit to prevent memory abuse
        try:
            encoded = json.dumps(value)
            if len(encoded.encode()) > _MAX_VALUE_BYTES:
                raise ValueError(
                    f"Value for key '{key}' exceeds the 1 MB per-entry limit"
                )
        except (TypeError, ValueError) as exc:
            if "1 MB" in str(exc):
                raise
            raise ValueError(f"Value for key '{key}' must be JSON-serialisable") from exc

        ns = self._store.setdefault(namespace, {})
        if key in ns:
            ns[key].update(value)
        else:
            ns[key] = MemoryEntry(key=key, value=value)

    def get(self, namespace: str, key: str) -> Optional[Any]:
        entry = self._store.get(namespace, {}).get(key)
        return entry.value if entry is not None else None

    def list_keys(self, namespace: str) -> list[str]:
        return list(self._store.get(namespace, {}).keys())

    def clear(self, namespace: str) -> None:
        self._store.pop(namespace, None)
