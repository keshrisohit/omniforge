# TASK-005: Update MasterAgent with LLM Intent + Keyword Fallback

## Description
Update `MasterAgent` to use `LLMIntentAnalyzer` as primary classifier with automatic fallback to keyword matching. Extract existing keyword logic into a named method.

## What to Build

### Modify `src/omniforge/agents/master_agent.py`
1. Add optional `intent_analyzer: Optional[LLMIntentAnalyzer]` parameter to `__init__`
2. Rename current `_analyze_intent` to `_keyword_analyze_intent` (exact same logic, no changes)
3. Create new `_analyze_intent(message, conversation_history=None) -> RoutingDecision`:
   - If `intent_analyzer` is set, try `await self._intent_analyzer.analyze(message, conversation_history)`
   - On `IntentAnalysisError`, log warning and fall back to `_keyword_analyze_intent(message)`
   - If `intent_analyzer` is None, use `_keyword_analyze_intent(message)` directly
4. Update `process_task` to extract conversation history from task messages and pass to `_analyze_intent`

## Key Requirements
- **Backward compatible**: When `intent_analyzer=None` (default), behavior is identical to current code
- Import from `routing.models` (ActionType, RoutingDecision already moved in TASK-001)
- Import `LLMIntentAnalyzer` and `IntentAnalysisError` from `conversation.intent_analyzer`
- All existing tests must continue to pass without modification
- Logging: WARNING level when LLM fails and keyword fallback is used

## Dependencies
- TASK-001 (routing models extracted)
- TASK-004 (LLMIntentAnalyzer)

## Success Criteria
- Existing keyword intent tests pass unchanged
- MasterAgent with `intent_analyzer=None` behaves identically to current
- MasterAgent with mocked analyzer delegates to LLM
- LLM failure triggers keyword fallback with warning log
- Conversation history extracted from task and forwarded to analyzer
- `tests/agents/test_master_agent_intent.py` (new tests for LLM + fallback)

## Complexity
Medium
