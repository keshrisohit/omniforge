# TASK-007: Integration Tests for Full Smart Master Agent Flow

## Description
End-to-end integration tests verifying the complete flow from ChatService through MasterAgent with conversation storage, context passing, and LLM intent analysis (mocked).

## What to Build

### `tests/integration/test_smart_master_agent.py`
1. **Full flow test**: Create ChatService with in-memory repo and mocked LLM analyzer. Send first message, verify conversation created, user message stored, LLM called with empty history, response generated, assistant message stored.
2. **Multi-turn test**: Send follow-up message, verify history includes both prior messages, LLM called with conversation context.
3. **LLM fallback test**: Simulate LLM failure (mock raises IntentAnalysisError), verify keyword fallback used and response still generated.
4. **Conversation continuity test**: Use same conversation_id across multiple requests, verify all messages accumulate correctly.
5. **Tenant isolation test**: Create conversations for two tenants, verify neither can access the other's data.
6. **Invalid conversation_id test**: Provide a conversation_id that doesn't exist, verify error raised.

### `tests/integration/test_backward_compat.py`
1. Create ChatService with NO repository (repo=None)
2. Verify identical behavior to current implementation
3. No storage calls, no context, keyword-only intent
4. All existing response patterns preserved

## Key Requirements
- All LLM calls mocked (no real API calls)
- Use `InMemoryConversationRepository` for storage
- Tests must be async (pytest-asyncio)
- Cover all review issues: tenant validation, error handling, fallback

## Dependencies
- TASK-001 through TASK-006 (all components)

## Success Criteria
- All 6+ integration test scenarios pass
- Backward compatibility test confirms no regressions
- Full round-trip with conversation_id continuity works
- Tenant isolation verified
- LLM fallback verified
- All existing tests still pass

## Complexity
Medium
