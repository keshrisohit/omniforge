# TASK-008: Intent Classification Eval Test Set

## Description
Create an evaluation test set of 30+ user messages with expected intents to validate LLM prompt accuracy. This enables prompt tuning and regression detection.

## What to Build

### `tests/conversation/test_intent_eval.py`
- Parametrized test cases with `(message, expected_action_type, expected_entities)` tuples
- At least 5 messages per action type (7 types = 35+ total)
- Include ambiguous and context-dependent messages:
  - "yes" / "do that" / "the first one" (requires context)
  - "create a report" (ambiguous: create_agent vs execute_task)
  - "help me analyze data" (ambiguous: query_info vs execute_task)
- Test both keyword analyzer and (mocked) LLM analyzer against same test set
- Report accuracy metrics (pass rate per action type)

### Example test messages per type:
- **create_agent**: "Create an agent that monitors stock prices", "Build me a data processing agent"
- **create_skill**: "Create a skill for parsing CSV files", "Add a new email notification skill"
- **execute_task**: "Run my report agent", "Analyze this dataset", "Process the uploaded file"
- **update_agent**: "Change my agent to run daily instead of weekly", "Update the data processor agent"
- **query_info**: "What agents do I have?", "How does the platform work?", "List all my skills"
- **manage_platform**: "Configure my dashboard", "Update platform settings"
- **unknown**: "asdf", "lorem ipsum", single emoji messages

## Key Requirements
- LLM calls mocked in tests (return expected JSON structure)
- Test set serves as regression suite for future prompt changes
- Document prompt version tested against

## Dependencies
- TASK-004 (LLMIntentAnalyzer)
- TASK-005 (keyword fallback for comparison)

## Success Criteria
- 30+ test cases covering all 7 action types
- Keyword analyzer accuracy documented (baseline)
- LLM analyzer (mocked) parses all test cases correctly
- Ambiguous cases have clear documentation of expected behavior
- Test runs as part of normal `pytest` suite

## Complexity
Simple
