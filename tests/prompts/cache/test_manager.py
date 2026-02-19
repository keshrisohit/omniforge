"""Tests for cache manager with two-tier caching."""

from datetime import datetime
from typing import Optional

import pytest

from omniforge.prompts.cache.manager import CacheManager
from omniforge.prompts.models import ComposedPrompt


class MockRedisClient:
    """Mock Redis client for testing."""

    def __init__(self) -> None:
        """Initialize mock Redis client."""
        self._storage: dict[str, str] = {}
        self._should_fail = False

    async def get(self, key: str) -> Optional[str]:
        """Mock get operation."""
        if self._should_fail:
            raise Exception("Redis connection error")
        return self._storage.get(key)

    async def set(self, key: str, value: str, ex: int) -> None:
        """Mock set operation with TTL."""
        if self._should_fail:
            raise Exception("Redis connection error")
        self._storage[key] = value

    async def delete(self, *keys: str) -> None:
        """Mock delete operation."""
        if self._should_fail:
            raise Exception("Redis connection error")
        for key in keys:
            self._storage.pop(key, None)

    async def scan(self, cursor: int, match: str, count: int) -> tuple[int, list[str]]:
        """Mock scan operation for pattern matching."""
        if self._should_fail:
            raise Exception("Redis connection error")

        # Simple pattern matching for testing
        import fnmatch

        matching_keys = [k for k in self._storage.keys() if fnmatch.fnmatch(k, match)]

        # Simulate cursor-based iteration
        if cursor == 0 and matching_keys:
            return (0, matching_keys)  # Return all at once for simplicity
        return (0, [])

    async def flushdb(self) -> None:
        """Mock flush operation."""
        if self._should_fail:
            raise Exception("Redis connection error")
        self._storage.clear()

    def set_failure_mode(self, should_fail: bool) -> None:
        """Set whether Redis operations should fail."""
        self._should_fail = should_fail


@pytest.fixture
def sample_composed_prompt() -> ComposedPrompt:
    """Create a sample ComposedPrompt for testing."""
    return ComposedPrompt(
        content="Test prompt content",
        layer_versions={"system": 1, "tenant": 2},
        composition_time_ms=10.5,
        composed_at=datetime.utcnow(),
    )


@pytest.fixture
def mock_redis() -> MockRedisClient:
    """Create a mock Redis client."""
    return MockRedisClient()


class TestCacheManagerMemoryOnly:
    """Tests for CacheManager with memory cache only (no Redis)."""

    @pytest.mark.asyncio
    async def test_init_without_redis(self) -> None:
        """CacheManager should initialize without Redis client."""
        manager = CacheManager(max_memory_items=100, redis_client=None)

        stats = manager.stats()
        assert stats["size"] == 0
        assert stats["max_size"] == 100
        assert stats["redis_available"] is False

    @pytest.mark.asyncio
    async def test_set_and_get_memory_cache(self, sample_composed_prompt: ComposedPrompt) -> None:
        """Should store and retrieve from memory cache."""
        manager = CacheManager(max_memory_items=100)

        await manager.set("test-key", sample_composed_prompt)
        result = await manager.get("test-key")

        assert result is not None
        assert result.content == sample_composed_prompt.content
        assert result.layer_versions == sample_composed_prompt.layer_versions

    @pytest.mark.asyncio
    async def test_get_nonexistent_key(self) -> None:
        """Getting non-existent key should return None."""
        manager = CacheManager()

        result = await manager.get("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_invalidate_existing_key(self, sample_composed_prompt: ComposedPrompt) -> None:
        """Should invalidate existing cache entry."""
        manager = CacheManager()

        await manager.set("test-key", sample_composed_prompt)
        await manager.invalidate("test-key")
        result = await manager.get("test-key")

        assert result is None

    @pytest.mark.asyncio
    async def test_invalidate_nonexistent_key(self) -> None:
        """Invalidating non-existent key should not raise error."""
        manager = CacheManager()

        # Should not raise any exception
        await manager.invalidate("nonexistent")

    @pytest.mark.asyncio
    async def test_clear_cache(self, sample_composed_prompt: ComposedPrompt) -> None:
        """Should clear all entries from cache."""
        manager = CacheManager()

        await manager.set("key1", sample_composed_prompt)
        await manager.set("key2", sample_composed_prompt)

        await manager.clear()

        assert await manager.get("key1") is None
        assert await manager.get("key2") is None
        assert manager.stats()["size"] == 0

    @pytest.mark.asyncio
    async def test_lru_eviction(self, sample_composed_prompt: ComposedPrompt) -> None:
        """Should evict least recently used items when cache is full."""
        manager = CacheManager(max_memory_items=2)

        await manager.set("key1", sample_composed_prompt)
        await manager.set("key2", sample_composed_prompt)
        await manager.set("key3", sample_composed_prompt)  # Should evict key1

        assert await manager.get("key1") is None  # Evicted
        assert await manager.get("key2") is not None
        assert await manager.get("key3") is not None

    @pytest.mark.asyncio
    async def test_stats_tracking(self, sample_composed_prompt: ComposedPrompt) -> None:
        """Should track cache hits and misses."""
        manager = CacheManager()

        # Miss
        await manager.get("key1")
        # Set and hit
        await manager.set("key1", sample_composed_prompt)
        await manager.get("key1")
        # Another miss
        await manager.get("key2")

        stats = manager.stats()
        assert stats["hit_count"] == 1
        assert stats["miss_count"] == 2
        assert stats["size"] == 1

    @pytest.mark.asyncio
    async def test_invalidate_pattern_memory(self, sample_composed_prompt: ComposedPrompt) -> None:
        """Should invalidate keys matching glob pattern from memory cache."""
        manager = CacheManager()

        await manager.set("tenant:123:prompt:1", sample_composed_prompt)
        await manager.set("tenant:123:prompt:2", sample_composed_prompt)
        await manager.set("tenant:456:prompt:1", sample_composed_prompt)

        count = await manager.invalidate_pattern("tenant:123:*")

        assert count == 2
        assert await manager.get("tenant:123:prompt:1") is None
        assert await manager.get("tenant:123:prompt:2") is None
        assert await manager.get("tenant:456:prompt:1") is not None


class TestCacheManagerWithRedis:
    """Tests for CacheManager with Redis backend."""

    @pytest.mark.asyncio
    async def test_init_with_redis(self, mock_redis: MockRedisClient) -> None:
        """CacheManager should initialize with Redis client."""
        manager = CacheManager(max_memory_items=100, redis_client=mock_redis, default_ttl=3600)

        stats = manager.stats()
        assert stats["redis_available"] is True

    @pytest.mark.asyncio
    async def test_set_stores_in_both_tiers(
        self, mock_redis: MockRedisClient, sample_composed_prompt: ComposedPrompt
    ) -> None:
        """Should store in both memory and Redis."""
        manager = CacheManager(redis_client=mock_redis)

        await manager.set("test-key", sample_composed_prompt)

        # Check Redis storage directly
        assert "test-key" in mock_redis._storage

    @pytest.mark.asyncio
    async def test_get_from_memory_first(
        self, mock_redis: MockRedisClient, sample_composed_prompt: ComposedPrompt
    ) -> None:
        """Should retrieve from memory cache first (L1 hit)."""
        manager = CacheManager(redis_client=mock_redis)

        await manager.set("test-key", sample_composed_prompt)
        result = await manager.get("test-key")

        assert result is not None
        assert result.content == sample_composed_prompt.content

    @pytest.mark.asyncio
    async def test_get_from_redis_on_memory_miss(
        self, mock_redis: MockRedisClient, sample_composed_prompt: ComposedPrompt
    ) -> None:
        """Should retrieve from Redis if not in memory (L2 hit)."""
        manager = CacheManager(redis_client=mock_redis)

        await manager.set("test-key", sample_composed_prompt)

        # Clear memory cache to simulate memory miss
        manager._memory_cache.clear()

        # Should retrieve from Redis
        result = await manager.get("test-key")

        assert result is not None
        assert result.content == sample_composed_prompt.content
        # Should also populate memory cache
        assert "test-key" in manager._memory_cache

    @pytest.mark.asyncio
    async def test_invalidate_from_both_tiers(
        self, mock_redis: MockRedisClient, sample_composed_prompt: ComposedPrompt
    ) -> None:
        """Should invalidate from both memory and Redis."""
        manager = CacheManager(redis_client=mock_redis)

        await manager.set("test-key", sample_composed_prompt)
        await manager.invalidate("test-key")

        assert await manager.get("test-key") is None
        assert "test-key" not in mock_redis._storage

    @pytest.mark.asyncio
    async def test_invalidate_pattern_both_tiers(
        self, mock_redis: MockRedisClient, sample_composed_prompt: ComposedPrompt
    ) -> None:
        """Should invalidate pattern from both memory and Redis."""
        manager = CacheManager(redis_client=mock_redis)

        await manager.set("tenant:123:prompt:1", sample_composed_prompt)
        await manager.set("tenant:123:prompt:2", sample_composed_prompt)
        await manager.set("tenant:456:prompt:1", sample_composed_prompt)

        count = await manager.invalidate_pattern("tenant:123:*")

        assert count == 2
        assert await manager.get("tenant:123:prompt:1") is None
        assert await manager.get("tenant:456:prompt:1") is not None

    @pytest.mark.asyncio
    async def test_clear_both_tiers(
        self, mock_redis: MockRedisClient, sample_composed_prompt: ComposedPrompt
    ) -> None:
        """Should clear both memory and Redis caches."""
        manager = CacheManager(redis_client=mock_redis)

        await manager.set("key1", sample_composed_prompt)
        await manager.set("key2", sample_composed_prompt)

        await manager.clear()

        assert await manager.get("key1") is None
        assert await manager.get("key2") is None
        assert len(mock_redis._storage) == 0

    @pytest.mark.asyncio
    async def test_custom_ttl(
        self, mock_redis: MockRedisClient, sample_composed_prompt: ComposedPrompt
    ) -> None:
        """Should use custom TTL when provided."""
        manager = CacheManager(redis_client=mock_redis, default_ttl=3600)

        await manager.set("test-key", sample_composed_prompt, ttl=7200)

        # We can't directly verify TTL in mock, but ensure no error
        assert "test-key" in mock_redis._storage


class TestCacheManagerRedisErrorHandling:
    """Tests for graceful Redis error handling."""

    @pytest.mark.asyncio
    async def test_get_continues_on_redis_error(
        self, mock_redis: MockRedisClient, sample_composed_prompt: ComposedPrompt
    ) -> None:
        """Should gracefully handle Redis errors on get."""
        manager = CacheManager(redis_client=mock_redis)

        # Store in both tiers
        await manager.set("test-key", sample_composed_prompt)

        # Clear memory to force Redis lookup
        manager._memory_cache.clear()

        # Make Redis fail
        mock_redis.set_failure_mode(True)

        # Should return None without raising exception
        result = await manager.get("test-key")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_continues_on_redis_error(
        self, mock_redis: MockRedisClient, sample_composed_prompt: ComposedPrompt
    ) -> None:
        """Should gracefully handle Redis errors on set."""
        manager = CacheManager(redis_client=mock_redis)

        # Make Redis fail
        mock_redis.set_failure_mode(True)

        # Should not raise exception
        await manager.set("test-key", sample_composed_prompt)

        # Should still be in memory cache
        result = await manager.get("test-key")
        assert result is not None

    @pytest.mark.asyncio
    async def test_invalidate_continues_on_redis_error(
        self, mock_redis: MockRedisClient, sample_composed_prompt: ComposedPrompt
    ) -> None:
        """Should gracefully handle Redis errors on invalidate."""
        manager = CacheManager(redis_client=mock_redis)

        await manager.set("test-key", sample_composed_prompt)

        # Make Redis fail
        mock_redis.set_failure_mode(True)

        # Should not raise exception
        await manager.invalidate("test-key")

        # Memory cache should still be invalidated
        result = await manager.get("test-key")
        assert result is None

    @pytest.mark.asyncio
    async def test_invalidate_pattern_continues_on_redis_error(
        self, mock_redis: MockRedisClient, sample_composed_prompt: ComposedPrompt
    ) -> None:
        """Should gracefully handle Redis errors on pattern invalidation."""
        manager = CacheManager(redis_client=mock_redis)

        await manager.set("tenant:123:prompt:1", sample_composed_prompt)

        # Make Redis fail
        mock_redis.set_failure_mode(True)

        # Should not raise exception, returns count from memory only
        count = await manager.invalidate_pattern("tenant:123:*")

        assert count == 1  # Only memory cache count

    @pytest.mark.asyncio
    async def test_clear_continues_on_redis_error(
        self, mock_redis: MockRedisClient, sample_composed_prompt: ComposedPrompt
    ) -> None:
        """Should gracefully handle Redis errors on clear."""
        manager = CacheManager(redis_client=mock_redis)

        await manager.set("test-key", sample_composed_prompt)

        # Make Redis fail
        mock_redis.set_failure_mode(True)

        # Should not raise exception
        await manager.clear()

        # Memory cache should still be cleared
        assert manager.stats()["size"] == 0


class TestCacheManagerThreadSafety:
    """Tests for thread-safe cache operations."""

    @pytest.mark.asyncio
    async def test_concurrent_get_operations(self, sample_composed_prompt: ComposedPrompt) -> None:
        """Should handle concurrent get operations safely."""
        import asyncio

        manager = CacheManager()
        await manager.set("test-key", sample_composed_prompt)

        # Run multiple concurrent gets
        results = await asyncio.gather(*[manager.get("test-key") for _ in range(10)])

        assert all(r is not None for r in results)
        assert all(r.content == sample_composed_prompt.content for r in results)

    @pytest.mark.asyncio
    async def test_concurrent_set_operations(self, sample_composed_prompt: ComposedPrompt) -> None:
        """Should handle concurrent set operations safely."""
        import asyncio

        manager = CacheManager()

        # Run multiple concurrent sets
        await asyncio.gather(*[manager.set(f"key-{i}", sample_composed_prompt) for i in range(10)])

        stats = manager.stats()
        assert stats["size"] == 10
