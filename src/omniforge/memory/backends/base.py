"""Abstract storage backend interface for the memory module."""

from abc import ABC, abstractmethod
from typing import Any, Optional


class StorageBackend(ABC):
    """Abstract key-value store scoped by a namespace string (trace_id)."""

    @abstractmethod
    def set(self, namespace: str, key: str, value: Any) -> None:
        """Write a value into the given namespace."""

    @abstractmethod
    def get(self, namespace: str, key: str) -> Optional[Any]:
        """Read a value from the given namespace. Returns None if missing."""

    @abstractmethod
    def list_keys(self, namespace: str) -> list[str]:
        """Return all keys present in the given namespace."""

    @abstractmethod
    def clear(self, namespace: str) -> None:
        """Delete all entries for the given namespace."""
