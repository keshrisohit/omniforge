# TASK-501: Implement Rate Limiter for Enterprise Quotas

## Description

Create the rate limiting system for enforcing per-tenant quotas on tool calls, tokens, and costs. This is essential for enterprise deployment to prevent abuse and ensure fair resource allocation.

## Requirements

- Create `RateLimitConfig` model:
  - llm_calls_per_minute: int
  - external_calls_per_minute: int
  - database_calls_per_minute: int
  - tokens_per_minute: int
  - tokens_per_hour: int
  - cost_per_hour_usd: float
  - cost_per_day_usd: float
- Create `TenantLimiter` class:
  - Constructor accepting RateLimitConfig
  - Create AsyncLimiter instances for each limit type
  - Track hourly/daily cost with sliding windows
  - `check_and_consume(tool_type, tokens, cost_usd)` async method
  - `_get_limiter(tool_type)` helper
  - `_reset_windows_if_needed()` for time window management
- Create `RateLimiter` class (multi-tenant):
  - Constructor accepting default_config
  - `configure_tenant(tenant_id, config)` method
  - `check_and_consume(tenant_id, tool_type, tokens, cost_usd)` async method
  - Lazy initialization of tenant limiters

## Acceptance Criteria

- [ ] Rate limits enforced per tool type
- [ ] Token limits enforced per minute and hour
- [ ] Cost limits enforced per hour and day
- [ ] Per-tenant configuration supported
- [ ] Default config used for unconfigured tenants
- [ ] Time windows reset correctly
- [ ] Unit tests verify rate limiting behavior

## Dependencies

- TASK-101 (for ToolType enum)
- External: aiolimiter >= 1.1.0

## Files to Create/Modify

- `src/omniforge/enterprise/__init__.py` (new)
- `src/omniforge/enterprise/rate_limiter.py` (new)
- `tests/enterprise/__init__.py` (new)
- `tests/enterprise/test_rate_limiter.py` (new)

## Estimated Complexity

Medium (4-5 hours)

## Key Considerations

- Use aiolimiter for async rate limiting
- Time window reset logic is critical
- Consider distributed rate limiting for multi-instance deployment
