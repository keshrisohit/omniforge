# TASK-301: Implement LLM Configuration Module

## Description

Create the configuration system for LLM providers. This handles model defaults, provider settings, API keys, and approved model lists for enterprise governance.

## Requirements

- Create `ProviderConfig` model:
  - api_key: Optional[str]
  - api_base: Optional[str]
  - api_version: Optional[str] (for Azure)
  - organization: Optional[str] (for OpenAI)
- Create `LLMConfig` model:
  - default_model: str = "claude-sonnet-4"
  - fallback_models: list[str] = []
  - timeout_ms: int = 60000
  - max_retries: int = 3
  - cache_enabled: bool = True
  - cache_ttl_seconds: int = 3600
  - approved_models: Optional[list[str]] = None (None = all allowed)
  - providers: dict[str, ProviderConfig]
- Create configuration utilities:
  - `get_default_config()` function returning LLMConfig
  - `load_config_from_env()` to load from environment variables
  - Environment variable patterns:
    - OMNIFORGE_LLM_DEFAULT_MODEL
    - OMNIFORGE_OPENAI_API_KEY
    - OMNIFORGE_ANTHROPIC_API_KEY
    - etc.

## Acceptance Criteria

- [ ] LLMConfig validates all fields correctly
- [ ] Default config has sensible values
- [ ] Config loads from environment variables
- [ ] Provider configs stored per-provider
- [ ] Approved models list is optional (None = no restrictions)
- [ ] Unit tests cover config validation and loading

## Dependencies

- None (foundational for LLM module)

## Files to Create/Modify

- `src/omniforge/llm/__init__.py` (new)
- `src/omniforge/llm/config.py` (new)
- `tests/llm/__init__.py` (new)
- `tests/llm/test_config.py` (new)

## Estimated Complexity

Simple (2-3 hours)

## Key Considerations

- Sensitive data (API keys) should never be logged
- Consider dotenv support for local development
- Config should be immutable after creation
