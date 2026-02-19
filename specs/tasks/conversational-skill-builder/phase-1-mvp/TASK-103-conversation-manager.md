# TASK-103: Conversation State Machine and Manager

**Phase**: 1 (MVP)
**Estimated Effort**: 16 hours
**Dependencies**: TASK-101
**Priority**: P0

## Objective

Implement the ConversationManager that guides users through agent creation via natural language conversation. This includes the state machine, session management, and LLM integration for understanding user intent.

## Requirements

- Create `ConversationPhase` enum: IDLE, DISCOVERY, OAUTH_FLOW, REQUIREMENTS, GENERATION, TESTING, ACTIVATION, COMPLETE
- Create `ConversationState` model with session_id, user_id, tenant_id, phase, context, pending_oauth, draft_agent_id
- Implement `ConversationManager` class with session lifecycle methods
- Create `ChatResponse` model for streaming responses with actions and oauth_url
- Integrate with `AgentGenerator` (stubbed initially) for requirements analysis
- Support OAuth flow interruption and resumption
- Implement state persistence (in-memory for MVP, extensible to Redis later)

## Implementation Notes

- Reference technical plan Section 5.1.1 for ConversationManager specification
- State machine flow: IDLE -> DISCOVERY -> OAUTH_FLOW (if needed) -> REQUIREMENTS -> GENERATION -> TESTING -> ACTIVATION -> COMPLETE
- Use async generators for streaming responses
- Session timeout after 30 minutes of inactivity
- Context accumulates user requirements across conversation turns
- LLM extracts structured requirements from natural language

## Acceptance Criteria

- [ ] ConversationManager correctly transitions through all phases
- [ ] `start_session()` creates new session in IDLE phase
- [ ] `process_message()` returns streaming ChatResponse with correct phase
- [ ] OAuth flow can be interrupted (DISCOVERY -> OAUTH_FLOW) and resumed
- [ ] `complete_oauth()` resumes conversation after OAuth callback
- [ ] Session context accumulates requirements across turns
- [ ] State machine handles edge cases (user going back, unexpected input)
- [ ] 80%+ test coverage for state transitions

## Files to Create/Modify

- `src/omniforge/builder/conversation/__init__.py` - Conversation package init
- `src/omniforge/builder/conversation/state.py` - ConversationPhase, ConversationState models
- `src/omniforge/builder/conversation/manager.py` - ConversationManager class
- `src/omniforge/builder/conversation/prompts.py` - LLM prompts for conversation
- `src/omniforge/builder/conversation/session_store.py` - In-memory session storage
- `tests/builder/conversation/__init__.py` - Test package
- `tests/builder/conversation/test_manager.py` - Manager tests
- `tests/builder/conversation/test_state_transitions.py` - State machine tests
