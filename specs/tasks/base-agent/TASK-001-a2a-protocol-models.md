# TASK-001: A2A Protocol Models

**Status**: Completed
**Complexity**: Medium
**Dependencies**: None
**Phase**: 1 - Core Agent Interface

## Objective

Create Pydantic models for A2A protocol entities including agent identity, capabilities, skills, message parts, and artifacts.

## Requirements

1. Create `src/omniforge/agents/models.py` with:
   - `AgentIdentity` - id, name, description, version
   - `AgentCapabilities` - streaming, push_notifications, multi_turn, hitl_support
   - `AgentSkill` - id, name, description, tags, examples, input/output modes
   - `SkillInputMode` and `SkillOutputMode` enums
   - `AuthScheme` enum and `SecurityConfig`
   - `AgentCard` - A2A compliant discovery document
   - `TextPart`, `FilePart`, `DataPart` message parts
   - `Artifact` model for agent outputs
   - `MessagePart` union type

2. Create `src/omniforge/agents/__init__.py` with public exports

3. Follow existing Pydantic patterns from `chat/models.py`

## Acceptance Criteria

- [ ] All models have complete type annotations
- [ ] Field validators where appropriate (e.g., name length limits)
- [ ] `AgentCard` supports JSON alias for camelCase A2A compliance (protocolVersion, serviceEndpoint)
- [ ] Unit tests in `tests/agents/test_models.py` covering serialization/validation
- [ ] mypy passes with strict mode
