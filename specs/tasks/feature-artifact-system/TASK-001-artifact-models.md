# TASK-001: Artifact Model Changes

**Status**: Pending  |  **Complexity**: Medium  |  **Dependencies**: None

## Objective

Refactor the `Artifact` model in `src/omniforge/agents/models.py` and add supporting types.

## Requirements

1. Add `ArtifactType(str, Enum)` after `SkillOutputMode` with values: `DOCUMENT`, `DATASET`, `CODE`, `IMAGE`, `STRUCTURED`.

2. Refactor `Artifact` (breaking changes):
   - `id`: required `str` -> `Optional[str] = None` (store generates UUID)
   - `type`: free-form `str` -> `ArtifactType` enum
   - Rename `content` -> `inline_content: Optional[Union[str, dict, list]]`
   - Add required `tenant_id: str`, optional `storage_url`, `mime_type`, `size_bytes` (ge=0), `schema_url`, `created_by_agent_id`, `created_at`
   - Add `model_validator(mode="after")`: at least one of `inline_content` or `storage_url` must be set

3. Add `ArtifactPart(BaseModel)` after `DataPart`: frozen `type="artifact"`, required `artifact_id: str` (min_length=1, max_length=255), optional `title`.

4. Update `MessagePart` union to include `ArtifactPart`.

## Acceptance Criteria

- `Artifact` without `inline_content` and `storage_url` raises `ValidationError`
- `Artifact` without `tenant_id` raises `ValidationError`
- `ArtifactPart` discriminated correctly in `MessagePart` union via `type: "artifact"`
- Existing `TextPart`/`FilePart`/`DataPart` deserialization unaffected
