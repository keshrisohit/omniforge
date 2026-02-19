"""LLM-powered response generator for chat interactions.

This module provides a real LLM-based response generator using litellm
to support multiple LLM providers including OpenRouter, OpenAI, Anthropic, etc.
"""

import os
import warnings
from typing import Any, AsyncIterator, Optional

import litellm
import tiktoken

from omniforge.llm.config import load_config_from_env
from omniforge.llm.cost import get_max_tokens_for_model
from omniforge.llm.tracing import setup_opik_tracing

# Suppress Pydantic serialization warnings from litellm
# These are internal litellm issues that don't affect functionality
warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    message=".*Pydantic serializer warnings.*",
)

# Setup Opik tracing if configured (via OPIK_API_KEY env var)
setup_opik_tracing()


class LLMResponseGenerator:
    """Generates chat responses using real LLM providers via litellm.

    This generator supports multiple LLM providers through litellm, including:
    - OpenRouter (various models)
    - OpenAI (GPT models)
    - Anthropic (Claude models)
    - Groq (open source models)
    - And many more

    Attributes:
        model: The LLM model to use (e.g., "openrouter/liquid/lfm-2.5-1.2b-instruct:free")
        api_key: API key for the provider
        api_base: Optional custom API base URL
        temperature: Sampling temperature (0.0-1.0)
        max_tokens: Maximum tokens to generate (model-specific default)
    """

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> None:
        """Initialize the LLM response generator.

        Args:
            model: Model name (defaults to config or "openrouter/liquid/lfm-2.5-1.2b-instruct:free")
            api_key: API key (defaults to env var OMNIFORGE_OPENROUTER_API_KEY)
            api_base: API base URL (defaults to OpenRouter base)
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate (defaults to model-specific limit)
        """
        # Load config from environment
        config = load_config_from_env()

        # Set model (priority: parameter > env config > default cheap model)
        self.model = model or config.default_model

        # Store fallback models and config for retry logic
        self.fallback_models = config.fallback_models
        self.config = config

        # Determine provider from model and set API key
        if "groq/" in self.model:
            self.api_key = api_key or os.getenv("OMNIFORGE_GROQ_API_KEY")
            self.api_base = None  # Groq uses default endpoint
            # Set environment variable for litellm
            if self.api_key:
                os.environ["GROQ_API_KEY"] = self.api_key
        elif "openrouter/" in self.model:
            self.api_key = api_key or os.getenv("OMNIFORGE_OPENROUTER_API_KEY")
            self.api_base = api_base or "https://openrouter.ai/api/v1"
            # Set environment variable for litellm
            if self.api_key:
                os.environ["OPENROUTER_API_KEY"] = self.api_key
        elif "openai/" in self.model or self.model.startswith("gpt-"):
            self.api_key = api_key or os.getenv("OMNIFORGE_OPENAI_API_KEY")
            self.api_base = api_base
            # Set environment variable for litellm
            if self.api_key:
                os.environ["OPENAI_API_KEY"] = self.api_key
        elif "anthropic/" in self.model or self.model.startswith("claude-"):
            self.api_key = api_key or os.getenv("OMNIFORGE_ANTHROPIC_API_KEY")
            self.api_base = api_base
            # Set environment variable for litellm
            if self.api_key:
                os.environ["ANTHROPIC_API_KEY"] = self.api_key
        else:
            # Generic fallback
            self.api_key = api_key or os.getenv("OMNIFORGE_OPENROUTER_API_KEY") or os.getenv("OMNIFORGE_GROQ_API_KEY")
            self.api_base = api_base or "https://openrouter.ai/api/v1"

        # Set generation parameters
        self.temperature = temperature
        # Use model-specific max_tokens if not provided
        self.max_tokens = max_tokens if max_tokens is not None else get_max_tokens_for_model(self.model)

        # Configure litellm for OpenRouter
        if not self.api_key:
            raise ValueError(
                "No API key found. Please set OMNIFORGE_OPENROUTER_API_KEY, "
                "OMNIFORGE_GROQ_API_KEY, or OMNIFORGE_OPENAI_API_KEY in your .env file"
            )

    async def _is_transient_error(self, error: Exception) -> bool:
        """Check if an error is transient and should trigger fallback.

        Args:
            error: The exception to check

        Returns:
            True if error is transient (rate limit, timeout, server error)
        """
        error_str = str(error).lower()

        # Rate limit errors
        if any(pattern in error_str for pattern in [
            "rate limit", "ratelimit", "too many requests", "429"
        ]):
            return True

        # Server errors (5xx)
        if any(pattern in error_str for pattern in [
            "500", "502", "503", "504", "server error", "internal server error"
        ]):
            return True

        # Network/timeout errors
        if any(pattern in error_str for pattern in [
            "timeout", "timed out", "connection", "network"
        ]):
            return True

        return False

    async def _execute_streaming_with_fallback(
        self,
        messages: list[dict[str, str]],
        primary_model: str,
    ) -> AsyncIterator[str]:
        """Execute streaming LLM call with intelligent fallback.

        Tries models in this order:
        1. Primary model (from instance config)
        2. All configured fallback models
        3. Free OpenRouter model (only if no OpenRouter in fallbacks)

        On transient errors (rate limits, timeouts, server errors),
        tries next model with reduced max_tokens (30% reduction).

        Args:
            messages: Messages to send
            primary_model: Primary model to try first

        Yields:
            Response chunks as they arrive

        Raises:
            Exception: If all models fail or non-transient error occurs
        """
        # Build list of models to try
        models_to_try = [primary_model]

        # Add ALL configured fallback models (not just 2)
        if self.fallback_models:
            models_to_try.extend(self.fallback_models)

        # Add free OpenRouter model as final fallback only if:
        # 1. API key is configured
        # 2. No OpenRouter models already in the list
        if self.config.providers.get("openrouter"):
            # Check if any OpenRouter model is already in the list
            has_openrouter = any("openrouter/" in model for model in models_to_try)
            if not has_openrouter:
                # Only add free model if user hasn't configured any OpenRouter models
                openrouter_fallback = "openrouter/qwen/qwen-2.5-72b-instruct"
                models_to_try.append(openrouter_fallback)

        current_max_tokens = self.max_tokens
        last_error = None

        for attempt_model in models_to_try:
            try:
                # Build kwargs for streaming completion
                kwargs = {
                    "model": attempt_model,
                    "messages": messages,
                    "temperature": self.temperature,
                    "max_tokens": current_max_tokens,
                    "stream": True,
                }

                # Determine if we need api_base for this model
                if "openrouter/" in attempt_model:
                    kwargs["api_base"] = "https://openrouter.ai/api/v1"
                elif "groq/" not in attempt_model and "anthropic/" not in attempt_model:
                    # Only add api_base for non-standard providers
                    if self.api_base:
                        kwargs["api_base"] = self.api_base

                # Try this model
                response = await litellm.acompletion(**kwargs)

                # Stream chunks as they arrive
                async for chunk in response:
                    # Extract content from chunk
                    if hasattr(chunk, "choices") and len(chunk.choices) > 0:
                        delta = chunk.choices[0].delta
                        if hasattr(delta, "content") and delta.content:
                            yield delta.content

                # Success - exit the loop
                return

            except Exception as e:
                last_error = e

                # Check if it's a transient error
                is_transient = await self._is_transient_error(e)

                if is_transient:
                    # Reduce max_tokens by 30% for next attempt
                    current_max_tokens = int(current_max_tokens * 0.7)

                    # Log the fallback attempt
                    print(f"Transient error with {attempt_model}: {str(e)}")

                    # Try next model if available
                    if attempt_model != models_to_try[-1]:
                        print(f"Falling back to next model (max_tokens reduced to {current_max_tokens})")
                        continue
                    else:
                        # Last model also failed with transient error
                        raise Exception(
                            f"All models failed with transient errors. Last error: {str(last_error)}"
                        )
                else:
                    # Non-transient error - try fallback models anyway
                    print(f"Non-transient error with {attempt_model}: {str(e)}")

                    if attempt_model == models_to_try[0]:
                        # Primary model failed - try fallbacks
                        if len(models_to_try) > 1:
                            print(f"Trying fallback models...")
                            continue
                        else:
                            # No fallbacks available
                            raise
                    else:
                        # Fallback model also failed - try next one
                        if attempt_model != models_to_try[-1]:
                            continue
                        else:
                            # All models exhausted
                            raise

        # All models exhausted
        if last_error:
            raise last_error

    async def generate_stream(self, message: str) -> AsyncIterator[str]:
        """Generate a streaming response to the user's message using LLM.

        This method includes comprehensive retry/fallback logic:
        - Automatically retries on transient errors (rate limits, timeouts, server errors)
        - Falls back to alternative models from config
        - Reduces max_tokens on rate limits to increase success rate
        - Provides detailed error messages if all attempts fail

        Args:
            message: The user's input message

        Yields:
            Response parts as strings to be formatted as SSE chunks

        Examples:
            >>> generator = LLMResponseGenerator()
            >>> async for chunk in generator.generate_stream("Hello"):
            ...     print(chunk)
            Hello!
            How can
            I help
            you today?
        """
        try:
            # Prepare messages for LLM
            messages = [
                {
                    "role": "system",
                    "content": "You are a helpful AI assistant. Provide clear, concise, and accurate responses.",
                },
                {"role": "user", "content": message},
            ]

            # Execute with fallback logic
            async for chunk in self._execute_streaming_with_fallback(messages, self.model):
                yield chunk

        except Exception as e:
            # Yield error message if all LLM attempts fail
            error_msg = f"Error generating response: {str(e)}"
            print(f"LLM Error (all models failed): {error_msg}")
            yield f"I apologize, but I encountered an error after trying multiple models: {str(e)}"

    def count_tokens(self, text: str) -> int:
        """Count tokens in the given text using tiktoken.

        This uses the cl100k_base encoding which is used by GPT-3.5/GPT-4.
        It's a reasonable approximation for most modern LLMs.

        Args:
            text: The text to count tokens for

        Returns:
            Token count

        Examples:
            >>> generator = LLMResponseGenerator()
            >>> generator.count_tokens("Hello, world!")
            4
        """
        try:
            # Use cl100k_base encoding (GPT-3.5/GPT-4)
            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
        except Exception:
            # Fallback to simple approximation if tiktoken fails
            return max(1, len(text) // 4)

    async def _execute_with_tools_fallback(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        primary_model: str,
    ) -> dict[str, Any]:
        """Execute non-streaming LLM call with tools and intelligent fallback.

        Args:
            messages: Messages to send (with system if needed)
            tools: Tool definitions
            primary_model: Primary model to try first

        Returns:
            Response dict with 'content' and optional 'tool_calls'

        Raises:
            Exception: If all models fail or non-transient error occurs
        """
        # Build list of models to try
        models_to_try = [primary_model]

        # Add ALL configured fallback models (not just 2)
        if self.fallback_models:
            models_to_try.extend(self.fallback_models)

        # Add free OpenRouter model as final fallback only if:
        # 1. API key is configured
        # 2. No OpenRouter models already in the list
        if self.config.providers.get("openrouter"):
            # Check if any OpenRouter model is already in the list
            has_openrouter = any("openrouter/" in model for model in models_to_try)
            if not has_openrouter:
                # Only add free model if user hasn't configured any OpenRouter models
                openrouter_fallback = "openrouter/qwen/qwen-2.5-72b-instruct"
                models_to_try.append(openrouter_fallback)

        current_max_tokens = self.max_tokens
        last_error = None

        for attempt_model in models_to_try:
            try:
                # Build kwargs for completion
                kwargs = {
                    "model": attempt_model,
                    "messages": messages,
                    "tools": tools,
                    "tool_choice": "auto",
                    "temperature": self.temperature,
                    "max_tokens": current_max_tokens,
                    "stream": False,
                }

                # Determine if we need api_base for this model
                if "openrouter/" in attempt_model:
                    kwargs["api_base"] = "https://openrouter.ai/api/v1"
                elif "groq/" not in attempt_model and "anthropic/" not in attempt_model:
                    # Only add api_base for non-standard providers
                    if self.api_base:
                        kwargs["api_base"] = self.api_base

                # Try this model
                response = await litellm.acompletion(**kwargs)

                # Parse response
                message = response.choices[0].message

                result = {
                    "content": message.content or "",
                    "tool_calls": None
                }

                # Check for tool calls
                if hasattr(message, 'tool_calls') and message.tool_calls:
                    result["tool_calls"] = []
                    for tc in message.tool_calls:
                        result["tool_calls"].append({
                            "id": tc.id,
                            "name": tc.function.name,
                            "arguments": eval(tc.function.arguments) if isinstance(tc.function.arguments, str) else tc.function.arguments
                        })

                return result

            except Exception as e:
                last_error = e

                # Check if it's a transient error
                is_transient = await self._is_transient_error(e)

                if is_transient:
                    # Reduce max_tokens by 30% for next attempt
                    current_max_tokens = int(current_max_tokens * 0.7)

                    # Log the fallback attempt
                    print(f"Transient error with {attempt_model} (tools): {str(e)}")

                    # Try next model if available
                    if attempt_model != models_to_try[-1]:
                        print(f"Falling back to next model (max_tokens reduced to {current_max_tokens})")
                        continue
                    else:
                        # Last model also failed with transient error
                        raise Exception(
                            f"All models failed with transient errors. Last error: {str(last_error)}"
                        )
                else:
                    # Non-transient error - try fallback models anyway
                    print(f"Non-transient error with {attempt_model} (tools): {str(e)}")

                    if attempt_model == models_to_try[0]:
                        # Primary model failed - try fallbacks
                        if len(models_to_try) > 1:
                            print(f"Trying fallback models...")
                            continue
                        else:
                            # No fallbacks available
                            raise
                    else:
                        # Fallback model also failed - try next one
                        if attempt_model != models_to_try[-1]:
                            continue
                        else:
                            # All models exhausted
                            raise

        # All models exhausted
        if last_error:
            raise last_error

        # Shouldn't reach here, but return error if we do
        return {
            "content": "Error: All models exhausted",
            "tool_calls": None
        }

    async def generate_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        system: Optional[str] = None,
    ) -> dict[str, Any]:
        """Generate response with native tool-use support.

        This method includes comprehensive retry/fallback logic:
        - Automatically retries on transient errors (rate limits, timeouts, server errors)
        - Falls back to alternative models from config
        - Reduces max_tokens on rate limits to increase success rate

        Args:
            messages: Conversation history
            tools: Tool definitions in OpenAI/Claude format
            system: Optional system message

        Returns:
            Response dict with 'content' and optional 'tool_calls'
        """
        try:
            # Build messages with system if provided
            full_messages = []
            if system:
                full_messages.append({"role": "system", "content": system})
            full_messages.extend(messages)

            # Execute with fallback logic
            return await self._execute_with_tools_fallback(full_messages, tools, self.model)

        except Exception as e:
            # Return error as text response if all attempts fail
            print(f"LLM Error (all models failed, tools): {str(e)}")
            return {
                "content": f"Error after trying multiple models: {str(e)}",
                "tool_calls": None
            }
