"""LLM tool providing unified access to 100+ LLM providers via LiteLLM.

This is the core tool for agent reasoning, supporting streaming, cost tracking,
and enterprise governance features.
"""

import os
import time
import warnings
from typing import Any, AsyncIterator, Optional

# Suppress Pydantic serialization warnings from litellm
# These are internal litellm issues that don't affect functionality
warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    message=".*Pydantic serializer warnings.*",
)

from omniforge.llm.config import LLMConfig, get_default_config
from omniforge.llm.cost import (
    calculate_cost_from_response,
    estimate_cost_before_call,
    get_max_tokens_for_model,
    get_provider_from_model,
)
from omniforge.llm.tracing import setup_opik_tracing
from omniforge.tools.base import (
    ParameterType,
    StreamingTool,
    ToolCallContext,
    ToolDefinition,
    ToolParameter,
    ToolPermissions,
    ToolResult,
    ToolRetryConfig,
    ToolVisibilityConfig,
)
from omniforge.tools.types import ToolType


class LLMTool(StreamingTool):
    """Tool for making LLM calls through unified interface.

    Provides access to 100+ LLM providers via LiteLLM with features:
    - Multi-provider support (OpenAI, Anthropic, Azure, etc.)
    - Cost tracking and budget enforcement
    - Approved models whitelist
    - Streaming support
    - Automatic fallback to alternative models
    - Provider-agnostic interface

    Example:
        >>> tool = LLMTool()
        >>> context = ToolCallContext(
        ...     correlation_id="corr-1",
        ...     task_id="task-1",
        ...     agent_id="agent-1"
        ... )
        >>> result = await tool.execute(
        ...     arguments={"prompt": "What is 2+2?"},
        ...     context=context
        ... )
        >>> result.result["content"]
        "2+2 equals 4."
    """

    def __init__(self, config: Optional[LLMConfig] = None):
        """Initialize LLM tool.

        Args:
            config: Optional LLM configuration. If not provided, uses default config.
        """
        self._config = config or get_default_config()
        self._setup_litellm()

    def _setup_litellm(self) -> None:
        """Configure LiteLLM with API keys and settings."""
        import litellm

        # Disable LiteLLM's internal retries (we handle retries in executor)
        litellm.num_retries = 0

        # Set API keys from config
        for provider_name, provider_config in self._config.providers.items():
            if provider_config.api_key:
                # Map provider names to LiteLLM environment variables
                env_var = self._get_provider_env_var(provider_name)
                if env_var:
                    os.environ[env_var] = provider_config.api_key

            # Set API base for custom endpoints (e.g., Azure)
            if provider_config.api_base:
                if provider_name == "azure":
                    os.environ["AZURE_API_BASE"] = provider_config.api_base
                    if provider_config.api_version:
                        os.environ["AZURE_API_VERSION"] = provider_config.api_version

            # Set organization for OpenAI
            if provider_config.organization and provider_name == "openai":
                os.environ["OPENAI_ORGANIZATION"] = provider_config.organization

        # Setup Opik tracing if configured (via OPIK_API_KEY env var)
        setup_opik_tracing()

    def _get_provider_env_var(self, provider_name: str) -> Optional[str]:
        """Get environment variable name for provider API key.

        Args:
            provider_name: Provider name (e.g., "openai", "anthropic")

        Returns:
            Environment variable name or None if unknown
        """
        mapping = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "azure": "AZURE_API_KEY",
            "google": "GOOGLE_API_KEY",
            "cohere": "COHERE_API_KEY",
            "huggingface": "HUGGINGFACE_API_KEY",
            "groq": "GROQ_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
        }
        return mapping.get(provider_name.lower())

    @property
    def definition(self) -> ToolDefinition:
        """Get tool definition."""
        return ToolDefinition(
            name="llm",
            type=ToolType.LLM,
            description="Make LLM calls for reasoning, generation, and analysis",
            parameters=[
                ToolParameter(
                    name="prompt",
                    type=ParameterType.STRING,
                    description="Simple text prompt (converted to user message)",
                    required=False,
                ),
                ToolParameter(
                    name="messages",
                    type=ParameterType.ARRAY,
                    description="Structured messages array (role + content)",
                    required=False,
                ),
                ToolParameter(
                    name="model",
                    type=ParameterType.STRING,
                    description=f"Model to use (default: {self._config.default_model})",
                    required=False,
                ),
                ToolParameter(
                    name="system",
                    type=ParameterType.STRING,
                    description="System prompt for model behavior",
                    required=False,
                ),
                ToolParameter(
                    name="temperature",
                    type=ParameterType.FLOAT,
                    description="Sampling temperature 0.0-2.0 (default: 0.7)",
                    required=False,
                ),
                ToolParameter(
                    name="max_tokens",
                    type=ParameterType.INTEGER,
                    description="Maximum tokens to generate (default: model-specific)",
                    required=False,
                ),
                ToolParameter(
                    name="stream",
                    type=ParameterType.BOOLEAN,
                    description="Enable streaming (default: false)",
                    required=False,
                ),
                ToolParameter(
                    name="response_format",
                    type=ParameterType.OBJECT,
                    description="Response format specification (e.g., {'type': 'json_object'} for JSON mode)",
                    required=False,
                ),
            ],
            returns={"description": "LLM response with content, usage, and cost"},
            timeout_ms=self._config.timeout_ms,
            retry_config=ToolRetryConfig(
                max_retries=self._config.max_retries,
                retry_on_status_codes=[429, 500, 502, 503, 504],
                exponential_backoff=True,
            ),
            visibility=ToolVisibilityConfig(),
            permissions=ToolPermissions(),
        )

    async def execute(self, context: ToolCallContext, arguments: dict[str, Any]) -> ToolResult:
        """Execute LLM call.

        Args:
            context: Execution context
            arguments: Tool arguments (prompt/messages, model, temperature, etc.)

        Returns:
            ToolResult with response content, usage stats, and cost
        """
        import litellm

        start_time = time.time()

        # Resolve model
        model = arguments.get("model", self._config.default_model)

        # Check approved models
        if self._config.approved_models and model not in self._config.approved_models:
            return ToolResult(
                success=False,
                error=f"Model '{model}' is not in approved models list: "
                f"{', '.join(self._config.approved_models)}",
                duration_ms=int((time.time() - start_time) * 1000),
            )

        # Build messages
        messages = self._build_messages(arguments)
        if not messages:
            return ToolResult(
                success=False,
                error="Either 'prompt' or 'messages' is required",
                duration_ms=int((time.time() - start_time) * 1000),
            )

        # Get parameters
        temperature = arguments.get("temperature", 0.7)
        # Get model-specific max_tokens default
        max_tokens = arguments.get("max_tokens", get_max_tokens_for_model(model))
        response_format = arguments.get("response_format")

        # Estimate cost before call for budget checking (only if enabled)
        estimated_cost = 0.0
        if self._config.cost_tracking_enabled:
            estimated_cost = estimate_cost_before_call(model, messages, max_tokens)

            # Check budget if context has one
            if hasattr(context, "max_cost_usd") and context.max_cost_usd is not None:
                if estimated_cost > context.max_cost_usd:
                    return ToolResult(
                        success=False,
                        error=f"Estimated cost ${estimated_cost:.4f} exceeds budget "
                        f"${context.max_cost_usd:.4f}",
                        duration_ms=int((time.time() - start_time) * 1000),
                    )

        # Try primary model, then fallbacks on rate limit
        try:
            response = await self._execute_with_rate_limit_fallback(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format=response_format,
                start_time=start_time,
            )

            if response is None:
                # All attempts failed due to rate limits
                duration_ms = int((time.time() - start_time) * 1000)
                return ToolResult(
                    success=False,
                    error="LLM call failed: All models (including fallbacks) are rate limited",
                    duration_ms=duration_ms,
                )
        except Exception as e:
            # Handle any errors from fallback attempts
            duration_ms = int((time.time() - start_time) * 1000)
            return ToolResult(
                success=False,
                error=f"LLM call failed: {str(e)}",
                duration_ms=duration_ms,
            )

        try:

            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)

            # Extract response content
            content = response.choices[0].message.content

            # Calculate actual cost (only if enabled)
            actual_cost = 0.0
            if self._config.cost_tracking_enabled:
                # Convert response to dict for cost calculation
                # (litellm returns ModelResponse object, not dict)
                response_dict = response.model_dump() if hasattr(response, "model_dump") else dict(response)
                actual_cost = calculate_cost_from_response(response_dict, model)

            # Extract usage
            usage = response.usage
            input_tokens = usage.prompt_tokens if usage else 0
            output_tokens = usage.completion_tokens if usage else 0

            # Get provider
            provider = get_provider_from_model(model)

            return ToolResult(
                success=True,
                result={
                    "content": content,
                    "model": model,
                    "provider": provider,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
                duration_ms=duration_ms,
                tokens_used=input_tokens + output_tokens,
                cost_usd=actual_cost,
            )

        except Exception as e:
            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)

            # Return error result
            return ToolResult(
                success=False,
                error=f"LLM call failed: {str(e)}",
                duration_ms=duration_ms,
            )

    async def execute_streaming(
        self, arguments: dict[str, Any], context: ToolCallContext
    ) -> AsyncIterator[dict[str, Any]]:
        """Execute LLM call with streaming.

        Args:
            arguments: Tool arguments (prompt/messages, model, temperature, etc.)
            context: Execution context

        Yields:
            Incremental result chunks with tokens and metadata
        """
        import litellm

        # Resolve model
        model = arguments.get("model", self._config.default_model)

        # Check approved models
        if self._config.approved_models and model not in self._config.approved_models:
            yield {
                "error": f"Model '{model}' is not in approved models list: "
                f"{', '.join(self._config.approved_models)}"
            }
            return

        # Build messages
        messages = self._build_messages(arguments)
        if not messages:
            yield {"error": "Either 'prompt' or 'messages' is required"}
            return

        # Get parameters
        temperature = arguments.get("temperature", 0.7)
        # Get model-specific max_tokens default
        max_tokens = arguments.get("max_tokens", get_max_tokens_for_model(model))

        try:
            # Call LiteLLM with streaming
            response = await litellm.acompletion(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=self._config.timeout_ms / 1000,
                stream=True,
            )

            # Track accumulated content and tokens
            accumulated_content = ""
            input_tokens = 0
            output_tokens = 0

            # Stream chunks
            async for chunk in response:
                if hasattr(chunk.choices[0], "delta"):
                    delta = chunk.choices[0].delta
                    if hasattr(delta, "content") and delta.content:
                        token = delta.content
                        accumulated_content += token
                        output_tokens += 1

                        yield {
                            "token": token,
                            "accumulated": accumulated_content,
                            "output_tokens": output_tokens,
                        }

            # Yield final result with full metadata
            provider = get_provider_from_model(model)

            # Estimate input tokens from messages
            input_tokens = sum(
                len(msg.get("content", "")) // 4 for msg in messages if "content" in msg
            )

            # Calculate cost from actual usage (only if enabled)
            actual_cost = 0.0
            if self._config.cost_tracking_enabled:
                actual_cost = (input_tokens + output_tokens) * 0.00001  # Rough estimate

            yield {
                "done": True,
                "content": accumulated_content,
                "model": model,
                "provider": provider,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "cost": actual_cost,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

        except Exception as e:
            yield {"error": f"LLM streaming failed: {str(e)}", "model": model}

    async def _execute_with_rate_limit_fallback(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
        response_format: Optional[dict],
        start_time: float,
    ) -> Optional[Any]:
        """Execute LLM call with intelligent rate limit fallback.

        Tries models in this order:
        1. Primary model (from arguments)
        2. Fallback models from config (1-2 models)
        3. OpenRouter as final fallback

        On rate limit errors, reduces max_tokens by 30% for next attempt.

        Args:
            model: Primary model to try
            messages: Messages to send
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            response_format: Optional response format
            start_time: Start time for duration tracking

        Returns:
            LiteLLM response object, or None if all attempts failed
        """
        import litellm

        # Build list of models to try
        models_to_try = [model]

        # Add configured fallback models (limit to 2)
        if self._config.fallback_models:
            models_to_try.extend(self._config.fallback_models[:2])

        # Add OpenRouter as final fallback only if API key is configured
        if self._config.providers.get("openrouter"):
            openrouter_fallback = "openrouter/qwen/qwen-2.5-72b-instruct"
            if openrouter_fallback not in models_to_try:
                models_to_try.append(openrouter_fallback)

        current_max_tokens = max_tokens
        last_error = None

        for attempt_model in models_to_try:
            try:
                # Build kwargs for LiteLLM
                completion_kwargs = {
                    "model": attempt_model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": current_max_tokens,
                    "timeout": self._config.timeout_ms / 1000,
                }

                # Add response_format if provided
                if response_format:
                    completion_kwargs["response_format"] = response_format

                # Try this model
                response = await litellm.acompletion(**completion_kwargs)
                return response

            except Exception as e:
                last_error = e
                error_str = str(e).lower()

                # Check if it's a rate limit error
                is_rate_limit = any(
                    pattern in error_str
                    for pattern in ["rate limit", "ratelimit", "too many requests", "429"]
                )

                if is_rate_limit:
                    # Reduce max_tokens by 30% for next attempt
                    current_max_tokens = int(current_max_tokens * 0.7)

                    # Try next model if available
                    if attempt_model != models_to_try[-1]:
                        continue
                    else:
                        # Last model also rate limited
                        return None
                else:
                    # Non-rate-limit error on first model, raise immediately
                    if attempt_model == models_to_try[0]:
                        raise
                    # Non-rate-limit error on fallback, try next model
                    continue

        # All models exhausted
        if last_error:
            raise last_error
        return None

    def _build_messages(self, arguments: dict[str, Any]) -> list[dict[str, str]]:
        """Build messages array from arguments.

        Args:
            arguments: Tool arguments with prompt or messages

        Returns:
            Messages array in OpenAI format
        """
        # Use provided messages if available
        if "messages" in arguments:
            messages = arguments["messages"].copy()

            # Check if system prompt is provided and not already in messages
            if "system" in arguments:
                # Check if first message is already a system message
                if not messages or messages[0].get("role") != "system":
                    # Prepend system message
                    messages.insert(0, {"role": "system", "content": arguments["system"]})

            return messages

        # Build from prompt
        if "prompt" in arguments:
            messages = []

            # Add system message if provided
            if "system" in arguments:
                messages.append({"role": "system", "content": arguments["system"]})

            # Add user message
            messages.append({"role": "user", "content": arguments["prompt"]})

            return messages

        return []
