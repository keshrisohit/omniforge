"""Tests for ReAct response parser with JSON format."""

from omniforge.agents.cot.parser import ParsedResponse, ReActParser


class TestParsedResponse:
    """Tests for ParsedResponse dataclass."""

    def test_default_values(self) -> None:
        """ParsedResponse should have sensible defaults."""
        parsed = ParsedResponse()

        assert parsed.thought is None
        assert parsed.is_final is False
        assert parsed.final_answer is None
        assert parsed.action is None
        assert parsed.action_input is None
        assert parsed.is_clarification is False
        assert parsed.clarification_question is None

    def test_custom_values(self) -> None:
        """ParsedResponse should accept custom values."""
        parsed = ParsedResponse(
            thought="test thought",
            is_final=True,
            final_answer="test answer",
            action="search",
            action_input={"query": "test"},
        )

        assert parsed.thought == "test thought"
        assert parsed.is_final is True
        assert parsed.final_answer == "test answer"
        assert parsed.action == "search"
        assert parsed.action_input == {"query": "test"}


class TestReActParser:
    """Tests for ReActParser class with JSON format."""

    def test_parse_standard_react_format(self) -> None:
        """Should parse standard JSON ReAct format with thought, action, and input."""
        response = """
{
  "thought": "I need to search for information about Python",
  "action": "search",
  "action_input": {"query": "Python programming"},
  "is_final": false
}
"""
        parsed = ReActParser.parse(response)

        assert parsed.thought == "I need to search for information about Python"
        assert parsed.action == "search"
        assert parsed.action_input == {"query": "Python programming"}
        assert parsed.is_final is False
        assert parsed.final_answer is None

    def test_parse_final_answer(self) -> None:
        """Should recognize Final Answer and set is_final=True."""
        response = """
{
  "thought": "I have all the information needed",
  "final_answer": "Python is a high-level programming language",
  "is_final": true
}
"""
        parsed = ReActParser.parse(response)

        assert parsed.thought == "I have all the information needed"
        assert parsed.is_final is True
        assert parsed.final_answer == "Python is a high-level programming language"
        assert parsed.action is None
        assert parsed.action_input is None

    def test_parse_multiline_thought(self) -> None:
        """Should preserve newlines in thought content."""
        response = """
{
  "thought": "First I need to:\\n1. Search for the data\\n2. Process the results\\n3. Return the answer",
  "action": "search",
  "action_input": {"query": "test"},
  "is_final": false
}
"""
        parsed = ReActParser.parse(response)

        assert "First I need to:" in parsed.thought
        assert "1. Search for the data" in parsed.thought
        assert "2. Process the results" in parsed.thought
        assert "3. Return the answer" in parsed.thought

    def test_parse_multiline_final_answer(self) -> None:
        """Should preserve newlines in final answer content."""
        response = """
{
  "thought": "Ready to respond",
  "final_answer": "Here are the results:\\n- Item 1\\n- Item 2\\n- Item 3",
  "is_final": true
}
"""
        parsed = ReActParser.parse(response)

        assert parsed.is_final is True
        assert "Here are the results:" in parsed.final_answer
        assert "- Item 1" in parsed.final_answer
        assert "- Item 2" in parsed.final_answer

    def test_parse_json_object_action_input(self) -> None:
        """Should parse JSON object in action_input."""
        response = """
{
  "thought": "Testing JSON parsing",
  "action": "test_tool",
  "action_input": {"key1": "value1", "key2": "value2"},
  "is_final": false
}
"""
        parsed = ReActParser.parse(response)

        assert parsed.action_input == {"key1": "value1", "key2": "value2"}

    def test_parse_json_array_action_input(self) -> None:
        """Should wrap JSON array in dict for consistent handling."""
        response = """
{
  "thought": "Testing array input",
  "action": "batch_process",
  "action_input": ["item1", "item2", "item3"],
  "is_final": false
}
"""
        parsed = ReActParser.parse(response)

        assert parsed.action_input == {"items": ["item1", "item2", "item3"]}

    def test_parse_nested_json_action_input(self) -> None:
        """Should parse nested JSON structures."""
        response = """
{
  "thought": "Complex nested structure",
  "action": "complex_tool",
  "action_input": {"outer": {"inner": "value"}, "list": [1, 2, 3]},
  "is_final": false
}
"""
        parsed = ReActParser.parse(response)

        assert parsed.action_input == {"outer": {"inner": "value"}, "list": [1, 2, 3]}

    def test_parse_malformed_json_stores_error_in_thought(self) -> None:
        """Malformed JSON returns empty ParsedResponse with parse error in thought."""
        response = """
{invalid json here}
"""
        parsed = ReActParser.parse(response)

        # thought now contains a diagnostic parse error string
        assert parsed.thought is not None
        assert "Parse error" in parsed.thought
        assert parsed.action is None
        assert parsed.action_input is None
        assert parsed.is_final is False

    def test_parse_empty_json_object(self) -> None:
        """Should parse empty action_input object."""
        response = """
{
  "thought": "Empty input",
  "action": "no_args_tool",
  "action_input": {},
  "is_final": false
}
"""
        parsed = ReActParser.parse(response)

        assert parsed.action_input == {}

    def test_parse_no_thought(self) -> None:
        """Should handle missing thought field."""
        response = """
{
  "action": "search",
  "action_input": {"query": "test"},
  "is_final": false
}
"""
        parsed = ReActParser.parse(response)

        assert parsed.thought is None
        assert parsed.action == "search"
        assert parsed.action_input == {"query": "test"}

    def test_parse_no_action(self) -> None:
        """Should handle missing action field."""
        response = """
{
  "thought": "Just thinking, no action yet",
  "is_final": false
}
"""
        parsed = ReActParser.parse(response)

        assert parsed.thought == "Just thinking, no action yet"
        assert parsed.action is None
        assert parsed.action_input is None

    def test_parse_no_action_input(self) -> None:
        """Should handle missing action_input field."""
        response = """
{
  "thought": "Calling tool without input",
  "action": "simple_tool",
  "is_final": false
}
"""
        parsed = ReActParser.parse(response)

        assert parsed.thought == "Calling tool without input"
        assert parsed.action == "simple_tool"
        assert parsed.action_input is None

    def test_parse_extra_whitespace(self) -> None:
        """Should handle extra whitespace in field values."""
        response = """
{
  "thought": "     Lots of spaces here     ",
  "action": "   search   ",
  "action_input": {"query": "test"},
  "is_final": false
}
"""
        parsed = ReActParser.parse(response)

        assert parsed.thought == "Lots of spaces here"
        assert parsed.action == "search"
        assert parsed.action_input == {"query": "test"}

    def test_parse_empty_string(self) -> None:
        """Should handle empty response string."""
        response = ""
        parsed = ReActParser.parse(response)

        assert parsed.thought is None
        assert parsed.action is None
        assert parsed.action_input is None
        assert parsed.is_final is False

    def test_parse_only_whitespace(self) -> None:
        """Should handle whitespace-only response."""
        response = "   \n\n  \t  "
        parsed = ReActParser.parse(response)

        assert parsed.thought is None
        assert parsed.action is None
        assert parsed.action_input is None

    def test_final_answer_takes_precedence(self) -> None:
        """is_final=true should ignore action fields."""
        response = """
{
  "thought": "This is the final step",
  "action": "search",
  "action_input": {"query": "ignored"},
  "final_answer": "The actual answer",
  "is_final": true
}
"""
        parsed = ReActParser.parse(response)

        assert parsed.is_final is True
        assert parsed.final_answer == "The actual answer"
        # Action fields should be ignored when is_final=true
        assert parsed.action is None
        assert parsed.action_input is None

    def test_parse_with_markdown_code_block(self) -> None:
        """Should handle JSON wrapped in markdown code blocks."""
        response = """```json
{
  "thought": "Testing markdown format",
  "action": "search",
  "action_input": {"query": "test"},
  "is_final": false
}
```"""
        parsed = ReActParser.parse(response)

        assert parsed.thought == "Testing markdown format"
        assert parsed.action == "search"
        assert parsed.action_input == {"query": "test"}

    def test_parse_action_with_special_characters(self) -> None:
        """Should handle action names with underscores and numbers."""
        response = """
{
  "thought": "Testing special tool names",
  "action": "search_web_v2",
  "action_input": {"query": "test"},
  "is_final": false
}
"""
        parsed = ReActParser.parse(response)

        assert parsed.action == "search_web_v2"

    def test_parse_json_with_multiline_strings(self) -> None:
        """Should handle JSON with escaped newlines."""
        response = """
{
  "thought": "Testing multiline JSON strings",
  "action": "create_doc",
  "action_input": {"content": "Line 1\\nLine 2\\nLine 3"},
  "is_final": false
}
"""
        parsed = ReActParser.parse(response)

        assert parsed.action_input == {"content": "Line 1\nLine 2\nLine 3"}

    def test_parse_realistic_complex_example(self) -> None:
        """Should parse a realistic complex ReAct response."""
        response = """
{
  "thought": "Based on the user's question about Python frameworks, I need to search for information about popular Python web frameworks. I'll query for Django, Flask, and FastAPI to provide a comprehensive answer.\\n\\nThe search should cover:\\n- Framework features\\n- Use cases\\n- Community support",
  "action": "web_search",
  "action_input": {
    "query": "popular Python web frameworks comparison",
    "filters": {
      "recency": "last_year",
      "domains": ["python.org", "realpython.com"]
    },
    "max_results": 5
  },
  "is_final": false
}
"""
        parsed = ReActParser.parse(response)

        assert "Python frameworks" in parsed.thought
        assert "- Framework features" in parsed.thought
        assert parsed.action == "web_search"
        assert parsed.action_input["query"] == "popular Python web frameworks comparison"
        assert parsed.action_input["filters"]["recency"] == "last_year"
        assert parsed.action_input["max_results"] == 5

    def test_parse_json_primitive_values(self) -> None:
        """Should wrap primitive JSON values in dict."""
        response = """
{
  "thought": "Testing string primitive",
  "action": "test_tool",
  "action_input": "just a string",
  "is_final": false
}
"""
        parsed = ReActParser.parse(response)

        assert parsed.action_input == {"value": "just a string"}

    def test_parse_json_number_primitive(self) -> None:
        """Should wrap number primitive in dict."""
        response = """
{
  "thought": "Testing number",
  "action": "test_tool",
  "action_input": 42,
  "is_final": false
}
"""
        parsed = ReActParser.parse(response)

        assert parsed.action_input == {"value": 42}

    def test_parse_is_final_defaults_to_false(self) -> None:
        """is_final should default to false if not provided."""
        response = """
{
  "thought": "Testing default is_final",
  "action": "search",
  "action_input": {"query": "test"}
}
"""
        parsed = ReActParser.parse(response)

        assert parsed.is_final is False

    def test_parse_null_action_input(self) -> None:
        """Should handle null action_input."""
        response = """
{
  "thought": "Testing null input",
  "action": "simple_tool",
  "action_input": null,
  "is_final": false
}
"""
        parsed = ReActParser.parse(response)

        assert parsed.action == "simple_tool"
        assert parsed.action_input is None

    def test_parse_boolean_is_final(self) -> None:
        """Should correctly parse boolean is_final values."""
        response_false = """
{
  "thought": "Not final",
  "action": "search",
  "action_input": {"query": "test"},
  "is_final": false
}
"""
        response_true = """
{
  "thought": "Final",
  "final_answer": "Done",
  "is_final": true
}
"""
        parsed_false = ReActParser.parse(response_false)
        parsed_true = ReActParser.parse(response_true)

        assert parsed_false.is_final is False
        assert parsed_true.is_final is True

    def test_parse_empty_strings_in_fields(self) -> None:
        """Should treat empty strings as None for optional fields."""
        response = """
{
  "thought": "",
  "action": "search",
  "action_input": {"query": "test"},
  "is_final": false
}
"""
        parsed = ReActParser.parse(response)

        assert parsed.thought is None
        assert parsed.action == "search"

    def test_parse_minified_json(self) -> None:
        """Should parse minified JSON without whitespace."""
        response = """{"thought":"Minified","action":"search","action_input":{"query":"test"},"is_final":false}"""
        parsed = ReActParser.parse(response)

        assert parsed.thought == "Minified"
        assert parsed.action == "search"
        assert parsed.action_input == {"query": "test"}
        assert parsed.is_final is False

    def test_parse_with_text_before_json(self) -> None:
        """Should extract JSON even if there's explanatory text before it."""
        response = """Let me call the calculator tool to solve this problem.

{
  "thought": "I need to calculate 5 + 3",
  "action": "calculator",
  "action_input": {"expression": "5 + 3"},
  "is_final": false
}"""
        parsed = ReActParser.parse(response)

        assert parsed.thought == "I need to calculate 5 + 3"
        assert parsed.action == "calculator"
        assert parsed.action_input == {"expression": "5 + 3"}
        assert parsed.is_final is False

    def test_parse_is_final_without_final_answer(self) -> None:
        """Should handle is_final=true without final_answer field."""
        response = """
{
  "thought": "I have completed the task",
  "is_final": true
}
"""
        parsed = ReActParser.parse(response)

        assert parsed.is_final is True
        assert parsed.final_answer is None
        assert parsed.action is None
        assert parsed.action_input is None

    def test_parse_is_final_with_empty_final_answer(self) -> None:
        """Should handle is_final=true with empty final_answer."""
        response = """
{
  "thought": "Task done",
  "final_answer": "",
  "is_final": true
}
"""
        parsed = ReActParser.parse(response)

        assert parsed.is_final is True
        assert parsed.final_answer is None  # Empty string should be treated as None
        assert parsed.action is None
        assert parsed.action_input is None

    def test_parse_clarification_format(self) -> None:
        """Should parse clarification_question into is_clarification=True."""
        response = """
{
  "thought": "I need to know the target directory",
  "clarification_question": "Which directory should I search in?",
  "is_final": false
}
"""
        parsed = ReActParser.parse(response)

        assert parsed.is_clarification is True
        assert parsed.clarification_question == "Which directory should I search in?"
        assert parsed.is_final is False
        assert parsed.action is None
        assert parsed.final_answer is None

    def test_parse_clarification_not_set_for_action(self) -> None:
        """Normal action response should not set is_clarification."""
        response = """
{
  "thought": "I'll use bash",
  "action": "bash",
  "action_input": {"command": "ls"},
  "is_final": false
}
"""
        parsed = ReActParser.parse(response)

        assert parsed.is_clarification is False
        assert parsed.clarification_question is None
        assert parsed.action == "bash"

    def test_parse_clarification_empty_question_ignored(self) -> None:
        """Empty clarification_question should not trigger is_clarification."""
        response = """
{
  "thought": "hm",
  "clarification_question": "",
  "is_final": false
}
"""
        parsed = ReActParser.parse(response)

        assert parsed.is_clarification is False
        assert parsed.clarification_question is None
