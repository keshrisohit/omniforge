"""LLM-powered intent classification for user messages.

Provides asynchronous intent analysis using LiteLLM with structured JSON output,
timeout configuration, and defensive error handling for routing decisions.
"""

import asyncio
import json
import logging
import os
from typing import Any, Optional

import litellm

from omniforge.conversation.context import format_context_for_llm
from omniforge.conversation.models import Message
from omniforge.llm.tracing import setup_opik_tracing
from omniforge.routing.models import ActionType, RoutingDecision

# Setup Opik tracing if configured (via OPIK_API_KEY env var)
setup_opik_tracing()

logger = logging.getLogger(__name__)


class IntentAnalysisError(Exception):
    """Raised when intent analysis fails due to LLM errors, timeout, or invalid response."""

    pass


class LLMIntentAnalyzer:
    """LLM-powered intent analyzer using litellm for structured classification.

    Analyzes user messages to determine intent (action type), confidence level,
    and extracted entities. Uses fast models via OpenRouter with timeout
    guarantees for low-latency responses.

    Attributes:
        model: LLM model identifier (e.g., "openrouter/arcee-ai/trinity-large-preview:free")
        temperature: Sampling temperature for response generation
        max_tokens: Maximum tokens in LLM response
        timeout: Maximum seconds to wait for LLM response
    """

    def __init__(
        self,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 500,
        timeout: Optional[float] = None,
    ) -> None:
        """Initialize LLM intent analyzer with configuration.

        Args:
            model: LLM model name (default: from OMNIFORGE_INTENT_MODEL or "openrouter/arcee-ai/trinity-large-preview:free")
            temperature: Sampling temperature (default: 0.1 for deterministic output)
            max_tokens: Maximum response tokens (default: 500)
            timeout: Timeout in seconds (default: from OMNIFORGE_INTENT_TIMEOUT_SEC or 2.0)
        """
        self.model = model or os.getenv("OMNIFORGE_INTENT_MODEL", "openrouter/arcee-ai/trinity-large-preview:free")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout or float(os.getenv("OMNIFORGE_INTENT_TIMEOUT_SEC", "10.0"))

        # Set up provider credentials from environment
        if "openrouter/" in self.model:
            openrouter_key = os.getenv("OMNIFORGE_OPENROUTER_API_KEY")
            if openrouter_key:
                os.environ["OPENROUTER_API_KEY"] = openrouter_key
        elif "groq/" in self.model:
            groq_key = os.getenv("OMNIFORGE_GROQ_API_KEY")
            if groq_key:
                os.environ["GROQ_API_KEY"] = groq_key

        logger.info(
            f"Initialized LLMIntentAnalyzer: model={self.model}, "
            f"timeout={self.timeout}s, temperature={self.temperature}"
        )

    async def analyze(
        self,
        message: str,
        conversation_history: Optional[list[Message]] = None,
        available_agents: Optional[list[dict[str, Any]]] = None,
    ) -> RoutingDecision:
        """Analyze user message to determine intent and routing decision.

        Args:
            message: Current user message to analyze
            conversation_history: Previous messages for context (optional)
            available_agents: List of available agents with metadata (optional)

        Returns:
            RoutingDecision with action type, confidence, entities, and reasoning

        Raises:
            IntentAnalysisError: If LLM call fails, times out, or returns invalid response
        """
        try:
            # Build system prompt with action types and available agents
            system_prompt = self._build_system_prompt(available_agents)

            # Build message list with history
            messages = self._build_messages(system_prompt, message, conversation_history)

            # Call LLM with timeout
            logger.debug(f"Calling LLM for intent analysis: model={self.model}")
            response = await asyncio.wait_for(self._call_llm(messages), timeout=self.timeout)

            # Parse and validate response
            content = response.choices[0].message.content
            if not content:
                raise IntentAnalysisError("LLM returned empty response")

            decision = self._parse_response(content)
            logger.info(
                f"Intent analysis complete: action={decision.action_type}, "
                f"confidence={decision.confidence:.2f}"
            )
            return decision

        except asyncio.TimeoutError as e:
            logger.error(f"Intent analysis timeout after {self.timeout}s")
            raise IntentAnalysisError(f"Intent analysis timed out after {self.timeout}s") from e
        except IntentAnalysisError:
            raise
        except Exception as e:
            logger.error(f"Intent analysis failed: {e}", exc_info=True)
            raise IntentAnalysisError(f"Intent analysis failed: {e}") from e

    def _build_system_prompt(self, available_agents: Optional[list[dict[str, Any]]]) -> str:
        """Build system prompt describing action types and classification task.

        Args:
            available_agents: List of available agents with metadata (optional)

        Returns:
            System prompt string for LLM
        """
        prompt = """You are an intent classifier for an AI agent platform. \
Analyze user messages and classify them into one of these action types:

1. CREATE_AGENT: User wants to create a new AI agent
   - Examples: "create an agent", "build a bot", "make a new assistant"

2. CREATE_SKILL: User wants to create a brand-new skill (not yet existing)
   - Examples: "create a capability", "build a new skill", "make a skill for X"

3. ADD_SKILL_TO_AGENT: User wants to assign an existing skill to an agent
   - Examples: "add the pdf skill to my agent", "assign skill to agent", "give agent the data-processor skill", "add skill to agent"

4. EXECUTE_TASK: User wants to execute a task, run an agent, or use an existing skill
   - Examples: "run this agent", "execute the task", "process this data", "use the skill", "use it", "invoke skill", "apply this skill"

5. UPDATE_AGENT: User wants to modify an existing agent
   - Examples: "update my agent", "change the configuration", "modify settings"

6. QUERY_INFO: User is asking for information or help
   - Examples: "what can you do?", "list my agents", "show help"

7. MANAGE_PLATFORM: User wants to manage platform settings or resources
   - Examples: "manage users", "configure settings", "view dashboard"

8. UNKNOWN: Cannot determine intent or doesn't fit other categories

Respond with JSON containing:
- "action_type": one of the above types (e.g., "create_agent")
- "confidence": float 0.0-1.0 indicating classification confidence
- "entities": dict of extracted entities (e.g., {"agent_name": "MyBot"})
- "reasoning": brief explanation of your classification
"""

        if available_agents:
            prompt += "\n\nAvailable agents:\n"
            for agent in available_agents:
                agent_id = agent.get("id", "unknown")
                agent_name = agent.get("name", "unknown")
                prompt += f"- {agent_name} (id: {agent_id})\n"

        return prompt

    def _build_messages(
        self,
        system_prompt: str,
        current_message: str,
        history: Optional[list[Message]],
    ) -> list[dict[str, str]]:
        """Build LLM message list with system prompt, history, and current message.

        Args:
            system_prompt: System prompt describing classification task
            current_message: Current user message to classify
            history: Previous conversation messages (optional)

        Returns:
            List of message dicts for LLM API
        """
        messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history if provided
        if history:
            formatted_history = format_context_for_llm(history)
            messages.extend(formatted_history)

        # Add current message
        messages.append({"role": "user", "content": current_message})

        return messages

    async def _call_llm(self, messages: list[dict[str, str]]) -> Any:
        """Call LiteLLM API with structured JSON output.

        Args:
            messages: Message list for LLM API

        Returns:
            LLM API response object

        Raises:
            Exception: If LLM API call fails
        """
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if "openrouter/" in self.model:
            kwargs["api_base"] = "https://openrouter.ai/api/v1"
        return await litellm.acompletion(**kwargs)

    def _parse_response(self, content: str) -> RoutingDecision:
        """Parse and validate LLM JSON response into RoutingDecision.

        Defensively handles:
        - Invalid JSON (raises IntentAnalysisError)
        - Unknown action types (defaults to UNKNOWN)
        - Missing fields (uses defaults)
        - Invalid confidence (clamps to 0.0-1.0)

        Args:
            content: JSON string from LLM response

        Returns:
            Parsed and validated RoutingDecision

        Raises:
            IntentAnalysisError: If JSON is malformed or required fields missing
        """
        # Strip markdown code fences if present (some models wrap JSON in ```json...```)
        stripped = content.strip()
        if stripped.startswith("```"):
            lines = stripped.splitlines()
            # Remove opening fence (```json or ```) and closing fence (```)
            inner = lines[1:] if lines[0].startswith("```") else lines
            if inner and inner[-1].strip() == "```":
                inner = inner[:-1]
            stripped = "\n".join(inner).strip()

        if not stripped:
            raise IntentAnalysisError("LLM returned empty/whitespace response")

        try:
            data = json.loads(stripped)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response: {e}")
            raise IntentAnalysisError(f"Invalid JSON response from LLM: {e}") from e

        # Extract and validate action_type
        action_type_str = data.get("action_type", "unknown")
        try:
            action_type = ActionType(action_type_str.lower())
        except ValueError:
            logger.warning(f"Unknown action type '{action_type_str}', defaulting to UNKNOWN")
            action_type = ActionType.UNKNOWN

        # Extract and clamp confidence
        confidence = data.get("confidence", 0.5)
        if not isinstance(confidence, (int, float)):
            logger.warning(f"Invalid confidence type: {type(confidence)}, using 0.5")
            confidence = 0.5
        confidence = max(0.0, min(1.0, float(confidence)))

        # Extract optional fields
        entities = data.get("entities", {})
        if not isinstance(entities, dict):
            logger.warning(f"Invalid entities type: {type(entities)}, using empty dict")
            entities = {}

        reasoning = data.get("reasoning", "")
        if not isinstance(reasoning, str):
            logger.warning(f"Invalid reasoning type: {type(reasoning)}, using empty string")
            reasoning = ""

        target_agent_id = data.get("target_agent_id")
        if target_agent_id and not isinstance(target_agent_id, str):
            logger.warning(f"Invalid target_agent_id type: {type(target_agent_id)}, ignoring")
            target_agent_id = None

        return RoutingDecision(
            action_type=action_type,
            confidence=confidence,
            target_agent_id=target_agent_id,
            reasoning=reasoning,
            entities=entities,
        )
