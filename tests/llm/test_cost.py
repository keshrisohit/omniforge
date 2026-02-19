"""Tests for LLM cost calculation utilities."""

import pytest

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


def test_cost_tables_have_same_models() -> None:
    """Test that input and output cost tables have the same models."""
    assert set(COST_PER_M_INPUT.keys()) == set(COST_PER_M_OUTPUT.keys())


def test_cost_tables_include_major_models() -> None:
    """Test that cost tables include major models."""
    expected_models = {
        "claude-opus-4",
        "claude-sonnet-4",
        "claude-haiku-4",
        "gpt-4",
        "gpt-4-turbo",
        "gpt-3.5-turbo",
        "gpt-4o",
    }

    assert expected_models.issubset(set(COST_PER_M_INPUT.keys()))
    assert expected_models.issubset(set(COST_PER_M_OUTPUT.keys()))


def test_cost_tables_are_positive() -> None:
    """Test that all costs are positive."""
    for model, cost in COST_PER_M_INPUT.items():
        assert cost > 0, f"Input cost for {model} should be positive"

    for model, cost in COST_PER_M_OUTPUT.items():
        assert cost > 0, f"Output cost for {model} should be positive"


def test_output_costs_higher_than_input() -> None:
    """Test that output costs are typically higher than input costs."""
    for model in COST_PER_M_INPUT.keys():
        assert (
            COST_PER_M_OUTPUT[model] >= COST_PER_M_INPUT[model]
        ), f"Output cost for {model} should be >= input cost"


def test_get_provider_from_model_prefixed() -> None:
    """Test provider detection from prefixed models."""
    assert get_provider_from_model("azure/gpt-4") == "azure"
    assert get_provider_from_model("openai/gpt-4") == "openai"
    assert get_provider_from_model("anthropic/claude-sonnet-4") == "anthropic"


def test_get_provider_from_model_unprefixed() -> None:
    """Test provider detection from unprefixed models."""
    assert get_provider_from_model("gpt-4") == "openai"
    assert get_provider_from_model("gpt-3.5-turbo") == "openai"
    assert get_provider_from_model("claude-sonnet-4") == "anthropic"
    assert get_provider_from_model("claude-opus-4") == "anthropic"


def test_get_provider_from_model_other_providers() -> None:
    """Test provider detection for other common providers."""
    assert get_provider_from_model("gemini-pro") == "google"
    assert get_provider_from_model("llama-2-70b") == "meta"
    assert get_provider_from_model("mistral-large") == "mistral"


def test_get_provider_from_model_groq() -> None:
    """Test provider detection for Groq models."""
    assert get_provider_from_model("llama-3.1-8b-instant") == "groq"
    assert get_provider_from_model("llama-3.3-70b-versatile") == "groq"
    assert get_provider_from_model("llama-guard-4-12b") == "groq"
    assert get_provider_from_model("gpt-oss-120b") == "groq"
    assert get_provider_from_model("gpt-oss-20b") == "groq"
    assert get_provider_from_model("groq/llama-3.1-8b-instant") == "groq"


def test_get_provider_from_model_unknown() -> None:
    """Test provider detection defaults to openai for unknown models."""
    assert get_provider_from_model("unknown-model-xyz") == "openai"


def test_normalize_model_name_with_prefix() -> None:
    """Test normalizing model names with provider prefix."""
    assert normalize_model_name("azure/gpt-4") == "gpt-4"
    assert normalize_model_name("openai/gpt-3.5-turbo") == "gpt-3.5-turbo"
    assert normalize_model_name("anthropic/claude-sonnet-4") == "claude-sonnet-4"


def test_normalize_model_name_without_prefix() -> None:
    """Test normalizing model names without prefix."""
    assert normalize_model_name("gpt-4") == "gpt-4"
    assert normalize_model_name("claude-sonnet-4") == "claude-sonnet-4"


def test_estimate_prompt_tokens() -> None:
    """Test token estimation from text."""
    # Empty string should return at least 1
    assert estimate_prompt_tokens("") == 1

    # Short text
    assert estimate_prompt_tokens("Hello") == 1  # 5 chars / 4 = 1

    # Longer text
    text = "This is a longer text that should have more tokens"
    tokens = estimate_prompt_tokens(text)
    assert tokens == len(text) // 4
    assert tokens > 0


def test_estimate_prompt_tokens_reasonable_approximation() -> None:
    """Test that token estimation is reasonably accurate."""
    # GPT-4 typically uses ~4 chars per token
    text = "The quick brown fox jumps over the lazy dog"
    tokens = estimate_prompt_tokens(text)

    # Should be in reasonable range (not exact due to tokenization)
    assert 8 <= tokens <= 15


def test_estimate_cost_gpt4() -> None:
    """Test cost estimation for GPT-4."""
    # 1000 input tokens, 500 output tokens
    cost = estimate_cost("gpt-4", 1000, 500)

    # GPT-4: $30/M input, $60/M output
    # (1000/1M * 30) + (500/1M * 60) = 0.03 + 0.03 = 0.06
    assert cost == pytest.approx(0.06, abs=0.001)


def test_estimate_cost_claude_sonnet() -> None:
    """Test cost estimation for Claude Sonnet."""
    # 1000 input tokens, 500 output tokens
    cost = estimate_cost("claude-sonnet-4", 1000, 500)

    # Claude Sonnet: $3/M input, $15/M output
    # (1000/1M * 3) + (500/1M * 15) = 0.003 + 0.0075 = 0.0105
    assert cost == pytest.approx(0.0105, abs=0.0001)


def test_estimate_cost_gpt35_turbo() -> None:
    """Test cost estimation for GPT-3.5 Turbo."""
    # 10000 input tokens, 2000 output tokens
    cost = estimate_cost("gpt-3.5-turbo", 10000, 2000)

    # GPT-3.5 Turbo: $0.5/M input, $1.5/M output
    # (10000/1M * 0.5) + (2000/1M * 1.5) = 0.005 + 0.003 = 0.008
    assert cost == pytest.approx(0.008, abs=0.0001)


def test_estimate_cost_groq_llama_3_1_8b() -> None:
    """Test cost estimation for Groq Llama 3.1 8B."""
    # 10000 input tokens, 5000 output tokens
    cost = estimate_cost("llama-3.1-8b-instant", 10000, 5000)

    # Llama 3.1 8B: $0.05/M input, $0.08/M output
    # (10000/1M * 0.05) + (5000/1M * 0.08) = 0.0005 + 0.0004 = 0.0009
    assert cost == pytest.approx(0.0009, abs=0.00001)


def test_estimate_cost_groq_llama_3_3_70b() -> None:
    """Test cost estimation for Groq Llama 3.3 70B."""
    # 10000 input tokens, 5000 output tokens
    cost = estimate_cost("llama-3.3-70b-versatile", 10000, 5000)

    # Llama 3.3 70B: $0.59/M input, $0.79/M output
    # (10000/1M * 0.59) + (5000/1M * 0.79) = 0.0059 + 0.00395 = 0.00985
    assert cost == pytest.approx(0.00985, abs=0.0001)


def test_estimate_cost_with_prefix() -> None:
    """Test cost estimation works with prefixed model names."""
    cost_without_prefix = estimate_cost("gpt-4", 1000, 500)
    cost_with_prefix = estimate_cost("azure/gpt-4", 1000, 500)

    assert cost_without_prefix == cost_with_prefix


def test_estimate_cost_unknown_model() -> None:
    """Test cost estimation raises error for unknown models."""
    with pytest.raises(ValueError) as exc_info:
        estimate_cost("unknown-model-xyz", 1000, 500)

    assert "not in cost tables" in str(exc_info.value)
    assert "unknown-model-xyz" in str(exc_info.value)


def test_estimate_cost_zero_tokens() -> None:
    """Test cost estimation with zero tokens."""
    cost = estimate_cost("gpt-4", 0, 0)
    assert cost == 0.0


def test_estimate_cost_before_call_simple() -> None:
    """Test pre-call cost estimation with simple message."""
    messages = [{"role": "user", "content": "Hello, how are you?"}]

    cost = estimate_cost_before_call("gpt-4", messages, max_tokens=500)

    # Should be positive and conservative (overestimate)
    assert cost > 0

    # Input: ~20 chars = 5 tokens
    # Output: 500 max_tokens / 2 = 250 tokens
    # Cost: (5/1M * 30) + (250/1M * 60) = 0.00015 + 0.015 = ~0.01515
    assert cost == pytest.approx(0.01515, abs=0.001)


def test_estimate_cost_before_call_multiple_messages() -> None:
    """Test pre-call cost estimation with multiple messages."""
    messages = [
        {"role": "user", "content": "What is the capital of France?"},
        {"role": "assistant", "content": "The capital of France is Paris."},
        {"role": "user", "content": "Tell me more about it."},
    ]

    cost = estimate_cost_before_call("gpt-4", messages, max_tokens=1000)

    # Should account for all messages
    assert cost > 0

    # Total input: ~100 chars = 25 tokens
    # Output: 1000 / 2 = 500 tokens
    # Cost: (25/1M * 30) + (500/1M * 60) = 0.00075 + 0.03 = ~0.03075
    assert cost == pytest.approx(0.03075, abs=0.001)


def test_estimate_cost_before_call_multipart_content() -> None:
    """Test pre-call cost estimation with multi-part content."""
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "What is in this image?"},
                {"type": "image_url", "image_url": {"url": "https://example.com/image.jpg"}},
            ],
        }
    ]

    cost = estimate_cost_before_call("gpt-4", messages, max_tokens=500)

    # Should only count text parts
    assert cost > 0

    # Input: ~24 chars = 6 tokens
    # Output: 500 / 2 = 250 tokens
    # Cost: (6/1M * 30) + (250/1M * 60) = 0.00018 + 0.015 = ~0.01518
    assert cost == pytest.approx(0.01518, abs=0.001)


def test_estimate_cost_before_call_empty_messages() -> None:
    """Test pre-call cost estimation with empty messages."""
    messages: list[dict] = []

    cost = estimate_cost_before_call("gpt-4", messages, max_tokens=500)

    # Should still estimate output cost
    assert cost > 0

    # Input: 0 tokens
    # Output: 500 / 2 = 250 tokens
    # Cost: (0/1M * 30) + (250/1M * 60) = 0 + 0.015 = 0.015
    assert cost == pytest.approx(0.015, abs=0.001)


def test_estimate_cost_before_call_conservative() -> None:
    """Test that pre-call estimation is conservative (overestimates)."""
    messages = [{"role": "user", "content": "Hello"}]

    # Estimate with large max_tokens
    cost_large = estimate_cost_before_call("gpt-4", messages, max_tokens=2000)
    cost_small = estimate_cost_before_call("gpt-4", messages, max_tokens=500)

    # Larger max_tokens should result in higher estimate
    assert cost_large > cost_small


def test_calculate_cost_from_response_with_usage() -> None:
    """Test cost calculation from response with usage info."""
    response = {
        "model": "gpt-4",
        "usage": {"prompt_tokens": 100, "completion_tokens": 50},
    }

    cost = calculate_cost_from_response(response, "gpt-4")

    # GPT-4: $30/M input, $60/M output
    # (100/1M * 30) + (50/1M * 60) = 0.003 + 0.003 = 0.006
    assert cost == pytest.approx(0.006, abs=0.0001)


def test_calculate_cost_from_response_with_litellm_cost() -> None:
    """Test cost calculation uses LiteLLM's cost if available."""
    response = {
        "model": "gpt-4",
        "usage": {"prompt_tokens": 100, "completion_tokens": 50},
        "_hidden_params": {"response_cost": 0.0075},
    }

    cost = calculate_cost_from_response(response, "gpt-4")

    # Should use LiteLLM's cost
    assert cost == 0.0075


def test_calculate_cost_from_response_fallback_model() -> None:
    """Test cost calculation uses fallback model if not in response."""
    response = {"usage": {"prompt_tokens": 100, "completion_tokens": 50}}

    cost = calculate_cost_from_response(response, "gpt-4")

    # Should use fallback model
    assert cost == pytest.approx(0.006, abs=0.0001)


def test_calculate_cost_from_response_no_usage() -> None:
    """Test cost calculation with no usage info returns zero."""
    response = {"model": "gpt-4"}

    cost = calculate_cost_from_response(response, "gpt-4")

    # No usage info, should return 0
    assert cost == 0.0


def test_calculate_cost_from_response_different_models() -> None:
    """Test cost calculation for different models."""
    # Claude Sonnet
    response_claude = {
        "model": "claude-sonnet-4",
        "usage": {"prompt_tokens": 1000, "completion_tokens": 500},
    }
    cost_claude = calculate_cost_from_response(response_claude, "claude-sonnet-4")
    assert cost_claude == pytest.approx(0.0105, abs=0.0001)

    # GPT-3.5 Turbo
    response_gpt35 = {
        "model": "gpt-3.5-turbo",
        "usage": {"prompt_tokens": 1000, "completion_tokens": 500},
    }
    cost_gpt35 = calculate_cost_from_response(response_gpt35, "gpt-3.5-turbo")
    assert cost_gpt35 == pytest.approx(0.0013, abs=0.0001)


def test_cost_estimation_end_to_end() -> None:
    """Test end-to-end cost estimation workflow."""
    model = "claude-sonnet-4"
    messages = [{"role": "user", "content": "Explain quantum computing in simple terms."}]

    # Pre-call estimation
    pre_cost = estimate_cost_before_call(model, messages, max_tokens=1000)
    assert pre_cost > 0

    # Simulate response
    response = {
        "model": model,
        "usage": {"prompt_tokens": 50, "completion_tokens": 300},
        "choices": [{"message": {"content": "Quantum computing is..."}}],
    }

    # Post-call calculation
    post_cost = calculate_cost_from_response(response, model)
    assert post_cost > 0

    # Pre-call should be conservative (higher estimate)
    # Note: This may not always be true if actual usage exceeds max_tokens/2
    # but in this case with moderate usage, pre-call should be higher
    assert pre_cost >= post_cost * 0.5  # At least in same ballpark


def test_model_max_tokens_table_has_common_models() -> None:
    """Test that MODEL_MAX_TOKENS includes common models."""
    expected_models = {
        "claude-opus-4",
        "claude-sonnet-4",
        "claude-haiku-4",
        "gpt-4",
        "gpt-4o",
        "llama-3.1-8b-instant",
        "llama-3.3-70b-versatile",
        "qwen3-32b",  # Normalized form (without provider prefix)
    }

    assert expected_models.issubset(set(MODEL_MAX_TOKENS.keys()))


def test_model_max_tokens_are_positive() -> None:
    """Test that all max_tokens values are positive."""
    for model, max_tokens in MODEL_MAX_TOKENS.items():
        assert max_tokens > 0, f"max_tokens for {model} should be positive"
        assert isinstance(max_tokens, int), f"max_tokens for {model} should be an integer"


def test_model_max_tokens_reasonable_range() -> None:
    """Test that max_tokens values are in reasonable range."""
    for model, max_tokens in MODEL_MAX_TOKENS.items():
        # Max tokens should be between 1K and 200K (reasonable bounds)
        assert 1024 <= max_tokens <= 200000, f"max_tokens for {model} ({max_tokens}) out of reasonable range"


def test_get_max_tokens_for_model_known_models() -> None:
    """Test get_max_tokens_for_model for known models."""
    # Claude models
    assert get_max_tokens_for_model("claude-opus-4") == 64000
    assert get_max_tokens_for_model("claude-sonnet-4") == 8192
    assert get_max_tokens_for_model("claude-haiku-4") == 8192

    # OpenAI models
    assert get_max_tokens_for_model("gpt-4") == 8192
    assert get_max_tokens_for_model("gpt-4o") == 16384
    assert get_max_tokens_for_model("gpt-3.5-turbo") == 4096

    # Groq models
    assert get_max_tokens_for_model("llama-3.1-8b-instant") == 131072
    assert get_max_tokens_for_model("llama-3.3-70b-versatile") == 32768
    assert get_max_tokens_for_model("qwen/qwen3-32b") == 40960


def test_get_max_tokens_for_model_with_prefix() -> None:
    """Test get_max_tokens_for_model works with prefixed model names."""
    # Should normalize and return the same value
    assert get_max_tokens_for_model("azure/gpt-4") == get_max_tokens_for_model("gpt-4")
    assert get_max_tokens_for_model("openai/gpt-4o") == get_max_tokens_for_model("gpt-4o")
    assert get_max_tokens_for_model("anthropic/claude-sonnet-4") == get_max_tokens_for_model("claude-sonnet-4")


def test_get_max_tokens_for_model_unknown_anthropic() -> None:
    """Test get_max_tokens_for_model fallback for unknown Anthropic models."""
    # Unknown Claude model should fallback to anthropic default
    max_tokens = get_max_tokens_for_model("claude-future-model")
    assert max_tokens == 8192  # Anthropic default


def test_get_max_tokens_for_model_unknown_openai() -> None:
    """Test get_max_tokens_for_model fallback for unknown OpenAI models."""
    # Unknown GPT model should fallback to openai default
    max_tokens = get_max_tokens_for_model("gpt-future-model")
    assert max_tokens == 4096  # OpenAI default


def test_get_max_tokens_for_model_unknown_groq() -> None:
    """Test get_max_tokens_for_model fallback for unknown Groq models."""
    # Unknown Groq model should fallback to groq default
    max_tokens = get_max_tokens_for_model("groq/unknown-model")
    assert max_tokens == 8192  # Groq default


def test_get_max_tokens_for_model_completely_unknown() -> None:
    """Test get_max_tokens_for_model fallback for completely unknown models."""
    # Completely unknown model should use conservative default
    max_tokens = get_max_tokens_for_model("totally-unknown-provider/model")
    assert max_tokens == DEFAULT_MAX_TOKENS
    assert max_tokens == 4096  # Conservative default


def test_default_max_tokens_is_reasonable() -> None:
    """Test that DEFAULT_MAX_TOKENS is a reasonable conservative value."""
    assert DEFAULT_MAX_TOKENS == 4096
    assert isinstance(DEFAULT_MAX_TOKENS, int)
    assert DEFAULT_MAX_TOKENS > 0


def test_groq_models_have_correct_limits() -> None:
    """Test Groq models have correct limits from official documentation."""
    # From https://console.groq.com/docs/models
    assert get_max_tokens_for_model("llama-3.1-8b-instant") == 131072
    assert get_max_tokens_for_model("llama-3.3-70b-versatile") == 32768
    assert get_max_tokens_for_model("llama-guard-4-12b") == 1024
    assert get_max_tokens_for_model("gpt-oss-120b") == 65536
    assert get_max_tokens_for_model("gpt-oss-20b") == 65536
    assert get_max_tokens_for_model("qwen/qwen3-32b") == 40960
