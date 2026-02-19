# TASK-003: Requirements Gatherer

**Phase**: 1 (MVP)
**Complexity**: Medium
**Estimated Effort**: 3-4 hours
**Dependencies**: TASK-001, TASK-002

## Description

Implement the RequirementsGatherer class that generates contextual clarifying questions, detects skill patterns, extracts requirements from user responses, and determines when sufficient context has been gathered for SKILL.md generation.

## Requirements

### Location
- Create `src/omniforge/skills/creation/gatherer.py`
- Create `src/omniforge/skills/creation/prompts.py` (LLM prompt templates)

### RequirementsGatherer Class

```python
class RequirementsGatherer:
    """Generate clarifying questions for skill requirements."""

    def __init__(self, llm_generator: LLMResponseGenerator) -> None: ...

    async def detect_skill_pattern(self, purpose: str) -> SkillPattern:
        """Classify skill pattern based on user's description."""

    async def generate_clarifying_questions(
        self,
        context: ConversationContext,
    ) -> list[str]:
        """Generate questions based on what's missing."""

    def extract_requirements(
        self,
        user_response: str,
        context: ConversationContext,
    ) -> dict[str, Any]:
        """Extract structured requirements from user response."""

    def has_sufficient_context(self, context: ConversationContext) -> bool:
        """Check if we have enough info to generate."""

    async def generate_skill_name(self, context: ConversationContext) -> str:
        """Generate kebab-case skill name from purpose."""

    async def generate_description(self, context: ConversationContext) -> str:
        """Generate description in official format: third person, WHAT + WHEN."""
```

### Prompt Templates (prompts.py)

1. **SKILL_PATTERN_CLASSIFICATION_PROMPT**: Classify into SIMPLE/WORKFLOW/REFERENCE/SCRIPT
2. **CLARIFYING_QUESTIONS_PROMPT**: Generate 2-3 contextual questions
3. **SKILL_NAME_GENERATION_PROMPT**: Generate kebab-case name (max 64 chars, gerund form)
4. **DESCRIPTION_GENERATION_PROMPT**: Third person, WHAT + WHEN, max 1024 chars

### Sufficient Context Criteria (MVP - Simple Skills)

A Simple skill has sufficient context when:
- skill_purpose is non-empty
- At least 1 example input/output provided OR clear instructions
- At least 1 trigger/context for WHEN to use

### Question Templates by Pattern

```python
QUESTIONS_BY_PATTERN = {
    SkillPattern.SIMPLE: [
        "What specific task should this skill help accomplish?",
        "Can you give 2-3 examples of inputs and expected outputs?",
        "When should this skill be used? What triggers it?",
    ],
    # ... other patterns for Phase 2
}
```

## Acceptance Criteria

- [ ] detect_skill_pattern returns correct pattern for various inputs
- [ ] generate_clarifying_questions produces relevant questions
- [ ] has_sufficient_context correctly identifies when ready to generate
- [ ] generate_skill_name produces valid kebab-case names
- [ ] generate_description produces third-person descriptions with WHAT + WHEN
- [ ] LLM calls use appropriate temperature settings (0.1-0.3 for classification)
- [ ] Unit tests with mocked LLM responses
- [ ] Test coverage > 85%

## Technical Notes

- Use existing LLMResponseGenerator for all LLM calls
- Configure LLM with low temperature (0.1-0.3) for deterministic outputs
- Parse JSON responses from LLM for structured data extraction
- Handle malformed LLM responses gracefully

## Test Cases

```python
async def test_detect_skill_pattern_simple():
    gatherer = RequirementsGatherer(mock_llm)
    mock_llm.generate.return_value = '{"pattern": "simple"}'
    pattern = await gatherer.detect_skill_pattern("Format product names")
    assert pattern == SkillPattern.SIMPLE

def test_has_sufficient_context_with_examples():
    ctx = ConversationContext(
        skill_purpose="Format names",
        examples=[{"input": "PA", "output": "Pro Analytics"}],
        triggers=["writing docs"]
    )
    assert gatherer.has_sufficient_context(ctx) is True

def test_has_sufficient_context_missing_examples():
    ctx = ConversationContext(skill_purpose="Format names")
    assert gatherer.has_sufficient_context(ctx) is False
```
