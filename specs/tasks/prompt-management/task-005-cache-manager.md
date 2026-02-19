# TASK-005: Implement Cache Manager with Two-Tier Caching

## Objective

Create a cache manager supporting in-memory LRU caching with optional Redis backend for distributed deployments.

## Requirements

### Cache Manager (`src/omniforge/prompts/cache/manager.py`)

**CacheManager class**:

Constructor parameters:
- `max_memory_items: int = 1000` - LRU cache size
- `redis_client: Optional[Any] = None` - Optional Redis async client
- `default_ttl: int = 3600` - Default TTL in seconds

Methods:
- `async get(key: str) -> Optional[ComposedPrompt]`:
  - Check memory cache first (L1)
  - If miss, check Redis (L2) if available
  - On Redis hit, populate memory cache
  - Return None if not found in any tier

- `async set(key: str, value: ComposedPrompt, ttl: Optional[int] = None)`:
  - Store in memory cache
  - Store in Redis with TTL if Redis available

- `async invalidate(key: str)`:
  - Remove from memory cache
  - Remove from Redis if available

- `async invalidate_pattern(pattern: str) -> int`:
  - Invalidate all keys matching pattern
  - Return count of invalidated keys
  - Support glob-style patterns

- `async clear()`:
  - Clear all entries from both tiers

- `stats() -> dict[str, Any]`:
  - Return cache statistics (size, max_size, hit/miss counts, redis_available)

### Cache Key Generation (`src/omniforge/prompts/cache/keys.py`)

**generate_cache_key function**:
- Input: version IDs from all layers, variables dict
- Output: SHA256 hash string
- Exclude highly variable items (user_input) from key
- Include sorted stable variables in hash

### Package Init
- `src/omniforge/prompts/cache/__init__.py`

### Error Handling
- Redis errors should not break composition (graceful degradation)
- Catch and log Redis exceptions, continue without cache

## Acceptance Criteria
- [ ] Memory cache (LRU) stores up to max_memory_items
- [ ] Redis operations work when client provided
- [ ] Graceful fallback when Redis unavailable or errors
- [ ] Cache key is deterministic for same inputs
- [ ] Pattern invalidation clears matching keys
- [ ] Stats reflect current cache state
- [ ] Unit tests cover all cache operations
- [ ] Tests verify graceful Redis error handling

## Dependencies
- TASK-001 (ComposedPrompt model)

## Estimated Complexity
Medium
