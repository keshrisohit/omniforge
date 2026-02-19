"""Cache manager with two-tier caching strategy.

This module implements a two-tier caching system:
- L1: In-memory LRU cache (< 0.1ms latency)
- L2: Optional Redis cache (1-5ms latency) for distributed deployments
"""

import asyncio
import logging
from typing import Any, Optional

import cachetools

from omniforge.prompts.models import ComposedPrompt

logger = logging.getLogger(__name__)


class CacheManager:
    """Two-tier cache manager for composed prompts.

    Implements a hierarchical caching strategy with fast in-memory cache (L1)
    and optional distributed Redis cache (L2) for scalability.

    Attributes:
        _memory_cache: L1 in-memory LRU cache
        _redis_client: Optional L2 Redis client for distributed caching
        _default_ttl: Default time-to-live for cache entries in seconds
        _lock: Asyncio lock for thread-safe operations
        _hit_count: Number of cache hits (L1 or L2)
        _miss_count: Number of cache misses
    """

    def __init__(
        self,
        max_memory_items: int = 1000,
        redis_client: Optional[Any] = None,
        default_ttl: int = 3600,
    ) -> None:
        """Initialize the cache manager.

        Args:
            max_memory_items: Maximum number of items in L1 cache
            redis_client: Optional Redis async client for L2 cache
            default_ttl: Default TTL in seconds for cache entries
        """
        self._memory_cache: cachetools.LRUCache[str, ComposedPrompt] = cachetools.LRUCache(
            maxsize=max_memory_items
        )
        self._redis_client = redis_client
        self._default_ttl = default_ttl
        self._lock = asyncio.Lock()
        self._hit_count = 0
        self._miss_count = 0

        logger.info(
            f"CacheManager initialized with max_memory_items={max_memory_items}, "
            f"redis_enabled={redis_client is not None}, default_ttl={default_ttl}"
        )

    async def get(self, key: str) -> Optional[ComposedPrompt]:
        """Retrieve a cached composed prompt.

        Checks L1 memory cache first, then L2 Redis cache if available.
        On Redis hit, populates the memory cache for faster subsequent access.

        Args:
            key: Cache key to retrieve

        Returns:
            Cached ComposedPrompt if found, None otherwise
        """
        async with self._lock:
            # Check L1 memory cache first
            if key in self._memory_cache:
                self._hit_count += 1
                logger.debug(f"L1 cache hit for key: {key[:16]}...")
                cached_value: ComposedPrompt = self._memory_cache[key]
                return cached_value

            # Check L2 Redis cache if available
            if self._redis_client:
                try:
                    cached_data = await self._redis_client.get(key)
                    if cached_data:
                        # Deserialize from JSON
                        composed_prompt = ComposedPrompt.model_validate_json(cached_data)

                        # Populate L1 cache for faster subsequent access
                        self._memory_cache[key] = composed_prompt
                        self._hit_count += 1
                        logger.debug(f"L2 cache hit for key: {key[:16]}...")
                        return composed_prompt
                except Exception as e:
                    # Redis errors should not break composition
                    logger.warning(f"Redis get error for key {key[:16]}...: {e}")

            # Cache miss
            self._miss_count += 1
            logger.debug(f"Cache miss for key: {key[:16]}...")
            return None

    async def set(self, key: str, value: ComposedPrompt, ttl: Optional[int] = None) -> None:
        """Store a composed prompt in the cache.

        Stores in both L1 memory cache and L2 Redis cache if available.

        Args:
            key: Cache key to store under
            value: ComposedPrompt to cache
            ttl: Optional TTL in seconds (uses default_ttl if not provided)
        """
        async with self._lock:
            # Store in L1 memory cache
            self._memory_cache[key] = value
            logger.debug(f"Stored in L1 cache: {key[:16]}...")

            # Store in L2 Redis cache if available
            if self._redis_client:
                try:
                    ttl_seconds = ttl if ttl is not None else self._default_ttl
                    # Serialize to JSON for Redis storage
                    cached_data = value.model_dump_json()
                    await self._redis_client.set(key, cached_data, ex=ttl_seconds)
                    logger.debug(f"Stored in L2 cache: {key[:16]}... with TTL={ttl_seconds}s")
                except Exception as e:
                    # Redis errors should not break composition
                    logger.warning(f"Redis set error for key {key[:16]}...: {e}")

    async def invalidate(self, key: str) -> None:
        """Invalidate a specific cache entry.

        Removes the entry from both L1 and L2 caches.

        Args:
            key: Cache key to invalidate
        """
        async with self._lock:
            # Remove from L1 memory cache
            if key in self._memory_cache:
                del self._memory_cache[key]
                logger.debug(f"Invalidated from L1 cache: {key[:16]}...")

            # Remove from L2 Redis cache if available
            if self._redis_client:
                try:
                    await self._redis_client.delete(key)
                    logger.debug(f"Invalidated from L2 cache: {key[:16]}...")
                except Exception as e:
                    # Redis errors should not break composition
                    logger.warning(f"Redis delete error for key {key[:16]}...: {e}")

    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all cache entries matching a pattern.

        Supports glob-style patterns (e.g., "tenant:123:*").
        For L1 cache, performs full scan. For L2 Redis, uses SCAN command.

        Args:
            pattern: Glob-style pattern to match keys

        Returns:
            Count of invalidated keys
        """
        invalidated_count = 0

        async with self._lock:
            # Invalidate matching keys from L1 memory cache
            # Convert glob pattern to simple prefix matching for memory cache
            keys_to_remove = []
            for key in self._memory_cache:
                if self._matches_pattern(key, pattern):
                    keys_to_remove.append(key)

            for key in keys_to_remove:
                del self._memory_cache[key]
                invalidated_count += 1

            logger.debug(f"Invalidated {invalidated_count} keys from L1 cache matching: {pattern}")

            # Invalidate from L2 Redis cache if available
            if self._redis_client:
                try:
                    # Use SCAN to find matching keys
                    cursor = 0
                    redis_count = 0
                    while True:
                        cursor, keys = await self._redis_client.scan(
                            cursor, match=pattern, count=100
                        )
                        if keys:
                            await self._redis_client.delete(*keys)
                            redis_count += len(keys)
                        if cursor == 0:
                            break

                    logger.debug(
                        f"Invalidated {redis_count} keys from L2 cache matching: {pattern}"
                    )
                except Exception as e:
                    # Redis errors should not break composition
                    logger.warning(f"Redis pattern invalidation error for {pattern}: {e}")

        return invalidated_count

    async def clear(self) -> None:
        """Clear all entries from both cache tiers.

        Removes all entries from L1 memory cache and L2 Redis cache.
        """
        async with self._lock:
            # Clear L1 memory cache
            self._memory_cache.clear()
            logger.info("Cleared L1 memory cache")

            # Clear L2 Redis cache if available
            if self._redis_client:
                try:
                    await self._redis_client.flushdb()
                    logger.info("Cleared L2 Redis cache")
                except Exception as e:
                    # Redis errors should not break composition
                    logger.warning(f"Redis flush error: {e}")

    def stats(self) -> dict[str, Any]:
        """Get current cache statistics.

        Returns:
            Dictionary containing cache statistics including size, max size,
            hit/miss counts, and Redis availability
        """
        return {
            "size": len(self._memory_cache),
            "max_size": self._memory_cache.maxsize,
            "hit_count": self._hit_count,
            "miss_count": self._miss_count,
            "redis_available": self._redis_client is not None,
        }

    @staticmethod
    def _matches_pattern(key: str, pattern: str) -> bool:
        """Check if a key matches a glob-style pattern.

        Supports simple glob patterns with * wildcard.

        Args:
            key: Key to check
            pattern: Glob-style pattern (e.g., "tenant:*:prompt")

        Returns:
            True if key matches pattern, False otherwise
        """
        import fnmatch

        return fnmatch.fnmatch(key, pattern)
