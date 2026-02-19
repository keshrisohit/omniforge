# Intent Classification Evaluation

This directory contains evaluation tests for the LLM-based intent classification system.

## Evaluation Tests

The evaluation test suite (`test_intent_evaluation.py`) provides comprehensive testing of intent classification accuracy using real LLM calls against a curated test set.

### Test Coverage

- **41 total test cases** across all 7 ActionType values:
  - `CREATE_AGENT`: 8 test cases
  - `CREATE_SKILL`: 6 test cases
  - `UPDATE_AGENT`: 5 test cases
  - `QUERY_INFO`: 6 test cases
  - `EXECUTE_TASK`: 6 test cases
  - `MANAGE_PLATFORM`: 3 test cases
  - `UNKNOWN`: 7 test cases (including edge cases)

- **Context-dependent test cases**: Tests classification with conversation history

### Running Evaluation Tests

Evaluation tests are marked with `@pytest.mark.eval` and are skipped by default in CI to avoid LLM costs.

#### Prerequisites

Set up an LLM API key. The tests support multiple providers:

```bash
# Option 1: Use Groq (recommended - free tier available)
export GROQ_API_KEY=your_groq_api_key
export OMNIFORGE_LLM_DEFAULT_MODEL=groq/llama-3.3-70b-versatile

# Option 2: Use OpenAI
export OPENAI_API_KEY=your_openai_api_key
# Tests will default to gpt-4o-mini if no model specified

# Option 3: Use OpenRouter
export OPENROUTER_API_KEY=your_openrouter_api_key
export OMNIFORGE_LLM_DEFAULT_MODEL=openrouter/anthropic/claude-3.5-sonnet
```

#### Run Evaluation

```bash
# Run all evaluation tests
pytest tests/conversation/test_intent_evaluation.py -m eval -v -s

# Run only the main evaluation test
pytest tests/conversation/test_intent_evaluation.py::test_intent_classification_evaluation -m eval -v -s

# Run only context-dependent tests
pytest tests/conversation/test_intent_evaluation.py::test_context_dependent_classification -m eval -v -s
```

#### Skip Evaluation Tests

```bash
# Run all tests except evaluation (default behavior)
pytest tests/conversation/ -m "not eval"

# Run all tests including evaluation
pytest tests/conversation/
```

### Performance Baseline

**Current Performance (as of 2026-01-30):**
- **Model**: `groq/llama-3.3-70b-versatile`
- **Overall Accuracy**: 87.80% (36/41 correct)
- **Minimum Threshold**: 75%

**Per-Class Metrics:**
| Action Type      | Precision | Recall | F1-Score |
|------------------|-----------|--------|----------|
| CREATE_AGENT     | 100.00%   | 100.00%| 100.00%  |
| CREATE_SKILL     | 100.00%   | 100.00%| 100.00%  |
| UPDATE_AGENT     | 100.00%   | 100.00%| 100.00%  |
| QUERY_INFO       | 85.71%    | 100.00%| 92.31%   |
| EXECUTE_TASK     | 100.00%   | 66.67% | 80.00%   |
| MANAGE_PLATFORM  | 0.00%     | 0.00%  | 0.00%    |
| UNKNOWN          | 63.64%    | 100.00%| 77.78%   |

**Known Issues:**
- `MANAGE_PLATFORM` classification needs improvement (0% accuracy)
- Some ambiguous `EXECUTE_TASK` cases misclassified as `QUERY_INFO` or `UNKNOWN`

### Evaluation Report

When running evaluation tests, a detailed report is printed including:

1. **Overall Accuracy**: Percentage of correct classifications
2. **Per-Class Metrics**: Precision, recall, and F1-score for each ActionType
3. **Confusion Matrix**: Expected vs predicted classifications
4. **Failed Cases**: Detailed list of misclassifications with explanations

Example output:
```
================================================================================
INTENT CLASSIFICATION EVALUATION REPORT
================================================================================

Overall Accuracy: 87.80% (36/41)

--------------------------------------------------------------------------------
Per-Class Metrics:
--------------------------------------------------------------------------------
Action Type          Precision    Recall       F1-Score
--------------------------------------------------------------------------------
create_agent            100.00%     100.00%     100.00%
...

--------------------------------------------------------------------------------
Confusion Matrix (Expected vs Predicted):
--------------------------------------------------------------------------------
Expected \ Predicted create create execut update query_ manage unknow
--------------------------------------------------------------------------------
create_agent              8      0      0      0      0      0      0
...

--------------------------------------------------------------------------------
Failed Cases (5):
--------------------------------------------------------------------------------

1. Message: "Process this dataset for me"
   Expected: execute_task
   Predicted: query_info
   Reason: Implicit task execution request
...
```

### Adding New Test Cases

To add new test cases, edit `test_intent_evaluation.py` and add entries to the `EVALUATION_TEST_CASES` list:

```python
IntentTestCase(
    message="Your test message here",
    expected_action=ActionType.CREATE_AGENT,  # Expected classification
    description="Brief explanation of why this is correct",
    conversation_history=None,  # Optional: add conversation context
),
```

**Guidelines for test cases:**
- Include diverse phrasing for each ActionType
- Add edge cases (empty messages, emojis, very short/long messages)
- Include ambiguous cases to test decision boundaries
- Add context-dependent cases with conversation history
- Document why each classification is correct

### Continuous Improvement

1. **Monitor accuracy**: Run evaluation regularly to catch regressions
2. **Analyze failures**: Review failed cases in the evaluation report
3. **Update test set**: Add new edge cases as you discover them
4. **Tune prompts**: Use evaluation results to improve LLM system prompt
5. **Track metrics**: Compare performance across different models/configurations

### CI/CD Integration

Evaluation tests are automatically skipped in CI (when `CI=true` environment variable is set) to avoid:
- LLM API costs
- Rate limiting issues
- Build time increases

To include evaluation in CI:
```yaml
# In your CI config
- name: Run evaluation tests
  run: pytest tests/conversation/test_intent_evaluation.py -m eval
  env:
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
    CI: false  # Override CI skip
```
