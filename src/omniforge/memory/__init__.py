"""OmniForge memory module.

Provides working memory (AgentContextStore) for sharing data across
agents in the same request chain, scoped by trace_id.
"""

from omniforge.memory.working import AgentContextStore, get_context_store

__all__ = ["AgentContextStore", "get_context_store"]
