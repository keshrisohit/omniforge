# LLM Architecture in OmniForge

This document explains how LLMs (Large Language Models) are called throughout the OmniForge platform.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      Application Layer                       │
│  (Chat Service, CoT Agents, Autonomous Agents)              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    ReasoningEngine                           │
│  • call_llm() - High-level LLM interface                    │
│  • call_tool() - Generic tool execution                     │
│  • Manages reasoning chains and steps                       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    Tool Registry                             │
│  • Maps tool names to tool instances                        │
│  • Provides tool discovery and lookup                       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                      LLMTool                                 │
│  • execute() - Non-streaming LLM calls                      │
│  • execute_streaming() - Streaming LLM calls                │
│  • Cost estimation and tracking                             │
│  • Model approval checking                                  │
│  • Provider configuration                                   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                      LiteLLM                                 │
│  • litellm.acompletion() - Async completion API            │
│  • Provider-agnostic interface                              │
│  • Supports 100+ LLM providers                              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              LLM Providers (OpenAI, Anthropic,              │
│              Azure, Groq, Google, etc.)                     │
└─────────────────────────────────────────────────────────────┘
```

## Call Flow

### 1. High-Level Agent Code

Agents use the `ReasoningEngine.call_llm()` method for simplicity:

```python
# In agent code (e.g., autonomous_simple.py, cot/autonomous.py)
llm_result = await engine.call_llm(
    prompt="Analyze this task and suggest a solution",
    model="claude-sonnet-4",
    temperature=0.7
)
```

**Location**: `src/omniforge/agents/cot/autonomous.py:166`

### 2. ReasoningEngine Layer

The `ReasoningEngine` provides a convenient wrapper that:
- Converts simple prompts to message format
- Applies default model settings
- Routes to the underlying tool system

```python
# src/omniforge/agents/cot/engine.py:174
async def call_llm(
    self,
    prompt: Optional[str] = None,
    messages: Optional[list[dict[str, str]]] = None,
    model: Optional[str] = None,
    system: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    visibility: Optional[VisibilityLevel] = None,
) -> ToolCallResult:
    # Build arguments
    arguments = {
        "model": model or self._default_llm_model,
        "temperature": temperature,
    }

    # Convert prompt to messages
    if prompt is not None:
        arguments["messages"] = [{"role": "user", "content": prompt}]
    else:
        arguments["messages"] = messages

    # Delegate to tool system
    return await self.call_tool("llm", arguments, visibility=visibility)
```

**Location**: `src/omniforge/agents/cot/engine.py:174-226`

### 3. Tool Registry

The tool registry manages tool instances and lookup:

```python
# src/omniforge/tools/setup.py:19-42
def setup_default_tools(registry: ToolRegistry, config: Optional[LLMConfig] = None):
    # Load configuration (from env or provided)
    llm_config = config or load_config_from_env()

    # Create and register LLM tool
    llm_tool = LLMTool(config=llm_config)
    registry.register(llm_tool)

    return registry
```

**Location**: `src/omniforge/tools/setup.py:19-42`

### 4. LLMTool Execution

The `LLMTool` handles the actual LLM interaction:

```python
# src/omniforge/tools/builtin/llm.py:173
async def execute(self, arguments: dict[str, Any], context: ToolCallContext) -> ToolResult:
    import litellm

    start_time = time.time()

    # 1. Resolve model (use default if not specified)
    model = arguments.get("model", self._config.default_model)

    # 2. Check approved models list
    if self._config.approved_models and model not in self._config.approved_models:
        return ToolResult(success=False, error="Model not approved")

    # 3. Build messages from arguments
    messages = self._build_messages(arguments)

    # 4. Get parameters
    temperature = arguments.get("temperature", 0.7)
    max_tokens = arguments.get("max_tokens", 1000)

    # 5. Estimate cost before call (for budget checking)
    estimated_cost = estimate_cost_before_call(model, messages, max_tokens)

    # 6. Check budget constraints
    if hasattr(context, "max_cost_usd") and context.max_cost_usd is not None:
        if estimated_cost > context.max_cost_usd:
            return ToolResult(success=False, error="Cost exceeds budget")

    # 7. Call LiteLLM
    response = await litellm.acompletion(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=self._config.timeout_ms / 1000
    )

    # 8. Extract response and calculate costs
    content = response.choices[0].message.content
    actual_cost = calculate_cost_from_response(response, model)
    usage = response.usage

    # 9. Return structured result
    return ToolResult(
        success=True,
        result={"content": content, "model": model, "provider": provider},
        duration_ms=duration_ms,
        tokens_used=input_tokens + output_tokens,
        cost_usd=actual_cost
    )
```

**Location**: `src/omniforge/tools/builtin/llm.py:173-275`

### 5. LiteLLM Integration

LiteLLM provides the provider-agnostic interface:

```python
# Inside LLMTool._setup_litellm()
import litellm

# Configure API keys for each provider
for provider_name, provider_config in self._config.providers.items():
    if provider_config.api_key:
        env_var = self._get_provider_env_var(provider_name)
        if env_var:
            os.environ[env_var] = provider_config.api_key

# Example: Setting Groq API key
# os.environ["GROQ_API_KEY"] = config.providers["groq"].api_key
```

**Location**: `src/omniforge/tools/builtin/llm.py:66-91`

## Configuration Flow

### Environment Variables → LLMConfig

```python
# Configuration loading
from omniforge.llm.config import load_config_from_env

# Reads environment variables:
# - OMNIFORGE_LLM_DEFAULT_MODEL
# - OMNIFORGE_OPENAI_API_KEY
# - OMNIFORGE_ANTHROPIC_API_KEY
# - OMNIFORGE_GROQ_API_KEY
# - OMNIFORGE_AZURE_OPENAI_API_KEY
# etc.

config = load_config_from_env()
```

**Location**: `src/omniforge/llm/config.py:153-239`

### LLMConfig Structure

```python
@dataclass
class LLMConfig:
    default_model: str = "claude-sonnet-4"
    fallback_models: list[str] = []
    timeout_ms: int = 60000
    max_retries: int = 3
    cache_enabled: bool = True
    cache_ttl_seconds: int = 3600
    approved_models: Optional[list[str]] = None
    providers: dict[str, ProviderConfig] = {}
```

**Location**: `src/omniforge/llm/config.py:34-121`

## Streaming Support

The LLMTool also supports streaming responses:

```python
async def execute_streaming(
    self, arguments: dict[str, Any], context: ToolCallContext
) -> AsyncIterator[dict[str, Any]]:
    # Call LiteLLM with streaming enabled
    response = await litellm.acompletion(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=self._config.timeout_ms / 1000,
        stream=True  # Enable streaming
    )

    # Stream chunks back to caller
    accumulated_content = ""
    async for chunk in response:
        if hasattr(chunk.choices[0], "delta"):
            delta = chunk.choices[0].delta
            if hasattr(delta, "content") and delta.content:
                token = delta.content
                accumulated_content += token

                yield {
                    "token": token,
                    "accumulated": accumulated_content,
                    "output_tokens": output_tokens
                }

    # Yield final result with metadata
    yield {
        "done": True,
        "content": accumulated_content,
        "model": model,
        "cost": actual_cost
    }
```

**Location**: `src/omniforge/tools/builtin/llm.py:277-368`

## Cost Tracking

Cost tracking happens at multiple levels:

### 1. Pre-Call Estimation

```python
from omniforge.llm.cost import estimate_cost_before_call

# Estimate cost before making the call
estimated_cost = estimate_cost_before_call(
    model="llama-3.1-8b-instant",
    messages=[{"role": "user", "content": "Hello"}],
    max_tokens=500
)
```

**Location**: `src/omniforge/llm/cost.py:180-217`

### 2. Post-Call Calculation

```python
from omniforge.llm.cost import calculate_cost_from_response

# Calculate actual cost from response
actual_cost = calculate_cost_from_response(response, model)
```

**Location**: `src/omniforge/llm/cost.py:220-253`

### 3. Provider Detection

```python
from omniforge.llm.cost import get_provider_from_model

# Automatically detect provider
provider = get_provider_from_model("llama-3.1-8b-instant")  # Returns: "groq"
provider = get_provider_from_model("gpt-4")  # Returns: "openai"
provider = get_provider_from_model("claude-sonnet-4")  # Returns: "anthropic"
```

**Location**: `src/omniforge/llm/cost.py:77-119`

## Provider-Specific Configuration

### Groq Example

```bash
# Set Groq API key
export OMNIFORGE_GROQ_API_KEY="gsk-..."
```

```python
# Load configuration
from omniforge.llm.config import load_config_from_env
config = load_config_from_env()

# Use Groq model
result = await engine.call_llm(
    prompt="Analyze this data",
    model="llama-3.1-8b-instant"
)
```

### Multi-Provider Setup

```bash
# Configure multiple providers
export OMNIFORGE_OPENAI_API_KEY="sk-..."
export OMNIFORGE_ANTHROPIC_API_KEY="sk-ant-..."
export OMNIFORGE_GROQ_API_KEY="gsk-..."
```

The LLMTool automatically uses the correct API key based on the model prefix or name.

## Key Design Principles

1. **Abstraction Layers**: Agents don't call LLM APIs directly; they use `ReasoningEngine.call_llm()`
2. **Unified Interface**: All LLM providers accessed through the same `LLMTool` interface
3. **Cost Tracking**: Automatic cost estimation and tracking at every call
4. **Configuration**: Centralized configuration through `LLMConfig` and environment variables
5. **Provider Agnostic**: LiteLLM handles provider-specific details
6. **Enterprise Features**: Approved models, budget limits, governance
7. **Flexibility**: Support for 100+ LLM providers without code changes

## File Reference

| Component | File Path | Key Functions |
|-----------|-----------|---------------|
| ReasoningEngine | `src/omniforge/agents/cot/engine.py` | `call_llm()`, `call_tool()` |
| LLMTool | `src/omniforge/tools/builtin/llm.py` | `execute()`, `execute_streaming()` |
| Config | `src/omniforge/llm/config.py` | `load_config_from_env()`, `LLMConfig` |
| Cost Utils | `src/omniforge/llm/cost.py` | `estimate_cost()`, `calculate_cost_from_response()` |
| Tool Setup | `src/omniforge/tools/setup.py` | `setup_default_tools()`, `get_default_tool_registry()` |

## Example: Complete Call Flow

```python
# 1. Agent makes high-level call
llm_result = await engine.call_llm(
    prompt="What is 2+2?",
    model="llama-3.1-8b-instant"
)

# 2. ReasoningEngine converts to tool call
await self.call_tool("llm", {
    "messages": [{"role": "user", "content": "What is 2+2?"}],
    "model": "llama-3.1-8b-instant",
    "temperature": 0.7
})

# 3. Tool Registry looks up "llm" → LLMTool instance

# 4. LLMTool.execute() processes the request:
#    - Checks approved models
#    - Estimates cost
#    - Validates budget
#    - Calls litellm.acompletion()

# 5. LiteLLM routes to Groq:
response = await litellm.acompletion(
    model="llama-3.1-8b-instant",
    messages=[{"role": "user", "content": "What is 2+2?"}],
    temperature=0.7
)

# 6. LLMTool calculates cost and returns structured result
return ToolResult(
    success=True,
    result={"content": "2+2 equals 4", "model": "llama-3.1-8b-instant"},
    cost_usd=0.000001
)

# 7. ReasoningEngine wraps as ToolCallResult
return ToolCallResult(result, call_step, result_step)

# 8. Agent receives result
print(llm_result.value["content"])  # "2+2 equals 4"
```

## Summary

LLMs in OmniForge are called through a well-structured architecture:
- **High-level API** (`ReasoningEngine.call_llm()`) for agent convenience
- **Tool abstraction** (`LLMTool`) for consistency and governance
- **Provider abstraction** (LiteLLM) for multi-provider support
- **Configuration** (`LLMConfig`) for centralized management
- **Cost tracking** at every level for transparency

This architecture enables flexible, cost-effective, and enterprise-ready LLM integration across the platform.
