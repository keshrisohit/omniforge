# Conversational Skill Builder - Task Decomposition

**Created**: 2026-01-25
**Technical Plan Version**: 2.0
**Review Status**: APPROVED

---

## Overview

This document organizes the implementation tasks for the Conversational Skill Builder feature. The feature enables non-technical users to create AI agents through natural language conversation.

## Phase Summary

| Phase | Duration | Focus | Tasks |
|-------|----------|-------|-------|
| Phase 1 (MVP) | 6 weeks | Single-skill agents, Notion OAuth, basic execution | TASK-101 to TASK-108 |
| Phase 2 (Multi-Skill) | 6 weeks | Sequential orchestration, scheduling, public skill library | TASK-201 to TASK-206 |
| Phase 3A (Advanced) | 4 weeks | Advanced orchestration (parallel, conditional) | TASK-301 to TASK-303 |
| Phase 3B (B2B2C) | 4 weeks | Enterprise and B2B2C features | TASK-311 to TASK-314 |

---

## Phase 1: MVP (Weeks 1-6)

**Goal**: Single-skill agents via conversation, Notion integration, on-demand execution.

**Exit Criteria**:
- User can create single-skill agent through conversation
- Notion OAuth works end-to-end
- Agent executes on-demand
- 80% test coverage

### Task List

| Task ID | Title | Effort | Dependencies | Priority |
|---------|-------|--------|--------------|----------|
| TASK-101 | Database Models and Repository Layer | 8h | None | P0 |
| TASK-102 | SKILL.md Generator with Claude Code Compliance | 12h | TASK-101 | P0 |
| TASK-103 | Conversation State Machine and Manager | 16h | TASK-101 | P0 |
| TASK-104 | Notion OAuth Integration | 12h | TASK-101 | P0 |
| TASK-105 | Agent Execution Service (Single-Skill) | 12h | TASK-101, TASK-102 | P0 |
| TASK-106 | REST API Endpoints | 10h | TASK-103, TASK-104, TASK-105 | P0 |
| TASK-107 | CLI Commands for Agent Management | 6h | TASK-105 | P1 |
| TASK-108 | Integration Tests and Quality Verification | 12h | TASK-106 | P0 |

### Dependency Graph (Phase 1)

```
TASK-101 (Database Models)
    |
    +---> TASK-102 (SKILL.md Generator)
    |         |
    |         +---> TASK-105 (Execution Service)
    |                    |
    +---> TASK-103 (Conversation Manager)
    |         |
    +---> TASK-104 (OAuth Integration)
    |         |
    |         +---> TASK-106 (REST API)
    |                    |
    |                    +---> TASK-107 (CLI)
    |                    |
    |                    +---> TASK-108 (Integration Tests)
```

---

## Phase 2: Multi-Skill & Scheduling (Weeks 7-12)

**Goal**: Sequential multi-skill agents, scheduled execution, public skill library.

**Exit Criteria**:
- User can create multi-skill sequential agents
- Scheduled execution works reliably
- Can browse and use public skills
- 95% execution success rate

### Task List

| Task ID | Title | Effort | Dependencies | Priority |
|---------|-------|--------|--------------|----------|
| TASK-201 | Sequential Orchestration Engine | 14h | TASK-105 | P0 |
| TASK-202 | APScheduler Integration for Scheduled Execution | 10h | TASK-201 | P0 |
| TASK-203 | Public Skill Library Storage and Discovery | 12h | TASK-102 | P1 |
| TASK-204 | Enhanced Conversation Flows for Multi-Skill | 12h | TASK-103, TASK-201 | P0 |
| TASK-205 | Skill Version Management | 8h | TASK-203 | P1 |
| TASK-206 | Observability and Monitoring | 10h | TASK-201, TASK-202 | P1 |

### Dependency Graph (Phase 2)

```
Phase 1 Complete
    |
    +---> TASK-201 (Sequential Orchestration)
    |         |
    |         +---> TASK-202 (APScheduler)
    |         |         |
    |         |         +---> TASK-206 (Observability)
    |         |
    |         +---> TASK-204 (Multi-Skill Conversation)
    |
    +---> TASK-203 (Public Skill Library)
              |
              +---> TASK-205 (Skill Versioning)
```

---

## Phase 3A: Advanced Orchestration (Weeks 13-16)

**Goal**: Parallel and conditional skill orchestration.

### Task List

| Task ID | Title | Effort | Dependencies | Priority |
|---------|-------|--------|--------------|----------|
| TASK-301 | Parallel Skill Orchestration | 16h | TASK-201 | P1 |
| TASK-302 | Conditional Skill Orchestration | 14h | TASK-301 | P1 |
| TASK-303 | Advanced Error Recovery Strategies | 10h | TASK-301 | P1 |

---

## Phase 3B: B2B2C Enterprise Features (Weeks 17-20)

**Goal**: B2B2C deployment, white-labeling, enterprise features.

### Task List

| Task ID | Title | Effort | Dependencies | Priority |
|---------|-------|--------|--------------|----------|
| TASK-311 | Multi-Tenant Isolation Enhancements | 14h | Phase 2 | P1 |
| TASK-312 | White-Label Infrastructure | 12h | TASK-311 | P2 |
| TASK-313 | Staged Rollout System | 10h | TASK-311 | P2 |
| TASK-314 | Analytics and Usage Dashboard | 12h | TASK-311 | P2 |

---

## Key Integration Points

### Existing Codebase Integration

| Existing Component | Location | How Builder Uses It |
|--------------------|----------|---------------------|
| `SkillLoader` | `src/omniforge/skills/loader.py` | Loads SKILL.md for execution |
| `SkillParser` | `src/omniforge/skills/parser.py` | Parses frontmatter and content |
| `SkillTool` | `src/omniforge/skills/tool.py` | Executes skills via unified interface |
| `SkillMetadata` | `src/omniforge/skills/models.py` | Validates skill metadata |
| `BaseAgent` | `src/omniforge/agents/base.py` | Abstract base for agent implementation |

### New Directory Structure

```
src/omniforge/
├── builder/                    # NEW: Conversational builder
│   ├── __init__.py
│   ├── conversation/
│   │   ├── manager.py          # ConversationManager
│   │   ├── state.py            # ConversationState, phases
│   │   └── prompts.py          # LLM prompts for conversation
│   ├── generation/
│   │   ├── agent_generator.py  # Determines skill composition
│   │   └── skill_md_generator.py # Generates SKILL.md
│   ├── models/
│   │   ├── agent_config.py     # AgentConfig, SkillReference
│   │   └── errors.py           # Builder-specific exceptions
│   └── storage/
│       └── skill_writer.py     # Writes SKILL.md to filesystem
│
├── execution/                  # NEW: Agent execution service
│   ├── __init__.py
│   ├── orchestration/
│   │   └── engine.py           # OrchestrationEngine
│   └── scheduler.py            # APScheduler integration
│
├── integrations/               # NEW: OAuth and integrations
│   ├── __init__.py
│   ├── oauth/
│   │   ├── manager.py          # OAuthManager
│   │   └── providers/
│   │       └── notion.py       # Notion-specific OAuth
│   └── credentials/
│       └── encryption.py       # Fernet credential encryption
│
└── api/routes/
    ├── conversation.py         # NEW: Conversation endpoints
    ├── builder_agents.py       # NEW: Agent CRUD endpoints
    └── oauth.py                # NEW: OAuth callback endpoints
```

---

## Testing Requirements

Each task includes specific test requirements:

- **Unit Tests**: pytest, 80% coverage minimum
- **Integration Tests**: pytest + testcontainers for database
- **SKILL.md Validation**: Format compliance tests
- **OAuth Tests**: Mock OAuth flows with sandbox

---

## References

- Technical Plan: `/Users/sohitkumar/code/omniforge/specs/technical-plan-conversational-skill-builder.md`
- Product Spec: `/Users/sohitkumar/code/omniforge/specs/product-spec-conversational-skill-builder.md`
- Review Findings: `/Users/sohitkumar/code/omniforge/specs/plan-review/conversational-skill-builder-technical-plan-review.md`
- Coding Guidelines: `/Users/sohitkumar/code/omniforge/coding-guidelines.md`
