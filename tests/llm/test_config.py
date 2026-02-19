"""Tests for LLM configuration module."""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from omniforge.llm.config import (
    LLMConfig,
    ProviderConfig,
    get_default_config,
    load_config_from_env,
)


def test_provider_config_default_values() -> None:
    """Test ProviderConfig with default values."""
    config = ProviderConfig()

    assert config.api_key is None
    assert config.api_base is None
    assert config.api_version is None
    assert config.organization is None


def test_provider_config_with_values() -> None:
    """Test ProviderConfig with explicit values."""
    config = ProviderConfig(
        api_key="sk-test-123",
        api_base="https://api.example.com",
        api_version="2023-05-15",
        organization="org-test",
    )

    assert config.api_key == "sk-test-123"
    assert config.api_base == "https://api.example.com"
    assert config.api_version == "2023-05-15"
    assert config.organization == "org-test"


def test_provider_config_immutable() -> None:
    """Test that ProviderConfig is immutable."""
    config = ProviderConfig(api_key="sk-test-123")

    with pytest.raises(ValidationError):
        config.api_key = "sk-new-key"  # type: ignore


def test_provider_config_api_key_not_in_repr() -> None:
    """Test that API key is not exposed in repr."""
    config = ProviderConfig(api_key="sk-secret-key")

    repr_str = repr(config)
    assert "sk-secret-key" not in repr_str


def test_llm_config_default_values() -> None:
    """Test LLMConfig with default values."""
    config = LLMConfig()

    assert config.default_model == "claude-sonnet-4"
    assert config.fallback_models == []
    assert config.timeout_ms == 60000
    assert config.max_retries == 3
    assert config.cache_enabled is True
    assert config.cache_ttl_seconds == 3600
    assert config.approved_models is None
    assert config.providers == {}


def test_llm_config_with_custom_values() -> None:
    """Test LLMConfig with custom values."""
    config = LLMConfig(
        default_model="gpt-4",
        fallback_models=["gpt-3.5-turbo", "claude-sonnet-4"],
        timeout_ms=30000,
        max_retries=5,
        cache_enabled=False,
        cache_ttl_seconds=7200,
        approved_models=["gpt-4", "gpt-3.5-turbo", "claude-sonnet-4"],
        providers={
            "openai": ProviderConfig(api_key="sk-openai-key"),
            "anthropic": ProviderConfig(api_key="sk-anthropic-key"),
        },
    )

    assert config.default_model == "gpt-4"
    assert config.fallback_models == ["gpt-3.5-turbo", "claude-sonnet-4"]
    assert config.timeout_ms == 30000
    assert config.max_retries == 5
    assert config.cache_enabled is False
    assert config.cache_ttl_seconds == 7200
    assert config.approved_models == ["gpt-4", "gpt-3.5-turbo", "claude-sonnet-4"]
    assert len(config.providers) == 2


def test_llm_config_timeout_validation() -> None:
    """Test LLMConfig validates timeout bounds."""
    # Too low
    with pytest.raises(ValidationError):
        LLMConfig(timeout_ms=500)

    # Too high
    with pytest.raises(ValidationError):
        LLMConfig(timeout_ms=700000)

    # Valid boundaries
    config_min = LLMConfig(timeout_ms=1000)
    assert config_min.timeout_ms == 1000

    config_max = LLMConfig(timeout_ms=600000)
    assert config_max.timeout_ms == 600000


def test_llm_config_max_retries_validation() -> None:
    """Test LLMConfig validates max_retries bounds."""
    # Below minimum
    with pytest.raises(ValidationError):
        LLMConfig(max_retries=-1)

    # Above maximum
    with pytest.raises(ValidationError):
        LLMConfig(max_retries=11)

    # Valid boundaries
    config_min = LLMConfig(max_retries=0)
    assert config_min.max_retries == 0

    config_max = LLMConfig(max_retries=10)
    assert config_max.max_retries == 10


def test_llm_config_approved_models_empty_list_rejected() -> None:
    """Test LLMConfig rejects empty approved_models list."""
    with pytest.raises(ValidationError) as exc_info:
        LLMConfig(approved_models=[])

    assert "must be None or non-empty list" in str(exc_info.value)


def test_llm_config_approved_models_none_allowed() -> None:
    """Test LLMConfig allows None for approved_models."""
    config = LLMConfig(approved_models=None)
    assert config.approved_models is None


def test_llm_config_default_model_in_approved_list() -> None:
    """Test LLMConfig validates default_model is in approved list."""
    # Valid: default in approved list
    config = LLMConfig(default_model="gpt-4", approved_models=["gpt-4", "claude-sonnet-4"])
    assert config.default_model == "gpt-4"

    # Invalid: default not in approved list
    with pytest.raises(ValidationError) as exc_info:
        LLMConfig(default_model="gpt-3.5-turbo", approved_models=["gpt-4", "claude-sonnet-4"])

    assert "must be in approved_models list" in str(exc_info.value)


def test_llm_config_immutable() -> None:
    """Test that LLMConfig is immutable."""
    config = LLMConfig()

    with pytest.raises(ValidationError):
        config.default_model = "gpt-4"  # type: ignore


def test_get_default_config() -> None:
    """Test get_default_config returns valid defaults."""
    config = get_default_config()

    assert isinstance(config, LLMConfig)
    assert config.default_model == "openrouter/arcee-ai/trinity-large-preview:free"
    assert config.fallback_models == [
        "openrouter/google/gemini-2.0-flash-exp:free",
        "openrouter/meta-llama/llama-3.3-70b-instruct",
    ]
    assert config.timeout_ms == 60000
    assert config.max_retries == 3
    assert config.cache_enabled is True
    assert config.cache_ttl_seconds == 3600
    assert config.cost_tracking_enabled is False
    assert config.approved_models is None
    assert config.providers == {}


def test_load_config_from_env_defaults(monkeypatch) -> None:
    """Test load_config_from_env with no env vars uses defaults."""
    # Clear all relevant env vars
    for key in os.environ.copy():
        if key.startswith("OMNIFORGE_"):
            monkeypatch.delenv(key, raising=False)

    # Mock load_dotenv to prevent loading from .env file
    with patch("omniforge.llm.config.load_dotenv"):
        config = load_config_from_env()

    assert config.default_model == "openrouter/arcee-ai/trinity-large-preview:free"
    assert config.fallback_models == []
    assert config.timeout_ms == 60000
    assert config.max_retries == 3
    assert config.cache_enabled is True
    assert config.cache_ttl_seconds == 3600
    assert config.approved_models is None
    assert config.providers == {}


def test_load_config_from_env_basic_settings(monkeypatch) -> None:
    """Test load_config_from_env loads basic settings."""
    monkeypatch.setenv("OMNIFORGE_LLM_DEFAULT_MODEL", "gpt-4")
    monkeypatch.setenv("OMNIFORGE_LLM_FALLBACK_MODELS", "gpt-3.5-turbo,claude-sonnet-4")
    monkeypatch.setenv("OMNIFORGE_LLM_TIMEOUT_MS", "30000")
    monkeypatch.setenv("OMNIFORGE_LLM_MAX_RETRIES", "5")
    monkeypatch.setenv("OMNIFORGE_LLM_CACHE_ENABLED", "false")
    monkeypatch.setenv("OMNIFORGE_LLM_CACHE_TTL_SECONDS", "7200")

    config = load_config_from_env()

    assert config.default_model == "gpt-4"
    assert config.fallback_models == ["gpt-3.5-turbo", "claude-sonnet-4"]
    assert config.timeout_ms == 30000
    assert config.max_retries == 5
    assert config.cache_enabled is False
    assert config.cache_ttl_seconds == 7200


def test_load_config_from_env_approved_models(monkeypatch) -> None:
    """Test load_config_from_env loads approved models."""
    monkeypatch.setenv("OMNIFORGE_LLM_APPROVED_MODELS", "gpt-4,claude-sonnet-4,gpt-3.5-turbo,openrouter/arcee-ai/trinity-large-preview:free")

    config = load_config_from_env()

    assert config.approved_models == ["gpt-4", "claude-sonnet-4", "gpt-3.5-turbo", "openrouter/arcee-ai/trinity-large-preview:free"]


def test_load_config_from_env_openai_provider(monkeypatch) -> None:
    """Test load_config_from_env loads OpenAI provider config."""
    monkeypatch.setenv("OMNIFORGE_OPENAI_API_KEY", "sk-openai-test-key")
    monkeypatch.setenv("OMNIFORGE_OPENAI_ORGANIZATION", "org-test")

    config = load_config_from_env()

    assert "openai" in config.providers
    assert config.providers["openai"].api_key == "sk-openai-test-key"
    assert config.providers["openai"].organization == "org-test"


def test_load_config_from_env_anthropic_provider(monkeypatch) -> None:
    """Test load_config_from_env loads Anthropic provider config."""
    monkeypatch.setenv("OMNIFORGE_ANTHROPIC_API_KEY", "sk-ant-test-key")

    config = load_config_from_env()

    assert "anthropic" in config.providers
    assert config.providers["anthropic"].api_key == "sk-ant-test-key"


def test_load_config_from_env_azure_provider(monkeypatch) -> None:
    """Test load_config_from_env loads Azure OpenAI provider config."""
    monkeypatch.setenv("OMNIFORGE_AZURE_OPENAI_API_KEY", "azure-test-key")
    monkeypatch.setenv("OMNIFORGE_AZURE_OPENAI_API_BASE", "https://test.openai.azure.com")
    monkeypatch.setenv("OMNIFORGE_AZURE_OPENAI_API_VERSION", "2023-05-15")

    config = load_config_from_env()

    assert "azure" in config.providers
    assert config.providers["azure"].api_key == "azure-test-key"
    assert config.providers["azure"].api_base == "https://test.openai.azure.com"
    assert config.providers["azure"].api_version == "2023-05-15"


def test_load_config_from_env_groq_provider(monkeypatch) -> None:
    """Test load_config_from_env loads Groq provider config."""
    monkeypatch.setenv("OMNIFORGE_GROQ_API_KEY", "gsk-groq-test-key")

    config = load_config_from_env()

    assert "groq" in config.providers
    assert config.providers["groq"].api_key == "gsk-groq-test-key"


def test_load_config_from_env_multiple_providers(monkeypatch) -> None:
    """Test load_config_from_env loads multiple providers."""
    # Clear any existing provider keys that may have been loaded from .env
    monkeypatch.delenv("OMNIFORGE_OPENROUTER_API_KEY", raising=False)

    monkeypatch.setenv("OMNIFORGE_OPENAI_API_KEY", "sk-openai-key")
    monkeypatch.setenv("OMNIFORGE_ANTHROPIC_API_KEY", "sk-ant-key")
    monkeypatch.setenv("OMNIFORGE_AZURE_OPENAI_API_KEY", "azure-key")
    monkeypatch.setenv("OMNIFORGE_GROQ_API_KEY", "gsk-groq-key")

    # Mock load_dotenv to prevent loading from .env file
    with patch("omniforge.llm.config.load_dotenv"):
        config = load_config_from_env()

    assert len(config.providers) == 4
    assert "openai" in config.providers
    assert "anthropic" in config.providers
    assert "azure" in config.providers
    assert "groq" in config.providers


def test_load_config_from_env_cache_enabled_variations(monkeypatch) -> None:
    """Test load_config_from_env handles cache_enabled variations."""
    # Test true values
    for value in ["true", "True", "TRUE", "1", "yes", "Yes"]:
        monkeypatch.setenv("OMNIFORGE_LLM_CACHE_ENABLED", value)
        config = load_config_from_env()
        assert config.cache_enabled is True

    # Test false values
    for value in ["false", "False", "FALSE", "0", "no", "No"]:
        monkeypatch.setenv("OMNIFORGE_LLM_CACHE_ENABLED", value)
        config = load_config_from_env()
        assert config.cache_enabled is False


def test_load_config_from_env_whitespace_handling(monkeypatch) -> None:
    """Test load_config_from_env handles whitespace in lists."""
    monkeypatch.setenv("OMNIFORGE_LLM_DEFAULT_MODEL", "gpt-4")
    monkeypatch.setenv("OMNIFORGE_LLM_FALLBACK_MODELS", " gpt-4 , claude-sonnet-4 , gpt-3.5 ")
    monkeypatch.setenv("OMNIFORGE_LLM_APPROVED_MODELS", " gpt-4 , model-1 , model-2 ")

    config = load_config_from_env()

    assert config.default_model == "gpt-4"
    assert config.fallback_models == ["gpt-4", "claude-sonnet-4", "gpt-3.5"]
    assert config.approved_models == ["gpt-4", "model-1", "model-2"]


def test_load_config_from_env_empty_list_strings(monkeypatch) -> None:
    """Test load_config_from_env handles empty list strings."""
    monkeypatch.setenv("OMNIFORGE_LLM_FALLBACK_MODELS", "")
    monkeypatch.setenv("OMNIFORGE_LLM_APPROVED_MODELS", "")

    config = load_config_from_env()

    assert config.fallback_models == []
    assert config.approved_models is None  # Empty string means None for approved models
