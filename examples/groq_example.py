"""Example: Using Groq provider with OmniForge.

This example demonstrates how to:
1. Configure Groq as an LLM provider
2. Estimate costs before making requests
3. Use Groq models with LiteLLM
4. Track actual costs after requests

Prerequisites:
- Set OMNIFORGE_GROQ_API_KEY environment variable
- Install dependencies: pip install litellm
"""

import os
from omniforge.llm.config import load_config_from_env
from omniforge.llm.cost import (
    estimate_cost_before_call,
    calculate_cost_from_response,
    get_provider_from_model,
)


def main() -> None:
    """Demonstrate Groq provider usage with OmniForge."""
    # Load configuration from environment
    config = load_config_from_env()

    # Check if Groq is configured
    if "groq" not in config.providers:
        print("Error: OMNIFORGE_GROQ_API_KEY environment variable not set")
        print("Please set it with: export OMNIFORGE_GROQ_API_KEY='your-api-key'")
        return

    print("✓ Groq provider configured")
    print(f"Configured providers: {list(config.providers.keys())}")

    # Example: Cost estimation
    model = "llama-3.1-8b-instant"
    messages = [
        {"role": "user", "content": "What is the capital of France?"}
    ]

    # Pre-call cost estimation
    from omniforge.llm.cost import estimate_cost_before_call, get_provider_from_model

    estimated_cost = estimate_cost_before_call(model, messages, max_tokens=100)
    provider = get_provider_from_model(model)

    print(f"Model: {model}")
    print(f"Provider: {provider}")
    print(f"Estimated cost: ${estimated_cost:.6f}")


if __name__ == "__main__":
    # Example usage
    from omniforge.llm.config import load_config_from_env

    config = load_config_from_env()
    if "groq" in config.providers:
        print("✓ Groq provider configured successfully!")
        print(f"  Available providers: {list(config.providers.keys())}")
    else:
        print("⚠ Groq provider not configured. Set OMNIFORGE_GROQ_API_KEY environment variable.")
