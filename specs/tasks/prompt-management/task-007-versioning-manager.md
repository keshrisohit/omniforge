# TASK-007: Implement Version Manager

## Objective

Create the version manager for handling prompt version lifecycle including creation, history, and rollback.

## Requirements

### Version Manager (`src/omniforge/prompts/versioning/manager.py`)

**VersionManager class**:

Constructor:
- `repository: PromptRepository`

Methods:

`async create_initial_version(prompt: Prompt, created_by: str) -> PromptVersion`:
- Create version 1 for a new prompt
- Set is_current=True
- Update prompt.current_version_id
- Store version in repository

`async create_version(prompt: Prompt, change_message: str, changed_by: str) -> PromptVersion`:
- Get next version number
- Clear is_current on previous version
- Create new version with is_current=True
- Update prompt.current_version_id
- Return new version

`async get_version(prompt_id: str, version_number: int) -> PromptVersion`:
- Retrieve specific version
- Raise PromptVersionNotFoundError if not found

`async list_versions(prompt_id: str, limit: int = 50) -> list[PromptVersion]`:
- Return versions sorted by version_number descending (newest first)
- Support pagination via limit

`async rollback(prompt_id: str, to_version: int, rolled_back_by: str) -> Prompt`:
- Verify version exists
- Set target version as current
- Create rollback audit entry (could be a new version with message "Rolled back to v{n}")
- Return updated prompt

`async get_current_version(prompt_id: str) -> PromptVersion`:
- Get the currently active version
- Raise error if no current version exists

### Package Init
- `src/omniforge/prompts/versioning/__init__.py`

### Version Immutability
- Versions are never modified after creation
- Rollback creates a new version pointing to old content or sets current pointer

## Acceptance Criteria
- [ ] Initial version is created with version_number=1
- [ ] Subsequent versions increment version_number
- [ ] Only one version can be is_current at a time
- [ ] Rollback correctly restores previous version state
- [ ] Version not found raises appropriate error
- [ ] List returns versions in descending order
- [ ] Unit tests cover version lifecycle
- [ ] Tests verify version immutability

## Dependencies
- TASK-001 (models, errors)
- TASK-002 (repository)

## Estimated Complexity
Medium
