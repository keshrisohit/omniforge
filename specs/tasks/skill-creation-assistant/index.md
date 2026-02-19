# Skill Creation Assistant - Task Index

**Feature**: Conversational agent for creating skills through natural dialogue
**Status**: Not Started
**Created**: 2026-02-03

## Overview

This task breakdown implements the Skill Creation Assistant Agent that enables users to create OmniForge skills (SKILL.md files) through natural conversation. The agent follows official Anthropic Agent Skills guidelines with strict compliance (only `name` and `description` in frontmatter).

## Phase Summary

| Phase | Focus | Tasks | Est. Effort |
|-------|-------|-------|-------------|
| Phase 1 | MVP - Simple Skills | TASK-001 to TASK-007 | 2-3 weeks |
| Phase 2 | Full Patterns | TASK-008, TASK-009 | 1-2 weeks |
| Phase 3 | Storage & UX | TASK-010 | 1 week |

**Total Estimated Effort**: 4-6 weeks

## Task List

### Phase 1: MVP (Simple Skills, Project Storage)

| ID | Subject | Status | Dependencies | Est. Hours |
|----|---------|--------|--------------|------------|
| [TASK-001](TASK-001-core-data-models.md) | Core data models and enums | Pending | None | 2-3 |
| [TASK-002](TASK-002-conversation-state-machine.md) | Conversation state machine | Pending | TASK-001 | 3-4 |
| [TASK-003](TASK-003-requirements-gatherer.md) | Requirements gatherer | Pending | TASK-001, TASK-002 | 3-4 |
| [TASK-004](TASK-004-skill-md-generator.md) | SKILL.md generator | Pending | TASK-001 | 4-5 |
| [TASK-005](TASK-005-skill-validator.md) | Skill validator (Anthropic spec) | Pending | TASK-004 | 3-4 |
| [TASK-006](TASK-006-skill-writer.md) | Skill writer | Pending | TASK-001 | 2-3 |
| [TASK-007](TASK-007-skill-creation-agent.md) | SkillCreationAgent orchestration | Pending | TASK-002 to TASK-006 | 4-5 |

**Phase 1 Total**: ~22-28 hours (2-3 weeks)

### Phase 2: Full Patterns

| ID | Subject | Status | Dependencies | Est. Hours |
|----|---------|--------|--------------|------------|
| [TASK-008](TASK-008-full-pattern-support.md) | Workflow and script-based skill generation | Pending | TASK-004, TASK-007 | 4-5 |
| [TASK-009](TASK-009-resource-generator.md) | Resource generator (scripts/, references/) | Pending | TASK-008 | 3-4 |

**Phase 2 Total**: ~7-9 hours (1-2 weeks)

### Phase 3: Storage & UX

| ID | Subject | Status | Dependencies | Est. Hours |
|----|---------|--------|--------------|------------|
| [TASK-010](TASK-010-storage-and-ux.md) | Storage layer selection and advanced UX | Pending | TASK-007 | 4-5 |

**Phase 3 Total**: ~4-5 hours (1 week)

## Dependency Graph

```
TASK-001 (Models)
    |
    +---> TASK-002 (State Machine)
    |         |
    |         +---> TASK-003 (Requirements Gatherer)
    |         |         |
    |         +---------|---> TASK-007 (Agent)
    |                   |         |
    +---> TASK-004 (Generator) ---+
    |         |                   |
    |         +---> TASK-005 (Validator)
    |         |                   |
    |         +---> TASK-008 (Patterns) ---> TASK-009 (Resources)
    |
    +---> TASK-006 (Writer)
                  |
                  +---> TASK-010 (Storage & UX)
```

## Key Architectural Decisions

1. **State Machine Architecture**: 12-state finite state machine for predictable conversation flows
2. **Official Format Compliance**: Only `name` and `description` in YAML frontmatter
3. **Integration-First**: Leverage existing SkillParser, SkillStorageManager, LLMResponseGenerator
4. **MVP Scope**: Simple skills only, Project storage layer, no versioning

## Component Overview

| Component | File | Purpose |
|-----------|------|---------|
| ConversationState | models.py | 12-state enum for conversation flow |
| SkillPattern | models.py | 4 skill patterns (Simple, Workflow, Reference, Script) |
| ConversationContext | models.py | Accumulated context during conversation |
| ConversationManager | conversation.py | State machine logic |
| RequirementsGatherer | gatherer.py | Question generation, pattern detection |
| SkillMdGenerator | generator.py | SKILL.md content generation |
| SkillValidator | validator.py | Official spec validation |
| SkillWriter | writer.py | Filesystem operations |
| ResourceGenerator | resources.py | Scripts and references generation |
| SkillCreationAgent | agent.py | Main orchestration entry point |

## Exit Criteria

### Phase 1 (MVP)
- Create Simple skills through conversation
- 100% frontmatter compliance (only name and description)
- 100% description format compliance (third person, WHAT + WHEN)
- 90%+ validation success on first attempt
- Unit test coverage > 80%

### Phase 2 (Full Patterns)
- All 4 skill patterns supported
- References generated with proper structure
- Scripts generated and validated

### Phase 3 (Storage & UX)
- All storage layers supported
- Proper permission enforcement
- Duplicate detection functional
- Enhanced error messages and UX

## File Structure

```
src/omniforge/skills/creation/
|-- __init__.py
|-- models.py          # TASK-001
|-- conversation.py    # TASK-002
|-- gatherer.py        # TASK-003
|-- generator.py       # TASK-004
|-- validator.py       # TASK-005
|-- writer.py          # TASK-006
|-- agent.py           # TASK-007
|-- resources.py       # TASK-009
+-- prompts.py         # LLM prompt templates

tests/skills/creation/
|-- test_models.py
|-- test_conversation.py
|-- test_gatherer.py
|-- test_generator.py
|-- test_validator.py
|-- test_writer.py
|-- test_agent.py
|-- test_resources.py
+-- test_integration.py
```

## References

- [Technical Plan](/Users/sohitkumar/code/omniforge/specs/skill-creation-assistant-technical-plan.md)
- [Gap Analysis](/Users/sohitkumar/code/omniforge/specs/skill-creation-assistant-gap-analysis.md)
- [Product Spec](/Users/sohitkumar/code/omniforge/specs/skill-creation-assistant-agent-spec.md)
- [Anthropic Agent Skills Docs](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)
