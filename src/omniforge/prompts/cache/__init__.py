"""Cache module for prompt management.

This module provides two-tier caching for composed prompts with:
- L1: In-memory LRU cache (< 0.1ms latency)
- L2: Optional Redis cache (1-5ms latency) for distributed deployments
"""

from omniforge.prompts.cache.keys import generate_cache_key
from omniforge.prompts.cache.manager import CacheManager

__all__ = [
    "CacheManager",
    "generate_cache_key",
]
