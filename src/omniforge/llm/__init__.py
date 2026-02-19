"""LLM abstraction layer with multi-provider support.

This module provides a unified interface for working with multiple LLM providers
(OpenAI, Anthropic, Azure, etc.) through LiteLLM integration, with built-in
cost tracking, rate limiting, and enterprise governance features.
"""

from omniforge.llm.config import (
    LLMConfig,
    ProviderConfig,
    get_default_config,
    load_config_from_env,
)
from omniforge.llm.cost import (
    COST_PER_M_INPUT,
    COST_PER_M_OUTPUT,
    DEFAULT_MAX_TOKENS,
    MODEL_MAX_TOKENS,
    calculate_cost_from_response,
    estimate_cost,
    estimate_cost_before_call,
    estimate_prompt_tokens,
    get_max_tokens_for_model,
    get_provider_from_model,
    normalize_model_name,
)

__all__ = [
    # Config
    "LLMConfig",
    "ProviderConfig",
    "get_default_config",
    "load_config_from_env",
    # Cost calculation
    "COST_PER_M_INPUT",
    "COST_PER_M_OUTPUT",
    "DEFAULT_MAX_TOKENS",
    "MODEL_MAX_TOKENS",
    "calculate_cost_from_response",
    "estimate_cost",
    "estimate_cost_before_call",
    "estimate_prompt_tokens",
    "get_max_tokens_for_model",
    "get_provider_from_model",
    "normalize_model_name",
]
