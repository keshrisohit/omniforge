"""Example: Using OpenRouter provider with OmniForge.

This example demonstrates how to:
1. Configure OpenRouter as an LLM provider
2. Use various models through OpenRouter (Claude, GPT-4, Llama, etc.)
3. Estimate costs before making requests
4. Track actual costs after requests

Prerequisites:
- Set OMNIFORGE_OPENROUTER_API_KEY environment variable
- Install dependencies: pip install litellm

OpenRouter provides access to multiple LLM providers through a single API.
Model format: openrouter/provider/model-name
Examples:
  - openrouter/arcee-ai/trinity-large-preview:free
  - openrouter/openai/gpt-4-turbo
  - openrouter/meta-llama/llama-3.1-70b-instruct
  - openrouter/google/gemini-pro
"""

from omniforge.llm.config import load_config_from_env
from omniforge.llm.cost import (
    estimate_cost_before_call,
    calculate_cost_from_response,
    get_provider_from_model,
)


def main() -> None:
    """Demonstrate OpenRouter provider usage with OmniForge."""
    # Load configuration from environment
    config = load_config_from_env()

    # Check if OpenRouter is configured
    if "openrouter" not in config.providers:
        print("Error: OMNIFORGE_OPENROUTER_API_KEY environment variable not set")
        print("Please set it with: export OMNIFORGE_OPENROUTER_API_KEY='your-api-key'")
        print("\nGet your API key from: https://openrouter.ai/keys")
        return

    print("✓ OpenRouter provider configured")
    print(f"Configured providers: {list(config.providers.keys())}")

    # Example models available through OpenRouter
    # Note: For cost estimation, use normalized model names without the full OpenRouter path
    # When making actual API calls, you'll use the full openrouter/<provider>/<model> format
    example_models = [
        "claude-sonnet-4",  # Anthropic Claude Sonnet
        "gpt-4-turbo",      # OpenAI GPT-4 Turbo
        "gpt-4o",           # OpenAI GPT-4o
        "claude-haiku-4",   # Anthropic Claude Haiku (fastest/cheapest)
    ]

    messages = [{"role": "user", "content": "What is the capital of France?"}]

    print("\n=== Cost Estimation for Different Models ===")
    for model in example_models:
        estimated_cost = estimate_cost_before_call(model, messages, max_tokens=100)
        provider = get_provider_from_model(model)

        print(f"\nModel: {model}")
        print(f"  Provider: {provider}")
        print(f"  Estimated cost: ${estimated_cost:.6f}")

    print("\n=== Usage Example ===")
    print("To use OpenRouter in your code:")
    print("""
from omniforge.llm.config import load_config_from_env
import litellm

config = load_config_from_env()

# For actual API calls, use the full OpenRouter model path:
response = litellm.completion(
    model="openrouter/arcee-ai/trinity-large-preview:free",
    messages=[{"role": "user", "content": "Hello!"}],
    api_key=config.providers["openrouter"].api_key,
    api_base=config.providers["openrouter"].api_base
)

# For cost estimation, use normalized model names (e.g., "claude-sonnet-4", "gpt-4-turbo")
# The cost tables use standardized model names regardless of provider
    """)


if __name__ == "__main__":
    # Quick configuration check
    from omniforge.llm.config import load_config_from_env

    config = load_config_from_env()
    if "openrouter" in config.providers:
        print("✓ OpenRouter provider configured successfully!")
        print(f"  API Base: {config.providers['openrouter'].api_base}")
        print(f"  Available providers: {list(config.providers.keys())}")
        print("\nRun main() to see cost estimates for different models.")
    else:
        print("⚠ OpenRouter provider not configured.")
        print("Set OMNIFORGE_OPENROUTER_API_KEY environment variable.")
        print("Get your API key from: https://openrouter.ai/keys")
