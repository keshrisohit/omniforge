# TASK-203: Implement ReAct Response Parser

## Description

Create the ReActParser class that extracts structured actions from LLM responses following the ReAct (Reasoning + Acting) format. This enables autonomous agents to parse LLM outputs and determine next actions.

## Requirements

- Create `ParsedResponse` class with:
  - thought: Optional[str] - the reasoning content
  - is_final: bool - whether this is the final answer
  - final_answer: Optional[str] - the final response (if is_final)
  - action: Optional[str] - tool name to call
  - action_input: Optional[dict] - arguments for the tool
- Create `ReActParser` class with:
  - Regex patterns for parsing:
    - THOUGHT_PATTERN: captures "Thought: ..." until Action or Final Answer
    - ACTION_PATTERN: captures "Action: tool_name"
    - ACTION_INPUT_PATTERN: captures "Action Input: {...}" JSON
    - FINAL_ANSWER_PATTERN: captures "Final Answer: ..."
  - `parse(response: str)` method returning ParsedResponse:
    - Extract thought content
    - Check for Final Answer first (terminates parsing)
    - Extract action and action_input
    - Handle malformed JSON gracefully
    - Handle missing fields gracefully

## Acceptance Criteria

- [ ] Parses standard ReAct format correctly
- [ ] Extracts thought content with newlines preserved
- [ ] Recognizes Final Answer and sets is_final=True
- [ ] Parses JSON action_input correctly
- [ ] Returns None for action_input on malformed JSON (not exception)
- [ ] Handles edge cases: no thought, missing action, extra whitespace
- [ ] Unit tests cover parsing success cases and edge cases

## Dependencies

- None (standalone utility)

## Files to Create/Modify

- `src/omniforge/agents/cot/parser.py` (new)
- `tests/agents/cot/test_parser.py` (new)

## Estimated Complexity

Medium (3-4 hours)

## Key Considerations

- Use re.DOTALL and re.MULTILINE flags appropriately
- Action Input can be object or array JSON
- Be lenient with whitespace variations
- Consider supporting "Observation:" prefix stripping
