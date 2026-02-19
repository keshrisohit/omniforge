# TASK-010: Implement SDK PromptManager Class

## Objective

Create the developer-facing SDK interface for programmatic prompt management operations.

## Requirements

### PromptManager (`src/omniforge/prompts/sdk/manager.py`)

**PromptManager class**:

Constructor:
- `tenant_id: Optional[str] = None` - Default tenant for operations
- `repository: Optional[PromptRepository] = None` - Storage backend (defaults to InMemory)
- Initialize CompositionEngine, VersionManager, SyntaxValidator, CacheManager

**Prompt CRUD**:

`async create_prompt(layer, name, content, scope_id, description, merge_points, variables_schema, created_by) -> Prompt`:
- Validate syntax before creation
- Build MergePointDefinition and VariableSchema from dicts
- Create prompt via repository
- Create initial version
- Return created prompt

`async get_prompt(prompt_id: str) -> Prompt`:
- Get prompt or raise PromptNotFoundError

`async update_prompt(prompt_id, content, change_message, changed_by, merge_points, variables_schema) -> Prompt`:
- Validate syntax
- Create new version via VersionManager
- Invalidate cache
- Return updated prompt

`async delete_prompt(prompt_id: str) -> None`:
- Soft delete via repository
- Invalidate cache

**Versioning**:

`async get_prompt_history(prompt_id: str, limit: int) -> list[PromptVersion]`:
- Return version history

`async rollback_prompt(prompt_id: str, to_version: int, rolled_back_by: str) -> Prompt`:
- Rollback via VersionManager
- Invalidate cache
- Return updated prompt

**Composition**:

`async compose_prompt(agent_id, feature_ids, user_input, variables, skip_cache) -> ComposedPrompt`:
- Delegate to CompositionEngine

**Validation**:

`validate_template(content: str) -> list[str]`:
- Return list of syntax errors (synchronous)

### PromptConfig (`src/omniforge/prompts/sdk/config.py`)

**PromptConfig class** (for agent definitions):
```python
@dataclass
class PromptConfig:
    agent_prompt: str
    variables: dict[str, Any] = field(default_factory=dict)
    merge_behavior: dict[str, MergeBehavior] = field(default_factory=dict)
```

### Package Init
- `src/omniforge/prompts/sdk/__init__.py`
- `src/omniforge/prompts/__init__.py` (main module exports)

## Acceptance Criteria
- [ ] Create prompt validates syntax and creates initial version
- [ ] Update prompt creates new version and invalidates cache
- [ ] Delete is soft delete with cache invalidation
- [ ] Rollback restores previous version
- [ ] Compose delegates to engine correctly
- [ ] PromptConfig works for agent definitions
- [ ] SDK provides clean, documented API
- [ ] Unit tests cover all SDK operations
- [ ] Example usage in docstrings

## Dependencies
- TASK-002 (repository)
- TASK-003 (syntax validator)
- TASK-005 (cache manager)
- TASK-006 (composition engine)
- TASK-007 (version manager)

## Estimated Complexity
Medium
