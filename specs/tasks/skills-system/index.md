# Skills System - Task Index

**Created**: 2026-01-13
**Technical Plan**: specs/skills-system-technical-plan.md (v1.1)
**Product Spec**: specs/skills-system-spec.md
**Status**: Ready for Implementation

---

## Overview

This task breakdown implements the Agent Skills System for OmniForge, enabling agents to discover and execute specialized capabilities defined in SKILL.md files. The system follows Claude Code's progressive disclosure pattern.

**Total Tasks**: 11 (including 1 optional)
**Estimated Duration**: 3-4 weeks

---

## Phase 1: Foundation (Week 1)

Core data models, parser, and storage management.

| Task ID | Title | Complexity | Dependencies | Status |
|---------|-------|------------|--------------|--------|
| TASK-001 | [Skill Data Models and Error Hierarchy](TASK-001-skill-models-and-errors.md) | Medium | None | Pending |
| TASK-002 | [Skill Parser for YAML Frontmatter](TASK-002-skill-parser.md) | Medium | TASK-001 | Pending |
| TASK-003 | [Skill Storage Manager](TASK-003-skill-storage-manager.md) | Simple | TASK-001 | Pending |

**Phase 1 Deliverables**:
- `src/omniforge/skills/models.py` - Pydantic models
- `src/omniforge/skills/errors.py` - Exception hierarchy
- `src/omniforge/skills/parser.py` - YAML frontmatter parser
- `src/omniforge/skills/storage.py` - 4-layer storage manager
- Unit tests with >80% coverage

---

## Phase 2: Loading & Caching (Week 2)

Skill loader with indexing, caching, and priority resolution.

| Task ID | Title | Complexity | Dependencies | Status |
|---------|-------|------------|--------------|--------|
| TASK-004 | [Skill Loader with Caching](TASK-004-skill-loader.md) | Medium | TASK-001, TASK-002, TASK-003 | Pending |
| TASK-005 | [Skill Hot Reload Support](TASK-005-skill-loader-hot-reload.md) (Optional) | Simple | TASK-004 | Pending |

**Phase 2 Deliverables**:
- `src/omniforge/skills/loader.py` - SkillLoader with caching
- Thread-safe index management
- Performance benchmark: < 100ms for 1000 skills
- Optional: watchdog-based hot reload

---

## Phase 3: Tool Integration (Week 3)

SkillTool, SkillContext, and ToolExecutor integration.

| Task ID | Title | Complexity | Dependencies | Status |
|---------|-------|------------|--------------|--------|
| TASK-006 | [Skill Context and Tool Restrictions](TASK-006-skill-context-and-tool-restrictions.md) | Medium | TASK-001 | Pending |
| TASK-007 | [SkillTool Implementation](TASK-007-skill-tool-implementation.md) | Medium | TASK-004, TASK-006 | Pending |
| TASK-008 | [ToolExecutor Skill Stack Integration](TASK-008-executor-skill-stack-integration.md) | Complex | TASK-006, TASK-007 | Pending |

**Phase 3 Deliverables**:
- `src/omniforge/skills/context.py` - SkillContext for tool restrictions
- `src/omniforge/skills/tool.py` - SkillTool for SKILL.md loading
- Modified `src/omniforge/tools/executor.py` with skill stack
- Script read blocking enforcement
- Exception-safe security model

---

## Phase 4: Rename & Integration (Week 4)

FunctionTool rename, system prompt, and integration tests.

| Task ID | Title | Complexity | Dependencies | Status |
|---------|-------|------------|--------------|--------|
| TASK-009 | [Rename SkillTool to FunctionTool](TASK-009-function-tool-rename.md) | Medium | TASK-007 | Pending |
| TASK-010 | [System Prompt Integration](TASK-010-system-prompt-integration.md) | Medium | TASK-007, TASK-008 | Pending |
| TASK-011 | [Integration Tests](TASK-011-integration-tests.md) | Medium | TASK-008, TASK-009, TASK-010 | Pending |

**Phase 4 Deliverables**:
- `src/omniforge/tools/builtin/function.py` - FunctionTool
- Modified `src/omniforge/agents/cot/prompts.py` - multi-LLM instructions
- Comprehensive integration tests
- Backward compatibility with deprecation warnings

---

## Dependency Graph

```
TASK-001 (Models & Errors)
    │
    ├── TASK-002 (Parser)
    │       │
    │       └── TASK-004 (Loader)
    │               │
    │               ├── TASK-005 (Hot Reload) [Optional]
    │               │
    │               └── TASK-007 (SkillTool)
    │                       │
    │                       ├── TASK-009 (FunctionTool Rename)
    │                       │
    │                       └── TASK-010 (System Prompt)
    │
    ├── TASK-003 (Storage)
    │       │
    │       └── TASK-004 (Loader)
    │
    └── TASK-006 (Context)
            │
            ├── TASK-007 (SkillTool)
            │
            └── TASK-008 (Executor Integration)
                    │
                    └── TASK-011 (Integration Tests)
```

---

## Critical Requirements Addressed

### CRITICAL-1: Multi-LLM Compatibility
- **Addressed in**: TASK-007, TASK-010
- Explicit path resolution examples in SkillTool description and system prompt

### CRITICAL-2: Script Execution Enforcement
- **Addressed in**: TASK-002, TASK-006, TASK-008
- Script detection during parsing, Read blocking in SkillContext

### CRITICAL-3: Tool Restriction Security
- **Addressed in**: TASK-006, TASK-008
- Stack-based tracking, exception-safe, explicit activate/deactivate

### HIGH-1: Storage Layer Detection
- **Addressed in**: TASK-002, TASK-004
- Explicit storage_layer parameter (no path heuristics)

---

## Success Metrics

| Metric | Target | Validation |
|--------|--------|------------|
| Index build time | < 100ms (1000 skills) | Benchmark test |
| Activation latency | < 50ms | Unit test timing |
| Test coverage | > 80% | pytest-cov |
| Type safety | 100% mypy | CI check |
| Tool restriction enforcement | 100% | Integration tests |
| Script read blocking | 100% | Integration tests |

---

## Implementation Notes

1. **Start with TASK-001** - All other tasks depend on core models
2. **Phase 1 is foundational** - Complete before moving to Phase 2
3. **TASK-005 is optional** - Can be deferred if timeline is tight
4. **TASK-008 is complex** - Allow extra time for security testing
5. **Run tests after each task** - Catch regressions early

---

## Files Created/Modified

### New Files
- `src/omniforge/skills/__init__.py`
- `src/omniforge/skills/models.py`
- `src/omniforge/skills/errors.py`
- `src/omniforge/skills/parser.py`
- `src/omniforge/skills/storage.py`
- `src/omniforge/skills/loader.py`
- `src/omniforge/skills/context.py`
- `src/omniforge/skills/tool.py`
- `src/omniforge/tools/builtin/function.py`
- `tests/skills/` (all test files)

### Modified Files
- `src/omniforge/tools/executor.py` - Skill stack integration
- `src/omniforge/tools/builtin/skill.py` - Deprecation wrapper
- `src/omniforge/tools/builtin/__init__.py` - New exports
- `src/omniforge/agents/cot/prompts.py` - Multi-LLM instructions
