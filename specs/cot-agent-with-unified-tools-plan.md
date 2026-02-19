# Chain of Thought Agent with Unified Tool Calling Interface
# Technical Implementation Plan

**Created**: 2026-01-11
**Last Updated**: 2026-01-11
**Version**: 1.0
**Status**: Draft
**Spec Reference**: [cot-agent-with-unified-tools-spec.md](./cot-agent-with-unified-tools-spec.md)

---

## Executive Summary

This technical plan defines the implementation architecture for OmniForge's Chain of Thought (CoT) Agent with Unified Tool Calling Interface, including the LLM-as-Tool architecture powered by LiteLLM. The design treats **every operation as a tool call** - including LLM reasoning itself - creating complete visibility, cost tracking, and enterprise-grade control over all agent operations.

**Key Architectural Decisions:**

1. **LLM-as-Tool via LiteLLM**: All LLM calls flow through the unified tool interface, enabling multi-provider support (100+ models), automatic fallbacks, and complete cost attribution
2. **Unified Tool Interface**: Single `ToolExecutor` handles all operations (LLM, external APIs, skills, sub-agents, database, files) with consistent error handling, retries, and observability
3. **Reasoning Chain as First-Class Data**: The `ReasoningChain` is a persistent, streamable data structure that captures every step of agent reasoning
4. **Extends BaseAgent**: CoTAgent extends the existing `BaseAgent` interface, maintaining A2A protocol compatibility
5. **Reuses Existing Infrastructure**: Leverages existing SSE streaming, task models, storage repositories, and security modules

**Technology Additions:**
- `litellm >= 1.50.0` - Multi-provider LLM gateway with cost tracking
- `aiolimiter >= 1.1.0` - Async rate limiting for enterprise quotas

**Implementation Scope:**
- Phase 1: Core CoT Engine and Unified Tool Interface (3-4 weeks)
- Phase 2: LLM Tool with LiteLLM Integration (2-3 weeks)
- Phase 3: Built-in Tool Types (2-3 weeks)
- Phase 4: Cost Tracking and Rate Limiting (2 weeks)
- Phase 5: Enterprise Features and Visibility Controls (2-3 weeks)

---

## Requirements Analysis

### Functional Requirements (from Product Spec)

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| FR1 | Unified Tool Interface for all operations | Must Have | Single interface for LLM, external, skills, sub-agents, database, files |
| FR2 | LLM-as-Tool via LiteLLM | Must Have | Multi-provider support, cost tracking, fallbacks |
| FR3 | Reasoning Chain as first-class data structure | Must Have | Persistent, streamable, auditable |
| FR4 | Real-time reasoning event streaming via SSE | Must Have | Extend existing streaming infrastructure |
| FR5 | Complete cost/token tracking per operation | Must Have | Attribution to tenant/task/agent |
| FR6 | Multi-model support (100+ providers) | Must Have | Via LiteLLM integration |
| FR7 | Tool registration and discovery | Must Have | Dynamic tool registry with schema validation |
| FR8 | Sub-agent delegation through tool interface | Must Have | A2A protocol integration |
| FR9 | Visibility configuration (full/summary/hidden) | Should Have | Per-role, per-tool-type |
| FR10 | Rate limiting per tenant | Should Have | Calls/tokens/cost per time window |
| FR11 | Cost budgets per task | Should Have | Stop execution if exceeded |
| FR12 | Model governance (approved models only) | Should Have | Enterprise compliance |
| FR13 | Chain persistence for audit | Must Have | Configurable retention |
| FR14 | Chain replay for debugging | Nice to Have | Deterministic debugging |

### Non-Functional Requirements

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR1 | Reasoning chain overhead | < 50ms per task | Framework processing time |
| NFR2 | SSE event latency | < 100ms | Step completion to client delivery |
| NFR3 | LiteLLM routing overhead | < 15ms | Added latency vs direct API call |
| NFR4 | Concurrent reasoning chains | > 1000 per instance | Active chains in memory |
| NFR5 | Chain retrieval | < 500ms | For chains up to 1000 steps |
| NFR6 | Test coverage | >= 80% | All new modules |
| NFR7 | Type annotation coverage | 100% | mypy strict mode |

### Integration Requirements

| ID | Requirement | Approach |
|----|-------------|----------|
| IR1 | Extend BaseAgent interface | CoTAgent subclasses BaseAgent |
| IR2 | Use existing SSE streaming | Extend `agents/streaming.py` with reasoning events |
| IR3 | Use existing task models | Extend Task with reasoning_chain_id |
| IR4 | Use existing storage repositories | Add ChainRepository protocol |
| IR5 | Use existing security/RBAC | Add tool-level permissions |
| IR6 | A2A protocol compatibility | Sub-agent calls via A2A |

---

## Constraints and Assumptions

### Constraints

1. **Python 3.9+ Compatibility**: All code must work with Python 3.9 features
2. **Line Length**: 100 characters (Black/Ruff configuration)
3. **Type Safety**: mypy strict mode with `disallow_untyped_defs = true`
4. **Existing Infrastructure**: Must integrate with current FastAPI app and streaming utilities
5. **A2A Protocol**: Must maintain compliance with A2A v0.3 specification
6. **No Breaking Changes**: Existing BaseAgent implementations must continue to work

### Assumptions

1. **LiteLLM Stability**: LiteLLM >= 1.50.0 provides stable async support and cost tracking
2. **Provider API Keys**: Managed via environment variables or secrets management
3. **Database Available**: SQLite for local SDK, PostgreSQL for platform deployment
4. **Memory Budget**: Average reasoning chain ~50KB (100 steps with typical results)
5. **Retention Default**: 90 days for chain storage, configurable per tenant

---

## System Architecture

### High-Level Architecture

```
+---------------------------------------------------------------------------------+
|                              OmniForge Platform                                  |
+---------------------------------------------------------------------------------+
|                                                                                  |
|  +---------------------------+  +---------------------------+                    |
|  |       API Layer           |  |      Security Layer       |                    |
|  |  (FastAPI + SSE)          |  |  (RBAC + Tenant Isolation) |                   |
|  +-------------+-------------+  +-------------+-------------+                    |
|                |                              |                                  |
|                v                              v                                  |
|  +-----------------------------------------------------------------------+      |
|  |                        CoT Agent Layer                                 |      |
|  |                                                                        |      |
|  |  +------------------+  +------------------+  +--------------------+    |      |
|  |  |   CoTAgent       |  |  ReasoningEngine |  |  ToolExecutor      |    |      |
|  |  |  (extends Base)  |  |  (Chain Manager) |  |  (Unified I/F)     |    |      |
|  |  +--------+---------+  +--------+---------+  +----------+---------+    |      |
|  |           |                     |                       |              |      |
|  |           +-----------+---------+-----------+-----------+              |      |
|  |                       |                     |                          |      |
|  +-----------------------------------------------------------------------+      |
|                          |                     |                                 |
|  +-----------------------------------------------------------------------+      |
|  |                        Tool Registry Layer                             |      |
|  |                                                                        |      |
|  |  +---------------+  +---------------+  +---------------+               |      |
|  |  |  LLM Tool     |  |  External     |  |  Skill Tool   |               |      |
|  |  |  (LiteLLM)    |  |  Tools        |  |  (Internal)   |               |      |
|  |  +---------------+  +---------------+  +---------------+               |      |
|  |                                                                        |      |
|  |  +---------------+  +---------------+  +---------------+               |      |
|  |  |  SubAgent     |  |  Database     |  |  FileSystem   |               |      |
|  |  |  Tool (A2A)   |  |  Tool         |  |  Tool         |               |      |
|  |  +---------------+  +---------------+  +---------------+               |      |
|  +-----------------------------------------------------------------------+      |
|                          |                     |                                 |
|  +-----------------------------------------------------------------------+      |
|  |                      Enterprise Controls                               |      |
|  |                                                                        |      |
|  |  +---------------+  +---------------+  +---------------+               |      |
|  |  | Rate Limiter  |  | Cost Tracker  |  | Audit Logger  |               |      |
|  |  +---------------+  +---------------+  +---------------+               |      |
|  +-----------------------------------------------------------------------+      |
|                          |                                                       |
|  +-----------------------------------------------------------------------+      |
|  |                        Storage Layer                                   |      |
|  |                                                                        |      |
|  |  +---------------+  +---------------+  +---------------+               |      |
|  |  | ChainRepo     |  | TaskRepo      |  | CostRepo      |               |      |
|  |  | (Reasoning)   |  | (Existing)    |  | (Billing)     |               |      |
|  |  +---------------+  +---------------+  +---------------+               |      |
|  +-----------------------------------------------------------------------+      |
|                                                                                  |
+---------------------------------------------------------------------------------+
```

### Reasoning Flow Architecture

```
                           User Request
                                |
                                v
+------------------------------------------------------------------+
|                         CoTAgent                                  |
|  +------------------------------------------------------------+  |
|  |                    ReasoningEngine                          |  |
|  |                                                             |  |
|  |  1. Initialize ReasoningChain                               |  |
|  |  2. Emit: chain_started event                               |  |
|  |                                                             |  |
|  |  +-------------------------------------------------------+  |  |
|  |  |                  Reasoning Loop                        |  |  |
|  |  |                                                        |  |  |
|  |  |  3. Call LLM Tool: "Analyze request"                   |  |  |
|  |  |     -> Emit: tool_call (llm/claude-sonnet-4)           |  |  |
|  |  |     <- Emit: tool_result (tokens: 450, cost: $0.0012)  |  |  |
|  |  |     -> Add step to chain                               |  |  |
|  |  |                                                        |  |  |
|  |  |  4. LLM Response: "I need to query the database"       |  |  |
|  |  |     -> Emit: thinking_step                             |  |  |
|  |  |                                                        |  |  |
|  |  |  5. Call Database Tool: "SELECT * FROM..."             |  |  |
|  |  |     -> Emit: tool_call (database/query)                |  |  |
|  |  |     <- Emit: tool_result (rows: 1247)                  |  |  |
|  |  |     -> Add step to chain                               |  |  |
|  |  |                                                        |  |  |
|  |  |  6. Call LLM Tool: "Synthesize results"                |  |  |
|  |  |     -> Emit: tool_call (llm/gpt-3.5-turbo)             |  |  |
|  |  |     <- Emit: tool_result (tokens: 280, cost: $0.0003)  |  |  |
|  |  |     -> Add step to chain                               |  |  |
|  |  |                                                        |  |  |
|  |  |  7. Task Complete                                      |  |  |
|  |  |     -> Emit: synthesis_step                            |  |  |
|  |  |     -> Emit: chain_completed                           |  |  |
|  |  +-------------------------------------------------------+  |  |
|  +------------------------------------------------------------+  |
+------------------------------------------------------------------+
                                |
                                v
                      SSE Stream to Client
```

### Component Interaction Diagram

```
Client          API          CoTAgent      ReasoningEngine    ToolExecutor      LLM/External
  |              |               |               |                 |                 |
  | POST /tasks  |               |               |                 |                 |
  |------------->|               |               |                 |                 |
  |              | process_task()|               |                 |                 |
  |              |-------------->|               |                 |                 |
  |              |               | start_chain() |                 |                 |
  |              |               |-------------->|                 |                 |
  |              |               |               | create_chain()  |                 |
  |<-------------|<--------------|<--------------|                 |                 |
  | SSE: chain_  |               |               |                 |                 |
  |   started    |               |               |                 |                 |
  |              |               |               |                 |                 |
  |              |               |               | execute("llm")  |                 |
  |              |               |               |---------------->|                 |
  |<-------------|<--------------|<--------------|<----------------|                 |
  | SSE: tool_   |               |               |  emit: tool_call|                 |
  |   call       |               |               |                 | litellm.acompl()|
  |              |               |               |                 |---------------->|
  |              |               |               |                 |<----------------|
  |<-------------|<--------------|<--------------|<----------------|                 |
  | SSE: tool_   |               |               |  emit: result   |                 |
  |   result     |               |               |                 |                 |
  |              |               |               |                 |                 |
  |              |               |               | add_step()      |                 |
  |              |               |               |---------------->|                 |
  |              |               |               |                 |                 |
  | ... more steps ...                                                               |
  |              |               |               |                 |                 |
  |<-------------|<--------------|<--------------|                 |                 |
  | SSE: chain_  |               |               |                 |                 |
  |   completed  |               |               |                 |                 |
  |              |               |               |                 |                 |
```

---

## Technology Stack

### Core Dependencies (Existing)

| Dependency | Version | Purpose |
|------------|---------|---------|
| fastapi | >=0.100.0 | Web framework, SSE streaming |
| pydantic | >=2.0.0 | Data validation, models |
| uvicorn | >=0.23.0 | ASGI server |
| httpx | >=0.24.0 | Async HTTP client (A2A) |
| sqlalchemy | >=2.0.0 | ORM for persistence |

### New Dependencies (Required)

| Dependency | Version | Purpose | Justification |
|------------|---------|---------|---------------|
| litellm | >=1.50.0 | Multi-provider LLM gateway | 100+ providers, cost tracking, fallbacks, streaming |
| aiolimiter | >=1.1.0 | Async rate limiting | Enterprise quotas per tenant |
| tiktoken | >=0.5.0 | Token counting | Pre-call token estimation for budgets |

### Development Dependencies

No new development dependencies required.

---

## Module Structure

### Directory Layout

```
src/omniforge/
|-- __init__.py
|-- agents/
|   |-- __init__.py
|   |-- base.py                      # EXISTING: BaseAgent abstract class
|   |-- models.py                    # EXISTING: A2A protocol models
|   |-- events.py                    # EXTEND: Add reasoning events
|   |-- streaming.py                 # EXTEND: Add reasoning event formatters
|   |-- errors.py                    # EXTEND: Add CoT-specific errors
|   |-- cot/                         # NEW: Chain of Thought module
|   |   |-- __init__.py
|   |   |-- agent.py                 # CoTAgent abstract base class
|   |   |-- engine.py                # ReasoningEngine
|   |   |-- chain.py                 # ReasoningChain data structure
|   |   |-- events.py                # Reasoning-specific events
|   |   |-- visibility.py            # Visibility control system
|   |   |-- autonomous.py            # NEW: AutonomousCoTAgent (ReAct implementation)
|   |   |-- parser.py                # NEW: ReActParser for parsing LLM responses
|   |   |-- prompts.py               # NEW: System prompt templates
|
|-- tools/                           # NEW: Unified Tool Interface
|   |-- __init__.py
|   |-- base.py                      # BaseTool abstract class
|   |-- registry.py                  # ToolRegistry for registration/discovery
|   |-- executor.py                  # ToolExecutor for unified execution
|   |-- models.py                    # Tool definitions, call/result models
|   |-- errors.py                    # Tool-specific exceptions
|   |-- builtin/                     # Built-in tool implementations
|   |   |-- __init__.py
|   |   |-- llm.py                   # LLM Tool (LiteLLM integration)
|   |   |-- database.py              # Database query tool
|   |   |-- filesystem.py            # File system operations tool
|   |   |-- subagent.py              # Sub-agent delegation tool
|   |   |-- skill.py                 # Internal skill invocation tool
|   |   |-- external.py              # External API tool base
|
|-- llm/                             # NEW: LLM abstraction layer
|   |-- __init__.py
|   |-- client.py                    # LiteLLM client wrapper
|   |-- config.py                    # Model/provider configuration
|   |-- cost.py                      # Cost calculation and tracking
|   |-- models.py                    # LLM request/response models
|
|-- enterprise/                      # NEW: Enterprise controls
|   |-- __init__.py
|   |-- rate_limiter.py              # Rate limiting per tenant
|   |-- cost_tracker.py              # Cost tracking and budgets
|   |-- model_governance.py          # Approved model enforcement
|   |-- audit.py                     # Audit logging for compliance
|
|-- storage/
|   |-- __init__.py
|   |-- base.py                      # EXTEND: Add ChainRepository protocol
|   |-- memory.py                    # EXTEND: Add in-memory chain storage
|   |-- database.py                  # EXTEND: Add chain persistence
|   |-- models.py                    # EXTEND: Add chain ORM models
|
|-- tasks/
|   |-- __init__.py
|   |-- models.py                    # EXTEND: Add reasoning_chain_id to Task
|   |-- manager.py                   # UNCHANGED
|
|-- security/
|   |-- __init__.py
|   |-- rbac.py                      # EXTEND: Add tool-level permissions
|   |-- tenant.py                    # UNCHANGED
|   |-- auth.py                      # UNCHANGED
|
|-- api/
|   |-- __init__.py
|   |-- app.py                       # MODIFY: Add chain endpoints
|   |-- routes/
|   |   |-- __init__.py
|   |   |-- chat.py                  # UNCHANGED
|   |   |-- agents.py                # UNCHANGED
|   |   |-- tasks.py                 # UNCHANGED
|   |   |-- chains.py                # NEW: Reasoning chain endpoints
```

### Module Dependencies

```
                                  +----------------+
                                  |    api/        |
                                  | routes, app    |
                                  +-------+--------+
                                          |
                    +---------------------+---------------------+
                    |                     |                     |
                    v                     v                     v
            +---------------+     +---------------+     +---------------+
            | agents/cot/   |     |   tools/      |     |   llm/        |
            | CoTAgent      |---->| ToolExecutor  |---->| LiteLLM       |
            +-------+-------+     +-------+-------+     +---------------+
                    |                     |
                    v                     v
            +---------------+     +---------------+
            | enterprise/   |     |   storage/    |
            | RateLimiter   |     | ChainRepo     |
            | CostTracker   |     | (Persistence) |
            +---------------+     +---------------+
                    |                     |
                    v                     v
            +-------------------------------------------+
            |               security/                   |
            |  RBAC, TenantContext, Audit               |
            +-------------------------------------------+
```

---

## Component Specifications

### 1. ReasoningChain Data Structure

**Location**: `src/omniforge/agents/cot/chain.py`

**Purpose**: First-class data structure representing the complete reasoning process.

```python
"""Reasoning chain data structures for Chain of Thought agents.

This module defines the ReasoningChain and ReasoningStep models that capture
every operation in an agent's reasoning process, providing complete visibility
and auditability.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class StepType(str, Enum):
    """Types of reasoning steps."""
    THINKING = "thinking"          # Internal reasoning/analysis
    TOOL_CALL = "tool_call"        # Initiating a tool call
    TOOL_RESULT = "tool_result"    # Result from a tool call
    SYNTHESIS = "synthesis"        # Combining results into conclusion


class ToolType(str, Enum):
    """Types of tools that can be called."""
    LLM = "llm"                    # Language model call
    EXTERNAL = "external"          # External API
    SKILL = "skill"                # Internal skill
    SUB_AGENT = "sub_agent"        # Delegation to another agent
    DATABASE = "database"          # Database operation
    FILE_SYSTEM = "file_system"    # File system operation
    CUSTOM = "custom"              # Custom tool type


class VisibilityLevel(str, Enum):
    """Visibility levels for reasoning steps."""
    FULL = "full"                  # Complete details visible
    SUMMARY = "summary"            # Human-readable summary only
    HIDDEN = "hidden"              # Step exists but not shown (audit only)


class ToolCallInfo(BaseModel):
    """Information about a tool call initiation."""
    tool_type: ToolType
    tool_name: str = Field(..., min_length=1, max_length=255)
    arguments: dict[str, Any] = Field(default_factory=dict)
    correlation_id: UUID = Field(default_factory=uuid4)

    # LLM-specific fields (populated when tool_type == LLM)
    model: Optional[str] = None
    provider: Optional[str] = None
    prompt_tokens_estimate: Optional[int] = None


class ToolResultInfo(BaseModel):
    """Information about a tool call result."""
    correlation_id: UUID
    success: bool
    result: Any = None
    error: Optional[str] = None
    duration_ms: int = Field(..., ge=0)

    # LLM-specific fields
    model: Optional[str] = None
    provider: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    cost_usd: Optional[float] = None

    # General metrics
    cached: bool = False


class ThinkingInfo(BaseModel):
    """Information about a thinking/reasoning step."""
    thought: str
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)


class SynthesisInfo(BaseModel):
    """Information about a synthesis step."""
    sources: list[UUID] = Field(default_factory=list)  # Step IDs that informed this
    conclusion: str


class VisibilityConfig(BaseModel):
    """Visibility configuration for a step."""
    level: VisibilityLevel = VisibilityLevel.FULL
    summary: Optional[str] = None  # Human-readable summary for non-technical users


class ReasoningStep(BaseModel):
    """A single step in the reasoning chain.

    Each step represents one operation in the agent's reasoning process,
    whether it's thinking, calling a tool, receiving a result, or synthesizing.
    """
    id: UUID = Field(default_factory=uuid4)
    step_number: int = Field(..., ge=1)
    type: StepType
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Type-specific information (mutually exclusive based on type)
    thinking: Optional[ThinkingInfo] = None
    tool_call: Optional[ToolCallInfo] = None
    tool_result: Optional[ToolResultInfo] = None
    synthesis: Optional[SynthesisInfo] = None

    # Visibility metadata
    visibility: VisibilityConfig = Field(default_factory=VisibilityConfig)

    # Parent step (for nested operations)
    parent_step_id: Optional[UUID] = None


class ChainStatus(str, Enum):
    """Status of a reasoning chain."""
    INITIALIZING = "initializing"
    THINKING = "thinking"
    TOOL_CALLING = "tool_calling"
    WAITING = "waiting"            # Waiting for external input
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ChainMetrics(BaseModel):
    """Aggregated metrics for a reasoning chain."""
    total_steps: int = 0
    llm_calls: int = 0
    tool_calls: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    total_duration_ms: int = 0


class ReasoningChain(BaseModel):
    """Complete reasoning chain for a task.

    The ReasoningChain captures the full journey from input to output,
    making the agent's decision-making process transparent and auditable.
    """
    id: UUID = Field(default_factory=uuid4)
    task_id: str = Field(..., min_length=1, max_length=255)
    agent_id: str = Field(..., min_length=1, max_length=255)

    # Lifecycle
    status: ChainStatus = ChainStatus.INITIALIZING
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    # Steps
    steps: list[ReasoningStep] = Field(default_factory=list)

    # Metrics (computed incrementally)
    metrics: ChainMetrics = Field(default_factory=ChainMetrics)

    # Child chains (for sub-agent delegation)
    child_chain_ids: list[UUID] = Field(default_factory=list)

    # Multi-tenancy
    tenant_id: Optional[str] = None

    def add_step(self, step: ReasoningStep) -> None:
        """Add a step to the chain and update metrics."""
        step.step_number = len(self.steps) + 1
        self.steps.append(step)
        self._update_metrics(step)

    def _update_metrics(self, step: ReasoningStep) -> None:
        """Update chain metrics based on new step."""
        self.metrics.total_steps += 1

        if step.type == StepType.TOOL_CALL:
            self.metrics.tool_calls += 1
            if step.tool_call and step.tool_call.tool_type == ToolType.LLM:
                self.metrics.llm_calls += 1

        if step.type == StepType.TOOL_RESULT and step.tool_result:
            result = step.tool_result
            self.metrics.total_duration_ms += result.duration_ms

            if result.total_tokens:
                self.metrics.total_tokens += result.total_tokens
            if result.cost_usd:
                self.metrics.total_cost_usd += result.cost_usd

    def get_step_by_correlation_id(self, correlation_id: UUID) -> Optional[ReasoningStep]:
        """Find a tool_call step by its correlation ID."""
        for step in self.steps:
            if step.tool_call and step.tool_call.correlation_id == correlation_id:
                return step
        return None
```

### 2. Unified Tool Interface

**Location**: `src/omniforge/tools/base.py`

**Purpose**: Abstract base class defining the contract all tools must implement.

```python
"""Base tool interface for the unified tool system.

All tools in OmniForge implement this interface, enabling consistent
execution, error handling, retries, and observability.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, AsyncIterator, Generic, Optional, TypeVar
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from omniforge.agents.cot.chain import ToolType, VisibilityLevel


# Generic types for tool input/output
TInput = TypeVar("TInput", bound=BaseModel)
TOutput = TypeVar("TOutput")


class ToolParameter(BaseModel):
    """Definition of a tool parameter."""
    name: str = Field(..., min_length=1, max_length=100)
    type: str = Field(..., min_length=1, max_length=50)  # JSON Schema type
    description: str = ""
    required: bool = True
    default: Any = None


class ToolRetryConfig(BaseModel):
    """Retry configuration for tool execution."""
    max_retries: int = Field(default=3, ge=0, le=10)
    backoff_ms: int = Field(default=1000, ge=100, le=60000)
    backoff_multiplier: float = Field(default=2.0, ge=1.0, le=5.0)
    retryable_errors: list[str] = Field(
        default_factory=lambda: ["timeout", "rate_limit", "temporary"]
    )


class ToolVisibilityConfig(BaseModel):
    """Visibility configuration for a tool."""
    default_level: VisibilityLevel = VisibilityLevel.FULL
    summary_template: Optional[str] = None  # e.g., "Queried {table}, returned {row_count} rows"
    sensitive_fields: list[str] = Field(default_factory=list)  # Fields to redact


class ToolPermissions(BaseModel):
    """Permission configuration for a tool."""
    required_roles: list[str] = Field(default_factory=list)
    audit_level: str = "basic"  # none, basic, full


class ToolDefinition(BaseModel):
    """Complete definition of a tool for registration."""
    name: str = Field(..., min_length=1, max_length=100)
    type: ToolType
    description: str = ""
    version: str = "1.0.0"

    # Parameters
    parameters: list[ToolParameter] = Field(default_factory=list)
    returns_description: str = ""

    # Execution config
    timeout_ms: int = Field(default=30000, ge=1000, le=600000)
    retry_config: ToolRetryConfig = Field(default_factory=ToolRetryConfig)
    cache_ttl_seconds: Optional[int] = None

    # Visibility
    visibility: ToolVisibilityConfig = Field(default_factory=ToolVisibilityConfig)

    # Security
    permissions: ToolPermissions = Field(default_factory=ToolPermissions)


class ToolCallContext(BaseModel):
    """Context passed to tool execution."""
    correlation_id: UUID = Field(default_factory=uuid4)
    task_id: str
    agent_id: str
    tenant_id: Optional[str] = None
    user_id: Optional[str] = None
    chain_id: UUID

    # Execution context
    started_at: datetime = Field(default_factory=datetime.utcnow)
    parent_step_id: Optional[UUID] = None

    # Budget constraints
    remaining_cost_budget_usd: Optional[float] = None
    remaining_token_budget: Optional[int] = None


class ToolResult(BaseModel):
    """Result of a tool execution."""
    success: bool
    result: Any = None
    error: Optional[str] = None
    error_code: Optional[str] = None

    # Timing
    duration_ms: int = Field(..., ge=0)

    # Metadata
    cached: bool = False
    retries_used: int = 0

    # LLM-specific (populated by LLM tool)
    model: Optional[str] = None
    provider: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    cost_usd: Optional[float] = None


class BaseTool(ABC, Generic[TInput, TOutput]):
    """Abstract base class for all tools.

    All tools in OmniForge extend this class to provide a consistent
    interface for registration, execution, and observability.
    """

    @property
    @abstractmethod
    def definition(self) -> ToolDefinition:
        """Return the tool definition for registration."""
        ...

    @abstractmethod
    async def execute(
        self,
        arguments: dict[str, Any],
        context: ToolCallContext,
    ) -> ToolResult:
        """Execute the tool with the given arguments.

        Args:
            arguments: Dictionary of argument name to value
            context: Execution context with task/tenant info

        Returns:
            ToolResult containing success status and result/error
        """
        ...

    async def validate_arguments(self, arguments: dict[str, Any]) -> list[str]:
        """Validate tool arguments. Override for custom validation.

        Args:
            arguments: Dictionary of argument name to value

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        for param in self.definition.parameters:
            if param.required and param.name not in arguments:
                errors.append(f"Missing required parameter: {param.name}")
        return errors

    def generate_summary(self, result: ToolResult) -> str:
        """Generate a human-readable summary of the result.

        Uses the summary_template if defined, otherwise returns a default.
        """
        template = self.definition.visibility.summary_template
        if template and result.success:
            try:
                return template.format(**result.result if isinstance(result.result, dict) else {})
            except (KeyError, TypeError):
                pass
        return f"{self.definition.name}: {'success' if result.success else 'failed'}"


class StreamingTool(BaseTool[TInput, TOutput]):
    """Base class for tools that support streaming responses."""

    @abstractmethod
    async def execute_streaming(
        self,
        arguments: dict[str, Any],
        context: ToolCallContext,
    ) -> AsyncIterator[Any]:
        """Execute the tool with streaming response.

        Yields:
            Partial results as they become available
        """
        ...
```

### 3. Tool Registry

**Location**: `src/omniforge/tools/registry.py`

**Purpose**: Central registry for tool registration, discovery, and retrieval.

```python
"""Tool registry for registration and discovery of tools.

The ToolRegistry provides a central point for registering tools,
looking them up by name, and managing tool lifecycle.
"""

from typing import Optional

from omniforge.agents.cot.chain import ToolType
from omniforge.tools.base import BaseTool, ToolDefinition
from omniforge.tools.errors import ToolNotFoundError, ToolAlreadyRegisteredError


class ToolRegistry:
    """Central registry for all tools.

    The registry maintains a mapping of tool names to tool instances,
    enabling dynamic tool registration and lookup.

    Example:
        >>> registry = ToolRegistry()
        >>> registry.register(llm_tool)
        >>> registry.register(weather_api_tool)
        >>>
        >>> tool = registry.get("llm")
        >>> result = await tool.execute({"prompt": "Hello"}, context)
    """

    def __init__(self) -> None:
        """Initialize an empty tool registry."""
        self._tools: dict[str, BaseTool] = {}
        self._definitions: dict[str, ToolDefinition] = {}

    def register(self, tool: BaseTool, replace: bool = False) -> None:
        """Register a tool with the registry.

        Args:
            tool: The tool instance to register
            replace: If True, replace existing tool with same name

        Raises:
            ToolAlreadyRegisteredError: If tool name exists and replace=False
        """
        name = tool.definition.name
        if name in self._tools and not replace:
            raise ToolAlreadyRegisteredError(name)

        self._tools[name] = tool
        self._definitions[name] = tool.definition

    def unregister(self, name: str) -> None:
        """Remove a tool from the registry.

        Args:
            name: Name of the tool to remove

        Raises:
            ToolNotFoundError: If tool does not exist
        """
        if name not in self._tools:
            raise ToolNotFoundError(name)

        del self._tools[name]
        del self._definitions[name]

    def get(self, name: str) -> BaseTool:
        """Get a tool by name.

        Args:
            name: Name of the tool to retrieve

        Returns:
            The tool instance

        Raises:
            ToolNotFoundError: If tool does not exist
        """
        if name not in self._tools:
            raise ToolNotFoundError(name)
        return self._tools[name]

    def get_definition(self, name: str) -> ToolDefinition:
        """Get a tool definition by name.

        Args:
            name: Name of the tool

        Returns:
            The tool definition

        Raises:
            ToolNotFoundError: If tool does not exist
        """
        if name not in self._definitions:
            raise ToolNotFoundError(name)
        return self._definitions[name]

    def list_tools(self, tool_type: Optional[ToolType] = None) -> list[ToolDefinition]:
        """List all registered tools, optionally filtered by type.

        Args:
            tool_type: Optional type filter

        Returns:
            List of tool definitions
        """
        definitions = list(self._definitions.values())
        if tool_type:
            definitions = [d for d in definitions if d.type == tool_type]
        return definitions

    def has_tool(self, name: str) -> bool:
        """Check if a tool is registered.

        Args:
            name: Name of the tool

        Returns:
            True if tool exists, False otherwise
        """
        return name in self._tools

    def clear(self) -> None:
        """Remove all tools from the registry."""
        self._tools.clear()
        self._definitions.clear()


# Global default registry instance
_default_registry: Optional[ToolRegistry] = None


def get_default_registry() -> ToolRegistry:
    """Get or create the default tool registry.

    Returns:
        The global default ToolRegistry instance
    """
    global _default_registry
    if _default_registry is None:
        _default_registry = ToolRegistry()
    return _default_registry


def register_tool(tool: BaseTool, replace: bool = False) -> None:
    """Register a tool with the default registry.

    Convenience function for the common case.

    Args:
        tool: The tool to register
        replace: If True, replace existing tool
    """
    get_default_registry().register(tool, replace)
```

### 4. Tool Executor

**Location**: `src/omniforge/tools/executor.py`

**Purpose**: Unified execution engine for all tool calls with retries, timeouts, and observability.

```python
"""Unified tool execution engine.

The ToolExecutor provides a consistent execution environment for all tools,
handling retries, timeouts, error handling, and integration with the
reasoning chain.
"""

import asyncio
import time
from typing import Any, AsyncIterator, Optional
from uuid import UUID

from omniforge.agents.cot.chain import (
    ReasoningChain,
    ReasoningStep,
    StepType,
    ToolCallInfo,
    ToolResultInfo,
    ToolType,
    VisibilityConfig,
)
from omniforge.enterprise.cost_tracker import CostTracker
from omniforge.enterprise.rate_limiter import RateLimiter
from omniforge.tools.base import BaseTool, StreamingTool, ToolCallContext, ToolResult
from omniforge.tools.errors import (
    ToolExecutionError,
    ToolNotFoundError,
    ToolTimeoutError,
    CostBudgetExceededError,
    RateLimitExceededError,
)
from omniforge.tools.registry import ToolRegistry


class ToolExecutor:
    """Unified execution engine for all tools.

    The executor handles:
    - Tool lookup from registry
    - Argument validation
    - Retry logic with backoff
    - Timeout enforcement
    - Rate limiting checks
    - Cost budget enforcement
    - Reasoning chain integration
    - Event emission for streaming

    Example:
        >>> executor = ToolExecutor(registry, rate_limiter, cost_tracker)
        >>>
        >>> # Execute a tool and get result
        >>> result = await executor.execute(
        ...     tool_name="llm",
        ...     arguments={"model": "claude-sonnet-4", "prompt": "Analyze this"},
        ...     context=context,
        ...     chain=reasoning_chain
        ... )
        >>>
        >>> # Stream tool execution events
        >>> async for step in executor.execute_with_events(
        ...     tool_name="llm",
        ...     arguments=arguments,
        ...     context=context,
        ...     chain=chain
        ... ):
        ...     yield step  # ReasoningStep events
    """

    def __init__(
        self,
        registry: ToolRegistry,
        rate_limiter: Optional[RateLimiter] = None,
        cost_tracker: Optional[CostTracker] = None,
    ) -> None:
        """Initialize the tool executor.

        Args:
            registry: Tool registry for looking up tools
            rate_limiter: Optional rate limiter for quota enforcement
            cost_tracker: Optional cost tracker for budget enforcement
        """
        self._registry = registry
        self._rate_limiter = rate_limiter
        self._cost_tracker = cost_tracker

    async def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        context: ToolCallContext,
        chain: Optional[ReasoningChain] = None,
    ) -> ToolResult:
        """Execute a tool and return the result.

        This method handles the full execution lifecycle including validation,
        retries, timeouts, and optional chain integration.

        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments
            context: Execution context
            chain: Optional reasoning chain to add steps to

        Returns:
            ToolResult with success status and result/error

        Raises:
            ToolNotFoundError: If tool is not registered
            RateLimitExceededError: If rate limit is exceeded
            CostBudgetExceededError: If cost budget would be exceeded
            ToolTimeoutError: If execution times out after retries
            ToolExecutionError: If execution fails after retries
        """
        # Get tool from registry
        tool = self._registry.get(tool_name)
        definition = tool.definition

        # Validate arguments
        errors = await tool.validate_arguments(arguments)
        if errors:
            return ToolResult(
                success=False,
                error="; ".join(errors),
                error_code="validation_error",
                duration_ms=0,
            )

        # Check rate limits
        if self._rate_limiter and context.tenant_id:
            allowed = await self._rate_limiter.check_and_consume(
                tenant_id=context.tenant_id,
                tool_type=definition.type,
            )
            if not allowed:
                raise RateLimitExceededError(context.tenant_id, tool_name)

        # Create tool call step
        correlation_id = context.correlation_id
        tool_call_info = ToolCallInfo(
            tool_type=definition.type,
            tool_name=tool_name,
            arguments=arguments,
            correlation_id=correlation_id,
            model=arguments.get("model") if definition.type == ToolType.LLM else None,
        )

        # Add tool_call step to chain
        if chain:
            call_step = ReasoningStep(
                type=StepType.TOOL_CALL,
                tool_call=tool_call_info,
                parent_step_id=context.parent_step_id,
                visibility=VisibilityConfig(level=definition.visibility.default_level),
            )
            chain.add_step(call_step)

        # Execute with retries
        result = await self._execute_with_retries(tool, arguments, context)

        # Track cost
        if self._cost_tracker and result.cost_usd and context.tenant_id:
            await self._cost_tracker.record_cost(
                tenant_id=context.tenant_id,
                task_id=context.task_id,
                tool_name=tool_name,
                cost_usd=result.cost_usd,
                tokens=result.total_tokens,
            )

        # Add tool_result step to chain
        if chain:
            result_info = ToolResultInfo(
                correlation_id=correlation_id,
                success=result.success,
                result=result.result if result.success else None,
                error=result.error,
                duration_ms=result.duration_ms,
                model=result.model,
                provider=result.provider,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                total_tokens=result.total_tokens,
                cost_usd=result.cost_usd,
                cached=result.cached,
            )
            result_step = ReasoningStep(
                type=StepType.TOOL_RESULT,
                tool_result=result_info,
                parent_step_id=context.parent_step_id,
                visibility=VisibilityConfig(
                    level=definition.visibility.default_level,
                    summary=tool.generate_summary(result),
                ),
            )
            chain.add_step(result_step)

        return result

    async def _execute_with_retries(
        self,
        tool: BaseTool,
        arguments: dict[str, Any],
        context: ToolCallContext,
    ) -> ToolResult:
        """Execute tool with retry logic.

        Args:
            tool: The tool to execute
            arguments: Tool arguments
            context: Execution context

        Returns:
            ToolResult from execution
        """
        retry_config = tool.definition.retry_config
        timeout_ms = tool.definition.timeout_ms
        last_error: Optional[str] = None
        retries_used = 0

        for attempt in range(retry_config.max_retries + 1):
            start_time = time.perf_counter()

            try:
                # Execute with timeout
                result = await asyncio.wait_for(
                    tool.execute(arguments, context),
                    timeout=timeout_ms / 1000.0,
                )
                result.retries_used = retries_used
                return result

            except asyncio.TimeoutError:
                last_error = f"Tool execution timed out after {timeout_ms}ms"
                retries_used = attempt

            except Exception as e:
                last_error = str(e)
                retries_used = attempt

            # Check if we should retry
            if attempt < retry_config.max_retries:
                # Calculate backoff
                backoff = retry_config.backoff_ms * (
                    retry_config.backoff_multiplier ** attempt
                )
                await asyncio.sleep(backoff / 1000.0)

        # All retries exhausted
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        return ToolResult(
            success=False,
            error=last_error,
            error_code="execution_failed",
            duration_ms=duration_ms,
            retries_used=retries_used,
        )

    async def execute_with_events(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        context: ToolCallContext,
        chain: ReasoningChain,
    ) -> AsyncIterator[ReasoningStep]:
        """Execute a tool and yield reasoning steps as events.

        This method is useful for streaming execution progress to clients.

        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments
            context: Execution context
            chain: Reasoning chain to add steps to

        Yields:
            ReasoningStep objects as they are created
        """
        tool = self._registry.get(tool_name)
        definition = tool.definition

        # Create and yield tool_call step
        correlation_id = context.correlation_id
        tool_call_info = ToolCallInfo(
            tool_type=definition.type,
            tool_name=tool_name,
            arguments=arguments,
            correlation_id=correlation_id,
            model=arguments.get("model") if definition.type == ToolType.LLM else None,
        )

        call_step = ReasoningStep(
            type=StepType.TOOL_CALL,
            tool_call=tool_call_info,
            visibility=VisibilityConfig(level=definition.visibility.default_level),
        )
        chain.add_step(call_step)
        yield call_step

        # Execute tool
        result = await self._execute_with_retries(tool, arguments, context)

        # Track cost
        if self._cost_tracker and result.cost_usd and context.tenant_id:
            await self._cost_tracker.record_cost(
                tenant_id=context.tenant_id,
                task_id=context.task_id,
                tool_name=tool_name,
                cost_usd=result.cost_usd,
                tokens=result.total_tokens,
            )

        # Create and yield tool_result step
        result_info = ToolResultInfo(
            correlation_id=correlation_id,
            success=result.success,
            result=result.result if result.success else None,
            error=result.error,
            duration_ms=result.duration_ms,
            model=result.model,
            provider=result.provider,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            total_tokens=result.total_tokens,
            cost_usd=result.cost_usd,
            cached=result.cached,
        )

        result_step = ReasoningStep(
            type=StepType.TOOL_RESULT,
            tool_result=result_info,
            visibility=VisibilityConfig(
                level=definition.visibility.default_level,
                summary=tool.generate_summary(result),
            ),
        )
        chain.add_step(result_step)
        yield result_step
```

### 5. LLM Tool with LiteLLM Integration

**Location**: `src/omniforge/tools/builtin/llm.py`

**Purpose**: LLM tool that wraps LiteLLM for multi-provider support.

```python
"""LLM Tool implementation using LiteLLM.

This tool provides access to 100+ LLM providers through a unified interface,
with support for streaming, cost tracking, and automatic fallbacks.
"""

import time
from typing import Any, AsyncIterator, Optional

import litellm
from litellm import acompletion, completion_cost

from omniforge.agents.cot.chain import ToolType
from omniforge.llm.config import LLMConfig, get_default_config
from omniforge.tools.base import (
    BaseTool,
    StreamingTool,
    ToolCallContext,
    ToolDefinition,
    ToolParameter,
    ToolResult,
    ToolRetryConfig,
    ToolVisibilityConfig,
)


class LLMTool(StreamingTool):
    """Tool for invoking LLMs through LiteLLM.

    This tool provides a unified interface to 100+ LLM providers including:
    - Anthropic (Claude)
    - OpenAI (GPT)
    - Google (Gemini)
    - Azure OpenAI
    - AWS Bedrock
    - Local models (Ollama, vLLM, etc.)

    The tool handles:
    - Provider routing and authentication
    - Automatic fallbacks on failure
    - Cost calculation and tracking
    - Token counting
    - Streaming responses
    - Response caching

    Example:
        >>> llm_tool = LLMTool(config)
        >>> result = await llm_tool.execute(
        ...     arguments={
        ...         "model": "claude-sonnet-4",
        ...         "prompt": "Analyze this data",
        ...         "temperature": 0.7
        ...     },
        ...     context=context
        ... )
        >>> print(f"Response: {result.result}")
        >>> print(f"Cost: ${result.cost_usd}")
    """

    def __init__(self, config: Optional[LLMConfig] = None) -> None:
        """Initialize the LLM tool.

        Args:
            config: LLM configuration. Uses default if not provided.
        """
        self._config = config or get_default_config()
        self._setup_litellm()

    def _setup_litellm(self) -> None:
        """Configure LiteLLM with provider settings."""
        # Set API keys from config
        for provider, settings in self._config.providers.items():
            if settings.api_key:
                litellm.api_key = settings.api_key
            if settings.api_base:
                litellm.api_base = settings.api_base

        # Enable cost tracking
        litellm.success_callback = []
        litellm.failure_callback = []

        # Set default retry config
        litellm.num_retries = 0  # We handle retries in ToolExecutor

    @property
    def definition(self) -> ToolDefinition:
        """Return the tool definition."""
        return ToolDefinition(
            name="llm",
            type=ToolType.LLM,
            description="Invoke a large language model for reasoning, analysis, or generation",
            version="1.0.0",
            parameters=[
                ToolParameter(
                    name="model",
                    type="string",
                    description="Model identifier (e.g., 'claude-sonnet-4', 'gpt-4')",
                    required=False,  # Uses default if not specified
                ),
                ToolParameter(
                    name="prompt",
                    type="string",
                    description="The prompt to send to the model",
                    required=True,
                ),
                ToolParameter(
                    name="messages",
                    type="array",
                    description="Chat messages (alternative to prompt)",
                    required=False,
                ),
                ToolParameter(
                    name="temperature",
                    type="number",
                    description="Sampling temperature (0.0-2.0)",
                    required=False,
                    default=0.7,
                ),
                ToolParameter(
                    name="max_tokens",
                    type="integer",
                    description="Maximum tokens in response",
                    required=False,
                    default=4096,
                ),
                ToolParameter(
                    name="system",
                    type="string",
                    description="System prompt",
                    required=False,
                ),
            ],
            timeout_ms=60000,  # LLM calls can take time
            retry_config=ToolRetryConfig(
                max_retries=3,
                backoff_ms=1000,
                retryable_errors=["timeout", "rate_limit", "overloaded"],
            ),
            visibility=ToolVisibilityConfig(
                summary_template="LLM call: {model} ({total_tokens} tokens, ${cost_usd:.4f})",
            ),
        )

    async def execute(
        self,
        arguments: dict[str, Any],
        context: ToolCallContext,
    ) -> ToolResult:
        """Execute an LLM call.

        Args:
            arguments: LLM call arguments
            context: Execution context

        Returns:
            ToolResult with LLM response and metrics
        """
        start_time = time.perf_counter()

        # Resolve model
        model = arguments.get("model", self._config.default_model)

        # Check if model is approved (enterprise governance)
        if self._config.approved_models and model not in self._config.approved_models:
            return ToolResult(
                success=False,
                error=f"Model '{model}' is not in the approved model list",
                error_code="model_not_approved",
                duration_ms=0,
            )

        # Build messages
        messages = arguments.get("messages")
        if not messages:
            prompt = arguments.get("prompt", "")
            system = arguments.get("system")
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

        # Check cost budget before call
        if context.remaining_cost_budget_usd is not None:
            estimated_cost = self._estimate_cost(model, messages, arguments.get("max_tokens", 4096))
            if estimated_cost > context.remaining_cost_budget_usd:
                return ToolResult(
                    success=False,
                    error=f"Estimated cost ${estimated_cost:.4f} exceeds remaining budget "
                          f"${context.remaining_cost_budget_usd:.4f}",
                    error_code="cost_budget_exceeded",
                    duration_ms=0,
                )

        try:
            # Make LLM call via LiteLLM
            response = await acompletion(
                model=model,
                messages=messages,
                temperature=arguments.get("temperature", 0.7),
                max_tokens=arguments.get("max_tokens", 4096),
                metadata={
                    "task_id": context.task_id,
                    "tenant_id": context.tenant_id,
                    "agent_id": context.agent_id,
                },
            )

            duration_ms = int((time.perf_counter() - start_time) * 1000)

            # Extract response content
            content = response.choices[0].message.content

            # Calculate usage
            usage = response.usage
            input_tokens = usage.prompt_tokens
            output_tokens = usage.completion_tokens
            total_tokens = usage.total_tokens

            # Calculate cost
            try:
                cost = completion_cost(completion_response=response)
            except Exception:
                cost = self._estimate_cost_from_tokens(model, input_tokens, output_tokens)

            return ToolResult(
                success=True,
                result=content,
                duration_ms=duration_ms,
                model=model,
                provider=self._get_provider(model),
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                cost_usd=cost,
            )

        except Exception as e:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            return ToolResult(
                success=False,
                error=str(e),
                error_code="llm_error",
                duration_ms=duration_ms,
                model=model,
            )

    async def execute_streaming(
        self,
        arguments: dict[str, Any],
        context: ToolCallContext,
    ) -> AsyncIterator[str]:
        """Execute an LLM call with streaming response.

        Yields:
            Token chunks as they are generated
        """
        model = arguments.get("model", self._config.default_model)

        messages = arguments.get("messages")
        if not messages:
            prompt = arguments.get("prompt", "")
            system = arguments.get("system")
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

        response = await acompletion(
            model=model,
            messages=messages,
            temperature=arguments.get("temperature", 0.7),
            max_tokens=arguments.get("max_tokens", 4096),
            stream=True,
        )

        async for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def _estimate_cost(
        self,
        model: str,
        messages: list[dict],
        max_tokens: int,
    ) -> float:
        """Estimate cost before making the call."""
        # Simple estimation - could be more sophisticated
        input_text = " ".join(m.get("content", "") for m in messages)
        estimated_input_tokens = len(input_text) // 4  # Rough estimate
        estimated_output_tokens = max_tokens // 2  # Assume half of max

        return self._estimate_cost_from_tokens(
            model, estimated_input_tokens, estimated_output_tokens
        )

    def _estimate_cost_from_tokens(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Estimate cost from token counts."""
        # Cost per 1M tokens (approximate, varies by provider)
        # LiteLLM handles actual cost calculation for known models
        COST_PER_M_INPUT = {
            "claude-sonnet-4": 3.0,
            "claude-opus-4": 15.0,
            "gpt-4": 30.0,
            "gpt-4-turbo": 10.0,
            "gpt-3.5-turbo": 0.5,
        }
        COST_PER_M_OUTPUT = {
            "claude-sonnet-4": 15.0,
            "claude-opus-4": 75.0,
            "gpt-4": 60.0,
            "gpt-4-turbo": 30.0,
            "gpt-3.5-turbo": 1.5,
        }

        # Get base model name (remove version suffixes)
        base_model = model.split("-20")[0]  # Remove date versions

        input_cost = (input_tokens / 1_000_000) * COST_PER_M_INPUT.get(base_model, 5.0)
        output_cost = (output_tokens / 1_000_000) * COST_PER_M_OUTPUT.get(base_model, 15.0)

        return input_cost + output_cost

    def _get_provider(self, model: str) -> str:
        """Determine provider from model name."""
        if model.startswith("claude"):
            return "anthropic"
        elif model.startswith("gpt"):
            return "openai"
        elif model.startswith("gemini"):
            return "google"
        elif "/" in model:
            return model.split("/")[0]
        return "unknown"
```

### 6. CoTAgent Class

**Location**: `src/omniforge/agents/cot/agent.py`

**Purpose**: Main agent class extending BaseAgent with chain of thought capabilities.

```python
"""Chain of Thought Agent implementation.

The CoTAgent extends BaseAgent to provide transparent, visible reasoning
through the unified tool interface.
"""

from typing import AsyncIterator, Optional
from uuid import UUID, uuid4

from omniforge.agents.base import BaseAgent
from omniforge.agents.cot.chain import (
    ChainStatus,
    ReasoningChain,
    ReasoningStep,
    StepType,
    SynthesisInfo,
    ThinkingInfo,
    VisibilityConfig,
    VisibilityLevel,
)
from omniforge.agents.cot.engine import ReasoningEngine
from omniforge.agents.cot.events import (
    ChainCompletedEvent,
    ChainStartedEvent,
    ReasoningStepEvent,
)
from omniforge.agents.events import TaskDoneEvent, TaskEvent, TaskStatusEvent
from omniforge.agents.models import AgentCapabilities, AgentIdentity, AgentSkill
from omniforge.enterprise.cost_tracker import CostTracker
from omniforge.enterprise.rate_limiter import RateLimiter
from omniforge.storage.base import ChainRepository
from omniforge.tasks.models import Task, TaskState
from omniforge.tools.executor import ToolExecutor
from omniforge.tools.registry import ToolRegistry


class CoTAgent(BaseAgent):
    """Chain of Thought Agent with unified tool interface.

    The CoTAgent provides transparent reasoning by routing all operations
    through the unified tool interface. Every action - including LLM calls
    for reasoning - appears as a visible step in the reasoning chain.

    Key features:
    - All operations flow through unified tool interface
    - LLM calls are tool calls (via LiteLLM)
    - Complete visibility into reasoning process
    - Full cost/token tracking
    - Streaming reasoning events

    Example:
        >>> class MyCoTAgent(CoTAgent):
        ...     identity = AgentIdentity(
        ...         id="my-cot-agent",
        ...         name="My CoT Agent",
        ...         description="Analyzes data with visible reasoning",
        ...         version="1.0.0"
        ...     )
        ...
        ...     async def reason(self, task: Task, engine: ReasoningEngine) -> None:
        ...         # Call LLM to analyze request
        ...         analysis = await engine.call_llm(
        ...             prompt=f"Analyze this request: {task.messages[-1].parts[0].text}",
        ...             model="claude-sonnet-4"
        ...         )
        ...
        ...         # Call database based on analysis
        ...         data = await engine.call_tool(
        ...             "database",
        ...             {"query": "SELECT * FROM ..."}
        ...         )
        ...
        ...         # Synthesize results
        ...         conclusion = await engine.call_llm(
        ...             prompt=f"Summarize findings: {data}",
        ...             model="gpt-3.5-turbo"  # Cheaper model for summary
        ...         )
        ...
        ...         engine.add_synthesis(
        ...             conclusion=conclusion,
        ...             sources=[analysis.step_id, data.step_id]
        ...         )
    """

    # Subclasses must define these
    identity: AgentIdentity
    capabilities: AgentCapabilities = AgentCapabilities(
        streaming=True,
        multi_turn=True,
        hitl_support=True,
    )
    skills: list[AgentSkill] = []

    def __init__(
        self,
        agent_id: Optional[UUID] = None,
        tenant_id: Optional[str] = None,
        tool_registry: Optional[ToolRegistry] = None,
        chain_repository: Optional[ChainRepository] = None,
        rate_limiter: Optional[RateLimiter] = None,
        cost_tracker: Optional[CostTracker] = None,
    ) -> None:
        """Initialize the CoT Agent.

        Args:
            agent_id: Optional explicit UUID for the agent instance
            tenant_id: Optional tenant identifier for multi-tenancy
            tool_registry: Tool registry (uses default if not provided)
            chain_repository: Chain storage (uses in-memory if not provided)
            rate_limiter: Optional rate limiter for quotas
            cost_tracker: Optional cost tracker for budgets
        """
        super().__init__(agent_id, tenant_id)

        self._tool_registry = tool_registry
        self._chain_repository = chain_repository
        self._rate_limiter = rate_limiter
        self._cost_tracker = cost_tracker

        # Create tool executor
        self._executor = ToolExecutor(
            registry=self._tool_registry,
            rate_limiter=self._rate_limiter,
            cost_tracker=self._cost_tracker,
        )

    async def process_task(self, task: Task) -> AsyncIterator[TaskEvent]:
        """Process a task with visible chain of thought.

        This method orchestrates the reasoning process, creating a reasoning
        chain and yielding events as the agent thinks and acts.

        Args:
            task: The task to process

        Yields:
            TaskEvent objects including reasoning chain events
        """
        # Create reasoning chain
        chain = ReasoningChain(
            task_id=task.id,
            agent_id=str(self._id),
            tenant_id=self.tenant_id,
        )

        # Emit chain started event
        yield ChainStartedEvent(
            task_id=task.id,
            chain_id=chain.id,
            timestamp=chain.started_at,
        )

        # Emit working status
        yield TaskStatusEvent(
            task_id=task.id,
            timestamp=chain.started_at,
            state=TaskState.WORKING,
        )

        try:
            # Create reasoning engine for this task
            engine = ReasoningEngine(
                chain=chain,
                executor=self._executor,
                task=task,
            )

            # Execute reasoning (subclasses implement this)
            async for step in self._reason_with_events(task, engine):
                yield ReasoningStepEvent(
                    task_id=task.id,
                    chain_id=chain.id,
                    step=step,
                    timestamp=step.timestamp,
                )

            # Complete the chain
            chain.status = ChainStatus.COMPLETED
            chain.completed_at = datetime.utcnow()

            # Persist chain
            if self._chain_repository:
                await self._chain_repository.save(chain)

            # Emit chain completed event
            yield ChainCompletedEvent(
                task_id=task.id,
                chain_id=chain.id,
                metrics=chain.metrics,
                timestamp=chain.completed_at,
            )

            # Emit task done
            yield TaskDoneEvent(
                task_id=task.id,
                timestamp=chain.completed_at,
                final_state=TaskState.COMPLETED,
            )

        except Exception as e:
            # Handle failure
            chain.status = ChainStatus.FAILED
            chain.completed_at = datetime.utcnow()

            if self._chain_repository:
                await self._chain_repository.save(chain)

            # Emit error event
            yield TaskErrorEvent(
                task_id=task.id,
                timestamp=chain.completed_at,
                error_code="reasoning_failed",
                error_message=str(e),
            )

            yield TaskDoneEvent(
                task_id=task.id,
                timestamp=chain.completed_at,
                final_state=TaskState.FAILED,
            )

    async def _reason_with_events(
        self,
        task: Task,
        engine: ReasoningEngine,
    ) -> AsyncIterator[ReasoningStep]:
        """Execute reasoning and yield steps as events.

        Subclasses should override the `reason` method to implement
        their specific reasoning logic. This method wraps that logic
        to yield events.

        Args:
            task: The task being processed
            engine: Reasoning engine for tool calls

        Yields:
            ReasoningStep objects as they are created
        """
        # Default implementation - subclasses override reason()
        async for step in engine.execute_reasoning(
            reasoning_func=lambda: self.reason(task, engine)
        ):
            yield step

    async def reason(self, task: Task, engine: ReasoningEngine) -> None:
        """Execute the reasoning logic for this task.

        Subclasses MUST override this method to implement their
        specific reasoning behavior. Use the engine to:
        - Call LLMs for reasoning
        - Call tools for actions
        - Add thinking steps
        - Create synthesis steps

        Args:
            task: The task to reason about
            engine: Reasoning engine providing tool access

        Example:
            >>> async def reason(self, task: Task, engine: ReasoningEngine) -> None:
            ...     # Analyze the request
            ...     engine.add_thinking("I need to analyze the user's request")
            ...
            ...     analysis = await engine.call_llm(
            ...         prompt=f"Analyze: {task.messages[-1].parts[0].text}",
            ...         model="claude-sonnet-4"
            ...     )
            ...
            ...     # Take action based on analysis
            ...     if "database" in analysis:
            ...         data = await engine.call_tool("database", {"query": "..."})
            ...
            ...     # Synthesize final response
            ...     engine.add_synthesis(
            ...         conclusion="Based on my analysis...",
            ...         sources=[analysis.step_id]
            ...     )
        """
        raise NotImplementedError(
            "Subclasses must implement the reason() method to define "
            "their reasoning logic."
        )
```

---

### 6.1. AutonomousCoTAgent (ReAct Implementation)

**Location**: `src/omniforge/agents/cot/autonomous.py`

**Purpose**: Concrete implementation of CoTAgent using ReAct pattern for fully autonomous reasoning.

**Key Features:**
- **Zero-code usage**: Users just provide task description
- **Autonomous decision making**: LLM decides all actions
- **ReAct loop**: Thought → Action → Observation → Repeat
- **Self-terminating**: Knows when task is complete
- **Error recovery**: Handles tool failures gracefully

**Architecture:**

```python
"""Autonomous CoT Agent using ReAct pattern."""

import json
import re
from typing import Any, Optional
from abc import abstractmethod

from omniforge.agents.cot.agent import CoTAgent
from omniforge.agents.cot.engine import ReasoningEngine
from omniforge.agents.models import AgentIdentity
from omniforge.tasks.models import Task
from omniforge.tools.base import ToolDefinition


class AutonomousCoTAgent(CoTAgent):
    """Fully autonomous agent using ReAct reasoning pattern.

    Users simply provide a task description. The agent autonomously:
    - Decides which tools to call
    - Generates its own prompts
    - Determines when the task is complete

    Example:
        >>> agent = AutonomousCoTAgent()
        >>> task = Task(messages=[Message(parts=[TextPart(
        ...     text="Analyze Q4 sales and identify top 3 products"
        ... )])])
        >>> async for event in agent.process_task(task):
        ...     print(event)

        # Agent autonomously:
        # 1. Calls database tool to get sales data
        # 2. Calls LLM tool to analyze trends
        # 3. Synthesizes final answer
        # 4. Returns "Final Answer: Top 3 products are..."
    """

    identity = AgentIdentity(
        id="autonomous-cot-agent",
        name="Autonomous CoT Agent",
        description="Autonomous agent using ReAct for reasoning",
        version="1.0.0",
    )

    def __init__(
        self,
        max_iterations: int = 10,
        reasoning_model: str = "claude-sonnet-4",
        temperature: float = 0.0,
        **kwargs: Any,
    ):
        """Initialize autonomous agent.

        Args:
            max_iterations: Maximum reasoning iterations
            reasoning_model: LLM model for reasoning
            temperature: Temperature for LLM calls
            **kwargs: Passed to CoTAgent
        """
        super().__init__(**kwargs)
        self.max_iterations = max_iterations
        self.reasoning_model = reasoning_model
        self.temperature = temperature
        self._parser = ReActParser()

    async def reason(self, task: Task, engine: ReasoningEngine) -> None:
        """Execute autonomous ReAct loop.

        This implements the abstract reason() method from CoTAgent
        using the ReAct pattern for autonomous reasoning.
        """
        # Build system prompt with available tools
        system_prompt = self._build_system_prompt(engine)

        # Initialize conversation
        conversation = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": task.messages[-1].parts[0].text},
        ]

        # ReAct loop
        for iteration in range(self.max_iterations):
            engine.add_thinking(
                f"Iteration {iteration + 1}/{self.max_iterations}"
            )

            # Call LLM to decide next action
            llm_result = await engine.call_llm(
                messages=conversation,
                model=self.reasoning_model,
                temperature=self.temperature,
            )

            # Parse response
            parsed = self._parser.parse(llm_result.value)

            if parsed.thought:
                engine.add_thinking(parsed.thought)

            # Check if done
            if parsed.is_final:
                engine.add_synthesis(
                    conclusion=parsed.final_answer,
                    sources=[step.id for step in engine.chain.steps],
                )
                return

            # Execute action
            if not parsed.action:
                raise ValueError(
                    f"LLM did not provide valid action: {llm_result.value}"
                )

            try:
                tool_result = await engine.call_tool(
                    parsed.action, parsed.action_input or {}
                )
                observation = tool_result.value
            except Exception as e:
                observation = f"Error: {str(e)}"

            # Continue conversation
            conversation.append(
                {"role": "assistant", "content": llm_result.value}
            )
            conversation.append(
                {"role": "user", "content": f"Observation: {observation}"}
            )

        # Max iterations reached
        raise MaxIterationsError(
            f"Agent did not complete task in {self.max_iterations} iterations"
        )

    def _build_system_prompt(self, engine: ReasoningEngine) -> str:
        """Build ReAct system prompt with tool descriptions."""
        tools = engine.get_available_tools()
        tool_descriptions = self._format_tool_descriptions(tools)

        return f"""You are an autonomous AI agent that can reason and act.

You have access to the following tools:

{tool_descriptions}

Use the following format:

Thought: <your reasoning>
Action: <tool name>
Action Input: <JSON arguments>
Observation: <tool result appears here>
... (repeat as needed)
Thought: <final reasoning>
Final Answer: <your response>

RULES:
1. Always start with "Thought:" explaining your reasoning
2. Use "Action:" to specify the tool
3. Use "Action Input:" with valid JSON
4. Wait for "Observation:" before continuing
5. When done, output "Final Answer:"
6. NEVER make up observations
7. Action Input MUST be valid JSON

Begin!"""

    def _format_tool_descriptions(
        self, tools: list[ToolDefinition]
    ) -> str:
        """Format tools for system prompt."""
        descriptions = []
        for tool in tools:
            desc = f"**{tool.name}**: {tool.description}"
            if tool.parameters:
                desc += "\n  Parameters:"
                for name, info in tool.parameters.items():
                    req = "required" if info.get("required") else "optional"
                    desc += f"\n    - {name} ({info.get('type')}, {req}): {info.get('description')}"
            descriptions.append(desc)
        return "\n\n".join(descriptions)


class ReActParser:
    """Parser for ReAct format responses."""

    THOUGHT_PATTERN = r"Thought:\s*(.+?)(?=\n(?:Action|Final Answer):|$)"
    ACTION_PATTERN = r"Action:\s*(\w+)"
    ACTION_INPUT_PATTERN = r"Action Input:\s*({.+?})"
    FINAL_ANSWER_PATTERN = r"Final Answer:\s*(.+?)$"

    def parse(self, response: str) -> "ParsedResponse":
        """Parse LLM response into ReAct format."""
        thought_match = re.search(self.THOUGHT_PATTERN, response, re.DOTALL)
        thought = thought_match.group(1).strip() if thought_match else None

        # Check for final answer
        final_match = re.search(
            self.FINAL_ANSWER_PATTERN, response, re.DOTALL | re.MULTILINE
        )
        if final_match:
            return ParsedResponse(
                thought=thought,
                is_final=True,
                final_answer=final_match.group(1).strip(),
            )

        # Extract action
        action_match = re.search(self.ACTION_PATTERN, response)
        action = action_match.group(1).strip() if action_match else None

        # Extract action input
        input_match = re.search(self.ACTION_INPUT_PATTERN, response, re.DOTALL)
        if input_match:
            try:
                action_input = json.loads(input_match.group(1))
            except json.JSONDecodeError:
                action_input = None
        else:
            action_input = None

        return ParsedResponse(
            thought=thought,
            is_final=False,
            action=action,
            action_input=action_input,
        )


class ParsedResponse:
    """Parsed ReAct response."""

    def __init__(
        self,
        thought: Optional[str] = None,
        is_final: bool = False,
        final_answer: Optional[str] = None,
        action: Optional[str] = None,
        action_input: Optional[dict[str, Any]] = None,
    ):
        self.thought = thought
        self.is_final = is_final
        self.final_answer = final_answer
        self.action = action
        self.action_input = action_input


class MaxIterationsError(Exception):
    """Raised when agent exceeds maximum iterations."""
    pass
```

**Usage:**

```python
# Zero-code usage - just provide a task
agent = AutonomousCoTAgent(
    max_iterations=10,
    reasoning_model="claude-sonnet-4"
)

task = Task(messages=[
    Message(parts=[TextPart(
        text="What's the weather in SF and Paris? Compare them."
    )])
])

# Agent autonomously:
# 1. Thinks: "I need weather for both cities"
# 2. Calls: weather_api for SF
# 3. Observes: temperature, conditions
# 4. Calls: weather_api for Paris
# 5. Observes: temperature, conditions
# 6. Thinks: "Now I can compare"
# 7. Returns: "Final Answer: SF is warmer..."
async for event in agent.process_task(task):
    print(event)
```

**How it integrates:**
- Uses existing `CoTAgent.process_task()` for orchestration
- Uses existing `ReasoningEngine` for tool calls
- Uses existing `ToolExecutor` and unified tool interface
- **Only adds**: ReAct loop logic + response parsing

---

### 7. Reasoning Engine

**Location**: `src/omniforge/agents/cot/engine.py`

**Purpose**: Provides a convenient API for agents to interact with tools and build reasoning chains.

```python
"""Reasoning Engine for Chain of Thought agents.

The ReasoningEngine provides a high-level API for agents to:
- Call LLMs for reasoning
- Execute tools
- Add thinking steps
- Create synthesis steps
- Manage the reasoning chain
"""

from datetime import datetime
from typing import Any, AsyncIterator, Callable, Coroutine, Optional
from uuid import UUID, uuid4

from omniforge.agents.cot.chain import (
    ReasoningChain,
    ReasoningStep,
    StepType,
    SynthesisInfo,
    ThinkingInfo,
    ToolType,
    VisibilityConfig,
    VisibilityLevel,
)
from omniforge.tasks.models import Task
from omniforge.tools.base import ToolCallContext, ToolResult
from omniforge.tools.executor import ToolExecutor


class ToolCallResult:
    """Result of a tool call with step reference."""

    def __init__(
        self,
        result: ToolResult,
        call_step: ReasoningStep,
        result_step: ReasoningStep,
    ) -> None:
        self.result = result
        self.call_step = call_step
        self.result_step = result_step

    @property
    def step_id(self) -> UUID:
        """ID of the result step for synthesis references."""
        return self.result_step.id

    @property
    def success(self) -> bool:
        return self.result.success

    @property
    def value(self) -> Any:
        return self.result.result

    @property
    def error(self) -> Optional[str]:
        return self.result.error


class ReasoningEngine:
    """Engine for executing reasoning with tool calls.

    The ReasoningEngine provides a convenient API for agents to:
    - Call LLMs through the unified tool interface
    - Execute other tools
    - Add thinking and synthesis steps
    - Stream reasoning events

    Example:
        >>> engine = ReasoningEngine(chain, executor, task)
        >>>
        >>> # Add a thinking step
        >>> engine.add_thinking("I need to analyze the data first")
        >>>
        >>> # Call LLM for analysis
        >>> result = await engine.call_llm(
        ...     prompt="Analyze this data",
        ...     model="claude-sonnet-4"
        ... )
        >>>
        >>> # Call a database tool
        >>> data = await engine.call_tool("database", {"query": "SELECT ..."})
        >>>
        >>> # Synthesize results
        >>> engine.add_synthesis(
        ...     conclusion="The analysis shows...",
        ...     sources=[result.step_id, data.step_id]
        ... )
    """

    def __init__(
        self,
        chain: ReasoningChain,
        executor: ToolExecutor,
        task: Task,
        default_llm_model: str = "claude-sonnet-4",
    ) -> None:
        """Initialize the reasoning engine.

        Args:
            chain: The reasoning chain to add steps to
            executor: Tool executor for running tools
            task: The task being processed
            default_llm_model: Default LLM model to use
        """
        self._chain = chain
        self._executor = executor
        self._task = task
        self._default_model = default_llm_model
        self._pending_steps: list[ReasoningStep] = []

    @property
    def chain(self) -> ReasoningChain:
        """Get the reasoning chain."""
        return self._chain

    @property
    def task(self) -> Task:
        """Get the task being processed."""
        return self._task

    def add_thinking(
        self,
        thought: str,
        confidence: Optional[float] = None,
        visibility: VisibilityLevel = VisibilityLevel.FULL,
    ) -> ReasoningStep:
        """Add a thinking step to the chain.

        Args:
            thought: The thinking content
            confidence: Optional confidence score (0-1)
            visibility: Visibility level for this step

        Returns:
            The created ReasoningStep
        """
        step = ReasoningStep(
            type=StepType.THINKING,
            thinking=ThinkingInfo(
                thought=thought,
                confidence=confidence,
            ),
            visibility=VisibilityConfig(level=visibility),
        )
        self._chain.add_step(step)
        self._pending_steps.append(step)
        return step

    def add_synthesis(
        self,
        conclusion: str,
        sources: list[UUID],
        visibility: VisibilityLevel = VisibilityLevel.FULL,
    ) -> ReasoningStep:
        """Add a synthesis step that combines previous results.

        Args:
            conclusion: The synthesized conclusion
            sources: List of step IDs that informed this synthesis
            visibility: Visibility level for this step

        Returns:
            The created ReasoningStep
        """
        step = ReasoningStep(
            type=StepType.SYNTHESIS,
            synthesis=SynthesisInfo(
                sources=sources,
                conclusion=conclusion,
            ),
            visibility=VisibilityConfig(level=visibility),
        )
        self._chain.add_step(step)
        self._pending_steps.append(step)
        return step

    async def call_llm(
        self,
        prompt: str,
        model: Optional[str] = None,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        visibility: VisibilityLevel = VisibilityLevel.FULL,
    ) -> ToolCallResult:
        """Call an LLM through the unified tool interface.

        This method wraps the LLM tool to provide a convenient API
        for reasoning operations.

        Args:
            prompt: The prompt to send
            model: Model to use (defaults to engine's default)
            system: Optional system prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            visibility: Visibility level for this step

        Returns:
            ToolCallResult with response and step references
        """
        arguments = {
            "model": model or self._default_model,
            "prompt": prompt,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if system:
            arguments["system"] = system

        return await self._call_tool_internal("llm", arguments, visibility)

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        visibility: Optional[VisibilityLevel] = None,
    ) -> ToolCallResult:
        """Call any registered tool.

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments
            visibility: Optional visibility override

        Returns:
            ToolCallResult with result and step references
        """
        return await self._call_tool_internal(tool_name, arguments, visibility)

    async def _call_tool_internal(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        visibility: Optional[VisibilityLevel] = None,
    ) -> ToolCallResult:
        """Internal method to execute a tool call.

        Args:
            tool_name: Name of the tool
            arguments: Tool arguments
            visibility: Visibility level

        Returns:
            ToolCallResult
        """
        context = ToolCallContext(
            task_id=self._task.id,
            agent_id=self._task.agent_id,
            tenant_id=self._task.tenant_id,
            user_id=self._task.user_id,
            chain_id=self._chain.id,
        )

        # Execute tool (adds steps to chain internally)
        steps_before = len(self._chain.steps)
        result = await self._executor.execute(
            tool_name=tool_name,
            arguments=arguments,
            context=context,
            chain=self._chain,
        )
        steps_after = len(self._chain.steps)

        # Get the steps that were added
        new_steps = self._chain.steps[steps_before:steps_after]
        call_step = new_steps[0] if new_steps else None
        result_step = new_steps[1] if len(new_steps) > 1 else None

        # Track pending steps
        for step in new_steps:
            self._pending_steps.append(step)

        return ToolCallResult(
            result=result,
            call_step=call_step,
            result_step=result_step,
        )

    async def execute_reasoning(
        self,
        reasoning_func: Callable[[], Coroutine[Any, Any, None]],
    ) -> AsyncIterator[ReasoningStep]:
        """Execute a reasoning function and yield steps as they are created.

        This method wraps the reasoning logic to yield steps as events
        for streaming to clients.

        Args:
            reasoning_func: Async function that performs reasoning

        Yields:
            ReasoningStep objects as they are created
        """
        # Clear pending steps
        self._pending_steps.clear()

        # Start reasoning in background
        import asyncio
        reasoning_task = asyncio.create_task(reasoning_func())

        # Yield steps as they are added
        yielded_count = 0
        while not reasoning_task.done():
            # Yield any new steps
            while yielded_count < len(self._pending_steps):
                yield self._pending_steps[yielded_count]
                yielded_count += 1

            # Small delay to avoid busy waiting
            await asyncio.sleep(0.01)

        # Wait for completion and check for errors
        try:
            await reasoning_task
        except Exception:
            raise

        # Yield any remaining steps
        while yielded_count < len(self._pending_steps):
            yield self._pending_steps[yielded_count]
            yielded_count += 1
```

---

## Database Schema

### Entity-Relationship Diagram

```
+------------------+       +------------------+       +------------------+
|  reasoning_chains|       |  reasoning_steps |       |    tool_calls    |
+------------------+       +------------------+       +------------------+
| id (PK)          |<---+  | id (PK)          |       | id (PK)          |
| task_id          |    |  | chain_id (FK)    |-------| step_id (FK)     |
| agent_id         |    +--| step_number      |       | tool_type        |
| status           |       | type             |       | tool_name        |
| started_at       |       | timestamp        |       | arguments (JSON) |
| completed_at     |       | thinking (JSON)  |       | correlation_id   |
| metrics (JSON)   |       | tool_call (JSON) |       +------------------+
| tenant_id        |       | tool_result (JSON)|
+------------------+       | synthesis (JSON) |       +------------------+
                           | visibility (JSON)|       |   cost_records   |
                           | parent_step_id   |       +------------------+
                           +------------------+       | id (PK)          |
                                                      | tenant_id        |
+------------------+                                  | task_id          |
|   model_usage    |                                  | tool_name        |
+------------------+                                  | cost_usd         |
| id (PK)          |                                  | tokens           |
| tenant_id        |                                  | model            |
| model            |                                  | created_at       |
| input_tokens     |                                  +------------------+
| output_tokens    |
| cost_usd         |
| timestamp        |
+------------------+
```

### SQLAlchemy ORM Models

**Location**: `src/omniforge/storage/models.py` (extend existing)

```python
"""ORM models for reasoning chain persistence.

These models extend the existing storage models to support
chain of thought reasoning persistence.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship

from omniforge.storage.models import Base


class ReasoningChainModel(Base):
    """Persistent reasoning chain storage."""

    __tablename__ = "reasoning_chains"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    task_id = Column(String(255), nullable=False, index=True)
    agent_id = Column(String(255), nullable=False, index=True)

    # Status
    status = Column(String(50), nullable=False, default="initializing")

    # Timestamps
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Metrics (aggregated)
    metrics = Column(JSON, nullable=False, default=dict)

    # Child chains (for sub-agent delegation)
    child_chain_ids = Column(JSON, nullable=False, default=list)

    # Multi-tenancy
    tenant_id = Column(String(100), nullable=True, index=True)

    # Relationships
    steps = relationship(
        "ReasoningStepModel",
        back_populates="chain",
        order_by="ReasoningStepModel.step_number",
    )

    __table_args__ = (
        Index("ix_chains_tenant_task", "tenant_id", "task_id"),
        Index("ix_chains_tenant_status", "tenant_id", "status"),
    )


class ReasoningStepModel(Base):
    """Persistent reasoning step storage."""

    __tablename__ = "reasoning_steps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    chain_id = Column(
        UUID(as_uuid=True),
        ForeignKey("reasoning_chains.id", ondelete="CASCADE"),
        nullable=False,
    )
    step_number = Column(Integer, nullable=False)
    type = Column(String(50), nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Type-specific data (one will be populated based on type)
    thinking = Column(JSON, nullable=True)
    tool_call = Column(JSON, nullable=True)
    tool_result = Column(JSON, nullable=True)
    synthesis = Column(JSON, nullable=True)

    # Visibility
    visibility = Column(JSON, nullable=False, default=dict)

    # Parent step (for nested operations)
    parent_step_id = Column(UUID(as_uuid=True), nullable=True)

    # Relationships
    chain = relationship("ReasoningChainModel", back_populates="steps")

    __table_args__ = (
        Index("ix_steps_chain_number", "chain_id", "step_number"),
        Index("ix_steps_chain_type", "chain_id", "type"),
    )


class CostRecordModel(Base):
    """Cost tracking record for billing and budgets."""

    __tablename__ = "cost_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(String(100), nullable=False, index=True)
    task_id = Column(String(255), nullable=False, index=True)
    chain_id = Column(UUID(as_uuid=True), nullable=True)
    step_id = Column(UUID(as_uuid=True), nullable=True)

    # Cost details
    tool_name = Column(String(100), nullable=False)
    cost_usd = Column(Float, nullable=False)
    tokens = Column(Integer, nullable=True)
    model = Column(String(100), nullable=True)

    # Timestamp
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_cost_tenant_date", "tenant_id", "created_at"),
        Index("ix_cost_tenant_task", "tenant_id", "task_id"),
    )


class ModelUsageModel(Base):
    """Aggregated model usage for reporting."""

    __tablename__ = "model_usage"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(String(100), nullable=False, index=True)
    model = Column(String(100), nullable=False)
    date = Column(DateTime, nullable=False)  # Truncated to day

    # Usage metrics
    call_count = Column(Integer, nullable=False, default=0)
    input_tokens = Column(Integer, nullable=False, default=0)
    output_tokens = Column(Integer, nullable=False, default=0)
    total_cost_usd = Column(Float, nullable=False, default=0.0)

    __table_args__ = (
        Index("ix_usage_tenant_model_date", "tenant_id", "model", "date", unique=True),
    )
```

---

## Streaming Event Flow

### Reasoning Event Types

**Location**: `src/omniforge/agents/cot/events.py`

```python
"""Reasoning-specific events for SSE streaming.

These events extend the base task events to support streaming
reasoning chain updates to clients.
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from omniforge.agents.cot.chain import ChainMetrics, ReasoningStep
from omniforge.agents.events import BaseTaskEvent


class ChainStartedEvent(BaseTaskEvent):
    """Event emitted when a reasoning chain starts."""

    type: Literal["chain_started"] = "chain_started"
    chain_id: UUID


class ReasoningStepEvent(BaseTaskEvent):
    """Event emitted for each reasoning step."""

    type: Literal["reasoning_step"] = "reasoning_step"
    chain_id: UUID
    step: ReasoningStep


class ChainCompletedEvent(BaseTaskEvent):
    """Event emitted when a reasoning chain completes."""

    type: Literal["chain_completed"] = "chain_completed"
    chain_id: UUID
    metrics: ChainMetrics


class ChainFailedEvent(BaseTaskEvent):
    """Event emitted when a reasoning chain fails."""

    type: Literal["chain_failed"] = "chain_failed"
    chain_id: UUID
    error_code: str
    error_message: str
```

### SSE Stream Format

```
event: chain_started
data: {"task_id": "abc123", "chain_id": "xyz789", "timestamp": "..."}

event: reasoning_step
data: {
  "task_id": "abc123",
  "chain_id": "xyz789",
  "step": {
    "id": "step001",
    "step_number": 1,
    "type": "tool_call",
    "tool_call": {
      "tool_type": "llm",
      "tool_name": "llm",
      "arguments": {"model": "claude-sonnet-4", "prompt": "..."},
      "correlation_id": "corr001"
    },
    "visibility": {"level": "full"}
  }
}

event: reasoning_step
data: {
  "task_id": "abc123",
  "chain_id": "xyz789",
  "step": {
    "id": "step002",
    "step_number": 2,
    "type": "tool_result",
    "tool_result": {
      "correlation_id": "corr001",
      "success": true,
      "result": "Analysis shows...",
      "duration_ms": 1234,
      "model": "claude-sonnet-4",
      "input_tokens": 450,
      "output_tokens": 380,
      "cost_usd": 0.0156
    },
    "visibility": {"level": "full", "summary": "LLM call: claude-sonnet-4 (830 tokens, $0.0156)"}
  }
}

event: reasoning_step
data: {
  "step": {
    "type": "thinking",
    "thinking": {"thought": "I need to query the database for sales data"}
  }
}

event: reasoning_step
data: {"step": {"type": "tool_call", "tool_call": {"tool_type": "database", ...}}}

event: reasoning_step
data: {"step": {"type": "tool_result", "tool_result": {"rows_returned": 1247, ...}}}

event: reasoning_step
data: {
  "step": {
    "type": "synthesis",
    "synthesis": {
      "sources": ["step002", "step005"],
      "conclusion": "Based on the analysis and data..."
    }
  }
}

event: chain_completed
data: {
  "task_id": "abc123",
  "chain_id": "xyz789",
  "metrics": {
    "total_steps": 6,
    "llm_calls": 2,
    "tool_calls": 3,
    "total_tokens": 1247,
    "total_cost_usd": 0.0234,
    "total_duration_ms": 4521
  }
}

event: done
data: {"task_id": "abc123", "final_state": "completed"}
```

---

## Enterprise Controls

### Rate Limiting

**Location**: `src/omniforge/enterprise/rate_limiter.py`

```python
"""Rate limiting for enterprise quota enforcement.

Provides per-tenant rate limiting for tool calls, tokens, and costs.
"""

from datetime import datetime, timedelta
from typing import Optional

from aiolimiter import AsyncLimiter
from pydantic import BaseModel, Field

from omniforge.agents.cot.chain import ToolType


class RateLimitConfig(BaseModel):
    """Rate limit configuration for a tenant."""

    # Calls per minute by tool type
    llm_calls_per_minute: int = Field(default=60, ge=1)
    external_calls_per_minute: int = Field(default=100, ge=1)
    database_calls_per_minute: int = Field(default=500, ge=1)

    # Token limits
    tokens_per_minute: int = Field(default=100000, ge=1000)
    tokens_per_hour: int = Field(default=1000000, ge=10000)

    # Cost limits
    cost_per_hour_usd: float = Field(default=10.0, ge=0.01)
    cost_per_day_usd: float = Field(default=100.0, ge=0.1)


class TenantLimiter:
    """Rate limiter for a single tenant."""

    def __init__(self, config: RateLimitConfig) -> None:
        self._config = config
        self._llm_limiter = AsyncLimiter(config.llm_calls_per_minute, 60)
        self._external_limiter = AsyncLimiter(config.external_calls_per_minute, 60)
        self._database_limiter = AsyncLimiter(config.database_calls_per_minute, 60)
        self._token_minute_limiter = AsyncLimiter(config.tokens_per_minute, 60)
        self._token_hour_limiter = AsyncLimiter(config.tokens_per_hour, 3600)

        # Cost tracking (sliding window)
        self._hourly_cost: float = 0.0
        self._daily_cost: float = 0.0
        self._hour_start: datetime = datetime.utcnow()
        self._day_start: datetime = datetime.utcnow()

    async def check_and_consume(
        self,
        tool_type: ToolType,
        tokens: int = 0,
        cost_usd: float = 0.0,
    ) -> bool:
        """Check rate limits and consume quota if allowed.

        Args:
            tool_type: Type of tool being called
            tokens: Number of tokens to consume
            cost_usd: Cost in USD to consume

        Returns:
            True if allowed, False if rate limited
        """
        # Check call rate
        limiter = self._get_limiter(tool_type)
        if not await limiter.acquire(1):
            return False

        # Check token limits
        if tokens > 0:
            if not await self._token_minute_limiter.acquire(tokens):
                return False
            if not await self._token_hour_limiter.acquire(tokens):
                return False

        # Check cost limits
        self._reset_windows_if_needed()
        if self._hourly_cost + cost_usd > self._config.cost_per_hour_usd:
            return False
        if self._daily_cost + cost_usd > self._config.cost_per_day_usd:
            return False

        # Consume cost
        self._hourly_cost += cost_usd
        self._daily_cost += cost_usd

        return True

    def _get_limiter(self, tool_type: ToolType) -> AsyncLimiter:
        if tool_type == ToolType.LLM:
            return self._llm_limiter
        elif tool_type == ToolType.DATABASE:
            return self._database_limiter
        else:
            return self._external_limiter

    def _reset_windows_if_needed(self) -> None:
        now = datetime.utcnow()
        if now - self._hour_start > timedelta(hours=1):
            self._hourly_cost = 0.0
            self._hour_start = now
        if now - self._day_start > timedelta(days=1):
            self._daily_cost = 0.0
            self._day_start = now


class RateLimiter:
    """Multi-tenant rate limiter."""

    def __init__(self, default_config: Optional[RateLimitConfig] = None) -> None:
        self._default_config = default_config or RateLimitConfig()
        self._tenant_limiters: dict[str, TenantLimiter] = {}
        self._tenant_configs: dict[str, RateLimitConfig] = {}

    def configure_tenant(self, tenant_id: str, config: RateLimitConfig) -> None:
        """Configure rate limits for a specific tenant."""
        self._tenant_configs[tenant_id] = config
        self._tenant_limiters[tenant_id] = TenantLimiter(config)

    async def check_and_consume(
        self,
        tenant_id: str,
        tool_type: ToolType,
        tokens: int = 0,
        cost_usd: float = 0.0,
    ) -> bool:
        """Check and consume rate limit for a tenant."""
        if tenant_id not in self._tenant_limiters:
            config = self._tenant_configs.get(tenant_id, self._default_config)
            self._tenant_limiters[tenant_id] = TenantLimiter(config)

        return await self._tenant_limiters[tenant_id].check_and_consume(
            tool_type, tokens, cost_usd
        )
```

### Cost Tracking

**Location**: `src/omniforge/enterprise/cost_tracker.py`

```python
"""Cost tracking for billing and budget enforcement.

Tracks costs at tenant, task, and operation level for billing,
budgets, and usage analytics.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from omniforge.storage.base import CostRepository


class CostRecord(BaseModel):
    """Record of a cost incurred."""

    tenant_id: str
    task_id: str
    chain_id: Optional[UUID] = None
    step_id: Optional[UUID] = None
    tool_name: str
    cost_usd: float
    tokens: Optional[int] = None
    model: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TaskBudget(BaseModel):
    """Budget constraints for a task."""

    max_cost_usd: Optional[float] = None
    max_tokens: Optional[int] = None
    max_llm_calls: Optional[int] = None


class CostTracker:
    """Tracks costs and enforces budgets.

    The CostTracker records costs from tool executions and provides
    budget checking for tasks.

    Example:
        >>> tracker = CostTracker(repository)
        >>>
        >>> # Record a cost
        >>> await tracker.record_cost(
        ...     tenant_id="tenant-1",
        ...     task_id="task-123",
        ...     tool_name="llm",
        ...     cost_usd=0.0156,
        ...     tokens=830
        ... )
        >>>
        >>> # Check remaining budget
        >>> remaining = await tracker.get_remaining_budget(
        ...     task_id="task-123",
        ...     budget=TaskBudget(max_cost_usd=1.0)
        ... )
        >>> print(f"Remaining: ${remaining.cost_usd}")
    """

    def __init__(self, repository: Optional[CostRepository] = None) -> None:
        self._repository = repository
        self._task_costs: dict[str, float] = {}
        self._task_tokens: dict[str, int] = {}
        self._task_llm_calls: dict[str, int] = {}

    async def record_cost(
        self,
        tenant_id: str,
        task_id: str,
        tool_name: str,
        cost_usd: float,
        tokens: Optional[int] = None,
        model: Optional[str] = None,
        chain_id: Optional[UUID] = None,
        step_id: Optional[UUID] = None,
    ) -> None:
        """Record a cost for a tool execution.

        Args:
            tenant_id: Tenant identifier
            task_id: Task identifier
            tool_name: Name of the tool
            cost_usd: Cost in USD
            tokens: Number of tokens (for LLM calls)
            model: Model used (for LLM calls)
            chain_id: Reasoning chain ID
            step_id: Reasoning step ID
        """
        # Update in-memory tracking
        self._task_costs[task_id] = self._task_costs.get(task_id, 0.0) + cost_usd
        if tokens:
            self._task_tokens[task_id] = self._task_tokens.get(task_id, 0) + tokens
        if tool_name == "llm":
            self._task_llm_calls[task_id] = self._task_llm_calls.get(task_id, 0) + 1

        # Persist if repository available
        if self._repository:
            record = CostRecord(
                tenant_id=tenant_id,
                task_id=task_id,
                chain_id=chain_id,
                step_id=step_id,
                tool_name=tool_name,
                cost_usd=cost_usd,
                tokens=tokens,
                model=model,
            )
            await self._repository.save(record)

    async def get_task_cost(self, task_id: str) -> float:
        """Get total cost for a task."""
        return self._task_costs.get(task_id, 0.0)

    async def get_task_tokens(self, task_id: str) -> int:
        """Get total tokens for a task."""
        return self._task_tokens.get(task_id, 0)

    async def check_budget(
        self,
        task_id: str,
        budget: TaskBudget,
        additional_cost: float = 0.0,
        additional_tokens: int = 0,
    ) -> bool:
        """Check if operation would exceed budget.

        Args:
            task_id: Task identifier
            budget: Budget constraints
            additional_cost: Cost to add
            additional_tokens: Tokens to add

        Returns:
            True if within budget, False if would exceed
        """
        current_cost = self._task_costs.get(task_id, 0.0)
        current_tokens = self._task_tokens.get(task_id, 0)
        current_calls = self._task_llm_calls.get(task_id, 0)

        if budget.max_cost_usd and current_cost + additional_cost > budget.max_cost_usd:
            return False
        if budget.max_tokens and current_tokens + additional_tokens > budget.max_tokens:
            return False
        if budget.max_llm_calls and current_calls >= budget.max_llm_calls:
            return False

        return True

    async def get_remaining_budget(
        self,
        task_id: str,
        budget: TaskBudget,
    ) -> TaskBudget:
        """Get remaining budget for a task.

        Args:
            task_id: Task identifier
            budget: Original budget constraints

        Returns:
            TaskBudget with remaining amounts
        """
        current_cost = self._task_costs.get(task_id, 0.0)
        current_tokens = self._task_tokens.get(task_id, 0)
        current_calls = self._task_llm_calls.get(task_id, 0)

        return TaskBudget(
            max_cost_usd=(budget.max_cost_usd - current_cost) if budget.max_cost_usd else None,
            max_tokens=(budget.max_tokens - current_tokens) if budget.max_tokens else None,
            max_llm_calls=(budget.max_llm_calls - current_calls) if budget.max_llm_calls else None,
        )
```

---

## API Endpoints

### Chain Endpoints

**Location**: `src/omniforge/api/routes/chains.py`

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/api/v1/chains/{chain_id}` | Get reasoning chain by ID | Required |
| GET | `/api/v1/tasks/{task_id}/chain` | Get chain for a task | Required |
| GET | `/api/v1/chains/{chain_id}/steps` | List steps with pagination | Required |
| GET | `/api/v1/tenants/{tenant_id}/chains` | List chains for tenant | Required |

### Usage/Cost Endpoints

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/api/v1/tenants/{tenant_id}/usage` | Get usage summary | Admin |
| GET | `/api/v1/tenants/{tenant_id}/costs` | Get cost breakdown | Admin |
| GET | `/api/v1/tasks/{task_id}/costs` | Get task cost details | Required |

---

## Testing Strategy

### Unit Tests

**Target Coverage**: >= 80%

| Module | Test Focus |
|--------|------------|
| `agents/cot/chain.py` | Chain/step model validation, metrics calculation |
| `agents/cot/engine.py` | Reasoning flow, step creation, event generation |
| `tools/base.py` | Tool interface contracts, validation |
| `tools/executor.py` | Retry logic, timeout handling, chain integration |
| `tools/builtin/llm.py` | LiteLLM integration, cost calculation |
| `enterprise/rate_limiter.py` | Rate limiting logic, window reset |
| `enterprise/cost_tracker.py` | Cost tracking, budget enforcement |

### Integration Tests

| Test Scenario | Description |
|---------------|-------------|
| Full reasoning flow | Task submission through chain completion |
| SSE streaming | Events delivered in correct order |
| Multi-model reasoning | Agent switches between models |
| Rate limiting | Requests throttled correctly |
| Cost budgets | Execution stops when budget exceeded |
| Sub-agent delegation | Parent/child chain relationships |

### Example Test Structure

```python
# tests/agents/cot/test_chain.py

import pytest
from datetime import datetime
from uuid import uuid4

from omniforge.agents.cot.chain import (
    ReasoningChain,
    ReasoningStep,
    StepType,
    ThinkingInfo,
    ToolCallInfo,
    ToolResultInfo,
    ToolType,
)


class TestReasoningChain:
    """Tests for ReasoningChain data structure."""

    def test_create_empty_chain(self) -> None:
        """Chain should initialize with default values."""
        chain = ReasoningChain(
            task_id="task-123",
            agent_id="agent-456",
        )

        assert chain.task_id == "task-123"
        assert chain.agent_id == "agent-456"
        assert len(chain.steps) == 0
        assert chain.metrics.total_steps == 0

    def test_add_thinking_step(self) -> None:
        """Adding thinking step should update metrics."""
        chain = ReasoningChain(task_id="task-123", agent_id="agent-456")

        step = ReasoningStep(
            type=StepType.THINKING,
            thinking=ThinkingInfo(thought="Analyzing request"),
        )
        chain.add_step(step)

        assert len(chain.steps) == 1
        assert chain.metrics.total_steps == 1
        assert chain.steps[0].step_number == 1

    def test_add_tool_call_step(self) -> None:
        """Adding tool call step should track tool calls."""
        chain = ReasoningChain(task_id="task-123", agent_id="agent-456")

        step = ReasoningStep(
            type=StepType.TOOL_CALL,
            tool_call=ToolCallInfo(
                tool_type=ToolType.LLM,
                tool_name="llm",
                arguments={"model": "claude-sonnet-4"},
            ),
        )
        chain.add_step(step)

        assert chain.metrics.tool_calls == 1
        assert chain.metrics.llm_calls == 1

    def test_add_tool_result_updates_cost(self) -> None:
        """Tool result should update cost metrics."""
        chain = ReasoningChain(task_id="task-123", agent_id="agent-456")

        result_step = ReasoningStep(
            type=StepType.TOOL_RESULT,
            tool_result=ToolResultInfo(
                correlation_id=uuid4(),
                success=True,
                result="Analysis complete",
                duration_ms=1234,
                total_tokens=830,
                cost_usd=0.0156,
            ),
        )
        chain.add_step(result_step)

        assert chain.metrics.total_tokens == 830
        assert chain.metrics.total_cost_usd == 0.0156
        assert chain.metrics.total_duration_ms == 1234
```

---

## Performance Considerations

### Latency Optimization

| Operation | Target | Strategy |
|-----------|--------|----------|
| Tool dispatch | < 5ms | In-memory registry lookup |
| Chain serialization | < 10ms | Pydantic v2 with orjson |
| LiteLLM overhead | < 15ms | Connection pooling, pre-warmed |
| SSE event delivery | < 100ms | Non-blocking async queues |

### Caching Strategy

1. **Tool definitions**: Cached in registry (never expire)
2. **LLM responses**: Optional caching with TTL (configurable)
3. **Agent cards**: Cached 5 minutes
4. **Rate limit state**: In-memory with periodic sync

### Scaling Considerations

1. **Stateless agents**: Chain state persisted, agent instances stateless
2. **Horizontal scaling**: Multiple agent instances behind load balancer
3. **Chain partitioning**: Chains partitioned by tenant for isolation
4. **Async everywhere**: All I/O async to maximize concurrency

---

## Security Architecture

### RBAC Extensions

**Location**: `src/omniforge/security/rbac.py` (extend)

```python
# New permissions for tools and chains
class Permission(str, Enum):
    # ... existing permissions ...

    # Tool permissions
    TOOL_EXECUTE = "tool:execute"
    TOOL_REGISTER = "tool:register"
    TOOL_CONFIGURE = "tool:configure"

    # Chain permissions
    CHAIN_READ = "chain:read"
    CHAIN_READ_FULL = "chain:read_full"  # Including hidden steps
    CHAIN_EXPORT = "chain:export"

    # Enterprise permissions
    RATE_LIMIT_CONFIGURE = "rate_limit:configure"
    COST_VIEW = "cost:view"
    COST_CONFIGURE = "cost:configure"
```

### Audit Logging

All tool executions are logged with:
- Tenant ID
- User ID
- Tool name and arguments (with sensitive field redaction)
- Result summary
- Cost/token metrics
- Timestamp

### Sensitive Data Handling

- Tool definitions specify `sensitive_fields` for redaction
- Reasoning chain visibility respects role permissions
- Prompts containing PII can be configured to use `summary` visibility
- Full audit logs accessible only to administrators

---

## Migration Path

### Integration with Existing Agents

Existing `BaseAgent` implementations continue to work unchanged. To adopt CoT capabilities:

1. **Option A: Extend CoTAgent**
   ```python
   class MyAgent(CoTAgent):
       async def reason(self, task, engine):
           # Implement reasoning logic
   ```

2. **Option B: Use Tool Interface Directly**
   ```python
   class MyAgent(BaseAgent):
       def __init__(self):
           self._executor = ToolExecutor(get_default_registry())

       async def process_task(self, task):
           result = await self._executor.execute("llm", {...}, context)
   ```

### Database Migrations

New tables required:
- `reasoning_chains`
- `reasoning_steps`
- `cost_records`
- `model_usage`

Migration scripts will be provided in `migrations/` directory.

---

## Implementation Phases

### Phase 1: Core CoT Engine and Unified Tool Interface (3-4 weeks)

**Goal**: Functional reasoning chain and tool execution framework.

**Deliverables**:
1. `agents/cot/chain.py` - ReasoningChain and ReasoningStep models
2. `agents/cot/events.py` - Reasoning-specific SSE events
3. `tools/base.py` - BaseTool and ToolDefinition
4. `tools/registry.py` - ToolRegistry
5. `tools/executor.py` - ToolExecutor with retries and timeouts
6. `tools/errors.py` - Tool exception hierarchy
7. Unit tests (80%+ coverage)

**Success Criteria**:
- [ ] ReasoningChain correctly tracks steps and metrics
- [ ] ToolExecutor handles retries and timeouts
- [ ] SSE events stream reasoning steps to clients
- [ ] CoTAgent base class implemented with abstract reason() method
- [ ] ReasoningEngine provides API for tool calls and chain management

### Phase 2: Agent Implementations (1-2 weeks)

**Goal**: Build CoTAgent base class and AutonomousCoTAgent (ReAct) implementation.

**Deliverables**:
1. `agents/cot/agent.py` - CoTAgent abstract base class
2. `agents/cot/engine.py` - ReasoningEngine for tool orchestration
3. `agents/cot/autonomous.py` - AutonomousCoTAgent with ReAct pattern
4. `agents/cot/parser.py` - ReActParser for parsing LLM responses
5. `agents/cot/prompts.py` - System prompt templates for ReAct
6. Integration tests with mocked tool registry
7. Example agents demonstrating different reasoning patterns

**Success Criteria**:
- [ ] CoTAgent properly orchestrates process_task() flow
- [ ] ReasoningEngine correctly manages tool calls and chain state
- [ ] AutonomousCoTAgent autonomously solves multi-step tasks
- [ ] ReActParser correctly extracts Thought/Action/Observation
- [ ] System prompts include tool descriptions dynamically
- [ ] Agent terminates on "Final Answer" or max iterations
- [ ] Error recovery works (tool failures don't crash agent)

**Example Usage:**
```python
# Zero-code autonomous agent
agent = AutonomousCoTAgent(max_iterations=10)
task = Task(messages=[Message(parts=[TextPart(text="Analyze Q4 sales")])])

# Agent autonomously:
# - Calls database tool
# - Analyzes results with LLM
# - Synthesizes answer
async for event in agent.process_task(task):
    print(event)
```

**Note**: This phase can be done in parallel with Phase 3 (LLM Tool), but benefits from having a mock LLM tool for testing.

---

### Phase 3: LLM Tool with LiteLLM Integration (2-3 weeks)

**Goal**: Full LLM tool with multi-provider support.

**Deliverables**:
1. `llm/client.py` - LiteLLM wrapper
2. `llm/config.py` - Provider configuration
3. `llm/cost.py` - Cost calculation utilities
4. `tools/builtin/llm.py` - LLM tool implementation
5. Integration tests with mocked providers

**Success Criteria**:
- [ ] LLM calls routed through unified interface
- [ ] Cost tracking accurate for known models
- [ ] Streaming responses work correctly
- [ ] Provider fallbacks function

### Phase 4: Built-in Tool Types (2-3 weeks)

**Goal**: Complete set of built-in tools.

**Deliverables**:
1. `tools/builtin/database.py` - Database query tool
2. `tools/builtin/filesystem.py` - File operations tool
3. `tools/builtin/subagent.py` - Sub-agent delegation tool
4. `tools/builtin/skill.py` - Internal skill invocation tool
5. `tools/builtin/external.py` - External API base tool

**Success Criteria**:
- [ ] All tool types execute through unified interface
- [ ] Sub-agent delegation creates proper chain relationships
- [ ] Database and file operations have appropriate permissions

### Phase 5: Cost Tracking and Rate Limiting (2 weeks)

**Goal**: Enterprise quota and budget enforcement.

**Deliverables**:
1. `enterprise/rate_limiter.py` - Per-tenant rate limiting
2. `enterprise/cost_tracker.py` - Cost tracking and budgets
3. `storage/models.py` - Cost record ORM models
4. API endpoints for usage/cost reporting

**Success Criteria**:
- [ ] Rate limiting enforced per tenant
- [ ] Cost budgets stop execution when exceeded
- [ ] Usage reports accurate

### Phase 6: Enterprise Features and Visibility Controls (2-3 weeks)

**Goal**: Production-ready enterprise features.

**Deliverables**:
1. `agents/cot/visibility.py` - Visibility control system
2. `enterprise/model_governance.py` - Approved model enforcement
3. `enterprise/audit.py` - Audit logging
4. `api/routes/chains.py` - Chain management endpoints
5. Database migrations

**Success Criteria**:
- [ ] Visibility respects role permissions
- [ ] Model governance enforced
- [ ] Complete audit trail for compliance
- [ ] Chain persistence and retrieval working

---

## Risk Assessment

### Technical Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| LiteLLM API changes | Medium | Low | Pin version, abstract wrapper layer |
| LLM provider outages | High | Medium | Automatic fallbacks, circuit breakers |
| Chain storage growth | Medium | High | Configurable retention, archival |
| Complex state management | Medium | Medium | Comprehensive tests, state machine pattern |
| SSE connection issues | Medium | Medium | Heartbeats, reconnection logic |

### Dependency Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| LiteLLM major update | Medium | Pin to ^1.50.0, abstraction layer |
| aiolimiter maintenance | Low | Simple dependency, easy to replace |
| tiktoken updates | Low | Used only for estimation |

---

## Alternative Approaches

### Alternative 1: Direct LLM Integration (Without LiteLLM)

**Description**: Implement provider-specific clients instead of using LiteLLM.

**Pros**:
- No external dependency
- Full control over implementation
- Potentially lower latency

**Cons**:
- Significant implementation effort (100+ providers)
- Ongoing maintenance burden
- No built-in cost tracking

**Recommendation**: Use LiteLLM for MVP; consider custom implementation only if specific needs arise.

### Alternative 2: Event Sourcing for Chains

**Description**: Store chains as append-only event logs instead of mutable documents.

**Pros**:
- Perfect audit trail
- Natural fit for streaming
- Easy replay

**Cons**:
- Higher storage requirements
- More complex querying
- Eventual consistency

**Recommendation**: Consider for v2 if audit requirements demand it.

### Alternative 3: Separate Tool Microservice

**Description**: Extract tool execution into a separate service.

**Pros**:
- Independent scaling
- Isolation of concerns
- Language-agnostic tools

**Cons**:
- Network latency
- Operational complexity
- Overkill for current scale

**Recommendation**: Keep integrated for MVP; revisit at scale.

---

## References

**OmniForge Internal:**
- [Product Specification](./cot-agent-with-unified-tools-spec.md)
- [Base Agent Interface Plan](./base-agent-interface-plan.md)
- [Existing BaseAgent Implementation](/Users/sohitkumar/code/omniforge/src/omniforge/agents/base.py)
- [Coding Guidelines](/Users/sohitkumar/code/omniforge/coding-guidelines.md)

**External:**
- [LiteLLM Documentation](https://docs.litellm.ai/)
- [LiteLLM GitHub](https://github.com/BerriAI/litellm)
- [A2A Protocol Specification v0.3](https://a2a-protocol.org/latest/specification/)
- [aiolimiter Documentation](https://aiolimiter.readthedocs.io/)
