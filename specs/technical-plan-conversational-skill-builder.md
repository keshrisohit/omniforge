# Technical Implementation Plan: Conversational Skill Builder

**Created**: 2026-01-25
**Last Updated**: 2026-01-25
**Version**: 2.0
**Status**: Revised

---

## Revision Notes (v2.0)

This plan has been revised based on the architectural review feedback. Key changes:

| Review Finding | Resolution |
|----------------|------------|
| **Domain Model Confusion** | Clarified: Conversational Skill Builder creates Agents (same as SDK). No separate "automation" concept. Users create Agents that have Skills. |
| **Dual Storage Format Complexity** | Removed agent.json. SKILL.md is single source of truth for execution. Agent metadata (trigger, schedule, sharing) stored in database (AgentConfig table). |
| **SKILL.md Frontmatter Violations** | Enforced Claude Code standard. Frontmatter contains only: name, description, allowed-tools, model, context, user-invocable, priority, tags. |
| **Technology Stack Over-Engineering** | Simplified for MVP: SQLite (dev), PostgreSQL (prod), asyncio (not Celery), APScheduler (not Redis queue), Fernet encryption (not Vault). |
| **Missing Integration with Existing Skills** | Now leverages existing SkillLoader, SkillTool, SkillParser from `src/omniforge/skills/`. |
| **Orchestration Complexity** | Phase 1: Sequential only. Phase 2+: Parallel/conditional after validation. |
| **No SDK Integration Story** | Added SDK interface for programmatic agent creation (same core engine). |

---

## Executive Summary

The Conversational Skill Builder enables non-technical users to create AI Agents through natural language conversation. These are the **same Agents** that SDK users create programmatically - the only difference is the creation UX.

**Key Architectural Decisions**:

1. **Single Agent Concept**: Users create Agents (same class as SDK), not a separate entity. An Agent has one or more Skills (SKILL.md files).

2. **SKILL.md as Single Source of Truth**: Skills follow Claude Code format exactly. Agent metadata (trigger, schedule, sharing) lives in database, not SKILL.md.

3. **Leverage Existing Infrastructure**: Uses existing SkillLoader, SkillTool, SkillParser, and BaseAgent class.

4. **MVP-First Technology Stack**: SQLite for development, PostgreSQL for production. asyncio for orchestration. APScheduler for scheduling. No Kubernetes, no ELK, no Vault.

5. **Sequential Orchestration Only (Phase 1)**: 80% of use cases need sequential only. Parallel and conditional deferred to Phase 2+.

6. **Dual Deployment Model**: Same Agent class works in SDK (standalone) and platform (managed). SKILL.md files are portable.

---

## Table of Contents

1. [Requirements Analysis](#1-requirements-analysis)
2. [Constraints and Assumptions](#2-constraints-and-assumptions)
3. [System Architecture](#3-system-architecture)
4. [Technology Stack](#4-technology-stack)
5. [Component Specifications](#5-component-specifications)
6. [Data Models](#6-data-models)
7. [Integration with Existing Skills System](#7-integration-with-existing-skills-system)
8. [Skill Orchestration](#8-skill-orchestration)
9. [OAuth and Integration Architecture](#9-oauth-and-integration-architecture)
10. [SDK Integration](#10-sdk-integration)
11. [B2B2C Deployment](#11-b2b2c-deployment)
12. [Security Architecture](#12-security-architecture)
13. [Infrastructure and Deployment](#13-infrastructure-and-deployment)
14. [API Specifications](#14-api-specifications)
15. [Testing Strategy](#15-testing-strategy)
16. [Implementation Phases](#16-implementation-phases)
17. [Risk Assessment](#17-risk-assessment)

---

## 1. Requirements Analysis

### 1.1 Functional Requirements

| ID | Requirement | Priority | Phase |
|----|-------------|----------|-------|
| FR-1 | Create Agents through natural language conversation | P0 | 1 |
| FR-2 | Generate SKILL.md files following Claude Code format | P0 | 1 |
| FR-3 | OAuth integration for Notion (MVP) | P0 | 1 |
| FR-4 | Single-skill agents | P0 | 1 |
| FR-5 | Pre-activation testing with dry-run capability | P0 | 1 |
| FR-6 | Agent metadata in database (AgentConfig table) | P0 | 1 |
| FR-7 | Sequential multi-skill orchestration | P1 | 2 |
| FR-8 | Public skill library discovery and reuse | P1 | 2 |
| FR-9 | Scheduled execution (cron-based) | P1 | 2 |
| FR-10 | Event-driven execution (Notion webhooks) | P2 | 3 |
| FR-11 | Parallel skill orchestration | P2 | 3 |
| FR-12 | Conditional skill orchestration | P2 | 3 |
| FR-13 | B2B2C white-label deployment | P2 | 3 |

### 1.2 Non-Functional Requirements

| ID | Requirement | Target | Phase |
|----|-------------|--------|-------|
| NFR-1 | Chatbot response latency | < 3 seconds | 1 |
| NFR-2 | Agent execution success rate | > 95% | 1 |
| NFR-3 | Test coverage | > 80% | All |
| NFR-4 | Schedule reliability | 99.9% on-time | 2 |
| NFR-5 | Concurrent executions | 100+ simultaneous | 2 |
| NFR-6 | B2B2C end customers per agent | 10,000+ | 3 |

### 1.3 Integration Requirements

- **Phase 1**: Notion OAuth 2.0
- **Phase 2**: Slack, Linear OAuth
- **Phase 3**: GitHub, custom webhooks
- **LLM Providers**: Anthropic Claude, OpenAI, OpenRouter (via existing provider infrastructure)

---

## 2. Constraints and Assumptions

### 2.1 Technical Constraints

| Constraint | Impact | Resolution |
|------------|--------|------------|
| Claude Code SKILL.md format compliance | Strict frontmatter fields | Agent metadata in database, not SKILL.md |
| Python 3.9+ requirement | Type hint syntax | Use `list[str]` not `List[str]` |
| Frontend/Backend separation | No shared code | REST API communication only |
| 100-char line length (Black) | Code formatting | Configured in pyproject.toml |
| Existing SkillLoader/SkillTool | Must integrate | Extend, don't replace |

### 2.2 Organizational Standards (from CLAUDE.md)

- SOLID principles for all module design
- Each module must have clean interfaces
- Modules should be replaceable with minimal effort
- Pure functions wherever possible
- 80% minimum test coverage
- Type annotations on all functions

### 2.3 Claude Code SKILL.md Frontmatter Rules

**Allowed Fields (Claude Code Standard)**:
- `name` (required): kebab-case identifier
- `description` (required): One-line, max 80 chars
- `allowed-tools` (optional): Tool restrictions
- `model` (optional): LLM model override
- `context` (optional): inherit or fork
- `user-invocable` (optional): Boolean

**OmniForge Extensions**:
- `priority` (optional): Numeric priority
- `tags` (optional): Categorization tags

**NEVER Include in SKILL.md**:
- `schedule`, `trigger`, `created-by`, `source`, `author`
- These belong in the AgentConfig database table

### 2.4 Assumptions

1. Users have existing Notion workspaces with databases
2. OAuth tokens can be securely stored and refreshed
3. Notion API rate limits are sufficient (3 req/sec)
4. LLM providers support streaming responses
5. Frontend will be built with Next.js 14+ (per CLAUDE.md)

---

## 3. System Architecture

### 3.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND (Next.js)                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ Chat UI      │  │ Agent List   │  │ Skill Library│  │ Test Console │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │ REST API
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           API GATEWAY (FastAPI)                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ Auth MW      │  │ Tenant MW    │  │ Rate Limit   │  │ Error Handler│    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
        ┌─────────────────────────────┼─────────────────────────────┐
        ▼                             ▼                             ▼
┌───────────────────┐  ┌───────────────────┐  ┌───────────────────────────┐
│ BUILDER SERVICE   │  │ EXECUTION SERVICE │  │ INTEGRATION SERVICE       │
│ ┌───────────────┐ │  │ ┌───────────────┐ │  │ ┌───────────────────────┐ │
│ │ Conversation  │ │  │ │ Orchestration │ │  │ │ OAuth Manager         │ │
│ │ Manager       │ │  │ │ Engine        │ │  │ │                       │ │
│ ├───────────────┤ │  │ ├───────────────┤ │  │ ├───────────────────────┤ │
│ │ Agent         │ │  │ │ ┌───────────┐ │ │  │ │ Credential Vault      │ │
│ │ Generator     │ │  │ │ │SkillTool │ │ │  │ │ (Fernet Encryption)   │ │
│ ├───────────────┤ │  │ │ │(existing)│ │ │  │ ├───────────────────────┤ │
│ │ SKILL.md      │ │  │ │ └───────────┘ │ │  │ │ Notion Client         │ │
│ │ Generator     │ │  │ ├───────────────┤ │  │ │                       │ │
│ └───────────────┘ │  │ │ APScheduler   │ │  │ └───────────────────────┘ │
└───────────────────┘  │ │ (scheduling)  │ │  └───────────────────────────┘
                       │ └───────────────┘ │
                       └───────────────────┘
                                │
                                ▼
          ┌─────────────────────────────────────────────────────┐
          │                  EXISTING SKILLS SYSTEM              │
          │  ┌───────────────┐  ┌───────────────┐               │
          │  │ SkillLoader   │  │ SkillParser   │               │
          │  │ (existing)    │  │ (existing)    │               │
          │  └───────────────┘  └───────────────┘               │
          │  ┌───────────────┐  ┌───────────────┐               │
          │  │ SkillTool     │  │ SkillStorage  │               │
          │  │ (existing)    │  │ Manager       │               │
          │  └───────────────┘  └───────────────┘               │
          └─────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           STORAGE LAYER                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                      │
│  │ AgentConfig  │  │ SKILL.md     │  │ Credentials  │                      │
│  │ (Database)   │  │ (File System)│  │ (Encrypted)  │                      │
│  └──────────────┘  └──────────────┘  └──────────────┘                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Key Architectural Principles

1. **Agent = Agent**: The "agent" created by conversational builder is the same `Agent` concept as SDK. It's an instance that can be executed by the platform's runtime agent.

2. **SKILL.md Files Are Portable**: Skills generated by the builder work identically in SDK standalone mode and platform managed mode.

3. **Extend, Don't Replace**: The builder integrates with existing SkillLoader, SkillTool, and SkillParser rather than creating parallel systems.

4. **Database for Metadata, Files for Execution**: AgentConfig table stores scheduling, triggers, sharing. SKILL.md files contain execution instructions only.

### 3.3 Directory Structure for Agent Skills

```
storage/
├── tenants/
│   └── {tenant_id}/
│       └── agents/
│           └── {agent_id}/
│               └── skills/
│                   ├── {skill-name}.md      # SKILL.md (single source of truth)
│                   └── docs/                # Optional supporting docs
│
└── public-skills/                           # Community skill library
    └── {skill-name}/
        ├── SKILL.md
        └── docs/
```

**Note**: No agent.json file. All agent metadata lives in the `agent_configs` database table.

### 3.4 Read vs Write Flow Analysis

| Operation | Flow Type | Complexity | Strategy |
|-----------|-----------|------------|----------|
| List agents | Read | Low | Query AgentConfig table |
| Get agent details | Read | Low | Join AgentConfig + load SKILL.md |
| Create agent | Write | High | Insert AgentConfig + write SKILL.md |
| Update agent | Write | Medium | Update AgentConfig + optionally SKILL.md |
| Execute agent | Read+Write | High | Load via SkillLoader, execute via SkillTool |
| Search public skills | Read | Medium | Full-text search on public_skills table |

### 3.5 Sync vs Async Decision Matrix

| Operation | Mode | Rationale |
|-----------|------|-----------|
| Chat responses | Async (streaming) | User experience |
| Agent creation | Sync | Immediate feedback |
| SKILL.md generation | Async | LLM latency |
| OAuth flow | Sync | Browser redirect |
| Agent execution | Async | Long-running |
| Scheduled triggers | Async (APScheduler) | Background processing |
| Test execution | Async | Duration varies |

---

## 4. Technology Stack

### 4.1 Phase 1 (MVP) Stack

| Component | Technology | Rationale |
|-----------|------------|-----------|
| Framework | FastAPI | Async support, type hints, OpenAPI |
| ORM | SQLAlchemy 2.0 | Async queries, type safety |
| Database (Dev) | SQLite | Zero setup, portable |
| Database (Prod) | PostgreSQL | JSONB, full-text search |
| Background Tasks | asyncio + APScheduler | Simple, no external deps |
| File Storage | Local filesystem | MVP simplicity |
| Secrets | Fernet encryption | Built into cryptography lib |
| Logging | Python logging | RotatingFileHandler |
| Metrics | Basic Prometheus | Counter, histogram |

### 4.2 Phase 2+ Stack (After Validation)

| Component | Technology | When to Add |
|-----------|------------|-------------|
| Cache | Redis | When caching needed for performance |
| Queue | Celery + Redis | When APScheduler insufficient |
| Secrets | AWS Secrets Manager | When multi-tenant credentials scale |
| Logging | ELK Stack | When centralized logging needed |
| Tracing | OpenTelemetry | When distributed tracing needed |
| Orchestration | Kubernetes | When horizontal scaling needed |

### 4.3 Frontend (Next.js)

| Component | Technology | Rationale |
|-----------|------------|-----------|
| Framework | Next.js 14+ | App Router, RSC |
| Language | TypeScript (strict) | Type safety |
| Styling | Tailwind CSS | Utility-first |
| State | React Query | Server state management |
| Forms | React Hook Form + Zod | Validation |
| Chat UI | Custom components | Streaming support |

---

## 5. Component Specifications

### 5.1 Builder Service

#### 5.1.1 Conversation Manager

**Purpose**: Manages the stateful conversation flow for agent creation/editing.

```python
# src/omniforge/builder/conversation/manager.py

from typing import AsyncIterator
from enum import Enum
from pydantic import BaseModel


class ConversationPhase(str, Enum):
    """Phases of agent-building conversation."""
    IDLE = "idle"
    DISCOVERY = "discovery"
    OAUTH_FLOW = "oauth_flow"
    REQUIREMENTS = "requirements"
    GENERATION = "generation"
    TESTING = "testing"
    ACTIVATION = "activation"
    COMPLETE = "complete"


class ConversationState(BaseModel):
    """State of an agent-building conversation."""
    session_id: str
    user_id: str
    tenant_id: str
    phase: ConversationPhase
    context: dict  # Accumulated requirements
    pending_oauth: str | None = None
    draft_agent_id: str | None = None


class ChatResponse(BaseModel):
    """Response from conversation manager."""
    text: str
    phase: ConversationPhase
    actions: list[str] = []  # Suggested user actions
    oauth_url: str | None = None  # If OAuth needed


class ConversationManager:
    """Manages agent-building conversation state and flow."""

    def __init__(
        self,
        agent_generator: "AgentGenerator",
        skill_generator: "SkillMdGenerator",
        oauth_manager: "OAuthManager",
    ) -> None:
        self._agent_gen = agent_generator
        self._skill_gen = skill_generator
        self._oauth = oauth_manager
        self._sessions: dict[str, ConversationState] = {}

    async def start_session(
        self, user_id: str, tenant_id: str
    ) -> ConversationState:
        """Start a new conversation session."""
        ...

    async def process_message(
        self, session_id: str, message: str
    ) -> AsyncIterator[ChatResponse]:
        """Process user message and stream response."""
        ...

    async def complete_oauth(
        self, session_id: str, integration: str, token_data: dict
    ) -> None:
        """Complete pending OAuth flow."""
        ...
```

**State Machine**:
```
IDLE → DISCOVERY → OAUTH_FLOW (if needed) → REQUIREMENTS → GENERATION → TESTING → ACTIVATION → COMPLETE
                        ↓                                     ↑
                  (OAuth complete) ───────────────────────────┘
```

#### 5.1.2 Agent Generator

**Purpose**: Determines skill composition and creates AgentConfig.

```python
# src/omniforge/builder/generation/agent_generator.py

from pydantic import BaseModel


class AgentRequirements(BaseModel):
    """Extracted requirements from conversation."""
    name: str
    description: str
    integrations: list[str]
    trigger_type: str  # on_demand, scheduled, event_driven
    schedule: str | None = None  # cron expression
    data_sources: list[dict]


class SkillSpec(BaseModel):
    """Specification for a skill to generate."""
    name: str
    description: str
    integration: str
    instructions: str
    allowed_tools: list[str]


class AgentGenerator:
    """Generates agent configuration and skill composition."""

    def __init__(self, llm_client: "LLMClient") -> None:
        self._llm = llm_client

    async def analyze_requirements(
        self, conversation_context: dict
    ) -> AgentRequirements:
        """Extract structured requirements from conversation."""
        ...

    async def determine_skills_needed(
        self, requirements: AgentRequirements
    ) -> list[SkillSpec]:
        """Determine what skills the agent needs.

        Phase 1: Always single skill.
        Phase 2+: May return multiple skills for sequential execution.
        """
        ...

    async def find_public_skills(
        self, skill_specs: list[SkillSpec]
    ) -> list[tuple[SkillSpec, "PublicSkill | None"]]:
        """Find matching public skills for each spec."""
        ...
```

#### 5.1.3 SKILL.md Generator

**Purpose**: Generates Claude Code-compliant SKILL.md files.

```python
# src/omniforge/builder/generation/skill_md_generator.py

import yaml
from pydantic import BaseModel


class SkillMdContent(BaseModel):
    """Generated SKILL.md content."""
    name: str
    frontmatter: dict
    body: str

    def to_markdown(self) -> str:
        """Convert to complete SKILL.md content."""
        fm = yaml.dump(self.frontmatter, default_flow_style=False)
        return f"---\n{fm}---\n\n{self.body}"


class SkillMdGenerator:
    """Generates Claude Code-compliant SKILL.md files."""

    # Allowed frontmatter fields per Claude Code spec
    ALLOWED_FRONTMATTER = {
        "name",           # Required
        "description",    # Required
        "allowed-tools",  # Optional
        "model",          # Optional
        "context",        # Optional
        "user-invocable", # Optional
        "priority",       # OmniForge extension
        "tags",           # OmniForge extension
    }

    def __init__(self, llm_client: "LLMClient") -> None:
        self._llm = llm_client

    async def generate(self, spec: "SkillSpec") -> SkillMdContent:
        """Generate SKILL.md content from specification."""
        frontmatter = self._build_frontmatter(spec)
        body = await self._generate_body(spec)
        return SkillMdContent(
            name=spec.name,
            frontmatter=frontmatter,
            body=body,
        )

    def _build_frontmatter(self, spec: "SkillSpec") -> dict:
        """Build valid YAML frontmatter.

        IMPORTANT: Only includes fields allowed by Claude Code spec.
        Agent metadata (schedule, trigger, author) goes in database.
        """
        fm = {
            "name": spec.name,
            "description": spec.description[:80],  # Max 80 chars
        }

        if spec.allowed_tools:
            fm["allowed-tools"] = spec.allowed_tools

        # Never include: schedule, trigger, created-by, source, author
        return fm

    async def _generate_body(self, spec: "SkillSpec") -> str:
        """Generate natural language instructions."""
        prompt = f"""Generate SKILL.md instructions for:

Name: {spec.name}
Description: {spec.description}
Integration: {spec.integration}
Requirements: {spec.instructions}

Output markdown with:
1. Clear heading
2. Prerequisites section
3. Step-by-step instructions in imperative voice
4. Error handling section
5. Keep under 5KB total
"""
        return await self._llm.generate(prompt)

    def validate_frontmatter(self, frontmatter: dict) -> list[str]:
        """Validate frontmatter against Claude Code spec.

        Returns list of validation errors (empty if valid).
        """
        errors = []

        # Check required fields
        if "name" not in frontmatter:
            errors.append("Missing required field: name")
        if "description" not in frontmatter:
            errors.append("Missing required field: description")

        # Check for forbidden fields
        forbidden = {"schedule", "trigger", "created-by", "source", "author"}
        for field in frontmatter:
            if field in forbidden:
                errors.append(f"Forbidden field in SKILL.md: {field}")
            elif field not in self.ALLOWED_FRONTMATTER:
                errors.append(f"Unknown field: {field}")

        return errors
```

### 5.2 Execution Service

#### 5.2.1 Orchestration Engine

**Purpose**: Orchestrates skill execution using existing SkillTool.

```python
# src/omniforge/execution/orchestration/engine.py

from typing import AsyncIterator
from pydantic import BaseModel

from omniforge.skills.loader import SkillLoader
from omniforge.skills.tool import SkillTool
from omniforge.tools.base import ToolCallContext, ToolResult


class ExecutionEvent(BaseModel):
    """Event emitted during execution."""
    type: str  # skill_started, skill_completed, skill_failed
    skill_name: str
    data: dict = {}


class OrchestrationEngine:
    """Orchestrates multi-skill agent execution.

    IMPORTANT: Uses existing SkillTool for execution, not a parallel system.

    Phase 1: Sequential execution only.
    Phase 2+: Add parallel and conditional support.
    """

    def __init__(
        self,
        skill_loader: SkillLoader,
        skill_tool: SkillTool,
    ) -> None:
        self._loader = skill_loader
        self._skill_tool = skill_tool

    async def execute_agent(
        self,
        agent_config: "AgentConfig",
        context: ToolCallContext,
        input_data: dict,
    ) -> AsyncIterator[ExecutionEvent]:
        """Execute all skills for an agent.

        Phase 1: Sequential only - skills execute in order.
        """
        skills = agent_config.skills  # List of SkillReference
        current_output = input_data

        for skill_ref in sorted(skills, key=lambda s: s.order):
            yield ExecutionEvent(
                type="skill_started",
                skill_name=skill_ref.name,
            )

            try:
                # Use existing SkillTool for execution
                result = await self._skill_tool.execute(
                    context=context,
                    arguments={
                        "skill_name": skill_ref.name,
                        "args": str(current_output),
                    },
                )

                if result.success:
                    current_output = result.result or {}
                    yield ExecutionEvent(
                        type="skill_completed",
                        skill_name=skill_ref.name,
                        data={"output": current_output},
                    )
                else:
                    yield ExecutionEvent(
                        type="skill_failed",
                        skill_name=skill_ref.name,
                        data={"error": result.error},
                    )
                    return  # Stop on failure

            except Exception as e:
                yield ExecutionEvent(
                    type="skill_failed",
                    skill_name=skill_ref.name,
                    data={"error": str(e)},
                )
                return

    async def execute_single_skill(
        self,
        skill_name: str,
        context: ToolCallContext,
        input_data: dict,
    ) -> ToolResult:
        """Execute a single skill via SkillTool."""
        return await self._skill_tool.execute(
            context=context,
            arguments={
                "skill_name": skill_name,
                "args": str(input_data),
            },
        )
```

#### 5.2.2 Scheduler

**Purpose**: Manages scheduled agent execution using APScheduler.

```python
# src/omniforge/execution/scheduler.py

from datetime import datetime
from typing import Callable
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from pydantic import BaseModel


class ScheduleConfig(BaseModel):
    """Schedule configuration."""
    agent_id: str
    tenant_id: str
    cron_expression: str
    timezone: str = "UTC"
    enabled: bool = True


class AgentScheduler:
    """Manages scheduled agent execution.

    Uses APScheduler (not Celery) for MVP simplicity.
    Phase 2+: Migrate to Celery if needed for scale.
    """

    def __init__(self, execution_callback: Callable) -> None:
        self._scheduler = AsyncIOScheduler()
        self._execute = execution_callback
        self._jobs: dict[str, str] = {}  # agent_id -> job_id

    def start(self) -> None:
        """Start the scheduler."""
        self._scheduler.start()

    def stop(self) -> None:
        """Stop the scheduler."""
        self._scheduler.shutdown()

    def add_schedule(self, config: ScheduleConfig) -> str:
        """Add a scheduled agent execution."""
        trigger = CronTrigger.from_crontab(
            config.cron_expression,
            timezone=config.timezone,
        )

        job = self._scheduler.add_job(
            self._execute,
            trigger=trigger,
            args=[config.agent_id, config.tenant_id],
            id=f"agent_{config.agent_id}",
            replace_existing=True,
        )

        self._jobs[config.agent_id] = job.id
        return job.id

    def remove_schedule(self, agent_id: str) -> None:
        """Remove a scheduled agent execution."""
        if agent_id in self._jobs:
            self._scheduler.remove_job(self._jobs[agent_id])
            del self._jobs[agent_id]

    def update_schedule(self, config: ScheduleConfig) -> None:
        """Update an existing schedule."""
        self.remove_schedule(config.agent_id)
        if config.enabled:
            self.add_schedule(config)
```

---

## 6. Data Models

### 6.1 AgentConfig Model (Database)

**IMPORTANT**: This replaces the agent.json file. All agent metadata lives here.

```python
# src/omniforge/builder/models/agent_config.py

from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field


class TriggerType(str, Enum):
    """Agent trigger types."""
    ON_DEMAND = "on_demand"
    SCHEDULED = "scheduled"
    EVENT_DRIVEN = "event_driven"


class AgentStatus(str, Enum):
    """Agent lifecycle status."""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class SharingLevel(str, Enum):
    """Agent sharing levels."""
    PRIVATE = "private"
    TEAM = "team"
    B2B2C = "b2b2c"


class SkillReference(BaseModel):
    """Reference to a skill within an agent."""
    name: str          # SKILL.md name (kebab-case)
    order: int         # Execution order (1, 2, 3...)
    source: str        # "custom" or "public"
    config: dict = {}  # Runtime configuration (passed as args)


class AgentConfig(BaseModel):
    """Agent configuration stored in database.

    NOTE: This is NOT stored in agent.json. SKILL.md is the only file.
    This model represents database table row.
    """
    id: str = Field(..., min_length=1, max_length=64)
    tenant_id: str
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., max_length=1024)
    status: AgentStatus = AgentStatus.DRAFT

    # Trigger configuration (NOT in SKILL.md)
    trigger_type: TriggerType = TriggerType.ON_DEMAND
    schedule: str | None = None  # cron expression
    event_config: dict | None = None

    # Skills (references to SKILL.md files)
    skills: list[SkillReference]

    # Integrations used
    integrations: list[str]

    # Metadata (NOT in SKILL.md)
    created_by: str
    created_at: datetime
    updated_at: datetime
    version: int = 1

    # Sharing (NOT in SKILL.md)
    sharing_level: SharingLevel = SharingLevel.PRIVATE
    shared_with: list[str] = []

    # Usage tracking
    total_runs: int = 0
    successful_runs: int = 0
    last_run: datetime | None = None
```

### 6.2 Database Schema (SQLite/PostgreSQL)

```sql
-- Agent configurations (replaces agent.json)
CREATE TABLE agent_configs (
    id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(32) NOT NULL DEFAULT 'draft',

    -- Trigger configuration
    trigger_type VARCHAR(32) NOT NULL DEFAULT 'on_demand',
    schedule VARCHAR(100),          -- cron expression
    event_config JSON,

    -- Skills (JSON array of SkillReference)
    skills JSON NOT NULL DEFAULT '[]',

    -- Integrations
    integrations JSON NOT NULL DEFAULT '[]',

    -- Metadata
    created_by VARCHAR(64) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    version INTEGER NOT NULL DEFAULT 1,

    -- Sharing
    sharing_level VARCHAR(32) NOT NULL DEFAULT 'private',
    shared_with JSON NOT NULL DEFAULT '[]',

    -- Usage
    total_runs INTEGER NOT NULL DEFAULT 0,
    successful_runs INTEGER NOT NULL DEFAULT 0,
    last_run TIMESTAMP
);

CREATE INDEX idx_agent_configs_tenant ON agent_configs(tenant_id);
CREATE INDEX idx_agent_configs_status ON agent_configs(status);
CREATE INDEX idx_agent_configs_created_by ON agent_configs(created_by);


-- OAuth credentials (encrypted)
CREATE TABLE credentials (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    tenant_id VARCHAR(64) NOT NULL,
    integration_id VARCHAR(64) NOT NULL,
    access_token_encrypted BLOB NOT NULL,
    refresh_token_encrypted BLOB,
    token_type VARCHAR(32) NOT NULL DEFAULT 'Bearer',
    expires_at TIMESTAMP,
    scopes JSON NOT NULL DEFAULT '[]',
    workspace_name VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(user_id, tenant_id, integration_id)
);


-- Agent execution logs
CREATE TABLE agent_executions (
    id VARCHAR(64) PRIMARY KEY,
    agent_id VARCHAR(64) NOT NULL,
    tenant_id VARCHAR(64) NOT NULL,
    triggered_by VARCHAR(64) NOT NULL,  -- user_id or 'scheduler'
    trigger_type VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    result JSON,
    error TEXT,
    skill_results JSON NOT NULL DEFAULT '[]',

    FOREIGN KEY (agent_id) REFERENCES agent_configs(id)
);

CREATE INDEX idx_executions_agent ON agent_executions(agent_id);
CREATE INDEX idx_executions_tenant ON agent_executions(tenant_id);


-- Public skill library (Phase 2)
CREATE TABLE public_skills (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(64) NOT NULL UNIQUE,
    description VARCHAR(1024) NOT NULL,
    content TEXT NOT NULL,              -- SKILL.md content
    author_id VARCHAR(64) NOT NULL,
    tags JSON NOT NULL DEFAULT '[]',
    integrations JSON NOT NULL DEFAULT '[]',
    usage_count INTEGER NOT NULL DEFAULT 0,
    rating_avg REAL NOT NULL DEFAULT 0,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_public_skills_name ON public_skills(name);
CREATE INDEX idx_public_skills_usage ON public_skills(usage_count DESC);
```

### 6.3 File System Structure

```
storage/
├── tenants/
│   └── {tenant_id}/
│       └── agents/
│           └── {agent_id}/
│               └── skills/
│                   ├── weekly-report.md     # SKILL.md file
│                   ├── slack-poster.md      # Another skill
│                   └── docs/                # Optional docs
│                       └── notion-api.md
│
└── public-skills/
    └── notion-weekly-summary/
        ├── SKILL.md
        └── docs/
```

**Note**: No `agent.json` file exists. Agent metadata is in `agent_configs` table.

---

## 7. Integration with Existing Skills System

### 7.1 Leveraging Existing Infrastructure

The builder integrates with existing skills system components:

| Existing Component | Location | How Builder Uses It |
|--------------------|----------|---------------------|
| `SkillLoader` | `src/omniforge/skills/loader.py` | Loads SKILL.md files for execution |
| `SkillParser` | `src/omniforge/skills/parser.py` | Parses frontmatter and content |
| `SkillTool` | `src/omniforge/skills/tool.py` | Executes skills via unified interface |
| `SkillMetadata` | `src/omniforge/skills/models.py` | Validates skill metadata |
| `SkillStorageManager` | `src/omniforge/skills/storage.py` | Multi-layer storage resolution |

### 7.2 Storage Layer Configuration

```python
# Extend existing StorageConfig for builder

from omniforge.skills.storage import StorageConfig, StorageLayer


def create_builder_storage_config(tenant_id: str) -> StorageConfig:
    """Create storage config for conversational builder.

    Layer priority (highest to lowest):
    1. Agent-specific skills (tenant/{tenant_id}/agents/{agent_id}/skills/)
    2. Tenant skills (tenant/{tenant_id}/skills/)
    3. Public skills (public-skills/)
    4. Global skills (global/)
    """
    return StorageConfig(
        # Existing layers
        global_path="storage/global",

        # Tenant layer
        tenant_path=f"storage/tenants/{tenant_id}/skills",

        # Public library
        plugin_paths=["storage/public-skills"],
    )
```

### 7.3 Writing Skills to Storage

```python
# src/omniforge/builder/storage/skill_writer.py

from pathlib import Path
from omniforge.skills.parser import SkillParser


class SkillWriter:
    """Writes generated SKILL.md files to storage."""

    def __init__(self, base_path: Path) -> None:
        self._base = base_path
        self._parser = SkillParser()

    def write_skill(
        self,
        tenant_id: str,
        agent_id: str,
        skill_content: "SkillMdContent",
    ) -> Path:
        """Write SKILL.md to agent's skill directory."""
        skill_dir = self._base / "tenants" / tenant_id / "agents" / agent_id / "skills"
        skill_dir.mkdir(parents=True, exist_ok=True)

        skill_path = skill_dir / f"{skill_content.name}.md"
        skill_path.write_text(skill_content.to_markdown())

        # Validate written skill is parseable
        self._parser.parse_full(skill_path, storage_layer=f"tenant-{tenant_id}")

        return skill_path

    def delete_skill(
        self,
        tenant_id: str,
        agent_id: str,
        skill_name: str,
    ) -> None:
        """Delete a skill file."""
        skill_path = (
            self._base / "tenants" / tenant_id / "agents" / agent_id /
            "skills" / f"{skill_name}.md"
        )
        if skill_path.exists():
            skill_path.unlink()
```

---

## 8. Skill Orchestration

### 8.1 Phase 1: Sequential Only

**Rationale**: 80% of user automations need sequential execution. Defer complexity.

```python
# Simple sequential orchestration

async def execute_sequential(
    skills: list[SkillReference],
    skill_tool: SkillTool,
    context: ToolCallContext,
    initial_input: dict,
) -> dict:
    """Execute skills sequentially, passing output to next skill."""
    current_data = initial_input

    for skill in sorted(skills, key=lambda s: s.order):
        result = await skill_tool.execute(
            context=context,
            arguments={
                "skill_name": skill.name,
                "args": str(current_data),
            },
        )

        if not result.success:
            raise SkillExecutionError(skill.name, result.error)

        # Output flows to next skill
        current_data = result.result or {}

    return current_data
```

### 8.2 Phase 2+: Parallel and Conditional (Deferred)

**Validation Criteria for Adding Complexity**:
- 30%+ of users request parallel/conditional
- Clear use cases that can't be solved with sequential
- Infrastructure proven stable with sequential

When validated, add:
- `execute_parallel()` - Run independent skills concurrently
- `execute_conditional()` - Run skills based on condition evaluation

---

## 9. OAuth and Integration Architecture

### 9.1 OAuth Flow (Notion MVP)

```
User clicks "Connect Notion"
        │
        ▼
┌───────────────────┐
│ POST /oauth/init  │──────► OAuthManager.initiate_flow()
└───────────────────┘                    │
        │                                │
        ▼                                ▼
   {auth_url, state}              Store state in DB
        │
        ▼
   Redirect to Notion
        │
        ▼
   User authorizes
        │
        ▼
   Redirect to callback
        │
        ▼
┌───────────────────┐
│ POST /oauth/      │──────► OAuthManager.complete_flow()
│ callback          │                    │
└───────────────────┘                    │
                                         ▼
                                   Exchange code for tokens
                                         │
                                         ▼
                                   Encrypt & store in DB
                                         │
                                         ▼
                                   Return credential_id
```

### 9.2 OAuth Manager

```python
# src/omniforge/integrations/oauth/manager.py

from pydantic import BaseModel
from cryptography.fernet import Fernet


class OAuthConfig(BaseModel):
    """OAuth configuration for an integration."""
    integration_id: str  # "notion", "slack", etc.
    client_id: str
    client_secret: str
    authorize_url: str
    token_url: str
    scopes: list[str]
    redirect_uri: str


class OAuthManager:
    """Manages OAuth flows for integrations.

    MVP uses Fernet encryption for credentials.
    Phase 2+: Migrate to AWS Secrets Manager for multi-tenant.
    """

    def __init__(
        self,
        configs: dict[str, OAuthConfig],
        encryption_key: bytes,
        db_session: "AsyncSession",
    ) -> None:
        self._configs = configs
        self._fernet = Fernet(encryption_key)
        self._db = db_session

    async def initiate_flow(
        self,
        integration_id: str,
        user_id: str,
        tenant_id: str,
        session_id: str,
    ) -> tuple[str, str]:
        """Initiate OAuth flow.

        Returns: (authorize_url, state)
        """
        config = self._configs[integration_id]
        state = self._generate_state(user_id, tenant_id, session_id)

        # Store state for callback validation
        await self._store_state(state, user_id, tenant_id, integration_id)

        auth_url = (
            f"{config.authorize_url}"
            f"?client_id={config.client_id}"
            f"&redirect_uri={config.redirect_uri}"
            f"&response_type=code"
            f"&scope={'+'.join(config.scopes)}"
            f"&state={state}"
        )

        return auth_url, state

    async def complete_flow(
        self,
        code: str,
        state: str,
    ) -> str:
        """Complete OAuth flow and store credentials.

        Returns: credential_id
        """
        # Validate and retrieve state
        state_data = await self._validate_state(state)
        config = self._configs[state_data.integration_id]

        # Exchange code for tokens
        tokens = await self._exchange_code(config, code)

        # Encrypt and store
        credential_id = await self._store_credential(
            user_id=state_data.user_id,
            tenant_id=state_data.tenant_id,
            integration_id=state_data.integration_id,
            tokens=tokens,
        )

        return credential_id

    async def get_access_token(
        self,
        credential_id: str,
        user_id: str,
        tenant_id: str,
    ) -> str:
        """Get access token, refreshing if expired."""
        credential = await self._get_credential(credential_id)

        # Verify ownership
        if credential.user_id != user_id or credential.tenant_id != tenant_id:
            raise PermissionError("Credential access denied")

        # Check expiry and refresh if needed
        if credential.is_expired():
            credential = await self._refresh_token(credential)

        # Decrypt and return
        return self._fernet.decrypt(credential.access_token_encrypted).decode()
```

### 9.3 Credential Encryption (MVP)

```python
# src/omniforge/integrations/credentials/encryption.py

from cryptography.fernet import Fernet


class CredentialEncryption:
    """Simple Fernet encryption for credentials.

    MVP: Single key stored in environment variable.
    Phase 2+: Per-tenant keys via AWS KMS.
    """

    def __init__(self, key: bytes) -> None:
        self._fernet = Fernet(key)

    def encrypt(self, plaintext: str) -> bytes:
        """Encrypt credential."""
        return self._fernet.encrypt(plaintext.encode())

    def decrypt(self, ciphertext: bytes) -> str:
        """Decrypt credential."""
        return self._fernet.decrypt(ciphertext).decode()


def generate_encryption_key() -> bytes:
    """Generate a new Fernet key.

    Run once at deployment, store in CREDENTIAL_ENCRYPTION_KEY env var.
    """
    return Fernet.generate_key()
```

---

## 10. SDK Integration

### 10.1 Dual Deployment Model

The same Agent concept works in both SDK and platform:

```
┌─────────────────────────────────────────────────────────────────┐
│                      SAME AGENT CLASS                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   SDK (Standalone)              Platform (Managed)               │
│   ────────────────              ─────────────────                │
│                                                                  │
│   # Create programmatically     # Created via conversation       │
│   agent = Agent(                # Stored in AgentConfig DB       │
│       name="weekly-reporter",   # Same SKILL.md files            │
│       skills=[skill_ref],       # Same SkillTool execution       │
│   )                                                              │
│                                                                  │
│   # Execute locally             # Execute via platform API       │
│   result = await agent.run()    result = await client.run(id)    │
│                                                                  │
│   # SKILL.md files portable     # Same SKILL.md files            │
│   # between SDK and platform    # Same execution logic           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 10.2 SDK Interface for Agent Creation

```python
# SDK usage - creates same agent as conversational builder

from omniforge import Agent, SkillRef

# Create agent programmatically
agent = Agent(
    name="weekly-reporter",
    description="Generate weekly reports from Notion and post to Slack",
    skills=[
        SkillRef(
            name="notion-weekly-summary",
            source="public",  # From public library
            order=1,
            config={"databases": ["Client Projects"]},
        ),
        SkillRef(
            name="slack-poster",
            source="custom",  # Custom skill
            order=2,
            config={"channel": "#team-updates"},
        ),
    ],
    trigger_type="scheduled",
    schedule="0 8 * * MON",  # Every Monday 8am
)

# Test locally
result = await agent.test(dry_run=True)
print(result)

# Deploy to platform (optional)
deployment = await agent.deploy(platform_url="https://api.omniforge.ai")
print(f"Deployed: {deployment.agent_id}")
```

### 10.3 Platform Client for SDK

```python
# SDK client for platform interaction

from omniforge.client import OmniForgeClient

client = OmniForgeClient(
    api_key="of_sk_...",
    base_url="https://api.omniforge.ai",
)

# List agents created via conversational builder
agents = await client.agents.list()

# Run agent
result = await client.agents.run(
    agent_id="weekly-reporter-123",
    input_data={"timeframe": "7 days"},
)

# Get execution logs
logs = await client.agents.get_executions(agent_id="weekly-reporter-123")
```

---

## 11. B2B2C Deployment

### 11.1 Overview (Phase 3)

B2B2C enables Tier 2 customers to deploy agents to their end customers (Tier 3).

```
OmniForge Platform (Tier 1)
└─ Customer Organization (Tier 2)
   ├─ Creates agents via conversation
   ├─ Configures white-labeling
   └─ Deploys to End Customers (Tier 3)
      ├─ End Customer A (isolated tenant)
      ├─ End Customer B (isolated tenant)
      └─ End Customer C (isolated tenant)
```

### 11.2 Key Capabilities (Deferred to Phase 3)

| Capability | Description |
|------------|-------------|
| White-labeled Portal | Custom branding, domain |
| Multi-tenant Isolation | Separate credentials per end customer |
| Centralized Updates | Tier 2 updates agent, propagates to all |
| Usage Analytics | Per-end-customer tracking |
| Staged Rollout | Test with subset before full deploy |

### 11.3 Database Schema Extension (Phase 3)

```sql
-- B2B2C organizations
CREATE TABLE b2b2c_orgs (
    id VARCHAR(64) PRIMARY KEY,
    tier2_tenant_id VARCHAR(64) NOT NULL,
    name VARCHAR(255) NOT NULL,
    branding JSON,
    custom_domain VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- B2B2C end customers
CREATE TABLE b2b2c_customers (
    id VARCHAR(64) PRIMARY KEY,
    org_id VARCHAR(64) NOT NULL,
    external_id VARCHAR(255),  -- Tier 2's customer identifier
    config JSON,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (org_id) REFERENCES b2b2c_orgs(id)
);

-- Per-customer agent config overrides
CREATE TABLE b2b2c_agent_configs (
    id VARCHAR(64) PRIMARY KEY,
    customer_id VARCHAR(64) NOT NULL,
    agent_id VARCHAR(64) NOT NULL,
    config_overrides JSON,
    enabled BOOLEAN DEFAULT true,

    FOREIGN KEY (customer_id) REFERENCES b2b2c_customers(id),
    FOREIGN KEY (agent_id) REFERENCES agent_configs(id)
);
```

---

## 12. Security Architecture

### 12.1 Authentication & Authorization

| Layer | Mechanism | Phase |
|-------|-----------|-------|
| API Auth | JWT tokens (existing) | 1 |
| Multi-tenancy | tenant_id in all queries | 1 |
| RBAC | Role-based permissions | 2 |
| SSO | SAML/OIDC integration | 3 |

### 12.2 Credential Security

| Concern | Solution | Phase |
|---------|----------|-------|
| Token Storage | Fernet encryption | 1 |
| Key Management | Env var (MVP) | 1 |
| Per-tenant Keys | AWS KMS | 2 |
| Token Rotation | Auto-refresh on expiry | 1 |
| Access Control | User+tenant ownership check | 1 |

### 12.3 Execution Isolation

| Concern | Solution | Phase |
|---------|----------|-------|
| Skill Sandboxing | Tool restrictions via allowed-tools | 1 |
| Resource Limits | Timeout per skill execution | 1 |
| Network Isolation | Container isolation | 3 |

---

## 13. Infrastructure and Deployment

### 13.1 Phase 1 (MVP) Infrastructure

```
┌─────────────────────────────────────────────┐
│           Single Server Deployment           │
│                                              │
│  ┌────────────┐  ┌────────────┐             │
│  │ FastAPI    │  │ Next.js    │             │
│  │ Backend    │  │ Frontend   │             │
│  └────────────┘  └────────────┘             │
│         │                                    │
│         ▼                                    │
│  ┌────────────┐  ┌────────────┐             │
│  │ SQLite/    │  │ File       │             │
│  │ PostgreSQL │  │ Storage    │             │
│  └────────────┘  └────────────┘             │
│                                              │
│  ┌────────────┐                              │
│  │ APScheduler│  (In-process)               │
│  └────────────┘                              │
└─────────────────────────────────────────────┘
```

### 13.2 Environment Configuration

```bash
# .env for MVP

# Database
DATABASE_URL=sqlite:///storage/omniforge.db
# DATABASE_URL=postgresql://user:pass@localhost/omniforge  # Production

# Credential Encryption
CREDENTIAL_ENCRYPTION_KEY=<fernet-key>

# OAuth (Notion)
NOTION_CLIENT_ID=<client-id>
NOTION_CLIENT_SECRET=<client-secret>
NOTION_REDIRECT_URI=https://app.omniforge.ai/oauth/callback/notion

# LLM
ANTHROPIC_API_KEY=<api-key>

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/omniforge.log
```

### 13.3 Phase 2+ Infrastructure (When Needed)

```
┌────────────────────────────────────────────────────────────────┐
│                     Scaled Deployment                           │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ API Server 1 │  │ API Server 2 │  │ API Server N │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│           │                │                │                  │
│           └────────────────┼────────────────┘                  │
│                            ▼                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ PostgreSQL   │  │ Redis        │  │ S3           │         │
│  │ (Primary)    │  │ (Cache/Queue)│  │ (Skills)     │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                │
│  ┌──────────────┐  ┌──────────────┐                            │
│  │ Celery       │  │ ELK Stack    │                            │
│  │ Workers      │  │ (Logging)    │                            │
│  └──────────────┘  └──────────────┘                            │
└────────────────────────────────────────────────────────────────┘
```

---

## 14. API Specifications

### 14.1 Conversation API

```yaml
# POST /api/v1/conversation/start
# Start a new agent-building conversation

Request:
  {}

Response:
  session_id: string
  message: string
  phase: "discovery"


# POST /api/v1/conversation/{session_id}/message
# Send message in conversation

Request:
  message: string

Response:
  text: string
  phase: string
  actions: string[]
  oauth_url: string | null


# POST /api/v1/conversation/{session_id}/oauth-complete
# Complete OAuth flow

Request:
  integration: string
  code: string
  state: string

Response:
  success: boolean
  workspace_name: string
```

### 14.2 Agent API

```yaml
# GET /api/v1/agents
# List user's agents

Response:
  agents:
    - id: string
      name: string
      description: string
      status: string
      trigger_type: string
      skills: SkillReference[]
      last_run: timestamp | null


# GET /api/v1/agents/{agent_id}
# Get agent details

Response:
  id: string
  name: string
  description: string
  status: string
  trigger_type: string
  schedule: string | null
  skills: SkillReference[]
  integrations: string[]
  usage_stats:
    total_runs: int
    successful_runs: int
    last_run: timestamp | null


# POST /api/v1/agents/{agent_id}/run
# Execute agent on-demand

Request:
  input_data: object

Response:
  execution_id: string
  status: "pending"


# GET /api/v1/agents/{agent_id}/executions
# List agent executions

Response:
  executions:
    - id: string
      status: string
      started_at: timestamp
      completed_at: timestamp | null
      result: object | null
      error: string | null
```

---

## 15. Testing Strategy

### 15.1 Testing Pyramid

| Level | Coverage | Tools |
|-------|----------|-------|
| Unit Tests | 80%+ | pytest |
| Integration Tests | Key flows | pytest + testcontainers |
| E2E Tests | Critical paths | Playwright |

### 15.2 Agent Testing

```python
# Test framework for agents

class AgentTestRunner:
    """Test runner for agent validation."""

    async def dry_run(
        self,
        agent_config: AgentConfig,
        mock_data: dict,
    ) -> TestResult:
        """Execute agent with mocked integrations.

        - Skills execute with mock API responses
        - No real API calls made
        - Validates skill composition works
        """
        ...

    async def integration_test(
        self,
        agent_config: AgentConfig,
        test_credentials: dict,
    ) -> TestResult:
        """Execute agent with real integrations.

        - Uses real API credentials
        - Accesses actual Notion data
        - Validates end-to-end flow
        """
        ...
```

### 15.3 Test Coverage Requirements

| Component | Min Coverage | Critical Paths |
|-----------|--------------|----------------|
| ConversationManager | 80% | State transitions |
| SkillMdGenerator | 90% | Frontmatter validation |
| OrchestrationEngine | 85% | Sequential execution |
| OAuthManager | 90% | Token exchange, refresh |
| AgentConfig CRUD | 80% | Create, update, delete |

---

## 16. Implementation Phases

### Phase 1: MVP (Weeks 1-6)

**Goal**: Single-skill agents via conversation, Notion integration, on-demand execution.

| Week | Deliverables |
|------|--------------|
| 1-2 | ConversationManager, state machine |
| 2-3 | SKILL.md Generator, validation |
| 3-4 | OAuth Manager (Notion), credential storage |
| 4-5 | OrchestrationEngine (single skill), AgentConfig CRUD |
| 5-6 | Testing, API documentation, basic frontend |

**Exit Criteria**:
- User can create single-skill agent through conversation
- Notion OAuth works end-to-end
- Agent executes on-demand
- 80% test coverage

### Phase 2: Multi-Skill & Scheduling (Weeks 7-12)

**Goal**: Sequential multi-skill agents, scheduled execution, public skill library.

| Week | Deliverables |
|------|--------------|
| 7-8 | Multi-skill sequential orchestration |
| 8-9 | APScheduler integration |
| 9-10 | Public skill library (read-only) |
| 10-11 | Slack OAuth integration |
| 11-12 | Performance optimization, monitoring |

**Exit Criteria**:
- User can create multi-skill sequential agents
- Scheduled execution works reliably
- Can browse and use public skills
- 95% execution success rate

### Phase 3: Enterprise & B2B2C (Weeks 13-20)

**Goal**: Parallel orchestration, B2B2C deployment, enterprise features.

| Week | Deliverables |
|------|--------------|
| 13-14 | Parallel skill orchestration |
| 15-16 | Conditional skill orchestration |
| 17-18 | B2B2C tenant isolation |
| 18-19 | White-label portal |
| 19-20 | Advanced analytics, staged rollout |

**Exit Criteria**:
- Complex orchestration patterns work
- B2B2C customers can deploy to 1000+ end users
- Enterprise-grade security and monitoring

---

## 17. Risk Assessment

### 17.1 Technical Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| LLM generates invalid SKILL.md | High | Medium | Strict validation, retry with feedback |
| OAuth token refresh failures | High | Low | Proactive refresh, user notification |
| APScheduler reliability at scale | Medium | Medium | Phase 2: Migrate to Celery |
| Skill execution timeout | Medium | Medium | Configurable timeouts, graceful termination |

### 17.2 Product Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Users need parallel execution MVP | High | Low | Sequential covers 80% use cases |
| Complex use cases don't fit sequential | Medium | Medium | Phase 2 adds parallel quickly |
| Public skill quality issues | Medium | Medium | Moderation, usage metrics |

### 17.3 Integration Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Notion API rate limits | High | Medium | Exponential backoff, user education |
| OAuth scope changes | Medium | Low | Monitor provider announcements |
| Third-party API outages | Medium | Low | Retry logic, status monitoring |

---

## References

- Product Vision: `/Users/sohitkumar/code/omniforge/specs/product-vision.md`
- Product Spec: `/Users/sohitkumar/code/omniforge/specs/product-spec-conversational-skill-builder.md`
- Review Findings: `/Users/sohitkumar/code/omniforge/specs/plan-review/conversational-skill-builder-technical-plan-review.md`
- Existing Skills System: `/Users/sohitkumar/code/omniforge/src/omniforge/skills/`
- Existing Agents: `/Users/sohitkumar/code/omniforge/src/omniforge/agents/`
- Coding Guidelines: `/Users/sohitkumar/code/omniforge/coding-guidelines.md`

---

**Document Version**: 2.0
**Last Reviewed**: 2026-01-25
**Next Review**: After Phase 1 completion
