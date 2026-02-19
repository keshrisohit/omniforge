# Groq Provider Setup

OmniForge now supports Groq as an LLM provider, enabling fast and cost-effective inference with models like Llama 3.1 and Llama 3.3.

## Supported Models

OmniForge includes built-in cost tracking for the following Groq models:

| Model | Model ID | Input Cost | Output Cost |
|-------|----------|------------|-------------|
| Llama 3.1 8B | `llama-3.1-8b-instant` | $0.05/M tokens | $0.08/M tokens |
| Llama 3.3 70B | `llama-3.3-70b-versatile` | $0.59/M tokens | $0.79/M tokens |
| Llama Guard 4 12B | `llama-guard-4-12b` | $0.20/M tokens | $0.20/M tokens |
| GPT OSS 120B | `gpt-oss-120b` | $0.15/M tokens | $0.60/M tokens |
| GPT OSS 20B | `gpt-oss-20b` | $0.075/M tokens | $0.30/M tokens |

## Configuration

### Environment Variable

Set the Groq API key using the environment variable:

```bash
export OMNIFORGE_GROQ_API_KEY="your-groq-api-key"
```

### Programmatic Configuration

You can also configure Groq programmatically:

```python
from omniforge.llm.config import LLMConfig, ProviderConfig

config = LLMConfig(
    default_model="llama-3.1-8b-instant",
    providers={
        "groq": ProviderConfig(api_key="your-groq-api-key")
    }
)
```

### Loading from Environment

Load configuration from environment variables:

```python
from omniforge.llm.config import load_config_from_env

config = load_config_from_env()
# Automatically loads OMNIFORGE_GROQ_API_KEY if set
```

## Usage Examples

### Basic Usage with LiteLLM

Since OmniForge uses LiteLLM under the hood, you can use Groq models with the standard LiteLLM interface:

```python
import litellm
from omniforge.llm.config import load_config_from_env

# Load config with Groq API key
config = load_config_from_env()

# Set the API key for LiteLLM
if "groq" in config.providers:
    import os
    os.environ["GROQ_API_KEY"] = config.providers["groq"].api_key

# Make a completion request
response = litellm.completion(
    model="groq/llama-3.1-8b-instant",
    messages=[{"role": "user", "content": "Hello, how are you?"}]
)
```

### Cost Estimation

Use OmniForge's cost utilities to estimate and track costs:

```python
from omniforge.llm.cost import estimate_cost, estimate_cost_before_call

# Estimate cost before making a call
messages = [{"role": "user", "content": "Explain quantum computing"}]
estimated_cost = estimate_cost_before_call(
    "llama-3.1-8b-instant",
    messages,
    max_tokens=500
)
print(f"Estimated cost: ${estimated_cost:.6f}")

# Calculate actual cost after call
actual_cost = estimate_cost("llama-3.1-8b-instant", input_tokens=100, output_tokens=200)
print(f"Actual cost: ${actual_cost:.6f}")
```

### Provider Detection

OmniForge automatically detects the provider from model names:

```python
from omniforge.llm.cost import get_provider_from_model

provider = get_provider_from_model("llama-3.1-8b-instant")
print(provider)  # Output: "groq"

provider = get_provider_from_model("groq/llama-3.3-70b-versatile")
print(provider)  # Output: "groq"
```

## Multi-Provider Setup

You can configure multiple providers simultaneously:

```bash
export OMNIFORGE_OPENAI_API_KEY="sk-..."
export OMNIFORGE_ANTHROPIC_API_KEY="sk-ant-..."
export OMNIFORGE_GROQ_API_KEY="gsk-..."
```

Then load all providers at once:

```python
from omniforge.llm.config import load_config_from_env

config = load_config_from_env()
print(f"Configured providers: {list(config.providers.keys())}")
# Output: ['openai', 'anthropic', 'groq']
```

## Best Practices

1. **Cost Optimization**: Groq offers some of the most cost-effective inference. Use `llama-3.1-8b-instant` for simple tasks to minimize costs.

2. **Performance**: Groq is optimized for speed. Consider using it for latency-sensitive applications.

3. **Model Selection**:
   - Use `llama-3.1-8b-instant` for quick, cost-effective responses
   - Use `llama-3.3-70b-versatile` for more complex reasoning tasks
   - Use `llama-guard-4-12b` for content moderation

4. **API Key Security**: Store your Groq API key securely using environment variables or a secrets manager. Never commit API keys to version control.

## Getting a Groq API Key

1. Sign up at [console.groq.com](https://console.groq.com)
2. Navigate to the API Keys section
3. Create a new API key
4. Copy and store it securely

## Troubleshooting

### API Key Not Found

If you see an error about missing API keys:

```python
# Verify your environment variable is set
import os
print(os.getenv("OMNIFORGE_GROQ_API_KEY"))  # Should not be None
```

### Model Not Found in Cost Tables

If you're using a newer Groq model not in the cost tables, you'll get an error. You can:

1. Use the model with LiteLLM directly (costs won't be tracked by OmniForge)
2. Add the model to `src/omniforge/llm/cost.py` with its pricing

### Provider Detection Issues

If the provider isn't detected correctly:

```python
# Use explicit provider prefix
response = litellm.completion(
    model="groq/your-model-name",
    messages=[...]
)
```

## References

- [Groq Official Documentation](https://console.groq.com/docs)
- [Groq Pricing](https://groq.com/pricing)
- [LiteLLM Groq Integration](https://docs.litellm.ai/docs/providers/groq)
