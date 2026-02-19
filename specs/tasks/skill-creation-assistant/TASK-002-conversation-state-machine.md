# TASK-002: Conversation State Machine

**Phase**: 1 (MVP)
**Complexity**: Medium
**Estimated Effort**: 3-4 hours
**Dependencies**: TASK-001

## Description

Implement the ConversationManager class that manages the finite state machine for skill creation conversations. This component tracks conversation state, determines transitions based on user input, and coordinates with other components.

## Requirements

### Location
- Create `src/omniforge/skills/creation/conversation.py`

### ConversationManager Class

```python
class ConversationManager:
    """Manage skill creation conversation state."""

    def __init__(
        self,
        gatherer: RequirementsGatherer,
        generator: SkillMdGenerator
    ) -> None: ...

    async def process_message(
        self,
        message: str,
        context: ConversationContext,
    ) -> tuple[str, ConversationContext]:
        """Process message, return response and updated context."""

    def get_next_state(
        self,
        context: ConversationContext,
        user_response: str
    ) -> ConversationState:
        """Determine next state based on current state and user input."""

    def is_complete(self, context: ConversationContext) -> bool:
        """Check if conversation has reached terminal state."""
```

### State Transitions

| Current State | Condition | Next State |
|---------------|-----------|------------|
| IDLE | Skill creation detected | GATHERING_PURPOSE |
| GATHERING_PURPOSE | Purpose received | GATHERING_DETAILS |
| GATHERING_DETAILS | Sufficient context | CONFIRMING_SPEC |
| GATHERING_DETAILS | Need more info | GATHERING_DETAILS |
| CONFIRMING_SPEC | User confirms | GENERATING |
| CONFIRMING_SPEC | User requests changes | GATHERING_DETAILS |
| GENERATING | Generation complete | VALIDATING |
| VALIDATING | Valid | SELECTING_STORAGE |
| VALIDATING | Invalid, retries left | FIXING_ERRORS |
| VALIDATING | Invalid, no retries | ERROR |
| FIXING_ERRORS | Fix attempted | VALIDATING |
| SELECTING_STORAGE | Layer selected | SAVING |
| SAVING | Save complete | COMPLETED |

### Key Behaviors

1. **Message History Tracking**: Append all messages to context.message_history
2. **State Transition Logging**: Log state transitions for debugging
3. **Error State Handling**: Graceful transition to ERROR state on failures
4. **Context Preservation**: Never lose accumulated context on state changes

## Acceptance Criteria

- [ ] ConversationManager initializes with dependencies
- [ ] process_message returns response and updated context
- [ ] All state transitions implemented per table above
- [ ] is_complete returns True only for COMPLETED or ERROR states
- [ ] Message history preserved across process_message calls
- [ ] Unit tests for all state transitions
- [ ] Test coverage > 85%

## Technical Notes

- Use pattern matching or dict-based dispatch for state handlers
- Keep state transition logic pure (easy to test)
- Delegate to RequirementsGatherer for GATHERING_* states
- Delegate to SkillMdGenerator for GENERATING state
- For MVP: SELECTING_STORAGE defaults to "project" layer

## Test Cases

```python
async def test_state_transition_idle_to_gathering():
    manager = ConversationManager(gatherer, generator)
    ctx = ConversationContext(state=ConversationState.IDLE)
    response, new_ctx = await manager.process_message("Create a skill", ctx)
    assert new_ctx.state == ConversationState.GATHERING_PURPOSE

async def test_is_complete_for_completed_state():
    ctx = ConversationContext(state=ConversationState.COMPLETED)
    assert manager.is_complete(ctx) is True

async def test_is_complete_for_in_progress_state():
    ctx = ConversationContext(state=ConversationState.GENERATING)
    assert manager.is_complete(ctx) is False
```
