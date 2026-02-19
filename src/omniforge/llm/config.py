"""LLM configuration models and utilities.

This module provides configuration management for LLM providers, including
API keys, model defaults, fallbacks, and enterprise governance settings.
"""

import os
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator, model_validator


class ProviderConfig(BaseModel):
    """Configuration for a specific LLM provider.

    Attributes:
        api_key: API key for authentication (sensitive - not logged)
        api_base: Base URL for API endpoint (e.g., custom Azure endpoint)
        api_version: API version (primarily for Azure OpenAI)
        organization: Organization ID (for OpenAI)
    """

    api_key: Optional[str] = Field(default=None, repr=False, description="API key (sensitive)")
    api_base: Optional[str] = Field(default=None, description="Base URL for API endpoint")
    api_version: Optional[str] = Field(default=None, description="API version (Azure)")
    organization: Optional[str] = Field(default=None, description="Organization ID (OpenAI)")

    class Config:
        """Pydantic config."""

        frozen = True  # Immutable after creation


class LLMConfig(BaseModel):
    """Global LLM configuration.

    This configuration controls LLM behavior across the entire platform,
    including model defaults, fallbacks, timeouts, caching, and enterprise
    governance features like approved model lists.

    Attributes:
        default_model: Default model to use (e.g., "claude-sonnet-4")
        fallback_models: List of fallback models if default fails
        timeout_ms: Request timeout in milliseconds
        max_retries: Maximum retry attempts for failed requests
        cache_enabled: Whether to enable response caching
        cache_ttl_seconds: Cache TTL in seconds
        cost_tracking_enabled: Whether to enable cost estimation and tracking
        approved_models: Optional list of approved models (None = all allowed)
        providers: Per-provider configuration (API keys, endpoints, etc.)

    Example:
        >>> config = LLMConfig(
        ...     default_model="claude-sonnet-4",
        ...     fallback_models=["gpt-4", "claude-opus-4"],
        ...     cost_tracking_enabled=True,
        ...     providers={
        ...         "anthropic": ProviderConfig(api_key="sk-ant-..."),
        ...         "openai": ProviderConfig(api_key="sk-...", organization="org-...")
        ...     }
        ... )
    """

    default_model: str = Field(
        default="claude-sonnet-4", description="Default model to use for LLM calls"
    )
    fallback_models: list[str] = Field(
        default_factory=list, description="Fallback models if default fails"
    )
    timeout_ms: int = Field(
        default=120000, ge=1000, le=600000, description="Request timeout (1s-10min)"
    )
    max_retries: int = Field(default=3, ge=0, le=10, description="Max retry attempts")
    cache_enabled: bool = Field(default=True, description="Enable response caching")
    cache_ttl_seconds: int = Field(
        default=3600, ge=0, description="Cache TTL in seconds (0=disabled)"
    )
    cost_tracking_enabled: bool = Field(
        default=False, description="Enable cost estimation and tracking"
    )
    approved_models: Optional[list[str]] = Field(
        default=None, description="Approved models list (None=all allowed)"
    )
    providers: dict[str, ProviderConfig] = Field(
        default_factory=dict, description="Per-provider configuration"
    )

    @field_validator("approved_models")
    @classmethod
    def validate_approved_models(cls, value: Optional[list[str]]) -> Optional[list[str]]:
        """Validate approved models list is not empty if provided.

        Args:
            value: The approved models list to validate

        Returns:
            The validated list

        Raises:
            ValueError: If list is provided but empty
        """
        if value is not None and len(value) == 0:
            raise ValueError("approved_models must be None or non-empty list")
        return value

    @model_validator(mode="after")
    def validate_default_in_approved(self) -> "LLMConfig":
        """Validate default model is in approved list if provided.

        Returns:
            The validated config

        Raises:
            ValueError: If default model not in approved list
        """
        if self.approved_models is not None and self.default_model not in self.approved_models:
            raise ValueError(
                f"default_model '{self.default_model}' must be in approved_models list: "
                f"{self.approved_models}"
            )
        return self

    class Config:
        """Pydantic config."""

        frozen = True  # Immutable after creation


def get_default_config() -> LLMConfig:
    """Get default LLM configuration with sensible defaults.

    This returns a basic configuration suitable for local development
    or testing. For production, use load_config_from_env() to load
    provider credentials from environment variables.

    Returns:
        LLMConfig with default values

    Example:
        >>> config = get_default_config()
        >>> config.default_model
        'openrouter/arcee-ai/trinity-large-preview:free'
        >>> config.timeout_ms
        60000
    """
    return LLMConfig(
        default_model="openrouter/arcee-ai/trinity-large-preview:free",
        fallback_models=[
            "openrouter/google/gemini-2.0-flash-exp:free",
            "openrouter/meta-llama/llama-3.3-70b-instruct",
        ],
        timeout_ms=60000,
        max_retries=3,
        cache_enabled=True,
        cache_ttl_seconds=3600,
        cost_tracking_enabled=False,
        approved_models=None,
        providers={},
    )


def load_config_from_env() -> LLMConfig:
    """Load LLM configuration from environment variables.

    Automatically loads variables from .env file if present in the project root.

    Reads configuration from environment variables with the following patterns:
    - OMNIFORGE_LLM_DEFAULT_MODEL: Default model name
    - OMNIFORGE_LLM_FALLBACK_MODELS: Comma-separated fallback models
    - OMNIFORGE_LLM_TIMEOUT_MS: Request timeout in milliseconds
    - OMNIFORGE_LLM_MAX_RETRIES: Maximum retry attempts
    - OMNIFORGE_LLM_CACHE_ENABLED: Enable caching (true/false)
    - OMNIFORGE_LLM_CACHE_TTL_SECONDS: Cache TTL in seconds
    - OMNIFORGE_LLM_COST_TRACKING_ENABLED: Enable cost tracking (true/false)
    - OMNIFORGE_LLM_APPROVED_MODELS: Comma-separated approved models
    - OMNIFORGE_OPENAI_API_KEY: OpenAI API key
    - OMNIFORGE_OPENAI_ORGANIZATION: OpenAI organization ID
    - OMNIFORGE_ANTHROPIC_API_KEY: Anthropic API key
    - OMNIFORGE_AZURE_OPENAI_API_KEY: Azure OpenAI API key
    - OMNIFORGE_AZURE_OPENAI_API_BASE: Azure OpenAI base URL
    - OMNIFORGE_AZURE_OPENAI_API_VERSION: Azure OpenAI API version
    - OMNIFORGE_GROQ_API_KEY: Groq API key
    - OMNIFORGE_OPENROUTER_API_KEY: OpenRouter API key

    Returns:
        LLMConfig loaded from environment

    Example:
        >>> import os
        >>> os.environ["OMNIFORGE_LLM_DEFAULT_MODEL"] = "gpt-4"
        >>> os.environ["OMNIFORGE_OPENAI_API_KEY"] = "sk-..."
        >>> config = load_config_from_env()
        >>> config.default_model
        'gpt-4'
    """
    # Load environment variables from .env file
    load_dotenv()

    # Load basic settings
    default_model = os.getenv("OMNIFORGE_LLM_DEFAULT_MODEL", "openrouter/arcee-ai/trinity-large-preview:free")

    fallback_models_str = os.getenv("OMNIFORGE_LLM_FALLBACK_MODELS", "")
    fallback_models = (
        [m.strip() for m in fallback_models_str.split(",") if m.strip()]
        if fallback_models_str
        else []
    )

    timeout_ms = int(os.getenv("OMNIFORGE_LLM_TIMEOUT_MS", "60000"))
    max_retries = int(os.getenv("OMNIFORGE_LLM_MAX_RETRIES", "3"))

    cache_enabled_str = os.getenv("OMNIFORGE_LLM_CACHE_ENABLED", "true").lower()
    cache_enabled = cache_enabled_str in ("true", "1", "yes")

    cache_ttl_seconds = int(os.getenv("OMNIFORGE_LLM_CACHE_TTL_SECONDS", "3600"))

    cost_tracking_enabled_str = os.getenv("OMNIFORGE_LLM_COST_TRACKING_ENABLED", "false").lower()
    cost_tracking_enabled = cost_tracking_enabled_str in ("true", "1", "yes")

    approved_models_str = os.getenv("OMNIFORGE_LLM_APPROVED_MODELS", "")
    approved_models = (
        [m.strip() for m in approved_models_str.split(",") if m.strip()]
        if approved_models_str
        else None
    )

    # Load provider configs
    providers: dict[str, ProviderConfig] = {}

    # OpenAI
    openai_key = os.getenv("OMNIFORGE_OPENAI_API_KEY")
    openai_org = os.getenv("OMNIFORGE_OPENAI_ORGANIZATION")
    if openai_key or openai_org:
        providers["openai"] = ProviderConfig(api_key=openai_key, organization=openai_org)

    # Anthropic
    anthropic_key = os.getenv("OMNIFORGE_ANTHROPIC_API_KEY")
    if anthropic_key:
        providers["anthropic"] = ProviderConfig(api_key=anthropic_key)

    # Azure OpenAI
    azure_key = os.getenv("OMNIFORGE_AZURE_OPENAI_API_KEY")
    azure_base = os.getenv("OMNIFORGE_AZURE_OPENAI_API_BASE")
    azure_version = os.getenv("OMNIFORGE_AZURE_OPENAI_API_VERSION")
    if azure_key or azure_base:
        providers["azure"] = ProviderConfig(
            api_key=azure_key, api_base=azure_base, api_version=azure_version
        )

    # Groq
    groq_key = os.getenv("OMNIFORGE_GROQ_API_KEY")
    if groq_key:
        providers["groq"] = ProviderConfig(api_key=groq_key)

    # OpenRouter
    openrouter_key = os.getenv("OMNIFORGE_OPENROUTER_API_KEY")
    if openrouter_key:
        providers["openrouter"] = ProviderConfig(
            api_key=openrouter_key, api_base="https://openrouter.ai/api/v1"
        )

    return LLMConfig(
        default_model=default_model,
        fallback_models=fallback_models,
        timeout_ms=timeout_ms,
        max_retries=max_retries,
        cache_enabled=cache_enabled,
        cache_ttl_seconds=cache_ttl_seconds,
        cost_tracking_enabled=cost_tracking_enabled,
        approved_models=approved_models,
        providers=providers,
    )
