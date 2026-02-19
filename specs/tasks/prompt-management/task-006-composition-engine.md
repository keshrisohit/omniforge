# TASK-006: Implement Composition Engine

## Objective

Create the main composition engine that orchestrates loading prompts from layers, merging, rendering, and caching.

## Requirements

### Composition Engine (`src/omniforge/prompts/composition/engine.py`)

**CompositionEngine class**:

Constructor:
- `repository: PromptRepository`
- `cache: Optional[CacheManager] = None`
- `experiment_manager: Optional[ExperimentManager] = None`
- Initialize `TemplateRenderer`, `MergeProcessor`, `SafetyValidator`

**Main method**:
`async compose(agent_id, tenant_id, feature_ids, user_input, variables, skip_cache) -> ComposedPrompt`:

1. Resolve tenant from context if not provided
2. Sanitize user input via SafetyValidator
3. Generate cache key
4. Check cache (if not skip_cache)
5. Load prompts from all applicable layers
6. Apply merge logic via MergeProcessor
7. Check for active A/B experiment, select variant if applicable
8. Build complete variable context (namespaced: system.*, tenant.*, agent.*, user.*)
9. Render template via TemplateRenderer
10. Collect version metadata
11. Store in cache
12. Return ComposedPrompt with timing metrics

**Helper methods**:
- `_load_layer_prompts(agent_id, tenant_id, feature_ids)`: Load prompts from each layer
- `_merge_feature_prompts(prompts: list[Prompt])`: Combine multiple feature prompts
- `_build_variable_context(tenant_id, agent_id, user_variables)`: Build namespaced variables
- `_generate_cache_key(...)`: Create deterministic cache key from versions + variables

### Safety Validator (`src/omniforge/prompts/validation/safety.py`)

**SafetyValidator class**:
- `sanitize_user_input(input: str) -> str`: Escape/sanitize user input for safe inclusion
- Prevent prompt injection attacks
- Strip dangerous patterns while preserving intent

### Variable Context Structure
```python
{
    "system": {"platform_name": "OmniForge", "platform_version": "..."},
    "tenant": {"id": tenant_id},
    "agent": {"id": agent_id},
    **user_variables  # User-provided variables
}
```

## Acceptance Criteria
- [ ] Composition loads prompts from all applicable layers
- [ ] Missing layers are skipped gracefully
- [ ] Feature prompts are combined when multiple provided
- [ ] Cache hit returns immediately without recomposition
- [ ] Cache key incorporates all version IDs
- [ ] User input is sanitized before inclusion
- [ ] Variable context is properly namespaced
- [ ] Composition timing is measured and returned
- [ ] Unit tests cover composition flow
- [ ] Integration test with full layer stack

## Dependencies
- TASK-002 (repository)
- TASK-003 (renderer)
- TASK-004 (merge processor)
- TASK-005 (cache manager)

## Estimated Complexity
Complex
