# TASK-002: Implement Repository Protocol and In-Memory Storage

## Objective

Create the repository protocol defining storage operations and implement a thread-safe in-memory repository for development and testing.

## Requirements

### Repository Protocol (`src/omniforge/prompts/storage/repository.py`)
Define a Protocol class `PromptRepository` with methods:
- **Prompt CRUD**: `create`, `get`, `get_by_layer`, `update`, `delete`, `list_by_tenant`
- **Version Operations**: `create_version`, `get_version`, `list_versions`, `set_current_version`
- **Experiment Operations**: `create_experiment`, `get_experiment`, `get_active_experiment`, `update_experiment`, `list_experiments`

All methods must be async and properly typed.

### In-Memory Implementation (`src/omniforge/prompts/storage/memory.py`)
Implement `InMemoryPromptRepository`:
- Use `asyncio.Lock` for thread safety
- Store prompts, versions, experiments in separate dictionaries
- Enforce unique constraint on (layer, scope_id) for active prompts
- Support soft-delete via `is_active` flag
- Handle UUID parsing for string prompt IDs
- Sort results by appropriate fields (created_at, version_number, etc.)

### Package Init (`src/omniforge/prompts/storage/__init__.py`)
Export `PromptRepository`, `InMemoryPromptRepository`

## Acceptance Criteria
- [ ] Protocol defines all required methods with proper type hints
- [ ] In-memory repository implements all protocol methods
- [ ] Thread safety via asyncio.Lock on all operations
- [ ] Duplicate (layer, scope_id) prevention works correctly
- [ ] Soft delete sets is_active=False, excludes from queries
- [ ] Version operations correctly update is_current flags
- [ ] List operations support pagination (limit, offset)
- [ ] Unit tests cover all CRUD operations
- [ ] Tests verify concurrent access safety

## Dependencies
- TASK-001 (models, enums, errors)

## Estimated Complexity
Medium
