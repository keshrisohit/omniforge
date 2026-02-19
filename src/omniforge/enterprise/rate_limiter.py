"""Rate limiting system for enterprise quotas.

This module provides rate limiting for tool calls, tokens, and costs per tenant,
ensuring fair resource allocation and preventing abuse in multi-tenant deployments.
"""

import time
from dataclasses import dataclass
from typing import Dict, Optional

from aiolimiter import AsyncLimiter

from omniforge.tools.types import ToolType


@dataclass
class RateLimitConfig:
    """Rate limit configuration for a tenant.

    Attributes:
        llm_calls_per_minute: Maximum LLM tool calls per minute
        external_calls_per_minute: Maximum external API calls per minute
        database_calls_per_minute: Maximum database calls per minute
        tokens_per_minute: Maximum tokens per minute
        tokens_per_hour: Maximum tokens per hour
        cost_per_hour_usd: Maximum cost in USD per hour
        cost_per_day_usd: Maximum cost in USD per day
    """

    llm_calls_per_minute: int = 100
    external_calls_per_minute: int = 200
    database_calls_per_minute: int = 300
    tokens_per_minute: int = 100000
    tokens_per_hour: int = 1000000
    cost_per_hour_usd: float = 10.0
    cost_per_day_usd: float = 100.0


class TenantLimiter:
    """Rate limiter for a single tenant.

    Manages rate limits for tool calls, tokens, and costs using sliding windows
    and async limiters for efficient enforcement.

    Example:
        >>> config = RateLimitConfig(
        ...     llm_calls_per_minute=50,
        ...     tokens_per_minute=50000,
        ...     cost_per_hour_usd=5.0
        ... )
        >>> limiter = TenantLimiter(config)
        >>> allowed = await limiter.check_and_consume(
        ...     tool_type=ToolType.LLM,
        ...     tokens=100,
        ...     cost_usd=0.01
        ... )
    """

    def __init__(self, config: RateLimitConfig):
        """Initialize tenant limiter with configuration.

        Args:
            config: Rate limit configuration
        """
        self.config = config

        # Create async limiters for each limit type
        self._llm_limiter = AsyncLimiter(
            max_rate=config.llm_calls_per_minute, time_period=60.0
        )
        self._external_limiter = AsyncLimiter(
            max_rate=config.external_calls_per_minute, time_period=60.0
        )
        self._database_limiter = AsyncLimiter(
            max_rate=config.database_calls_per_minute, time_period=60.0
        )
        self._token_minute_limiter = AsyncLimiter(
            max_rate=config.tokens_per_minute, time_period=60.0
        )
        self._token_hour_limiter = AsyncLimiter(
            max_rate=config.tokens_per_hour, time_period=3600.0
        )

        # Cost tracking with sliding windows
        self._hourly_cost = 0.0
        self._daily_cost = 0.0
        self._hour_window_start = time.time()
        self._day_window_start = time.time()

    async def check_and_consume(
        self,
        tool_type: ToolType,
        tokens: int = 0,
        cost_usd: float = 0.0,
    ) -> bool:
        """Check rate limits and consume if allowed.

        Args:
            tool_type: Type of tool being called
            tokens: Number of tokens to consume
            cost_usd: Cost in USD to consume

        Returns:
            True if allowed and consumed, False if rate limit exceeded
        """
        # Reset windows if needed
        self._reset_windows_if_needed()

        # Check cost limits first (fail fast)
        if cost_usd > 0:
            if self._hourly_cost + cost_usd > self.config.cost_per_hour_usd:
                return False
            if self._daily_cost + cost_usd > self.config.cost_per_day_usd:
                return False

        # Check token limits
        if tokens > 0:
            # Check both minute and hour limits
            if not self._token_minute_limiter.has_capacity(tokens):
                return False
            if not self._token_hour_limiter.has_capacity(tokens):
                return False

        # Check tool-specific limits
        limiter = self._get_limiter(tool_type)
        if limiter and not limiter.has_capacity(1):
            return False

        # All checks passed - consume the resources
        if tokens > 0:
            await self._token_minute_limiter.acquire(tokens)
            await self._token_hour_limiter.acquire(tokens)

        if limiter:
            await limiter.acquire(1)

        if cost_usd > 0:
            self._hourly_cost += cost_usd
            self._daily_cost += cost_usd

        return True

    def _get_limiter(self, tool_type: ToolType) -> Optional[AsyncLimiter]:
        """Get the appropriate limiter for a tool type.

        Args:
            tool_type: Type of tool

        Returns:
            AsyncLimiter for the tool type, or None if no specific limiter
        """
        if tool_type == ToolType.LLM:
            return self._llm_limiter
        elif tool_type == ToolType.API:
            return self._external_limiter
        elif tool_type == ToolType.DATABASE:
            return self._database_limiter
        # No specific limiter for other types
        return None

    def _reset_windows_if_needed(self) -> None:
        """Reset cost tracking windows if time periods have elapsed."""
        current_time = time.time()

        # Reset hourly window (1 hour = 3600 seconds)
        if current_time - self._hour_window_start >= 3600:
            self._hourly_cost = 0.0
            self._hour_window_start = current_time

        # Reset daily window (1 day = 86400 seconds)
        if current_time - self._day_window_start >= 86400:
            self._daily_cost = 0.0
            self._day_window_start = current_time


class RateLimiter:
    """Multi-tenant rate limiter.

    Manages rate limiters for multiple tenants with per-tenant configuration
    and lazy initialization.

    Example:
        >>> default_config = RateLimitConfig(llm_calls_per_minute=100)
        >>> limiter = RateLimiter(default_config=default_config)
        >>> limiter.configure_tenant("tenant-1", RateLimitConfig(llm_calls_per_minute=50))
        >>> allowed = await limiter.check_and_consume(
        ...     tenant_id="tenant-1",
        ...     tool_type=ToolType.LLM,
        ...     tokens=100,
        ...     cost_usd=0.01
        ... )
    """

    def __init__(self, default_config: Optional[RateLimitConfig] = None):
        """Initialize multi-tenant rate limiter.

        Args:
            default_config: Default configuration for unconfigured tenants
        """
        self._default_config = default_config or RateLimitConfig()
        self._tenant_configs: Dict[str, RateLimitConfig] = {}
        self._tenant_limiters: Dict[str, TenantLimiter] = {}

    def configure_tenant(self, tenant_id: str, config: RateLimitConfig) -> None:
        """Configure rate limits for a specific tenant.

        Args:
            tenant_id: Unique tenant identifier
            config: Rate limit configuration for this tenant
        """
        self._tenant_configs[tenant_id] = config
        # Remove existing limiter to force recreation with new config
        if tenant_id in self._tenant_limiters:
            del self._tenant_limiters[tenant_id]

    async def check_and_consume(
        self,
        tenant_id: str,
        tool_type: ToolType,
        tokens: int = 0,
        cost_usd: float = 0.0,
    ) -> bool:
        """Check rate limits for a tenant and consume if allowed.

        Args:
            tenant_id: Unique tenant identifier
            tool_type: Type of tool being called
            tokens: Number of tokens to consume
            cost_usd: Cost in USD to consume

        Returns:
            True if allowed and consumed, False if rate limit exceeded
        """
        # Get or create tenant limiter
        if tenant_id not in self._tenant_limiters:
            config = self._tenant_configs.get(tenant_id, self._default_config)
            self._tenant_limiters[tenant_id] = TenantLimiter(config)

        limiter = self._tenant_limiters[tenant_id]
        return await limiter.check_and_consume(tool_type, tokens, cost_usd)

    def get_tenant_config(self, tenant_id: str) -> RateLimitConfig:
        """Get the configuration for a tenant.

        Args:
            tenant_id: Unique tenant identifier

        Returns:
            Rate limit configuration for the tenant
        """
        return self._tenant_configs.get(tenant_id, self._default_config)
