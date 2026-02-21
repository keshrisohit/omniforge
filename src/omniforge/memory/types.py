"""Core types for the OmniForge memory module.

Defines MemoryEntry — the atomic unit stored in any memory backend.
"""

from datetime import datetime
from typing import Any


class MemoryEntry:
    """A single key-value entry in a memory store.

    Attributes:
        key: Slot name within the trace scope
        value: Any JSON-serialisable value
        created_at: When the entry was written
        updated_at: When the entry was last overwritten
    """

    __slots__ = ("key", "value", "created_at", "updated_at")

    def __init__(self, key: str, value: Any) -> None:
        now = datetime.utcnow()
        self.key = key
        self.value = value
        self.created_at = now
        self.updated_at = now

    def update(self, value: Any) -> None:
        self.value = value
        self.updated_at = datetime.utcnow()
