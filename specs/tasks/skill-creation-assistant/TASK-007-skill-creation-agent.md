# TASK-007: SkillCreationAgent Orchestration

**Phase**: 1 (MVP)
**Complexity**: High
**Estimated Effort**: 4-5 hours
**Dependencies**: TASK-002, TASK-003, TASK-004, TASK-005, TASK-006

## Description

Implement the SkillCreationAgent class that serves as the main entry point for skill creation conversations. This agent orchestrates all components (ConversationManager, RequirementsGatherer, SkillMdGenerator, SkillValidator, SkillWriter) to enable conversational skill creation.

## Requirements

### Location
- Create `src/omniforge/skills/creation/agent.py`
- Update `src/omniforge/skills/creation/__init__.py` with exports

### SkillCreationAgent Class

```python
class SkillCreationAgent:
    """Conversational agent for skill creation following Anthropic guidelines."""

    identity = AgentIdentity(
        id="skill-creation-assistant",
        name="Skill Creation Assistant",
        description="Create OmniForge skills through natural conversation",
        version="1.0.0",
    )

    def __init__(
        self,
        llm_generator: Optional[LLMResponseGenerator] = None,
        storage_config: Optional[StorageConfig] = None,
        skill_loader: Optional[SkillLoader] = None,
    ) -> None:
        """Initialize agent with dependencies (or create defaults)."""

    async def handle_message(
        self,
        message: str,
        session_id: str,
        conversation_history: Optional[list[dict[str, str]]] = None,
    ) -> AsyncIterator[str]:
        """Handle conversational message for skill creation.

        Yields:
            Response chunks for streaming to user
        """

    async def create_skill(
        self,
        purpose: str,
        examples: list[dict[str, str]],
        triggers: list[str],
        storage_layer: str = "project",
    ) -> Path:
        """Programmatic skill creation (non-conversational).

        Returns:
            Path to created skill
        """

    def get_session_context(self, session_id: str) -> ConversationContext:
        """Get or create conversation context for session."""

    def _clear_session(self, session_id: str) -> None:
        """Clear session context after completion."""
```

### Session Management

- Store ConversationContext per session_id in memory (dict)
- Create new context for unknown session_id
- Clear context when conversation reaches COMPLETED or ERROR state
- Handle concurrent sessions (thread-safe for async)

### Response Generation

For each state, generate appropriate responses:

| State | Response Type |
|-------|---------------|
| IDLE | Intent detection question or greeting |
| GATHERING_PURPOSE | Questions about skill purpose |
| GATHERING_DETAILS | Clarifying questions |
| CONFIRMING_SPEC | Skill specification preview |
| GENERATING | Progress indicator |
| VALIDATING | Validation status |
| FIXING_ERRORS | Error explanation + retry |
| SELECTING_STORAGE | Storage layer options (MVP: skip, default to project) |
| SAVING | Save confirmation |
| COMPLETED | Success message + usage instructions |
| ERROR | Error message + recovery options |

### Integration Points

1. **LLMResponseGenerator**: For all LLM calls (questions, generation)
2. **ConversationManager**: For state machine logic
3. **RequirementsGatherer**: For question generation
4. **SkillMdGenerator**: For SKILL.md generation
5. **SkillValidator**: For validation
6. **SkillWriter**: For file writing

## Acceptance Criteria

- [ ] handle_message() processes messages and yields responses
- [ ] Session context persisted across multiple handle_message calls
- [ ] State machine transitions correctly through conversation
- [ ] Generated skills pass validation (95%+ first attempt)
- [ ] create_skill() provides programmatic API
- [ ] Proper error handling with user-friendly messages
- [ ] Integration tests for complete conversation flow
- [ ] Test coverage > 80%

## Technical Notes

- Use AsyncIterator for streaming responses
- Store sessions in dict[str, ConversationContext]
- Consider session timeout for memory cleanup (future enhancement)
- Follow patterns from existing agents in `src/omniforge/agents/`

## Test Cases

```python
async def test_handle_message_first_message():
    agent = SkillCreationAgent(mock_llm)
    responses = []
    async for chunk in agent.handle_message(
        "Create a skill to format product names",
        session_id="test-session"
    ):
        responses.append(chunk)

    full_response = "".join(responses)
    assert "clarify" in full_response.lower() or "question" in full_response.lower()

async def test_full_conversation_flow():
    agent = SkillCreationAgent(mock_llm, tmp_storage_config)

    # First message: describe purpose
    await consume_iterator(agent.handle_message(
        "Create a skill to format product names", "session1"
    ))

    # Second message: provide examples
    await consume_iterator(agent.handle_message(
        "Examples: 'PA' -> 'Pro Analytics'. Use for docs.", "session1"
    ))

    # Continue until completion...
    ctx = agent.get_session_context("session1")
    # Eventually reaches COMPLETED
    assert ctx.generated_content is not None

async def test_create_skill_programmatic():
    agent = SkillCreationAgent(mock_llm, tmp_storage_config)
    path = await agent.create_skill(
        purpose="Format product names",
        examples=[{"input": "PA", "output": "Pro Analytics"}],
        triggers=["writing documentation"],
        storage_layer="project"
    )
    assert path.exists()
    assert (path / "SKILL.md").exists()
```

## User-Friendly Response Templates

```python
RESPONSE_TEMPLATES = {
    "greeting": "I'd be happy to help you create a new skill!",
    "gathering_purpose": "To create an effective skill, I need to understand:\n"
                        "1. {questions}",
    "confirming_spec": "Here's what I'll create:\n\n"
                       "**Name**: {name}\n"
                       "**Description**: {description}\n\n"
                       "Does this look correct?",
    "generating": "Creating your skill...",
    "validation_success": "Skill validated successfully!",
    "validation_failure": "I found some issues:\n{errors}\n\nLet me fix these...",
    "completed": "Your skill '{name}' has been created!\n\n"
                "Location: {path}\n\n"
                "To use it, agents will automatically apply it when relevant, "
                "or you can invoke it manually.",
    "error": "I encountered an error: {error}\n\n"
            "Would you like to try again or modify your requirements?"
}
```
