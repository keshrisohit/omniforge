"""Prompt storage implementations.

This package provides repository interfaces and implementations for
storing prompts, versions, and experiments.
"""

from omniforge.prompts.storage.memory import InMemoryPromptRepository
from omniforge.prompts.storage.repository import PromptRepository

__all__ = [
    "PromptRepository",
    "InMemoryPromptRepository",
]
