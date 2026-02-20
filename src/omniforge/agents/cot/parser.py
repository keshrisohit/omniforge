"""ReAct response parser for extracting structured actions from LLM responses.

This module provides parsing capabilities for the ReAct (Reasoning + Acting) format,
enabling agents to extract thoughts, actions, and final answers from LLM outputs.
The parser expects JSON-formatted responses from the LLM.
"""

import json
from dataclasses import dataclass
from typing import Optional


@dataclass
class ParsedResponse:
    """Structured representation of a parsed ReAct response.

    Attributes:
        thought: The reasoning/thinking content from the LLM
        is_final: Whether this response contains a final answer
        final_answer: The final response text (if is_final=True)
        action: The tool name to call (if not final)
        action_input: Arguments for the tool as a parsed dictionary
        is_clarification: Whether this response asks the user for more info
        clarification_question: The question to ask the user (if is_clarification=True)
    """

    thought: Optional[str] = None
    is_final: bool = False
    final_answer: Optional[str] = None
    action: Optional[str] = None
    action_input: Optional[dict] = None
    is_clarification: bool = False
    clarification_question: Optional[str] = None


class ReActParser:
    """Parser for JSON-formatted ReAct LLM responses.

    The ReAct format expects JSON responses in one of two formats:

    Format 1 - Action (calling a tool):
    {
      "thought": "reasoning about what to do next",
      "action": "tool_name",
      "action_input": {"arg": "value"},
      "is_final": false
    }

    Format 2 - Final Answer:
    {
      "thought": "final reasoning",
      "final_answer": "response to user",
      "is_final": true
    }

    The parser handles:
    - Valid JSON responses with all required fields
    - Missing optional fields (thought, action_input)
    - Malformed JSON without raising exceptions
    - JSON with extra whitespace or markdown code blocks
    - Legacy text-based format for backward compatibility
    """

    @classmethod
    def parse(cls, response: str) -> ParsedResponse:
        """Parse a JSON-formatted ReAct response into structured components.

        Args:
            response: The LLM response string to parse (should be JSON)

        Returns:
            ParsedResponse containing extracted fields. Handles missing fields
            and malformed JSON gracefully by returning None for those fields.

        Examples:
            >>> response = '''
            ... {
            ...   "thought": "I need to search for information",
            ...   "action": "search",
            ...   "action_input": {"query": "weather"},
            ...   "is_final": false
            ... }
            ... '''
            >>> parsed = ReActParser.parse(response)
            >>> parsed.thought
            'I need to search for information'
            >>> parsed.action
            'search'
        """
        parsed = ParsedResponse()

        # Clean up response - remove markdown code blocks if present
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]  # Remove ```json
        if response.startswith("```"):
            response = response[3:]  # Remove ```
        if response.endswith("```"):
            response = response[:-3]  # Remove trailing ```
        response = response.strip()

        # Try to extract JSON if there's text before it
        # Look for the first { and last } to extract JSON block
        json_start = response.find("{")
        json_end = response.rfind("}")
        if json_start != -1 and json_end != -1 and json_end > json_start:
            response = response[json_start : json_end + 1]

        try:
            # Parse JSON response
            data = json.loads(response)

            # Extract thought (optional)
            if "thought" in data and data["thought"]:
                parsed.thought = str(data["thought"]).strip()

            # Extract is_final flag (required, defaults to False)
            parsed.is_final = bool(data.get("is_final", False))

            # Handle final answer
            if parsed.is_final:
                if "final_answer" in data and data["final_answer"]:
                    parsed.final_answer = str(data["final_answer"]).strip()
                return parsed

            # Handle clarification request
            if "clarification_question" in data and data["clarification_question"]:
                parsed.is_clarification = True
                parsed.clarification_question = str(data["clarification_question"]).strip()
                return parsed

            # Handle action (for non-final responses)
            if "action" in data and data["action"]:
                parsed.action = str(data["action"]).strip()

            # Extract action_input (optional, must be dict)
            if "action_input" in data:
                action_input = data["action_input"]
                if isinstance(action_input, dict):
                    parsed.action_input = action_input
                elif isinstance(action_input, list):
                    # Wrap array in dict for consistent handling
                    parsed.action_input = {"items": action_input}
                elif action_input is not None:
                    # Wrap other types in dict
                    parsed.action_input = {"value": action_input}

        except (json.JSONDecodeError, ValueError, TypeError, KeyError) as exc:
            # Malformed JSON — store a diagnostic in thought only when there was
            # actual content (empty/whitespace responses are handled by the caller)
            if response.strip():
                parsed.thought = (
                    f"[Parse error: {type(exc).__name__} — model response was not valid JSON]"
                )

        return parsed
