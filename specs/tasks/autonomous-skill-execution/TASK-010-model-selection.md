# TASK-010: Add model selection per skill

**Priority:** P1 (Should Have)
**Estimated Effort:** Small (<1 day)
**Dependencies:** TASK-005

---

## Description

Implement model selection per skill (FR-12). Skills can specify which LLM model to use for reasoning via the `model` field in SKILL.md frontmatter. Supports haiku (fast/cheap), sonnet (balanced), and opus (powerful) with mapping to actual Anthropic model IDs.

## Files to Modify

- `src/omniforge/skills/autonomous_executor.py` - Add model selection logic
- `src/omniforge/skills/models.py` - Ensure model field is parsed

## Implementation Requirements

### Model Mapping

```python
MODEL_MAP = {
    "haiku": "claude-haiku-4",
    "sonnet": "claude-sonnet-4",
    "opus": "claude-opus-4",
}

DEFAULT_MODEL = "claude-sonnet-4"
```

### SKILL.md Configuration

```yaml
---
name: quick-search
description: Fast file search
model: haiku              # Fast, cheap model
max-iterations: 5
---

---
name: complex-analysis
description: Deep code analysis
model: opus               # Powerful reasoning model
max-iterations: 20
---
```

### Model Resolution Logic

In `AutonomousSkillExecutor`:

```python
def _resolve_model(self) -> str:
    """Resolve LLM model to use for this skill."""
    # Priority: config override > skill metadata > default
    if self._config.model:
        return self._resolve_model_name(self._config.model)

    if self._skill.metadata.model:
        return self._resolve_model_name(self._skill.metadata.model)

    return DEFAULT_MODEL

def _resolve_model_name(self, model_hint: str) -> str:
    """Map model hint to actual model ID."""
    return MODEL_MAP.get(model_hint.lower(), model_hint)
```

### Usage in ReAct Loop

```python
llm_result = await engine.call_llm(
    messages=conversation,
    system=system_prompt,
    model=self._resolve_model(),  # Use resolved model
    temperature=self._config.temperature,
)
```

### Cost Tracking

Add model to execution metrics:
```python
metrics["model_used"] = model_id
metrics["estimated_cost_per_call"] = MODEL_COSTS.get(model_id, 0.0)
```

## Acceptance Criteria

- [ ] Skills can specify `model` in frontmatter
- [ ] Supported values: haiku, sonnet, opus
- [ ] Falls back to platform default if not specified
- [ ] Config override takes precedence over skill metadata
- [ ] Model selection logged in execution metrics
- [ ] Invalid model names use the value as-is (future compatibility)
- [ ] Unit tests for model resolution

## Testing

```python
def test_model_from_skill_metadata():
    """Skill with model: haiku should use haiku."""
    skill = create_skill_with_model("haiku")
    executor = AutonomousSkillExecutor(skill, ...)
    assert executor._resolve_model() == "claude-haiku-4"

def test_model_default_fallback():
    """Skills without model use default."""
    skill = create_skill_without_model()
    executor = AutonomousSkillExecutor(skill, ...)
    assert executor._resolve_model() == "claude-sonnet-4"

def test_model_config_override():
    """Config override takes precedence."""
    skill = create_skill_with_model("haiku")
    config = AutonomousConfig(model="opus")
    executor = AutonomousSkillExecutor(skill, ..., config=config)
    assert executor._resolve_model() == "claude-opus-4"

def test_model_unknown_passthrough():
    """Unknown model names are used as-is."""
    skill = create_skill_with_model("claude-3-5-sonnet-20241022")
    executor = AutonomousSkillExecutor(skill, ...)
    assert executor._resolve_model() == "claude-3-5-sonnet-20241022"
```

## Technical Notes

- Model costs for tracking (approximate):
  - haiku: ~$0.25/1M input, ~$1.25/1M output
  - sonnet: ~$3/1M input, ~$15/1M output
  - opus: ~$15/1M input, ~$75/1M output
- Consider adding model to TaskEvent for visibility
- Admin override capability for cost management
