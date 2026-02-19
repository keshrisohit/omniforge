"""Tests for rate limiter."""

import asyncio
import time

import pytest

from omniforge.enterprise.rate_limiter import RateLimitConfig, RateLimiter, TenantLimiter
from omniforge.tools.types import ToolType


def test_rate_limit_config_defaults():
    """Test RateLimitConfig default values."""
    config = RateLimitConfig()

    assert config.llm_calls_per_minute == 100
    assert config.external_calls_per_minute == 200
    assert config.database_calls_per_minute == 300
    assert config.tokens_per_minute == 100000
    assert config.tokens_per_hour == 1000000
    assert config.cost_per_hour_usd == 10.0
    assert config.cost_per_day_usd == 100.0


def test_rate_limit_config_custom():
    """Test RateLimitConfig with custom values."""
    config = RateLimitConfig(
        llm_calls_per_minute=50,
        tokens_per_minute=50000,
        cost_per_hour_usd=5.0,
    )

    assert config.llm_calls_per_minute == 50
    assert config.tokens_per_minute == 50000
    assert config.cost_per_hour_usd == 5.0


def test_tenant_limiter_initialization():
    """Test TenantLimiter initializes correctly."""
    config = RateLimitConfig(llm_calls_per_minute=10)
    limiter = TenantLimiter(config)

    assert limiter.config == config
    assert limiter._hourly_cost == 0.0
    assert limiter._daily_cost == 0.0


@pytest.mark.asyncio
async def test_tenant_limiter_llm_calls():
    """Test LLM call rate limiting."""
    config = RateLimitConfig(llm_calls_per_minute=3)
    limiter = TenantLimiter(config)

    # First 3 calls should succeed
    assert await limiter.check_and_consume(ToolType.LLM) is True
    assert await limiter.check_and_consume(ToolType.LLM) is True
    assert await limiter.check_and_consume(ToolType.LLM) is True

    # 4th call should fail (rate limit exceeded)
    assert await limiter.check_and_consume(ToolType.LLM) is False


@pytest.mark.asyncio
async def test_tenant_limiter_external_calls():
    """Test external API call rate limiting."""
    config = RateLimitConfig(external_calls_per_minute=2)
    limiter = TenantLimiter(config)

    # First 2 calls should succeed
    assert await limiter.check_and_consume(ToolType.API) is True
    assert await limiter.check_and_consume(ToolType.API) is True

    # 3rd call should fail
    assert await limiter.check_and_consume(ToolType.API) is False


@pytest.mark.asyncio
async def test_tenant_limiter_database_calls():
    """Test database call rate limiting."""
    config = RateLimitConfig(database_calls_per_minute=2)
    limiter = TenantLimiter(config)

    # First 2 calls should succeed
    assert await limiter.check_and_consume(ToolType.DATABASE) is True
    assert await limiter.check_and_consume(ToolType.DATABASE) is True

    # 3rd call should fail
    assert await limiter.check_and_consume(ToolType.DATABASE) is False


@pytest.mark.asyncio
async def test_tenant_limiter_token_limits():
    """Test token rate limiting."""
    config = RateLimitConfig(tokens_per_minute=1000)
    limiter = TenantLimiter(config)

    # Consume 800 tokens - should succeed
    assert await limiter.check_and_consume(ToolType.LLM, tokens=800) is True

    # Consume 100 more tokens - should succeed (total 900)
    assert await limiter.check_and_consume(ToolType.LLM, tokens=100) is True

    # Try to consume 200 more - should fail (would exceed 1000)
    assert await limiter.check_and_consume(ToolType.LLM, tokens=200) is False


@pytest.mark.asyncio
async def test_tenant_limiter_cost_limits_hourly():
    """Test hourly cost limiting."""
    config = RateLimitConfig(cost_per_hour_usd=1.0)
    limiter = TenantLimiter(config)

    # Consume $0.6 - should succeed
    assert await limiter.check_and_consume(ToolType.LLM, cost_usd=0.6) is True

    # Consume $0.3 more - should succeed (total $0.9)
    assert await limiter.check_and_consume(ToolType.LLM, cost_usd=0.3) is True

    # Try to consume $0.2 more - should fail (would exceed $1.0)
    assert await limiter.check_and_consume(ToolType.LLM, cost_usd=0.2) is False


@pytest.mark.asyncio
async def test_tenant_limiter_cost_limits_daily():
    """Test daily cost limiting."""
    config = RateLimitConfig(cost_per_day_usd=2.0, cost_per_hour_usd=10.0)
    limiter = TenantLimiter(config)

    # Consume $1.5 - should succeed
    assert await limiter.check_and_consume(ToolType.LLM, cost_usd=1.5) is True

    # Try to consume $0.6 more - should fail (would exceed daily $2.0)
    assert await limiter.check_and_consume(ToolType.LLM, cost_usd=0.6) is False


@pytest.mark.asyncio
async def test_tenant_limiter_combined_limits():
    """Test multiple limits checked together."""
    config = RateLimitConfig(
        llm_calls_per_minute=5,
        tokens_per_minute=1000,
        cost_per_hour_usd=1.0,
    )
    limiter = TenantLimiter(config)

    # Make calls with tokens and cost
    assert await limiter.check_and_consume(ToolType.LLM, tokens=200, cost_usd=0.2) is True
    assert await limiter.check_and_consume(ToolType.LLM, tokens=300, cost_usd=0.3) is True
    assert await limiter.check_and_consume(ToolType.LLM, tokens=400, cost_usd=0.4) is True

    # Total: 3 calls, 900 tokens, $0.9
    # Next call with 200 tokens and $0.2 should fail due to cost limit
    assert await limiter.check_and_consume(ToolType.LLM, tokens=200, cost_usd=0.2) is False


@pytest.mark.asyncio
async def test_tenant_limiter_no_limit_for_other_tool_types():
    """Test that tool types without specific limiters still work."""
    config = RateLimitConfig()
    limiter = TenantLimiter(config)

    # FILE_SYSTEM type has no specific limiter, should still track tokens/cost
    assert await limiter.check_and_consume(ToolType.FILE_SYSTEM, tokens=100, cost_usd=0.1) is True


@pytest.mark.asyncio
async def test_tenant_limiter_window_reset():
    """Test that cost windows reset after time period."""
    config = RateLimitConfig(cost_per_hour_usd=1.0)
    limiter = TenantLimiter(config)

    # Consume $0.9
    assert await limiter.check_and_consume(ToolType.LLM, cost_usd=0.9) is True

    # Manually advance time by 1 hour
    limiter._hour_window_start -= 3601

    # Reset should happen on next check
    # Now we should be able to consume $0.9 again
    assert await limiter.check_and_consume(ToolType.LLM, cost_usd=0.9) is True


def test_rate_limiter_initialization():
    """Test RateLimiter initializes correctly."""
    default_config = RateLimitConfig(llm_calls_per_minute=50)
    limiter = RateLimiter(default_config=default_config)

    assert limiter._default_config == default_config
    assert len(limiter._tenant_configs) == 0
    assert len(limiter._tenant_limiters) == 0


def test_rate_limiter_configure_tenant():
    """Test tenant configuration."""
    limiter = RateLimiter()
    tenant_config = RateLimitConfig(llm_calls_per_minute=20)

    limiter.configure_tenant("tenant-1", tenant_config)

    assert "tenant-1" in limiter._tenant_configs
    assert limiter._tenant_configs["tenant-1"] == tenant_config


def test_rate_limiter_get_tenant_config():
    """Test getting tenant configuration."""
    default_config = RateLimitConfig(llm_calls_per_minute=100)
    limiter = RateLimiter(default_config=default_config)

    # Unconfigured tenant should get default config
    config = limiter.get_tenant_config("tenant-1")
    assert config == default_config

    # Configured tenant should get its own config
    tenant_config = RateLimitConfig(llm_calls_per_minute=50)
    limiter.configure_tenant("tenant-2", tenant_config)
    config = limiter.get_tenant_config("tenant-2")
    assert config == tenant_config


@pytest.mark.asyncio
async def test_rate_limiter_multi_tenant():
    """Test rate limiting for multiple tenants."""
    limiter = RateLimiter(default_config=RateLimitConfig(llm_calls_per_minute=2))

    # Configure custom limit for tenant-1
    limiter.configure_tenant("tenant-1", RateLimitConfig(llm_calls_per_minute=3))

    # Tenant-1 should get 3 calls
    assert await limiter.check_and_consume("tenant-1", ToolType.LLM) is True
    assert await limiter.check_and_consume("tenant-1", ToolType.LLM) is True
    assert await limiter.check_and_consume("tenant-1", ToolType.LLM) is True
    assert await limiter.check_and_consume("tenant-1", ToolType.LLM) is False

    # Tenant-2 (using default) should get 2 calls
    assert await limiter.check_and_consume("tenant-2", ToolType.LLM) is True
    assert await limiter.check_and_consume("tenant-2", ToolType.LLM) is True
    assert await limiter.check_and_consume("tenant-2", ToolType.LLM) is False


@pytest.mark.asyncio
async def test_rate_limiter_lazy_initialization():
    """Test that tenant limiters are created lazily."""
    limiter = RateLimiter()

    # No limiters created initially
    assert len(limiter._tenant_limiters) == 0

    # Make a call for tenant-1
    await limiter.check_and_consume("tenant-1", ToolType.LLM)

    # Now limiter should be created
    assert "tenant-1" in limiter._tenant_limiters


@pytest.mark.asyncio
async def test_rate_limiter_reconfigure_tenant():
    """Test reconfiguring an existing tenant."""
    limiter = RateLimiter()

    # Initial config
    limiter.configure_tenant("tenant-1", RateLimitConfig(llm_calls_per_minute=2))
    await limiter.check_and_consume("tenant-1", ToolType.LLM)
    await limiter.check_and_consume("tenant-1", ToolType.LLM)

    # Reconfigure with higher limit
    limiter.configure_tenant("tenant-1", RateLimitConfig(llm_calls_per_minute=5))

    # Old limiter should be removed, new one should allow more calls
    assert await limiter.check_and_consume("tenant-1", ToolType.LLM) is True


@pytest.mark.asyncio
async def test_tenant_limiter_token_hour_limit():
    """Test hourly token limiting."""
    config = RateLimitConfig(tokens_per_minute=20000, tokens_per_hour=15000)
    limiter = TenantLimiter(config)

    # Consume tokens under minute limit but approaching hour limit
    assert await limiter.check_and_consume(ToolType.LLM, tokens=8000) is True
    assert await limiter.check_and_consume(ToolType.LLM, tokens=6000) is True  # Total: 14000

    # Next 2000 should fail due to hour limit (would exceed 15000)
    assert await limiter.check_and_consume(ToolType.LLM, tokens=2000) is False


@pytest.mark.asyncio
async def test_rate_limiter_isolated_tenants():
    """Test that tenants don't affect each other's limits."""
    limiter = RateLimiter(default_config=RateLimitConfig(llm_calls_per_minute=2))

    # Exhaust tenant-1's limit
    assert await limiter.check_and_consume("tenant-1", ToolType.LLM) is True
    assert await limiter.check_and_consume("tenant-1", ToolType.LLM) is True
    assert await limiter.check_and_consume("tenant-1", ToolType.LLM) is False

    # Tenant-2 should still have full limit available
    assert await limiter.check_and_consume("tenant-2", ToolType.LLM) is True
    assert await limiter.check_and_consume("tenant-2", ToolType.LLM) is True
