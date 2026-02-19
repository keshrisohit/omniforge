# Prompt Management Module - Technical Implementation Plan

**Created**: 2026-01-11
**Last Updated**: 2026-01-11
**Version**: 1.0
**Status**: Draft

---

## Executive Summary

This technical plan defines the implementation architecture for OmniForge's Prompt Management Module, a foundational system enabling layered prompt composition, versioning, A/B testing, validation, and caching across the platform. The design follows existing codebase patterns (Pydantic models, Protocol-based repositories, FastAPI routes) while introducing new capabilities for enterprise-grade prompt management.

**Key Architectural Decisions:**

1. **Layered Composition Engine**: Five-layer prompt hierarchy (system, tenant, feature, agent, user) with merge-point-based composition using explicit merge behaviors (append, prepend, replace, inject)
2. **Jinja2 Sandboxed Templating**: Industry-standard templating with security sandboxing to prevent code execution and injection attacks
3. **Two-Tier Caching Strategy**: In-memory LRU cache for hot prompts with Redis-compatible distributed cache for multi-instance deployments
4. **Version-First Storage**: All prompt changes create new versions; current version is a pointer, enabling instant rollback
5. **Repository Pattern Consistency**: Following existing `TaskRepository`/`AgentRepository` patterns with Protocol interfaces and in-memory/database implementations
6. **Integrated A/B Testing**: Traffic splitting at composition time with statistical analysis for experiment evaluation

**Implementation Scope:**
- Phase 1: Core models, composition engine, and basic CRUD (2 weeks)
- Phase 2: Versioning, validation framework, and caching (2 weeks)
- Phase 3: A/B testing and experiments (1.5 weeks)
- Phase 4: SDK integration and API endpoints (1.5 weeks)
- Phase 5: Enterprise features and optimization (1 week)

---

## Requirements Analysis

### Functional Requirements (from Product Spec)

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| FR1 | Five-layer prompt hierarchy (system, tenant, feature, agent, user) | Must Have | Core architecture |
| FR2 | Merge-point-based composition with configurable behaviors | Must Have | append/prepend/replace/inject |
| FR3 | Jinja2 templating with variables, filters, conditionals, loops | Must Have | Sandboxed execution |
| FR4 | Prompt versioning with complete history | Must Have | Immutable versions |
| FR5 | Instant rollback to any previous version | Must Have | < 30 seconds |
| FR6 | A/B testing with traffic splitting | Must Have | 50/50 or custom splits |
| FR7 | Template syntax validation | Must Have | Pre-activation check |
| FR8 | Content validation (length, prohibited content) | Must Have | Configurable rules |
| FR9 | Multi-tenant isolation | Must Have | Zero cross-tenant leakage |
| FR10 | Prompt caching for performance | Must Have | > 90% cache hit rate |
| FR11 | RBAC for prompt operations | Must Have | Layer-specific permissions |
| FR12 | Audit logging for all changes | Must Have | Compliance support |
| FR13 | SDK programmatic access | Must Have | PromptManager class |
| FR14 | REST API for CRUD operations | Should Have | Dashboard integration |
| FR15 | Prompt preview before activation | Should Have | Composition preview |
| FR16 | Experiment statistical analysis | Should Have | Significance testing |
| FR17 | Variable schema validation | Should Have | JSON Schema support |
| FR18 | Locked merge points (non-overridable) | Should Have | Safety-critical content |

### Non-Functional Requirements

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR1 | Composition latency (cold) | < 10ms p95 | Time for full composition without cache |
| NFR2 | Composition latency (cached) | < 1ms p95 | Time with cache hit |
| NFR3 | Cache hit rate (steady state) | > 90% | Hits / (Hits + Misses) |
| NFR4 | Version rollback time | < 30 seconds | Time to effect change |
| NFR5 | Type annotation coverage | 100% | mypy strict mode |
| NFR6 | Test coverage | >= 80% | pytest-cov |
| NFR7 | Python version | >= 3.9 | Per project requirements |
| NFR8 | Line length | 100 chars | Black/Ruff configuration |

### Integration Requirements

| ID | Requirement | Approach |
|----|-------------|----------|
| IR1 | Integrate with existing RBAC (`security/rbac.py`) | Extend Permission enum with prompt permissions |
| IR2 | Integrate with tenant context (`security/tenant.py`) | Use TenantContext for isolation |
| IR3 | Follow repository pattern (`storage/base.py`) | Create PromptRepository Protocol |
| IR4 | Consistent error handling (`agents/errors.py`) | Create PromptError hierarchy |
| IR5 | Agent integration (`agents/base.py`) | Add prompt_config to BaseAgent |
| IR6 | API integration (`api/routes/`) | New prompts.py route module |

---

## Constraints and Assumptions

### Constraints

1. **Python 3.9+ Compatibility**: All code must work with Python 3.9 features only (no `|` union syntax in runtime contexts, use `Union[]` from typing or `Optional[]`)
2. **Existing Infrastructure**: Must integrate with current FastAPI app structure and existing modules
3. **Line Length**: 100 characters (Black/Ruff configuration)
4. **Type Safety**: mypy strict mode with `disallow_untyped_defs = true`
5. **Database-Only Storage**: No file-based prompt storage; all prompts in database
6. **Jinja2 Templating**: Must use Jinja2 (not custom templating)
7. **Existing Dependencies**: Prefer existing dependencies (pydantic, fastapi) over new ones

### Assumptions

1. **Database**: PostgreSQL will be the production database; SQLite for local development
2. **Redis**: Redis available for distributed caching in production (optional for local)
3. **No Existing Prompts**: Starting fresh; no migration from file-based prompts needed
4. **Tenant Context Available**: Tenant ID accessible via existing `TenantContext` mechanism
5. **Auth Context Available**: User role/permissions accessible from request context
6. **A2A Integration**: Prompts will be consumed by agents via internal API, not exposed to A2A protocol directly

---

## System Architecture

### High-Level Architecture

```
+------------------------------------------------------------------------+
|                         OmniForge Platform                              |
+------------------------------------------------------------------------+
|                                                                         |
|  +------------------+    +-------------------+    +------------------+   |
|  |   API Layer      |    |  SDK Interface    |    |   Security       |   |
|  |  (FastAPI)       |    |  (PromptManager)  |    |  (RBAC/Tenant)   |   |
|  +--------+---------+    +--------+----------+    +--------+---------+   |
|           |                       |                        |             |
|           +-----------------------+------------------------+             |
|                                   |                                      |
|                                   v                                      |
|  +---------------------------------------------------------------+      |
|  |                   Prompt Management Module                     |      |
|  |                                                                |      |
|  |  +----------------+  +------------------+  +----------------+  |      |
|  |  | Composition    |  | Version Manager  |  | Experiment     |  |      |
|  |  | Engine         |  | (Versioning)     |  | Manager (A/B)  |  |      |
|  |  +----------------+  +------------------+  +----------------+  |      |
|  |          |                   |                    |            |      |
|  |          v                   v                    v            |      |
|  |  +----------------+  +------------------+  +----------------+  |      |
|  |  | Template       |  | Validation       |  | Cache          |  |      |
|  |  | Renderer       |  | Framework        |  | Manager        |  |      |
|  |  | (Jinja2)       |  | (Syntax/Content) |  | (LRU/Redis)    |  |      |
|  |  +----------------+  +------------------+  +----------------+  |      |
|  |                                                                |      |
|  +---------------------------------------------------------------+      |
|                                   |                                      |
|                                   v                                      |
|  +---------------------------------------------------------------+      |
|  |                    Storage Layer                               |      |
|  |  +------------------+    +------------------+                  |      |
|  |  | Prompt Repository|    | Cache Repository |                  |      |
|  |  | (PostgreSQL)     |    | (Redis/Memory)   |                  |      |
|  |  +------------------+    +------------------+                  |      |
|  +---------------------------------------------------------------+      |
|                                                                         |
+------------------------------------------------------------------------+
```

### Composition Flow Diagram

```
                           Composition Request
                                   |
                                   v
                      +------------------------+
                      |    Cache Lookup        |
                      |  (cache_key = hash of  |
                      |   versions + vars)     |
                      +------------------------+
                                   |
                    +--------------+--------------+
                    |                             |
               Cache Hit                     Cache Miss
                    |                             |
                    v                             v
              Return Cached              +------------------+
                                         | Load Prompts     |
                                         | (5 layers)       |
                                         +------------------+
                                                  |
                                                  v
                                         +------------------+
                                         | Apply Merge      |
                                         | Points           |
                                         +------------------+
                                                  |
                                                  v
                                         +------------------+
                                         | Check A/B Test   |
                                         | (variant select) |
                                         +------------------+
                                                  |
                                                  v
                                         +------------------+
                                         | Render Jinja2    |
                                         | Template         |
                                         +------------------+
                                                  |
                                                  v
                                         +------------------+
                                         | Validate Output  |
                                         +------------------+
                                                  |
                                                  v
                                         +------------------+
                                         | Store in Cache   |
                                         +------------------+
                                                  |
                                                  v
                                            Return Result
```

### Layer Merge Algorithm

```
Input: system_prompt, tenant_prompt, feature_prompts[], agent_prompt, user_input, variables

1. Start with system_prompt as base template

2. For each merge_point in system_prompt:
   a. Collect content from all layers that define this merge_point:
      - system_content = get_merge_point_content(system_prompt, merge_point)
      - tenant_content = get_merge_point_content(tenant_prompt, merge_point)
      - feature_content = merge([get_merge_point_content(fp, merge_point) for fp in feature_prompts])
      - agent_content = get_merge_point_content(agent_prompt, merge_point)

   b. Check if merge_point is locked:
      - If locked and system_content exists: use system_content only

   c. Apply merge behavior:
      - APPEND: result = system_content + tenant_content + feature_content + agent_content
      - PREPEND: result = agent_content + feature_content + tenant_content + system_content
      - REPLACE: result = first_non_empty([agent_content, feature_content, tenant_content, system_content])
      - INJECT: result = inject at specified position

   d. Replace {{ merge_point("name") }} with result

3. Substitute user_input into {{ merge_point("user_input") }}

4. Return composed template (pre-rendering)
```

---

## Technology Stack

### Core Dependencies (Existing)

| Dependency | Version | Purpose |
|------------|---------|---------|
| fastapi | >=0.100.0 | Web framework, API endpoints |
| pydantic | >=2.0.0 | Data validation, models |
| uvicorn | >=0.23.0 | ASGI server |

### New Dependencies (Required)

| Dependency | Version | Purpose | Justification |
|------------|---------|---------|---------------|
| jinja2 | >=3.1.0 | Template rendering | Industry standard, sandboxing support |
| sqlalchemy | >=2.0.0 | ORM for prompt persistence | Consistent with planned database layer |
| asyncpg | >=0.28.0 | Async PostgreSQL driver | Production database support |
| aiosqlite | >=0.19.0 | Async SQLite driver | Local development |
| redis | >=5.0.0 | Distributed caching (optional) | Production cache layer |
| cachetools | >=5.3.0 | In-memory LRU cache | Local/single-instance caching |
| jsonschema | >=4.20.0 | Variable schema validation | JSON Schema support |

### Development Dependencies (Existing)

All existing dev dependencies remain unchanged (pytest, black, ruff, mypy).

---

## Module Structure

### Directory Layout

```
src/omniforge/
|-- __init__.py
|-- prompts/                           # NEW: Prompt Management Module
|   |-- __init__.py                    # Public exports
|   |-- models.py                      # Pydantic models (Prompt, Version, Experiment)
|   |-- errors.py                      # Exception hierarchy
|   |-- enums.py                       # Enumerations (Layer, MergeBehavior, etc.)
|   |-- composition/                   # Composition engine
|   |   |-- __init__.py
|   |   |-- engine.py                  # Main composition logic
|   |   |-- merge.py                   # Merge point processing
|   |   |-- renderer.py                # Jinja2 template rendering
|   |-- versioning/                    # Version management
|   |   |-- __init__.py
|   |   |-- manager.py                 # Version lifecycle operations
|   |-- validation/                    # Validation framework
|   |   |-- __init__.py
|   |   |-- syntax.py                  # Jinja2 syntax validation
|   |   |-- content.py                 # Content rules validation
|   |   |-- schema.py                  # Variable schema validation
|   |   |-- safety.py                  # Injection detection
|   |-- experiments/                   # A/B testing
|   |   |-- __init__.py
|   |   |-- manager.py                 # Experiment lifecycle
|   |   |-- allocation.py              # Traffic splitting
|   |   |-- analysis.py                # Statistical analysis
|   |-- cache/                         # Caching layer
|   |   |-- __init__.py
|   |   |-- manager.py                 # Cache operations
|   |   |-- keys.py                    # Cache key generation
|   |   |-- backends/                  # Cache backends
|   |   |   |-- __init__.py
|   |   |   |-- memory.py              # In-memory LRU cache
|   |   |   |-- redis.py               # Redis cache
|   |-- storage/                       # Persistence layer
|   |   |-- __init__.py
|   |   |-- repository.py              # Repository Protocol
|   |   |-- memory.py                  # In-memory implementation
|   |   |-- database.py                # SQLAlchemy implementation
|   |   |-- orm_models.py              # SQLAlchemy ORM models
|   |-- sdk/                           # SDK interface
|   |   |-- __init__.py
|   |   |-- manager.py                 # PromptManager class
|   |   |-- config.py                  # PromptConfig for agents
|
|-- api/
|   |-- routes/
|   |   |-- prompts.py                 # NEW: Prompt API endpoints
|
|-- security/
|   |-- rbac.py                        # MODIFY: Add prompt permissions
|
|-- agents/
|   |-- base.py                        # MODIFY: Add prompt_config support
```

### Module Dependencies

```
                                  +----------------+
                                  |    api/        |
                                  | routes/prompts |
                                  +-------+--------+
                                          |
                    +---------------------+---------------------+
                    |                     |                     |
                    v                     v                     v
            +---------------+     +---------------+     +---------------+
            | prompts/sdk/  |     |   security/   |     |   agents/     |
            | manager       |     |   rbac        |     |   base        |
            +-------+-------+     +---------------+     +-------+-------+
                    |                                           |
                    +-------------------+-----------------------+
                                        |
                                        v
                              +-------------------+
                              |  prompts/         |
                              |  composition/     |
                              |  engine           |
                              +--------+----------+
                                       |
         +-----------------------------+-----------------------------+
         |                |                |                         |
         v                v                v                         v
+---------------+ +---------------+ +---------------+       +---------------+
| prompts/      | | prompts/      | | prompts/      |       | prompts/      |
| versioning/   | | validation/   | | experiments/  |       | cache/        |
+---------------+ +---------------+ +---------------+       +---------------+
         |                |                |                         |
         +----------------+----------------+-------------------------+
                                        |
                                        v
                              +-------------------+
                              |  prompts/         |
                              |  storage/         |
                              |  repository       |
                              +-------------------+
```

---

## Component Specifications

### 1. Core Models

**Location**: `src/omniforge/prompts/models.py`

```python
"""Prompt Management data models.

Defines Pydantic models for prompts, versions, merge points, experiments,
and related entities.
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator

from omniforge.prompts.enums import (
    ExperimentStatus,
    MergeBehavior,
    PromptLayer,
)


class MergePointDefinition(BaseModel):
    """Definition of a merge point within a prompt template.

    Attributes:
        name: Unique identifier for the merge point
        behavior: How content from different layers combines
        required: Whether at least one layer must provide content
        locked: Whether lower-layer content cannot be overridden
        description: Human-readable description of the merge point's purpose
    """

    name: str = Field(..., min_length=1, max_length=100)
    behavior: MergeBehavior = MergeBehavior.APPEND
    required: bool = False
    locked: bool = False
    description: str = Field(default="")


class VariableSchema(BaseModel):
    """JSON Schema definition for prompt variables.

    Attributes:
        properties: Variable definitions with types and constraints
        required: List of required variable names
    """

    properties: dict[str, dict[str, Any]] = Field(default_factory=dict)
    required: list[str] = Field(default_factory=list)


class Prompt(BaseModel):
    """A prompt template at a specific layer.

    Prompts are immutable after creation. Updates create new versions.

    Attributes:
        id: Unique identifier
        layer: Which layer this prompt belongs to (SYSTEM, TENANT, etc.)
        scope_id: Context identifier (tenant_id, feature_id, agent_id, or None for system)
        name: Human-readable name for the prompt
        description: Detailed description of the prompt's purpose
        content: Jinja2 template content
        merge_points: List of merge point definitions
        variables_schema: JSON Schema for expected variables
        metadata: Additional key-value metadata
        created_at: Creation timestamp
        created_by: User ID who created the prompt
        is_active: Whether this prompt is active (soft delete support)
        current_version_id: ID of the currently active version
        tenant_id: Owning tenant (for tenant isolation)
    """

    id: UUID = Field(default_factory=uuid4)
    layer: PromptLayer
    scope_id: Optional[str] = Field(None, max_length=255)
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(default="")
    content: str = Field(..., min_length=1, max_length=100000)
    merge_points: list[MergePointDefinition] = Field(default_factory=list)
    variables_schema: VariableSchema = Field(default_factory=VariableSchema)
    metadata: dict[str, str] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(..., min_length=1, max_length=255)
    is_active: bool = True
    current_version_id: Optional[UUID] = None
    tenant_id: Optional[str] = Field(None, max_length=255)

    @field_validator("content")
    @classmethod
    def validate_content_not_empty(cls, value: str) -> str:
        """Validate that content is not just whitespace."""
        if not value.strip():
            raise ValueError("Prompt content cannot be empty or whitespace only")
        return value


class PromptVersion(BaseModel):
    """An immutable version of a prompt.

    Every change to a prompt creates a new version. Versions are immutable
    and can be used for rollback and audit purposes.

    Attributes:
        id: Unique identifier for this version
        prompt_id: Parent prompt ID
        version_number: Sequential version number (1, 2, 3, ...)
        content: Jinja2 template content at this version
        variables_schema: Variable schema at this version
        merge_points: Merge point definitions at this version
        change_message: Commit-style message describing the change
        changed_by: User ID who made the change
        changed_at: When the change was made
        is_current: Whether this is the active version
    """

    id: UUID = Field(default_factory=uuid4)
    prompt_id: UUID
    version_number: int = Field(..., ge=1)
    content: str = Field(..., min_length=1, max_length=100000)
    variables_schema: VariableSchema = Field(default_factory=VariableSchema)
    merge_points: list[MergePointDefinition] = Field(default_factory=list)
    change_message: str = Field(..., min_length=1, max_length=1000)
    changed_by: str = Field(..., min_length=1, max_length=255)
    changed_at: datetime = Field(default_factory=datetime.utcnow)
    is_current: bool = False


class ExperimentVariant(BaseModel):
    """A variant in an A/B experiment.

    Attributes:
        id: Unique variant identifier
        name: Human-readable name (e.g., "Control", "Treatment A")
        prompt_version_id: Which prompt version this variant uses
        traffic_percentage: Percentage of traffic allocated (0-100)
        metrics: Collected metrics for this variant
    """

    id: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=255)
    prompt_version_id: UUID
    traffic_percentage: float = Field(..., ge=0, le=100)
    metrics: dict[str, Any] = Field(default_factory=dict)


class PromptExperiment(BaseModel):
    """An A/B test experiment on a prompt.

    Attributes:
        id: Unique identifier
        prompt_id: The prompt being experimented on
        name: Human-readable experiment name
        description: Experiment hypothesis and goals
        status: Current experiment status
        variants: List of experiment variants
        success_metric: The metric to optimize
        start_date: When the experiment started
        end_date: When the experiment ended (if completed)
        results: Statistical results and analysis
        created_by: User ID who created the experiment
        tenant_id: Owning tenant
    """

    id: UUID = Field(default_factory=uuid4)
    prompt_id: UUID
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(default="")
    status: ExperimentStatus = ExperimentStatus.DRAFT
    variants: list[ExperimentVariant] = Field(default_factory=list)
    success_metric: str = Field(..., min_length=1, max_length=100)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    results: dict[str, Any] = Field(default_factory=dict)
    created_by: str = Field(..., min_length=1, max_length=255)
    tenant_id: Optional[str] = Field(None, max_length=255)

    @field_validator("variants")
    @classmethod
    def validate_traffic_allocation(cls, value: list[ExperimentVariant]) -> list[ExperimentVariant]:
        """Validate that traffic percentages sum to 100."""
        if value:
            total = sum(v.traffic_percentage for v in value)
            if abs(total - 100.0) > 0.01:
                raise ValueError(f"Traffic allocation must sum to 100%, got {total}%")
        return value


class ComposedPrompt(BaseModel):
    """Result of prompt composition.

    Attributes:
        content: The fully composed and rendered prompt text
        layer_versions: Map of layer -> version ID used
        variables_used: Variables that were substituted
        experiment_variant: If A/B test active, which variant was selected
        cache_key: Key used for caching this composition
        composition_time_ms: Time taken to compose (milliseconds)
    """

    content: str
    layer_versions: dict[str, UUID] = Field(default_factory=dict)
    variables_used: dict[str, Any] = Field(default_factory=dict)
    experiment_variant: Optional[str] = None
    cache_key: Optional[str] = None
    composition_time_ms: float = 0.0
```

### 2. Enumerations

**Location**: `src/omniforge/prompts/enums.py`

```python
"""Enumerations for Prompt Management Module."""

from enum import Enum


class PromptLayer(str, Enum):
    """Layers in the prompt hierarchy.

    Listed in order of precedence (lower layers provide base,
    higher layers can override at merge points).
    """

    SYSTEM = "system"      # Platform-level defaults
    TENANT = "tenant"      # Organization customizations
    FEATURE = "feature"    # Feature/capability specific
    AGENT = "agent"        # Agent instance specific
    USER = "user"          # Runtime user input


class MergeBehavior(str, Enum):
    """How content from different layers combines at merge points."""

    APPEND = "append"      # Higher layer content added after lower layer
    PREPEND = "prepend"    # Higher layer content added before lower layer
    REPLACE = "replace"    # Higher layer content replaces lower layer
    INJECT = "inject"      # Content inserted at specific position


class ExperimentStatus(str, Enum):
    """Status of an A/B experiment."""

    DRAFT = "draft"            # Created but not started
    RUNNING = "running"        # Actively collecting data
    PAUSED = "paused"          # Temporarily stopped
    COMPLETED = "completed"    # Finished, results available
    CANCELLED = "cancelled"    # Stopped without results


class ValidationSeverity(str, Enum):
    """Severity levels for validation results."""

    ERROR = "error"        # Blocks activation
    WARNING = "warning"    # Allows activation with notice
    INFO = "info"          # Informational only
```

### 3. Exception Hierarchy

**Location**: `src/omniforge/prompts/errors.py`

```python
"""Prompt Management exception hierarchy.

Follows the pattern established in agents/errors.py for consistency.
"""

from typing import Optional


class PromptError(Exception):
    """Base exception for all prompt-related errors.

    Attributes:
        message: Human-readable error description
        code: Machine-readable error code
        status_code: HTTP status code for API responses
    """

    def __init__(self, message: str, code: str, status_code: int) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class PromptNotFoundError(PromptError):
    """Raised when a prompt cannot be found."""

    def __init__(self, prompt_id: str) -> None:
        super().__init__(
            message=f"Prompt '{prompt_id}' not found",
            code="prompt_not_found",
            status_code=404,
        )
        self.prompt_id = prompt_id


class PromptVersionNotFoundError(PromptError):
    """Raised when a prompt version cannot be found."""

    def __init__(self, prompt_id: str, version: int) -> None:
        super().__init__(
            message=f"Version {version} of prompt '{prompt_id}' not found",
            code="prompt_version_not_found",
            status_code=404,
        )
        self.prompt_id = prompt_id
        self.version = version


class PromptValidationError(PromptError):
    """Raised when prompt validation fails."""

    def __init__(self, message: str, errors: Optional[list[dict]] = None) -> None:
        super().__init__(
            message=message,
            code="prompt_validation_error",
            status_code=400,
        )
        self.errors = errors or []


class PromptCompositionError(PromptError):
    """Raised when prompt composition fails."""

    def __init__(self, message: str, layer: Optional[str] = None) -> None:
        super().__init__(
            message=message,
            code="prompt_composition_error",
            status_code=500,
        )
        self.layer = layer


class PromptRenderError(PromptError):
    """Raised when Jinja2 template rendering fails."""

    def __init__(self, message: str, template_error: Optional[str] = None) -> None:
        super().__init__(
            message=f"Template rendering failed: {message}",
            code="prompt_render_error",
            status_code=500,
        )
        self.template_error = template_error


class ExperimentNotFoundError(PromptError):
    """Raised when an experiment cannot be found."""

    def __init__(self, experiment_id: str) -> None:
        super().__init__(
            message=f"Experiment '{experiment_id}' not found",
            code="experiment_not_found",
            status_code=404,
        )
        self.experiment_id = experiment_id


class ExperimentStateError(PromptError):
    """Raised when an experiment operation is invalid for current state."""

    def __init__(self, experiment_id: str, current_status: str, operation: str) -> None:
        super().__init__(
            message=f"Cannot perform '{operation}' on experiment '{experiment_id}' "
            f"in status '{current_status}'",
            code="experiment_state_error",
            status_code=409,
        )
        self.experiment_id = experiment_id
        self.current_status = current_status
        self.operation = operation


class MergePointConflictError(PromptError):
    """Raised when merge point configuration is invalid."""

    def __init__(self, merge_point: str, message: str) -> None:
        super().__init__(
            message=f"Merge point '{merge_point}' conflict: {message}",
            code="merge_point_conflict",
            status_code=400,
        )
        self.merge_point = merge_point


class PromptLockViolationError(PromptError):
    """Raised when attempting to override a locked merge point."""

    def __init__(self, merge_point: str, layer: str) -> None:
        super().__init__(
            message=f"Cannot override locked merge point '{merge_point}' from layer '{layer}'",
            code="prompt_lock_violation",
            status_code=403,
        )
        self.merge_point = merge_point
        self.layer = layer


class PromptConcurrencyError(PromptError):
    """Raised when concurrent edit conflict detected."""

    def __init__(self, prompt_id: str, expected_version: int, actual_version: int) -> None:
        super().__init__(
            message=f"Prompt '{prompt_id}' was modified. "
            f"Expected version {expected_version}, found {actual_version}",
            code="prompt_concurrency_error",
            status_code=409,
        )
        self.prompt_id = prompt_id
        self.expected_version = expected_version
        self.actual_version = actual_version
```

### 4. Composition Engine

**Location**: `src/omniforge/prompts/composition/engine.py`

```python
"""Prompt composition engine.

The core logic for composing prompts from multiple layers into a single
rendered template.
"""

import hashlib
import time
from typing import Any, Optional

from omniforge.prompts.cache.manager import CacheManager
from omniforge.prompts.composition.merge import MergeProcessor
from omniforge.prompts.composition.renderer import TemplateRenderer
from omniforge.prompts.enums import PromptLayer
from omniforge.prompts.errors import PromptCompositionError
from omniforge.prompts.experiments.manager import ExperimentManager
from omniforge.prompts.models import ComposedPrompt, Prompt, PromptVersion
from omniforge.prompts.storage.repository import PromptRepository
from omniforge.prompts.validation.safety import SafetyValidator
from omniforge.security.tenant import get_tenant_id


class CompositionEngine:
    """Orchestrates the prompt composition process.

    This class coordinates loading prompts from multiple layers, applying
    merge logic, selecting experiment variants, rendering templates, and
    caching results.

    Attributes:
        repository: Storage backend for prompts
        cache: Cache manager for composed prompts
        renderer: Jinja2 template renderer
        merge_processor: Merge point processor
        experiment_manager: A/B test manager
        safety_validator: Input sanitization
    """

    def __init__(
        self,
        repository: PromptRepository,
        cache: Optional[CacheManager] = None,
        experiment_manager: Optional[ExperimentManager] = None,
    ) -> None:
        """Initialize the composition engine.

        Args:
            repository: Prompt storage backend
            cache: Optional cache manager (in-memory default if None)
            experiment_manager: Optional A/B test manager
        """
        self.repository = repository
        self.cache = cache or CacheManager()
        self.renderer = TemplateRenderer()
        self.merge_processor = MergeProcessor()
        self.experiment_manager = experiment_manager
        self.safety_validator = SafetyValidator()

    async def compose(
        self,
        agent_id: str,
        tenant_id: Optional[str] = None,
        feature_ids: Optional[list[str]] = None,
        user_input: Optional[str] = None,
        variables: Optional[dict[str, Any]] = None,
        skip_cache: bool = False,
    ) -> ComposedPrompt:
        """Compose a prompt from all applicable layers.

        Args:
            agent_id: Agent identifier for agent-layer prompt lookup
            tenant_id: Tenant identifier (defaults to current context)
            feature_ids: Feature identifiers for feature-layer prompts
            user_input: User's input text (safely escaped)
            variables: Variables to substitute in template
            skip_cache: If True, bypass cache and recompose

        Returns:
            ComposedPrompt with rendered content and metadata

        Raises:
            PromptCompositionError: If composition fails
            PromptRenderError: If template rendering fails
        """
        start_time = time.perf_counter()

        # Resolve tenant from context if not provided
        tenant_id = tenant_id or get_tenant_id()
        feature_ids = feature_ids or []
        variables = variables or {}

        # Sanitize user input
        safe_user_input = ""
        if user_input:
            safe_user_input = self.safety_validator.sanitize_user_input(user_input)

        # Generate cache key
        cache_key = await self._generate_cache_key(
            agent_id=agent_id,
            tenant_id=tenant_id,
            feature_ids=feature_ids,
            variables=variables,
        )

        # Check cache
        if not skip_cache:
            cached = await self.cache.get(cache_key)
            if cached is not None:
                return cached

        # Load prompts from each layer
        layer_prompts = await self._load_layer_prompts(
            agent_id=agent_id,
            tenant_id=tenant_id,
            feature_ids=feature_ids,
        )

        # Apply merge logic
        merged_template = await self.merge_processor.merge(
            layer_prompts=layer_prompts,
            user_input=safe_user_input,
        )

        # Check for active experiment and select variant
        experiment_variant = None
        if self.experiment_manager:
            variant_info = await self.experiment_manager.select_variant(
                prompts=layer_prompts,
                tenant_id=tenant_id,
            )
            if variant_info:
                experiment_variant = variant_info.variant_id
                # Use variant's prompt version if applicable
                merged_template = variant_info.template or merged_template

        # Build complete variables context
        full_variables = self._build_variable_context(
            tenant_id=tenant_id,
            agent_id=agent_id,
            user_variables=variables,
        )

        # Render template
        rendered_content = await self.renderer.render(
            template=merged_template,
            variables=full_variables,
        )

        # Collect version metadata
        layer_versions = {
            layer.value: prompt.current_version_id
            for layer, prompt in layer_prompts.items()
            if prompt and prompt.current_version_id
        }

        # Build result
        composition_time = (time.perf_counter() - start_time) * 1000

        result = ComposedPrompt(
            content=rendered_content,
            layer_versions=layer_versions,
            variables_used=full_variables,
            experiment_variant=experiment_variant,
            cache_key=cache_key,
            composition_time_ms=composition_time,
        )

        # Store in cache
        if not skip_cache:
            await self.cache.set(cache_key, result)

        return result

    async def _load_layer_prompts(
        self,
        agent_id: str,
        tenant_id: Optional[str],
        feature_ids: list[str],
    ) -> dict[PromptLayer, Optional[Prompt]]:
        """Load prompts from all applicable layers.

        Args:
            agent_id: Agent identifier
            tenant_id: Tenant identifier
            feature_ids: Feature identifiers

        Returns:
            Dictionary mapping layers to their prompts (None if not found)
        """
        result: dict[PromptLayer, Optional[Prompt]] = {}

        # System layer (always present)
        result[PromptLayer.SYSTEM] = await self.repository.get_by_layer(
            layer=PromptLayer.SYSTEM,
            scope_id=None,
        )

        # Tenant layer
        if tenant_id:
            result[PromptLayer.TENANT] = await self.repository.get_by_layer(
                layer=PromptLayer.TENANT,
                scope_id=tenant_id,
            )
        else:
            result[PromptLayer.TENANT] = None

        # Feature layer (merge multiple features)
        feature_prompts = []
        for feature_id in feature_ids:
            prompt = await self.repository.get_by_layer(
                layer=PromptLayer.FEATURE,
                scope_id=feature_id,
            )
            if prompt:
                feature_prompts.append(prompt)
        result[PromptLayer.FEATURE] = self._merge_feature_prompts(feature_prompts)

        # Agent layer
        result[PromptLayer.AGENT] = await self.repository.get_by_layer(
            layer=PromptLayer.AGENT,
            scope_id=agent_id,
        )

        return result

    def _merge_feature_prompts(self, prompts: list[Prompt]) -> Optional[Prompt]:
        """Merge multiple feature prompts into one.

        When an agent uses multiple features, their prompts are combined
        in order of feature_id priority.

        Args:
            prompts: List of feature prompts to merge

        Returns:
            Merged prompt or None if no prompts
        """
        if not prompts:
            return None
        if len(prompts) == 1:
            return prompts[0]

        # Combine content with separator
        combined_content = "\n\n".join(p.content for p in prompts)

        # Merge merge_points definitions
        combined_merge_points = []
        seen_names = set()
        for prompt in prompts:
            for mp in prompt.merge_points:
                if mp.name not in seen_names:
                    combined_merge_points.append(mp)
                    seen_names.add(mp.name)

        return Prompt(
            layer=PromptLayer.FEATURE,
            scope_id="combined",
            name="Combined Features",
            content=combined_content,
            merge_points=combined_merge_points,
            created_by="system",
        )

    def _build_variable_context(
        self,
        tenant_id: Optional[str],
        agent_id: str,
        user_variables: dict[str, Any],
    ) -> dict[str, Any]:
        """Build the complete variable context for template rendering.

        Variables are namespaced to prevent collisions:
        - system.*: Platform-level variables
        - tenant.*: Tenant-specific variables
        - agent.*: Agent-specific variables
        - user.*: User-provided variables

        Args:
            tenant_id: Current tenant identifier
            agent_id: Current agent identifier
            user_variables: User-provided variables

        Returns:
            Complete variable dictionary
        """
        return {
            "system": {
                "platform_name": "OmniForge",
                "platform_version": "0.1.0",
            },
            "tenant": {
                "id": tenant_id,
            },
            "agent": {
                "id": agent_id,
            },
            **user_variables,
        }

    async def _generate_cache_key(
        self,
        agent_id: str,
        tenant_id: Optional[str],
        feature_ids: list[str],
        variables: dict[str, Any],
    ) -> str:
        """Generate a unique cache key for a composition request.

        The key incorporates version IDs of all relevant prompts plus
        a hash of the variables (excluding user input which is too variable).

        Args:
            agent_id: Agent identifier
            tenant_id: Tenant identifier
            feature_ids: Feature identifiers
            variables: Template variables

        Returns:
            SHA256 hash string as cache key
        """
        # Get current version IDs for all layers
        version_parts = []

        system_prompt = await self.repository.get_by_layer(PromptLayer.SYSTEM, None)
        if system_prompt and system_prompt.current_version_id:
            version_parts.append(f"sys:{system_prompt.current_version_id}")

        if tenant_id:
            tenant_prompt = await self.repository.get_by_layer(PromptLayer.TENANT, tenant_id)
            if tenant_prompt and tenant_prompt.current_version_id:
                version_parts.append(f"tenant:{tenant_prompt.current_version_id}")

        for feature_id in sorted(feature_ids):
            feature_prompt = await self.repository.get_by_layer(PromptLayer.FEATURE, feature_id)
            if feature_prompt and feature_prompt.current_version_id:
                version_parts.append(f"feat:{feature_prompt.current_version_id}")

        agent_prompt = await self.repository.get_by_layer(PromptLayer.AGENT, agent_id)
        if agent_prompt and agent_prompt.current_version_id:
            version_parts.append(f"agent:{agent_prompt.current_version_id}")

        # Hash variables (excluding highly variable ones)
        stable_vars = {k: v for k, v in variables.items() if k not in {"user_input"}}
        var_hash = hashlib.sha256(str(sorted(stable_vars.items())).encode()).hexdigest()[:16]

        # Combine into key
        key_parts = version_parts + [f"vars:{var_hash}"]
        combined = ":".join(key_parts)

        return hashlib.sha256(combined.encode()).hexdigest()
```

### 5. Jinja2 Template Renderer

**Location**: `src/omniforge/prompts/composition/renderer.py`

```python
"""Jinja2 template renderer with sandboxing.

Provides secure template rendering with injection protection.
"""

from typing import Any

from jinja2 import Environment, BaseLoader, TemplateSyntaxError, UndefinedError
from jinja2.sandbox import SandboxedEnvironment

from omniforge.prompts.errors import PromptRenderError


class PromptTemplateLoader(BaseLoader):
    """Minimal loader for string-based templates.

    Templates are loaded from strings, not files, for security.
    """

    def get_source(
        self,
        environment: Environment,
        template: str,
    ) -> tuple[str, None, callable]:
        """Return template source from string.

        Args:
            environment: Jinja2 environment
            template: Template string

        Returns:
            Tuple of (source, filename, uptodate_func)
        """
        return template, None, lambda: True


class TemplateRenderer:
    """Secure Jinja2 template renderer.

    Uses sandboxed environment to prevent code execution and
    includes custom filters for prompt-specific operations.
    """

    def __init__(self) -> None:
        """Initialize the template renderer with sandboxed environment."""
        self.env = SandboxedEnvironment(
            loader=PromptTemplateLoader(),
            autoescape=False,  # We handle escaping separately
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Register custom filters
        self._register_filters()

    def _register_filters(self) -> None:
        """Register prompt-specific Jinja2 filters."""
        self.env.filters["default"] = lambda v, d="": v if v else d
        self.env.filters["truncate"] = self._truncate_filter
        self.env.filters["capitalize_first"] = lambda s: s[0].upper() + s[1:] if s else s
        self.env.filters["bullet_list"] = self._bullet_list_filter

    def _truncate_filter(self, value: str, length: int = 255, suffix: str = "...") -> str:
        """Truncate string to specified length.

        Args:
            value: String to truncate
            length: Maximum length
            suffix: Suffix to add if truncated

        Returns:
            Truncated string
        """
        if len(value) <= length:
            return value
        return value[: length - len(suffix)] + suffix

    def _bullet_list_filter(self, items: list[str], bullet: str = "-") -> str:
        """Format list as bullet points.

        Args:
            items: List of strings
            bullet: Bullet character

        Returns:
            Formatted bullet list
        """
        return "\n".join(f"{bullet} {item}" for item in items)

    async def render(
        self,
        template: str,
        variables: dict[str, Any],
    ) -> str:
        """Render a Jinja2 template with variables.

        Args:
            template: Jinja2 template string
            variables: Variables to substitute

        Returns:
            Rendered string

        Raises:
            PromptRenderError: If rendering fails
        """
        try:
            compiled = self.env.from_string(template)
            return compiled.render(**variables)
        except TemplateSyntaxError as e:
            raise PromptRenderError(
                message=f"Template syntax error at line {e.lineno}: {e.message}",
                template_error=str(e),
            )
        except UndefinedError as e:
            raise PromptRenderError(
                message=f"Undefined variable: {e.message}",
                template_error=str(e),
            )
        except Exception as e:
            raise PromptRenderError(
                message=f"Unexpected rendering error: {str(e)}",
                template_error=str(e),
            )

    def validate_syntax(self, template: str) -> list[str]:
        """Validate template syntax without rendering.

        Args:
            template: Jinja2 template string

        Returns:
            List of syntax errors (empty if valid)
        """
        errors = []
        try:
            self.env.parse(template)
        except TemplateSyntaxError as e:
            errors.append(f"Line {e.lineno}: {e.message}")
        return errors
```

### 6. Repository Interface

**Location**: `src/omniforge/prompts/storage/repository.py`

```python
"""Repository protocol for prompt storage.

Defines the interface that all storage backends must implement,
following the existing pattern from storage/base.py.
"""

from typing import Optional, Protocol

from omniforge.prompts.enums import PromptLayer
from omniforge.prompts.models import (
    Prompt,
    PromptExperiment,
    PromptVersion,
)


class PromptRepository(Protocol):
    """Protocol for prompt storage operations.

    This protocol defines the interface that all prompt repository
    implementations must follow, enabling storage backend swapping.
    """

    # ========== Prompt CRUD ==========

    async def create(self, prompt: Prompt) -> Prompt:
        """Create a new prompt.

        Args:
            prompt: Prompt to create

        Returns:
            Created prompt with ID populated

        Raises:
            ValueError: If prompt with same layer/scope_id already exists
        """
        ...

    async def get(self, prompt_id: str) -> Optional[Prompt]:
        """Get a prompt by ID.

        Args:
            prompt_id: Unique prompt identifier

        Returns:
            Prompt if found, None otherwise
        """
        ...

    async def get_by_layer(
        self,
        layer: PromptLayer,
        scope_id: Optional[str],
    ) -> Optional[Prompt]:
        """Get a prompt by layer and scope.

        Args:
            layer: Prompt layer
            scope_id: Scope identifier (tenant_id, feature_id, etc.)

        Returns:
            Prompt if found, None otherwise
        """
        ...

    async def update(self, prompt: Prompt) -> Prompt:
        """Update an existing prompt.

        Note: This creates a new version; prompts are immutable.

        Args:
            prompt: Prompt with updated fields

        Returns:
            Updated prompt

        Raises:
            ValueError: If prompt does not exist
        """
        ...

    async def delete(self, prompt_id: str) -> None:
        """Soft-delete a prompt.

        Args:
            prompt_id: Prompt ID to delete

        Raises:
            ValueError: If prompt does not exist
        """
        ...

    async def list_by_tenant(
        self,
        tenant_id: str,
        layer: Optional[PromptLayer] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Prompt]:
        """List prompts for a tenant.

        Args:
            tenant_id: Tenant identifier
            layer: Optional layer filter
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of prompts
        """
        ...

    # ========== Version Operations ==========

    async def create_version(self, version: PromptVersion) -> PromptVersion:
        """Create a new prompt version.

        Args:
            version: Version to create

        Returns:
            Created version
        """
        ...

    async def get_version(
        self,
        prompt_id: str,
        version_number: int,
    ) -> Optional[PromptVersion]:
        """Get a specific version of a prompt.

        Args:
            prompt_id: Parent prompt ID
            version_number: Version number to retrieve

        Returns:
            PromptVersion if found, None otherwise
        """
        ...

    async def list_versions(
        self,
        prompt_id: str,
        limit: int = 50,
    ) -> list[PromptVersion]:
        """List versions for a prompt.

        Args:
            prompt_id: Parent prompt ID
            limit: Maximum versions to return

        Returns:
            List of versions, newest first
        """
        ...

    async def set_current_version(
        self,
        prompt_id: str,
        version_id: str,
    ) -> None:
        """Set the current active version for a prompt.

        Args:
            prompt_id: Prompt ID
            version_id: Version ID to make current

        Raises:
            ValueError: If prompt or version not found
        """
        ...

    # ========== Experiment Operations ==========

    async def create_experiment(
        self,
        experiment: PromptExperiment,
    ) -> PromptExperiment:
        """Create a new A/B experiment.

        Args:
            experiment: Experiment to create

        Returns:
            Created experiment
        """
        ...

    async def get_experiment(
        self,
        experiment_id: str,
    ) -> Optional[PromptExperiment]:
        """Get an experiment by ID.

        Args:
            experiment_id: Experiment identifier

        Returns:
            PromptExperiment if found, None otherwise
        """
        ...

    async def get_active_experiment(
        self,
        prompt_id: str,
    ) -> Optional[PromptExperiment]:
        """Get the active experiment for a prompt.

        Args:
            prompt_id: Prompt being experimented on

        Returns:
            Active experiment if one exists, None otherwise
        """
        ...

    async def update_experiment(
        self,
        experiment: PromptExperiment,
    ) -> PromptExperiment:
        """Update an experiment.

        Args:
            experiment: Experiment with updated fields

        Returns:
            Updated experiment
        """
        ...

    async def list_experiments(
        self,
        prompt_id: str,
        limit: int = 50,
    ) -> list[PromptExperiment]:
        """List experiments for a prompt.

        Args:
            prompt_id: Prompt ID
            limit: Maximum results

        Returns:
            List of experiments
        """
        ...
```

### 7. In-Memory Repository

**Location**: `src/omniforge/prompts/storage/memory.py`

```python
"""In-memory implementation of PromptRepository.

Thread-safe dictionary-based storage for development and testing.
"""

import asyncio
from typing import Optional
from uuid import UUID

from omniforge.prompts.enums import ExperimentStatus, PromptLayer
from omniforge.prompts.models import (
    Prompt,
    PromptExperiment,
    PromptVersion,
)


class InMemoryPromptRepository:
    """Thread-safe in-memory prompt repository.

    Uses dictionaries with asyncio locks for concurrent access.
    """

    def __init__(self) -> None:
        """Initialize in-memory storage."""
        self._prompts: dict[UUID, Prompt] = {}
        self._versions: dict[UUID, PromptVersion] = {}
        self._experiments: dict[UUID, PromptExperiment] = {}
        self._lock = asyncio.Lock()

    # ========== Prompt CRUD ==========

    async def create(self, prompt: Prompt) -> Prompt:
        """Create a new prompt."""
        async with self._lock:
            # Check for duplicate layer/scope
            for existing in self._prompts.values():
                if (
                    existing.layer == prompt.layer
                    and existing.scope_id == prompt.scope_id
                    and existing.is_active
                ):
                    raise ValueError(
                        f"Prompt for layer '{prompt.layer}' and scope '{prompt.scope_id}' "
                        "already exists"
                    )

            self._prompts[prompt.id] = prompt
            return prompt

    async def get(self, prompt_id: str) -> Optional[Prompt]:
        """Get a prompt by ID."""
        async with self._lock:
            uid = UUID(prompt_id)
            prompt = self._prompts.get(uid)
            return prompt if prompt and prompt.is_active else None

    async def get_by_layer(
        self,
        layer: PromptLayer,
        scope_id: Optional[str],
    ) -> Optional[Prompt]:
        """Get a prompt by layer and scope."""
        async with self._lock:
            for prompt in self._prompts.values():
                if (
                    prompt.layer == layer
                    and prompt.scope_id == scope_id
                    and prompt.is_active
                ):
                    return prompt
            return None

    async def update(self, prompt: Prompt) -> Prompt:
        """Update an existing prompt."""
        async with self._lock:
            if prompt.id not in self._prompts:
                raise ValueError(f"Prompt '{prompt.id}' not found")
            self._prompts[prompt.id] = prompt
            return prompt

    async def delete(self, prompt_id: str) -> None:
        """Soft-delete a prompt."""
        async with self._lock:
            uid = UUID(prompt_id)
            if uid not in self._prompts:
                raise ValueError(f"Prompt '{prompt_id}' not found")
            self._prompts[uid].is_active = False

    async def list_by_tenant(
        self,
        tenant_id: str,
        layer: Optional[PromptLayer] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Prompt]:
        """List prompts for a tenant."""
        async with self._lock:
            results = [
                p for p in self._prompts.values()
                if p.tenant_id == tenant_id
                and p.is_active
                and (layer is None or p.layer == layer)
            ]
            results.sort(key=lambda p: p.created_at, reverse=True)
            return results[offset : offset + limit]

    # ========== Version Operations ==========

    async def create_version(self, version: PromptVersion) -> PromptVersion:
        """Create a new prompt version."""
        async with self._lock:
            self._versions[version.id] = version
            return version

    async def get_version(
        self,
        prompt_id: str,
        version_number: int,
    ) -> Optional[PromptVersion]:
        """Get a specific version."""
        async with self._lock:
            uid = UUID(prompt_id)
            for version in self._versions.values():
                if version.prompt_id == uid and version.version_number == version_number:
                    return version
            return None

    async def list_versions(
        self,
        prompt_id: str,
        limit: int = 50,
    ) -> list[PromptVersion]:
        """List versions for a prompt."""
        async with self._lock:
            uid = UUID(prompt_id)
            versions = [v for v in self._versions.values() if v.prompt_id == uid]
            versions.sort(key=lambda v: v.version_number, reverse=True)
            return versions[:limit]

    async def set_current_version(
        self,
        prompt_id: str,
        version_id: str,
    ) -> None:
        """Set the current active version."""
        async with self._lock:
            p_uid = UUID(prompt_id)
            v_uid = UUID(version_id)

            if p_uid not in self._prompts:
                raise ValueError(f"Prompt '{prompt_id}' not found")
            if v_uid not in self._versions:
                raise ValueError(f"Version '{version_id}' not found")

            # Clear current flag on all versions
            for version in self._versions.values():
                if version.prompt_id == p_uid:
                    version.is_current = False

            # Set new current
            self._versions[v_uid].is_current = True
            self._prompts[p_uid].current_version_id = v_uid

    # ========== Experiment Operations ==========

    async def create_experiment(
        self,
        experiment: PromptExperiment,
    ) -> PromptExperiment:
        """Create a new experiment."""
        async with self._lock:
            self._experiments[experiment.id] = experiment
            return experiment

    async def get_experiment(
        self,
        experiment_id: str,
    ) -> Optional[PromptExperiment]:
        """Get an experiment by ID."""
        async with self._lock:
            uid = UUID(experiment_id)
            return self._experiments.get(uid)

    async def get_active_experiment(
        self,
        prompt_id: str,
    ) -> Optional[PromptExperiment]:
        """Get the active experiment for a prompt."""
        async with self._lock:
            p_uid = UUID(prompt_id)
            for exp in self._experiments.values():
                if exp.prompt_id == p_uid and exp.status == ExperimentStatus.RUNNING:
                    return exp
            return None

    async def update_experiment(
        self,
        experiment: PromptExperiment,
    ) -> PromptExperiment:
        """Update an experiment."""
        async with self._lock:
            if experiment.id not in self._experiments:
                raise ValueError(f"Experiment '{experiment.id}' not found")
            self._experiments[experiment.id] = experiment
            return experiment

    async def list_experiments(
        self,
        prompt_id: str,
        limit: int = 50,
    ) -> list[PromptExperiment]:
        """List experiments for a prompt."""
        async with self._lock:
            p_uid = UUID(prompt_id)
            experiments = [e for e in self._experiments.values() if e.prompt_id == p_uid]
            experiments.sort(key=lambda e: e.start_date or e.id, reverse=True)
            return experiments[:limit]
```

### 8. Cache Manager

**Location**: `src/omniforge/prompts/cache/manager.py`

```python
"""Cache manager for composed prompts.

Implements two-tier caching with in-memory LRU and optional Redis.
"""

import hashlib
import json
from typing import Any, Optional

from cachetools import LRUCache

from omniforge.prompts.models import ComposedPrompt


class CacheManager:
    """Two-tier cache for composed prompts.

    First tier: In-memory LRU cache for hot prompts
    Second tier: Redis for distributed deployments (optional)

    Attributes:
        memory_cache: In-memory LRU cache
        redis_client: Optional Redis client for distributed caching
        default_ttl: Default time-to-live in seconds
    """

    def __init__(
        self,
        max_memory_items: int = 1000,
        redis_client: Optional[Any] = None,
        default_ttl: int = 3600,
    ) -> None:
        """Initialize cache manager.

        Args:
            max_memory_items: Maximum items in memory cache
            redis_client: Optional Redis client
            default_ttl: Default TTL in seconds (1 hour)
        """
        self.memory_cache: LRUCache = LRUCache(maxsize=max_memory_items)
        self.redis_client = redis_client
        self.default_ttl = default_ttl

    async def get(self, key: str) -> Optional[ComposedPrompt]:
        """Get a cached composition.

        Checks memory first, then Redis if available.

        Args:
            key: Cache key

        Returns:
            ComposedPrompt if found, None otherwise
        """
        # Check memory first
        if key in self.memory_cache:
            return self.memory_cache[key]

        # Check Redis if available
        if self.redis_client:
            try:
                data = await self.redis_client.get(f"prompt:{key}")
                if data:
                    prompt = ComposedPrompt.model_validate_json(data)
                    # Populate memory cache
                    self.memory_cache[key] = prompt
                    return prompt
            except Exception:
                # Redis errors should not break composition
                pass

        return None

    async def set(
        self,
        key: str,
        value: ComposedPrompt,
        ttl: Optional[int] = None,
    ) -> None:
        """Store a composed prompt in cache.

        Stores in both memory and Redis (if available).

        Args:
            key: Cache key
            value: Composed prompt to cache
            ttl: Time-to-live in seconds (default: default_ttl)
        """
        ttl = ttl or self.default_ttl

        # Store in memory
        self.memory_cache[key] = value

        # Store in Redis if available
        if self.redis_client:
            try:
                await self.redis_client.setex(
                    f"prompt:{key}",
                    ttl,
                    value.model_dump_json(),
                )
            except Exception:
                # Redis errors should not break composition
                pass

    async def invalidate(self, key: str) -> None:
        """Remove a specific key from cache.

        Args:
            key: Cache key to invalidate
        """
        # Remove from memory
        self.memory_cache.pop(key, None)

        # Remove from Redis
        if self.redis_client:
            try:
                await self.redis_client.delete(f"prompt:{key}")
            except Exception:
                pass

    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching a pattern.

        Useful for invalidating all caches when a prompt version changes.

        Args:
            pattern: Glob pattern to match (e.g., "sys:*")

        Returns:
            Number of keys invalidated
        """
        count = 0

        # Clear memory cache entries matching pattern
        keys_to_remove = [k for k in self.memory_cache.keys() if pattern in k]
        for key in keys_to_remove:
            self.memory_cache.pop(key, None)
            count += 1

        # Clear Redis if available
        if self.redis_client:
            try:
                async for key in self.redis_client.scan_iter(f"prompt:*{pattern}*"):
                    await self.redis_client.delete(key)
                    count += 1
            except Exception:
                pass

        return count

    async def clear(self) -> None:
        """Clear all cached entries."""
        self.memory_cache.clear()

        if self.redis_client:
            try:
                async for key in self.redis_client.scan_iter("prompt:*"):
                    await self.redis_client.delete(key)
            except Exception:
                pass

    def stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        return {
            "memory_size": len(self.memory_cache),
            "memory_max_size": self.memory_cache.maxsize,
            "memory_hits": getattr(self.memory_cache, "hits", 0),
            "memory_misses": getattr(self.memory_cache, "misses", 0),
            "redis_available": self.redis_client is not None,
        }
```

### 9. SDK PromptManager

**Location**: `src/omniforge/prompts/sdk/manager.py`

```python
"""SDK interface for prompt management.

Provides a clean, developer-friendly API for programmatic prompt operations.
"""

from typing import Any, Optional
from uuid import UUID

from omniforge.prompts.cache.manager import CacheManager
from omniforge.prompts.composition.engine import CompositionEngine
from omniforge.prompts.enums import PromptLayer
from omniforge.prompts.errors import PromptNotFoundError, PromptVersionNotFoundError
from omniforge.prompts.models import (
    ComposedPrompt,
    MergePointDefinition,
    Prompt,
    PromptExperiment,
    PromptVersion,
    VariableSchema,
)
from omniforge.prompts.storage.memory import InMemoryPromptRepository
from omniforge.prompts.storage.repository import PromptRepository
from omniforge.prompts.validation.syntax import SyntaxValidator
from omniforge.prompts.versioning.manager import VersionManager


class PromptManager:
    """SDK interface for prompt management.

    Provides programmatic access to all prompt operations including
    CRUD, versioning, composition, and validation.

    Example:
        >>> manager = PromptManager(tenant_id="acme-corp")
        >>>
        >>> # Create a prompt
        >>> prompt = manager.create_prompt(
        ...     layer=PromptLayer.TENANT,
        ...     name="brand_voice",
        ...     content="Respond in a {{ tone }} tone.",
        ...     variables_schema={"tone": {"type": "string"}}
        ... )
        >>>
        >>> # Compose prompt for an agent
        >>> composed = await manager.compose_prompt(
        ...     agent_id="agent-123",
        ...     variables={"tone": "friendly"}
        ... )
    """

    def __init__(
        self,
        tenant_id: Optional[str] = None,
        repository: Optional[PromptRepository] = None,
    ) -> None:
        """Initialize prompt manager.

        Args:
            tenant_id: Default tenant ID for operations
            repository: Storage backend (in-memory default)
        """
        self.tenant_id = tenant_id
        self.repository = repository or InMemoryPromptRepository()
        self.cache = CacheManager()
        self.composition_engine = CompositionEngine(
            repository=self.repository,
            cache=self.cache,
        )
        self.version_manager = VersionManager(repository=self.repository)
        self.syntax_validator = SyntaxValidator()

    # ========== Prompt CRUD ==========

    async def create_prompt(
        self,
        layer: PromptLayer,
        name: str,
        content: str,
        scope_id: Optional[str] = None,
        description: str = "",
        merge_points: Optional[list[dict[str, Any]]] = None,
        variables_schema: Optional[dict[str, Any]] = None,
        created_by: str = "sdk",
    ) -> Prompt:
        """Create a new prompt.

        Args:
            layer: Which layer this prompt belongs to
            name: Human-readable name
            content: Jinja2 template content
            scope_id: Context identifier (tenant_id, feature_id, agent_id)
            description: Prompt description
            merge_points: Merge point definitions
            variables_schema: JSON Schema for variables
            created_by: User/system identifier

        Returns:
            Created prompt

        Raises:
            PromptValidationError: If content has syntax errors
        """
        # Validate syntax
        errors = self.syntax_validator.validate(content)
        if errors:
            from omniforge.prompts.errors import PromptValidationError
            raise PromptValidationError(
                message="Template syntax validation failed",
                errors=[{"message": e} for e in errors],
            )

        # Build merge point definitions
        mp_defs = []
        if merge_points:
            mp_defs = [MergePointDefinition(**mp) for mp in merge_points]

        # Build variable schema
        var_schema = VariableSchema()
        if variables_schema:
            var_schema = VariableSchema(
                properties=variables_schema,
                required=list(variables_schema.keys()),
            )

        prompt = Prompt(
            layer=layer,
            scope_id=scope_id,
            name=name,
            description=description,
            content=content,
            merge_points=mp_defs,
            variables_schema=var_schema,
            created_by=created_by,
            tenant_id=self.tenant_id,
        )

        created = await self.repository.create(prompt)

        # Create initial version
        await self.version_manager.create_initial_version(
            prompt=created,
            created_by=created_by,
        )

        return created

    async def get_prompt(self, prompt_id: str) -> Prompt:
        """Get a prompt by ID.

        Args:
            prompt_id: Prompt identifier

        Returns:
            Prompt

        Raises:
            PromptNotFoundError: If prompt not found
        """
        prompt = await self.repository.get(prompt_id)
        if not prompt:
            raise PromptNotFoundError(prompt_id)
        return prompt

    async def update_prompt(
        self,
        prompt_id: str,
        content: str,
        change_message: str,
        changed_by: str = "sdk",
        merge_points: Optional[list[dict[str, Any]]] = None,
        variables_schema: Optional[dict[str, Any]] = None,
    ) -> Prompt:
        """Update a prompt (creates new version).

        Args:
            prompt_id: Prompt to update
            content: New template content
            change_message: Description of the change
            changed_by: User making the change
            merge_points: Optional new merge points
            variables_schema: Optional new variable schema

        Returns:
            Updated prompt

        Raises:
            PromptNotFoundError: If prompt not found
            PromptValidationError: If content has syntax errors
        """
        prompt = await self.get_prompt(prompt_id)

        # Validate syntax
        errors = self.syntax_validator.validate(content)
        if errors:
            from omniforge.prompts.errors import PromptValidationError
            raise PromptValidationError(
                message="Template syntax validation failed",
                errors=[{"message": e} for e in errors],
            )

        # Update fields
        prompt.content = content
        if merge_points:
            prompt.merge_points = [MergePointDefinition(**mp) for mp in merge_points]
        if variables_schema:
            prompt.variables_schema = VariableSchema(
                properties=variables_schema,
                required=list(variables_schema.keys()),
            )

        # Create new version
        await self.version_manager.create_version(
            prompt=prompt,
            change_message=change_message,
            changed_by=changed_by,
        )

        # Invalidate cache
        await self.cache.invalidate_pattern(str(prompt.id))

        return await self.repository.update(prompt)

    async def delete_prompt(self, prompt_id: str) -> None:
        """Soft-delete a prompt.

        Args:
            prompt_id: Prompt to delete

        Raises:
            PromptNotFoundError: If prompt not found
        """
        await self.get_prompt(prompt_id)  # Verify exists
        await self.repository.delete(prompt_id)
        await self.cache.invalidate_pattern(str(prompt_id))

    # ========== Versioning ==========

    async def get_prompt_history(
        self,
        prompt_id: str,
        limit: int = 50,
    ) -> list[PromptVersion]:
        """Get version history for a prompt.

        Args:
            prompt_id: Prompt ID
            limit: Maximum versions to return

        Returns:
            List of versions, newest first
        """
        await self.get_prompt(prompt_id)  # Verify exists
        return await self.repository.list_versions(prompt_id, limit)

    async def rollback_prompt(
        self,
        prompt_id: str,
        to_version: int,
        rolled_back_by: str = "sdk",
    ) -> Prompt:
        """Rollback prompt to a previous version.

        Args:
            prompt_id: Prompt to rollback
            to_version: Version number to restore
            rolled_back_by: User performing rollback

        Returns:
            Updated prompt

        Raises:
            PromptVersionNotFoundError: If version not found
        """
        version = await self.repository.get_version(prompt_id, to_version)
        if not version:
            raise PromptVersionNotFoundError(prompt_id, to_version)

        await self.repository.set_current_version(prompt_id, str(version.id))
        await self.cache.invalidate_pattern(prompt_id)

        return await self.get_prompt(prompt_id)

    # ========== Composition ==========

    async def compose_prompt(
        self,
        agent_id: str,
        feature_ids: Optional[list[str]] = None,
        user_input: Optional[str] = None,
        variables: Optional[dict[str, Any]] = None,
        skip_cache: bool = False,
    ) -> ComposedPrompt:
        """Compose a prompt for an agent.

        Loads prompts from all applicable layers, applies merge logic,
        and renders the final template.

        Args:
            agent_id: Agent identifier
            feature_ids: Feature identifiers
            user_input: User's input (safely escaped)
            variables: Template variables
            skip_cache: Bypass cache if True

        Returns:
            ComposedPrompt with rendered content
        """
        return await self.composition_engine.compose(
            agent_id=agent_id,
            tenant_id=self.tenant_id,
            feature_ids=feature_ids,
            user_input=user_input,
            variables=variables,
            skip_cache=skip_cache,
        )

    # ========== Validation ==========

    def validate_template(self, content: str) -> list[str]:
        """Validate template syntax.

        Args:
            content: Jinja2 template content

        Returns:
            List of validation errors (empty if valid)
        """
        return self.syntax_validator.validate(content)
```

---

## Database Schema

### Entity-Relationship Diagram

```
+----------------------+       +------------------------+
|       prompts        |       |    prompt_versions     |
+----------------------+       +------------------------+
| id (PK)              |<------| id (PK)                |
| layer                |       | prompt_id (FK)         |
| scope_id             |       | version_number         |
| name                 |       | content                |
| description          |       | variables_schema (JSON)|
| content              |       | merge_points (JSON)    |
| merge_points (JSON)  |       | change_message         |
| variables_schema     |       | changed_by             |
| metadata (JSON)      |       | changed_at             |
| created_at           |       | is_current             |
| created_by           |       +------------------------+
| is_active            |
| current_version_id   |       +------------------------+
| tenant_id            |       |  prompt_experiments    |
+----------------------+       +------------------------+
         |                     | id (PK)                |
         +-------------------->| prompt_id (FK)         |
                               | name                   |
                               | description            |
                               | status                 |
                               | variants (JSON)        |
                               | success_metric         |
                               | start_date             |
                               | end_date               |
                               | results (JSON)         |
                               | created_by             |
                               | tenant_id              |
                               +------------------------+

+------------------------+
|    prompt_cache        |
+------------------------+
| cache_key (PK)         |
| composed_content       |
| layer_versions (JSON)  |
| variables_hash         |
| created_at             |
| expires_at             |
+------------------------+
```

### SQL Schema (PostgreSQL)

```sql
-- Prompts table
CREATE TABLE prompts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    layer VARCHAR(20) NOT NULL CHECK (layer IN ('system', 'tenant', 'feature', 'agent', 'user')),
    scope_id VARCHAR(255),
    name VARCHAR(255) NOT NULL,
    description TEXT DEFAULT '',
    content TEXT NOT NULL,
    merge_points JSONB DEFAULT '[]'::jsonb,
    variables_schema JSONB DEFAULT '{}'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    current_version_id UUID,
    tenant_id VARCHAR(255),

    UNIQUE (layer, scope_id) WHERE is_active = TRUE
);

-- Indexes for prompts
CREATE INDEX idx_prompts_layer_scope ON prompts(layer, scope_id) WHERE is_active = TRUE;
CREATE INDEX idx_prompts_tenant ON prompts(tenant_id) WHERE is_active = TRUE;
CREATE INDEX idx_prompts_created_at ON prompts(created_at DESC);

-- Prompt versions table
CREATE TABLE prompt_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prompt_id UUID NOT NULL REFERENCES prompts(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    content TEXT NOT NULL,
    variables_schema JSONB DEFAULT '{}'::jsonb,
    merge_points JSONB DEFAULT '[]'::jsonb,
    change_message VARCHAR(1000) NOT NULL,
    changed_by VARCHAR(255) NOT NULL,
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_current BOOLEAN DEFAULT FALSE,

    UNIQUE (prompt_id, version_number)
);

-- Indexes for versions
CREATE INDEX idx_versions_prompt ON prompt_versions(prompt_id);
CREATE INDEX idx_versions_current ON prompt_versions(prompt_id) WHERE is_current = TRUE;

-- Experiments table
CREATE TABLE prompt_experiments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prompt_id UUID NOT NULL REFERENCES prompts(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT DEFAULT '',
    status VARCHAR(20) NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'running', 'paused', 'completed', 'cancelled')),
    variants JSONB NOT NULL DEFAULT '[]'::jsonb,
    success_metric VARCHAR(100) NOT NULL,
    start_date TIMESTAMP WITH TIME ZONE,
    end_date TIMESTAMP WITH TIME ZONE,
    results JSONB DEFAULT '{}'::jsonb,
    created_by VARCHAR(255) NOT NULL,
    tenant_id VARCHAR(255)
);

-- Indexes for experiments
CREATE INDEX idx_experiments_prompt ON prompt_experiments(prompt_id);
CREATE INDEX idx_experiments_status ON prompt_experiments(status) WHERE status = 'running';
CREATE INDEX idx_experiments_tenant ON prompt_experiments(tenant_id);

-- Cache table (optional, for database-backed caching)
CREATE TABLE prompt_cache (
    cache_key VARCHAR(64) PRIMARY KEY,
    composed_content TEXT NOT NULL,
    layer_versions JSONB NOT NULL,
    variables_hash VARCHAR(32),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL
);

-- Index for cache expiry cleanup
CREATE INDEX idx_cache_expires ON prompt_cache(expires_at);

-- Add foreign key constraint for current_version_id
ALTER TABLE prompts
    ADD CONSTRAINT fk_current_version
    FOREIGN KEY (current_version_id)
    REFERENCES prompt_versions(id);
```

---

## API Design

### REST API Endpoints

**Location**: `src/omniforge/api/routes/prompts.py`

| Method | Path | Description | Auth Required |
|--------|------|-------------|---------------|
| **Prompt CRUD** |
| GET | `/api/v1/prompts` | List prompts (filtered by layer, tenant) | Yes |
| POST | `/api/v1/prompts` | Create prompt | Yes |
| GET | `/api/v1/prompts/{id}` | Get prompt | Yes |
| PUT | `/api/v1/prompts/{id}` | Update prompt (creates version) | Yes |
| DELETE | `/api/v1/prompts/{id}` | Soft delete prompt | Yes |
| **Versioning** |
| GET | `/api/v1/prompts/{id}/versions` | List versions | Yes |
| GET | `/api/v1/prompts/{id}/versions/{v}` | Get specific version | Yes |
| POST | `/api/v1/prompts/{id}/rollback` | Rollback to version | Yes |
| **Composition** |
| POST | `/api/v1/prompts/compose` | Compose prompt for agent | Yes |
| POST | `/api/v1/prompts/preview` | Preview composition without caching | Yes |
| **Validation** |
| POST | `/api/v1/prompts/validate` | Validate template syntax | Yes |
| **A/B Testing** |
| POST | `/api/v1/prompts/{id}/experiments` | Create experiment | Yes |
| GET | `/api/v1/prompts/{id}/experiments` | List experiments | Yes |
| GET | `/api/v1/experiments/{id}` | Get experiment | Yes |
| PUT | `/api/v1/experiments/{id}` | Update experiment | Yes |
| POST | `/api/v1/experiments/{id}/start` | Start experiment | Yes |
| POST | `/api/v1/experiments/{id}/stop` | Stop experiment | Yes |
| POST | `/api/v1/experiments/{id}/promote` | Promote winning variant | Yes |
| **Cache Management** |
| DELETE | `/api/v1/prompts/cache` | Clear cache (admin) | Admin |
| GET | `/api/v1/prompts/cache/stats` | Cache statistics | Admin |

### Request/Response Models

```python
# Request models
class PromptCreateRequest(BaseModel):
    layer: PromptLayer
    name: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1, max_length=100000)
    scope_id: Optional[str] = Field(None, max_length=255)
    description: str = ""
    merge_points: list[dict[str, Any]] = Field(default_factory=list)
    variables_schema: dict[str, Any] = Field(default_factory=dict)


class PromptUpdateRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=100000)
    change_message: str = Field(..., min_length=1, max_length=1000)
    merge_points: Optional[list[dict[str, Any]]] = None
    variables_schema: Optional[dict[str, Any]] = None


class PromptComposeRequest(BaseModel):
    agent_id: str = Field(..., min_length=1, max_length=255)
    feature_ids: list[str] = Field(default_factory=list)
    user_input: Optional[str] = None
    variables: dict[str, Any] = Field(default_factory=dict)
    skip_cache: bool = False


class PromptRollbackRequest(BaseModel):
    to_version: int = Field(..., ge=1)


class ExperimentCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    success_metric: str = Field(..., min_length=1, max_length=100)
    variants: list[dict[str, Any]]


# Response models
class PromptResponse(BaseModel):
    id: UUID
    layer: PromptLayer
    scope_id: Optional[str]
    name: str
    description: str
    current_version: int
    created_at: datetime
    created_by: str


class PromptVersionResponse(BaseModel):
    version_number: int
    content: str
    change_message: str
    changed_by: str
    changed_at: datetime
    is_current: bool


class ComposedPromptResponse(BaseModel):
    content: str
    composition_time_ms: float
    cache_hit: bool
    experiment_variant: Optional[str]
```

---

## Security Implementation

### RBAC Extensions

Add the following permissions to `src/omniforge/security/rbac.py`:

```python
class Permission(str, Enum):
    # ... existing permissions ...

    # Prompt permissions
    PROMPT_CREATE = "prompt:create"
    PROMPT_READ = "prompt:read"
    PROMPT_UPDATE = "prompt:update"
    PROMPT_DELETE = "prompt:delete"
    PROMPT_COMPOSE = "prompt:compose"

    # Experiment permissions
    EXPERIMENT_CREATE = "experiment:create"
    EXPERIMENT_READ = "experiment:read"
    EXPERIMENT_UPDATE = "experiment:update"
    EXPERIMENT_DELETE = "experiment:delete"

    # Cache permissions
    CACHE_CLEAR = "cache:clear"
    CACHE_STATS = "cache:stats"


# Extended role permissions
ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.VIEWER: {
        # ... existing ...
        Permission.PROMPT_READ,
        Permission.EXPERIMENT_READ,
    },
    Role.OPERATOR: {
        # ... existing ...
        Permission.PROMPT_READ,
        Permission.PROMPT_COMPOSE,
        Permission.EXPERIMENT_READ,
    },
    Role.DEVELOPER: {
        # ... existing ...
        Permission.PROMPT_CREATE,
        Permission.PROMPT_READ,
        Permission.PROMPT_UPDATE,
        Permission.PROMPT_COMPOSE,
        Permission.EXPERIMENT_CREATE,
        Permission.EXPERIMENT_READ,
        Permission.EXPERIMENT_UPDATE,
    },
    Role.ADMIN: {
        # All permissions
        # ... existing ...
        Permission.PROMPT_CREATE,
        Permission.PROMPT_READ,
        Permission.PROMPT_UPDATE,
        Permission.PROMPT_DELETE,
        Permission.PROMPT_COMPOSE,
        Permission.EXPERIMENT_CREATE,
        Permission.EXPERIMENT_READ,
        Permission.EXPERIMENT_UPDATE,
        Permission.EXPERIMENT_DELETE,
        Permission.CACHE_CLEAR,
        Permission.CACHE_STATS,
    },
}
```

### Layer-Based Access Control

```python
"""Layer-based access control for prompts.

Enforces that users can only modify prompts at their authorized layers.
"""

from omniforge.prompts.enums import PromptLayer
from omniforge.security.rbac import Role


# Layer access by role
LAYER_ACCESS: dict[Role, set[PromptLayer]] = {
    Role.VIEWER: set(),  # Read-only, no layer modification
    Role.OPERATOR: set(),  # No prompt modification
    Role.DEVELOPER: {
        PromptLayer.FEATURE,
        PromptLayer.AGENT,
    },
    Role.ADMIN: {
        PromptLayer.SYSTEM,
        PromptLayer.TENANT,
        PromptLayer.FEATURE,
        PromptLayer.AGENT,
    },
}


def can_modify_layer(role: Role, layer: PromptLayer) -> bool:
    """Check if a role can modify prompts at a specific layer.

    Args:
        role: User's role
        layer: Layer to modify

    Returns:
        True if allowed, False otherwise
    """
    return layer in LAYER_ACCESS.get(role, set())
```

### Tenant Isolation

All prompt operations automatically filter by the current tenant context:

```python
async def list_prompts_for_tenant(
    tenant_id: str,
    repository: PromptRepository,
) -> list[Prompt]:
    """List prompts with tenant isolation enforced.

    System-layer prompts are visible to all tenants.
    Tenant-layer prompts are only visible to the owning tenant.
    """
    prompts = []

    # System prompts (visible to all)
    system_prompt = await repository.get_by_layer(PromptLayer.SYSTEM, None)
    if system_prompt:
        prompts.append(system_prompt)

    # Tenant-specific prompts
    tenant_prompts = await repository.list_by_tenant(tenant_id)
    prompts.extend(tenant_prompts)

    return prompts
```

---

## Performance Considerations

### Composition Optimization

1. **Cache Key Design**: Cache keys incorporate version IDs, not content hashes, allowing quick invalidation when versions change

2. **Lazy Loading**: Feature prompts are only loaded when `feature_ids` are provided

3. **Parallel Loading**: Multiple layer prompts can be loaded concurrently:
```python
async def _load_layer_prompts_parallel(self, ...):
    tasks = [
        self.repository.get_by_layer(PromptLayer.SYSTEM, None),
        self.repository.get_by_layer(PromptLayer.TENANT, tenant_id),
        self.repository.get_by_layer(PromptLayer.AGENT, agent_id),
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    # ... process results
```

4. **Pre-computed Merge Templates**: For frequently used layer combinations, pre-compute the merged template structure

### Caching Strategy

| Cache Tier | Storage | TTL | Hit Latency | Miss Latency |
|------------|---------|-----|-------------|--------------|
| Memory (L1) | In-process LRU | 5 min | < 0.1ms | N/A |
| Redis (L2) | Distributed | 1 hour | 1-5ms | N/A |
| Database (L3) | PostgreSQL | Permanent | 10-50ms | N/A |

**Cache Invalidation Triggers:**
- Prompt version change: Invalidate all cache entries containing that prompt ID
- Experiment start/stop: Invalidate cache entries for affected prompt
- Manual flush: Admin can clear all caches

### Performance Targets

| Operation | Target Latency | Notes |
|-----------|----------------|-------|
| Composition (cached) | < 1ms p95 | Memory cache hit |
| Composition (cold) | < 10ms p95 | Full composition without cache |
| Version creation | < 50ms | Database write |
| Rollback | < 100ms | Version switch + cache invalidation |
| Template validation | < 5ms | Syntax check only |

---

## Testing Strategy

### Unit Tests

**Target**: 80%+ coverage

```python
# tests/prompts/test_models.py
class TestPromptModels:
    def test_prompt_content_validation(self) -> None:
        """Prompt content cannot be empty or whitespace."""
        with pytest.raises(ValueError):
            Prompt(
                layer=PromptLayer.SYSTEM,
                name="test",
                content="   ",  # Whitespace only
                created_by="test",
            )

    def test_experiment_traffic_allocation_validation(self) -> None:
        """Experiment variants must sum to 100%."""
        with pytest.raises(ValueError):
            PromptExperiment(
                prompt_id=uuid4(),
                name="test",
                success_metric="satisfaction",
                variants=[
                    ExperimentVariant(id="a", name="A", prompt_version_id=uuid4(), traffic_percentage=30),
                    ExperimentVariant(id="b", name="B", prompt_version_id=uuid4(), traffic_percentage=30),
                ],
                created_by="test",
            )


# tests/prompts/test_composition.py
class TestCompositionEngine:
    @pytest.mark.asyncio
    async def test_compose_with_all_layers(self) -> None:
        """Composition merges content from all layers."""
        # Setup prompts at each layer
        # Call compose
        # Assert merged content includes all layer contributions

    @pytest.mark.asyncio
    async def test_locked_merge_point_not_overridden(self) -> None:
        """Locked merge points preserve system content."""
        # Create system prompt with locked safety guidelines
        # Create tenant prompt trying to override
        # Assert system content is preserved


# tests/prompts/test_cache.py
class TestCacheManager:
    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached_value(self) -> None:
        """Cache returns stored value on hit."""
        cache = CacheManager()
        composed = ComposedPrompt(content="test", layer_versions={})
        await cache.set("key", composed)
        result = await cache.get("key")
        assert result.content == "test"

    @pytest.mark.asyncio
    async def test_invalidate_pattern_clears_matching(self) -> None:
        """Pattern invalidation clears matching keys."""
        cache = CacheManager()
        await cache.set("sys:v1:agent1", ComposedPrompt(content="a"))
        await cache.set("sys:v1:agent2", ComposedPrompt(content="b"))
        await cache.set("sys:v2:agent1", ComposedPrompt(content="c"))

        count = await cache.invalidate_pattern("v1")
        assert count == 2
```

### Integration Tests

```python
# tests/prompts/test_integration.py
class TestPromptAPIIntegration:
    @pytest.mark.asyncio
    async def test_create_update_compose_flow(self, client: AsyncClient) -> None:
        """Full flow: create prompt, update, compose."""
        # Create prompt
        response = await client.post("/api/v1/prompts", json={
            "layer": "tenant",
            "name": "brand_voice",
            "content": "Be {{ tone }}.",
        })
        assert response.status_code == 201
        prompt_id = response.json()["id"]

        # Update prompt
        response = await client.put(f"/api/v1/prompts/{prompt_id}", json={
            "content": "Be {{ tone }} and helpful.",
            "change_message": "Added helpfulness",
        })
        assert response.status_code == 200

        # Compose
        response = await client.post("/api/v1/prompts/compose", json={
            "agent_id": "test-agent",
            "variables": {"tone": "friendly"},
        })
        assert response.status_code == 200
        assert "friendly and helpful" in response.json()["content"]


class TestTenantIsolation:
    @pytest.mark.asyncio
    async def test_tenant_cannot_access_other_tenant_prompts(
        self, client: AsyncClient
    ) -> None:
        """Tenant isolation prevents cross-tenant access."""
        # Create prompt as tenant A
        # Try to access as tenant B
        # Assert 404 or 403
```

---

## Risk Assessment

### Technical Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Jinja2 security vulnerabilities | High | Low | Use SandboxedEnvironment, restrict allowed features |
| Cache inconsistency | Medium | Medium | Version-based cache keys, aggressive invalidation |
| Composition performance degradation | Medium | Medium | Caching, parallel loading, pre-computed templates |
| Merge conflict resolution complexity | Medium | Medium | Clear priority rules, conflict detection UI |
| A/B test statistical errors | Medium | Low | Built-in significance testing, sample size warnings |
| Database schema migration complexity | Medium | Low | Incremental migrations, backward compatibility |

### Dependency Risks

| Dependency | Risk | Mitigation |
|------------|------|------------|
| Jinja2 | Low (stable library) | Pin to 3.1.x, extensive templating tests |
| Redis | Low | Optional dependency, graceful fallback to memory |
| SQLAlchemy | Low | Already planned for platform |
| cachetools | Low | Small, stable library |

---

## Implementation Phases

### Phase 1: Core Foundation (Week 1-2)

**Goal**: Basic prompt CRUD with models and in-memory storage

**Deliverables**:
1. `prompts/models.py` - Prompt, PromptVersion, MergePoint models
2. `prompts/enums.py` - PromptLayer, MergeBehavior enums
3. `prompts/errors.py` - Exception hierarchy
4. `prompts/storage/repository.py` - Repository Protocol
5. `prompts/storage/memory.py` - In-memory implementation
6. Unit tests for all models

**Success Criteria**:
- [ ] Models validate correctly
- [ ] In-memory storage passes all CRUD tests
- [ ] 80%+ test coverage

### Phase 2: Composition Engine (Week 3-4)

**Goal**: Layer merging and template rendering

**Deliverables**:
1. `prompts/composition/engine.py` - Main composition logic
2. `prompts/composition/merge.py` - Merge point processing
3. `prompts/composition/renderer.py` - Jinja2 sandboxed rendering
4. `prompts/validation/syntax.py` - Template syntax validation
5. `prompts/cache/manager.py` - Basic caching
6. Integration tests for composition

**Success Criteria**:
- [ ] Multi-layer composition works correctly
- [ ] Locked merge points enforced
- [ ] Template rendering is sandboxed
- [ ] Syntax validation catches errors

### Phase 3: Versioning & Validation (Week 5-6)

**Goal**: Version history, rollback, and content validation

**Deliverables**:
1. `prompts/versioning/manager.py` - Version lifecycle
2. `prompts/validation/content.py` - Content rules
3. `prompts/validation/schema.py` - Variable schema validation
4. `prompts/validation/safety.py` - Injection detection
5. Database schema and migrations
6. `prompts/storage/database.py` - SQLAlchemy implementation

**Success Criteria**:
- [ ] Versions are immutable
- [ ] Rollback restores previous state
- [ ] Content validation catches prohibited content
- [ ] Variable schemas enforce types

### Phase 4: A/B Testing (Week 7)

**Goal**: Experiment creation and traffic splitting

**Deliverables**:
1. `prompts/experiments/manager.py` - Experiment lifecycle
2. `prompts/experiments/allocation.py` - Traffic splitting
3. `prompts/experiments/analysis.py` - Statistical analysis
4. Experiment API endpoints

**Success Criteria**:
- [ ] Experiments can be created and started
- [ ] Traffic is correctly split between variants
- [ ] Metrics are collected per variant
- [ ] Winner promotion works

### Phase 5: SDK & API Integration (Week 8)

**Goal**: Developer-facing SDK and REST API

**Deliverables**:
1. `prompts/sdk/manager.py` - PromptManager class
2. `prompts/sdk/config.py` - PromptConfig for agents
3. `api/routes/prompts.py` - REST API endpoints
4. Agent integration (`agents/base.py` modifications)
5. RBAC extensions (`security/rbac.py`)
6. Documentation

**Success Criteria**:
- [ ] SDK provides clean API
- [ ] REST endpoints pass integration tests
- [ ] Agent prompt_config works
- [ ] RBAC enforces permissions

---

## Alternative Approaches Considered

### Alternative 1: File-Based Prompt Storage

**Description**: Store prompts as Jinja2 files in a directory structure.

**Pros**:
- Simple to understand and edit
- Version control via Git
- No database required

**Cons**:
- No runtime updates without deployment
- Difficult multi-tenant isolation
- No A/B testing support
- Does not meet product requirements

**Decision**: Rejected - Product spec explicitly requires database-only storage.

### Alternative 2: Template Inheritance Instead of Merge Points

**Description**: Use Jinja2's native `{% extends %}` and `{% block %}` for layering.

**Pros**:
- Familiar to developers
- Built-in Jinja2 feature
- Clean syntax

**Cons**:
- Requires file-based templates (contradicts DB-only requirement)
- Less flexible for non-technical users
- Harder to control merge behavior programmatically

**Decision**: Rejected for primary mechanism, but can be supported for advanced SDK users who prefer inheritance patterns.

### Alternative 3: Single-Table Versioning (SCD Type 2)

**Description**: Store all versions in the prompts table with effective dates.

**Pros**:
- Simpler schema
- Single table queries

**Cons**:
- Complex queries for current version
- Harder to maintain constraints
- More difficult to list version history

**Decision**: Rejected - Separate versions table is cleaner and matches existing patterns.

### Alternative 4: Event Sourcing for Prompt Changes

**Description**: Store all changes as events, rebuild state on read.

**Pros**:
- Complete audit trail
- Natural undo/redo
- Time-travel queries

**Cons**:
- Higher read latency
- More complex implementation
- Overkill for prompt management

**Decision**: Rejected for MVP - Consider for future audit requirements.

---

## Open Questions Resolution

### Q1: Template Inheritance vs. Composition

**Resolution**: Support both, but default to merge points.
- Merge points: Primary mechanism for all layers
- Template inheritance: Optional for SDK users who prefer it
- UI/dashboard always uses merge points

### Q2: Variable Namespacing

**Resolution**: Prefix-based namespaces.
- `system.*`: Platform variables
- `tenant.*`: Tenant variables
- `agent.*`: Agent variables
- User variables: No prefix (top-level)

This prevents collisions while keeping user variables simple.

### Q3: Prompt Testing Environment

**Resolution**: Preview mode with no persistence.
- `POST /api/v1/prompts/preview`: Compose without caching
- SDK: `compose(..., skip_cache=True)`
- Dashboard: "Preview" button shows sample output

### Q4: Historical Prompt Lookup

**Resolution**: Store version references with conversations.
- Each conversation stores: `{prompt_id, version_id}` for each layer
- Reconstruction is fast (point lookups by ID)
- Full composed prompt can be regenerated

### Q5: A/B Test Metrics

**Resolution**: Flexible metric collection.
- Built-in: Response time, completion rate
- Custom: SDK allows registering custom metrics
- Integration: Webhook for external analytics

---

## References

- [Product Specification](/Users/sohitkumar/code/omniforge/specs/prompt-management-spec.md)
- [Coding Guidelines](/Users/sohitkumar/code/omniforge/coding-guidelines.md)
- [Base Agent Interface Plan](/Users/sohitkumar/code/omniforge/specs/base-agent-interface-plan.md)
- [Existing RBAC Implementation](/Users/sohitkumar/code/omniforge/src/omniforge/security/rbac.py)
- [Existing Tenant Context](/Users/sohitkumar/code/omniforge/src/omniforge/security/tenant.py)
- [Repository Pattern](/Users/sohitkumar/code/omniforge/src/omniforge/storage/base.py)
- [Jinja2 Documentation](https://jinja.palletsprojects.com/)
