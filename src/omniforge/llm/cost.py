"""LLM cost calculation and estimation utilities.

This module provides utilities for estimating and calculating LLM costs across
different providers. It supports pre-call cost estimation for budget checks and
post-call cost calculation for tracking.
"""

from typing import Any

# Cost per 1M tokens (input) in USD
# Updated as of January 2025
COST_PER_M_INPUT: dict[str, float] = {
    # Anthropic Claude models
    "claude-opus-4": 15.0,
    "claude-sonnet-4": 3.0,
    "claude-haiku-4": 0.8,
    "claude-3-opus": 15.0,
    "claude-3-sonnet": 3.0,
    "claude-3-haiku": 0.25,
    # OpenAI GPT-4 models
    "gpt-4": 30.0,
    "gpt-4-turbo": 10.0,
    "gpt-4-turbo-preview": 10.0,
    "gpt-4-0125-preview": 10.0,
    "gpt-4-1106-preview": 10.0,
    "gpt-4o": 5.0,
    "gpt-4o-mini": 0.15,
    # OpenAI GPT-3.5 models
    "gpt-3.5-turbo": 0.5,
    "gpt-3.5-turbo-0125": 0.5,
    "gpt-3.5-turbo-1106": 1.0,
    # OpenAI GPT-4.5 models (hypothetical future pricing)
    "gpt-4.5-turbo": 12.0,
    "gpt-4.5": 35.0,
    # Groq models
    "llama-3.1-8b-instant": 0.05,
    "llama-3.3-70b-versatile": 0.59,
    "llama-guard-4-12b": 0.20,
    "gpt-oss-120b": 0.15,
    "gpt-oss-20b": 0.075,
    "qwen/qwen3-32b": 0.10,
    "qwen3-32b": 0.10,  # Normalized version of qwen/qwen3-32b
}

# Cost per 1M tokens (output) in USD
# Updated as of January 2025
COST_PER_M_OUTPUT: dict[str, float] = {
    # Anthropic Claude models
    "claude-opus-4": 75.0,
    "claude-sonnet-4": 15.0,
    "claude-haiku-4": 4.0,
    "claude-3-opus": 75.0,
    "claude-3-sonnet": 15.0,
    "claude-3-haiku": 1.25,
    # OpenAI GPT-4 models
    "gpt-4": 60.0,
    "gpt-4-turbo": 30.0,
    "gpt-4-turbo-preview": 30.0,
    "gpt-4-0125-preview": 30.0,
    "gpt-4-1106-preview": 30.0,
    "gpt-4o": 15.0,
    "gpt-4o-mini": 0.6,
    # OpenAI GPT-3.5 models
    "gpt-3.5-turbo": 1.5,
    "gpt-3.5-turbo-0125": 1.5,
    "gpt-3.5-turbo-1106": 2.0,
    # OpenAI GPT-4.5 models (hypothetical future pricing)
    "gpt-4.5-turbo": 36.0,
    "gpt-4.5": 105.0,
    # Groq models
    "llama-3.1-8b-instant": 0.08,
    "llama-3.3-70b-versatile": 0.79,
    "llama-guard-4-12b": 0.20,
    "gpt-oss-120b": 0.60,
    "gpt-oss-20b": 0.30,
    "qwen/qwen3-32b": 0.15,
    "qwen3-32b": 0.15,  # Normalized version of qwen/qwen3-32b
}

# Maximum output tokens per model
# Updated as of January 2026 from official documentation
# Sources: https://console.groq.com/docs/models, https://openrouter.ai/api/v1/models
MODEL_MAX_TOKENS: dict[str, int] = {
    # Anthropic Claude models (via OpenRouter API)
    "claude-opus-4": 64000,  # Claude Opus 4.5: 64k max completion
    "claude-sonnet-4": 8192,  # Conservative estimate for Claude Sonnet 4
    "claude-haiku-4": 8192,  # Claude Haiku 4.5: Conservative estimate
    "claude-3-opus": 4096,
    "claude-3-sonnet": 4096,
    "claude-3-haiku": 4096,
    # OpenAI GPT-4 models
    "gpt-4": 8192,
    "gpt-4-turbo": 4096,
    "gpt-4-turbo-preview": 4096,
    "gpt-4-0125-preview": 4096,
    "gpt-4-1106-preview": 4096,
    "gpt-4o": 16384,
    "gpt-4o-mini": 16384,
    # OpenAI GPT-3.5 models
    "gpt-3.5-turbo": 4096,
    "gpt-3.5-turbo-0125": 4096,
    "gpt-3.5-turbo-1106": 4096,
    # OpenAI GPT-4.5/5 models (via OpenRouter)
    "gpt-4.5-turbo": 8192,
    "gpt-4.5": 8192,
    "gpt-5.1": 128000,  # GPT-5.1: 128k max completion
    "gpt-5.2-pro": 128000,  # GPT-5.2 Pro: 128k max completion
    # Groq models (from https://console.groq.com/docs/models)
    "llama-3.1-8b-instant": 131072,  # Llama 3.1 8B: 131,072 max output
    "llama-3.3-70b-versatile": 32768,  # Llama 3.3 70B: 32,768 max output
    "llama-guard-4-12b": 1024,  # Llama Guard 4 12B: 1,024 max output
    "gpt-oss-120b": 65536,  # GPT OSS 120B: 65,536 max output
    "gpt-oss-20b": 65536,  # GPT OSS 20B: 65,536 max output
    "qwen3-32b": 40960,  # Qwen3-32B: 40,960 max output (normalized from qwen/qwen3-32b)
    # Groq Systems
    "compound": 8192,  # Compound: 8,192 max output
    "compound-mini": 8192,  # Compound Mini: 8,192 max output
}

# Default max_tokens for unknown models
DEFAULT_MAX_TOKENS = 4096


def get_provider_from_model(model: str) -> str:
    """Extract provider from model name.

    Args:
        model: Model name, possibly prefixed (e.g., "azure/gpt-4", "gpt-4")

    Returns:
        Provider name ("openai", "anthropic", "azure", "groq", etc.)

    Example:
        >>> get_provider_from_model("gpt-4")
        'openai'
        >>> get_provider_from_model("claude-sonnet-4")
        'anthropic'
        >>> get_provider_from_model("azure/gpt-4")
        'azure'
        >>> get_provider_from_model("llama-3.1-8b-instant")
        'groq'
    """
    # Handle prefixed models (e.g., "azure/gpt-4")
    if "/" in model:
        prefix, _ = model.split("/", 1)
        return prefix.lower()

    # Infer from model name
    model_lower = model.lower()
    if "claude" in model_lower:
        return "anthropic"
    elif "gpt" in model_lower:
        # Check if it's a Groq model (gpt-oss prefix)
        if "gpt-oss" in model_lower:
            return "groq"
        return "openai"
    elif "gemini" in model_lower:
        return "google"
    elif "llama" in model_lower:
        # Llama models on Groq have specific naming patterns
        if any(x in model_lower for x in ["llama-3.1", "llama-3.3", "llama-guard"]):
            return "groq"
        return "meta"
    elif "mistral" in model_lower:
        return "mistral"

    # Default to openai if unknown
    return "openai"


def normalize_model_name(model: str) -> str:
    """Normalize model name by removing provider prefix.

    Args:
        model: Model name, possibly prefixed (e.g., "azure/gpt-4", "gpt-4")

    Returns:
        Normalized model name without prefix

    Example:
        >>> normalize_model_name("azure/gpt-4")
        'gpt-4'
        >>> normalize_model_name("gpt-4")
        'gpt-4'
    """
    if "/" in model:
        _, model_name = model.split("/", 1)
        return model_name
    return model


def get_max_tokens_for_model(model: str) -> int:
    """Get maximum output tokens for a given model.

    Args:
        model: Model name, possibly prefixed (e.g., "azure/gpt-4", "gpt-4")

    Returns:
        Maximum output tokens for the model

    Example:
        >>> get_max_tokens_for_model("claude-sonnet-4")
        8192
        >>> get_max_tokens_for_model("gpt-4o")
        16384
        >>> get_max_tokens_for_model("unknown-model")
        4096
    """
    normalized = normalize_model_name(model)

    # Return model-specific max_tokens if available
    if normalized in MODEL_MAX_TOKENS:
        return MODEL_MAX_TOKENS[normalized]

    # Fallback: try to infer from provider
    provider = get_provider_from_model(model)
    if provider == "anthropic":
        # Default for Claude models
        return 8192
    elif provider == "openai":
        # Default for OpenAI models
        return 4096
    elif provider == "groq":
        # Default for Groq models
        return 8192

    # Conservative default for unknown models
    return DEFAULT_MAX_TOKENS


def estimate_prompt_tokens(text: str) -> int:
    """Estimate token count from text.

    This uses a simple approximation: 1 token ≈ 4 characters.
    For more accurate counting, consider using tiktoken library.

    Args:
        text: Text to estimate tokens for

    Returns:
        Estimated token count

    Example:
        >>> estimate_prompt_tokens("Hello world")
        2
        >>> estimate_prompt_tokens("This is a longer text that should have more tokens")
        13
    """
    return max(1, len(text) // 4)


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate cost for a given model and token counts.

    Args:
        model: Model name (will be normalized)
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens

    Returns:
        Estimated cost in USD

    Raises:
        ValueError: If model is not in cost tables

    Example:
        >>> estimate_cost("gpt-4", 1000, 500)
        0.06
        >>> estimate_cost("claude-sonnet-4", 1000, 500)
        0.01050
    """
    normalized = normalize_model_name(model)

    if normalized not in COST_PER_M_INPUT:
        raise ValueError(
            f"Model '{normalized}' not in cost tables. "
            f"Available models: {', '.join(sorted(COST_PER_M_INPUT.keys()))}"
        )

    input_cost = (input_tokens / 1_000_000) * COST_PER_M_INPUT[normalized]
    output_cost = (output_tokens / 1_000_000) * COST_PER_M_OUTPUT[normalized]

    return input_cost + output_cost


def estimate_cost_before_call(
    model: str, messages: list[dict[str, Any]], max_tokens: int = 1000
) -> float:
    """Estimate cost before making an LLM call.

    This provides a conservative (overestimate) for budget checks.
    Input tokens are estimated from messages, output tokens are
    estimated as max_tokens // 2.

    Args:
        model: Model name
        messages: List of message dictionaries with "content" field
        max_tokens: Maximum output tokens (default: 1000)

    Returns:
        Estimated cost in USD (conservative overestimate)

    Example:
        >>> messages = [{"role": "user", "content": "Hello, how are you?"}]
        >>> estimate_cost_before_call("gpt-4", messages, max_tokens=500)
        0.02325
    """
    # Estimate input tokens from all messages
    input_tokens = 0
    for message in messages:
        content = message.get("content", "")
        if isinstance(content, str):
            input_tokens += estimate_prompt_tokens(content)
        elif isinstance(content, list):
            # Handle multi-part content (text + images)
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    input_tokens += estimate_prompt_tokens(part.get("text", ""))

    # Conservative estimate for output tokens (assume half of max_tokens)
    output_tokens = max(1, max_tokens // 2)

    return estimate_cost(model, input_tokens, output_tokens)


def calculate_cost_from_response(response: dict[str, Any], model: str) -> float:
    """Calculate actual cost from LLM response.

    Attempts to use LiteLLM's completion_cost if available,
    otherwise falls back to estimate_cost with actual token counts.

    Args:
        response: LLM response dictionary (LiteLLM format)
        model: Model name (fallback if not in response)

    Returns:
        Actual cost in USD

    Example:
        >>> response = {
        ...     "usage": {"prompt_tokens": 100, "completion_tokens": 50},
        ...     "model": "gpt-4"
        ... }
        >>> calculate_cost_from_response(response, "gpt-4")
        0.006
    """
    # Try to use LiteLLM's built-in cost calculation
    if "_hidden_params" in response and "response_cost" in response["_hidden_params"]:
        return float(response["_hidden_params"]["response_cost"])

    # Fallback: calculate from token counts
    usage = response.get("usage", {})
    input_tokens = usage.get("prompt_tokens", 0)
    output_tokens = usage.get("completion_tokens", 0)

    # Get model from response or use provided fallback
    response_model = response.get("model", model)

    return estimate_cost(response_model, input_tokens, output_tokens)
